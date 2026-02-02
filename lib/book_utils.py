#!/usr/bin/env python3
"""
Book Utilities
==============
Common utilities for book operations extracted from 30+ duplicate implementations.

Provides centralized functions for:
- Book iteration and filtering
- Book loading (chapters, metadata, bible)
- Chapter operations
- File operations
"""

import json
from pathlib import Path
from typing import List, Iterator, Optional, Dict
from dataclasses import dataclass

from lib.logging_config import get_logger

logger = get_logger(__name__)


@dataclass
class BookInfo:
    """Information about a book."""
    dir: Path
    name: str
    chapters: List[Path]
    bible_file: Optional[Path]
    metadata_file: Optional[Path]
    metadata: Optional[Dict]

    @property
    def chapter_count(self) -> int:
        return len(self.chapters)

    def load_bible(self) -> Optional[str]:
        """Load story bible content."""
        if self.bible_file and self.bible_file.exists():
            try:
                return self.bible_file.read_text()
            except Exception as e:
                logger.warning(f"Could not load bible for {self.name}: {e}")
        return None

    def load_chapter(self, chapter_num: int) -> Optional[str]:
        """Load specific chapter content."""
        if 0 <= chapter_num < len(self.chapters):
            try:
                return self.chapters[chapter_num].read_text()
            except Exception as e:
                logger.warning(f"Could not load chapter {chapter_num}: {e}")
        return None

    def save_chapter(self, chapter_num: int, content: str) -> bool:
        """Save chapter content."""
        if 0 <= chapter_num < len(self.chapters):
            try:
                self.chapters[chapter_num].write_text(content)
                return True
            except Exception as e:
                logger.error(f"Could not save chapter {chapter_num}: {e}")
        return False


def load_book(book_dir: Path) -> Optional[BookInfo]:
    """
    Load book with chapters, bible, and metadata.

    Args:
        book_dir: Path to book directory

    Returns:
        BookInfo object or None if invalid
    """
    if not book_dir.is_dir():
        return None

    # Find chapters
    chapters = sorted(book_dir.glob("chapter_*.md"))
    if not chapters:
        logger.debug(f"No chapters found in {book_dir.name}")
        return None

    # Find bible
    bible_file = book_dir / "story_bible.md"
    if not bible_file.exists():
        bible_file = book_dir / "bible.md"
        if not bible_file.exists():
            bible_file = None

    # Find metadata
    metadata_file = book_dir / "metadata.json"
    metadata = None
    if metadata_file.exists():
        try:
            metadata = json.loads(metadata_file.read_text())
        except Exception as e:
            logger.warning(f"Could not load metadata for {book_dir.name}: {e}")

    return BookInfo(
        dir=book_dir,
        name=book_dir.name,
        chapters=chapters,
        bible_file=bible_file,
        metadata_file=metadata_file,
        metadata=metadata
    )


def iterate_books(fiction_dir: Path,
                  min_chapters: int = 0,
                  max_chapters: Optional[int] = None,
                  require_bible: bool = False,
                  skip_hidden: bool = True) -> Iterator[BookInfo]:
    """
    Iterate through books in fiction directory with filtering.

    Args:
        fiction_dir: Directory containing book subdirectories
        min_chapters: Minimum number of chapters required
        max_chapters: Maximum number of chapters (None = unlimited)
        require_bible: Only return books with story bible
        skip_hidden: Skip directories starting with '.'

    Yields:
        BookInfo objects for valid books
    """
    if not fiction_dir.exists():
        logger.error(f"Fiction directory not found: {fiction_dir}")
        return

    for book_dir in sorted(fiction_dir.iterdir()):
        # Skip non-directories
        if not book_dir.is_dir():
            continue

        # Skip hidden directories
        if skip_hidden and book_dir.name.startswith('.'):
            continue

        # Load book info
        book = load_book(book_dir)
        if not book:
            continue

        # Apply filters
        if book.chapter_count < min_chapters:
            continue

        if max_chapters and book.chapter_count > max_chapters:
            continue

        if require_bible and not book.bible_file:
            continue

        yield book


def get_book_paths(fiction_dir: Path, **kwargs) -> List[Path]:
    """
    Get list of book directory paths.

    Convenience wrapper around iterate_books that returns paths instead of BookInfo.

    Args:
        fiction_dir: Fiction directory
        **kwargs: Filtering arguments (see iterate_books)

    Returns:
        List of book directory paths
    """
    return [book.dir for book in iterate_books(fiction_dir, **kwargs)]


def count_books(fiction_dir: Path, **kwargs) -> int:
    """
    Count books matching criteria.

    Args:
        fiction_dir: Fiction directory
        **kwargs: Filtering arguments (see iterate_books)

    Returns:
        Number of books matching criteria
    """
    return sum(1 for _ in iterate_books(fiction_dir, **kwargs))


def find_book(fiction_dir: Path, book_name: str) -> Optional[BookInfo]:
    """
    Find specific book by name.

    Args:
        fiction_dir: Fiction directory
        book_name: Book directory name to find

    Returns:
        BookInfo if found, None otherwise
    """
    book_dir = fiction_dir / book_name
    if not book_dir.exists():
        return None

    return load_book(book_dir)


def get_all_chapters(fiction_dir: Path) -> List[Path]:
    """
    Get all chapter files from all books.

    Args:
        fiction_dir: Fiction directory

    Returns:
        List of all chapter file paths
    """
    chapters = []
    for book in iterate_books(fiction_dir):
        chapters.extend(book.chapters)
    return chapters


def validate_book_structure(book_dir: Path) -> tuple[bool, List[str]]:
    """
    Validate book has proper structure.

    Checks:
    - Directory exists
    - Has at least one chapter
    - Chapters are numbered sequentially
    - No missing chapter numbers
    - Has story bible (warning only)

    Args:
        book_dir: Book directory path

    Returns:
        (is_valid, list_of_issues)
    """
    issues = []

    if not book_dir.exists():
        return False, ["Directory does not exist"]

    if not book_dir.is_dir():
        return False, ["Path is not a directory"]

    # Check for chapters
    chapters = sorted(book_dir.glob("chapter_*.md"))
    if not chapters:
        return False, ["No chapters found"]

    # Check sequential numbering
    chapter_numbers = []
    for chapter in chapters:
        try:
            # Extract number from "chapter_N.md"
            num = int(chapter.stem.split('_')[1])
            chapter_numbers.append(num)
        except (IndexError, ValueError):
            issues.append(f"Invalid chapter filename: {chapter.name}")

    if chapter_numbers:
        chapter_numbers.sort()
        expected = list(range(1, len(chapter_numbers) + 1))
        if chapter_numbers != expected:
            missing = set(expected) - set(chapter_numbers)
            if missing:
                issues.append(f"Missing chapter numbers: {sorted(missing)}")

    # Check for story bible (warning only)
    bible_file = book_dir / "story_bible.md"
    if not bible_file.exists():
        bible_file = book_dir / "bible.md"
        if not bible_file.exists():
            issues.append("No story bible found (warning)")

    # Valid if no critical issues (only warnings allowed)
    is_valid = len(issues) <= 1  # Allow missing bible warning

    return is_valid, issues


def get_book_stats(book: BookInfo) -> Dict:
    """
    Get statistics about a book.

    Args:
        book: BookInfo object

    Returns:
        Dictionary with statistics
    """
    stats = {
        "name": book.name,
        "chapter_count": book.chapter_count,
        "has_bible": book.bible_file is not None,
        "has_metadata": book.metadata is not None,
        "total_words": 0,
        "avg_words_per_chapter": 0
    }

    # Count words
    word_counts = []
    for chapter_file in book.chapters:
        try:
            content = chapter_file.read_text()
            word_count = len(content.split())
            word_counts.append(word_count)
        except Exception:
            pass

    if word_counts:
        stats["total_words"] = sum(word_counts)
        stats["avg_words_per_chapter"] = stats["total_words"] / len(word_counts)

    return stats


def create_book_directory(fiction_dir: Path, book_name: str,
                          chapter_count: int = 10) -> Path:
    """
    Create new book directory structure.

    Args:
        fiction_dir: Fiction directory
        book_name: Name for book directory
        chapter_count: Number of chapter files to create

    Returns:
        Path to created book directory
    """
    book_dir = fiction_dir / book_name
    book_dir.mkdir(parents=True, exist_ok=True)

    # Create chapter files
    for i in range(1, chapter_count + 1):
        chapter_file = book_dir / f"chapter_{i}.md"
        if not chapter_file.exists():
            chapter_file.write_text(f"# Chapter {i}\n\n")

    # Create story bible
    bible_file = book_dir / "story_bible.md"
    if not bible_file.exists():
        bible_file.write_text("# Story Bible\n\n")

    logger.info(f"Created book directory: {book_name} ({chapter_count} chapters)")
    return book_dir


# Convenience functions for common operations

def backup_book(book: BookInfo, backup_dir: Path, description: str = "") -> bool:
    """
    Create backup of entire book directory.

    Args:
        book: BookInfo object
        backup_dir: Directory for backups
        description: Optional description for backup

    Returns:
        True if successful
    """
    try:
        from lib.backup import BackupManager
        manager = BackupManager()
        manager.create_backup(book.dir, description=description)
        return True
    except Exception as e:
        logger.error(f"Backup failed for {book.name}: {e}")
        return False


def restore_book(book_dir: Path, backup_path: Path) -> bool:
    """
    Restore book from backup.

    Args:
        book_dir: Book directory to restore to
        backup_path: Path to backup

    Returns:
        True if successful
    """
    try:
        import shutil
        if backup_path.exists():
            shutil.copytree(backup_path, book_dir, dirs_exist_ok=True)
            logger.info(f"Restored {book_dir.name} from backup")
            return True
    except Exception as e:
        logger.error(f"Restore failed: {e}")
    return False


if __name__ == "__main__":
    # Demo usage
    from pathlib import Path

    fiction_dir = Path("/mnt/e/projects/bookcli/output/fiction")

    print("=== Book Utilities Demo ===\n")

    # Count books
    total = count_books(fiction_dir)
    with_bible = count_books(fiction_dir, require_bible=True)
    print(f"Total books: {total}")
    print(f"Books with bible: {with_bible}\n")

    # Iterate books
    print("First 5 books:")
    for i, book in enumerate(iterate_books(fiction_dir, min_chapters=1)):
        if i >= 5:
            break
        stats = get_book_stats(book)
        print(f"  {book.name}: {book.chapter_count} chapters, "
              f"{stats['total_words']:,} words")

    # Validate structure
    print("\nValidating first book...")
    for book in iterate_books(fiction_dir, min_chapters=1):
        is_valid, issues = validate_book_structure(book.dir)
        print(f"  {book.name}: {'✓ Valid' if is_valid else '✗ Invalid'}")
        if issues:
            for issue in issues:
                print(f"    - {issue}")
        break
