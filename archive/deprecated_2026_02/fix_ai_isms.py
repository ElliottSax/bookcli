#!/usr/bin/env python3
"""
⚠️  DEPRECATION NOTICE (2026-02-01) ⚠️
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
This file has been DEPRECATED and replaced by:

    fixers/quality_fixer.py

The AI-ism removal logic is now part of the centralized quality fixer.
This standalone script is no longer maintained.

New Usage:
    from fixers.quality_fixer import QualityFixer

    fixer = QualityFixer()
    fixed_content = fixer.fix(content)  # Includes AI-ism removal

Or use the quality pipeline:
    from lib.quality_pipeline import QualityPipeline

    pipeline = QualityPipeline(fiction_dir)
    pipeline.run()  # Runs all fixes including AI-isms

Migration Guide: See REFACTORING_COMPLETE_2026_02.md
Quick Start: See REFACTORING_QUICK_START.md
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Fix common AI-isms and improve prose quality.
Targets: delve, tapestry, couldn't help but, filter words, etc.
"""
import re
import sys
import random
from pathlib import Path
from datetime import datetime

# Replacements for common AI phrases
AI_PHRASE_REPLACEMENTS = {
    # "delve" alternatives
    r'\bdelve(?:d|s|ing)? into\b': [
        'explore', 'examine', 'investigate', 'dig into', 'look into', 'study'
    ],
    r'\bdelve(?:d|s)?\b': ['explore', 'examine', 'investigate', 'dig', 'probe'],

    # "tapestry" alternatives (when used metaphorically)
    r'a tapestry of\b': ['a mix of', 'a blend of', 'layers of', 'a weave of'],
    r'rich tapestry\b': ['complex mix', 'intricate blend', 'layered'],

    # "embark on a journey"
    r'\bembark(?:ed|s|ing)? on (?:a |this |their )?journey\b': [
        'begin', 'start', 'set out', 'undertake'
    ],

    # "couldn't help but"
    r"couldn't help but\b": ['had to', 'found herself', 'inevitably'],
    r"could not help but\b": ['had to', 'found himself', 'inevitably'],

    # "a testament to"
    r'\ba testament to\b': ['proof of', 'evidence of', 'showed'],

    # "it's worth noting"
    r"it'?s worth noting that?\b": ['notably,', 'importantly,', ''],

    # Overused qualifiers
    r'\bvery unique\b': ['unique', 'distinctive', 'singular'],
    r'\bcompletely destroyed\b': ['destroyed', 'ruined', 'demolished'],
    r'\babsolutely essential\b': ['essential', 'critical', 'vital'],
}

# Filter words to reduce (not eliminate - some are fine)
FILTER_WORD_PATTERNS = [
    # "felt" - often can be shown instead
    (r'(\w+) felt (a |the )?(sense of |feeling of )?(\w+)', r'\1 \4'),

    # "seemed to" - often unnecessary
    (r'seemed to be\b', 'was'),
    (r'appeared to be\b', 'was'),

    # "began to" / "started to" - usually just use the verb
    (r'\bbegan to (\w+)', r'\1'),
    (r'\bstarted to (\w+)', r'\1'),

    # "suddenly" - usually unnecessary
    (r'\bSuddenly, ', ''),
    (r'\bsuddenly ', ''),
]


def fix_ai_isms(text: str) -> tuple[str, int]:
    """Fix AI-isms and return (fixed_text, count_of_fixes)."""
    fixes = 0

    # Replace AI phrases with alternatives
    for pattern, replacements in AI_PHRASE_REPLACEMENTS.items():
        matches = list(re.finditer(pattern, text, re.IGNORECASE))
        for match in reversed(matches):  # Reverse to maintain positions
            replacement = random.choice(replacements) if isinstance(replacements, list) else replacements
            # Preserve case of first letter
            if match.group()[0].isupper():
                replacement = replacement.capitalize()
            text = text[:match.start()] + replacement + text[match.end():]
            fixes += 1

    # Apply filter word reductions (more conservatively)
    for pattern, replacement in FILTER_WORD_PATTERNS:
        text, count = re.subn(pattern, replacement, text)
        fixes += count

    return text, fixes


def process_file(filepath: Path, dry_run: bool = False) -> int:
    """Process a single file. Returns number of fixes made."""
    try:
        content = filepath.read_text(encoding='utf-8')
        fixed, count = fix_ai_isms(content)

        if count > 0 and not dry_run:
            # Backup first
            backup_dir = filepath.parent / '.ai_ism_backups'
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
    parser = argparse.ArgumentParser(description='Fix AI-isms in fiction books')
    parser.add_argument('--fiction-dir', type=Path,
                       default=Path('/mnt/e/projects/bookcli/output/fiction'))
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('--book', type=str, help='Fix only specific book')
    args = parser.parse_args()

    print("=" * 60)
    print("AI-ISM FIXER")
    print("=" * 60)

    if args.dry_run:
        print("DRY RUN MODE\n")

    # Find chapter files
    if args.book:
        book_dir = args.fiction_dir / args.book
        chapter_files = list(book_dir.glob('chapter_*.md'))
    else:
        chapter_files = list(args.fiction_dir.glob('*/chapter_*.md'))

    print(f"Found {len(chapter_files)} chapter files\n")

    total_fixes = 0
    files_fixed = 0

    for filepath in sorted(chapter_files):
        fixes = process_file(filepath, args.dry_run)
        if fixes > 0:
            files_fixed += 1
            total_fixes += fixes
            if fixes >= 3:  # Only report files with significant changes
                print(f"Fixed {filepath.parent.name}/{filepath.name}: {fixes} AI-isms")

    print("\n" + "=" * 60)
    print("COMPLETE")
    print("=" * 60)
    print(f"Files with fixes: {files_fixed}")
    print(f"Total AI-isms fixed: {total_fixes}")


if __name__ == '__main__':
    main()
