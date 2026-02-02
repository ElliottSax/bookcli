# Refactoring Quick Start Guide

**For Developers Using the Refactored Code**

---

## 🚀 Quick Start

### New Modules Available

Three new consolidated modules are now available:

1. **`lib/quality_pipeline.py`** - Consolidated quality pipeline (3 modes)
2. **`lib/book_utils.py`** - Common book operations
3. **`lib/fix_utils.py`** - Fix validation utilities

---

## 📖 Usage Examples

### 1. Quality Pipeline

**Run quality fixes on books:**

```python
from lib.quality_pipeline import QualityPipeline
from pathlib import Path

fiction_dir = Path("/path/to/fiction")
pipeline = QualityPipeline(fiction_dir)
pipeline.run()
```

**With Oracle Cloud sync:**

```python
from lib.quality_pipeline import DistributedPipeline

pipeline = DistributedPipeline(
    fiction_dir,
    oracle_host="user@oracle.host",
    sync_before=True,
    sync_after=False
)
pipeline.run()
```

**Parallel batch processing:**

```python
from lib.quality_pipeline import BatchPipeline

pipeline = BatchPipeline(
    fiction_dir,
    max_workers=4,
    enable_backup=True
)
pipeline.run()
```

---

### 2. Book Utilities

**Iterate through books:**

```python
from lib.book_utils import iterate_books

for book in iterate_books(fiction_dir, min_chapters=5):
    print(f"{book.name}: {book.chapter_count} chapters")

    # Access chapters
    for chapter_file in book.chapters:
        content = chapter_file.read_text()
        # ... process content
```

**Load a specific book:**

```python
from lib.book_utils import load_book

book = load_book(book_dir)
if book:
    # Load and modify chapter
    content = book.load_chapter(0)
    modified = process_content(content)
    book.save_chapter(0, modified)

    # Access bible
    bible = book.load_bible()
```

**Validate book structure:**

```python
from lib.book_utils import validate_book_structure

is_valid, issues = validate_book_structure(book_dir)
if not is_valid:
    print(f"Issues found: {issues}")
```

**Get book statistics:**

```python
from lib.book_utils import get_book_stats

stats = get_book_stats(book)
print(f"Total words: {stats['total_words']:,}")
print(f"Average per chapter: {stats['avg_words_per_chapter']:.0f}")
```

---

### 3. Fix Validation

**Validate a single fix:**

```python
from lib.fix_utils import validate_fix

original = chapter_file.read_text()
fixed = apply_some_fix(original)

result = validate_fix(original, fixed, chapter_file)

if result.success:
    print(f"Improvement: {result.delta:.1f} points")
    chapter_file.write_text(result.fixed_content)
else:
    print("No improvement detected")
```

**Batch validation:**

```python
from lib.fix_utils import batch_validate_fixes, get_fix_summary

fixes = {}
for chapter_file in book.chapters:
    original = chapter_file.read_text()
    fixed = apply_fix(original)
    fixes[chapter_file] = (original, fixed)

results = batch_validate_fixes(fixes, min_improvement=2.0)
summary = get_fix_summary(results)

print(f"Improved: {summary['improved_count']}/{summary['total_files']}")
print(f"Average improvement: {summary['average_delta']:.1f} points")
```

**Auto-apply validated fixes:**

```python
from lib.fix_utils import validate_chapter_fix

original = chapter_file.read_text()
fixed = apply_fix(original)

# Automatically write if improvement detected
applied = validate_chapter_fix(
    chapter_file,
    original,
    fixed,
    auto_apply=True  # Write if improved
)

if applied:
    print(f"✓ Fix applied to {chapter_file.name}")
```

---

## 🔄 Migration Patterns

### Pattern 1: Book Iteration

**Before (duplicated 30+ times):**
```python
for book_dir in fiction_dir.iterdir():
    if not book_dir.is_dir():
        continue
    if book_dir.name.startswith('.'):
        continue
    chapters = sorted(book_dir.glob("chapter_*.md"))
    if len(chapters) < 5:
        continue
    # ... process book
```

**After (use once):**
```python
from lib.book_utils import iterate_books

for book in iterate_books(fiction_dir, min_chapters=5):
    # book.chapters already loaded
    # book.bible_file available
    # book.metadata loaded
    # ... process book
```

---

### Pattern 2: Fix Validation

**Before (duplicated 15+ times):**
```python
from lib.quality_scorer import QualityScorer

scorer = QualityScorer()
original = chapter_file.read_text()

score_before = scorer.analyze(original).score
fixed = apply_fix(original)
score_after = scorer.analyze(fixed).score

if score_after > score_before:
    chapter_file.write_text(fixed)
    print(f"Improved: {score_before} → {score_after}")
```

**After (use once):**
```python
from lib.fix_utils import validate_fix

original = chapter_file.read_text()
fixed = apply_fix(original)

result = validate_fix(original, fixed, chapter_file)

if result.success:
    chapter_file.write_text(result.fixed_content)
    print(f"Improved: {result.score_before:.1f} → {result.score_after:.1f}")
```

---

### Pattern 3: Quality Pipeline

**Before (3 different implementations):**
```python
# Option 1
from master_quality_pipeline import run_pipeline
run_pipeline()

# Option 2
from unified_quality_pipeline import process_books
process_books()

# Option 3
from lib.quality_pipeline_manager import QualityPipelineManager
manager = QualityPipelineManager()
manager.run()
```

**After (one consistent API):**
```python
from lib.quality_pipeline import QualityPipeline, DistributedPipeline, BatchPipeline

# Local mode
pipeline = QualityPipeline(fiction_dir)
pipeline.run()

# Or distributed
pipeline = DistributedPipeline(fiction_dir, oracle_host="...")
pipeline.run()

# Or batch
pipeline = BatchPipeline(fiction_dir, max_workers=4)
pipeline.run()
```

---

## ⚡ Quick Tips

### 1. Always Filter Books

```python
# Good - filter during iteration
for book in iterate_books(fiction_dir, min_chapters=5):
    # Only processes books with 5+ chapters
    process(book)

# Better - filter by multiple criteria
for book in iterate_books(
    fiction_dir,
    min_chapters=5,
    max_chapters=15,
    require_bible=True
):
    process(book)
```

### 2. Use BookInfo Properties

```python
book = load_book(book_dir)

# Use properties
print(f"Chapters: {book.chapter_count}")
print(f"Has bible: {book.bible_file is not None}")

# Use methods
bible_content = book.load_bible()
chapter_content = book.load_chapter(0)
```

### 3. Check Fix Results

```python
result = validate_fix(original, fixed)

# Check success
if result.success:
    print("Improvement detected!")

# Access metrics
print(f"Delta: {result.delta:.1f}")
print(f"Issues fixed: {len(result.issues_fixed)}")
print(f"Metrics: {result.metrics}")
```

### 4. Use Batch Operations

```python
# Instead of validating one at a time
for chapter in chapters:
    result = validate_fix(...)  # Slow

# Validate in batch
fixes = {ch: (orig, fixed) for ch in chapters}
results = batch_validate_fixes(fixes)  # Faster + summary stats
```

---

## 🐛 Common Issues

### Import Error

**Problem:**
```python
ModuleNotFoundError: No module named 'lib'
```

**Solution:**
```bash
# Run from project root
cd /path/to/bookcli
python your_script.py

# Or set PYTHONPATH
PYTHONPATH=/path/to/bookcli python your_script.py
```

### No Books Found

**Problem:**
```python
for book in iterate_books(fiction_dir):
    # Never executes
```

**Solution:**
```python
# Check path
print(f"Fiction dir exists: {fiction_dir.exists()}")

# Check filtering
for book in iterate_books(fiction_dir, min_chapters=0):
    # Looser filter
```

### Fix Not Applied

**Problem:**
```python
result = validate_fix(original, fixed)
# result.success is False
```

**Solution:**
```python
# Check if actually improved
print(f"Before: {result.score_before}")
print(f"After: {result.score_after}")
print(f"Delta: {result.delta}")

# Lower threshold if needed
if result.delta > 0.5:  # Any small improvement
    apply_fix()
```

---

## 📚 Full API Reference

### QualityPipeline

```python
class QualityPipeline:
    def __init__(self, fiction_dir, mode="local",
                 enable_backup=True, parallel=False)

    def run()  # Main entry point
    def get_books() -> List[Path]
    def process_book(book_dir) -> bool
    def validate_quality(book_dir) -> Tuple[float, Dict]
```

### Book Utilities

```python
def iterate_books(fiction_dir, min_chapters=0, max_chapters=None,
                  require_bible=False, skip_hidden=True) -> Iterator[BookInfo]

def load_book(book_dir) -> Optional[BookInfo]

def validate_book_structure(book_dir) -> Tuple[bool, List[str]]

def get_book_stats(book) -> Dict

def count_books(fiction_dir, **kwargs) -> int

def find_book(fiction_dir, book_name) -> Optional[BookInfo]
```

### Fix Utilities

```python
def validate_fix(original, fixed, chapter_file=None) -> FixResult

def should_apply_fix(result, min_improvement=0.0) -> bool

def validate_chapter_fix(chapter_file, original, fixed,
                        auto_apply=False) -> bool

def batch_validate_fixes(fixes, min_improvement=1.0) -> Dict[Path, FixResult]

def get_fix_summary(results) -> Dict
```

---

## ✅ Testing Your Code

### Test with Demo Scripts

```bash
# Test book utilities
PYTHONPATH=/path/to/bookcli python lib/book_utils.py

# Test fix utilities
PYTHONPATH=/path/to/bookcli python lib/fix_utils.py

# Test quality pipeline
PYTHONPATH=/path/to/bookcli python -m lib.quality_pipeline --mode local
```

### Verify Integration

```python
# In your script
from lib.book_utils import iterate_books
from lib.fix_utils import validate_fix
from lib.quality_pipeline import QualityPipeline

# All imports should work without errors
print("✓ All modules imported successfully")
```

---

## 🆘 Getting Help

### Documentation Files

- **`CODE_REVIEW_SUMMARY_2026_02.md`** - Detailed analysis
- **`REFACTORING_COMPLETE_2026_02.md`** - Full implementation guide
- **`REFACTORING_FINAL_SUMMARY.md`** - Executive summary
- **`REFACTORING_QUICK_START.md`** - This file

### Module Docstrings

```python
# View module documentation
help(QualityPipeline)
help(iterate_books)
help(validate_fix)
```

### Demo Scripts

All modules include demo scripts:
```bash
python lib/book_utils.py        # Book utils demo
python lib/fix_utils.py          # Fix utils demo
python -m lib.quality_pipeline   # Pipeline demo
```

---

**Quick Start Version:** 1.0
**Date:** 2026-02-01
**Status:** ✅ Ready to Use

**Remember:** All changes are backwards compatible. Old code still works while you migrate!
