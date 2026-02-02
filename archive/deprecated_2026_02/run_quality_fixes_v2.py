#!/usr/bin/env python3
"""
⚠️  DEPRECATION NOTICE (2026-02-01) ⚠️
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
This file has been DEPRECATED. Use instead:

    fix_books.py

Or use the quality pipeline:

    lib/quality_pipeline.py

New Usage:
    python fix_books.py --target-books 10

Or:
    from lib.quality_pipeline import QualityPipeline

    pipeline = QualityPipeline(fiction_dir)
    pipeline.run()

Migration Guide: See REFACTORING_COMPLETE_2026_02.md
Quick Start: See REFACTORING_QUICK_START.md
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

AI Quality Fixes v2 - Main command-line interface.

Usage:
    python run_quality_fixes_v2.py --detect-only    # Just scan for issues
    python run_quality_fixes_v2.py --fix            # Scan and fix issues
    python run_quality_fixes_v2.py --stats          # Show statistics
    python run_quality_fixes_v2.py --test           # Test on a single book
"""

import sys
from pathlib import Path

# Add lib directory to path
lib_path = Path(__file__).parent / 'lib'
sys.path.insert(0, str(lib_path))

from quality_pipeline_manager import QualityPipelineManager
from ai_quality_detector import AIQualityDetector, analyze_chapter_file
from ai_quality_fixer import fix_chapter_file, fix_book_directory
import json
import argparse


def test_single_book(fiction_dir: Path):
    """Test detection and fixing on a single book."""
    books = [d for d in fiction_dir.iterdir() if d.is_dir() and not d.name.startswith('.')]

    if not books:
        print("No books found")
        return

    # Pick a book that had issues in the quality review
    test_book = None
    for book in books:
        if 'Atomic_Productivity' in book.name or 'Action_Architect' in book.name:
            test_book = book
            break

    if not test_book:
        test_book = books[0]

    print(f"\n{'='*70}")
    print(f"TESTING ON: {test_book.name}")
    print(f"{'='*70}\n")

    # Find a chapter to test
    chapters = sorted(test_book.glob('chapter_*.md'))
    if not chapters:
        print("No chapters found")
        return

    test_chapter = chapters[2] if len(chapters) > 2 else chapters[0]

    print(f"Testing chapter: {test_chapter.name}\n")

    # 1. Detect issues
    print("1. DETECTING ISSUES...")
    print("-" * 70)

    issues, report = analyze_chapter_file(str(test_chapter))

    print(f"Quality Score: {report['quality_score']}/100")
    print(f"Total Issues: {report['total_issues']}\n")

    if report['by_severity']:
        print("Issues by severity:")
        for severity, count in sorted(report['by_severity'].items()):
            print(f"  {severity}: {count}")
        print()

    if report['critical_fixes_needed']:
        print("Critical fixes needed:")
        for i, fix in enumerate(report['critical_fixes_needed'][:5], 1):
            print(f"  {i}. {fix['type']}: {fix['message']}")
            if fix['suggestion']:
                print(f"     → {fix['suggestion']}")
        print()

    # 2. Show a sample of the content with issues
    print("2. SAMPLE OF CONTENT WITH ISSUES:")
    print("-" * 70)
    content = test_chapter.read_text()
    lines = content.split('\n')
    for i, line in enumerate(lines[20:30], 20):
        print(f"  {i:3d}: {line[:100]}")
    print()

    # 3. Apply fixes
    print("3. APPLYING FIXES...")
    print("-" * 70)

    fix_report = fix_chapter_file(test_chapter, backup=True)

    if fix_report['changes_made']:
        print(f"Fixes applied: {fix_report['fixes_applied']}\n")
        for fix in fix_report['fixes']:
            print(f"  • {fix['description']} ({fix['instances']} instances)")
            if fix.get('examples'):
                for example in fix['examples'][:3]:
                    print(f"    - {example}")
        print()
    else:
        print("No fixes needed or applied.\n")

    # 4. Show sample after fixing
    if fix_report['changes_made']:
        print("4. SAMPLE AFTER FIXES:")
        print("-" * 70)
        content = test_chapter.read_text()
        lines = content.split('\n')
        for i, line in enumerate(lines[20:30], 20):
            print(f"  {i:3d}: {line[:100]}")
        print()

    print(f"{'='*70}")
    print("TEST COMPLETE")
    print(f"Backup saved to: {test_chapter}.bak")
    print(f"{'='*70}\n")


def quick_scan(fiction_dir: Path, limit: int = 10):
    """Quick scan of books to identify issues."""
    books = [d for d in fiction_dir.iterdir() if d.is_dir() and not d.name.startswith('.')]
    books = books[:limit]

    print(f"\n{'='*70}")
    print(f"QUICK QUALITY SCAN ({len(books)} books)")
    print(f"{'='*70}\n")

    detector = AIQualityDetector()
    results = []

    for i, book in enumerate(books, 1):
        print(f"[{i}/{len(books)}] Scanning: {book.name}")

        chapters = sorted(book.glob('chapter_*.md'))
        book_issues = 0
        book_scores = []

        for chapter in chapters:
            try:
                issues, report = analyze_chapter_file(str(chapter))
                book_issues += report['total_issues']
                book_scores.append(report['quality_score'])
            except Exception as e:
                print(f"  Error: {e}")

        avg_score = sum(book_scores) / len(book_scores) if book_scores else 0

        results.append({
            'name': book.name,
            'score': int(avg_score),
            'issues': book_issues,
            'chapters': len(chapters)
        })

        status = "✓" if avg_score >= 80 else "⚠" if avg_score >= 60 else "✗"
        print(f"  {status} Score: {int(avg_score)}/100, Issues: {book_issues}\n")

    # Summary
    print(f"{'='*70}")
    print("SCAN SUMMARY")
    print(f"{'='*70}\n")

    results.sort(key=lambda x: x['score'])

    print("Books needing attention (lowest scores):")
    for result in results[:5]:
        print(f"  ✗ {result['name']}: {result['score']}/100, {result['issues']} issues")

    print()
    print("Best quality books:")
    for result in results[-5:]:
        print(f"  ✓ {result['name']}: {result['score']}/100, {result['issues']} issues")

    print(f"\n{'='*70}\n")


def main():
    parser = argparse.ArgumentParser(
        description='AI Quality Detection and Fixing System',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --test              # Test on a single book
  %(prog)s --scan              # Quick scan of 10 books
  %(prog)s --detect-only       # Detect issues in all books
  %(prog)s --fix               # Detect and fix all books
  %(prog)s --fix --limit 5     # Fix first 5 books
  %(prog)s --stats             # Show statistics
  %(prog)s --force --fix       # Force reprocessing of all books
        """
    )

    parser.add_argument('--fiction-dir', default='output/fiction',
                       help='Fiction directory path (default: output/fiction)')
    parser.add_argument('--test', action='store_true',
                       help='Test on a single book')
    parser.add_argument('--scan', action='store_true',
                       help='Quick scan of books')
    parser.add_argument('--detect-only', action='store_true',
                       help='Only detect issues, do not fix')
    parser.add_argument('--fix', action='store_true',
                       help='Detect and fix issues')
    parser.add_argument('--force', action='store_true',
                       help='Force reprocessing of all books')
    parser.add_argument('--limit', type=int,
                       help='Limit number of books to process')
    parser.add_argument('--stats', action='store_true',
                       help='Show statistics')

    args = parser.parse_args()

    fiction_dir = Path(args.fiction_dir)

    if not fiction_dir.exists():
        print(f"Error: Fiction directory not found: {fiction_dir}")
        sys.exit(1)

    # Test mode
    if args.test:
        test_single_book(fiction_dir)
        return

    # Quick scan mode
    if args.scan:
        quick_scan(fiction_dir, limit=10)
        return

    # Full pipeline processing
    manager = QualityPipelineManager(fiction_dir)

    if args.stats:
        stats = manager.get_statistics()
        print(json.dumps(stats, indent=2))
        return

    if args.fix or args.detect_only:
        summary = manager.process_all_books(
            fix=args.fix,
            force=args.force,
            limit=args.limit
        )
        manager.print_summary(summary)
        return

    # No action specified, show help
    parser.print_help()


if __name__ == "__main__":
    main()
