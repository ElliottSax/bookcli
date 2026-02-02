#!/usr/bin/env python3
"""
Quality Pipeline Manager - Efficiently manages AI quality fixes across all books.

Features:
- Tracks which books have been processed
- Prevents redundant processing
- Batch processing with progress tracking
- Detailed reporting
- Resume capability
"""

import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Set
from dataclasses import dataclass, asdict
import hashlib

from ai_quality_detector import AIQualityDetector, analyze_chapter_file
from ai_quality_fixer import AIQualityFixer, fix_chapter_file, fix_book_directory


@dataclass
class BookProcessingRecord:
    """Record of a book's processing status."""
    book_name: str
    processed_at: str
    quality_score: int
    issues_found: int
    fixes_applied: int
    chapters_fixed: int
    total_chapters: int
    content_hash: str
    needs_reprocessing: bool = False


class QualityPipelineManager:
    """Manages the quality fixing pipeline across all books."""

    def __init__(self, fiction_dir: Path, state_file: Path = None):
        self.fiction_dir = Path(fiction_dir)
        self.state_file = state_file or self.fiction_dir / '.quality_pipeline_state.json'
        self.state: Dict[str, BookProcessingRecord] = {}
        self.load_state()

    def load_state(self):
        """Load processing state from disk."""
        if self.state_file.exists():
            try:
                data = json.loads(self.state_file.read_text())
                self.state = {
                    name: BookProcessingRecord(**record)
                    for name, record in data.items()
                }
                print(f"Loaded state: {len(self.state)} books previously processed")
            except Exception as e:
                print(f"Warning: Could not load state: {e}")
                self.state = {}

    def save_state(self):
        """Save processing state to disk."""
        data = {
            name: asdict(record)
            for name, record in self.state.items()
        }
        self.state_file.write_text(json.dumps(data, indent=2))

    def get_content_hash(self, book_path: Path) -> str:
        """Calculate hash of all chapter contents to detect changes."""
        hasher = hashlib.sha256()
        chapters = sorted(book_path.glob('chapter_*.md'))

        for chapter in chapters:
            try:
                content = chapter.read_text(encoding='utf-8')
                hasher.update(content.encode('utf-8'))
            except Exception:
                pass

        return hasher.hexdigest()

    def should_process_book(self, book_path: Path, force: bool = False) -> bool:
        """Determine if a book needs processing."""
        book_name = book_path.name

        # Force reprocessing if requested
        if force:
            return True

        # Not processed before
        if book_name not in self.state:
            return True

        record = self.state[book_name]

        # Marked for reprocessing
        if record.needs_reprocessing:
            return True

        # Content has changed since last processing
        current_hash = self.get_content_hash(book_path)
        if current_hash != record.content_hash:
            print(f"  {book_name}: Content changed since last processing")
            return True

        # Already processed and unchanged
        return False

    def process_book(self, book_path: Path, fix: bool = True) -> Dict:
        """Process a single book: detect issues and optionally fix."""
        book_name = book_path.name
        chapters = sorted(book_path.glob('chapter_*.md'))

        result = {
            'book': book_name,
            'status': 'processed',
            'chapters': len(chapters),
            'total_issues': 0,
            'total_fixes': 0,
            'chapters_fixed': 0,
            'quality_scores': [],
            'critical_issues': [],
        }

        detector = AIQualityDetector()

        # Detect issues in all chapters
        for chapter in chapters:
            try:
                issues, report = analyze_chapter_file(str(chapter))

                result['total_issues'] += report['total_issues']
                result['quality_scores'].append(report['quality_score'])

                # Collect critical issues
                for fix_needed in report.get('critical_fixes_needed', []):
                    result['critical_issues'].append({
                        'chapter': chapter.name,
                        'type': fix_needed['type'],
                        'message': fix_needed['message']
                    })

            except Exception as e:
                print(f"    Error analyzing {chapter.name}: {e}")

        # Calculate average quality score
        avg_score = sum(result['quality_scores']) / len(result['quality_scores']) if result['quality_scores'] else 0
        result['avg_quality_score'] = int(avg_score)

        # Apply fixes if requested and issues found
        if fix and result['total_issues'] > 0:
            print(f"  Applying fixes to {book_name}...")
            fix_result = fix_book_directory(book_path, backup=True)
            result['total_fixes'] = fix_result['total_fixes']
            result['chapters_fixed'] = fix_result['chapters_fixed']
            result['fix_details'] = fix_result

        # Update state
        self.state[book_name] = BookProcessingRecord(
            book_name=book_name,
            processed_at=datetime.now().isoformat(),
            quality_score=result['avg_quality_score'],
            issues_found=result['total_issues'],
            fixes_applied=result['total_fixes'],
            chapters_fixed=result['chapters_fixed'],
            total_chapters=len(chapters),
            content_hash=self.get_content_hash(book_path),
            needs_reprocessing=False
        )
        self.save_state()

        return result

    def process_all_books(self, fix: bool = True, force: bool = False,
                         limit: Optional[int] = None) -> Dict:
        """Process all books in the fiction directory."""
        all_books = [
            d for d in self.fiction_dir.iterdir()
            if d.is_dir() and not d.name.startswith('.')
        ]

        # Filter to only books that need processing
        books_to_process = [
            book for book in all_books
            if self.should_process_book(book, force=force)
        ]

        if limit:
            books_to_process = books_to_process[:limit]

        summary = {
            'total_books': len(all_books),
            'books_processed': 0,
            'books_fixed': 0,
            'total_issues_found': 0,
            'total_fixes_applied': 0,
            'books_skipped': len(all_books) - len(books_to_process),
            'processing_results': [],
            'critical_books': [],
            'started_at': datetime.now().isoformat(),
        }

        print(f"\n{'='*70}")
        print(f"QUALITY PIPELINE PROCESSING")
        print(f"{'='*70}")
        print(f"Total books: {len(all_books)}")
        print(f"Already processed: {len(all_books) - len(books_to_process)}")
        print(f"To process: {len(books_to_process)}")
        print(f"Fix mode: {'ON' if fix else 'DETECT ONLY'}")
        print(f"{'='*70}\n")

        for i, book_path in enumerate(books_to_process, 1):
            print(f"[{i}/{len(books_to_process)}] Processing: {book_path.name}")

            try:
                result = self.process_book(book_path, fix=fix)
                summary['books_processed'] += 1
                summary['total_issues_found'] += result['total_issues']
                summary['total_fixes_applied'] += result['total_fixes']

                if result['chapters_fixed'] > 0:
                    summary['books_fixed'] += 1

                summary['processing_results'].append(result)

                # Track critical books (low quality score or many issues)
                if result['avg_quality_score'] < 50 or result['total_issues'] > 20:
                    summary['critical_books'].append({
                        'name': book_path.name,
                        'score': result['avg_quality_score'],
                        'issues': result['total_issues'],
                        'critical_issue_count': len(result['critical_issues'])
                    })

                # Print summary
                print(f"    Score: {result['avg_quality_score']}/100 | "
                      f"Issues: {result['total_issues']} | "
                      f"Fixed: {result['total_fixes']}")

            except Exception as e:
                print(f"    ERROR: {e}")
                summary['processing_results'].append({
                    'book': book_path.name,
                    'status': 'error',
                    'error': str(e)
                })

        summary['completed_at'] = datetime.now().isoformat()

        # Save summary report
        report_file = self.fiction_dir.parent / 'quality_pipeline_report.json'
        report_file.write_text(json.dumps(summary, indent=2, default=str))
        print(f"\nFull report saved to: {report_file}")

        return summary

    def get_statistics(self) -> Dict:
        """Get statistics on processed books."""
        if not self.state:
            return {'message': 'No books processed yet'}

        scores = [record.quality_score for record in self.state.values()]
        total_issues = sum(record.issues_found for record in self.state.values())
        total_fixes = sum(record.fixes_applied for record in self.state.values())

        return {
            'total_processed': len(self.state),
            'average_quality_score': sum(scores) / len(scores) if scores else 0,
            'min_quality_score': min(scores) if scores else 0,
            'max_quality_score': max(scores) if scores else 0,
            'total_issues_found': total_issues,
            'total_fixes_applied': total_fixes,
            'books_needing_attention': [
                {'name': record.book_name, 'score': record.quality_score}
                for record in self.state.values()
                if record.quality_score < 60
            ]
        }

    def mark_for_reprocessing(self, book_names: List[str] = None):
        """Mark books for reprocessing."""
        if book_names is None:
            # Mark all
            for record in self.state.values():
                record.needs_reprocessing = True
        else:
            for name in book_names:
                if name in self.state:
                    self.state[name].needs_reprocessing = True

        self.save_state()

    def print_summary(self, summary: Dict):
        """Print a formatted summary of processing."""
        print(f"\n{'='*70}")
        print("QUALITY PIPELINE SUMMARY")
        print(f"{'='*70}\n")

        print(f"Books processed: {summary['books_processed']}/{summary['total_books']}")
        print(f"Books fixed: {summary['books_fixed']}")
        print(f"Books skipped (already processed): {summary['books_skipped']}")
        print(f"Total issues found: {summary['total_issues_found']}")
        print(f"Total fixes applied: {summary['total_fixes_applied']}")

        if summary['critical_books']:
            print(f"\nBOOKS NEEDING ATTENTION ({len(summary['critical_books'])}):")
            for book in sorted(summary['critical_books'], key=lambda x: x['score'])[:10]:
                print(f"  ⚠ {book['name']}: Score {book['score']}/100, "
                      f"{book['issues']} issues, "
                      f"{book['critical_issue_count']} critical")

        print(f"\n{'='*70}")


def main():
    import argparse

    parser = argparse.ArgumentParser(description='AI Quality Pipeline Manager')
    parser.add_argument('--fiction-dir', default='output/fiction',
                       help='Fiction directory path')
    parser.add_argument('--detect-only', action='store_true',
                       help='Only detect issues, do not fix')
    parser.add_argument('--force', action='store_true',
                       help='Force reprocessing of all books')
    parser.add_argument('--limit', type=int,
                       help='Limit number of books to process')
    parser.add_argument('--stats', action='store_true',
                       help='Show statistics and exit')
    parser.add_argument('--mark-reprocess', nargs='*',
                       help='Mark books for reprocessing')

    args = parser.parse_args()

    manager = QualityPipelineManager(Path(args.fiction_dir))

    if args.stats:
        stats = manager.get_statistics()
        print(json.dumps(stats, indent=2))
        return

    if args.mark_reprocess is not None:
        manager.mark_for_reprocessing(args.mark_reprocess if args.mark_reprocess else None)
        print("Books marked for reprocessing")
        return

    # Process books
    summary = manager.process_all_books(
        fix=not args.detect_only,
        force=args.force,
        limit=args.limit
    )

    manager.print_summary(summary)


if __name__ == "__main__":
    main()
