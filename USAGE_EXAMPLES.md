# Usage Examples

## Example 1: Quick Thriller

Transform a mystery story into a fast-paced thriller:

```bash
# Download source (public domain)
curl -o source/sherlock.txt \
  "https://www.gutenberg.org/files/1661/1661-0.txt"

# Generate thriller
python3 scripts/orchestrator.py \
  --source source/sherlock.txt \
  --book-name deadly-detective \
  --genre thriller \
  --target-words 75000

# Check output
ls -lh output/deadly-detective/
```

**Expected Output:**
- 23-25 chapters, 2,500-3,500 words each
- Fast pacing with cliffhangers
- Try-fail cycles enforced
- Total time: ~2 hours with Claude

## Example 2: Romance Novel

Create a contemporary romance:

```bash
# Use romantic source material
python3 scripts/orchestrator.py \
  --source source/pride_prejudice.txt \
  --book-name modern-love \
  --genre romance \
  --target-words 90000

# Result: Dual POV, HEA ending
# 25-28 chapters following Romancing the Beat
```

**Key Features:**
- Chemistry building through banter
- Touch escalation tracked
- Emotional arc = main plot
- HEA mandatory

## Example 3: Epic Fantasy

Build a fantasy epic:

```bash
python3 scripts/orchestrator.py \
  --source source/mythology.txt \
  --book-name shadow-realms \
  --genre fantasy \
  --target-words 120000

# Result: Quest structure with magic system
# 30-35 chapters, 3,500-4,500 words each
```

**Includes:**
- Hard magic system with rules
- World-building through action
- Iceberg approach (know 10x more)
- Quest structure beats

## Example 4: Using Claude Code CLI

Interactive chapter-by-chapter generation:

```bash
# Start Claude Code in this directory
claude-code

# Then in Claude:
```

**Session:**
```
User: /analyze-source source/mystery.txt crime-thriller thriller

Claude: [Analyzes source, creates plan in workspace/crime-thriller/]

User: /write-chapter crime-thriller 1

Claude: [Generates chapter 1, runs quality gate, updates continuity]

User: /write-chapter crime-thriller 2

Claude: [Continues with chapter 2...]

# After all chapters complete
User: /assemble-book crime-thriller

Claude: [Assembles manuscript, creates KDP formats]
```

## Example 5: Batch Processing

Process multiple books:

```bash
#!/bin/bash
# batch_process.sh

for book in source/*.txt; do
    name=$(basename "$book" .txt)

    echo "Processing: $name"

    python3 scripts/orchestrator.py \
        --source "$book" \
        --book-name "$name" \
        --genre thriller \
        --target-words 80000

    echo "Completed: $name"
    echo "---"
done

echo "All books processed!"
ls -lh output/
```

## Example 6: Quality Checking Individual Chapter

Manual quality check:

```bash
# Check specific chapter
python3 scripts/quality_gate.py \
  workspace/my-book/chapters/chapter_005.md

# Output shows:
# - Forbidden words found: 2
# - Auto-fixes applied: 2
# - File updated: true
# - Pass: true

# Review the fixed file
cat workspace/my-book/chapters/chapter_005.md
```

## Example 7: Continuity Review

Check story consistency:

```bash
# Get overall summary
python3 scripts/continuity_tracker.py \
  workspace/my-book summary

# Check specific character
python3 scripts/continuity_tracker.py \
  workspace/my-book get_context 10 | \
  jq '.characters["Sarah"]'

# Review timeline
cat workspace/my-book/continuity/timeline.json | jq
```

## Example 8: Custom Genre

Create and use custom genre:

```bash
# Create genre file
cat > config/genres/space-opera.md << 'EOF'
# Space Opera Genre Module

## PACING
- Chapter length: 3,000-5,000 words
- Action-adventure rhythm
- Planet-hopping for variety

## STRUCTURE
- Ensemble cast dynamics
- Political backdrop, personal stakes
- Multiple POVs (4-6 characters)

## REQUIRED ELEMENTS
- Space travel/combat
- Diverse alien cultures
- Technology that feels lived-in
- Character arcs amid grand events

## FORBIDDEN
- Technology as magic without explanation
- Aliens as humans with makeup
- Technobabble solving problems
EOF

# Use it
python3 scripts/orchestrator.py \
  --source source/scifi.txt \
  --book-name star-wars-clone \
  --genre space-opera \
  --target-words 100000
```

## Example 9: Debugging Failed Quality Gate

When quality check fails:

```bash
# Run without auto-fix to see issues
python3 scripts/quality_gate.py \
  workspace/book/chapters/chapter_001.md \
  --no-fix | jq

# Review specific issue types
python3 scripts/quality_gate.py \
  workspace/book/chapters/chapter_001.md \
  --no-fix | jq '.remaining_issues.forbidden_words'

# Manual fix, then re-check
nano workspace/book/chapters/chapter_001.md

python3 scripts/quality_gate.py \
  workspace/book/chapters/chapter_001.md
```

## Example 10: Viewing Production Progress

Monitor active generation:

```bash
# Watch log in real-time
tail -f workspace/my-thriller/production.log

# Check status
cat workspace/my-thriller/status.json | jq

# Expected output:
{
  "book_name": "my-thriller",
  "genre": "thriller",
  "chapters_planned": 25,
  "chapters_completed": 12,
  "total_words": 42150,
  "stage": "generation",
  "errors": []
}

# Calculate progress
echo "Progress: 12/25 chapters (48%)"
```

## Example 11: KDP Upload Preparation

Final steps before publishing:

```bash
# Assemble and format
/assemble-book my-thriller

# Check generated files
ls -lh output/my-thriller/

# Validate EPUB (if epubcheck installed)
epubcheck output/my-thriller/my-thriller.epub

# Open HTML for final review
open output/my-thriller/my-thriller_kdp.html

# Upload to KDP:
# 1. Use my-thriller_kdp.html for interior
# 2. Create cover (1600x2560px)
# 3. Set metadata in KDP dashboard
# 4. Price and publish
```

## Example 12: Integration with Claude API

Full automation with API:

```python
# api_generate.py
import anthropic
import json
from pathlib import Path

client = anthropic.Anthropic(api_key="your-api-key")

# Load chapter prompt
prompt_file = Path("workspace/my-book/prompt_ch1.md")
prompt = prompt_file.read_text()

# Generate chapter
response = client.messages.create(
    model="claude-sonnet-4-20250514",
    max_tokens=16000,
    messages=[{
        "role": "user",
        "content": prompt
    }]
)

# Save chapter
chapter_file = Path("workspace/my-book/chapters/chapter_001.md")
chapter_file.write_text(response.content[0].text)

# Run quality gate
import subprocess
subprocess.run([
    "python3", "scripts/quality_gate.py",
    str(chapter_file)
])

print("Chapter 1 complete!")
```

Then run:
```bash
python3 api_generate.py
```

## Example 13: Testing System

Before production run:

```bash
# Full test suite
python3 tests/run_tests.py

# Expected output:
# ✓ All 6 config files present
# ✓ All 4 scripts present
# ✓ Quality gate fixed 5 issues
# ✓ Continuity tracker initialized
# ✓ Forbidden word detection working
# ✓ KDP formatter created HTML
#
# Tests Passed: 6
# Tests Failed: 0
#
# ✓ ALL TESTS PASSED - System ready for production

# If any test fails, review and fix before proceeding
```

## Example 14: Demo Run

Quick demonstration:

```bash
# Use included example
bash example_run.sh

# This will:
# 1. Run tests
# 2. Create sample source
# 3. Analyze and plan
# 4. Create chapter prompts
# 5. Show next steps

# Output:
# workspace/example-adventure/
#   analysis/plan.json
#   analysis/chapter_plan.json
#   prompt_ch1.md (ready for Claude)
```

## Example 15: Advanced - Multiple POVs

For dual POV romance:

```bash
# Create book with dual POV tracking
python3 scripts/orchestrator.py \
  --source source/romance.txt \
  --book-name dual-pov-romance \
  --genre romance \
  --target-words 90000

# In chapter prompts, system will alternate:
# Chapter 1: POV Character A
# Chapter 2: POV Character B
# Chapter 3: POV Character A
# etc.

# Continuity tracker maintains separate knowledge per character
```

## Common Workflows

### Workflow 1: Public Domain Adaptation
```
1. Find public domain book (Gutenberg)
2. Download to source/
3. Run orchestrator with target genre
4. Generate all chapters
5. Assemble and format
6. Publish on KDP
```

### Workflow 2: Original Concept
```
1. Write 5,000-10,000 word outline/synopsis
2. Save to source/
3. Run orchestrator
4. Generate chapters
5. Review and refine
6. Format and publish
```

### Workflow 3: Series Production
```
1. Create book 1 (establish world)
2. Save continuity files as series bible
3. Create book 2 (load book 1 continuity)
4. Maintain consistent characters/world
5. Repeat for series
```

## Tips & Tricks

### Speed Up Generation
- Use shorter target word count first (60k)
- Process chapters in parallel (multiple Claude instances)
- Cache continuity summaries

### Improve Quality
- Better source material = better output
- Review first 3 chapters before continuing
- Adjust genre module if needed

### Cost Optimization
- Use Claude Sonnet instead of Opus
- Reduce target word count
- Reuse continuity across series

---

For more examples, see:
- `README.md` - Full documentation
- `QUICKSTART.md` - Getting started
- `SYSTEM_SUMMARY.md` - Technical overview
