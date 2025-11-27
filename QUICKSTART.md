# Quick Start Guide - Book Factory

## 30-Second Start

```bash
# 1. Run tests
python3 tests/run_tests.py

# 2. Generate book (automated)
python3 scripts/orchestrator.py \
  --source source/your-book.txt \
  --book-name thriller-demo \
  --genre thriller \
  --target-words 80000
```

## Detailed Walkthrough

### Prerequisites

1. **Python 3.8+** (check: `python3 --version`)
2. **Source material** in `source/` directory
3. **Optional**: Pandoc for EPUB/DOCX (`pandoc --version`)

### Step-by-Step: Your First Book

#### 1. Verify Installation

```bash
cd bookcli
python3 tests/run_tests.py
```

Expected output: `✓ ALL TESTS PASSED`

#### 2. Prepare Source Material

Place your source text in `source/`:

```bash
# Example: Download public domain book
curl -o source/count_of_monte_cristo.txt \
  "https://www.gutenberg.org/files/1184/1184-0.txt"
```

Or use your own text file (any format, will be processed).

#### 3. Choose Your Approach

**Option A: Fully Automated (Python Script)**

```bash
python3 scripts/orchestrator.py \
  --source source/count_of_monte_cristo.txt \
  --book-name quantum-vengeance \
  --genre thriller \
  --target-words 90000
```

This creates chapter prompts. For full automation, integrate Claude API (see Advanced).

**Option B: Claude Code CLI (Interactive)**

```bash
# In Claude Code CLI:

# Analyze source
/analyze-source source/count_of_monte_cristo.txt quantum-vengeance thriller

# Generate chapter 1
/write-chapter quantum-vengeance 1

# Check quality
/quality-check workspace/quantum-vengeance/chapters/chapter_001.md

# Continue for all chapters...
/write-chapter quantum-vengeance 2
/write-chapter quantum-vengeance 3
# ... etc

# Assemble final book
/assemble-book quantum-vengeance
```

#### 4. Monitor Progress

```bash
# Check current status
cat workspace/quantum-vengeance/status.json

# View production log
tail -f workspace/quantum-vengeance/production.log

# Check continuity
python3 scripts/continuity_tracker.py \
  workspace/quantum-vengeance summary
```

#### 5. Review Output

```bash
# Generated files in output/
ls -lh output/quantum-vengeance/

# Expected:
# - quantum-vengeance_manuscript.md    (complete book)
# - quantum-vengeance_kdp.html         (KDP upload format)
# - quantum-vengeance.epub             (if pandoc installed)
# - quantum-vengeance.docx             (if pandoc installed)
# - quantum-vengeance_print.pdf        (if xelatex installed)
# - REPORT.md                          (production summary)
# - continuity_report.json             (consistency check)
```

## Workflow Examples

### Thriller Novel (80k words)

```bash
# Fast-paced, 25-30 chapters
python3 scripts/orchestrator.py \
  --source source/mystery.txt \
  --book-name deadly-secret \
  --genre thriller \
  --target-words 80000

# Chapters will be ~2500-3500 words
# Each ends on cliffhanger
# Total time: ~2-3 hours autonomous
```

### Romance Novel (90k words)

```bash
# Dual POV, HEA ending
python3 scripts/orchestrator.py \
  --source source/love_story.txt \
  --book-name second-chance \
  --genre romance \
  --target-words 90000

# Chapters will be ~3000-4000 words
# Follows Romancing the Beat structure
# Total time: ~3-4 hours
```

### Fantasy Novel (120k words)

```bash
# Epic scope, world-building
python3 scripts/orchestrator.py \
  --source source/myth.txt \
  --book-name shadow-realm \
  --genre fantasy \
  --target-words 120000

# Chapters will be ~4000-5000 words
# Magic system established early
# Total time: ~4-5 hours
```

## Troubleshooting Common Issues

### "Tests failed"

```bash
# Check which test failed
python3 tests/run_tests.py 2>&1 | grep FAIL

# Verify all files present
ls -R .claude/ config/ scripts/

# Reinstall if needed
git clone [repo] && cd bookcli
```

### "Quality gate fails repeatedly"

```bash
# Check specific issues
python3 scripts/quality_gate.py \
  workspace/book/chapters/chapter_001.md \
  --no-fix

# Review forbidden words list
cat .claude/forbidden-lists.md

# Manual fix and recheck
nano workspace/book/chapters/chapter_001.md
python3 scripts/quality_gate.py workspace/book/chapters/chapter_001.md
```

### "KDP formatter fails"

```bash
# Check pandoc
which pandoc || echo "Pandoc not installed"

# Install pandoc
# Ubuntu/Debian: sudo apt-get install pandoc
# Mac: brew install pandoc
# Windows: choco install pandoc

# HTML generation works without pandoc
# EPUB/DOCX require pandoc
```

### "Continuity errors"

```bash
# Review current continuity state
python3 scripts/continuity_tracker.py workspace/book summary

# Check specific character
cat workspace/book/continuity/characters.json | jq '.["Character Name"]'

# Manually fix continuity file if needed
nano workspace/book/continuity/characters.json
```

## Advanced Features

### Custom Genre Module

Create `config/genres/my-genre.md`:

```markdown
# My Custom Genre

## PACING
- Chapter length: 3000-4000 words
- [Your requirements...]

## STRUCTURE
- [Your structure...]

## FORBIDDEN
- [Genre-specific taboos...]
```

Use it:
```bash
python3 scripts/orchestrator.py \
  --source source/book.txt \
  --book-name my-book \
  --genre my-genre \
  --target-words 80000
```

### Integrate Claude API

Edit `scripts/orchestrator.py`, in `generate_chapter()`:

```python
import anthropic

def generate_chapter(self, chapter_num: int):
    client = anthropic.Anthropic(api_key="your-key")

    prompt = self._create_chapter_prompt(chapter_num, ...)

    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=16000,
        messages=[{"role": "user", "content": prompt}]
    )

    chapter_text = response.content[0].text
    chapter_file.write_text(chapter_text)
    # ... continue with quality checks
```

### Batch Processing

Process multiple books:

```bash
#!/bin/bash
for book in source/*.txt; do
    name=$(basename "$book" .txt)
    python3 scripts/orchestrator.py \
        --source "$book" \
        --book-name "$name" \
        --genre thriller \
        --target-words 80000
done
```

## Production Checklist

- [ ] Self-tests pass (`python3 tests/run_tests.py`)
- [ ] Source material prepared (in `source/`)
- [ ] Genre selected (thriller/romance/fantasy)
- [ ] Target word count set
- [ ] Orchestrator completed successfully
- [ ] All chapters generated
- [ ] Quality gates passed
- [ ] Continuity verified
- [ ] Manuscript assembled
- [ ] KDP formats created
- [ ] Final review of output files

## Next Steps

1. **Upload to KDP**: Use `output/book-name/book-name_kdp.html`
2. **Create cover**: Dimensions: 1600x2560 for ebook
3. **Set metadata**: Title, author, description, keywords
4. **Price**: Research competitive pricing
5. **Publish**: Submit for review

## Getting Help

- **Documentation**: Read `README.md` for full details
- **Examples**: Check `examples/` directory
- **Config files**: Review `.claude/` and `config/`
- **Logs**: Check `workspace/book-name/production.log`

## Tips for Best Results

1. **Source quality matters**: Better source = better output
2. **Genre consistency**: Stick to one primary genre
3. **Target length**: 60k-100k optimal for first run
4. **Review output**: Always do final human review
5. **Iterate**: Use output as strong first draft, refine

---

**Ready to create your first book? Start with the example:**

```bash
bash example_run.sh
```
