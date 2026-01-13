#!/usr/bin/env python3
"""
Kaggle/Colab Book Fixer Worker
Run this in a Kaggle or Google Colab notebook.

Setup:
1. Create a new Kaggle notebook or Colab notebook
2. Copy this entire file into a cell
3. Set your API keys in the KEYS section below
4. Run!

The notebook will:
- Pull work queue from GitHub Gist
- Fix books using free LLM APIs
- Save results to output files (download when done)
"""

import os
import json
import time
import random
import requests
from pathlib import Path

#######################
# CONFIGURATION
#######################

# GitHub Gist for work coordination (public gist)
WORK_GIST_ID = os.environ.get("WORK_GIST_ID", "")  # Will create if empty

# API Keys - Get free keys from these providers:
# Groq: https://console.groq.com (free tier)
# Together: https://api.together.xyz (free credits)
# Fireworks: https://fireworks.ai (free tier)
# Cerebras: https://cerebras.ai (free inference)
# OpenRouter: https://openrouter.ai (free models)
# DeepSeek: https://deepseek.com (cheap)

KEYS = {
    "GROQ_API_KEY": os.environ.get("GROQ_API_KEY", ""),
    "TOGETHER_KEY": os.environ.get("TOGETHER_KEY", ""),
    "FIREWORKS_API_KEY": os.environ.get("FIREWORKS_API_KEY", ""),
    "CEREBRAS_API_KEY": os.environ.get("CEREBRAS_API_KEY", ""),
    "OPENROUTER_KEY": os.environ.get("OPENROUTER_KEY", ""),
    "DEEPSEEK_API_KEY": os.environ.get("DEEPSEEK_API_KEY", ""),
}

# LLM APIs configuration
APIS = [
    ("Groq", "https://api.groq.com/openai/v1/chat/completions",
     KEYS["GROQ_API_KEY"], "llama-3.3-70b-versatile"),
    ("Cerebras", "https://api.cerebras.ai/v1/chat/completions",
     KEYS["CEREBRAS_API_KEY"], "llama3.1-70b"),
    ("Together", "https://api.together.xyz/v1/chat/completions",
     KEYS["TOGETHER_KEY"], "meta-llama/Llama-3.3-70B-Instruct-Turbo"),
    ("Fireworks", "https://api.fireworks.ai/inference/v1/chat/completions",
     KEYS["FIREWORKS_API_KEY"], "accounts/fireworks/models/llama-v3p3-70b-instruct"),
    ("OpenRouter", "https://openrouter.ai/api/v1/chat/completions",
     KEYS["OPENROUTER_KEY"], "meta-llama/llama-3.3-70b-instruct"),
    ("DeepSeek", "https://api.deepseek.com/v1/chat/completions",
     KEYS["DEEPSEEK_API_KEY"], "deepseek-chat"),
]

#######################
# LLM HELPERS
#######################

_api_idx = random.randint(0, len(APIS) - 1)

def call_llm(prompt, max_tokens=4000, temperature=0.7):
    """Call LLM API with automatic fallback."""
    global _api_idx

    for i in range(len(APIS)):
        idx = (_api_idx + i) % len(APIS)
        name, url, key, model = APIS[idx]

        if not key:
            continue

        try:
            headers = {
                "Authorization": f"Bearer {key}",
                "Content-Type": "application/json"
            }

            # OpenRouter needs extra header
            if "openrouter" in url:
                headers["HTTP-Referer"] = "https://kaggle.com"

            resp = requests.post(url,
                headers=headers,
                json={
                    "model": model,
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": max_tokens,
                    "temperature": temperature
                },
                timeout=120
            )

            if resp.status_code == 200:
                print(f"  ✓ {name}")
                _api_idx = (idx + 1) % len(APIS)
                return resp.json()["choices"][0]["message"]["content"]
            elif resp.status_code == 429:
                print(f"  ⚠ {name} rate limited")
                time.sleep(2)
            else:
                print(f"  ✗ {name}: {resp.status_code}")

        except Exception as e:
            print(f"  ✗ {name}: {str(e)[:50]}")

    return None

#######################
# BOOK FIXING LOGIC
#######################

def analyze_names(chapters):
    """Find character name inconsistencies."""
    all_text = "\n".join(chapters)

    prompt = f"""Analyze this story for character name inconsistencies.
Look for:
- Same character referred to by different names/spellings
- Inconsistent capitalization
- Typos in names

Text (first 8000 chars):
{all_text[:8000]}

Return JSON array of issues found:
[{{"character": "main name", "variants": ["variant1", "variant2"], "fix_to": "correct name"}}]

Return ONLY the JSON array, no other text."""

    result = call_llm(prompt, max_tokens=1000)
    if result:
        try:
            # Extract JSON from response
            start = result.find('[')
            end = result.rfind(']') + 1
            if start >= 0 and end > start:
                return json.loads(result[start:end])
        except:
            pass
    return []

def expand_chapter(chapter_text, chapter_num, story_context=""):
    """Expand a short chapter to meet word count."""
    word_count = len(chapter_text.split())
    target = max(3000, word_count + 1000)

    prompt = f"""Expand this chapter to approximately {target} words while maintaining the story's voice and style.

Current word count: {word_count}
Target: {target} words

Add more:
- Sensory details and atmosphere
- Character thoughts and emotions
- Dialogue and interactions
- Scene transitions

Keep the same plot points and ending. Maintain consistent tone.

Chapter {chapter_num}:
{chapter_text}

Write the expanded chapter:"""

    result = call_llm(prompt, max_tokens=6000)
    if result and len(result.split()) > word_count:
        return result
    return chapter_text

def fix_names_in_text(text, name_fixes):
    """Apply name fixes to text."""
    for fix in name_fixes:
        correct = fix.get("fix_to", fix.get("character", ""))
        for variant in fix.get("variants", []):
            if variant != correct:
                text = text.replace(variant, correct)
    return text

def fix_book(book_data):
    """Fix a single book."""
    print(f"\n{'='*50}")
    print(f"Fixing: {book_data['name']}")
    print(f"{'='*50}")

    chapters = book_data.get("chapters", {})
    if not chapters:
        return None

    chapter_texts = []
    for i in range(1, 20):
        key = f"chapter_{i:02d}"
        if key in chapters:
            chapter_texts.append(chapters[key])

    if not chapter_texts:
        return None

    # 1. Analyze name inconsistencies
    print("\n[1/3] Analyzing names...")
    name_fixes = analyze_names(chapter_texts)
    if name_fixes:
        print(f"  Found {len(name_fixes)} name issues")
        for fix in name_fixes:
            print(f"    - {fix.get('variants', [])} → {fix.get('fix_to', '')}")

    # 2. Fix names in all chapters
    print("\n[2/3] Applying fixes...")
    fixed_chapters = {}
    for i, text in enumerate(chapter_texts, 1):
        key = f"chapter_{i:02d}"
        fixed = fix_names_in_text(text, name_fixes)
        fixed_chapters[key] = fixed

    # 3. Expand short chapters
    print("\n[3/3] Expanding short chapters...")
    for key, text in fixed_chapters.items():
        word_count = len(text.split())
        if word_count < 2500:
            print(f"  {key}: {word_count} words (expanding...)")
            expanded = expand_chapter(text, key)
            fixed_chapters[key] = expanded
            new_count = len(expanded.split())
            print(f"    → {new_count} words")

    return {
        "name": book_data["name"],
        "chapters": fixed_chapters,
        "fixes_applied": {
            "name_fixes": name_fixes,
            "chapters_expanded": sum(1 for k, v in fixed_chapters.items()
                                    if len(v.split()) > len(chapters.get(k, "").split()))
        }
    }

#######################
# WORK QUEUE
#######################

def get_work_queue(gist_url=None):
    """Get list of books to fix from GitHub Gist."""
    if gist_url:
        try:
            resp = requests.get(gist_url, timeout=30)
            if resp.status_code == 200:
                return resp.json()
        except:
            pass

    # Fallback: return sample work
    print("No work queue URL provided. Using sample data.")
    return None

def save_results(results, output_dir="output"):
    """Save fixed books to files."""
    out_path = Path(output_dir)
    out_path.mkdir(exist_ok=True)

    for result in results:
        if not result:
            continue
        book_name = result["name"]
        book_dir = out_path / book_name
        book_dir.mkdir(exist_ok=True)

        # Save chapters
        for key, text in result["chapters"].items():
            (book_dir / f"{key}.md").write_text(text)

        # Save fix report
        (book_dir / "fix_report.json").write_text(
            json.dumps(result["fixes_applied"], indent=2)
        )

        print(f"Saved: {book_name}")

#######################
# MAIN
#######################

def run_worker(books_data, max_books=5):
    """Main worker loop."""
    print("="*60)
    print("KAGGLE/COLAB BOOK FIXER WORKER")
    print("="*60)

    # Check API keys
    active_apis = [name for name, _, key, _ in APIS if key]
    print(f"\nActive APIs: {', '.join(active_apis) or 'NONE - Set API keys!'}")

    if not active_apis:
        print("\n⚠️  No API keys configured!")
        print("Set at least one of these environment variables:")
        for key in KEYS:
            print(f"  - {key}")
        return

    results = []

    for i, book in enumerate(books_data[:max_books]):
        print(f"\n[{i+1}/{min(len(books_data), max_books)}] Processing...")
        result = fix_book(book)
        if result:
            results.append(result)

    # Save results
    if results:
        save_results(results)
        print(f"\n✅ Fixed {len(results)} books!")
        print("Download the 'output' folder to get your fixed books.")

    return results


# Example usage with inline data (for testing)
if __name__ == "__main__":
    # Sample book data for testing
    sample_books = [
        {
            "name": "Test_Book",
            "chapters": {
                "chapter_01": """Chapter 1: The Beginning

John walked into the room. Jon looked around carefully. Jonn noticed the strange atmosphere.
The room was dark and mysterious. He felt uneasy.""",
                "chapter_02": """Chapter 2: The Discovery

John found a hidden door. Behind it was a secret passage that led deep underground."""
            }
        }
    ]

    # Run with sample data
    run_worker(sample_books, max_books=1)
