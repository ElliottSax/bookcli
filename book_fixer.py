#!/usr/bin/env python3
"""
Book Fixer - Automatic Quality Improvement Pipeline
====================================================

Fixes:
1. Character name inconsistencies
2. Setting/location name inconsistencies
3. Plot holes and continuity errors
4. POV/tense inconsistencies
5. Low-quality or short chapters
6. Doubled names, placeholders, LLM artifacts

Uses the modular fixers/ module for core fixing functionality.
"""

import json
import re
import time
import argparse
from pathlib import Path
from typing import Optional, Dict, List
from dataclasses import dataclass

# Centralized lib modules
from lib.logging_config import setup_logging, get_logger
from lib.config import get_config
from lib.api_client import call_llm, extract_json_from_response
from lib.backup import BackupManager
from lib.checkpoint import CheckpointManager, ProcessingStage, BookStatus

# Use fixers module
from fixers import BookContext, TextFixer, NameFixer, QualityFixer, FixerPipeline

# Initialize
setup_logging()
logger = get_logger(__name__)
config = get_config()

# Paths from config
FICTION_DIR = config.paths.fiction_dir


@dataclass
class BookIssue:
    """Represents an issue found in a book."""
    issue_type: str  # name_inconsistency, pov_shift, short_chapter, etc.
    description: str
    affected_chapters: List[int]
    fix_applied: bool = False


class BookFixer:
    """
    Fixes quality issues in a book using the modular fixers pipeline.

    This class provides a higher-level interface over the fixers module,
    adding:
    - Checkpoint/recovery support
    - Backup before modifications
    - Setting inconsistency fixes (AI-based)
    - Integration with story bible
    """

    def __init__(self, book_dir: Path, create_backup: bool = True):
        """
        Initialize book fixer.

        Args:
            book_dir: Path to book directory
            create_backup: Whether to backup chapters before modifying
        """
        self.book_dir = book_dir
        self.context = BookContext(book_dir)
        self.issues: List[BookIssue] = []
        self.fixes_applied = 0

        # Create backup before any modifications
        if create_backup and self.context.chapters:
            self._backup_manager = BackupManager(book_dir)
            self._backup_manager.backup_all_chapters()
        else:
            self._backup_manager = None

        # Checkpoint manager for recovery
        self._checkpoint = CheckpointManager(book_dir)

    @property
    def story_bible(self) -> Dict:
        """Access story bible from context."""
        return self.context.story_bible

    @property
    def chapters(self) -> Dict[int, str]:
        """Access chapters from context."""
        return self.context.chapters

    # =========================================================================
    # TEXT FIXES (using fixers module)
    # =========================================================================

    def run_text_fixes(self) -> int:
        """
        Run all text-based fixes (no AI calls).

        Returns:
            Number of fixes applied
        """
        text_fixer = TextFixer(self.context)
        fixes = text_fixer.fix()
        self.fixes_applied += fixes
        return fixes

    # =========================================================================
    # NAME FIXES (using fixers module)
    # =========================================================================

    def run_name_fixes(self, use_ai: bool = True) -> int:
        """
        Run name consistency fixes.

        Args:
            use_ai: Whether to use AI for complex cases

        Returns:
            Number of fixes applied
        """
        name_fixer = NameFixer(self.context, use_ai=use_ai)
        fixes = name_fixer.fix()
        self.fixes_applied += fixes
        return fixes

    # =========================================================================
    # QUALITY FIXES (using fixers module)
    # =========================================================================

    def run_quality_fixes(self, expand_short: bool = True, fix_pov: bool = True) -> int:
        """
        Run quality fixes (POV consistency, chapter expansion).

        Args:
            expand_short: Whether to expand short chapters
            fix_pov: Whether to fix POV inconsistencies

        Returns:
            Number of fixes applied
        """
        quality_fixer = QualityFixer(
            self.context,
            expand_short=expand_short,
            fix_pov=fix_pov,
        )
        fixes = quality_fixer.fix()
        self.fixes_applied += fixes
        return fixes

    # =========================================================================
    # SETTING FIXES (unique to book_fixer, not in fixers module)
    # =========================================================================

    def fix_setting_inconsistencies(self) -> int:
        """
        Fix setting/location name inconsistencies using AI.

        This analyzes the text to find location names that are used
        inconsistently and normalizes them.

        Returns:
            Number of fixes applied
        """
        if not self.story_bible:
            return 0

        all_text = self._get_all_text()[:10000]

        prompt = f"""Analyze this book text and find setting/location name inconsistencies.

BOOK TEXT:
{all_text}

STORY BIBLE SETTING:
{json.dumps(self.story_bible.get('setting', {}), indent=2)}

Find locations mentioned inconsistently and return a JSON object mapping variant names to canonical names:
{{"variant1": "canonical1", "variant2": "canonical1"}}

Return ONLY the JSON object."""

        result = call_llm(prompt, max_tokens=1000)
        if not result:
            return 0

        mappings = extract_json_from_response(result)
        if not mappings or not isinstance(mappings, dict):
            return 0

        fixes = 0
        for variant, canonical in mappings.items():
            if isinstance(variant, str) and isinstance(canonical, str) and variant != canonical:
                for num, content in self.chapters.items():
                    original = content
                    pattern = r'\b' + re.escape(variant) + r'\b'
                    content = re.sub(pattern, canonical, content)

                    if content != original:
                        self.context.save_chapter(num, content)
                        fixes += 1

        self.fixes_applied += fixes
        return fixes

    def _get_all_text(self) -> str:
        """Get all chapter text combined."""
        return "\n\n".join(self.chapters.values())

    # =========================================================================
    # ANALYSIS
    # =========================================================================

    def analyze(self) -> Dict:
        """
        Analyze the book for issues.

        Returns:
            Dict with analysis results
        """
        # Use quality fixer for analysis
        quality_fixer = QualityFixer(self.context)
        quality_analysis = quality_fixer.analyze_quality()

        # Use text fixer for text issue stats
        text_fixer = TextFixer(self.context)
        text_stats = text_fixer.get_stats()

        # Use name fixer for name frequency
        name_fixer = NameFixer(self.context, use_ai=False)
        name_freq = name_fixer.get_name_frequency()

        return {
            "book": self.book_dir.name,
            "chapters": quality_analysis['total_chapters'],
            "total_words": quality_analysis['total_words'],
            "avg_words_per_chapter": quality_analysis['avg_words_per_chapter'],
            "short_chapters": quality_analysis['short_chapters'],
            "pov_distribution": quality_analysis['pov_distribution'],
            "has_pov_issues": quality_analysis['has_pov_inconsistency'],
            "text_issues": text_stats,
            "top_names": dict(sorted(name_freq.items(), key=lambda x: -x[1])[:10]),
        }

    # =========================================================================
    # MAIN FIX PIPELINE
    # =========================================================================

    def run_full_fix(self, text_only: bool = False) -> Dict:
        """
        Run all fixes in order.

        Args:
            text_only: If True, only run text fixes (no AI calls)

        Returns:
            Dict with fix results
        """
        results = {
            "book": self.book_dir.name,
            "issues_found": 0,
            "fixes_applied": 0,
            "details": []
        }

        # Save checkpoint at start
        self._checkpoint.save(
            ProcessingStage.EDITING,
            chapter=0,
            total=len(self.chapters),
            status=BookStatus.IN_PROGRESS,
        )

        try:
            # 1. Text fixes first (no AI calls)
            text_fixes = self.run_text_fixes()
            if text_fixes:
                results["details"].append(f"Applied {text_fixes} text fixes (doubled names, placeholders, artifacts)")
                results["fixes_applied"] += text_fixes

            if text_only:
                return results

            # 2. Name consistency fixes
            name_fixes = self.run_name_fixes(use_ai=True)
            if name_fixes:
                results["details"].append(f"Fixed name inconsistencies in {name_fixes} chapters")
                results["fixes_applied"] += name_fixes

            # 3. Quality fixes (POV, chapter expansion)
            quality_fixes = self.run_quality_fixes(expand_short=True, fix_pov=True)
            if quality_fixes:
                results["details"].append(f"Applied {quality_fixes} quality fixes")
                results["fixes_applied"] += quality_fixes

            # 4. Setting inconsistencies
            setting_fixes = self.fix_setting_inconsistencies()
            if setting_fixes:
                results["details"].append(f"Fixed setting inconsistencies in {setting_fixes} chapters")
                results["fixes_applied"] += setting_fixes

            # Mark as fixed in story bible
            if self.story_bible and results["fixes_applied"] > 0:
                self.story_bible["quality_fixed"] = True
                self.story_bible["fixes_applied"] = results["fixes_applied"]
                bible_path = self.book_dir / "story_bible.json"
                bible_path.write_text(json.dumps(self.story_bible, indent=2))

            # Save successful checkpoint
            self._checkpoint.mark_completed(metadata={"fixes": results["fixes_applied"]})

        except Exception as e:
            # Save failure checkpoint
            self._checkpoint.mark_failed(str(e))
            raise

        results["fixes_applied"] = self.fixes_applied
        return results


def get_books_needing_fixes() -> List[Path]:
    """Get all books that haven't been fixed yet."""
    books = []

    for book_dir in FICTION_DIR.iterdir():
        if not book_dir.is_dir():
            continue

        story_bible_path = book_dir / "story_bible.json"
        if not story_bible_path.exists():
            continue

        try:
            bible = json.loads(story_bible_path.read_text())
            if bible.get("quality_fixed"):
                continue
        except json.JSONDecodeError:
            continue

        chapters = list(book_dir.glob("chapter_*.md"))
        if len(chapters) >= 3:
            books.append(book_dir)

    return books


def get_all_books() -> List[Path]:
    """Get all books with chapters (regardless of fix status)."""
    books = []

    for book_dir in FICTION_DIR.iterdir():
        if not book_dir.is_dir():
            continue

        chapters = list(book_dir.glob("chapter_*.md"))
        if len(chapters) >= 3:
            books.append(book_dir)

    return books


def main():
    """Main fix loop."""
    parser = argparse.ArgumentParser(description="Book Fixer - Automatic Quality Improvement")
    parser.add_argument("--rerun", action="store_true",
                       help="Re-run fixes on all books, including already-fixed ones")
    parser.add_argument("--book", type=str,
                       help="Fix a specific book by name")
    parser.add_argument("--limit", type=int, default=None,
                       help="Limit number of books to process")
    parser.add_argument("--text-only", action="store_true",
                       help="Only run text fixes (doubled names, placeholders, etc.) - no AI calls")
    parser.add_argument("--no-backup", action="store_true",
                       help="Skip creating backups before fixing")
    parser.add_argument("--analyze", action="store_true",
                       help="Only analyze books, don't apply fixes")
    args = parser.parse_args()

    logger.info("=" * 60)
    logger.info("BOOK FIXER - Automatic Quality Improvement")
    logger.info("=" * 60)

    if args.book:
        book_path = FICTION_DIR / args.book
        if not book_path.exists():
            matches = [d for d in FICTION_DIR.iterdir() if args.book.lower() in d.name.lower()]
            if matches:
                book_path = matches[0]
            else:
                logger.error(f"Book not found: {args.book}")
                return
        books = [book_path]
    elif args.rerun:
        books = get_all_books()
    else:
        books = get_books_needing_fixes()

    if args.limit:
        books = books[:args.limit]

    logger.info(f"Found {len(books)} books to process")

    if not books:
        logger.info("No books to process!")
        return

    total_issues = 0
    total_fixes = 0

    for i, book_dir in enumerate(books, 1):
        logger.info(f"\n[{i}/{len(books)}] {book_dir.name}")

        try:
            fixer = BookFixer(book_dir, create_backup=not args.no_backup)

            if args.analyze:
                # Analysis only
                analysis = fixer.analyze()
                logger.info(f"  Chapters: {analysis['chapters']}")
                logger.info(f"  Words: {analysis['total_words']}")
                logger.info(f"  Short chapters: {analysis['short_chapters']}")
                logger.info(f"  POV issues: {analysis['has_pov_issues']}")
                logger.info(f"  Text issues: {sum(analysis['text_issues'].values())}")
                continue

            results = fixer.run_full_fix(text_only=args.text_only)

            total_issues += results.get("issues_found", 0)
            total_fixes += results["fixes_applied"]

            if results["details"]:
                for detail in results["details"]:
                    logger.info(f"    ✓ {detail}")

        except Exception as e:
            logger.error(f"  Error fixing {book_dir.name}: {e}")
            import traceback
            traceback.print_exc()

        time.sleep(1 if args.text_only else config.pipeline.delay_between_books)

    logger.info("\n" + "=" * 60)
    logger.info("FIX COMPLETE")
    logger.info(f"  Total issues found: {total_issues}")
    logger.info(f"  Total fixes applied: {total_fixes}")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
