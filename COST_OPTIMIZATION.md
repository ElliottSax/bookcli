# Cost Optimization Guide

**Reduce book generation costs by up to 97% using alternative LLM providers**

---

## Quick Cost Comparison

| Provider | Cost per 80k Book | Savings vs Claude |
|----------|-------------------|-------------------|
| **DeepSeek** | **$0.05** | **↓ 97%** ✨ |
| OpenRouter | $0.05 | ↓ 97% |
| Alibaba Qwen | $0.10 | ↓ 95% |
| Claude Sonnet 4 | $1.85 | baseline |
| OpenAI GPT-4 | $4.40 | ↑ 138% |

**Recommendation:** Use **DeepSeek** for 97% cost savings ($0.05 vs $1.85 per book)

---

## Setup Instructions

### Option 1: DeepSeek (Recommended - Cheapest)

**Cost:** $0.14/$0.28 per 1M tokens (~$0.05 per 80k-word book)

```bash
# 1. Get API key from https://platform.deepseek.com/
# 2. Set environment variable
export DEEPSEEK_API_KEY=sk-your-key-here

# 3. Install OpenAI package (DeepSeek uses OpenAI-compatible API)
pip install openai

# 4. Generate book with DeepSeek
python3 scripts/orchestrator.py \
  --source source/my-book.txt \
  --book-name my-book \
  --genre thriller \
  --target-words 80000 \
  --use-api \
  --provider deepseek \
  --max-budget 5.0
```

**Estimated cost for full 80k book:** $0.05-$0.10

---

### Option 2: OpenRouter

**Cost:** $0.14/$0.28 per 1M tokens (varies by model)

```bash
# 1. Get API key from https://openrouter.ai/
# 2. Set environment variable
export OPENROUTER_API_KEY=sk-or-your-key-here

# 3. Install OpenAI package
pip install openai

# 4. Generate book
python3 scripts/orchestrator.py \
  --source source/my-book.txt \
  --book-name my-book \
  --genre thriller \
  --target-words 80000 \
  --use-api \
  --provider openrouter \
  --max-budget 5.0
```

**Benefit:** Access to multiple models through one API

---

### Option 3: Alibaba Qwen

**Cost:** $0.29/$0.57 per 1M tokens (~$0.10 per 80k-word book)

```bash
# 1. Get API key from https://www.alibabacloud.com/
# 2. Set environment variable
export QWEN_API_KEY=sk-your-key-here

# 3. Install OpenAI package
pip install openai

# 4. Generate book
python3 scripts/orchestrator.py \
  --source source/my-book.txt \
  --book-name my-book \
  --genre thriller \
  --target-words 80000 \
  --use-api \
  --provider qwen \
  --max-budget 5.0
```

---

### Option 4: Claude Sonnet 4 (Default - Highest Quality)

**Cost:** $3/$15 per 1M tokens (~$1.85 per 80k-word book)

```bash
# 1. Get API key from https://console.anthropic.com/
# 2. Set environment variable
export ANTHROPIC_API_KEY=sk-ant-your-key-here

# 3. Install anthropic package
pip install anthropic

# 4. Generate book
python3 scripts/orchestrator.py \
  --source source/my-book.txt \
  --book-name my-book \
  --genre thriller \
  --target-words 80000 \
  --use-api \
  --provider claude \
  --max-budget 5.0
```

**Benefit:** Highest quality output, best instruction following

---

## Detailed Cost Breakdown

### Per-Chapter Costs

| Provider | Input Tokens | Output Tokens | Cost/Chapter |
|----------|--------------|---------------|--------------|
| DeepSeek | 8,000 | 4,000 | **$0.002** |
| OpenRouter | 8,000 | 4,000 | **$0.002** |
| Qwen | 8,000 | 4,000 | **$0.005** |
| Claude | 8,000 | 4,000 | **$0.084** |
| OpenAI | 8,000 | 4,000 | **$0.200** |

### Complete Book Costs (80k words, 22 chapters)

| Provider | Total Cost | Time | Quality |
|----------|------------|------|---------|
| **DeepSeek** | **$0.05** | 2-4 hours | Very Good ⭐⭐⭐⭐ |
| OpenRouter | $0.05 | 2-4 hours | Good-Excellent (varies) |
| Qwen | $0.10 | 2-4 hours | Very Good ⭐⭐⭐⭐ |
| Claude | $1.85 | 2-4 hours | Excellent ⭐⭐⭐⭐⭐ |
| OpenAI | $4.40 | 2-4 hours | Excellent ⭐⭐⭐⭐⭐ |

---

## Cost Savings Calculator

### Batch Production Example

**Scenario:** Generate 10 thriller novels (80k words each)

| Provider | Total Cost | Savings |
|----------|------------|---------|
| DeepSeek | **$0.50** | **baseline** |
| Claude | $18.50 | costs 37× more |
| OpenAI | $44.00 | costs 88× more |

**With DeepSeek, you can generate:**
- **370 books** for the cost of 10 books with Claude
- **880 books** for the cost of 10 books with OpenAI

---

## Quality Comparison

### DeepSeek Quality

**Pros:**
- ✅ Very competitive with Claude for fiction writing
- ✅ Good instruction following
- ✅ Strong creative writing capabilities
- ✅ Excellent value (97% cheaper)
- ✅ Handles long-form content well

**Cons:**
- ⚠️ Slightly more verbose than Claude (may need extra quality fixes)
- ⚠️ Occasionally less natural dialogue
- ⚠️ May require 1-2 regenerations for best quality

**Overall:** **4/5 stars** - Excellent for cost-conscious production

---

### When to Use Each Provider

**Use DeepSeek when:**
- ✅ Cost is primary concern
- ✅ Generating many books in batch
- ✅ Testing ideas/concepts before committing
- ✅ Creating first drafts for heavy editing
- ✅ Budget is tight (<$10)

**Use Claude when:**
- ✅ Quality is paramount
- ✅ Complex narratives with intricate continuity
- ✅ Literary fiction requiring nuance
- ✅ Budget allows ($20-50 per book)
- ✅ Minimal editing desired

**Use Qwen when:**
- ✅ Middle ground between cost and quality
- ✅ International/Asian settings (better cultural knowledge)
- ✅ DeepSeek unavailable in your region

---

## Hybrid Approach (Best of Both Worlds)

**Strategy:** Use different providers for different stages

```bash
# Stage 1: Planning & first draft with DeepSeek (cheap)
python3 scripts/orchestrator.py \
  --source source/book.txt \
  --book-name book-draft \
  --genre thriller \
  --target-words 80000 \
  --use-api \
  --provider deepseek \
  --max-budget 1.0

# Review draft, identify weak chapters

# Stage 2: Regenerate weak chapters with Claude (quality)
# Edit weak chapters manually, use Claude for specific improvements

# Total cost: ~$0.10 (DeepSeek) + ~$0.50 (Claude touch-ups) = $0.60
# vs $1.85 for all Claude = 68% savings with comparable quality
```

---

## Installation Guide for Each Provider

### DeepSeek Setup

```bash
# 1. Sign up
# Visit: https://platform.deepseek.com/
# Create account and get API key

# 2. Install dependencies
pip install openai  # DeepSeek uses OpenAI-compatible API

# 3. Set API key
export DEEPSEEK_API_KEY=sk-your-key-here

# 4. Verify
python3 scripts/llm_providers.py compare
```

### OpenRouter Setup

```bash
# 1. Sign up
# Visit: https://openrouter.ai/
# Connect account and get API key

# 2. Install dependencies
pip install openai

# 3. Set API key
export OPENROUTER_API_KEY=sk-or-your-key-here

# 4. Choose model
# Edit scripts/llm_providers.py to change model if desired
# Available: deepseek/deepseek-chat, anthropic/claude, etc.
```

### Qwen (Alibaba Cloud) Setup

```bash
# 1. Sign up
# Visit: https://www.alibabacloud.com/
# Enable DashScope API and get API key

# 2. Install dependencies
pip install openai

# 3. Set API key
export QWEN_API_KEY=sk-your-key-here

# 4. Verify
python3 scripts/llm_providers.py compare
```

---

## ROI Analysis

### Example: Self-Publishing Business

**Traditional approach (Claude):**
- Cost per book: $1.85
- 100 books per year: $185
- Profit per book (Amazon): $3.00
- Net profit: $300 - $185 = $115

**With DeepSeek:**
- Cost per book: $0.05
- 100 books per year: $5
- Profit per book: $3.00
- Net profit: $300 - $5 = **$295**

**Savings: $180 per year (157% increase in profit margin)**

---

### Example: High-Volume Publisher

**1,000 books per year:**

| Provider | Annual Cost | Profit @$3/book | ROI |
|----------|-------------|-----------------|-----|
| DeepSeek | **$50** | **$2,950** | **5,900%** |
| Claude | $1,850 | $1,150 | 62% |
| OpenAI | $4,400 | $-1,400 | -32% (loss) |

**With DeepSeek, a high-volume publisher can:**
- Save $1,800/year vs Claude
- Maintain profitability vs OpenAI (which loses money)
- Increase profit margin from 38% to 98%

---

## Testing Quality Before Committing

### Generate Test Chapter

```bash
# Test DeepSeek with single chapter (costs <$0.01)
python3 scripts/orchestrator.py \
  --source source/test.txt \
  --book-name deepseek-test \
  --genre thriller \
  --target-words 3500 \
  --use-api \
  --provider deepseek \
  --max-budget 0.10

# Compare with Claude
python3 scripts/orchestrator.py \
  --source source/test.txt \
  --book-name claude-test \
  --genre thriller \
  --target-words 3500 \
  --use-api \
  --provider claude \
  --max-budget 0.50

# Review both outputs
diff workspace/deepseek-test/chapters/chapter_001.md \
     workspace/claude-test/chapters/chapter_001.md
```

---

## Troubleshooting

### "Package 'openai' not found"

```bash
pip install openai
```

### "API key not set"

```bash
# DeepSeek
export DEEPSEEK_API_KEY=sk-your-key

# OpenRouter
export OPENROUTER_API_KEY=sk-or-your-key

# Qwen
export QWEN_API_KEY=sk-your-key
```

### "Invalid API endpoint"

**Check your region/country**
- DeepSeek: Global availability
- Qwen: May have regional restrictions
- Claude: US/UK/EU primarily

### Rate Limits

All providers have rate limits:
- DeepSeek: Typically high for paid accounts
- OpenRouter: Varies by model
- Qwen: Check DashScope docs
- Claude: 50 requests/min (Tier 1)

**Solution:** System automatically retries with 2s delay

---

## Summary

### Recommended Setup

**For beginners / cost-conscious:**
```bash
--provider deepseek
--max-budget 1.0
```
**Cost:** $0.05 per 80k-word book

**For quality-focused:**
```bash
--provider claude
--max-budget 5.0
```
**Cost:** $1.85 per 80k-word book

**For middle ground:**
```bash
--provider qwen
--max-budget 1.0
```
**Cost:** $0.10 per 80k-word book

---

## Real-World Cost Examples

### Romance Novel (100k words, 28 chapters)

| Provider | Cost | vs DeepSeek |
|----------|------|-------------|
| DeepSeek | $0.06 | baseline |
| Qwen | $0.13 | 2.2× more |
| Claude | $2.31 | 38× more |

### Thriller (75k words, 20 chapters)

| Provider | Cost | vs DeepSeek |
|----------|------|-------------|
| DeepSeek | $0.04 | baseline |
| Qwen | $0.09 | 2.3× more |
| Claude | $1.67 | 42× more |

### Fantasy Epic (120k words, 35 chapters)

| Provider | Cost | vs DeepSeek |
|----------|------|-------------|
| DeepSeek | $0.07 | baseline |
| Qwen | $0.16 | 2.3× more |
| Claude | $2.78 | 40× more |

---

## Conclusion

**DeepSeek offers 97% cost savings with very good quality.**

For most users, especially those generating multiple books, **DeepSeek is the optimal choice:**

- ✅ **$0.05 per book** vs $1.85 (Claude) or $4.40 (OpenAI)
- ✅ **37× cheaper** than Claude for batch production
- ✅ **Very good quality** (4/5 stars) suitable for commercial fiction
- ✅ **Same speed** (~2-4 hours per book)
- ✅ **No quality gate changes needed** - all rules work the same

**Start with DeepSeek, upgrade to Claude only if quality demands it.**

---

**Ready to save 97% on book production costs?**

```bash
pip install openai
export DEEPSEEK_API_KEY=your-key
python3 scripts/orchestrator.py --use-api --provider deepseek
```

---

*Last Updated: 2025-11-27*
*Version: 1.2.0*
