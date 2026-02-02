#!/usr/bin/env python3
"""
Add subtext and depth to dialogue using the fixers module.

This is a thin wrapper around QualityFixer.add_dialogue_subtext().
The actual implementation is in fixers/quality_fixer.py.
"""

import time
from pathlib import Path

# Use centralized lib modules
from lib.logging_config import setup_logging, get_logger
from lib.config import get_config

# Use the fixers module for actual work
from fixers import BookContext, QualityFixer

# Initialize logging once
setup_logging()
logger = get_logger(__name__)

# Get config
config = get_config()
FICTION_DIR = config.paths.fiction_dir


def process_book(book_dir: Path) -> int:
    """
    Process a book to add dialogue depth.

    Uses QualityFixer.add_dialogue_subtext() for the actual work.
    """
    context = BookContext(book_dir)
    fixer = QualityFixer(
        context,
        expand_short=False,
        fix_pov=False,
        fix_ai_isms=False,
        add_dialogue_depth=True,
    )
    return fixer.add_dialogue_subtext()


def main():
    """Process all books that haven't been processed yet."""
    if not FICTION_DIR.exists():
        logger.warning(f"Fiction directory not found: {FICTION_DIR}")
        return

    books = [d for d in FICTION_DIR.iterdir() if d.is_dir()]
    books = [b for b in books if not (b / ".dialogue_depth").exists()]

    logger.info(f"Found {len(books)} books to add dialogue depth")

    for i, book_dir in enumerate(books, 1):
        chapters = sorted(book_dir.glob("chapter_*.md"))
        if not chapters:
            continue

        logger.info(f"[{i}/{len(books)}] {book_dir.name}")
        improved = process_book(book_dir)

        if improved > 0:
            logger.info(f"  Improved {improved} chapters")
            (book_dir / ".dialogue_depth").write_text(f"{improved}")

        time.sleep(config.pipeline.delay_between_books)


if __name__ == "__main__":
    main()
