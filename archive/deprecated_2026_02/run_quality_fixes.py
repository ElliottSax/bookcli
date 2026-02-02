#!/usr/bin/env python3
"""
⚠️  DEPRECATION NOTICE (2026-02-01) ⚠️
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
This file has been DEPRECATED. Use instead:

    fix_books.py

The fix_books.py script provides the same functionality with better
integration and more comprehensive options.

New Usage:
    python fix_books.py --target-books 10

Or use the quality pipeline:
    from lib.quality_pipeline import QualityPipeline

    pipeline = QualityPipeline(fiction_dir)
    pipeline.run()

Migration Guide: See REFACTORING_COMPLETE_2026_02.md
Quick Start: See REFACTORING_QUICK_START.md
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Run quality fixes on books: variety improvement and hook strengthening.

Usage:
    python run_quality_fixes.py [--books N] [--variety] [--hooks] [--all]
"""

import argparse
import random
import sys
import time
from pathlib import Path

from dotenv import load_dotenv
load_dotenv()

from lib.logging_config import setup_logging, get_logger
from lib.config import get_config
from lib.backup import BackupManager
from fixers import BookContext, VarietyFixer, HookStrengthener, CoherencyFixer

setup_logging()
logger = get_logger(__name__)
config = get_config()

FICTION_DIR = config.paths.fiction_dir


def get_books(n: int = None, random_sample: bool = True) -> list:
    """Get books to process."""
    all_books = [
        d for d in FICTION_DIR.iterdir()
        if d.is_dir() and not d.name.startswith('.') and list(d.glob("chapter_*.md"))
    ]

    # Filter out already processed
    unprocessed = [b for b in all_books if not (b / ".variety_fixed").exists()]

    if n and len(unprocessed) > n:
        if random_sample:
            return random.sample(unprocessed, n)
        return unprocessed[:n]

    return unprocessed


def fix_book(book_path: Path, fix_variety: bool = True, fix_hooks: bool = True,
             fix_coherency: bool = True, use_llm: bool = True) -> dict:
    """
    Run fixes on a single book.

    Returns stats dict.
    """
    stats = {"variety_fixes": 0, "hook_fixes": 0, "coherency_fixes": 0, "error": None}

    try:
        # Create backup
        backup_mgr = BackupManager(book_path)
        backup_mgr.backup_all_chapters()

        # Fix coherency FIRST (generation loops, duplications)
        # This should run before other fixes as it removes duplicate content
        if fix_coherency:
            context = BookContext(book_path)
            coherency_fixer = CoherencyFixer(
                context,
                fix_loops=True,
                fix_duplicates=True,
                aggressive=False  # Safe mode by default
            )
            stats["coherency_fixes"] = coherency_fixer.fix()

        # Fix variety (pattern-based first, then LLM if needed)
        if fix_variety:
            context = BookContext(book_path)  # Reload after coherency fixes
            variety_fixer = VarietyFixer(context, use_llm=use_llm, threshold=5)
            stats["variety_fixes"] = variety_fixer.fix()

        # Fix hooks
        if fix_hooks:
            context = BookContext(book_path)  # Reload after variety fixes
            hook_fixer = HookStrengthener(context, chapters_to_fix=[1])  # Just chapter 1
            stats["hook_fixes"] = hook_fixer.fix()

        # Mark as processed
        (book_path / ".variety_fixed").write_text(f"{stats}")

    except Exception as e:
        stats["error"] = str(e)
        logger.error(f"  Error: {e}")

    return stats


def main():
    parser = argparse.ArgumentParser(description="Run quality fixes on books")
    parser.add_argument("--books", "-n", type=int, default=10,
                       help="Number of books to process (default: 10)")
    parser.add_argument("--variety", action="store_true",
                       help="Run variety fixer only")
    parser.add_argument("--hooks", action="store_true",
                       help="Run hook strengthener only")
    parser.add_argument("--coherency", action="store_true",
                       help="Run coherency fixer only (fixes generation loops)")
    parser.add_argument("--no-llm", action="store_true",
                       help="Skip LLM-based fixes (faster)")
    parser.add_argument("--all", action="store_true",
                       help="Process all books")
    args = parser.parse_args()

    # Determine what to fix
    # If any specific fixer is requested, only run those
    specific_requested = args.variety or args.hooks or args.coherency
    fix_variety = args.variety or not specific_requested
    fix_hooks = args.hooks or not specific_requested
    fix_coherency = args.coherency or not specific_requested
    use_llm = not args.no_llm

    n_books = None if args.all else args.books
    books = get_books(n_books)

    if not books:
        logger.info("No unprocessed books found")
        return

    logger.info(f"Processing {len(books)} books")
    logger.info(f"Fixes: coherency={fix_coherency}, variety={fix_variety}, hooks={fix_hooks}, llm={use_llm}")

    total_coherency = 0
    total_variety = 0
    total_hooks = 0
    success = 0

    for i, book_path in enumerate(books, 1):
        logger.info(f"[{i}/{len(books)}] {book_path.name}")

        stats = fix_book(book_path, fix_variety, fix_hooks, fix_coherency, use_llm)

        if stats["error"]:
            logger.warning(f"  Failed: {stats['error']}")
        else:
            logger.info(f"  Coherency: {stats['coherency_fixes']}, Variety: {stats['variety_fixes']}, Hooks: {stats['hook_fixes']}")
            total_coherency += stats["coherency_fixes"]
            total_variety += stats["variety_fixes"]
            total_hooks += stats["hook_fixes"]
            success += 1

        time.sleep(0.5)  # Brief pause

    logger.info("=" * 60)
    logger.info(f"COMPLETE: {success}/{len(books)} books processed")
    logger.info(f"Coherency fixes: {total_coherency}")
    logger.info(f"Variety fixes: {total_variety}")
    logger.info(f"Hook fixes: {total_hooks}")


if __name__ == "__main__":
    main()
