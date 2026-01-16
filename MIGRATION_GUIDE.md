# BookCLI Migration Guide

This guide explains how to migrate existing scripts to use the new centralized `lib/` modules.

## Overview

The refactoring introduced these new modules:

| Module | Purpose |
|--------|---------|
| `lib/config.py` | Centralized configuration (paths, API settings, quality thresholds) |
| `lib/logging_config.py` | Centralized logging with rotation |
| `lib/api_client.py` | Unified API client for all LLM providers |
| `lib/retry.py` | Retry, rate limiting, and circuit breaker utilities |
| `fixers/` | Modular fixer classes (TextFixer, NameFixer, QualityFixer) |

## Migration Steps

### 1. Replace Logging Setup

**Before:**
```python
import logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[logging.FileHandler('my_script.log'), logging.StreamHandler()])
logger = logging.getLogger(__name__)
```

**After:**
```python
from lib.logging_config import setup_logging, get_logger

setup_logging()  # Call once at module level
logger = get_logger(__name__)
```

### 2. Replace Hardcoded Paths

**Before:**
```python
FICTION_DIR = Path("/mnt/e/projects/bookcli/output/fiction")
```

**After:**
```python
from lib.config import get_config

config = get_config()
FICTION_DIR = config.paths.fiction_dir
```

### 3. Replace API Calls

**Before:**
```python
import os
import requests

DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY")

def call_deepseek(prompt: str, max_tokens: int = 2000) -> str:
    headers = {"Authorization": f"Bearer {DEEPSEEK_API_KEY}", "Content-Type": "application/json"}
    payload = {"model": "deepseek-chat", "messages": [{"role": "user", "content": prompt}], "max_tokens": max_tokens}
    response = requests.post("https://api.deepseek.com/chat/completions", headers=headers, json=payload, timeout=120)
    return response.json()["choices"][0]["message"]["content"]
```

**After:**
```python
from lib.api_client import call_llm

# Simple usage - automatically uses best available API
result = call_llm(prompt, max_tokens=2000)

# Or with more control
from lib.api_client import get_api_client

client = get_api_client()
response = client.call_api("deepseek", prompt, max_tokens=2000)
if response.success:
    result = response.content
```

### 4. Replace Magic Numbers

**Before:**
```python
if word_count < 2500:
    # expand chapter
```

**After:**
```python
from lib.config import get_config

config = get_config()
if word_count < config.quality.min_chapter_words:
    # expand chapter
```

### 5. Use Retry Utilities

**Before:**
```python
for attempt in range(3):
    try:
        result = api_call()
        break
    except Exception:
        time.sleep(2 ** attempt)
```

**After:**
```python
from lib.retry import retry_with_backoff

@retry_with_backoff(max_attempts=3, base_delay=1.0)
def api_call():
    return actual_api_call()
```

### 6. Use the New Fixer Classes

**Before (monolithic):**
```python
from book_fixer import BookFixer

fixer = BookFixer(book_dir)
fixer.run_full_fix()
```

**After (modular):**
```python
from fixers.base import BookContext, FixerPipeline
from fixers.text_fixer import TextFixer
from fixers.name_fixer import NameFixer
from fixers.quality_fixer import QualityFixer

context = BookContext(book_dir)
pipeline = FixerPipeline(context)
pipeline.add(TextFixer)
pipeline.add(NameFixer)
pipeline.add(QualityFixer)
total_fixes = pipeline.run()
```

Or use the convenience function:
```python
from fixers.base import process_book

fixes = process_book(book_dir, text_only=True)  # Only text fixes, no AI
```

## Complete Example

Here's a complete migration example:

**Before (`my_script.py`):**
```python
#!/usr/bin/env python3
import os, logging, time
from pathlib import Path

logging.basicConfig(level=logging.INFO, ...)
logger = logging.getLogger(__name__)

DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY")
FICTION_DIR = Path("/mnt/e/projects/bookcli/output/fiction")

def call_deepseek(prompt, max_tokens=2000):
    # 20 lines of API code...
    pass

def process_book(book_dir):
    # processing logic
    pass

def main():
    books = [d for d in FICTION_DIR.iterdir() if d.is_dir()]
    for book in books:
        process_book(book)
        time.sleep(2)

if __name__ == "__main__":
    main()
```

**After (`my_script.py`):**
```python
#!/usr/bin/env python3
import time
from pathlib import Path

from lib.logging_config import setup_logging, get_logger
from lib.config import get_config
from lib.api_client import call_llm

setup_logging()
logger = get_logger(__name__)
config = get_config()

def process_book(book_dir):
    # processing logic using call_llm()
    pass

def main():
    books = [d for d in config.paths.fiction_dir.iterdir() if d.is_dir()]
    for book in books:
        process_book(book)
        time.sleep(config.pipeline.delay_between_books)

if __name__ == "__main__":
    main()
```

## Files Already Migrated

- `dialogue_depth.py` ✓
- `show_dont_tell.py` ✓
- `book_fixer.py` ✓ (1247 → 835 lines, -33%)
- `autonomous_pipeline.py` ✓ (765 → 685 lines, -10%)
- `master_quality_pipeline.py` ✓ (693 → 657 lines, -5%)
- `scripts/continuous_generator.py` ✓

## Files to Migrate (Lower Priority)

Remaining scripts with API calls (lower impact):
- Other scripts in `scripts/` directory
- Any remaining files with direct API calls

## Testing After Migration

```bash
# Verify imports work
python3 -c "from lib.api_client import call_llm; print('OK')"

# Run unit tests (if pytest installed)
python3 -m pytest tests/unit/ -v

# Test a migrated script
python3 dialogue_depth.py --help
```

## Benefits After Migration

1. **Single source of truth** - All config in one place
2. **Automatic retries** - API calls retry on failure
3. **Rate limiting** - Prevents hitting API limits
4. **Circuit breaker** - Stops calling failing APIs
5. **Log rotation** - Logs don't grow unbounded
6. **Testability** - Easier to mock and test
7. **Maintainability** - Change API once, works everywhere
