"""
Unit tests for lib/retry.py
"""

import pytest
import time
from unittest.mock import Mock, patch

import sys
sys.path.insert(0, str(__file__).rsplit('/tests/', 1)[0])

from lib.retry import (
    retry_with_backoff,
    RateLimiter,
    CircuitBreaker,
    CircuitBreakerOpen,
    simple_retry,
)


class TestRetryWithBackoff:
    """Tests for the retry_with_backoff decorator."""

    def test_succeeds_on_first_try(self):
        """Function that succeeds should only be called once."""
        call_count = 0

        @retry_with_backoff(max_attempts=3)
        def succeeds():
            nonlocal call_count
            call_count += 1
            return "success"

        result = succeeds()
        assert result == "success"
        assert call_count == 1

    def test_retries_on_failure(self):
        """Function that fails should be retried."""
        call_count = 0

        @retry_with_backoff(max_attempts=3, base_delay=0.01)
        def fails_twice():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError("Not yet")
            return "success"

        result = fails_twice()
        assert result == "success"
        assert call_count == 3

    def test_raises_after_max_attempts(self):
        """Function that always fails should raise after max attempts."""
        call_count = 0

        @retry_with_backoff(max_attempts=3, base_delay=0.01)
        def always_fails():
            nonlocal call_count
            call_count += 1
            raise ValueError("Always fail")

        with pytest.raises(ValueError, match="Always fail"):
            always_fails()

        assert call_count == 3

    def test_only_retries_specified_exceptions(self):
        """Should only retry on specified exception types."""
        call_count = 0

        @retry_with_backoff(
            max_attempts=3,
            base_delay=0.01,
            retryable_exceptions=(ValueError,)
        )
        def raises_type_error():
            nonlocal call_count
            call_count += 1
            raise TypeError("Wrong type")

        with pytest.raises(TypeError):
            raises_type_error()

        assert call_count == 1  # No retries for TypeError

    def test_on_retry_callback(self):
        """on_retry callback should be called on each retry."""
        retries = []

        def on_retry(exc, attempt):
            retries.append((str(exc), attempt))

        @retry_with_backoff(
            max_attempts=3,
            base_delay=0.01,
            on_retry=on_retry
        )
        def fails_twice():
            if len(retries) < 2:
                raise ValueError("Fail")
            return "success"

        result = fails_twice()
        assert result == "success"
        assert len(retries) == 2
        assert retries[0][1] == 1
        assert retries[1][1] == 2


class TestRateLimiter:
    """Tests for the RateLimiter class."""

    def test_allows_first_call_immediately(self):
        """First call should be allowed immediately."""
        limiter = RateLimiter(calls_per_minute=60)
        start = time.time()
        limiter.acquire()
        elapsed = time.time() - start
        assert elapsed < 0.1

    def test_rate_limits_subsequent_calls(self):
        """Subsequent calls should be rate limited."""
        limiter = RateLimiter(calls_per_second=10)  # 0.1s between calls

        limiter.acquire()
        start = time.time()
        limiter.acquire()
        elapsed = time.time() - start

        assert elapsed >= 0.09  # Allow small timing variance

    def test_try_acquire_non_blocking(self):
        """try_acquire should return False when rate limited."""
        limiter = RateLimiter(calls_per_second=1)

        assert limiter.try_acquire() is True
        assert limiter.try_acquire() is False  # Should fail immediately


class TestCircuitBreaker:
    """Tests for the CircuitBreaker class."""

    def test_closed_allows_calls(self):
        """Closed circuit should allow calls."""
        breaker = CircuitBreaker(failure_threshold=3)

        @breaker
        def succeeds():
            return "success"

        assert succeeds() == "success"
        assert breaker.is_closed

    def test_opens_after_failures(self):
        """Circuit should open after failure threshold."""
        breaker = CircuitBreaker(failure_threshold=2, recovery_timeout=1.0)

        @breaker
        def fails():
            raise ValueError("Fail")

        # First failure
        with pytest.raises(ValueError):
            fails()

        # Second failure - should open circuit
        with pytest.raises(ValueError):
            fails()

        assert breaker.is_open

    def test_open_circuit_rejects_calls(self):
        """Open circuit should reject calls immediately."""
        breaker = CircuitBreaker(failure_threshold=1, recovery_timeout=10.0)

        @breaker
        def fails():
            raise ValueError("Fail")

        with pytest.raises(ValueError):
            fails()

        # Circuit is now open
        with pytest.raises(CircuitBreakerOpen):
            fails()

    def test_half_open_after_timeout(self):
        """Circuit should go half-open after recovery timeout."""
        breaker = CircuitBreaker(
            failure_threshold=1,
            recovery_timeout=0.1  # Very short for testing
        )

        @breaker
        def fails():
            raise ValueError("Fail")

        # Open the circuit
        with pytest.raises(ValueError):
            fails()

        assert breaker.is_open

        # Wait for recovery
        time.sleep(0.15)

        # Should now be half-open and allow a test call
        # (will fail and re-open)
        with pytest.raises(ValueError):
            fails()

    def test_success_closes_circuit(self):
        """Successful call should close the circuit."""
        breaker = CircuitBreaker(failure_threshold=1, recovery_timeout=0.1)
        call_count = 0

        @breaker
        def sometimes_fails():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise ValueError("Fail")
            return "success"

        # First call fails, opens circuit
        with pytest.raises(ValueError):
            sometimes_fails()

        # Wait for half-open
        time.sleep(0.15)

        # Second call succeeds, closes circuit
        result = sometimes_fails()
        assert result == "success"
        assert breaker.is_closed


class TestSimpleRetry:
    """Tests for the simple_retry helper."""

    def test_returns_on_success(self):
        """Should return result on success."""
        result = simple_retry(lambda: "success", max_attempts=3)
        assert result == "success"

    def test_retries_on_failure(self):
        """Should retry on failure."""
        calls = []

        def fails_then_succeeds():
            calls.append(1)
            if len(calls) < 2:
                raise ValueError("Fail")
            return "success"

        result = simple_retry(fails_then_succeeds, max_attempts=3, delay=0.01)
        assert result == "success"
        assert len(calls) == 2

    def test_raises_after_all_attempts(self):
        """Should raise after all attempts exhausted."""
        with pytest.raises(ValueError):
            simple_retry(
                lambda: (_ for _ in ()).throw(ValueError("Fail")),
                max_attempts=2,
                delay=0.01
            )
