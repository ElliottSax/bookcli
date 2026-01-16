#!/usr/bin/env python3
"""Convert telling to showing using the centralized API client."""

import re
import time
from pathlib import Path

# Use centralized lib modules
from lib.logging_config import setup_logging, get_logger
from lib.config import get_config
from lib.api_client import call_llm

# Initialize logging once
setup_logging()
logger = get_logger(__name__)

# Get config
config = get_config()
FICTION_DIR = config.paths.fiction_dir


def find_telling_passages(text: str) -> list:
    """Find passages that tell instead of show."""
    telling_patterns = [
        r'(was|were|felt|seemed) (angry|sad|happy|nervous|scared|excited|worried)',
        r'(He|She|They) (was|were) (very|extremely|really) \w+',
    ]

    paragraphs = text.split('\n\n')
    telling = []

    for i, para in enumerate(paragraphs):
        if len(para) < config.quality.min_paragraph_length:
            continue
        for pattern in telling_patterns:
            if re.search(pattern, para, re.IGNORECASE):
                telling.append((i, para))
                break

    return telling[:3]


def convert_to_showing(para: str) -> str:
    """Convert a telling passage to showing."""
    prompt = f"""Convert this "telling" passage to "showing".
Instead of stating emotions directly, show them through:
- Physical sensations and body language
- Actions and dialogue
- Sensory details

Keep the same meaning. Return ONLY the improved passage.

{para}"""

    improved = call_llm(prompt, max_tokens=500, temperature=0.6)

    if improved and len(improved) > 50:
        return improved
    return None


def process_book(book_dir: Path) -> int:
    """Process a book to convert telling to showing."""
    improvements = 0

    for chapter in sorted(book_dir.glob("chapter_*.md"))[:5]:
        text = chapter.read_text()
        telling = find_telling_passages(text)

        for idx, para in telling:
            improved = convert_to_showing(para)
            if improved:
                text = text.replace(para, improved)
                improvements += 1
                time.sleep(config.pipeline.delay_between_chapters)

        if improvements > 0:
            chapter.write_text(text)

    return improvements


def main():
    """Process all books that haven't been processed yet."""
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
