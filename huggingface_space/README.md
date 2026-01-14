---
title: Book Fixer Worker
emoji: 📚
colorFrom: blue
colorTo: purple
sdk: gradio
sdk_version: 4.44.0
app_file: app.py
pinned: false
---

# Book Fixer Worker

A HuggingFace Space that runs as a distributed book fixer worker.

## Setup

1. **Fork/Duplicate this Space**

2. **Add Secrets** (Settings → Secrets):
   - `BOOK_SERVER_URL`: Your ngrok tunnel URL (e.g., `https://xxx.ngrok-free.app`)
   - `DEEPSEEK_API_KEY`: From https://platform.deepseek.com
   - `GROQ_API_KEY`: From https://console.groq.com (free tier)
   - `TOGETHER_KEY`: From https://api.together.xyz
   - `OPENROUTER_KEY`: From https://openrouter.ai
   - `FIREWORKS_API_KEY`: From https://fireworks.ai
   - `CEREBRAS_API_KEY`: From https://cerebras.ai
   - `HF_TOKEN`: Your HuggingFace token (for HF Inference API)

3. **Start the Worker**:
   - Enter the book server URL in the interface
   - Click "Start Worker"
   - The worker will automatically process unfixed books

## How it Works

1. Connects to your local book server (exposed via ngrok)
2. Fetches list of unfixed books
3. Expands short chapters using various free LLM APIs
4. Updates the book server with fixed chapters
5. Marks books as quality_fixed

## Running the Book Server

On your local machine:
```bash
cd /path/to/bookcli
python book_server.py  # Starts on port 8765
ngrok http 8765        # Exposes to internet
```

Use the ngrok URL in this Space.
