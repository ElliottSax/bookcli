#!/usr/bin/env python3
"""
WORKER DASHBOARD
================

Real-time monitoring of all book generation systems:
- Fiction book status
- Cover generation progress
- API health and usage
- Task queue status
- Perpetual worker status
"""

import os
import json
import time
from pathlib import Path
from datetime import datetime


def get_fiction_status():
    """Get status of all fiction books."""
    fiction_dir = Path("/mnt/e/projects/bookcli/output/fiction")
    books = sorted([d for d in fiction_dir.iterdir() if d.is_dir() and not d.name.startswith('.')])

    stats = {
        "total_books": len(books),
        "with_covers": 0,
        "with_metadata": 0,
        "with_epub": 0,
        "total_chapters": 0,
        "total_words": 0,
        "missing_covers": [],
    }

    for book in books:
        chapters = list(book.glob("chapter_*.md"))
        stats["total_chapters"] += len(chapters)

        for ch in chapters:
            try:
                stats["total_words"] += len(ch.read_text().split())
            except (OSError, UnicodeDecodeError):
                pass

        if (book / "metadata.json").exists():
            stats["with_metadata"] += 1

        if list(book.glob("*.epub")):
            stats["with_epub"] += 1

        covers = list(book.glob("cover*.png")) + list(book.glob("cover*.jpg"))
        if covers:
            stats["with_covers"] += 1
        else:
            stats["missing_covers"].append(book.name)

    return stats


def get_api_status():
    """Check which APIs are configured."""
    # Import centralized API config (no hardcoded keys)
    from api_config import get_available_apis
    available = get_available_apis()
    apis = {
        "deepseek": available.get("DeepSeek", False),
        "groq": available.get("Groq", False),
        "hf": available.get("HuggingFace", False),
        "replicate": available.get("Replicate", False),
        "openrouter": available.get("OpenRouter", False),
        "together": available.get("Together AI", False),
    }
    return apis


def get_concept_counts():
    """Count available book concepts."""
    counts = {}

    try:
        from fiction_generator import (
            ROMANTASY_BOOKS, DARK_ROMANCE_BOOKS, COZY_MYSTERY_BOOKS,
            THRILLER_BOOKS, URBAN_FANTASY_BOOKS, GOTHIC_HORROR_BOOKS,
            PUBLIC_DOMAIN_REIMAGININGS, ALL_FICTION_BOOKS
        )
        counts["fiction_generator"] = len(ALL_FICTION_BOOKS)
    except ImportError:
        counts["fiction_generator"] = 0

    try:
        from bom_reimaginings import BOOK_OF_MORMON_REIMAGININGS
        counts["bom_reimaginings"] = len(BOOK_OF_MORMON_REIMAGININGS)
    except ImportError:
        counts["bom_reimaginings"] = 0

    try:
        from new_book_concepts import ALL_NEW_CONCEPTS
        counts["new_concepts"] = len(ALL_NEW_CONCEPTS)
    except ImportError:
        counts["new_concepts"] = 0

    return counts


def print_dashboard():
    """Print the dashboard."""
    print("\n" + "=" * 70)
    print("                    BOOKCLI WORKER DASHBOARD")
    print("                    " + datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    print("=" * 70)

    # Fiction Status
    stats = get_fiction_status()
    print("\n📚 FICTION BOOKS STATUS")
    print("-" * 40)
    print(f"  Total books:      {stats['total_books']}")
    print(f"  With covers:      {stats['with_covers']} ({100*stats['with_covers']//max(1,stats['total_books'])}%)")
    print(f"  With metadata:    {stats['with_metadata']}")
    print(f"  With EPUB:        {stats['with_epub']}")
    print(f"  Total chapters:   {stats['total_chapters']}")
    print(f"  Total words:      {stats['total_words']:,}")
    print(f"  Avg words/book:   {stats['total_words']//max(1,stats['total_books']):,}")

    if stats["missing_covers"]:
        print(f"\n  Missing covers ({len(stats['missing_covers'])}):")
        for book in stats["missing_covers"][:5]:
            print(f"    - {book}")
        if len(stats["missing_covers"]) > 5:
            print(f"    ... and {len(stats['missing_covers']) - 5} more")

    # API Status
    apis = get_api_status()
    print("\n🔌 API STATUS")
    print("-" * 40)
    for api, available in apis.items():
        status = "✓ Available" if available else "✗ Not configured"
        print(f"  {api:15} {status}")

    # Concept Counts
    concepts = get_concept_counts()
    print("\n📝 BOOK CONCEPTS AVAILABLE")
    print("-" * 40)
    total = 0
    for source, count in concepts.items():
        print(f"  {source:20} {count}")
        total += count
    print(f"  {'TOTAL':20} {total}")

    # Check for running processes
    print("\n⚡ WORKER STATUS")
    print("-" * 40)

    log_files = [
        ("perpetual_ultra.log", "Perpetual Ultra Worker"),
        ("multi_api.log", "Multi-API Worker"),
        ("parallel_completion.log", "Parallel Completion"),
    ]

    for log_file, name in log_files:
        log_path = Path(f"/mnt/e/projects/bookcli/{log_file}")
        if log_path.exists():
            try:
                mtime = datetime.fromtimestamp(log_path.stat().st_mtime)
                age = (datetime.now() - mtime).total_seconds()
                if age < 300:  # Active in last 5 minutes
                    status = "🟢 ACTIVE"
                elif age < 3600:
                    status = "🟡 IDLE"
                else:
                    status = "🔴 STOPPED"
                print(f"  {name:25} {status} (last: {mtime.strftime('%H:%M:%S')})")
            except:
                print(f"  {name:25} ❓ Unknown")
        else:
            print(f"  {name:25} ❌ No log")

    print("\n" + "=" * 70)


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Worker Dashboard")
    parser.add_argument("--watch", "-w", action="store_true", help="Watch mode (refresh every 30s)")
    args = parser.parse_args()

    if args.watch:
        try:
            while True:
                os.system('clear' if os.name == 'posix' else 'cls')
                print_dashboard()
                print("\nPress Ctrl+C to exit. Refreshing in 30s...")
                time.sleep(30)
        except KeyboardInterrupt:
            print("\nExiting...")
    else:
        print_dashboard()


if __name__ == "__main__":
    main()
