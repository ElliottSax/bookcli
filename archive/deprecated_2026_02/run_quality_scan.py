#!/usr/bin/env python3
"""
⚠️  DEPRECATION NOTICE (2026-02-01) ⚠️
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
This file has been DEPRECATED. Use instead:

    quality_scanner.py

The quality_scanner.py script provides comprehensive quality scanning
with better reporting and integration.

New Usage:
    python quality_scanner.py --all              # Scan all books
    python quality_scanner.py --book "BookName"  # Scan specific book

Or use the quality pipeline:
    from lib.quality_pipeline import QualityPipeline

    pipeline = QualityPipeline(fiction_dir)
    pipeline.run()

Migration Guide: See REFACTORING_COMPLETE_2026_02.md
Quick Start: See REFACTORING_QUICK_START.md
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Master Quality Scan Script
===========================
Runs all quality checks and fixers on the book library.

This script orchestrates:
1. Corruption detection and fixing
2. AI issues scanning
3. Quality scoring
4. Report generation

Usage:
    python run_quality_scan.py                    # Scan only
    python run_quality_scan.py --fix              # Scan and fix
    python run_quality_scan.py --book "BookName"  # Scan specific book
"""

import argparse
import json
import time
from pathlib import Path
from typing import Dict, List, Optional

# Import our fixers
from fixers.corruption_fixer import CorruptionFixer, CorruptionReport
from fixers.ai_issues_checker import AIIssuesChecker, AIIssuesWorker


def scan_for_corruption(fiction_dir: Path, fix: bool = False) -> Dict:
    """Run corruption scan on all books."""
    print("\n" + "=" * 70)
    print("PHASE 1: CORRUPTION DETECTION")
    print("=" * 70)

    fixer = CorruptionFixer()
    results = fixer.scan_all_books(fiction_dir)

    # Summary
    total_issues = sum(len(reports) for reports in results.values())
    critical_count = sum(
        1 for reports in results.values()
        for r in reports if r.severity == 'critical'
    )

    print(f"\nBooks with corruption: {len(results)}")
    print(f"Total corrupted chapters: {total_issues}")
    print(f"Critical issues: {critical_count}")

    if critical_count > 0:
        print("\nCritical corruptions found:")
        for book_name, reports in results.items():
            for report in reports:
                if report.severity == 'critical':
                    print(f"  - {book_name}: {report.corruption_type}")

    # Fix if requested
    if fix and results:
        print("\nFixing corrupted chapters...")
        fixed_count = 0
        for book_name, reports in results.items():
            for report in reports:
                if report.fixable:
                    chapter_path = Path(report.file_path)
                    fix_report = fixer.fix_chapter(chapter_path)
                    if fix_report.fixed:
                        fixed_count += 1
                        print(f"  Fixed: {chapter_path.name}")
        print(f"Fixed {fixed_count} chapters")

    return {
        'books_with_corruption': len(results),
        'total_corrupted_chapters': total_issues,
        'critical_issues': critical_count,
        'details': {
            book: [
                {
                    'file': r.file_path,
                    'type': r.corruption_type,
                    'severity': r.severity,
                    'fixable': r.fixable
                }
                for r in reports
            ]
            for book, reports in results.items()
        }
    }


def scan_for_ai_issues(fiction_dir: Path, max_workers: int = 4) -> Dict:
    """Run AI issues scan on all books."""
    print("\n" + "=" * 70)
    print("PHASE 2: AI LITERARY ISSUES DETECTION")
    print("=" * 70)

    worker = AIIssuesWorker(max_workers=max_workers)
    results = worker.scan_all_books(fiction_dir)

    # Print summary
    worker.print_summary(results)

    return results


def generate_prioritized_fix_list(
    corruption_results: Dict,
    ai_results: Dict
) -> List[Dict]:
    """
    Generate a prioritized list of books needing fixes.

    Priority order:
    1. Critical corruption (completely broken)
    2. Low AI score + high corruption
    3. Low AI score
    4. Medium issues
    """
    books_to_fix = []

    # Get all book names
    all_books = set(corruption_results.get('details', {}).keys())
    all_books.update(ai_results.keys())

    for book_name in all_books:
        corruption_info = corruption_results.get('details', {}).get(book_name, [])
        ai_info = ai_results.get(book_name, {})

        has_critical = any(c.get('severity') == 'critical' for c in corruption_info)
        has_high_corruption = any(c.get('severity') in ('critical', 'high') for c in corruption_info)
        ai_score = ai_info.get('average_score', 10)
        ai_issues = ai_info.get('total_issues', 0)

        # Calculate priority score (lower = more urgent)
        if has_critical:
            priority = 0
        elif has_high_corruption and ai_score < 6:
            priority = 1
        elif ai_score < 5:
            priority = 2
        elif ai_score < 7:
            priority = 3
        else:
            priority = 4

        books_to_fix.append({
            'book_name': book_name,
            'priority': priority,
            'ai_score': ai_score,
            'ai_issues': ai_issues,
            'has_corruption': len(corruption_info) > 0,
            'corruption_count': len(corruption_info),
            'critical_corruption': has_critical,
        })

    # Sort by priority, then by AI score
    books_to_fix.sort(key=lambda x: (x['priority'], x['ai_score']))

    return books_to_fix


def save_report(
    corruption_results: Dict,
    ai_results: Dict,
    fix_list: List[Dict],
    output_dir: Path
) -> None:
    """Save comprehensive quality report."""
    report = {
        'generated_at': time.strftime('%Y-%m-%d %H:%M:%S'),
        'summary': {
            'books_with_corruption': corruption_results.get('books_with_corruption', 0),
            'critical_corruptions': corruption_results.get('critical_issues', 0),
            'books_scanned_for_ai': len(ai_results),
            'books_needing_attention': len([b for b in fix_list if b['priority'] <= 2]),
        },
        'corruption_details': corruption_results.get('details', {}),
        'ai_issues_by_book': ai_results,
        'prioritized_fix_list': fix_list[:50],  # Top 50 to fix
    }

    report_path = output_dir / 'quality_scan_report.json'
    with open(report_path, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2)

    print(f"\nFull report saved to: {report_path}")

    # Also save a simple fix list
    fix_list_path = output_dir / 'books_to_fix.txt'
    with open(fix_list_path, 'w', encoding='utf-8') as f:
        f.write("BOOKS TO FIX (Priority Order)\n")
        f.write("=" * 50 + "\n\n")

        priority_names = {
            0: "CRITICAL - Completely broken",
            1: "HIGH - Corruption + Low quality",
            2: "HIGH - Very low AI quality",
            3: "MEDIUM - Below average quality",
            4: "LOW - Minor issues"
        }

        current_priority = -1
        for book in fix_list:
            if book['priority'] != current_priority:
                current_priority = book['priority']
                f.write(f"\n{priority_names.get(current_priority, 'Unknown')}:\n")
                f.write("-" * 40 + "\n")

            status = "BROKEN" if book['critical_corruption'] else f"{book['ai_score']:.1f}/10"
            f.write(f"  [{status}] {book['book_name']}\n")

    print(f"Fix list saved to: {fix_list_path}")


def main():
    parser = argparse.ArgumentParser(description='Run quality scan on book library')
    parser.add_argument('--fix', action='store_true', help='Fix issues automatically')
    parser.add_argument('--book', type=str, help='Scan specific book only')
    parser.add_argument('--workers', type=int, default=4, help='Number of parallel workers')
    parser.add_argument(
        '--fiction-dir',
        type=str,
        default='/mnt/e/projects/bookcli/output/fiction',
        help='Path to fiction directory'
    )
    args = parser.parse_args()

    fiction_dir = Path(args.fiction_dir)
    if not fiction_dir.exists():
        print(f"Error: Fiction directory not found: {fiction_dir}")
        return 1

    print("=" * 70)
    print("BOOKCLI QUALITY SCAN")
    print("=" * 70)
    print(f"Fiction Directory: {fiction_dir}")
    print(f"Mode: {'Scan and Fix' if args.fix else 'Scan Only'}")
    print(f"Workers: {args.workers}")

    if args.book:
        # Single book mode
        book_dir = fiction_dir / args.book
        if not book_dir.exists():
            print(f"Error: Book not found: {args.book}")
            return 1
        print(f"Scanning single book: {args.book}")
        # TODO: Implement single book scan
    else:
        # Full scan
        start_time = time.time()

        # Phase 1: Corruption
        corruption_results = scan_for_corruption(fiction_dir, fix=args.fix)

        # Phase 2: AI Issues
        ai_results = scan_for_ai_issues(fiction_dir, max_workers=args.workers)

        # Generate prioritized list
        fix_list = generate_prioritized_fix_list(corruption_results, ai_results)

        # Save reports
        save_report(corruption_results, ai_results, fix_list, fiction_dir.parent)

        elapsed = time.time() - start_time
        print(f"\n{'=' * 70}")
        print(f"SCAN COMPLETE - {elapsed:.1f} seconds")
        print(f"{'=' * 70}")

        # Summary
        critical_count = len([b for b in fix_list if b['priority'] == 0])
        high_count = len([b for b in fix_list if b['priority'] in (1, 2)])

        print(f"\nBooks requiring immediate attention:")
        print(f"  Critical (broken): {critical_count}")
        print(f"  High priority: {high_count}")

        if critical_count > 0:
            print("\nCRITICAL BOOKS (fix first):")
            for book in fix_list:
                if book['priority'] == 0:
                    print(f"  - {book['book_name']}")

    return 0


if __name__ == '__main__':
    exit(main())
