#!/usr/bin/env python3
"""
HuggingFace Spaces Book Fixer Worker
====================================
Deploy this to a HuggingFace Space to run a book fixer worker.

Setup:
1. Create a new Space on HuggingFace (Gradio SDK)
2. Add secrets: BOOK_SERVER_URL, DEEPSEEK_API_KEY, GROQ_API_KEY, etc.
3. Upload this file as app.py
"""

import os
import gradio as gr
import requests
import json
import time
import threading
from datetime import datetime

# Configuration
BOOK_SERVER_URL = os.environ.get("BOOK_SERVER_URL", "")  # Your ngrok URL
WORKER_ID = os.environ.get("WORKER_ID", f"hf-{os.environ.get('SPACE_ID', 'local')[:8]}")

# API Keys
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
OPENROUTER_KEY = os.environ.get("OPENROUTER_KEY", "")
TOGETHER_KEY = os.environ.get("TOGETHER_KEY", "")
FIREWORKS_API_KEY = os.environ.get("FIREWORKS_API_KEY", "")
CEREBRAS_API_KEY = os.environ.get("CEREBRAS_API_KEY", "")
HF_TOKEN = os.environ.get("HF_TOKEN", "")

# Build API list
APIS = []
if GROQ_API_KEY:
    APIS.append(("Groq", "https://api.groq.com/openai/v1/chat/completions",
                 GROQ_API_KEY, "llama-3.3-70b-versatile"))
if CEREBRAS_API_KEY:
    APIS.append(("Cerebras", "https://api.cerebras.ai/v1/chat/completions",
                 CEREBRAS_API_KEY, "llama3.1-8b"))
if TOGETHER_KEY:
    APIS.append(("Together", "https://api.together.xyz/v1/chat/completions",
                 TOGETHER_KEY, "meta-llama/Llama-3.3-70B-Instruct-Turbo"))
if FIREWORKS_API_KEY:
    APIS.append(("Fireworks", "https://api.fireworks.ai/inference/v1/chat/completions",
                 FIREWORKS_API_KEY, "accounts/fireworks/models/llama-v3p3-70b-instruct"))
if OPENROUTER_KEY:
    APIS.append(("OpenRouter", "https://openrouter.ai/api/v1/chat/completions",
                 OPENROUTER_KEY, "meta-llama/llama-3.2-3b-instruct:free"))
if DEEPSEEK_API_KEY:
    APIS.append(("DeepSeek", "https://api.deepseek.com/v1/chat/completions",
                 DEEPSEEK_API_KEY, "deepseek-chat"))
if HF_TOKEN:
    APIS.append(("HuggingFace", "https://router.huggingface.co/v1/chat/completions",
                 HF_TOKEN, "meta-llama/Llama-3.2-3B-Instruct"))

_api_idx = 0
_worker_status = {
    "running": False,
    "books_fixed": 0,
    "chapters_expanded": 0,
    "current_book": None,
    "last_update": None,
    "logs": []
}

def log(msg):
    timestamp = datetime.now().strftime("%H:%M:%S")
    entry = f"[{timestamp}] {msg}"
    _worker_status["logs"].append(entry)
    if len(_worker_status["logs"]) > 100:
        _worker_status["logs"] = _worker_status["logs"][-100:]
    print(entry)

def call_api(prompt, max_tokens=4000):
    global _api_idx
    for i in range(len(APIS)):
        idx = (_api_idx + i) % len(APIS)
        name, url, key, model = APIS[idx]
        try:
            resp = requests.post(url,
                headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
                json={"model": model, "messages": [{"role": "user", "content": prompt}],
                      "max_tokens": max_tokens, "temperature": 0.7},
                timeout=120)
            if resp.status_code == 200:
                log(f"  ✓ {name}")
                _api_idx = (idx + 1) % len(APIS)
                return resp.json()["choices"][0]["message"]["content"]
            elif resp.status_code == 429:
                log(f"  ⚠ {name} rate limited")
        except Exception as e:
            log(f"  ✗ {name}: {str(e)[:50]}")
    return None

def expand_chapter(content, chapter_num=1):
    words = len(content.split())
    if words >= 2500:
        return content, False

    prompt = f"""Expand this chapter to at least 2500 words. Keep the same style, characters, and plot.
Do not add author notes, commentary, or meta-text. Just write the expanded chapter.

CHAPTER {chapter_num}:
{content[:10000]}

Write the COMPLETE expanded chapter (at least 2500 words):"""

    result = call_api(prompt, max_tokens=5000)
    if result and len(result.split()) > words:
        return result, True
    return content, False

def fix_book(server_url, book_name):
    """Fix a single book."""
    try:
        resp = requests.get(f"{server_url}/book/{book_name}", timeout=30)
        if resp.status_code != 200:
            log(f"  Error getting book: {resp.status_code}")
            return False

        data = resp.json()
        chapters = data.get("chapters", {})
        bible = data.get("story_bible", {})

        if bible.get("quality_fixed"):
            log(f"  Already fixed")
            return True

        updated_chapters = {}
        any_changes = False

        for ch_name in sorted(chapters.keys()):
            content = chapters[ch_name]
            words = len(content.split())

            if words < 2500:
                log(f"  Expanding {ch_name} ({words}w)")
                ch_num = int(ch_name.replace("chapter_", "").replace(".md", ""))
                expanded, changed = expand_chapter(content, ch_num)
                if changed:
                    updated_chapters[ch_name] = expanded
                    any_changes = True
                    new_words = len(expanded.split())
                    log(f"    → {new_words}w")
                    _worker_status["chapters_expanded"] += 1
                time.sleep(1)

        # Send updates
        update_data = {"quality_fixed": True, "fixed_by": WORKER_ID}
        if any_changes:
            update_data["chapters"] = updated_chapters

        requests.post(f"{server_url}/book/{book_name}/update",
                     json=update_data, timeout=30)

        _worker_status["books_fixed"] += 1
        return True

    except Exception as e:
        log(f"  Error: {e}")
        return False

def worker_loop(server_url):
    """Main worker loop."""
    log(f"Starting worker {WORKER_ID}")
    log(f"Server: {server_url}")
    log(f"APIs: {[a[0] for a in APIS]}")

    if not APIS:
        log("ERROR: No API keys configured!")
        return

    # Test connection
    try:
        resp = requests.get(f"{server_url}/status", timeout=10)
        status = resp.json()
        log(f"Server status: {status['fixed']}/{status['total']} fixed")
    except Exception as e:
        log(f"ERROR: Cannot connect to server: {e}")
        return

    # Test APIs
    result = call_api("Say 'OK' in one word")
    if not result:
        log("ERROR: No working APIs!")
        return
    log(f"API test: {result[:20]}")

    # Main loop
    while _worker_status["running"]:
        try:
            resp = requests.get(f"{server_url}/books", timeout=30)
            books = resp.json().get("books", [])

            if not books:
                log("No books to fix, waiting...")
                time.sleep(60)
                continue

            # Pick a random book to avoid conflicts
            import random
            book = random.choice(books)
            _worker_status["current_book"] = book
            _worker_status["last_update"] = datetime.now().isoformat()

            log(f"Processing: {book}")
            fix_book(server_url, book)

            time.sleep(5)  # Rate limiting

        except Exception as e:
            log(f"Loop error: {e}")
            time.sleep(30)

    log("Worker stopped")

def start_worker(server_url):
    if not server_url:
        return "Error: Please enter server URL"

    if _worker_status["running"]:
        return "Worker already running"

    _worker_status["running"] = True
    _worker_status["logs"] = []

    thread = threading.Thread(target=worker_loop, args=(server_url.rstrip("/"),))
    thread.daemon = True
    thread.start()

    return f"Worker started! ID: {WORKER_ID}"

def stop_worker():
    _worker_status["running"] = False
    return "Worker stopping..."

def get_status():
    return json.dumps({
        "worker_id": WORKER_ID,
        "running": _worker_status["running"],
        "books_fixed": _worker_status["books_fixed"],
        "chapters_expanded": _worker_status["chapters_expanded"],
        "current_book": _worker_status["current_book"],
        "apis_available": len(APIS),
        "api_names": [a[0] for a in APIS]
    }, indent=2)

def get_logs():
    return "\n".join(_worker_status["logs"][-50:])

# Gradio Interface
with gr.Blocks(title="Book Fixer Worker") as app:
    gr.Markdown("# 📚 Book Fixer Worker")
    gr.Markdown(f"Worker ID: `{WORKER_ID}` | APIs configured: {len(APIS)}")

    with gr.Row():
        server_input = gr.Textbox(
            label="Book Server URL",
            placeholder="https://xxx.ngrok-free.app",
            value=BOOK_SERVER_URL
        )

    with gr.Row():
        start_btn = gr.Button("▶️ Start Worker", variant="primary")
        stop_btn = gr.Button("⏹️ Stop Worker", variant="stop")

    status_output = gr.Textbox(label="Status", lines=8)
    logs_output = gr.Textbox(label="Logs", lines=15)

    start_btn.click(start_worker, inputs=[server_input], outputs=[status_output])
    stop_btn.click(stop_worker, outputs=[status_output])

    # Auto-refresh every 5 seconds
    app.load(get_status, outputs=[status_output], every=5)
    app.load(get_logs, outputs=[logs_output], every=3)

if __name__ == "__main__":
    app.launch()
