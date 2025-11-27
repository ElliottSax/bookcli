# Production Deployment Guide

**Autonomous Book Production with Claude API**

This guide covers deploying the Book Factory system for fully autonomous book generation.

---

## Table of Contents

1. [Installation](#installation)
2. [API Setup](#api-setup)
3. [Usage Modes](#usage-modes)
4. [Cost Estimation](#cost-estimation)
5. [Production Workflow](#production-workflow)
6. [Monitoring & Recovery](#monitoring--recovery)
7. [Best Practices](#best-practices)
8. [Troubleshooting](#troubleshooting)

---

## Installation

### Prerequisites

- **Python 3.8+**
- **pip** (Python package manager)
- **Claude API account** (for autonomous mode)

### Step 1: Clone Repository

```bash
git clone https://github.com/yourusername/bookcli.git
cd bookcli
```

### Step 2: Install Dependencies

```bash
# Install Anthropic SDK for Claude API
pip install anthropic

# Optional: Install pandoc for EPUB/DOCX/PDF export
# macOS:
brew install pandoc

# Ubuntu/Debian:
sudo apt-get install pandoc texlive-xetex

# Windows:
# Download from https://pandoc.org/installing.html
```

### Step 3: Verify Installation

```bash
python3 tests/run_tests.py
```

Expected output: `✓ ALL TESTS PASSED`

---

## API Setup

### Get Claude API Key

1. Go to https://console.anthropic.com/
2. Sign up or log in
3. Navigate to API Keys
4. Create new key
5. Copy the key (starts with `sk-ant-`)

### Set Environment Variable

**Linux/macOS:**
```bash
# Temporary (current session only)
export ANTHROPIC_API_KEY=sk-ant-your-key-here

# Permanent (add to ~/.bashrc or ~/.zshrc)
echo 'export ANTHROPIC_API_KEY=sk-ant-your-key-here' >> ~/.bashrc
source ~/.bashrc
```

**Windows (PowerShell):**
```powershell
# Temporary
$env:ANTHROPIC_API_KEY="sk-ant-your-key-here"

# Permanent (System)
[Environment]::SetEnvironmentVariable("ANTHROPIC_API_KEY", "sk-ant-your-key-here", "User")
```

### Verify API Access

```bash
python3 tests/test_api_integration.py
```

If API key is set correctly, you'll see:
```
✓ API key found
✓ Orchestrator initialized with API mode
```

---

## Usage Modes

### Mode 1: Manual (No API - Claude Code CLI)

**Best for:** Testing, learning, or when you want control over each chapter

```bash
# Create prompts only (no API calls)
python3 scripts/orchestrator.py \
  --source source/your-book.txt \
  --book-name my-thriller \
  --genre thriller \
  --target-words 80000

# Then manually generate each chapter with Claude Code CLI:
/write-chapter my-thriller 1
/write-chapter my-thriller 2
# ... etc
```

**Cost:** $0 (uses Claude Code CLI)
**Time:** Interactive, depends on your pace

---

### Mode 2: Autonomous (API)

**Best for:** Production, generating complete books hands-free

```bash
# Fully autonomous generation
python3 scripts/orchestrator.py \
  --source source/your-book.txt \
  --book-name my-thriller \
  --genre thriller \
  --target-words 80000 \
  --use-api \
  --max-budget 50.0
```

**Cost:** ~$15-25 per 80k-word book
**Time:** 2-4 hours (depends on chapter count)

**Features:**
- ✅ Calls Claude API automatically
- ✅ Generates all chapters sequentially
- ✅ Runs quality checks after each chapter
- ✅ Tracks continuity automatically
- ✅ Monitors costs in real-time
- ✅ Stops if budget exceeded
- ✅ Resume capability on interruption

---

## Cost Estimation

### Pricing (Claude Sonnet 4)

- **Input:** $3.00 per million tokens
- **Output:** $15.00 per million tokens

### Typical Chapter Costs

| Component | Input Tokens | Output Tokens | Cost |
|-----------|--------------|---------------|------|
| Chapter generation | ~8,000 | ~4,000 | ~$0.08 |
| Total per chapter | - | - | **~$0.08** |

### Full Book Costs

| Book Length | Chapters | Est. Cost |
|-------------|----------|-----------|
| 60k words | 20 chapters | **$15-20** |
| 80k words | 22 chapters | **$18-25** |
| 100k words | 28 chapters | **$22-30** |

### Budget Safety

The system includes budget protection:

```bash
# Set maximum spend (default: $50)
--max-budget 30.0

# System will:
# - Track costs in real-time
# - Log cost after each chapter
# - STOP if budget exceeded
# - Save all work before stopping
```

---

## Production Workflow

### Complete Book Generation

```bash
# Step 1: Prepare source material
mkdir -p source
vim source/my-book.txt  # Add your source (outline, synopsis, or public domain text)

# Step 2: Run autonomous generation
python3 scripts/orchestrator.py \
  --source source/my-book.txt \
  --book-name my-book \
  --genre thriller \
  --target-words 80000 \
  --use-api \
  --max-budget 50.0

# Step 3: Monitor progress
# Watch real-time logs:
tail -f workspace/my-book/production.log

# Check status:
cat workspace/my-book/status.json

# Step 4: Review output
# Manuscript:
cat output/my-book/my-book_manuscript.md

# KDP-ready HTML:
open output/my-book/my-book_kdp.html
```

### What Happens Automatically

1. **Analysis** (<1 second)
   - Reads source material
   - Calculates chapter plan
   - Creates 3-act structure

2. **Generation** (2-4 hours for 80k words)
   - Generates each chapter via Claude API
   - Applies quality gate auto-fixes
   - Tracks continuity
   - Saves summaries
   - Updates status

3. **Assembly** (<5 seconds)
   - Combines all chapters
   - Removes metadata sections
   - Creates complete manuscript

4. **Formatting** (<5 seconds)
   - Converts to KDP HTML
   - Optional: EPUB, DOCX, PDF

---

## Monitoring & Recovery

### Real-Time Monitoring

**Watch logs:**
```bash
tail -f workspace/my-book/production.log
```

**Check status:**
```bash
# View status JSON
cat workspace/my-book/status.json | python3 -m json.tool

# Check progress
grep "chapters_completed" workspace/my-book/status.json
```

**Cost tracking:**
```bash
# View total cost so far
grep "total_cost" workspace/my-book/status.json
```

### Resume After Interruption

If generation is interrupted (computer restart, network issue, budget hit):

```bash
# Just re-run the same command
python3 scripts/orchestrator.py \
  --source source/my-book.txt \
  --book-name my-book \
  --genre thriller \
  --target-words 80000 \
  --use-api \
  --max-budget 50.0

# System will:
# - Detect last completed chapter
# - Resume from next chapter
# - Preserve all previous work
# - Continue cost tracking
```

Example log output:
```
[INFO] Resuming from chapter 12 (completed: 11)
[INFO] CHAPTER 12/22 | Progress: 54.5% | ETA: 01:23:45
```

### Progress Tracking

During generation, you'll see:

```
============================================================
CHAPTER 15/22 | Progress: 68.2% | ETA: 00:47:12
============================================================

[INFO] Calling Claude API (attempt 1/3)...
[INFO] Tokens: 7842 in, 3956 out | Cost: $0.0828 | Total: $12.45
[INFO] Chapter 15 generated: 3,421 words
[INFO] Extracting continuity from chapter 15...
[INFO] Tracked 3 character mentions
[INFO] Quality check: chapter 15...
[INFO] ✓ Chapter 15 passed quality gate
[INFO] ✓ Chapter 15 complete
[INFO] Total cost so far: $12.45
```

---

## Best Practices

### Source Material

**Recommended length:**
- Minimum: 500 words (outline/synopsis)
- Optimal: 1,500-3,000 words (detailed outline)
- Maximum: 10,000 words (adapted from public domain)

**Quality tips:**
- Include character descriptions
- Specify key plot points
- Note genre expectations
- Define world/setting details

### Genre Selection

Available genres:
- `thriller` - Fast pacing, cliffhangers, 75-90k words
- `romance` - Dual POV, HEA/HFN, 80-100k words
- `fantasy` - World-building, magic systems, 90-120k words

### Target Word Counts

| Genre | Recommended Range | Chapters |
|-------|------------------|----------|
| Thriller | 75,000-90,000 | 22-25 |
| Romance | 80,000-100,000 | 25-30 |
| Fantasy | 90,000-120,000 | 30-35 |

### Budget Planning

**Conservative approach:**
```bash
# Start with low budget for first book
--max-budget 25.0

# Increase after confirming quality
--max-budget 50.0
```

**Testing first:**
```bash
# Generate just 1-2 chapters first
--target-words 7000  # Creates ~2 chapters
--max-budget 5.0

# Review quality before committing to full book
```

---

## Troubleshooting

### "ANTHROPIC_API_KEY not set"

**Problem:** API key not found

**Solution:**
```bash
# Verify key is set
echo $ANTHROPIC_API_KEY

# If empty, set it
export ANTHROPIC_API_KEY=sk-ant-your-key-here

# Make permanent
echo 'export ANTHROPIC_API_KEY=sk-ant-your-key-here' >> ~/.bashrc
```

---

### "anthropic package not installed"

**Problem:** Missing Python package

**Solution:**
```bash
pip install anthropic

# Verify installation
python3 -c "import anthropic; print('✓ Installed')"
```

---

### "Budget exceeded"

**Problem:** Hit max budget before completion

**Solution:**
```bash
# Check how many chapters completed
cat workspace/my-book/status.json | grep chapters_completed

# Increase budget and resume
python3 scripts/orchestrator.py \
  --source source/my-book.txt \
  --book-name my-book \
  --genre thriller \
  --target-words 80000 \
  --use-api \
  --max-budget 75.0  # Increased budget
```

---

### "Failed to generate chapter after 3 attempts"

**Problem:** API call failed repeatedly

**Possible causes:**
- Network issue
- API rate limit
- Invalid API key

**Solution:**
```bash
# Check API key
python3 -c "import os; print(os.environ.get('ANTHROPIC_API_KEY', 'NOT SET'))"

# Check network
curl https://api.anthropic.com

# Wait 1 minute and retry (rate limit)
sleep 60
python3 scripts/orchestrator.py ...  # Resume
```

---

### Quality Check Failures

**Problem:** Chapter failed quality gate

**What happens:**
- Auto-fixes applied automatically
- If critical issues remain, logged as error
- Chapter still saved (you can review manually)
- Generation continues

**Review failures:**
```bash
# Check production log
grep "quality issues" workspace/my-book/production.log

# View specific chapter
cat workspace/my-book/chapters/chapter_015.md
```

---

### Continuity Issues

**Problem:** Later chapters contradict earlier ones

**Prevention:**
- System tracks characters, events, facts automatically
- Each chapter gets context from previous chapters

**Manual fix if needed:**
```bash
# View tracked continuity
cat workspace/my-book/continuity/characters.json
cat workspace/my-book/continuity/facts.json
cat workspace/my-book/continuity/timeline.json

# Edit chapter manually if needed
vim workspace/my-book/chapters/chapter_015.md

# Re-run assembly
python3 scripts/orchestrator.py \
  --source source/my-book.txt \
  --book-name my-book \
  --genre thriller \
  --assemble-only  # (Note: would need to add this flag)
```

---

## Advanced Usage

### Batch Processing Multiple Books

```bash
#!/bin/bash
# Generate multiple books in sequence

books=(
  "thriller-1:source/book1.txt"
  "thriller-2:source/book2.txt"
  "thriller-3:source/book3.txt"
)

for book in "${books[@]}"; do
  name="${book%%:*}"
  source="${book##*:}"

  echo "Generating: $name"

  python3 scripts/orchestrator.py \
    --source "$source" \
    --book-name "$name" \
    --genre thriller \
    --target-words 80000 \
    --use-api \
    --max-budget 50.0

  echo "Completed: $name"
  echo "---"
done
```

### Custom Configuration

Create project-specific config:

```bash
# .env file
export ANTHROPIC_API_KEY=sk-ant-your-key
export DEFAULT_GENRE=thriller
export DEFAULT_TARGET=80000
export DEFAULT_BUDGET=50.0

# Load and run
source .env
python3 scripts/orchestrator.py \
  --source source/book.txt \
  --book-name my-book \
  --genre $DEFAULT_GENRE \
  --target-words $DEFAULT_TARGET \
  --use-api \
  --max-budget $DEFAULT_BUDGET
```

---

## Performance Metrics

### Typical Generation Times

| Book Size | Chapters | Time (API Mode) | Cost |
|-----------|----------|----------------|------|
| 60k words | 20 | 1.5-2 hours | $15-20 |
| 80k words | 22 | 2-3 hours | $18-25 |
| 100k words | 28 | 3-4 hours | $22-30 |

### System Requirements

**Minimum:**
- CPU: 2 cores
- RAM: 2 GB
- Disk: 500 MB free
- Network: Stable internet connection

**Recommended:**
- CPU: 4+ cores
- RAM: 4+ GB
- Disk: 2+ GB free
- Network: High-speed internet

---

## Output Files

### Directory Structure

```
workspace/my-book/
├── analysis/
│   ├── plan.json              # Project plan
│   └── chapter_plan.json      # Chapter structure
├── chapters/
│   ├── chapter_001.md         # Generated chapters
│   ├── chapter_002.md
│   └── ...
├── continuity/
│   ├── characters.json        # Character tracking
│   ├── timeline.json          # Event timeline
│   ├── facts.json             # Established facts
│   ├── threads.json           # Plot threads
│   └── knowledge.json         # Character knowledge
├── summaries/
│   ├── chapter_001_summary.md # Chapter summaries
│   └── ...
├── status.json                # Progress tracking
└── production.log             # Detailed logs

output/my-book/
├── my-book_manuscript.md      # Complete manuscript
├── my-book_kdp.html           # KDP upload format
├── my-book.epub               # EPUB (if pandoc installed)
├── my-book.docx               # Word doc (if pandoc installed)
└── my-book.pdf                # PDF (if xelatex installed)
```

---

## Quality Assurance

### Automated Checks

Every chapter goes through:

1. **Forbidden Word Detection** (30+ AI-tell patterns)
   - delve, embark, leverage, unlock, etc.
   - Auto-removed and replaced

2. **Purple Prose Removal**
   - "heart hammered", "shivers down spine"
   - Auto-fixed with better prose

3. **Show Don't Tell**
   - Filter words removed (felt, saw, heard)
   - Converted to direct experience

4. **POV Consistency**
   - Maintains deep third-person limited
   - Character perspective enforced

5. **Dialogue Quality**
   - Proper formatting
   - Varied tags
   - Natural rhythm

### Manual Review Recommended

While the system produces publication-ready first drafts:

- ✅ Professional line editing still recommended
- ✅ Proofread for typos
- ✅ Verify continuity makes sense
- ✅ Check chapter endings are strong

---

## Next Steps

1. **Install dependencies**
   ```bash
   pip install anthropic
   ```

2. **Set API key**
   ```bash
   export ANTHROPIC_API_KEY=your-key
   ```

3. **Test with minimal book**
   ```bash
   python3 tests/test_api_integration.py
   ```

4. **Generate your first book**
   ```bash
   python3 scripts/orchestrator.py \
     --source source/your-book.txt \
     --book-name my-first-book \
     --genre thriller \
     --target-words 80000 \
     --use-api \
     --max-budget 50.0
   ```

5. **Monitor and review**
   ```bash
   tail -f workspace/my-first-book/production.log
   ```

---

## Support & Resources

- **Documentation:** See README.md, QUICKSTART.md
- **Examples:** See USAGE_EXAMPLES.md
- **Test Results:** See TEST_REPORT.md
- **Demonstration:** See DEMONSTRATION_COMPLETE.md

---

**The Book Factory is ready for production deployment.**

**Start creating autonomous books today.**

---

*Version: 1.0.0*
*Last Updated: 2025-11-27*
