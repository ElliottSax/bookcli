#!/usr/bin/env python3
"""
Cloud Worker - Connects to book server and fixes books
Run this on Google Colab, Kaggle, Replit, etc.

Usage:
  python cloud_worker.py https://YOUR-TUNNEL-URL.trycloudflare.com
"""

import sys
import requests
import json
import time
import random

# API Keys - SET THESE BEFORE RUNNING
# Get free keys from: groq.com, together.ai, fireworks.ai, cerebras.ai, openrouter.ai, deepseek.com
import os
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "YOUR_GROQ_KEY")
TOGETHER_KEY = os.environ.get("TOGETHER_KEY", "YOUR_TOGETHER_KEY")
FIREWORKS_API_KEY = os.environ.get("FIREWORKS_API_KEY", "YOUR_FIREWORKS_KEY")
CEREBRAS_API_KEY = os.environ.get("CEREBRAS_API_KEY", "YOUR_CEREBRAS_KEY")
OPENROUTER_KEY = os.environ.get("OPENROUTER_KEY", "YOUR_OPENROUTER_KEY")
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "YOUR_DEEPSEEK_KEY")

APIS = [
    ("Groq", "https://api.groq.com/openai/v1/chat/completions", GROQ_API_KEY, "llama-3.3-70b-versatile"),
    ("Cerebras", "https://api.cerebras.ai/v1/chat/completions", CEREBRAS_API_KEY, "llama3.1-8b"),
    ("Together", "https://api.together.xyz/v1/chat/completions", TOGETHER_KEY, "meta-llama/Llama-3.3-70B-Instruct-Turbo"),
    ("Fireworks", "https://api.fireworks.ai/inference/v1/chat/completions", FIREWORKS_API_KEY, "accounts/fireworks/models/llama-v3p3-70b-instruct"),
    ("OpenRouter", "https://openrouter.ai/api/v1/chat/completions", OPENROUTER_KEY, "meta-llama/llama-3.2-3b-instruct:free"),
    ("DeepSeek", "https://api.deepseek.com/v1/chat/completions", DEEPSEEK_API_KEY, "deepseek-chat"),
]

_api_idx = random.randint(0, len(APIS) - 1)

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
                print(f"  ✓ {name}")
                _api_idx = (idx + 1) % len(APIS)
                return resp.json()["choices"][0]["message"]["content"]
            elif resp.status_code == 429:
                print(f"  ⚠ {name} rate limited")
        except Exception as e:
            print(f"  ✗ {name}: {str(e)[:50]}")
    return None

def fix_book(server_url, book_name):
    """Fetch, fix, and upload a book."""
    # Get book data
    resp = requests.get(f"{server_url}/book/{book_name}", timeout=30)
    if resp.status_code != 200:
        print(f"  Failed to fetch: {resp.status_code}")
        return False

    data = resp.json()
    chapters = data.get("chapters", {})
    updated_chapters = {}
    any_changes = False

    for ch_name, content in chapters.items():
        words = len(content.split())
        if words < 2000:
            print(f"  Expanding {ch_name} ({words} words)")
            prompt = f"""Expand this chapter to at least 2500 words. Keep the same style and story.
Write ONLY the expanded chapter, no commentary.

{content[:10000]}

EXPANDED CHAPTER:"""

            result = call_api(prompt, max_tokens=4000)
            if result and len(result.split()) > words:
                updated_chapters[ch_name] = result
                any_changes = True
                print(f"    → {len(result.split())} words")
            time.sleep(1)

    # Upload changes
    if any_changes:
        resp = requests.post(
            f"{server_url}/book/{book_name}/update",
            json={"chapters": updated_chapters, "quality_fixed": True},
            timeout=30
        )
        if resp.status_code == 200:
            print(f"  ✓ Uploaded changes")
            return True
    else:
        # Mark as fixed even if no changes needed
        resp = requests.post(
            f"{server_url}/book/{book_name}/update",
            json={"quality_fixed": True},
            timeout=30
        )

    return True

def main():
    if len(sys.argv) < 2:
        print("Usage: python cloud_worker.py <server_url>")
        print("Example: python cloud_worker.py https://xxx.trycloudflare.com")
        return

    server_url = sys.argv[1].rstrip("/")
    print(f"=== Cloud Book Fixer ===")
    print(f"Server: {server_url}")

    # Test connection
    try:
        resp = requests.get(f"{server_url}/status", timeout=10)
        status = resp.json()
        print(f"Status: {status['fixed']}/{status['total']} fixed, {status['remaining']} remaining")
    except Exception as e:
        print(f"ERROR: Cannot connect to server: {e}")
        return

    # Test APIs
    print("\nTesting APIs...")
    result = call_api("Say 'OK' in one word")
    if not result:
        print("ERROR: No working APIs!")
        return
    print(f"API test: {result}")

    # Get books to fix
    print("\nFetching book list...")
    resp = requests.get(f"{server_url}/books", timeout=30)
    books = resp.json().get("books", [])
    random.shuffle(books)  # Randomize to avoid conflicts with other workers

    print(f"Found {len(books)} books to fix\n")

    for i, book in enumerate(books[:50]):  # Limit to 50 per run
        print(f"[{i+1}/{min(len(books), 50)}] {book}")
        try:
            fix_book(server_url, book)
        except Exception as e:
            print(f"  Error: {e}")
        time.sleep(2)

    print("\n=== Done ===")
    resp = requests.get(f"{server_url}/status", timeout=10)
    status = resp.json()
    print(f"Final status: {status['fixed']}/{status['total']} fixed")

if __name__ == "__main__":
    main()
