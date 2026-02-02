#!/usr/bin/env python3
"""
⚠️  DEPRECATION NOTICE (2026-02-01) ⚠️
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
This file has been DEPRECATED and replaced by:

    lib/quality_pipeline.py

The quality pipeline has been consolidated into a unified module with
better state tracking, consistent API, and 3 processing modes.

New Usage:
    from lib.quality_pipeline import QualityPipeline

    # Simple local processing
    pipeline = QualityPipeline(fiction_dir)
    pipeline.run()

    # Parallel batch processing
    from lib.quality_pipeline import BatchPipeline
    pipeline = BatchPipeline(fiction_dir, max_workers=4)
    pipeline.run()

Migration Guide: See REFACTORING_COMPLETE_2026_02.md
Quick Start: See REFACTORING_QUICK_START.md
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Run quality improvements on all books in the output directories.

Uses the fixers module for quality improvements with checkpoint/backup support.
Processes books from:
- output/fiction (fiction books)
- output/books (non-fiction/self-help books)

Tracking Features:
- Content hash verification to detect changed books
- Timestamp checking against chapter modifications
- Integration with checkpoint system
- Stale marker detection and cleanup
"""

import sys
import time
import json
import hashlib
import argparse
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime

# Load .env file before importing config
from dotenv import load_dotenv
load_dotenv()

from lib.logging_config import setup_logging, get_logger
from lib.config import get_config
from lib.checkpoint import CheckpointManager, ProcessingStage, BookStatus
from lib.backup import BackupManager
from fixers import BookContext, QualityFixer, TextFixer

# Initialize
setup_logging()
logger = get_logger(__name__)
config = get_config()

# All directories containing books to process
BOOK_DIRS = [
    config.paths.fiction_dir,  # output/fiction
    config.paths.output_dir / "books",  # output/books (non-fiction)
]

# Quality marker version for compatibility
QUALITY_MARKER_VERSION = 2


def compute_book_hash(book_dir: Path) -> str:
    """
    Compute a hash of all chapter content to detect changes.

    Args:
        book_dir: Path to book directory

    Returns:
        SHA256 hash of all chapter content concatenated
    """
    hasher = hashlib.sha256()

    chapters = sorted(book_dir.glob("chapter_*.md"))
    for chapter in chapters:
        try:
            content = chapter.read_bytes()
            hasher.update(content)
        except (OSError, IOError) as e:
            logger.debug(f"Could not read {chapter}: {e}")

    return hasher.hexdigest()


def get_latest_chapter_mtime(book_dir: Path) -> float:
    """
    Get the modification time of the most recently modified chapter.

    Args:
        book_dir: Path to book directory

    Returns:
        Timestamp of newest chapter, or 0 if no chapters found
    """
    chapters = list(book_dir.glob("chapter_*.md"))
    if not chapters:
        return 0.0

    return max(c.stat().st_mtime for c in chapters)


def read_quality_marker(book_dir: Path) -> Optional[Dict]:
    """
    Read and parse quality marker file.

    Args:
        book_dir: Path to book directory

    Returns:
        Dict with marker data, or None if not found/invalid
    """
    marker_file = book_dir / ".quality_processed"
    if not marker_file.exists():
        return None

    try:
        content = marker_file.read_text().strip()

        if not content:
            return None

        # Try JSON first (new format v2)
        if content.startswith('{') and ('"version"' in content or '"timestamp"' in content):
            try:
                return json.loads(content)
            except json.JSONDecodeError:
                pass

        # Handle old format with Python dict syntax (single quotes)
        if content.startswith('{'):
            try:
                import ast
                stats = ast.literal_eval(content)
                return {
                    "version": 1,
                    "timestamp": marker_file.stat().st_mtime,
                    "content_hash": None,
                    "stats": stats
                }
            except (ValueError, SyntaxError):
                pass

        # Very old format like "text:18,quality:10"
        if ':' in content and ',' in content:
            try:
                parts = content.split(',')
                text_fixes = int(parts[0].split(':')[1])
                quality_fixes = int(parts[1].split(':')[1]) if len(parts) > 1 else 0
                return {
                    "version": 1,
                    "timestamp": marker_file.stat().st_mtime,
                    "content_hash": None,
                    "stats": {"text_fixes": text_fixes, "quality_fixes": quality_fixes, "error": None}
                }
            except (ValueError, IndexError):
                pass

        return None

    except Exception as e:
        logger.debug(f"Could not parse quality marker for {book_dir.name}: {e}")
        return None


def write_quality_marker(book_dir: Path, stats: Dict, content_hash: str) -> None:
    """
    Write quality marker with full tracking information.

    Args:
        book_dir: Path to book directory
        stats: Statistics from quality run
        content_hash: Hash of chapter content at time of processing
    """
    marker_data = {
        "version": QUALITY_MARKER_VERSION,
        "timestamp": time.time(),
        "date": datetime.now().isoformat(),
        "content_hash": content_hash,
        "stats": stats
    }

    marker_file = book_dir / ".quality_processed"
    marker_file.write_text(json.dumps(marker_data, indent=2))


def is_marker_stale(book_dir: Path, marker: Dict, quick: bool = False) -> bool:
    """
    Check if quality marker is stale (book changed since processing).

    A marker is stale if:
    1. Any chapter was modified after marker timestamp (fast check)
    2. Checkpoint shows newer fixes than marker (medium check)
    3. Content hash doesn't match current content (slow check, skipped if quick=True)

    Args:
        book_dir: Path to book directory
        marker: Marker data from read_quality_marker()
        quick: If True, skip expensive checks (checkpoint + hash)

    Returns:
        True if marker is stale and book should be reprocessed
    """
    if not marker:
        return True

    marker_time = marker.get("timestamp", 0)

    # Check 1: Chapter modification times (FAST - always check)
    latest_chapter_mtime = get_latest_chapter_mtime(book_dir)
    if latest_chapter_mtime > marker_time + 60:  # Allow 60 second buffer
        logger.debug(f"{book_dir.name}: Chapters modified after quality run")
        return True

    # If in quick mode, stop here - chapter mtime check is sufficient
    if quick:
        return False

    # Check 2: Checkpoint shows newer work (MEDIUM speed)
    checkpoint_file = book_dir / ".checkpoint.json"
    if checkpoint_file.exists():
        try:
            checkpoint_mtime = checkpoint_file.stat().st_mtime
            if checkpoint_mtime > marker_time + 60:
                # Checkpoint is newer, parse it to check fixes
                checkpoint_data = json.loads(checkpoint_file.read_text())
                fixes = checkpoint_data.get("metadata", {}).get("fixes", 0)
                marker_fixes = marker.get("stats", {}).get("text_fixes", 0) + marker.get("stats", {}).get("quality_fixes", 0)
                if fixes > marker_fixes:
                    logger.debug(f"{book_dir.name}: Checkpoint shows {fixes} fixes vs marker's {marker_fixes}")
                    return True
        except Exception as e:
            logger.debug(f"Error checking checkpoint for {book_dir.name}: {e}")

    # Check 3: Content hash (SLOW - only in non-quick mode)
    marker_hash = marker.get("content_hash")
    if marker_hash:
        current_hash = compute_book_hash(book_dir)
        if current_hash != marker_hash:
            logger.debug(f"{book_dir.name}: Content hash changed")
            return True

    return False


def run_quality_on_book(book_dir: Path, use_llm: bool = False) -> dict:
    """
    Run all quality improvements on a single book.

    Args:
        book_dir: Path to book directory
        use_llm: Whether to run LLM-based quality fixes

    Returns:
        Dict with stats: text_fixes, quality_fixes, error
    """
    stats = {"text_fixes": 0, "quality_fixes": 0, "error": None}

    try:
        chapters = sorted(book_dir.glob("chapter_*.md"))
        if not chapters:
            stats["error"] = "No chapters found"
            return stats

        # Compute initial hash before any changes
        initial_hash = compute_book_hash(book_dir)

        # Initialize managers
        checkpoint_mgr = CheckpointManager(book_dir)
        backup_mgr = BackupManager(book_dir)

        # Create backup before modifications
        backups = backup_mgr.backup_all_chapters()
        logger.info(f"  Created {len(backups)} backups")

        # Save checkpoint
        checkpoint_mgr.save(ProcessingStage.QUALITY_CHECKS, chapter=0, total=len(chapters))

        # Create context and run text fixes (no LLM required)
        context = BookContext(book_dir)
        text_fixer = TextFixer(context)
        stats["text_fixes"] = text_fixer.fix()

        # Only run LLM-based fixes if API is available
        if use_llm:
            # Reload context and run quality fixes
            context = BookContext(book_dir)
            quality_fixer = QualityFixer(
                context,
                expand_short=True,
                fix_pov=True,
                fix_ai_isms=True,
                add_sensory=False,  # Skip heavy AI passes for speed
                add_tension=False,
                improve_dialogue=False,
                improve_endings=False,
                show_dont_tell=False,
                add_dialogue_depth=False,
            )
            stats["quality_fixes"] = quality_fixer.fix()

        # Compute final hash after all fixes
        final_hash = compute_book_hash(book_dir)

        # Mark complete in checkpoint
        total_fixes = stats["text_fixes"] + stats["quality_fixes"]
        checkpoint_mgr.save(
            ProcessingStage.QUALITY_CHECKS,
            chapter=len(chapters),
            total=len(chapters),
            status=BookStatus.COMPLETED,
            metadata={"fixes": total_fixes}
        )

        # Write quality marker with full tracking info
        write_quality_marker(book_dir, stats, final_hash)

        logger.debug(f"  Quality marker: v{QUALITY_MARKER_VERSION}, hash={final_hash[:8]}...")

    except Exception as e:
        stats["error"] = str(e)
        logger.error(f"  Error: {e}")

    return stats


def get_all_books() -> List[Path]:
    """Get all book directories from all configured locations."""
    all_books = []

    for book_dir in BOOK_DIRS:
        if book_dir.exists():
            books = [d for d in book_dir.iterdir() if d.is_dir() and not d.name.startswith('.')]
            # Only include directories that have chapter files (optimized check)
            books_with_chapters = []
            for b in books:
                # Use next() to check for existence without listing all files
                try:
                    next(b.glob("chapter_*.md"))
                    books_with_chapters.append(b)
                except StopIteration:
                    pass
            all_books.extend(books_with_chapters)
            logger.info(f"Found {len(books_with_chapters)} books in {book_dir}")

    return sorted(all_books, key=lambda x: x.name)


def check_stale_markers(books: List[Path], quick: bool = True) -> Dict[str, List[Path]]:
    """
    Analyze all books and categorize by marker status.

    Args:
        books: List of book directories to check
        quick: If True, skip expensive content hash checks (much faster)

    Returns:
        Dict with categories: unprocessed, stale, fresh, errors
    """
    results = {
        "unprocessed": [],
        "stale": [],
        "fresh": [],
        "errors": []
    }

    logger.info(f"Checking {len(books)} books (quick={'yes' if quick else 'no'})...")

    for i, book_dir in enumerate(books, 1):
        if i % 50 == 0:
            logger.info(f"  Checked {i}/{len(books)} books...")

        try:
            marker = read_quality_marker(book_dir)

            if not marker:
                results["unprocessed"].append(book_dir)
            elif is_marker_stale(book_dir, marker, quick=quick):
                results["stale"].append(book_dir)
            else:
                results["fresh"].append(book_dir)
        except Exception as e:
            logger.debug(f"Error checking {book_dir.name}: {e}")
            results["errors"].append(book_dir)

    return results


def clear_all_markers(books: List[Path]) -> int:
    """
    Clear all quality markers from books.

    Args:
        books: List of book directories

    Returns:
        Number of markers cleared
    """
    cleared = 0
    for book_dir in books:
        marker_file = book_dir / ".quality_processed"
        if marker_file.exists():
            try:
                marker_file.unlink()
                cleared += 1
            except Exception as e:
                logger.warning(f"Could not clear marker for {book_dir.name}: {e}")

    return cleared


def main():
    """Process all books with smart tracking and stale detection."""
    parser = argparse.ArgumentParser(
        description="Run quality improvements on all books",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                    # Process only unprocessed books
  %(prog)s --check-stale      # Report on stale markers without processing
  %(prog)s --force-stale      # Process only books with stale markers
  %(prog)s --force            # Reprocess all books (ignores markers)
  %(prog)s --clear-markers    # Clear all quality markers
        """
    )
    parser.add_argument(
        "--check-stale",
        action="store_true",
        help="Check for stale markers and report without processing"
    )
    parser.add_argument(
        "--force-stale",
        action="store_true",
        help="Process only books with stale markers"
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Reprocess all books regardless of markers"
    )
    parser.add_argument(
        "--clear-markers",
        action="store_true",
        help="Clear all quality markers and exit"
    )

    args = parser.parse_args()

    # Check if API is available for LLM-based fixes
    available_apis = config.api.get_available_apis()
    use_llm = len(available_apis) > 0

    if use_llm:
        logger.info(f"API available ({available_apis[0]}) - LLM-based fixes enabled")
    else:
        logger.info("No API keys configured - running text fixes only (no LLM)")
        logger.info("Set one of: DEEPSEEK_API_KEY, GROQ_API_KEY, OPENROUTER_API_KEY, etc.")

    # Get books from all directories
    books = get_all_books()

    if not books:
        logger.error("No books found in any configured directory")
        sys.exit(1)

    # Handle --clear-markers
    if args.clear_markers:
        logger.info("Clearing all quality markers...")
        cleared = clear_all_markers(books)
        logger.info(f"Cleared {cleared} quality markers")
        return

    # Analyze marker status
    logger.info("Analyzing quality markers...")
    status = check_stale_markers(books)

    logger.info("=" * 60)
    logger.info(f"Quality Marker Status:")
    logger.info(f"  Unprocessed (no marker): {len(status['unprocessed'])}")
    logger.info(f"  Stale (needs reprocess): {len(status['stale'])}")
    logger.info(f"  Fresh (up to date): {len(status['fresh'])}")
    if status['errors']:
        logger.info(f"  Errors: {len(status['errors'])}")
    logger.info("=" * 60)

    # Handle --check-stale (report only)
    if args.check_stale:
        if status['stale']:
            logger.info("\nBooks with stale markers:")
            for i, book_dir in enumerate(status['stale'][:50], 1):
                marker = read_quality_marker(book_dir)
                marker_date = datetime.fromtimestamp(marker['timestamp']).strftime('%Y-%m-%d %H:%M')
                logger.info(f"  {i}. {book_dir.name} (marker: {marker_date})")
            if len(status['stale']) > 50:
                logger.info(f"  ... and {len(status['stale']) - 50} more")
        else:
            logger.info("\nNo stale markers found!")
        return

    # Determine which books to process
    if args.force:
        # Reprocess all books
        to_process = books
        logger.info("Force mode: Processing all books")
    elif args.force_stale:
        # Process only stale books
        to_process = status['stale']
        logger.info(f"Processing {len(to_process)} books with stale markers")
    else:
        # Process unprocessed + stale books (default smart mode)
        to_process = status['unprocessed'] + status['stale']
        logger.info(f"Processing {len(to_process)} books (unprocessed + stale)")

    if not to_process:
        logger.info("No books need processing!")
        logger.info("Use --check-stale to see marker status")
        logger.info("Use --force to reprocess all books anyway")
        return

    # Process books
    total_text = 0
    total_quality = 0
    start_time = time.time()

    for i, book_dir in enumerate(to_process, 1):
        logger.info(f"[{i}/{len(to_process)}] Processing: {book_dir.name}")

        stats = run_quality_on_book(book_dir, use_llm=use_llm)

        if stats["error"]:
            logger.warning(f"  Failed: {stats['error']}")
        else:
            logger.info(f"  Text fixes: {stats['text_fixes']}, Quality fixes: {stats['quality_fixes']}")
            total_text += stats["text_fixes"]
            total_quality += stats["quality_fixes"]

        time.sleep(0.5)  # Brief pause between books

    elapsed = time.time() - start_time

    logger.info("=" * 60)
    logger.info(f"COMPLETE: {len(to_process)} books processed in {elapsed/60:.1f} minutes")
    logger.info(f"Total text fixes: {total_text}")
    logger.info(f"Total quality fixes: {total_quality}")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
