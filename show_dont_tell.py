#!/usr/bin/env python3
"""
Convert telling to showing using the fixers module.

This is a thin wrapper around QualityFixer.convert_telling_to_showing().
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
    Process a book to convert telling to showing.

    Uses QualityFixer.convert_telling_to_showing() for the actual work.
    """
    context = BookContext(book_dir)
    fixer = QualityFixer(
        context,
        expand_short=False,
        fix_pov=False,
        fix_ai_isms=False,
        show_dont_tell=True,
    )
    return fixer.convert_telling_to_showing()


def main():
    """Process all books that haven't been processed yet."""
    if not FICTION_DIR.exists():
        logger.warning(f"Fiction directory not found: {FICTION_DIR}")
        return

    books = [d for d in FICTION_DIR.iterdir() if d.is_dir()]
    books = [b for b in books if not (b / ".show_dont_tell").exists()]

    logger.info(f"Found {len(books)} books to improve show-don't-tell")

    for i, book_dir in enumerate(books, 1):
        if not list(book_dir.glob("chapter_*.md")):
            continue

        logger.info(f"[{i}/{len(books)}] {book_dir.name}")
        count = process_book(book_dir)

        if count > 0:
            logger.info(f"  Converted {count} passages")
            (book_dir / ".show_dont_tell").write_text(f"{count}")

        time.sleep(config.pipeline.delay_between_books)


if __name__ == "__main__":
    main()
