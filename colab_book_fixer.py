# Book Fixer for Google Colab
# Copy this to a Colab notebook and run!

# Step 1: Install dependencies
# !pip install requests

import requests
import json
import time
import os

# Step 2: Set your API keys (paste your keys here or use environment variables)
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")  # Get from https://console.groq.com
TOGETHER_KEY = os.environ.get("TOGETHER_KEY", "")  # Get from https://api.together.xyz
FIREWORKS_API_KEY = os.environ.get("FIREWORKS_API_KEY", "")  # Get from https://fireworks.ai
CEREBRAS_API_KEY = os.environ.get("CEREBRAS_API_KEY", "")  # Get from https://cerebras.ai
OPENROUTER_KEY = os.environ.get("OPENROUTER_KEY", "")  # Get from https://openrouter.ai
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")  # Get from https://deepseek.com

APIS = [
    ("Groq", "https://api.groq.com/openai/v1/chat/completions", GROQ_API_KEY, "llama-3.3-70b-versatile"),
    ("Cerebras", "https://api.cerebras.ai/v1/chat/completions", CEREBRAS_API_KEY, "llama3.1-8b"),
    ("Together", "https://api.together.xyz/v1/chat/completions", TOGETHER_KEY, "meta-llama/Llama-3.3-70B-Instruct-Turbo"),
    ("Fireworks", "https://api.fireworks.ai/inference/v1/chat/completions", FIREWORKS_API_KEY, "accounts/fireworks/models/llama-v3p3-70b-instruct"),
    ("OpenRouter", "https://openrouter.ai/api/v1/chat/completions", OPENROUTER_KEY, "meta-llama/llama-3.2-3b-instruct:free"),
    ("DeepSeek", "https://api.deepseek.com/v1/chat/completions", DEEPSEEK_API_KEY, "deepseek-chat"),
]

_api_idx = 0

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
            print(f"  ✗ {name}: {e}")
    return None

# Step 3: Test APIs
print("Testing APIs...")
result = call_api("Say 'API working' in 3 words")
print(f"Result: {result}")

# Step 4: Upload your books folder to Colab or mount Google Drive
# from google.colab import drive
# drive.mount('/content/drive')

# Step 5: Process books
def fix_chapter(content):
    """Expand a short chapter."""
    words = len(content.split())
    if words >= 2500:
        return content

    prompt = f"""Expand this chapter to at least 2500 words. Keep the same style, characters, and plot.
Do not add author notes or commentary. Just write the expanded chapter.

CHAPTER:
{content[:10000]}

EXPANDED CHAPTER:"""

    result = call_api(prompt, max_tokens=4000)
    if result and len(result.split()) > words:
        return result
    return content

# Example usage:
# chapter_text = open("chapter_01.md").read()
# fixed = fix_chapter(chapter_text)
# print(f"Expanded from {len(chapter_text.split())} to {len(fixed.split())} words")
