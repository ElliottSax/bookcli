"""
Retry and resilience utilities for BookCLI.

Provides:
- Exponential backoff decorator
- Rate limiter
- Circuit breaker pattern
"""

import time
import random
import functools
import threading
from typing import Callable, Optional, TypeVar, Any, Tuple, Type, List, Dict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

T = TypeVar('T')


@dataclass
class RetryConfig:
    """Configuration for retry behavior."""
    max_attempts: int = 3
    base_delay: float = 1.0
    max_delay: float = 60.0
    exponential_base: float = 2.0
    jitter: bool = True
    retryable_exceptions: Tuple[Type[Exception], ...] = (Exception,)


def retry_with_backoff(
    max_attempts: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    exponential_base: float = 2.0,
    jitter: bool = True,
    retryable_exceptions: Tuple[Type[Exception], ...] = (Exception,),
    on_retry: Optional[Callable[[Exception, int], None]] = None,
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """
    Decorator for retrying functions with exponential backoff.

    Args:
        max_attempts: Maximum number of retry attempts
        base_delay: Initial delay between retries in seconds
        max_delay: Maximum delay between retries
        exponential_base: Base for exponential backoff calculation
        jitter: Add random jitter to prevent thundering herd
        retryable_exceptions: Tuple of exception types to retry on
        on_retry: Optional callback called on each retry with (exception, attempt)

    Example:
        @retry_with_backoff(max_attempts=3, base_delay=1.0)
        def call_api():
            return requests.get(url)
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            last_exception: Optional[Exception] = None

            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except retryable_exceptions as e:
                    last_exception = e

                    if attempt == max_attempts:
                        logger.error(
                            f"{func.__name__} failed after {max_attempts} attempts: {e}"
                        )
                        raise

                    # Calculate delay with exponential backoff
                    delay = min(
                        base_delay * (exponential_base ** (attempt - 1)),
                        max_delay
                    )

                    # Add jitter (0-25% of delay)
                    if jitter:
                        delay = delay * (1 + random.uniform(0, 0.25))

                    logger.warning(
                        f"{func.__name__} attempt {attempt}/{max_attempts} failed: {e}. "
                        f"Retrying in {delay:.2f}s..."
                    )

                    if on_retry:
                        on_retry(e, attempt)

                    time.sleep(delay)

            # Should never reach here, but satisfy type checker
            if last_exception:
                raise last_exception
            raise RuntimeError("Unexpected retry loop exit")

        return wrapper
    return decorator


class RateLimiter:
    """
    Token bucket rate limiter for API calls.

    Thread-safe implementation that limits the rate of operations.

    Example:
        limiter = RateLimiter(calls_per_minute=60)

        for item in items:
            limiter.acquire()  # Blocks if rate limit exceeded
            api.call(item)
    """

    def __init__(
        self,
        calls_per_minute: int = 60,
        calls_per_second: Optional[float] = None,
    ):
        """
        Initialize rate limiter.

        Args:
            calls_per_minute: Maximum calls allowed per minute
            calls_per_second: Alternative: max calls per second (overrides per_minute)
        """
        if calls_per_second is not None:
            self.min_interval = 1.0 / calls_per_second
        else:
            self.min_interval = 60.0 / calls_per_minute

        self._last_call: float = 0.0
        self._lock = threading.Lock()

    def acquire(self) -> None:
        """
        Acquire permission to make a call. Blocks if rate limit exceeded.
        """
        with self._lock:
            now = time.time()
            elapsed = now - self._last_call

            if elapsed < self.min_interval:
                sleep_time = self.min_interval - elapsed
                time.sleep(sleep_time)

            self._last_call = time.time()

    def try_acquire(self) -> bool:
        """
        Try to acquire permission without blocking.

        Returns:
            True if acquired, False if rate limit would be exceeded
        """
        with self._lock:
            now = time.time()
            elapsed = now - self._last_call

            if elapsed >= self.min_interval:
                self._last_call = now
                return True
            return False


@dataclass
class CircuitBreakerState:
    """Internal state for circuit breaker."""
    failures: int = 0
    last_failure_time: Optional[datetime] = None
    state: str = "closed"  # closed, open, half-open


class CircuitBreaker:
    """
    Circuit breaker pattern for fault tolerance.

    Prevents cascading failures by stopping calls to failing services.

    States:
    - CLOSED: Normal operation, calls pass through
    - OPEN: Calls fail immediately without attempting
    - HALF-OPEN: Test calls to see if service recovered

    Example:
        breaker = CircuitBreaker(failure_threshold=5, recovery_timeout=30)

        @breaker
        def call_external_api():
            return requests.get(url)

        # Or use as context manager:
        with breaker:
            result = call_external_api()
    """

    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: float = 30.0,
        half_open_max_calls: int = 1,
        excluded_exceptions: Tuple[Type[Exception], ...] = (),
    ):
        """
        Initialize circuit breaker.

        Args:
            failure_threshold: Number of failures before opening circuit
            recovery_timeout: Seconds to wait before attempting recovery
            half_open_max_calls: Max calls allowed in half-open state
            excluded_exceptions: Exceptions that don't count as failures
        """
        self.failure_threshold = failure_threshold
        self.recovery_timeout = timedelta(seconds=recovery_timeout)
        self.half_open_max_calls = half_open_max_calls
        self.excluded_exceptions = excluded_exceptions

        self._state = CircuitBreakerState()
        self._lock = threading.Lock()
        self._half_open_calls = 0

    @property
    def is_open(self) -> bool:
        """Check if circuit is open (failing fast)."""
        return self._state.state == "open"

    @property
    def is_closed(self) -> bool:
        """Check if circuit is closed (normal operation)."""
        return self._state.state == "closed"

    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to attempt recovery."""
        if self._state.last_failure_time is None:
            return True
        return datetime.now() - self._state.last_failure_time >= self.recovery_timeout

    def _record_success(self) -> None:
        """Record a successful call."""
        with self._lock:
            self._state.failures = 0
            self._state.state = "closed"
            self._half_open_calls = 0

    def _record_failure(self) -> None:
        """Record a failed call."""
        with self._lock:
            self._state.failures += 1
            self._state.last_failure_time = datetime.now()

            if self._state.failures >= self.failure_threshold:
                self._state.state = "open"
                logger.warning(
                    f"Circuit breaker opened after {self._state.failures} failures"
                )

    def __call__(self, func: Callable[..., T]) -> Callable[..., T]:
        """Use as decorator."""
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            return self._execute(lambda: func(*args, **kwargs))
        return wrapper

    def __enter__(self) -> 'CircuitBreaker':
        """Use as context manager - check state on entry."""
        self._check_state()
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> bool:
        """Record result on exit."""
        if exc_type is None:
            self._record_success()
        elif exc_type not in self.excluded_exceptions:
            self._record_failure()
        return False  # Don't suppress exceptions

    def _check_state(self) -> None:
        """Check if call should be allowed, raise if circuit is open."""
        with self._lock:
            if self._state.state == "open":
                if self._should_attempt_reset():
                    self._state.state = "half-open"
                    self._half_open_calls = 0
                    logger.info("Circuit breaker entering half-open state")
                else:
                    raise CircuitBreakerOpen(
                        f"Circuit breaker is open. "
                        f"Recovery in {self.recovery_timeout.total_seconds()}s"
                    )

            if self._state.state == "half-open":
                if self._half_open_calls >= self.half_open_max_calls:
                    raise CircuitBreakerOpen("Circuit breaker half-open, max test calls reached")
                self._half_open_calls += 1

    def _execute(self, func: Callable[[], T]) -> T:
        """Execute function with circuit breaker protection."""
        self._check_state()

        try:
            result = func()
            self._record_success()
            return result
        except self.excluded_exceptions:
            raise
        except Exception as e:
            self._record_failure()
            raise


class CircuitBreakerOpen(Exception):
    """Raised when circuit breaker is open and calls are being rejected."""
    pass


class RateBasedCircuitBreaker:
    """
    Rate-based circuit breaker that opens based on failure rate.

    Unlike the count-based CircuitBreaker, this version:
    - Tracks success/failure over a sliding window
    - Opens when failure RATE exceeds threshold (e.g., 50%)
    - Requires minimum calls before evaluating rate

    This is more appropriate for APIs where occasional failures are normal
    but sustained high failure rates indicate problems.

    Example:
        breaker = RateBasedCircuitBreaker(
            failure_rate_threshold=0.5,  # 50% failure rate
            minimum_calls=10,             # Need 10 calls before evaluating
            window_size=20,               # Track last 20 calls
        )

        if breaker.allow_request():
            try:
                result = api.call()
                breaker.record_success()
            except:
                breaker.record_failure()
    """

    def __init__(
        self,
        failure_rate_threshold: float = 0.5,
        minimum_calls: int = 10,
        window_size: int = 20,
        recovery_timeout: float = 30.0,
        half_open_max_calls: int = 3,
    ):
        """
        Initialize rate-based circuit breaker.

        Args:
            failure_rate_threshold: Failure rate (0-1) that triggers open state
            minimum_calls: Minimum calls in window before evaluating rate
            window_size: Number of recent calls to track
            recovery_timeout: Seconds to wait before attempting recovery
            half_open_max_calls: Max test calls in half-open state
        """
        self.failure_rate_threshold = failure_rate_threshold
        self.minimum_calls = minimum_calls
        self.window_size = window_size
        self.recovery_timeout = timedelta(seconds=recovery_timeout)
        self.half_open_max_calls = half_open_max_calls

        # Sliding window of results (True=success, False=failure)
        self._results: List[bool] = []
        self._state = "closed"  # closed, open, half-open
        self._last_failure_time: Optional[datetime] = None
        self._half_open_calls = 0
        self._half_open_successes = 0
        self._lock = threading.Lock()

    @property
    def is_open(self) -> bool:
        """Check if circuit is open."""
        return self._state == "open"

    @property
    def is_closed(self) -> bool:
        """Check if circuit is closed."""
        return self._state == "closed"

    @property
    def failure_rate(self) -> float:
        """Calculate current failure rate."""
        if not self._results:
            return 0.0
        failures = sum(1 for r in self._results if not r)
        return failures / len(self._results)

    def allow_request(self) -> bool:
        """
        Check if a request should be allowed.

        Returns True if request can proceed, False if circuit is open.
        """
        with self._lock:
            if self._state == "closed":
                return True

            if self._state == "open":
                # Check if recovery timeout has passed
                if self._last_failure_time and \
                   datetime.now() - self._last_failure_time >= self.recovery_timeout:
                    self._state = "half-open"
                    self._half_open_calls = 0
                    self._half_open_successes = 0
                    logger.info("Rate-based circuit breaker entering half-open state")
                    return True
                return False

            if self._state == "half-open":
                if self._half_open_calls < self.half_open_max_calls:
                    self._half_open_calls += 1
                    return True
                return False

            return False

    def record_success(self) -> None:
        """Record a successful call."""
        with self._lock:
            self._add_result(True)

            if self._state == "half-open":
                self._half_open_successes += 1
                # If all half-open calls succeeded, close the circuit
                if self._half_open_successes >= self.half_open_max_calls:
                    self._state = "closed"
                    self._results.clear()  # Fresh start
                    logger.info("Rate-based circuit breaker closed after successful recovery")

    def record_failure(self) -> None:
        """Record a failed call."""
        with self._lock:
            self._add_result(False)
            self._last_failure_time = datetime.now()

            if self._state == "half-open":
                # Any failure in half-open goes back to open
                self._state = "open"
                logger.warning("Rate-based circuit breaker re-opened after half-open failure")
                return

            # Check if we should open the circuit
            if len(self._results) >= self.minimum_calls:
                rate = self.failure_rate
                if rate >= self.failure_rate_threshold:
                    self._state = "open"
                    logger.warning(
                        f"Rate-based circuit breaker opened: "
                        f"{rate:.1%} failure rate over {len(self._results)} calls"
                    )

    def _add_result(self, success: bool) -> None:
        """Add a result to the sliding window."""
        self._results.append(success)
        if len(self._results) > self.window_size:
            self._results.pop(0)

    def reset(self) -> None:
        """Reset the circuit breaker to closed state."""
        with self._lock:
            self._results.clear()
            self._state = "closed"
            self._last_failure_time = None
            self._half_open_calls = 0
            self._half_open_successes = 0

    def get_stats(self) -> Dict[str, Any]:
        """Get current circuit breaker statistics."""
        with self._lock:
            return {
                "state": self._state,
                "total_calls": len(self._results),
                "failures": sum(1 for r in self._results if not r),
                "failure_rate": f"{self.failure_rate:.1%}",
                "threshold": f"{self.failure_rate_threshold:.1%}",
            }


# Convenience function for simple retry
def simple_retry(
    func: Callable[..., T],
    max_attempts: int = 3,
    delay: float = 1.0,
) -> T:
    """
    Simple retry helper for one-off retries.

    Example:
        result = simple_retry(lambda: api.call(), max_attempts=3)
    """
    last_error: Optional[Exception] = None

    for attempt in range(max_attempts):
        try:
            return func()
        except Exception as e:
            last_error = e
            if attempt < max_attempts - 1:
                time.sleep(delay * (attempt + 1))

    if last_error:
        raise last_error
    raise RuntimeError("Retry failed unexpectedly")
