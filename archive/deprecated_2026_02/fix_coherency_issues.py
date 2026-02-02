#!/usr/bin/env python3
"""
⚠️  DEPRECATION NOTICE (2026-02-01) ⚠️
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
This file has been DEPRECATED. Use instead:

    fixers/coherency_fixer.py (direct usage)

Or better yet, use the quality pipeline which includes coherency fixes:

    lib/quality_pipeline.py

New Usage:
    from lib.quality_pipeline import QualityPipeline

    pipeline = QualityPipeline(fiction_dir)
    pipeline.run()  # Includes coherency fixes

Or direct usage:
    from fixers import BookContext, CoherencyFixer

    context = BookContext(book_dir)
    fixer = CoherencyFixer(context, fix_loops=True, fix_duplicates=True)
    fixes = fixer.fix()

Migration Guide: See REFACTORING_COMPLETE_2026_02.md
Quick Start: See REFACTORING_QUICK_START.md
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Fix Coherency Issues
====================
Runs CoherencyFixer on all books that failed coherency validation.

Reads from coherency_summary.json and fixes:
- Generation loops (paragraph, dialogue, sentence repetition)
- Cross-chapter duplications
"""

import json
import time
import argparse
from pathlib import Path
from typing import List, Dict
from concurrent.futures import ThreadPoolExecutor, as_completed

from lib.logging_config import setup_logging, get_logger
from lib.config import get_config
from fixers import BookContext, CoherencyFixer

setup_logging()
logger = get_logger(__name__)
config = get_config()


def get_failing_books() -> List[Path]:
    """Get list of books that failed coherency validation."""
    summary_path = config.paths.output_dir / "coherency_summary.json"

    if not summary_path.exists():
        logger.error(f"Coherency summary not found: {summary_path}")
        logger.info("Run coherency_validator.py --all first")
        return []

    summary = json.loads(summary_path.read_text())
    failing = []

    for book_info in summary.get('failing_books', []):
        book_name = book_info['book']
        # Check fiction first, then books
        book_path = config.paths.fiction_dir / book_name
        if not book_path.exists():
            book_path = config.paths.books_dir / book_name
        if book_path.exists():
            failing.append(book_path)

    return failing


def get_books_with_loops() -> List[Path]:
    """Get books specifically with loop issues."""
    summary_path = config.paths.output_dir / "coherency_summary.json"

    if not summary_path.exists():
        return []

    summary = json.loads(summary_path.read_text())
    loop_books = []

    for book_name in summary.get('books_with_loops', []):
        book_path = config.paths.fiction_dir / book_name
        if not book_path.exists():
            book_path = config.paths.books_dir / book_name
        if book_path.exists():
            loop_books.append(book_path)

    return loop_books


def fix_book(book_dir: Path, aggressive: bool = False) -> Dict:
    """Fix coherency issues in a single book."""
    result = {
        'book': book_dir.name,
        'fixes': 0,
        'error': None
    }

    try:
        context = BookContext(book_dir)
        fixer = CoherencyFixer(context, fix_loops=True, fix_duplicates=True,
                               aggressive=aggressive)

        # Analyze first
        analysis = fixer.analyze()
        result['issues_found'] = {
            'paragraph_loops': analysis['paragraph_loops'],
            'dialogue_loops': analysis['dialogue_loops'],
            'sentence_loops': analysis['sentence_loops'],
            'cross_chapter_duplicates': analysis['cross_chapter_duplicates']
        }

        # Apply fixes
        fixes = fixer.fix()
        result['fixes'] = fixes

        # Save report
        report_path = book_dir / 'coherency_fix_report.json'
        report_path.write_text(json.dumps(result, indent=2))

    except Exception as e:
        result['error'] = str(e)
        logger.error(f"Error fixing {book_dir.name}: {e}")

    return result


def main():
    parser = argparse.ArgumentParser(description="Fix coherency issues in books")
    parser.add_argument('--book', type=str, help="Fix specific book by name")
    parser.add_argument('--loops-only', action='store_true',
                       help="Only fix books with loop issues")
    parser.add_argument('--all-failing', action='store_true',
                       help="Fix all failing books from coherency validation")
    parser.add_argument('--limit', type=int, help="Limit number of books")
    parser.add_argument('--aggressive', action='store_true',
                       help="Use aggressive fixing (remove more content)")
    parser.add_argument('--parallel', type=int, default=1,
                       help="Number of parallel workers")
    parser.add_argument('--analyze-only', action='store_true',
                       help="Only analyze, don't fix")
    args = parser.parse_args()

    logger.info("=" * 60)
    logger.info("COHERENCY FIXER")
    logger.info("=" * 60)

    # Get books to process
    if args.book:
        book_path = config.paths.fiction_dir / args.book
        if not book_path.exists():
            # Try fuzzy match
            matches = [d for d in config.paths.fiction_dir.iterdir()
                      if args.book.lower() in d.name.lower()]
            if matches:
                book_path = matches[0]
            else:
                book_path = config.paths.books_dir / args.book
        if not book_path.exists():
            logger.error(f"Book not found: {args.book}")
            return
        books = [book_path]
    elif args.loops_only:
        books = get_books_with_loops()
    elif args.all_failing:
        books = get_failing_books()
    else:
        # Default: fix books with loops
        books = get_books_with_loops()

    if args.limit:
        books = books[:args.limit]

    logger.info(f"Books to process: {len(books)}")

    if not books:
        logger.info("No books to process!")
        return

    total_fixes = 0
    total_issues = 0

    if args.parallel > 1:
        # Parallel processing
        with ThreadPoolExecutor(max_workers=args.parallel) as executor:
            futures = {executor.submit(fix_book, b, args.aggressive): b for b in books}

            for i, future in enumerate(as_completed(futures), 1):
                book = futures[future]
                try:
                    result = future.result()
                    fixes = result.get('fixes', 0)
                    total_fixes += fixes

                    issues = result.get('issues_found', {})
                    book_issues = sum(issues.values()) if issues else 0
                    total_issues += book_issues

                    logger.info(f"[{i}/{len(books)}] {book.name}: "
                               f"{book_issues} issues, {fixes} fixes")

                except Exception as e:
                    logger.error(f"[{i}/{len(books)}] {book.name}: ERROR - {e}")

    else:
        # Sequential processing
        for i, book_dir in enumerate(books, 1):
            logger.info(f"[{i}/{len(books)}] {book_dir.name}")

            if args.analyze_only:
                context = BookContext(book_dir)
                fixer = CoherencyFixer(context)
                analysis = fixer.analyze()
                total = (analysis['paragraph_loops'] + analysis['dialogue_loops'] +
                        analysis['sentence_loops'] + analysis['cross_chapter_duplicates'])
                logger.info(f"  Paragraph loops: {analysis['paragraph_loops']}")
                logger.info(f"  Dialogue loops: {analysis['dialogue_loops']}")
                logger.info(f"  Sentence loops: {analysis['sentence_loops']}")
                logger.info(f"  Cross-chapter duplicates: {analysis['cross_chapter_duplicates']}")
                total_issues += total
                continue

            result = fix_book(book_dir, args.aggressive)

            if result.get('error'):
                logger.error(f"  Error: {result['error']}")
                continue

            fixes = result.get('fixes', 0)
            total_fixes += fixes

            issues = result.get('issues_found', {})
            if issues:
                total = sum(issues.values())
                total_issues += total
                if total > 0:
                    logger.info(f"  Found {total} issues, applied {fixes} fixes")

            time.sleep(0.1)  # Small delay between books

    logger.info("=" * 60)
    logger.info("COMPLETE")
    logger.info(f"  Total issues found: {total_issues}")
    if not args.analyze_only:
        logger.info(f"  Total fixes applied: {total_fixes}")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
