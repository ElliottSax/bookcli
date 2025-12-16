# Quick API Key Setup (2 minutes)

To generate books, you need an LLM API key. **Groq is recommended** (free, fast).

## Option 1: Groq (FREE - Recommended)

1. Go to: https://console.groq.com
2. Click **"Sign in"** (top right)
3. Sign in with Google or GitHub
4. Once logged in, click **"API Keys"** in left menu
5. Click **"Create API Key"**
6. Name it: "book-generation"
7. Click **"Submit"**
8. **Copy the key** (starts with `gsk_...`)

### Set the key:
```bash
export GROQ_API_KEY='paste-your-key-here'

# Make it permanent (optional):
echo 'export GROQ_API_KEY="your-key"' >> ~/.bashrc
source ~/.bashrc
```

## Option 2: DeepSeek (Ultra Cheap - $0.14 per million tokens)

1. Go to: https://platform.deepseek.com
2. Sign up with email
3. Go to **"API Keys"**
4. Create new key
5. **Copy the key**

```bash
export DEEPSEEK_API_KEY='your-key-here'
```

## Option 3: OpenAI (Most Compatible)

1. Go to: https://platform.openai.com/api-keys
2. Sign in or create account
3. Click **"Create new secret key"**
4. **Copy the key** (starts with `sk-...`)

```bash
export OPENAI_API_KEY='your-key-here'
```

## Test Your Key

```bash
# Check if set
echo $GROQ_API_KEY

# Generate test book
python3 scripts/resilient_orchestrator.py
```

## Cost Comparison

| Provider | Free Tier | Cost per Book (30k words) |
|----------|-----------|---------------------------|
| **Groq** | Yes (generous) | ~$0.05 |
| **DeepSeek** | $5 credit | ~$0.03 |
| **OpenAI** | $5 credit | ~$0.20 |

**Recommendation**: Use Groq for free testing, DeepSeek for production (cheapest).
