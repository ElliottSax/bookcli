"""
Checkpoint system for BookCLI pipeline recovery.

Provides:
- Save progress at key milestones
- Resume interrupted processing
- Track book processing status
"""

import json
import time
from pathlib import Path
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field, asdict
from enum import Enum

from .logging_config import get_logger

logger = get_logger(__name__)


class ProcessingStage(str, Enum):
    """Stages of book processing."""
    CONCEPT = "concept"
    OUTLINE = "outline"
    GENERATION = "generation"
    EDITING = "editing"
    QUALITY_CHECKS = "quality_checks"
    FINALIZATION = "finalization"
    COMPLETED = "completed"
    FAILED = "failed"


class BookStatus(str, Enum):
    """Overall book status."""
    DRAFT = "draft"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    NEEDS_REVIEW = "needs_review"


@dataclass
class Checkpoint:
    """Represents a processing checkpoint."""
    book_id: str
    stage: ProcessingStage
    timestamp: float = field(default_factory=time.time)
    chapter_progress: int = 0  # Current chapter being processed
    total_chapters: int = 0
    status: BookStatus = BookStatus.IN_PROGRESS
    metadata: Dict[str, Any] = field(default_factory=dict)
    error_message: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        data = asdict(self)
        data['stage'] = self.stage.value
        data['status'] = self.status.value
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Checkpoint':
        """Create from dictionary."""
        data['stage'] = ProcessingStage(data['stage'])
        data['status'] = BookStatus(data['status'])
        return cls(**data)


class CheckpointManager:
    """
    Manages checkpoints for book processing pipelines.

    Example:
        manager = CheckpointManager(book_dir)

        # Save progress
        manager.save(ProcessingStage.GENERATION, chapter=5, total=12)

        # Check if should skip stages
        if manager.is_stage_completed(ProcessingStage.EDITING):
            print("Skipping editing - already done")

        # Resume from checkpoint
        checkpoint = manager.load()
        if checkpoint:
            start_chapter = checkpoint.chapter_progress
    """

    CHECKPOINT_FILE = ".checkpoint.json"

    def __init__(self, book_dir: Path):
        """
        Initialize checkpoint manager.

        Args:
            book_dir: Path to book directory
        """
        self.book_dir = Path(book_dir)
        self.checkpoint_file = self.book_dir / self.CHECKPOINT_FILE
        self.book_id = self.book_dir.name

    def save(
        self,
        stage: ProcessingStage,
        chapter: int = 0,
        total: int = 0,
        status: BookStatus = BookStatus.IN_PROGRESS,
        metadata: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None,
    ) -> Checkpoint:
        """
        Save a checkpoint.

        Args:
            stage: Current processing stage
            chapter: Current chapter number
            total: Total chapters
            status: Book status
            metadata: Additional metadata to save
            error: Error message if failed

        Returns:
            The saved checkpoint
        """
        checkpoint = Checkpoint(
            book_id=self.book_id,
            stage=stage,
            chapter_progress=chapter,
            total_chapters=total,
            status=status,
            metadata=metadata or {},
            error_message=error,
        )

        self.checkpoint_file.write_text(
            json.dumps(checkpoint.to_dict(), indent=2),
            encoding='utf-8'
        )

        logger.debug(f"Saved checkpoint: {stage.value} chapter {chapter}/{total}")
        return checkpoint

    def load(self) -> Optional[Checkpoint]:
        """
        Load the most recent checkpoint.

        Returns:
            Checkpoint if exists, None otherwise
        """
        if not self.checkpoint_file.exists():
            return None

        try:
            data = json.loads(self.checkpoint_file.read_text(encoding='utf-8'))
            return Checkpoint.from_dict(data)
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            logger.warning(f"Could not load checkpoint: {e}")
            return None

    def clear(self) -> None:
        """Remove checkpoint file."""
        if self.checkpoint_file.exists():
            self.checkpoint_file.unlink()
            logger.debug("Cleared checkpoint")

    def is_stage_completed(self, stage: ProcessingStage) -> bool:
        """
        Check if a stage has been completed.

        Args:
            stage: Stage to check

        Returns:
            True if stage was completed in a previous run
        """
        checkpoint = self.load()
        if not checkpoint:
            return False

        # Define stage order
        stage_order = list(ProcessingStage)
        try:
            current_idx = stage_order.index(checkpoint.stage)
            check_idx = stage_order.index(stage)
            return check_idx < current_idx
        except ValueError:
            return False

    def get_resume_point(self) -> Optional[Dict[str, Any]]:
        """
        Get information needed to resume processing.

        Returns:
            Dict with stage and chapter to resume from, or None
        """
        checkpoint = self.load()
        if not checkpoint:
            return None

        if checkpoint.status == BookStatus.COMPLETED:
            return None  # No need to resume

        return {
            'stage': checkpoint.stage,
            'chapter': checkpoint.chapter_progress,
            'total_chapters': checkpoint.total_chapters,
            'metadata': checkpoint.metadata,
        }

    def mark_completed(self, metadata: Optional[Dict[str, Any]] = None) -> Checkpoint:
        """Mark book processing as completed."""
        return self.save(
            stage=ProcessingStage.COMPLETED,
            status=BookStatus.COMPLETED,
            metadata=metadata,
        )

    def mark_failed(self, error: str, metadata: Optional[Dict[str, Any]] = None) -> Checkpoint:
        """Mark book processing as failed."""
        checkpoint = self.load()
        return self.save(
            stage=checkpoint.stage if checkpoint else ProcessingStage.FAILED,
            chapter=checkpoint.chapter_progress if checkpoint else 0,
            total=checkpoint.total_chapters if checkpoint else 0,
            status=BookStatus.FAILED,
            metadata=metadata,
            error=error,
        )


def get_books_by_status(
    fiction_dir: Path,
    status: BookStatus,
) -> List[Path]:
    """
    Find all books with a specific status.

    Args:
        fiction_dir: Directory containing book directories
        status: Status to filter by

    Returns:
        List of book directory paths
    """
    results = []

    for book_dir in fiction_dir.iterdir():
        if not book_dir.is_dir():
            continue

        manager = CheckpointManager(book_dir)
        checkpoint = manager.load()

        if checkpoint and checkpoint.status == status:
            results.append(book_dir)
        elif not checkpoint and status == BookStatus.DRAFT:
            # No checkpoint means draft/unprocessed
            results.append(book_dir)

    return results


def get_failed_books(fiction_dir: Path) -> List[Dict[str, Any]]:
    """
    Get all failed books with their error information.

    Args:
        fiction_dir: Directory containing book directories

    Returns:
        List of dicts with book info and error details
    """
    failed = []

    for book_dir in fiction_dir.iterdir():
        if not book_dir.is_dir():
            continue

        manager = CheckpointManager(book_dir)
        checkpoint = manager.load()

        if checkpoint and checkpoint.status == BookStatus.FAILED:
            failed.append({
                'book_id': checkpoint.book_id,
                'path': book_dir,
                'stage': checkpoint.stage.value,
                'chapter': checkpoint.chapter_progress,
                'error': checkpoint.error_message,
                'timestamp': checkpoint.timestamp,
            })

    return failed


def get_in_progress_books(fiction_dir: Path) -> List[Dict[str, Any]]:
    """
    Get all books currently in progress.

    Args:
        fiction_dir: Directory containing book directories

    Returns:
        List of dicts with book progress info
    """
    in_progress = []

    for book_dir in fiction_dir.iterdir():
        if not book_dir.is_dir():
            continue

        manager = CheckpointManager(book_dir)
        checkpoint = manager.load()

        if checkpoint and checkpoint.status == BookStatus.IN_PROGRESS:
            in_progress.append({
                'book_id': checkpoint.book_id,
                'path': book_dir,
                'stage': checkpoint.stage.value,
                'chapter': checkpoint.chapter_progress,
                'total_chapters': checkpoint.total_chapters,
                'timestamp': checkpoint.timestamp,
            })

    return in_progress
