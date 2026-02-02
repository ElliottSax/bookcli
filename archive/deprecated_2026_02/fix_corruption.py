#!/usr/bin/env python3
"""
⚠️  DEPRECATION NOTICE (2026-02-01) ⚠️
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
This file has been DEPRECATED and replaced by:

    fixers/corruption_fixer.py

The corruption detection and fixing logic is now part of the centralized
corruption fixer module. This standalone script is no longer maintained.

New Usage:
    from fixers.corruption_fixer import CorruptionFixer

    fixer = CorruptionFixer()
    fixed_content = fixer.fix(content)

Or use the quality pipeline:
    from lib.quality_pipeline import QualityPipeline

    pipeline = QualityPipeline(fiction_dir)
    pipeline.run()  # Runs all fixes including corruption

Migration Guide: See REFACTORING_COMPLETE_2026_02.md
Quick Start: See REFACTORING_QUICK_START.md
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Fix text corruption patterns in fiction books.
Handles patterns like:
- "sansweredaid" -> "she answered"
- "Watsansweredaid" -> "Watson answered"
- "seemed appeared to" -> "seemed to"
- "whisperedy" -> "whispered"
- "leng the ning" -> "lengthening"
"""
import re
import sys
from pathlib import Path
from datetime import datetime

def fix_corruption(text: str) -> tuple[str, int]:
    """Fix corruption patterns and return (fixed_text, count_of_fixes)."""
    fixes = 0
    original = text

    # Pattern 1: Name + "answered" merged ("Watsansweredaid" -> "Watson answered")
    patterns = [
        # Common name corruptions
        (r'\bWatsansweredaid\b', 'Watson answered'),
        (r'\bJensansweredaid\b', 'Jensen answered'),
        (r'\bprofessansweredaid\b', 'professor answered'),
        (r'\bsansweredaid\b', 'she answered'),
        (r'\bhansweredaid\b', 'he answered'),

        # Generic "answered" corruptions - capture name before
        (r'(\w+)answeredaid\b', r'\1 answered'),

        # "appeared to" corruptions
        (r'appeared tol(?:\'s)?\b', 'appeared to'),
        (r'seemed appeared to(\w+)', r'seemed to \1'),
        (r'seemed appeared ton\b', 'seemed to an'),
        (r'seemed appeared toim\b', 'seemed to him'),
        (r'seemed appeared toer\b', 'seemed to her'),
        (r'itappeared tol', 'it appeared to'),
        (r'appeared to appeared to', 'appeared to'),

        # Dialogue tag corruptions
        (r'\bwhisperedy\b', 'whispered'),
        (r'\bshoutedy\b', 'shouted'),
        (r'\bmurmeredy\b', 'murmured'),
        (r'\brepliedy\b', 'replied'),

        # Space corruptions
        (r'\bleng the ning\b', 'lengthening'),
        (r'\bwith out\b', 'without'),
        (r'\bcan not\b', 'cannot'),

        # Merged words with "said"
        (r'(\w+)saidaid\b', r'\1 said'),
        (r'\bcoaansweredaid\b', 'she answered'),

        # Double words
        (r'\b(\w+) \1\b', r'\1'),  # Remove exact duplicates

        # AI artifacts - meta commentary
        (r'This rewritten paragraph aims to[^.]+\.', ''),
        (r'This paragraph aims to[^.]+\.', ''),
    ]

    for pattern, replacement in patterns:
        text, count = re.subn(pattern, replacement, text, flags=re.IGNORECASE)
        fixes += count

    # Clean up extra whitespace
    text = re.sub(r'  +', ' ', text)
    text = re.sub(r'\n\n\n+', '\n\n', text)

    return text, fixes


def process_file(filepath: Path, dry_run: bool = False) -> int:
    """Process a single file. Returns number of fixes made."""
    try:
        content = filepath.read_text(encoding='utf-8')
        fixed, count = fix_corruption(content)

        if count > 0 and not dry_run:
            # Backup first
            backup_dir = filepath.parent / '.corruption_backups'
            backup_dir.mkdir(exist_ok=True)
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_path = backup_dir / f"{filepath.stem}_{timestamp}.backup"
            backup_path.write_text(content, encoding='utf-8')

            # Write fixed content
            filepath.write_text(fixed, encoding='utf-8')

        return count
    except Exception as e:
        print(f"Error processing {filepath}: {e}")
        return 0


def main():
    import argparse
    parser = argparse.ArgumentParser(description='Fix text corruption in fiction books')
    parser.add_argument('--fiction-dir', type=Path,
                       default=Path('/mnt/e/projects/bookcli/output/fiction'))
    parser.add_argument('--dry-run', action='store_true', help='Show what would be fixed without changing files')
    parser.add_argument('--book', type=str, help='Fix only specific book (directory name)')
    args = parser.parse_args()

    print("=" * 60)
    print("CORRUPTION FIXER")
    print("=" * 60)

    if args.dry_run:
        print("DRY RUN MODE - No files will be modified\n")

    # Find all chapter files
    if args.book:
        book_dir = args.fiction_dir / args.book
        if not book_dir.exists():
            print(f"Book not found: {args.book}")
            return
        chapter_files = list(book_dir.glob('chapter_*.md'))
    else:
        chapter_files = list(args.fiction_dir.glob('*/chapter_*.md'))

    print(f"Found {len(chapter_files)} chapter files\n")

    total_fixes = 0
    files_fixed = 0

    for i, filepath in enumerate(sorted(chapter_files)):
        fixes = process_file(filepath, args.dry_run)
        if fixes > 0:
            files_fixed += 1
            total_fixes += fixes
            book_name = filepath.parent.name
            print(f"Fixed {book_name}/{filepath.name}: {fixes} corrections")

    print("\n" + "=" * 60)
    print("COMPLETE")
    print("=" * 60)
    print(f"Files processed: {len(chapter_files)}")
    print(f"Files with fixes: {files_fixed}")
    print(f"Total corrections: {total_fixes}")


if __name__ == '__main__':
    main()
