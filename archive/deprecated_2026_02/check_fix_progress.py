#!/usr/bin/env python3
"""
⚠️  DEPRECATION NOTICE (2026-02-01) ⚠️
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
This file has been DEPRECATED.

Progress tracking is now integrated into:
    - lib/quality_pipeline.py (built-in progress tracking)
    - lib/checkpoint.py (checkpoint manager for recovery)

Migration Guide: See REFACTORING_COMPLETE_2026_02.md
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Check progress of the book fixing process.
"""

import json
from pathlib import Path

output_dir = Path("output/fiction")
broken_file = Path("output/broken_books_final.json")

# Load broken books list
broken_books = json.loads(broken_file.read_text())
broken_names = {b["book"] for b in broken_books}

# Count fixed books
fixed = 0
for book_name in broken_names:
    book_path = output_dir / book_name
    if (book_path / ".loop_fixed").exists():
        fixed += 1

print(f"Progress: {fixed}/{len(broken_books)} books fixed ({100*fixed/len(broken_books):.1f}%)")
print(f"Remaining: {len(broken_books) - fixed} books")
