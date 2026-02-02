"""
BookCLI Core Library

Centralized utilities for the book generation pipeline.
"""

# Auto-load .env file on import
from pathlib import Path
try:
    from dotenv import load_dotenv
    # Look for .env in the bookcli root directory
    _env_path = Path(__file__).parent.parent / ".env"
    if _env_path.exists():
        load_dotenv(_env_path)
except ImportError:
    pass  # dotenv not installed, skip

from .config import Config, get_config, ConfigValidationError
from .logging_config import setup_logging, get_logger
from .retry import retry_with_backoff, RateLimiter, CircuitBreaker
from .api_client import APIClient, get_api_client
from .checkpoint import (
    CheckpointManager,
    ProcessingStage,
    BookStatus,
    get_books_by_status,
    get_failed_books,
    get_in_progress_books,
)
from .backup import BackupManager, backup_book, restore_book
from .worker_base import WorkerBase, generate, setup_worker_logging, BookCompletionWorker

__all__ = [
    # Config
    'Config',
    'get_config',
    'ConfigValidationError',
    # Logging
    'setup_logging',
    'get_logger',
    # Retry/Resilience
    'retry_with_backoff',
    'RateLimiter',
    'CircuitBreaker',
    # API
    'APIClient',
    'get_api_client',
    # Checkpoint
    'CheckpointManager',
    'ProcessingStage',
    'BookStatus',
    'get_books_by_status',
    'get_failed_books',
    'get_in_progress_books',
    # Backup
    'BackupManager',
    'backup_book',
    'restore_book',
    # Worker
    'WorkerBase',
    'generate',
    'setup_worker_logging',
    'BookCompletionWorker',
]
