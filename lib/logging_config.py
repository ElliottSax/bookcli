"""
Centralized logging configuration for BookCLI.

Provides:
- Single point of logging configuration
- Log rotation
- Consistent formatting
- Easy logger access
"""

import logging
import logging.handlers
import sys
from pathlib import Path
from typing import Optional
from datetime import datetime

# Global state to track if logging has been configured
_logging_configured = False
_log_dir: Optional[Path] = None


def setup_logging(
    log_dir: Optional[Path] = None,
    level: int = logging.INFO,
    log_to_console: bool = True,
    log_to_file: bool = True,
    max_bytes: int = 10 * 1024 * 1024,  # 10MB
    backup_count: int = 5,
    format_string: Optional[str] = None,
) -> None:
    """
    Configure logging for the entire application.

    Should be called once at application startup. Subsequent calls are ignored
    unless force=True.

    Args:
        log_dir: Directory for log files. Defaults to bookcli/logs/
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_to_console: Whether to output to stderr
        log_to_file: Whether to output to rotating file
        max_bytes: Maximum log file size before rotation
        backup_count: Number of backup files to keep
        format_string: Custom format string (optional)
    """
    global _logging_configured, _log_dir

    if _logging_configured:
        return

    # Determine log directory
    if log_dir is None:
        log_dir = Path(__file__).parent.parent / "logs"

    log_dir.mkdir(parents=True, exist_ok=True)
    _log_dir = log_dir

    # Default format
    if format_string is None:
        format_string = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"

    formatter = logging.Formatter(format_string, datefmt="%Y-%m-%d %H:%M:%S")

    # Get root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    # Remove any existing handlers
    root_logger.handlers.clear()

    # Console handler
    if log_to_console:
        console_handler = logging.StreamHandler(sys.stderr)
        console_handler.setLevel(level)
        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)

    # Rotating file handler
    if log_to_file:
        log_file = log_dir / "bookcli.log"
        file_handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding='utf-8',
        )
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)

    # Reduce noise from third-party libraries
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("requests").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)

    _logging_configured = True

    root_logger.info(f"Logging initialized. Log directory: {log_dir}")


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger with the given name.

    Ensures logging is configured before returning logger.

    Args:
        name: Logger name (typically __name__)

    Returns:
        Configured logger instance

    Example:
        from lib.logging_config import get_logger
        logger = get_logger(__name__)
        logger.info("Processing started")
    """
    # Auto-configure with defaults if not already done
    if not _logging_configured:
        setup_logging()

    return logging.getLogger(name)


def get_task_logger(task_name: str, log_dir: Optional[Path] = None) -> logging.Logger:
    """
    Get a logger that writes to a task-specific file.

    Useful for long-running tasks that need separate log files.

    Args:
        task_name: Name of the task (used for log filename)
        log_dir: Optional custom directory for the log file

    Returns:
        Logger that writes to both main log and task-specific file

    Example:
        logger = get_task_logger("book_fixer")
        logger.info("Starting book fixes...")
    """
    if not _logging_configured:
        setup_logging()

    logger = logging.getLogger(f"task.{task_name}")

    # Check if we already have a file handler for this task
    for handler in logger.handlers:
        if isinstance(handler, logging.FileHandler):
            return logger

    # Add task-specific file handler
    task_log_dir = log_dir or _log_dir or Path("logs")
    task_log_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = task_log_dir / f"{task_name}_{timestamp}.log"

    handler = logging.FileHandler(log_file, encoding='utf-8')
    handler.setFormatter(logging.Formatter(
        "%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    ))
    logger.addHandler(handler)

    return logger


class LogContext:
    """
    Context manager for temporarily changing log level or adding context.

    Example:
        with LogContext(level=logging.DEBUG):
            # Verbose logging in this block
            do_something()
    """

    def __init__(
        self,
        level: Optional[int] = None,
        extra_handler: Optional[logging.Handler] = None,
    ):
        self.level = level
        self.extra_handler = extra_handler
        self._original_level: Optional[int] = None
        self._root_logger = logging.getLogger()

    def __enter__(self) -> 'LogContext':
        if self.level is not None:
            self._original_level = self._root_logger.level
            self._root_logger.setLevel(self.level)

        if self.extra_handler is not None:
            self._root_logger.addHandler(self.extra_handler)

        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> bool:
        if self._original_level is not None:
            self._root_logger.setLevel(self._original_level)

        if self.extra_handler is not None:
            self._root_logger.removeHandler(self.extra_handler)

        return False


# Convenience functions for common log patterns
def log_section(logger: logging.Logger, title: str, char: str = "=", width: int = 60) -> None:
    """Log a section header for visual separation."""
    logger.info(char * width)
    logger.info(title.center(width))
    logger.info(char * width)


def log_progress(
    logger: logging.Logger,
    current: int,
    total: int,
    item_name: str = "items",
    prefix: str = "",
) -> None:
    """Log progress update."""
    percent = (current / total * 100) if total > 0 else 0
    logger.info(f"{prefix}[{current}/{total}] ({percent:.1f}%) {item_name}")


def log_summary(logger: logging.Logger, stats: dict, title: str = "Summary") -> None:
    """Log a summary of statistics."""
    logger.info(f"\n{title}:")
    for key, value in stats.items():
        logger.info(f"  {key}: {value}")
