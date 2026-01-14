# Cloud Workers Setup Guide

## Status
- **Books**: 494 total, 405 fixed, **89 remaining**
- **Server**: `book_server_v2.py` ready (with claim coordination)

## Quick Start

### 1. Update ngrok Token
Your ngrok token is invalid. Get a new one:
1. Go to https://dashboard.ngrok.com/get-started/your-authtoken
2. Copy your auth token
3. Run: `~/.local/bin/ngrok config add-authtoken YOUR_TOKEN`

### 2. Start the Server
```bash
cd /mnt/e/projects/bookcli

# Start book server
python3 book_server_v2.py &

# Start ngrok tunnel
~/.local/bin/ngrok http 8765

# Copy the https URL shown (e.g., https://xxxx.ngrok-free.app)
```

### 3. Launch Workers

#### Option A: Google Colab
1. Open `notebooks/colab_book_fixer.ipynb` in Colab
2. Set `SERVER_URL` to your ngrok URL
3. Add your API keys (Groq, DeepSeek, Together, etc.)
4. Run all cells

#### Option B: Kaggle
1. Upload `notebooks/kaggle_book_fixer.ipynb` to Kaggle
2. Add secrets: `BOOK_SERVER_URL`, `DEEPSEEK_API_KEY`, `GROQ_API_KEY`
3. Enable internet access
4. Run the notebook

#### Option C: GitHub Actions
1. Set repo secrets (Settings → Secrets):
   - `DEEPSEEK_API_KEY`, `GROQ_API_KEY`, `TOGETHER_KEY`, etc.
2. Run workflow: Actions → "Cloud Book Fixers" → Run workflow
3. Enter your ngrok tunnel URL

#### Option D: HuggingFace Spaces
1. Create a new Gradio Space on HuggingFace
2. Upload files from `huggingface_space/`:
   - `app.py`
   - `requirements.txt`
   - `README.md`
3. Add secrets: `BOOK_SERVER_URL`, API keys
4. The Space will auto-start

## API Keys (Free Tiers)

| Provider | URL | Free Tier |
|----------|-----|-----------|
| Groq | https://console.groq.com | Generous free tier |
| DeepSeek | https://platform.deepseek.com | $5 free credit |
| Together | https://api.together.xyz | $5 free credit |
| OpenRouter | https://openrouter.ai | Free models |
| Fireworks | https://fireworks.ai | Free trial |
| Cerebras | https://cerebras.ai | Free tier |

## Server Endpoints

- `GET /status` - Fix progress
- `GET /books` - List unfixed books
- `GET /book/<name>` - Get book data
- `GET /claim/<name>` - Claim book (prevents conflicts)
- `GET /release/<name>` - Release claim
- `POST /book/<name>/update` - Save fixed book
- `GET /workers` - List active workers

## Files Created

```
bookcli/
├── book_server_v2.py          # Enhanced server with coordination
├── start_cloud_server.sh      # Launch script
├── huggingface_space/         # HF Spaces app
│   ├── app.py
│   ├── requirements.txt
│   └── README.md
├── notebooks/
│   ├── colab_book_fixer.ipynb # Updated with server mode
│   └── kaggle_book_fixer.ipynb
└── .github/workflows/
    ├── book-fixer.yml         # Scheduled + manual
    └── cloud-workers.yml      # Server-based workers
```
