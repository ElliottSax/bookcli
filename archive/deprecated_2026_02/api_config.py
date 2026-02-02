#!/usr/bin/env python3
"""
⚠️  DEPRECATION NOTICE (2026-02-01) ⚠️
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
This file has been DEPRECATED. Use instead:

    lib/config.py

The lib/config.py module provides comprehensive configuration management
including API keys, paths, and all other settings.

New Usage:
    from lib.config import get_config

    config = get_config()

    # Access API keys
    available_apis = config.api.get_available_apis()
    deepseek_key = config.api.deepseek

    # All configuration in one place
    fiction_dir = config.paths.fiction_dir

Migration Guide: See REFACTORING_COMPLETE_2026_02.md
Quick Start: See REFACTORING_QUICK_START.md
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Centralized API Configuration
==============================
Manages all API keys securely from environment variables.
NO hardcoded keys - all keys must be provided via environment.

Usage:
    from api_config import get_api_key, get_available_apis, APIKeys

    # Get a specific key (raises if not set)
    key = get_api_key("DEEPSEEK_API_KEY")

    # Get a key with fallback to None
    key = get_api_key("DEEPSEEK_API_KEY", required=False)

    # Check which APIs are available
    available = get_available_apis()

    # Access all keys via the APIKeys class
    keys = APIKeys()
    if keys.deepseek:
        # use deepseek...
"""

import os
import logging
from typing import Optional, Dict, List
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# All supported API key environment variable names
API_KEY_NAMES = {
    # LLM Providers
    "DEEPSEEK_API_KEY": "DeepSeek",
    "GROQ_API_KEY": "Groq",
    "OPENROUTER_API_KEY": "OpenRouter",
    "OPENROUTER_KEY": "OpenRouter",  # Alias
    "TOGETHER_API_KEY": "Together AI",
    "TOGETHER_KEY": "Together AI",  # Alias
    "HF_TOKEN": "HuggingFace",
    "GITHUB_TOKEN": "GitHub Models",
    "CEREBRAS_API_KEY": "Cerebras",
    "CLOUDFLARE_API_TOKEN": "Cloudflare",
    "CLOUDFLARE_ACCOUNT_ID": "Cloudflare Account",
    "FIREWORKS_API_KEY": "Fireworks",
    "MOONSHOT_API_KEY": "Moonshot",
    "ALIBABA_API_KEY": "Alibaba/DashScope",
    "SILICONFLOW_API_KEY": "SiliconFlow",

    # Image Generation
    "REPLICATE_API_TOKEN": "Replicate",
    "OPENAI_API_KEY": "OpenAI",

    # Other Services
    "ANTHROPIC_API_KEY": "Anthropic",
}


class APIKeyError(Exception):
    """Raised when a required API key is not set."""
    pass


def get_api_key(key_name: str, required: bool = True) -> Optional[str]:
    """
    Get an API key from environment variables.

    Args:
        key_name: The environment variable name (e.g., "DEEPSEEK_API_KEY")
        required: If True, raises APIKeyError when key is not set

    Returns:
        The API key value, or None if not set and not required

    Raises:
        APIKeyError: If required=True and the key is not set
    """
    value = os.environ.get(key_name, "").strip()

    if not value:
        if required:
            provider = API_KEY_NAMES.get(key_name, key_name)
            raise APIKeyError(
                f"{provider} API key not set. "
                f"Please set the {key_name} environment variable."
            )
        return None

    return value


def get_available_apis() -> Dict[str, bool]:
    """
    Check which APIs have keys configured.

    Returns:
        Dict mapping API names to availability status
    """
    available = {}

    # Check each unique provider
    providers_checked = set()
    for key_name, provider in API_KEY_NAMES.items():
        if provider in providers_checked:
            continue
        providers_checked.add(provider)

        value = os.environ.get(key_name, "").strip()
        available[provider] = bool(value)

    return available


def get_configured_api_keys() -> Dict[str, str]:
    """
    Get all configured API keys.

    Returns:
        Dict mapping key names to their values (only for keys that are set)
    """
    configured = {}
    for key_name in API_KEY_NAMES:
        value = os.environ.get(key_name, "").strip()
        if value:
            configured[key_name] = value
    return configured


def log_api_status():
    """Log the status of all API configurations."""
    available = get_available_apis()

    logger.info("API Configuration Status:")
    for provider, is_available in sorted(available.items()):
        status = "OK" if is_available else "NOT SET"
        logger.info(f"  {provider}: {status}")


@dataclass
class APIKeys:
    """
    Convenient access to all API keys.
    Keys are None if not configured in environment.

    Usage:
        keys = APIKeys()
        if keys.deepseek:
            response = call_deepseek(keys.deepseek, prompt)
    """

    def __init__(self):
        # LLM Providers
        self.deepseek: Optional[str] = get_api_key("DEEPSEEK_API_KEY", required=False)
        self.groq: Optional[str] = get_api_key("GROQ_API_KEY", required=False)
        self.openrouter: Optional[str] = (
            get_api_key("OPENROUTER_API_KEY", required=False) or
            get_api_key("OPENROUTER_KEY", required=False)
        )
        self.together: Optional[str] = (
            get_api_key("TOGETHER_API_KEY", required=False) or
            get_api_key("TOGETHER_KEY", required=False)
        )
        self.huggingface: Optional[str] = get_api_key("HF_TOKEN", required=False)
        self.github: Optional[str] = get_api_key("GITHUB_TOKEN", required=False)
        self.cerebras: Optional[str] = get_api_key("CEREBRAS_API_KEY", required=False)
        self.cloudflare_token: Optional[str] = get_api_key("CLOUDFLARE_API_TOKEN", required=False)
        self.cloudflare_account: Optional[str] = get_api_key("CLOUDFLARE_ACCOUNT_ID", required=False)
        self.fireworks: Optional[str] = get_api_key("FIREWORKS_API_KEY", required=False)
        self.moonshot: Optional[str] = get_api_key("MOONSHOT_API_KEY", required=False)
        self.alibaba: Optional[str] = get_api_key("ALIBABA_API_KEY", required=False)
        self.siliconflow: Optional[str] = get_api_key("SILICONFLOW_API_KEY", required=False)

        # Image Generation
        self.replicate: Optional[str] = get_api_key("REPLICATE_API_TOKEN", required=False)
        self.openai: Optional[str] = get_api_key("OPENAI_API_KEY", required=False)

        # Other
        self.anthropic: Optional[str] = get_api_key("ANTHROPIC_API_KEY", required=False)

    def get_available_llm_apis(self) -> List[str]:
        """Get list of available LLM API names."""
        available = []
        if self.deepseek:
            available.append("deepseek")
        if self.groq:
            available.append("groq")
        if self.openrouter:
            available.append("openrouter")
        if self.together:
            available.append("together")
        if self.huggingface:
            available.append("huggingface")
        if self.github:
            available.append("github")
        if self.cerebras:
            available.append("cerebras")
        if self.cloudflare_token and self.cloudflare_account:
            available.append("cloudflare")
        if self.fireworks:
            available.append("fireworks")
        if self.moonshot:
            available.append("moonshot")
        if self.alibaba:
            available.append("alibaba")
        if self.siliconflow:
            available.append("siliconflow")
        return available

    def has_any_llm_api(self) -> bool:
        """Check if at least one LLM API is configured."""
        return len(self.get_available_llm_apis()) > 0

    def require_at_least_one_llm(self):
        """Raise error if no LLM APIs are configured."""
        if not self.has_any_llm_api():
            raise APIKeyError(
                "No LLM API keys configured. Please set at least one of: "
                "DEEPSEEK_API_KEY, GROQ_API_KEY, OPENROUTER_API_KEY, "
                "TOGETHER_API_KEY, HF_TOKEN, GITHUB_TOKEN, etc."
            )


# Singleton instance for convenience
_api_keys: Optional[APIKeys] = None

def get_api_keys() -> APIKeys:
    """Get the singleton APIKeys instance."""
    global _api_keys
    if _api_keys is None:
        _api_keys = APIKeys()
    return _api_keys


# For backwards compatibility - these return None if not set
# Use these instead of hardcoded defaults
DEEPSEEK_API_KEY = get_api_key("DEEPSEEK_API_KEY", required=False)
GROQ_API_KEY = get_api_key("GROQ_API_KEY", required=False)
HF_TOKEN = get_api_key("HF_TOKEN", required=False)
OPENROUTER_API_KEY = get_api_key("OPENROUTER_API_KEY", required=False) or get_api_key("OPENROUTER_KEY", required=False)
TOGETHER_API_KEY = get_api_key("TOGETHER_API_KEY", required=False) or get_api_key("TOGETHER_KEY", required=False)
GITHUB_TOKEN = get_api_key("GITHUB_TOKEN", required=False)
CEREBRAS_API_KEY = get_api_key("CEREBRAS_API_KEY", required=False)
CLOUDFLARE_TOKEN = get_api_key("CLOUDFLARE_API_TOKEN", required=False)
CLOUDFLARE_ACCOUNT = get_api_key("CLOUDFLARE_ACCOUNT_ID", required=False)
FIREWORKS_API_KEY = get_api_key("FIREWORKS_API_KEY", required=False)
MOONSHOT_API_KEY = get_api_key("MOONSHOT_API_KEY", required=False)
ALIBABA_API_KEY = get_api_key("ALIBABA_API_KEY", required=False)
SILICONFLOW_API_KEY = get_api_key("SILICONFLOW_API_KEY", required=False)
REPLICATE_API_TOKEN = get_api_key("REPLICATE_API_TOKEN", required=False)


if __name__ == "__main__":
    # Test/display current configuration
    from lib.logging_config import setup_logging
    setup_logging()
    log_api_status()

    keys = APIKeys()
    print(f"\nAvailable LLM APIs: {keys.get_available_llm_apis()}")
    print(f"Has any LLM API: {keys.has_any_llm_api()}")
