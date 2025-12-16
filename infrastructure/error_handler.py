"""
Comprehensive Error Handling System for Book Factory
Provides resilient error handling, recovery, and monitoring
"""

import logging
import traceback
import json
import sqlite3
from pathlib import Path
from typing import Any, Dict, Optional, Type, Callable, List
from dataclasses import dataclass, asdict
from datetime import datetime
from enum import Enum
import functools
import time
import random
import sys

logger = logging.getLogger(__name__)


class ErrorSeverity(Enum):
    """Error severity levels."""
    LOW = "low"  # Can continue
    MEDIUM = "medium"  # Should retry
    HIGH = "high"  # Should alert
    CRITICAL = "critical"  # Should stop


class ErrorCategory(Enum):
    """Error categories."""
    API = "api"
    DATABASE = "database"
    FILE_SYSTEM = "file_system"
    NETWORK = "network"
    VALIDATION = "validation"
    GENERATION = "generation"
    PUBLISHING = "publishing"
    ANALYSIS = "analysis"
    CONFIGURATION = "configuration"
    UNKNOWN = "unknown"


@dataclass
class ErrorContext:
    """Context information for errors."""
    error_id: str
    timestamp: str
    severity: ErrorSeverity
    category: ErrorCategory
    error_type: str
    message: str
    stack_trace: str

    # Context
    module: Optional[str] = None
    function: Optional[str] = None
    book_id: Optional[str] = None
    chapter: Optional[int] = None

    # Recovery
    retry_count: int = 0
    max_retries: int = 3
    can_retry: bool = True
    recovery_action: Optional[str] = None

    # Metadata
    additional_data: Dict[str, Any] = None

    def __post_init__(self):
        if self.additional_data is None:
            self.additional_data = {}


class ErrorHandler:
    """
    Comprehensive error handling system.
    Features:
    - Automatic retry with exponential backoff
    - Error categorization and severity assessment
    - Recovery strategies
    - Error tracking and analytics
    - Alerting for critical errors
    - Graceful degradation
    """

    # Retry configuration
    DEFAULT_MAX_RETRIES = 3
    DEFAULT_BACKOFF_BASE = 2
    DEFAULT_BACKOFF_MAX = 60

    # Recovery strategies
    RECOVERY_STRATEGIES = {
        ErrorCategory.API: [
            "retry_with_backoff",
            "fallback_provider",
            "reduce_request_size",
            "cache_response"
        ],
        ErrorCategory.DATABASE: [
            "retry_transaction",
            "reconnect_database",
            "use_backup",
            "recreate_tables"
        ],
        ErrorCategory.FILE_SYSTEM: [
            "create_directory",
            "use_alternative_path",
            "clear_disk_space",
            "repair_permissions"
        ],
        ErrorCategory.NETWORK: [
            "retry_with_backoff",
            "use_proxy",
            "reduce_timeout",
            "offline_mode"
        ],
        ErrorCategory.GENERATION: [
            "retry_with_different_prompt",
            "reduce_quality_requirements",
            "use_fallback_model",
            "skip_chapter"
        ]
    }

    def __init__(self, workspace: Path, alert_threshold: ErrorSeverity = ErrorSeverity.HIGH):
        """
        Initialize error handler.

        Args:
            workspace: Path for error logs
            alert_threshold: Minimum severity for alerts
        """
        self.workspace = Path(workspace)
        self.workspace.mkdir(parents=True, exist_ok=True)

        self.alert_threshold = alert_threshold
        self.error_log = self.workspace / "errors.db"
        self._init_database()

        # Error statistics
        self.error_counts = {}
        self.success_counts = {}

        # Alert callbacks
        self.alert_callbacks = []

    def _init_database(self):
        """Initialize error tracking database."""
        conn = sqlite3.connect(self.error_log)
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS errors (
                error_id TEXT PRIMARY KEY,
                timestamp TEXT NOT NULL,
                severity TEXT NOT NULL,
                category TEXT NOT NULL,
                error_type TEXT NOT NULL,
                message TEXT NOT NULL,
                module TEXT,
                function TEXT,
                book_id TEXT,
                retry_count INTEGER DEFAULT 0,
                resolved BOOLEAN DEFAULT FALSE,
                resolution TEXT,
                data JSON,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS error_patterns (
                pattern_id TEXT PRIMARY KEY,
                pattern TEXT NOT NULL,
                frequency INTEGER DEFAULT 1,
                last_seen TIMESTAMP,
                recovery_success_rate REAL,
                recommended_action TEXT
            )
        """)

        conn.commit()
        conn.close()

    def handle_error(
        self,
        exception: Exception,
        severity: Optional[ErrorSeverity] = None,
        category: Optional[ErrorCategory] = None,
        module: Optional[str] = None,
        function: Optional[str] = None,
        book_id: Optional[str] = None,
        chapter: Optional[int] = None,
        can_retry: bool = True,
        **kwargs
    ) -> ErrorContext:
        """
        Handle an error with full context.

        Args:
            exception: The exception that occurred
            severity: Error severity (auto-detected if None)
            category: Error category (auto-detected if None)
            module: Module where error occurred
            function: Function where error occurred
            book_id: Related book ID
            chapter: Related chapter number
            can_retry: Whether error can be retried
            **kwargs: Additional context

        Returns:
            ErrorContext with full error information
        """
        # Auto-detect severity and category if not provided
        if severity is None:
            severity = self._assess_severity(exception)
        if category is None:
            category = self._categorize_error(exception)

        # Create error context
        error_context = ErrorContext(
            error_id=self._generate_error_id(),
            timestamp=datetime.now().isoformat(),
            severity=severity,
            category=category,
            error_type=type(exception).__name__,
            message=str(exception),
            stack_trace=traceback.format_exc(),
            module=module,
            function=function,
            book_id=book_id,
            chapter=chapter,
            can_retry=can_retry,
            additional_data=kwargs
        )

        # Log error
        self._log_error(error_context)

        # Track error pattern
        self._track_pattern(error_context)

        # Trigger alerts if needed
        if severity.value >= self.alert_threshold.value:
            self._trigger_alerts(error_context)

        # Suggest recovery action
        error_context.recovery_action = self._suggest_recovery(error_context)

        return error_context

    def retry_with_backoff(
        self,
        func: Callable,
        max_retries: Optional[int] = None,
        backoff_base: Optional[float] = None,
        on_retry: Optional[Callable] = None,
        **kwargs
    ) -> Any:
        """
        Retry a function with exponential backoff.

        Args:
            func: Function to retry
            max_retries: Maximum retry attempts
            backoff_base: Base for exponential backoff
            on_retry: Callback on retry
            **kwargs: Arguments for func

        Returns:
            Function result

        Raises:
            Last exception if all retries fail
        """
        max_retries = max_retries or self.DEFAULT_MAX_RETRIES
        backoff_base = backoff_base or self.DEFAULT_BACKOFF_BASE

        last_exception = None

        for attempt in range(max_retries + 1):
            try:
                return func(**kwargs)

            except Exception as e:
                last_exception = e

                if attempt < max_retries:
                    # Calculate backoff
                    backoff = min(
                        backoff_base ** attempt + random.uniform(0, 1),
                        self.DEFAULT_BACKOFF_MAX
                    )

                    if on_retry:
                        on_retry(attempt + 1, backoff, e)

                    logger.warning(
                        f"Attempt {attempt + 1}/{max_retries} failed: {e}. "
                        f"Retrying in {backoff:.1f}s..."
                    )

                    time.sleep(backoff)
                else:
                    logger.error(f"All {max_retries} retries failed: {e}")

        raise last_exception

    def with_error_handling(
        self,
        severity: ErrorSeverity = ErrorSeverity.MEDIUM,
        category: ErrorCategory = ErrorCategory.UNKNOWN,
        max_retries: int = 3,
        fallback_value: Any = None
    ):
        """
        Decorator for automatic error handling.

        Args:
            severity: Error severity
            category: Error category
            max_retries: Maximum retry attempts
            fallback_value: Value to return on failure

        Returns:
            Decorated function
        """
        def decorator(func):
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                try:
                    # Try with retries
                    return self.retry_with_backoff(
                        func,
                        max_retries=max_retries,
                        *args,
                        **kwargs
                    )
                except Exception as e:
                    # Handle error
                    error_context = self.handle_error(
                        e,
                        severity=severity,
                        category=category,
                        module=func.__module__,
                        function=func.__name__
                    )

                    # Return fallback value
                    if fallback_value is not None:
                        logger.info(f"Returning fallback value: {fallback_value}")
                        return fallback_value

                    # Re-raise if critical
                    if severity == ErrorSeverity.CRITICAL:
                        raise

                    return None

            return wrapper
        return decorator

    def create_recovery_checkpoint(
        self,
        checkpoint_id: str,
        data: Dict[str, Any]
    ) -> bool:
        """
        Create a recovery checkpoint.

        Args:
            checkpoint_id: Unique checkpoint identifier
            data: Data to checkpoint

        Returns:
            Success status
        """
        checkpoint_path = self.workspace / f"checkpoint_{checkpoint_id}.json"

        try:
            checkpoint = {
                'checkpoint_id': checkpoint_id,
                'timestamp': datetime.now().isoformat(),
                'data': data
            }

            checkpoint_path.write_text(
                json.dumps(checkpoint, indent=2),
                encoding='utf-8'
            )

            logger.info(f"Created checkpoint: {checkpoint_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to create checkpoint: {e}")
            return False

    def restore_from_checkpoint(
        self,
        checkpoint_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Restore from a checkpoint.

        Args:
            checkpoint_id: Checkpoint identifier

        Returns:
            Checkpoint data or None
        """
        checkpoint_path = self.workspace / f"checkpoint_{checkpoint_id}.json"

        if not checkpoint_path.exists():
            logger.warning(f"Checkpoint not found: {checkpoint_id}")
            return None

        try:
            checkpoint = json.loads(checkpoint_path.read_text())
            logger.info(f"Restored from checkpoint: {checkpoint_id}")
            return checkpoint['data']

        except Exception as e:
            logger.error(f"Failed to restore checkpoint: {e}")
            return None

    def register_alert_callback(self, callback: Callable):
        """
        Register a callback for error alerts.

        Args:
            callback: Function to call on alert
        """
        self.alert_callbacks.append(callback)

    def get_error_statistics(self) -> Dict[str, Any]:
        """
        Get error statistics.

        Returns:
            Error statistics
        """
        conn = sqlite3.connect(self.error_log)
        cursor = conn.cursor()

        # Total errors
        cursor.execute("SELECT COUNT(*) FROM errors")
        total_errors = cursor.fetchone()[0]

        # Errors by severity
        cursor.execute("""
            SELECT severity, COUNT(*)
            FROM errors
            GROUP BY severity
        """)
        by_severity = dict(cursor.fetchall())

        # Errors by category
        cursor.execute("""
            SELECT category, COUNT(*)
            FROM errors
            GROUP BY category
        """)
        by_category = dict(cursor.fetchall())

        # Resolution rate
        cursor.execute("""
            SELECT
                COUNT(CASE WHEN resolved = 1 THEN 1 END) as resolved,
                COUNT(*) as total
            FROM errors
        """)
        resolved, total = cursor.fetchone()
        resolution_rate = (resolved / total * 100) if total > 0 else 0

        # Common patterns
        cursor.execute("""
            SELECT pattern, frequency
            FROM error_patterns
            ORDER BY frequency DESC
            LIMIT 10
        """)
        common_patterns = cursor.fetchall()

        conn.close()

        return {
            'total_errors': total_errors,
            'by_severity': by_severity,
            'by_category': by_category,
            'resolution_rate': resolution_rate,
            'common_patterns': common_patterns
        }

    def _assess_severity(self, exception: Exception) -> ErrorSeverity:
        """Auto-assess error severity."""
        error_type = type(exception).__name__

        # Critical errors
        critical_errors = [
            'SystemExit', 'KeyboardInterrupt', 'MemoryError',
            'SystemError', 'RecursionError'
        ]
        if error_type in critical_errors:
            return ErrorSeverity.CRITICAL

        # High severity
        high_errors = [
            'DatabaseError', 'IntegrityError', 'PermissionError',
            'AuthenticationError', 'ConfigurationError'
        ]
        if error_type in high_errors:
            return ErrorSeverity.HIGH

        # Medium severity
        medium_errors = [
            'ConnectionError', 'TimeoutError', 'HTTPError',
            'ValidationError', 'FileNotFoundError'
        ]
        if error_type in medium_errors:
            return ErrorSeverity.MEDIUM

        # Low severity
        return ErrorSeverity.LOW

    def _categorize_error(self, exception: Exception) -> ErrorCategory:
        """Auto-categorize error."""
        error_type = type(exception).__name__
        error_msg = str(exception).lower()

        # API errors
        if 'api' in error_msg or 'endpoint' in error_msg or 'request' in error_msg:
            return ErrorCategory.API

        # Database errors
        if 'database' in error_msg or 'sql' in error_msg or 'table' in error_msg:
            return ErrorCategory.DATABASE

        # File system errors
        if 'file' in error_msg or 'directory' in error_msg or 'path' in error_msg:
            return ErrorCategory.FILE_SYSTEM

        # Network errors
        if 'connection' in error_msg or 'network' in error_msg or 'timeout' in error_msg:
            return ErrorCategory.NETWORK

        # Validation errors
        if 'validation' in error_msg or 'invalid' in error_msg or 'format' in error_msg:
            return ErrorCategory.VALIDATION

        # Generation errors
        if 'generation' in error_msg or 'llm' in error_msg or 'model' in error_msg:
            return ErrorCategory.GENERATION

        return ErrorCategory.UNKNOWN

    def _suggest_recovery(self, error_context: ErrorContext) -> str:
        """Suggest recovery action based on error."""
        strategies = self.RECOVERY_STRATEGIES.get(
            error_context.category,
            ["manual_intervention"]
        )

        # Pick strategy based on retry count
        if error_context.retry_count < len(strategies):
            return strategies[error_context.retry_count]

        return strategies[-1]  # Last resort

    def _log_error(self, error_context: ErrorContext):
        """Log error to database."""
        conn = sqlite3.connect(self.error_log)
        cursor = conn.cursor()

        cursor.execute("""
            INSERT OR REPLACE INTO errors
            (error_id, timestamp, severity, category, error_type,
             message, module, function, book_id, retry_count, data)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            error_context.error_id,
            error_context.timestamp,
            error_context.severity.value,
            error_context.category.value,
            error_context.error_type,
            error_context.message,
            error_context.module,
            error_context.function,
            error_context.book_id,
            error_context.retry_count,
            json.dumps(error_context.additional_data)
        ))

        conn.commit()
        conn.close()

    def _track_pattern(self, error_context: ErrorContext):
        """Track error patterns."""
        pattern = f"{error_context.category.value}:{error_context.error_type}"

        conn = sqlite3.connect(self.error_log)
        cursor = conn.cursor()

        # Check if pattern exists
        cursor.execute(
            "SELECT frequency FROM error_patterns WHERE pattern = ?",
            (pattern,)
        )
        result = cursor.fetchone()

        if result:
            # Update existing pattern
            cursor.execute("""
                UPDATE error_patterns
                SET frequency = frequency + 1,
                    last_seen = CURRENT_TIMESTAMP
                WHERE pattern = ?
            """, (pattern,))
        else:
            # Insert new pattern
            pattern_id = self._generate_error_id()
            cursor.execute("""
                INSERT INTO error_patterns
                (pattern_id, pattern, last_seen)
                VALUES (?, ?, CURRENT_TIMESTAMP)
            """, (pattern_id, pattern))

        conn.commit()
        conn.close()

    def _trigger_alerts(self, error_context: ErrorContext):
        """Trigger alerts for high severity errors."""
        alert_data = {
            'error_id': error_context.error_id,
            'severity': error_context.severity.value,
            'category': error_context.category.value,
            'message': error_context.message,
            'timestamp': error_context.timestamp
        }

        # Log critical alert
        logger.critical(f"ALERT: {error_context.severity.value} error - {error_context.message}")

        # Call registered callbacks
        for callback in self.alert_callbacks:
            try:
                callback(alert_data)
            except Exception as e:
                logger.error(f"Alert callback failed: {e}")

    def _generate_error_id(self) -> str:
        """Generate unique error ID."""
        import hashlib
        timestamp = datetime.now().isoformat()
        random_val = random.random()
        data = f"{timestamp}_{random_val}"
        return hashlib.md5(data.encode()).hexdigest()[:12]


class CircuitBreaker:
    """
    Circuit breaker pattern for fault tolerance.
    """

    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
        expected_exception: Type[Exception] = Exception
    ):
        """
        Initialize circuit breaker.

        Args:
            failure_threshold: Failures before opening circuit
            recovery_timeout: Seconds before attempting recovery
            expected_exception: Exception type to catch
        """
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception

        self.failure_count = 0
        self.last_failure_time = None
        self.state = 'closed'  # closed, open, half_open

    def call(self, func: Callable, *args, **kwargs) -> Any:
        """
        Call function with circuit breaker.

        Args:
            func: Function to call
            *args: Function arguments
            **kwargs: Function keyword arguments

        Returns:
            Function result

        Raises:
            Exception if circuit is open
        """
        if self.state == 'open':
            if self._should_attempt_reset():
                self.state = 'half_open'
            else:
                raise Exception("Circuit breaker is open")

        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result

        except self.expected_exception as e:
            self._on_failure()
            raise e

    def _should_attempt_reset(self) -> bool:
        """Check if should attempt reset."""
        return (
            self.last_failure_time and
            time.time() - self.last_failure_time >= self.recovery_timeout
        )

    def _on_success(self):
        """Handle successful call."""
        self.failure_count = 0
        self.state = 'closed'

    def _on_failure(self):
        """Handle failed call."""
        self.failure_count += 1
        self.last_failure_time = time.time()

        if self.failure_count >= self.failure_threshold:
            self.state = 'open'
            logger.warning(f"Circuit breaker opened after {self.failure_count} failures")


# Global error handler instance
_error_handler = None

def get_error_handler(workspace: Optional[Path] = None) -> ErrorHandler:
    """Get global error handler instance."""
    global _error_handler
    if _error_handler is None:
        workspace = workspace or Path("workspace/errors")
        _error_handler = ErrorHandler(workspace)
    return _error_handler