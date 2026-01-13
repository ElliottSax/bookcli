#!/usr/bin/env python3
"""
Cloud Book Fixer - Runs in GitHub Actions
"""

import os
import json
import time
import requests
from pathlib import Path

# API Keys from environment
APIS = [
    ("Groq", "https://api.groq.com/openai/v1/chat/completions",
     os.environ.get("GROQ_API_KEY"), "llama-3.3-70b-versatile"),
    ("Cerebras", "https://api.cerebras.ai/v1/chat/completions",
     os.environ.get("CEREBRAS_API_KEY"), "llama3.1-8b"),
    ("Together", "https://api.together.xyz/v1/chat/completions",
     os.environ.get("TOGETHER_KEY"), "meta-llama/Llama-3.3-70B-Instruct-Turbo"),
    ("Fireworks", "https://api.fireworks.ai/inference/v1/chat/completions",
     os.environ.get("FIREWORKS_API_KEY"), "accounts/fireworks/models/llama-v3p3-70b-instruct"),
    ("OpenRouter", "https://openrouter.ai/api/v1/chat/completions",
     os.environ.get("OPENROUTER_KEY"), "meta-llama/llama-3.2-3b-instruct:free"),
    ("DeepSeek", "https://api.deepseek.com/v1/chat/completions",
     os.environ.get("DEEPSEEK_API_KEY"), "deepseek-chat"),
]

_api_idx = int(os.environ.get("WORKER_ID", "1")) - 1

def call_api(prompt, max_tokens=4000):
    global _api_idx
    for i in range(len(APIS)):
        idx = (_api_idx + i) % len(APIS)
        name, url, key, model = APIS[idx]
        if not key:
            continue
        try:
            resp = requests.post(url,
                headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
                json={"model": model, "messages": [{"role": "user", "content": prompt}],
                      "max_tokens": max_tokens, "temperature": 0.7},
                timeout=120)
            if resp.status_code == 200:
                _api_idx = (idx + 1) % len(APIS)
                return resp.json()["choices"][0]["message"]["content"]
        except Exception as e:
            print(f"  {name} error: {e}")
    return None

def fix_book(book_dir):
    """Fix a single book."""
    bible_path = book_dir / "story_bible.json"
    if not bible_path.exists():
        return False

    with open(bible_path) as f:
        bible = json.load(f)

    if bible.get("quality_fixed"):
        return True  # Already done

    # Load chapters
    chapters = sorted(book_dir.glob("chapter_*.md"))
    if not chapters:
        return False

    print(f"Fixing: {book_dir.name}")

    # Simple quality check - expand short chapters
    for ch_path in chapters:
        content = ch_path.read_text()
        words = len(content.split())

        if words < 2000:
            print(f"  Expanding {ch_path.name} ({words} words)")
            prompt = f"""Expand this chapter to at least 2500 words while maintaining the story:

{content[:8000]}

Write the expanded chapter:"""

            result = call_api(prompt, max_tokens=4000)
            if result and len(result.split()) > words:
                ch_path.write_text(result)
                print(f"    Expanded to {len(result.split())} words")

    # Mark as fixed
    bible["quality_fixed"] = True
    with open(bible_path, "w") as f:
        json.dump(bible, f, indent=2)

    return True

def main():
    worker_id = int(os.environ.get("WORKER_ID", "1"))
    print(f"=== Cloud Book Fixer Worker {worker_id} ===")

    # Test API connectivity
    result = call_api("Say 'API OK' in 2 words")
    print(f"API test: {result}")

    if not result:
        print("ERROR: No working APIs!")
        return

    # Find books to fix
    output_dir = Path("output/fiction")
    if not output_dir.exists():
        print(f"No books found in {output_dir}")
        return

    books = sorted([d for d in output_dir.iterdir() if d.is_dir()])

    # Each worker takes every Nth book
    total_workers = int(os.environ.get("WORKER_COUNT", "5"))
    my_books = [b for i, b in enumerate(books) if i % total_workers == (worker_id - 1)]

    print(f"Processing {len(my_books)} books (of {len(books)} total)")

    for i, book in enumerate(my_books):
        print(f"[{i+1}/{len(my_books)}] {book.name}")
        try:
            fix_book(book)
        except Exception as e:
            print(f"  Error: {e}")
        time.sleep(1)  # Rate limit protection

if __name__ == "__main__":
    main()
