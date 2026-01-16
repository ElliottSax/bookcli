#!/usr/bin/env python3
"""Add subtext and depth to dialogue using the centralized API client."""

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


def add_dialogue_depth(chapter_file: Path) -> bool:
    """Add subtext and depth to dialogue in a chapter."""
    text = chapter_file.read_text()

    # Check if chapter has enough dialogue
    if text.count('"') < config.quality.min_dialogue_quotes:
        return False

    prompt = f"""Add subtext and depth to the dialogue in this passage.
- Add what characters are really thinking vs saying
- Include meaningful pauses and reactions
- Add physical beats between lines
- Show unspoken tension or emotion
Keep same plot. Return ONLY the improved text.

{text[:3500]}"""

    improved = call_llm(prompt, max_tokens=4000)

    if improved and len(improved) > 1000:
        chapter_file.write_text(improved)
        return True

    return False


def main():
    """Process all books that haven't been processed yet."""
    books = [d for d in FICTION_DIR.iterdir() if d.is_dir()]
    books = [b for b in books if not (b / ".dialogue_depth").exists()]

    logger.info(f"Found {len(books)} books to add dialogue depth")

    for i, book_dir in enumerate(books, 1):
        chapters = sorted(book_dir.glob("chapter_*.md"))
        if not chapters:
            continue

        logger.info(f"[{i}/{len(books)}] {book_dir.name}")
        improved = 0

        for ch in chapters[:3]:
            if add_dialogue_depth(ch):
                improved += 1
                logger.info(f"  Improved {ch.name}")
                time.sleep(config.pipeline.delay_between_chapters)

        if improved > 0:
            (book_dir / ".dialogue_depth").write_text(f"{improved}")

        time.sleep(config.pipeline.delay_between_books)


if __name__ == "__main__":
    main()
