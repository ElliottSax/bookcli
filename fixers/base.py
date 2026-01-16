"""
Base fixer class with common functionality.

All fixers inherit from BaseFixer which provides:
- Chapter loading and saving
- Story bible access
- Progress tracking
- Logging
"""

import json
from pathlib import Path
from typing import Dict, Optional, List, Any
from dataclasses import dataclass, field
from abc import ABC, abstractmethod

from lib.logging_config import get_logger
from lib.config import get_config

logger = get_logger(__name__)


@dataclass
class BookContext:
    """
    Context information about a book being processed.

    Provides access to chapters, story bible, and metadata.
    Uses caching to avoid repeated extraction/parsing of same data.
    """
    book_dir: Path
    chapters: Dict[int, str] = field(default_factory=dict)
    story_bible: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

    # Cached values (computed once, reused)
    _cached_character_names: Optional[List[str]] = field(default=None, repr=False)
    _cached_setting: Optional[str] = field(default=None, repr=False)
    _cached_word_counts: Optional[Dict[int, int]] = field(default=None, repr=False)
    _cached_total_words: Optional[int] = field(default=None, repr=False)

    def __post_init__(self):
        """Load chapters and story bible on initialization."""
        self._load_chapters()
        self._load_story_bible()

    def _load_chapters(self) -> None:
        """Load all chapter files into memory."""
        chapter_files = sorted(self.book_dir.glob("chapter_*.md"))

        for chapter_file in chapter_files:
            try:
                # Extract chapter number from filename
                num_str = chapter_file.stem.replace("chapter_", "")
                num = int(num_str)
                self.chapters[num] = chapter_file.read_text(encoding='utf-8')
            except (ValueError, IOError) as e:
                logger.warning(f"Could not load {chapter_file}: {e}")

    def _load_story_bible(self) -> None:
        """Load story bible if it exists."""
        bible_path = self.book_dir / "story_bible.json"
        if bible_path.exists():
            try:
                self.story_bible = json.loads(bible_path.read_text(encoding='utf-8'))
            except (json.JSONDecodeError, IOError) as e:
                logger.warning(f"Could not load story bible: {e}")

    def save_chapter(self, chapter_num: int, content: str) -> bool:
        """
        Save chapter content to file.

        Args:
            chapter_num: Chapter number
            content: New chapter content

        Returns:
            True if saved successfully
        """
        chapter_file = self.book_dir / f"chapter_{chapter_num:02d}.md"
        try:
            chapter_file.write_text(content, encoding='utf-8')
            self.chapters[chapter_num] = content
            # Invalidate word count cache since content changed
            self._cached_word_counts = None
            self._cached_total_words = None
            return True
        except IOError as e:
            logger.error(f"Could not save chapter {chapter_num}: {e}")
            return False

    def get_character_names(self) -> List[str]:
        """
        Extract character names from story bible.

        Results are cached after first extraction.
        """
        if self._cached_character_names is not None:
            return self._cached_character_names

        names = []

        # Try different story bible structures
        if 'characters' in self.story_bible:
            chars = self.story_bible['characters']
            if isinstance(chars, dict):
                names.extend(chars.keys())
            elif isinstance(chars, list):
                for char in chars:
                    if isinstance(char, dict) and 'name' in char:
                        names.append(char['name'])
                    elif isinstance(char, str):
                        names.append(char)

        if 'protagonist' in self.story_bible:
            protag = self.story_bible['protagonist']
            if isinstance(protag, dict) and 'name' in protag:
                names.append(protag['name'])
            elif isinstance(protag, str):
                names.append(protag)

        self._cached_character_names = names
        return names

    def get_setting(self) -> str:
        """
        Get primary setting from story bible.

        Results are cached after first extraction.
        """
        if self._cached_setting is not None:
            return self._cached_setting

        setting = self.story_bible.get('setting', {})

        result = "the estate"  # Default fallback

        if isinstance(setting, str):
            result = setting
        elif isinstance(setting, dict):
            for key in ['primary_location', 'name', 'location']:
                value = setting.get(key)
                if isinstance(value, str) and value:
                    result = value
                    break

        self._cached_setting = result
        return result

    def get_word_count(self, chapter_num: int) -> int:
        """
        Get word count for a specific chapter.

        Word counts are cached after first calculation.
        """
        if self._cached_word_counts is None:
            self._cached_word_counts = {}

        if chapter_num not in self._cached_word_counts:
            content = self.chapters.get(chapter_num, "")
            self._cached_word_counts[chapter_num] = len(content.split())

        return self._cached_word_counts[chapter_num]

    def get_total_words(self) -> int:
        """
        Get total word count for all chapters.

        Cached after first calculation.
        """
        if self._cached_total_words is not None:
            return self._cached_total_words

        total = sum(self.get_word_count(num) for num in self.chapters)
        self._cached_total_words = total
        return total

    def invalidate_cache(self) -> None:
        """Clear all cached values (call after major changes)."""
        self._cached_character_names = None
        self._cached_setting = None
        self._cached_word_counts = None
        self._cached_total_words = None

    @property
    def name(self) -> str:
        """Get book directory name."""
        return self.book_dir.name

    @property
    def chapter_count(self) -> int:
        """Get number of chapters."""
        return len(self.chapters)


class BaseFixer(ABC):
    """
    Abstract base class for all fixers.

    Provides common functionality:
    - Book context management
    - Progress tracking
    - Consistent interface
    """

    def __init__(self, context: BookContext):
        """
        Initialize fixer with book context.

        Args:
            context: BookContext with loaded chapters and metadata
        """
        self.context = context
        self.fixes_applied = 0
        self.logger = get_logger(f"{__name__}.{self.__class__.__name__}")

    @abstractmethod
    def fix(self) -> int:
        """
        Apply fixes to the book.

        Returns:
            Number of fixes applied
        """
        pass

    @abstractmethod
    def describe(self) -> str:
        """
        Describe what this fixer does.

        Returns:
            Human-readable description
        """
        pass

    def _save_chapter(self, chapter_num: int, content: str) -> bool:
        """Save chapter and update context."""
        return self.context.save_chapter(chapter_num, content)

    def _log_fix(self, chapter_num: int, description: str) -> None:
        """Log a fix being applied."""
        self.logger.info(f"  Chapter {chapter_num}: {description}")
        self.fixes_applied += 1


class FixerPipeline:
    """
    Pipeline to run multiple fixers in sequence.

    Example:
        context = BookContext(book_dir)
        pipeline = FixerPipeline(context)
        pipeline.add(TextFixer)
        pipeline.add(NameFixer)
        total_fixes = pipeline.run()
    """

    def __init__(self, context: BookContext):
        """
        Initialize pipeline with book context.

        Args:
            context: BookContext to pass to all fixers
        """
        self.context = context
        self.fixers: List[BaseFixer] = []
        self.logger = get_logger(__name__)

    def add(self, fixer_class: type, **kwargs) -> 'FixerPipeline':
        """
        Add a fixer to the pipeline.

        Args:
            fixer_class: Fixer class to instantiate
            **kwargs: Additional arguments for fixer constructor

        Returns:
            Self for chaining
        """
        fixer = fixer_class(self.context, **kwargs)
        self.fixers.append(fixer)
        return self

    def run(self) -> int:
        """
        Run all fixers in sequence.

        Returns:
            Total number of fixes applied
        """
        total_fixes = 0

        for fixer in self.fixers:
            self.logger.info(f"Running {fixer.__class__.__name__}: {fixer.describe()}")
            fixes = fixer.fix()
            total_fixes += fixes
            if fixes > 0:
                self.logger.info(f"  Applied {fixes} fixes")

        return total_fixes


def process_book(
    book_dir: Path,
    fixer_classes: Optional[List[type]] = None,
    text_only: bool = False,
) -> int:
    """
    Process a single book with all or specified fixers.

    Args:
        book_dir: Path to book directory
        fixer_classes: Optional list of fixer classes to run
        text_only: If True, only run text fixers (no AI calls)

    Returns:
        Total number of fixes applied
    """
    # Import here to avoid circular imports
    from .text_fixer import TextFixer
    from .name_fixer import NameFixer
    from .quality_fixer import QualityFixer

    context = BookContext(book_dir)

    if fixer_classes is None:
        if text_only:
            fixer_classes = [TextFixer]
        else:
            fixer_classes = [TextFixer, NameFixer, QualityFixer]

    pipeline = FixerPipeline(context)
    for fixer_class in fixer_classes:
        pipeline.add(fixer_class)

    return pipeline.run()


def process_all_books(
    fiction_dir: Optional[Path] = None,
    fixer_classes: Optional[List[type]] = None,
    text_only: bool = False,
    limit: Optional[int] = None,
    skip_fixed: bool = True,
    marker_file: str = ".fixes_applied",
) -> Dict[str, int]:
    """
    Process all books in the fiction directory.

    Args:
        fiction_dir: Path to fiction directory (uses config default if None)
        fixer_classes: Optional list of fixer classes to run
        text_only: If True, only run text fixers
        limit: Optional limit on number of books to process
        skip_fixed: Skip books that have marker file
        marker_file: Name of marker file indicating book was processed

    Returns:
        Dict mapping book names to fix counts
    """
    if fiction_dir is None:
        fiction_dir = get_config().paths.fiction_dir

    books = [d for d in fiction_dir.iterdir() if d.is_dir()]

    if skip_fixed:
        books = [b for b in books if not (b / marker_file).exists()]

    if limit:
        books = books[:limit]

    results = {}
    log = get_logger(__name__)

    log.info(f"Processing {len(books)} books")

    for i, book_dir in enumerate(books, 1):
        log.info(f"[{i}/{len(books)}] {book_dir.name}")

        try:
            fixes = process_book(book_dir, fixer_classes, text_only)
            results[book_dir.name] = fixes

            if fixes > 0:
                # Write marker file
                (book_dir / marker_file).write_text(str(fixes))

        except Exception as e:
            log.error(f"  Error processing {book_dir.name}: {e}")
            results[book_dir.name] = -1

    return results
