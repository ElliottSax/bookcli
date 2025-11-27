# Quick Reference Card

**Book Factory - Autonomous Book Production**

---

## 🚀 Quick Start

### 1. Install
```bash
pip install anthropic
export ANTHROPIC_API_KEY=sk-ant-your-key
```

### 2. Generate Book
```bash
python3 scripts/orchestrator.py \
  --source source/your-book.txt \
  --book-name my-book \
  --genre thriller \
  --target-words 80000 \
  --use-api \
  --max-budget 50.0
```

### 3. Monitor
```bash
tail -f workspace/my-book/production.log
```

---

## 📋 Command Options

| Flag | Description | Default |
|------|-------------|---------|
| `--source` | Source file path | Required |
| `--book-name` | Book name (slug) | Required |
| `--genre` | Genre (thriller/romance/fantasy) | Required |
| `--target-words` | Target word count | 80000 |
| `--use-api` | Enable autonomous API mode | False |
| `--max-budget` | Maximum budget (USD) | 50.0 |
| `--no-test` | Skip self-tests | False |

---

## 📁 Key Files

### Input
- `source/your-book.txt` - Your source material

### Output
- `output/{book}/` - Final manuscripts
  - `*_manuscript.md` - Complete book
  - `*_kdp.html` - KDP upload format

### Workspace
- `workspace/{book}/status.json` - Progress tracking
- `workspace/{book}/production.log` - Detailed logs
- `workspace/{book}/chapters/` - Generated chapters

---

## 💰 Cost Estimation

| Book Length | Est. Cost |
|-------------|-----------|
| 60k words | $15-20 |
| 80k words | $18-25 |
| 100k words | $22-30 |

---

## ⏱️ Time Estimation

| Book Length | Generation Time |
|-------------|-----------------|
| 60k words | 1.5-2 hours |
| 80k words | 2-3 hours |
| 100k words | 3-4 hours |

---

## 🔍 Monitoring Commands

```bash
# Watch live logs
tail -f workspace/my-book/production.log

# Check progress
cat workspace/my-book/status.json | grep chapters_completed

# Check cost
cat workspace/my-book/status.json | grep total_cost

# View chapter
cat workspace/my-book/chapters/chapter_001.md
```

---

## 🔄 Resume After Interruption

Just re-run the same command:
```bash
python3 scripts/orchestrator.py \
  --source source/my-book.txt \
  --book-name my-book \
  --genre thriller \
  --target-words 80000 \
  --use-api \
  --max-budget 50.0
```

System automatically:
- Detects last completed chapter
- Resumes from next chapter
- Preserves all previous work

---

## 🧪 Testing

### Run All Tests
```bash
python3 tests/run_tests.py
```

### Test API Integration
```bash
python3 tests/test_api_integration.py
```

### Demo System
```bash
bash example_run.sh
```

---

## 🎯 Supported Genres

### Thriller
- Target: 75-90k words
- Chapters: 22-25
- Features: Fast pacing, cliffhangers, try-fail cycles

### Romance
- Target: 80-100k words
- Chapters: 25-30
- Features: Dual POV, HEA/HFN, chemistry building

### Fantasy
- Target: 90-120k words
- Chapters: 30-35
- Features: Magic systems, world-building, quest structure

---

## 🛠️ Troubleshooting

### API Key Not Set
```bash
export ANTHROPIC_API_KEY=sk-ant-your-key
echo 'export ANTHROPIC_API_KEY=sk-ant-your-key' >> ~/.bashrc
```

### Missing Package
```bash
pip install anthropic
```

### Budget Exceeded
Increase budget and resume:
```bash
--max-budget 75.0
```

### Generation Failed
System auto-retries 3 times. Check logs:
```bash
grep ERROR workspace/my-book/production.log
```

---

## 📚 Documentation

- **START_HERE.md** - Navigation guide
- **QUICKSTART.md** - Getting started
- **README.md** - Complete documentation
- **DEPLOYMENT.md** - Production deployment
- **USAGE_EXAMPLES.md** - 15 practical examples
- **SYSTEM_SUMMARY.md** - Technical overview

---

## ✨ Quality Features

Auto-removes:
- ✅ 30+ forbidden AI words (delve, embark, etc.)
- ✅ Purple prose patterns
- ✅ Filter words (felt, saw, heard)
- ✅ Weak modifiers
- ✅ POV violations

Auto-enforces:
- ✅ Show don't tell
- ✅ Active voice
- ✅ Varied sentence structure
- ✅ Professional dialogue
- ✅ Genre conventions

---

## 🎓 Learning Path

### Beginner (10 minutes)
1. `cat START_HERE.md`
2. `bash example_run.sh`
3. Review `workspace/example-adventure/`

### Intermediate (30 minutes)
1. `cat QUICKSTART.md`
2. Generate test book (7k words, 2 chapters)
3. Review quality output

### Advanced (1 hour)
1. `cat DEPLOYMENT.md`
2. Generate full book (80k words)
3. Upload to KDP

---

## 💡 Pro Tips

### Test First
```bash
# Generate just 2 chapters first
--target-words 7000 --max-budget 5.0

# Review quality before committing to full book
```

### Source Material
- Minimum: 500 words (outline)
- Optimal: 1,500-3,000 words (detailed outline)
- Maximum: 10,000 words (adaptation)

### Budget Safety
```bash
# Start conservative
--max-budget 25.0

# Increase after confirming quality
--max-budget 50.0
```

---

## 🚀 Next Steps

1. **Set API key:** `export ANTHROPIC_API_KEY=your-key`
2. **Create source:** Put text in `source/my-book.txt`
3. **Generate:** Run orchestrator with `--use-api`
4. **Monitor:** Watch logs with `tail -f`
5. **Review:** Check `output/my-book/`
6. **Upload:** Use KDP HTML file

---

**The Book Factory is ready to create your book.**

*For detailed instructions, see DEPLOYMENT.md*
