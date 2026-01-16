"""
Backup and restore system for BookCLI.

Provides:
- Chapter backup before modifications
- Restore from backups
- Backup management (cleanup old backups)
"""

import shutil
import time
from pathlib import Path
from typing import Optional, List, Dict, Any
from dataclasses import dataclass

from .logging_config import get_logger

logger = get_logger(__name__)


@dataclass
class BackupInfo:
    """Information about a backup file."""
    chapter_num: int
    timestamp: float
    backup_path: Path
    original_path: Path

    @property
    def age_hours(self) -> float:
        """Get backup age in hours."""
        return (time.time() - self.timestamp) / 3600

    @property
    def formatted_time(self) -> str:
        """Get human-readable timestamp."""
        import datetime
        dt = datetime.datetime.fromtimestamp(self.timestamp)
        return dt.strftime("%Y-%m-%d %H:%M:%S")


class BackupManager:
    """
    Manages backups for book chapters.

    Example:
        manager = BackupManager(book_dir)

        # Backup before editing
        backup_path = manager.backup_chapter(5)

        # ... make changes ...

        # If something goes wrong, restore
        manager.restore_chapter(5)

        # Or restore specific backup
        manager.restore_chapter(5, timestamp="20240115_143022")
    """

    BACKUP_DIR = ".backups"
    BACKUP_PREFIX = "chapter_"
    BACKUP_SUFFIX = ".backup"

    def __init__(self, book_dir: Path, max_backups_per_chapter: int = 5):
        """
        Initialize backup manager.

        Args:
            book_dir: Path to book directory
            max_backups_per_chapter: Maximum backups to keep per chapter
        """
        self.book_dir = Path(book_dir)
        self.backup_dir = self.book_dir / self.BACKUP_DIR
        self.max_backups = max_backups_per_chapter

    def _ensure_backup_dir(self) -> Path:
        """Ensure backup directory exists."""
        self.backup_dir.mkdir(exist_ok=True)
        return self.backup_dir

    def _get_chapter_path(self, chapter_num: int) -> Path:
        """Get path to chapter file."""
        return self.book_dir / f"chapter_{chapter_num:02d}.md"

    def _generate_backup_name(self, chapter_num: int) -> str:
        """Generate backup filename with timestamp."""
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        return f"{self.BACKUP_PREFIX}{chapter_num:02d}_{timestamp}{self.BACKUP_SUFFIX}.md"

    def _parse_backup_name(self, filename: str) -> Optional[Dict[str, Any]]:
        """Parse backup filename to extract chapter number and timestamp."""
        import re

        pattern = rf"{self.BACKUP_PREFIX}(\d+)_(\d{{8}}_\d{{6}}){self.BACKUP_SUFFIX}\.md"
        match = re.match(pattern, filename)

        if not match:
            return None

        chapter_num = int(match.group(1))
        timestamp_str = match.group(2)

        # Parse timestamp
        try:
            import datetime
            dt = datetime.datetime.strptime(timestamp_str, "%Y%m%d_%H%M%S")
            timestamp = dt.timestamp()
        except ValueError:
            return None

        return {
            'chapter_num': chapter_num,
            'timestamp': timestamp,
            'timestamp_str': timestamp_str,
        }

    def backup_chapter(self, chapter_num: int) -> Optional[Path]:
        """
        Create a backup of a chapter.

        Args:
            chapter_num: Chapter number to backup

        Returns:
            Path to backup file, or None if chapter doesn't exist
        """
        chapter_path = self._get_chapter_path(chapter_num)

        if not chapter_path.exists():
            logger.warning(f"Cannot backup chapter {chapter_num}: file not found")
            return None

        self._ensure_backup_dir()

        backup_name = self._generate_backup_name(chapter_num)
        backup_path = self.backup_dir / backup_name

        shutil.copy2(chapter_path, backup_path)
        logger.debug(f"Backed up chapter {chapter_num} to {backup_path.name}")

        # Cleanup old backups
        self._cleanup_old_backups(chapter_num)

        return backup_path

    def backup_all_chapters(self) -> List[Path]:
        """
        Backup all chapters in the book.

        Returns:
            List of backup paths created
        """
        backups = []

        for chapter_file in sorted(self.book_dir.glob("chapter_*.md")):
            try:
                num_str = chapter_file.stem.replace("chapter_", "")
                chapter_num = int(num_str)
                backup_path = self.backup_chapter(chapter_num)
                if backup_path:
                    backups.append(backup_path)
            except ValueError:
                continue

        logger.info(f"Backed up {len(backups)} chapters")
        return backups

    def restore_chapter(
        self,
        chapter_num: int,
        timestamp: Optional[str] = None,
    ) -> bool:
        """
        Restore a chapter from backup.

        Args:
            chapter_num: Chapter number to restore
            timestamp: Specific timestamp to restore (default: most recent)

        Returns:
            True if restored successfully
        """
        backups = self.get_backups(chapter_num)

        if not backups:
            logger.warning(f"No backups found for chapter {chapter_num}")
            return False

        # Find the backup to restore
        if timestamp:
            backup = next(
                (b for b in backups if str(b.timestamp).startswith(timestamp)),
                None
            )
            if not backup:
                logger.warning(f"No backup found for timestamp {timestamp}")
                return False
        else:
            # Use most recent backup
            backup = backups[0]

        chapter_path = self._get_chapter_path(chapter_num)
        shutil.copy2(backup.backup_path, chapter_path)

        logger.info(f"Restored chapter {chapter_num} from backup ({backup.formatted_time})")
        return True

    def get_backups(self, chapter_num: Optional[int] = None) -> List[BackupInfo]:
        """
        Get list of backups.

        Args:
            chapter_num: Filter to specific chapter (default: all)

        Returns:
            List of BackupInfo objects, sorted by timestamp (newest first)
        """
        if not self.backup_dir.exists():
            return []

        backups = []

        for backup_file in self.backup_dir.glob(f"{self.BACKUP_PREFIX}*{self.BACKUP_SUFFIX}.md"):
            parsed = self._parse_backup_name(backup_file.name)
            if not parsed:
                continue

            if chapter_num is not None and parsed['chapter_num'] != chapter_num:
                continue

            backups.append(BackupInfo(
                chapter_num=parsed['chapter_num'],
                timestamp=parsed['timestamp'],
                backup_path=backup_file,
                original_path=self._get_chapter_path(parsed['chapter_num']),
            ))

        # Sort by timestamp (newest first)
        backups.sort(key=lambda b: b.timestamp, reverse=True)
        return backups

    def _cleanup_old_backups(self, chapter_num: int) -> int:
        """
        Remove old backups exceeding max_backups limit.

        Args:
            chapter_num: Chapter to cleanup backups for

        Returns:
            Number of backups removed
        """
        backups = self.get_backups(chapter_num)

        if len(backups) <= self.max_backups:
            return 0

        # Remove oldest backups
        removed = 0
        for backup in backups[self.max_backups:]:
            try:
                backup.backup_path.unlink()
                removed += 1
                logger.debug(f"Removed old backup: {backup.backup_path.name}")
            except OSError as e:
                logger.warning(f"Could not remove backup {backup.backup_path}: {e}")

        return removed

    def cleanup_all_old_backups(self) -> int:
        """
        Cleanup old backups for all chapters.

        Returns:
            Total number of backups removed
        """
        removed = 0

        # Get all unique chapter numbers with backups
        all_backups = self.get_backups()
        chapter_nums = set(b.chapter_num for b in all_backups)

        for chapter_num in chapter_nums:
            removed += self._cleanup_old_backups(chapter_num)

        if removed:
            logger.info(f"Cleaned up {removed} old backups")
        return removed

    def get_backup_stats(self) -> Dict[str, Any]:
        """
        Get statistics about backups.

        Returns:
            Dict with backup statistics
        """
        backups = self.get_backups()

        if not backups:
            return {
                'total_backups': 0,
                'chapters_with_backups': 0,
                'total_size_bytes': 0,
                'oldest_backup': None,
                'newest_backup': None,
            }

        chapter_nums = set(b.chapter_num for b in backups)
        total_size = sum(b.backup_path.stat().st_size for b in backups)

        return {
            'total_backups': len(backups),
            'chapters_with_backups': len(chapter_nums),
            'total_size_bytes': total_size,
            'total_size_mb': round(total_size / (1024 * 1024), 2),
            'oldest_backup': backups[-1].formatted_time if backups else None,
            'newest_backup': backups[0].formatted_time if backups else None,
        }

    def delete_all_backups(self) -> int:
        """
        Delete all backups for this book.

        Returns:
            Number of backups deleted
        """
        if not self.backup_dir.exists():
            return 0

        backups = self.get_backups()
        deleted = 0

        for backup in backups:
            try:
                backup.backup_path.unlink()
                deleted += 1
            except OSError:
                pass

        # Try to remove backup directory if empty
        try:
            self.backup_dir.rmdir()
        except OSError:
            pass

        logger.info(f"Deleted {deleted} backups")
        return deleted


def backup_book(book_dir: Path) -> List[Path]:
    """
    Convenience function to backup all chapters in a book.

    Args:
        book_dir: Path to book directory

    Returns:
        List of backup paths created
    """
    manager = BackupManager(book_dir)
    return manager.backup_all_chapters()


def restore_book(book_dir: Path, timestamp: Optional[str] = None) -> int:
    """
    Convenience function to restore all chapters from backup.

    Args:
        book_dir: Path to book directory
        timestamp: Specific timestamp to restore (default: most recent)

    Returns:
        Number of chapters restored
    """
    manager = BackupManager(book_dir)
    backups = manager.get_backups()

    # Get unique chapter numbers
    chapter_nums = sorted(set(b.chapter_num for b in backups))

    restored = 0
    for chapter_num in chapter_nums:
        if manager.restore_chapter(chapter_num, timestamp):
            restored += 1

    return restored
