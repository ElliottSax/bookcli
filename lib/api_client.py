"""
Centralized API client for BookCLI.

Provides unified access to all LLM APIs with:
- Consistent error handling
- Automatic retries with exponential backoff
- Rate limiting
- Circuit breaker pattern
- Round-robin load balancing
- Thread-safe operation
- Response caching with TTL
"""

import hashlib
import threading
import time
import json
import re
from collections import OrderedDict
from pathlib import Path
from typing import Optional, Dict, Any, List, Callable, Tuple
from dataclasses import dataclass, field
import requests
from requests.exceptions import RequestException, Timeout, ConnectionError

from .config import get_config, APIConfig
from .logging_config import get_logger
from .retry import retry_with_backoff, RateLimiter, CircuitBreaker, CircuitBreakerOpen

logger = get_logger(__name__)


# =============================================================================
# Response Cache
# =============================================================================

@dataclass
class CacheEntry:
    """Single cache entry with TTL tracking."""
    response: 'APIResponse'
    created_at: float
    ttl_seconds: float

    @property
    def is_expired(self) -> bool:
        return time.time() - self.created_at > self.ttl_seconds


class ResponseCache:
    """
    LRU cache for API responses with TTL support.

    Features:
    - Hash-based key generation from prompt + parameters
    - TTL (time-to-live) support for cache entries
    - Maximum size with LRU eviction
    - Thread-safe operation
    - Optional disk persistence
    - Cache statistics

    Example:
        cache = ResponseCache(max_size=1000, default_ttl=3600)

        # Check cache
        key = cache.make_key(prompt="Hello", max_tokens=100)
        if cached := cache.get(key):
            return cached

        # Store result
        cache.set(key, response)
    """

    def __init__(
        self,
        max_size: int = 1000,
        default_ttl: float = 3600.0,  # 1 hour default
        enabled: bool = True,
        cache_file: Optional[Path] = None,
    ):
        """
        Initialize response cache.

        Args:
            max_size: Maximum number of entries to store
            default_ttl: Default time-to-live in seconds
            enabled: Whether caching is enabled
            cache_file: Optional path to persist cache to disk
        """
        self.max_size = max_size
        self.default_ttl = default_ttl
        self.enabled = enabled
        self.cache_file = cache_file

        self._cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self._lock = threading.Lock()

        # Statistics
        self._hits = 0
        self._misses = 0
        self._evictions = 0

        # Load from disk if available
        if cache_file and cache_file.exists():
            self._load_from_disk()

    def make_key(
        self,
        prompt: str,
        max_tokens: int = 4000,
        temperature: float = 0.7,
        system_prompt: Optional[str] = None,
    ) -> str:
        """
        Generate a cache key from request parameters.

        Uses SHA256 hash for consistent, collision-resistant keys.
        """
        key_data = f"{prompt}|{max_tokens}|{temperature}|{system_prompt or ''}"
        return hashlib.sha256(key_data.encode()).hexdigest()[:32]

    def get(self, key: str) -> Optional['APIResponse']:
        """
        Get a cached response if available and not expired.

        Args:
            key: Cache key from make_key()

        Returns:
            Cached APIResponse or None if not found/expired
        """
        if not self.enabled:
            return None

        with self._lock:
            entry = self._cache.get(key)

            if entry is None:
                self._misses += 1
                return None

            if entry.is_expired:
                del self._cache[key]
                self._misses += 1
                return None

            # Move to end for LRU
            self._cache.move_to_end(key)
            self._hits += 1

            # Return a copy with cache indicator
            response = entry.response
            logger.debug(f"Cache hit for key {key[:8]}...")
            return response

    def set(
        self,
        key: str,
        response: 'APIResponse',
        ttl: Optional[float] = None,
    ) -> None:
        """
        Store a response in the cache.

        Args:
            key: Cache key from make_key()
            response: APIResponse to cache
            ttl: Optional custom TTL (uses default if not specified)
        """
        if not self.enabled:
            return

        if not response.success:
            return  # Don't cache failures

        with self._lock:
            # Evict if at capacity
            while len(self._cache) >= self.max_size:
                oldest_key = next(iter(self._cache))
                del self._cache[oldest_key]
                self._evictions += 1

            self._cache[key] = CacheEntry(
                response=response,
                created_at=time.time(),
                ttl_seconds=ttl or self.default_ttl,
            )

            logger.debug(f"Cached response for key {key[:8]}...")

    def clear(self) -> int:
        """Clear all cache entries. Returns number of entries cleared."""
        with self._lock:
            count = len(self._cache)
            self._cache.clear()
            return count

    def cleanup_expired(self) -> int:
        """Remove expired entries. Returns number removed."""
        with self._lock:
            expired_keys = [
                key for key, entry in self._cache.items()
                if entry.is_expired
            ]
            for key in expired_keys:
                del self._cache[key]
            return len(expired_keys)

    @property
    def stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        with self._lock:
            total = self._hits + self._misses
            hit_rate = (self._hits / total * 100) if total > 0 else 0.0
            return {
                "size": len(self._cache),
                "max_size": self.max_size,
                "hits": self._hits,
                "misses": self._misses,
                "hit_rate": f"{hit_rate:.1f}%",
                "evictions": self._evictions,
                "enabled": self.enabled,
            }

    def _save_to_disk(self) -> None:
        """Persist cache to disk."""
        if not self.cache_file:
            return

        with self._lock:
            data = {
                key: {
                    "content": entry.response.content,
                    "api_name": entry.response.api_name,
                    "model": entry.response.model,
                    "created_at": entry.created_at,
                    "ttl_seconds": entry.ttl_seconds,
                }
                for key, entry in self._cache.items()
                if not entry.is_expired
            }

        self.cache_file.write_text(json.dumps(data, indent=2))
        logger.info(f"Saved {len(data)} cache entries to disk")

    def _load_from_disk(self) -> None:
        """Load cache from disk."""
        if not self.cache_file or not self.cache_file.exists():
            return

        try:
            data = json.loads(self.cache_file.read_text())

            with self._lock:
                for key, entry_data in data.items():
                    # Skip if would be expired
                    age = time.time() - entry_data["created_at"]
                    if age > entry_data["ttl_seconds"]:
                        continue

                    self._cache[key] = CacheEntry(
                        response=APIResponse(
                            content=entry_data["content"],
                            success=True,
                            api_name=entry_data["api_name"],
                            model=entry_data["model"],
                        ),
                        created_at=entry_data["created_at"],
                        ttl_seconds=entry_data["ttl_seconds"],
                    )

            logger.info(f"Loaded {len(self._cache)} cache entries from disk")

        except Exception as e:
            logger.warning(f"Failed to load cache from disk: {e}")


@dataclass
class APIResponse:
    """Standardized response from any API."""
    content: Optional[str] = None
    success: bool = False
    api_name: str = ""
    model: str = ""
    error: Optional[str] = None
    tokens_used: int = 0
    latency_ms: float = 0.0

    def __bool__(self) -> bool:
        return self.success and self.content is not None


@dataclass
class APIEndpoint:
    """Configuration for a single API endpoint."""
    name: str
    key: Optional[str]
    url: str
    default_model: str
    auth_header: str = "Authorization"
    auth_prefix: str = "Bearer"
    extra_headers: Dict[str, str] = field(default_factory=dict)
    response_parser: Optional[Callable] = None  # Custom response parser if needed

    def get_auth_header(self) -> Dict[str, str]:
        """Get authorization header for this endpoint."""
        if not self.key:
            return {}
        return {self.auth_header: f"{self.auth_prefix} {self.key}"}


class APIClient:
    """
    Unified API client for all LLM providers.

    Features:
    - Single interface for all APIs (DeepSeek, Groq, OpenRouter, etc.)
    - Automatic retries with exponential backoff
    - Per-API rate limiting
    - Circuit breaker for failing APIs
    - Round-robin load balancing across healthy APIs
    - Thread-safe operation
    - Response caching with TTL

    Example:
        client = APIClient()

        # Simple call (uses best available API)
        response = client.call("Write a poem about stars")

        # Call specific API
        response = client.call_api("deepseek", "Write a poem")

        # Call with fallback
        response = client.call_with_fallback("Write a poem", max_tokens=1000)

        # Check cache stats
        print(client.cache_stats)
    """

    def __init__(
        self,
        config: Optional[APIConfig] = None,
        cache_enabled: bool = True,
        cache_max_size: int = 1000,
        cache_ttl: float = 3600.0,
    ):
        """
        Initialize API client.

        Args:
            config: Optional APIConfig. Uses global config if not provided.
            cache_enabled: Whether to enable response caching (default: True)
            cache_max_size: Maximum cache entries (default: 1000)
            cache_ttl: Cache TTL in seconds (default: 3600 = 1 hour)
        """
        self.config = config or get_config().api
        self._lock = threading.Lock()
        self._api_index = 0

        # Initialize response cache
        global_config = get_config()
        cache_dir = global_config.paths.base_dir / "cache"
        cache_dir.mkdir(exist_ok=True)
        self._cache = ResponseCache(
            max_size=cache_max_size,
            default_ttl=cache_ttl,
            enabled=cache_enabled,
            cache_file=cache_dir / "api_response_cache.json",
        )

        # Initialize rate limiters for each API
        self._rate_limiters: Dict[str, RateLimiter] = {}
        for api_name, rpm in self.config.rate_limits.items():
            self._rate_limiters[api_name] = RateLimiter(calls_per_minute=rpm)

        # Initialize circuit breakers for each API
        pipeline_config = global_config.pipeline
        self._circuit_breakers: Dict[str, CircuitBreaker] = {}
        for api_name in self.config.rate_limits.keys():
            self._circuit_breakers[api_name] = CircuitBreaker(
                failure_threshold=pipeline_config.failure_threshold,
                recovery_timeout=pipeline_config.recovery_timeout,
            )

        # Build endpoint configurations
        self._endpoints: Dict[str, APIEndpoint] = self._build_endpoints()

        # API implementations - use generic method for OpenAI-compatible APIs
        def make_api_func(ep: APIEndpoint) -> Callable:
            """Create a wrapper function for the endpoint."""
            def api_func(prompt, max_tokens, temperature, system_prompt, model):
                return self._call_openai_compatible(ep, prompt, max_tokens, temperature, system_prompt, model)
            return api_func

        self._api_functions: Dict[str, Callable] = {
            name: make_api_func(endpoint)
            for name, endpoint in self._endpoints.items()
            if name != "cloudflare"  # Cloudflare has custom response format
        }
        # Add cloudflare with custom implementation
        if "cloudflare" in self._endpoints:
            self._api_functions["cloudflare"] = self._call_cloudflare

    @property
    def cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        return self._cache.stats

    def clear_cache(self) -> int:
        """Clear the response cache. Returns number of entries cleared."""
        return self._cache.clear()

    def save_cache(self) -> None:
        """Persist cache to disk."""
        self._cache._save_to_disk()

    def get_available_apis(self) -> List[str]:
        """Get list of APIs that are configured and not circuit-broken."""
        available = []
        configured = self.config.get_available_apis()

        for api_name in configured:
            breaker = self._circuit_breakers.get(api_name)
            if breaker and not breaker.is_open:
                available.append(api_name)

        return available

    def _build_endpoints(self) -> Dict[str, APIEndpoint]:
        """Build endpoint configurations from APIConfig."""
        endpoints = {}

        # DeepSeek
        if self.config.deepseek_key:
            endpoints["deepseek"] = APIEndpoint(
                name="deepseek",
                key=self.config.deepseek_key,
                url=self.config.deepseek_url,
                default_model=self.config.deepseek_model,
            )

        # Groq
        if self.config.groq_key:
            endpoints["groq"] = APIEndpoint(
                name="groq",
                key=self.config.groq_key,
                url=self.config.groq_url,
                default_model=self.config.groq_model,
            )

        # OpenRouter
        if self.config.openrouter_key:
            endpoints["openrouter"] = APIEndpoint(
                name="openrouter",
                key=self.config.openrouter_key,
                url=self.config.openrouter_url,
                default_model=self.config.openrouter_model,
            )

        # Together AI
        if self.config.together_key:
            endpoints["together"] = APIEndpoint(
                name="together",
                key=self.config.together_key,
                url=self.config.together_url,
                default_model=self.config.together_model,
            )

        # GitHub Models
        if self.config.github_key:
            endpoints["github"] = APIEndpoint(
                name="github",
                key=self.config.github_key,
                url=self.config.github_url,
                default_model=self.config.github_model,
            )

        # Cerebras
        if self.config.cerebras_key:
            endpoints["cerebras"] = APIEndpoint(
                name="cerebras",
                key=self.config.cerebras_key,
                url=self.config.cerebras_url,
                default_model=self.config.cerebras_model,
            )

        # Fireworks AI
        if self.config.fireworks_key:
            endpoints["fireworks"] = APIEndpoint(
                name="fireworks",
                key=self.config.fireworks_key,
                url=self.config.fireworks_url,
                default_model=self.config.fireworks_model,
            )

        # Cloudflare (special case - different URL format)
        if self.config.cloudflare_key and self.config.cloudflare_account:
            endpoints["cloudflare"] = APIEndpoint(
                name="cloudflare",
                key=self.config.cloudflare_key,
                url="",  # URL is built dynamically
                default_model="@cf/meta/llama-3-8b-instruct",
            )

        return endpoints

    def _call_openai_compatible(
        self,
        endpoint: APIEndpoint,
        prompt: str,
        max_tokens: int,
        temperature: float,
        system_prompt: Optional[str],
        model: Optional[str],
    ) -> APIResponse:
        """
        Generic method for OpenAI-compatible APIs.

        Handles DeepSeek, Groq, OpenRouter, Together, GitHub, Cerebras, Fireworks.

        Args:
            endpoint: API endpoint configuration
            prompt: The prompt to send
            max_tokens: Maximum tokens in response
            temperature: Sampling temperature
            system_prompt: Optional system message
            model: Optional model override

        Returns:
            APIResponse with content or error details
        """
        if not endpoint.key:
            return APIResponse(success=False, api_name=endpoint.name, error="No API key")

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        try:
            headers = {
                "Content-Type": "application/json",
                **endpoint.get_auth_header(),
                **endpoint.extra_headers,
            }

            response = requests.post(
                endpoint.url,
                headers=headers,
                json={
                    "model": model or endpoint.default_model,
                    "messages": messages,
                    "max_tokens": max_tokens,
                    "temperature": temperature,
                },
                timeout=self.config.default_timeout,
            )

            if response.status_code == 200:
                data = response.json()
                content = data["choices"][0]["message"]["content"]
                return APIResponse(
                    content=content,
                    success=True,
                    api_name=endpoint.name,
                    model=model or endpoint.default_model,
                    tokens_used=data.get("usage", {}).get("total_tokens", 0),
                )
            elif response.status_code == 429:
                return APIResponse(success=False, api_name=endpoint.name, error="Rate limited")
            else:
                return APIResponse(
                    success=False,
                    api_name=endpoint.name,
                    error=f"HTTP {response.status_code}: {response.text[:200]}"
                )

        except Timeout:
            return APIResponse(success=False, api_name=endpoint.name, error="Request timeout")
        except Exception as e:
            return APIResponse(success=False, api_name=endpoint.name, error=str(e))

    def call(
        self,
        prompt: str,
        max_tokens: int = 4000,
        temperature: float = 0.7,
        system_prompt: Optional[str] = None,
    ) -> APIResponse:
        """
        Call the best available API.

        Uses round-robin across healthy APIs with automatic fallback.

        Args:
            prompt: The prompt to send
            max_tokens: Maximum tokens in response
            temperature: Sampling temperature
            system_prompt: Optional system message

        Returns:
            APIResponse with content or error details
        """
        return self.call_with_fallback(
            prompt=prompt,
            max_tokens=max_tokens,
            temperature=temperature,
            system_prompt=system_prompt,
        )

    def call_api(
        self,
        api_name: str,
        prompt: str,
        max_tokens: int = 4000,
        temperature: float = 0.7,
        system_prompt: Optional[str] = None,
        model: Optional[str] = None,
        use_cache: bool = True,
    ) -> APIResponse:
        """
        Call a specific API.

        Args:
            api_name: Name of API to use (deepseek, groq, etc.)
            prompt: The prompt to send
            max_tokens: Maximum tokens in response
            temperature: Sampling temperature
            system_prompt: Optional system message
            model: Optional model override
            use_cache: Whether to use cache for this call (default: True)

        Returns:
            APIResponse with content or error details
        """
        if api_name not in self._api_functions:
            return APIResponse(
                success=False,
                api_name=api_name,
                error=f"Unknown API: {api_name}"
            )

        # Check cache first (only for deterministic calls, skip high-temperature)
        cache_key = None
        if use_cache and temperature <= 0.3:
            cache_key = self._cache.make_key(prompt, max_tokens, temperature, system_prompt)
            if cached := self._cache.get(cache_key):
                logger.debug(f"Cache hit for {api_name} call")
                return cached

        # Check circuit breaker
        breaker = self._circuit_breakers.get(api_name)
        if breaker and breaker.is_open:
            return APIResponse(
                success=False,
                api_name=api_name,
                error="Circuit breaker is open"
            )

        # Apply rate limiting
        limiter = self._rate_limiters.get(api_name)
        if limiter:
            limiter.acquire()

        # Make the call
        try:
            start_time = time.time()
            func = self._api_functions[api_name]
            response = func(
                prompt=prompt,
                max_tokens=max_tokens,
                temperature=temperature,
                system_prompt=system_prompt,
                model=model,
            )
            response.latency_ms = (time.time() - start_time) * 1000

            # Record success/failure for circuit breaker
            if breaker:
                if response.success:
                    breaker._record_success()
                else:
                    breaker._record_failure()

            # Store successful response in cache
            if cache_key and response.success:
                self._cache.set(cache_key, response)

            return response

        except Exception as e:
            if breaker:
                breaker._record_failure()

            return APIResponse(
                success=False,
                api_name=api_name,
                error=str(e)
            )

    def call_with_fallback(
        self,
        prompt: str,
        max_tokens: int = 4000,
        temperature: float = 0.7,
        system_prompt: Optional[str] = None,
        preferred_apis: Optional[List[str]] = None,
    ) -> APIResponse:
        """
        Call APIs with round-robin fallback.

        Tries each available API in order until one succeeds.

        Args:
            prompt: The prompt to send
            max_tokens: Maximum tokens in response
            temperature: Sampling temperature
            system_prompt: Optional system message
            preferred_apis: Optional list of APIs to try (in order)

        Returns:
            APIResponse from first successful API, or last error
        """
        apis = preferred_apis or self.get_available_apis()

        if not apis:
            return APIResponse(
                success=False,
                error="No APIs available (all circuit breakers open or unconfigured)"
            )

        # Round-robin starting point
        with self._lock:
            start_idx = self._api_index % len(apis)
            self._api_index += 1

        last_response = None

        for i in range(len(apis)):
            idx = (start_idx + i) % len(apis)
            api_name = apis[idx]

            response = self.call_api(
                api_name=api_name,
                prompt=prompt,
                max_tokens=max_tokens,
                temperature=temperature,
                system_prompt=system_prompt,
            )

            if response.success:
                logger.debug(f"Success via {api_name}")
                return response

            last_response = response
            logger.warning(f"{api_name} failed: {response.error}")

        logger.error("All APIs failed")
        return last_response or APIResponse(success=False, error="All APIs failed")

    # =========================================================================
    # Special API implementations (non-OpenAI compatible)
    # =========================================================================

    def _call_cloudflare(
        self,
        prompt: str,
        max_tokens: int,
        temperature: float,
        system_prompt: Optional[str],
        model: Optional[str],
    ) -> APIResponse:
        """Call Cloudflare Workers AI API."""
        if not self.config.cloudflare_key or not self.config.cloudflare_account:
            return APIResponse(success=False, api_name="cloudflare", error="No API key or account")

        model_name = model or "@cf/meta/llama-3-8b-instruct"
        url = f"https://api.cloudflare.com/client/v4/accounts/{self.config.cloudflare_account}/ai/run/{model_name}"

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        try:
            response = requests.post(
                url,
                headers={
                    "Authorization": f"Bearer {self.config.cloudflare_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "messages": messages,
                    "max_tokens": max_tokens,
                },
                timeout=self.config.default_timeout,
            )

            if response.status_code == 200:
                data = response.json()
                if data.get("success") and "result" in data:
                    content = data["result"].get("response", "")
                    return APIResponse(
                        content=content,
                        success=True,
                        api_name="cloudflare",
                        model=model_name,
                    )
                return APIResponse(
                    success=False,
                    api_name="cloudflare",
                    error=f"Unexpected response format"
                )
            elif response.status_code == 429:
                return APIResponse(success=False, api_name="cloudflare", error="Rate limited")
            else:
                return APIResponse(
                    success=False,
                    api_name="cloudflare",
                    error=f"HTTP {response.status_code}"
                )

        except Timeout:
            return APIResponse(success=False, api_name="cloudflare", error="Request timeout")
        except Exception as e:
            return APIResponse(success=False, api_name="cloudflare", error=str(e))


# Singleton instance
_client: Optional[APIClient] = None
_client_lock = threading.Lock()


def get_api_client() -> APIClient:
    """
    Get the global API client instance.

    Thread-safe singleton accessor.

    Returns:
        APIClient instance

    Example:
        from lib.api_client import get_api_client
        client = get_api_client()
        response = client.call("Write a story")
    """
    global _client

    if _client is None:
        with _client_lock:
            if _client is None:
                _client = APIClient()

    return _client


def reset_api_client() -> None:
    """Reset the global API client. Useful for testing."""
    global _client
    with _client_lock:
        _client = None


# =========================================================================
# Convenience functions for simple usage
# =========================================================================

def call_llm(
    prompt: str,
    max_tokens: int = 4000,
    temperature: float = 0.7,
    system_prompt: Optional[str] = None,
) -> Optional[str]:
    """
    Simple function to call an LLM and get response text.

    This is the easiest way to make an API call.

    Args:
        prompt: The prompt to send
        max_tokens: Maximum tokens in response
        temperature: Sampling temperature
        system_prompt: Optional system message

    Returns:
        Response text if successful, None otherwise

    Example:
        from lib.api_client import call_llm
        story = call_llm("Write a short story about a robot")
    """
    client = get_api_client()
    response = client.call(
        prompt=prompt,
        max_tokens=max_tokens,
        temperature=temperature,
        system_prompt=system_prompt,
    )
    return response.content if response.success else None


def call_llm_with_retry(
    prompt: str,
    max_tokens: int = 4000,
    max_attempts: int = 3,
    temperature: float = 0.7,
    system_prompt: Optional[str] = None,
) -> Optional[str]:
    """
    Call LLM with explicit retry on failure.

    Args:
        prompt: The prompt to send
        max_tokens: Maximum tokens in response
        max_attempts: Number of retry attempts
        temperature: Sampling temperature
        system_prompt: Optional system message

    Returns:
        Response text if successful, None otherwise
    """
    client = get_api_client()

    for attempt in range(max_attempts):
        response = client.call(
            prompt=prompt,
            max_tokens=max_tokens,
            temperature=temperature,
            system_prompt=system_prompt,
        )

        if response.success:
            return response.content

        if attempt < max_attempts - 1:
            delay = 2 ** attempt  # Exponential backoff
            logger.warning(f"Attempt {attempt + 1} failed, retrying in {delay}s...")
            time.sleep(delay)

    return None


def extract_json_from_response(response: str) -> Optional[Dict[str, Any]]:
    """
    Extract JSON from an LLM response that may contain markdown code blocks.

    Args:
        response: Raw response text from LLM

    Returns:
        Parsed JSON dict, or None if parsing fails
    """
    if not response:
        return None

    # Try to extract from code blocks
    if "```json" in response:
        try:
            json_str = response.split("```json")[1].split("```")[0].strip()
            return json.loads(json_str)
        except (IndexError, json.JSONDecodeError):
            pass

    if "```" in response:
        try:
            json_str = response.split("```")[1].split("```")[0].strip()
            return json.loads(json_str)
        except (IndexError, json.JSONDecodeError):
            pass

    # Try direct parse
    try:
        return json.loads(response)
    except json.JSONDecodeError:
        pass

    # Try to find JSON-like content
    match = re.search(r'\{[^{}]*\}', response, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass

    return None
