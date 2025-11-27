# Book Factory - Autonomous Book Production System

Transform public domain works into modern commercial fiction with zero manual intervention.

## Features

- **Fully Autonomous**: Zero check-ins required - makes all creative decisions
- **Quality Control**: Auto-fix for AI-tell words, purple prose, filter words
- **Continuity Tracking**: Maintains character, plot, and fact consistency
- **Multi-Genre**: Thriller, Romance, Fantasy modules (easily extensible)
- **KDP-Ready Output**: EPUB, DOCX, HTML, and Print PDF formats

## Quick Start

### 1. Run Self-Tests

```bash
python3 tests/run_tests.py
```

Verifies all components working correctly.

### 2. Create a Book (Full Automation)

```bash
python3 scripts/orchestrator.py \
  --source source/your-book.txt \
  --book-name my-thriller \
  --genre thriller \
  --target-words 80000
```

This runs the complete pipeline:
- Analysis
- Chapter planning
- Generation (creates prompts for Claude)
- Quality checking
- Assembly
- KDP formatting

### 3. Using Claude Code CLI (Interactive)

For chapter-by-chapter generation with Claude Code:

```bash
# Analyze source
/analyze-source source/your-book.txt my-book thriller

# Generate chapters
/write-chapter my-book 1
/write-chapter my-book 2
# ... continue for all chapters

# Assemble final book
/assemble-book my-book
```

## Project Structure

```
bookcli/
├── .claude/
│   ├── core-rules.md           # Essential writing rules
│   ├── forbidden-lists.md      # Words/phrases to avoid
│   └── commands/               # Slash commands
│       ├── analyze-source.md
│       ├── write-chapter.md
│       ├── quality-check.md
│       └── assemble-book.md
├── config/
│   ├── genres/                 # Genre-specific rules
│   │   ├── thriller.md
│   │   ├── romance.md
│   │   └── fantasy.md
│   └── craft/                  # Universal craft principles
│       └── scene-structure.md
├── scripts/
│   ├── orchestrator.py         # Master automation script
│   ├── quality_gate.py         # Auto-fix quality issues
│   ├── continuity_tracker.py   # Track story consistency
│   └── kdp_formatter.py        # Format for publishing
├── workspace/                  # Active projects
│   └── {book-name}/
│       ├── analysis/
│       ├── chapters/
│       ├── continuity/
│       └── summaries/
├── output/                     # Final manuscripts
└── source/                     # Source materials
```

## Quality Standards

The system enforces:

### Tier 1: Forbidden AI Words (Auto-removed)
delve, embark, leverage, harness, unlock, unveil, illuminate, elevate, foster, resonate, endeavor, unleash, multifaceted, intricate, pivotal, groundbreaking, transformative, paramount, seamless, comprehensive, holistic, myriad, plethora, tapestry, testament, beacon, robust, nuanced, synergy

### Tier 2: Purple Prose (Auto-fixed)
- "shivers down spine" → specific physical reaction
- "breath caught/hitched" → varied alternatives
- "heart hammered" → ONE per book maximum
- "electricity" (for attraction) → concrete sensation
- "drowning/lost in eyes" → specific detail

### Tier 3: Show Don't Tell (Auto-fixed)
Filter words removed: saw, heard, felt, noticed, realized, knew, thought, wondered, watched, seemed, appeared

Weak modifiers removed: very, really, quite, rather, somewhat, slightly, basically, actually, literally

### Quality Metrics

| Metric | Target | Enforced |
|--------|--------|----------|
| Forbidden words | 0 | Yes |
| Passive voice | <10% | Warned |
| Dialogue ratio | 25-45% | Warned |
| Avg sentence length | 12-18 words | Warned |
| Sentence variance | High (SD >6) | Warned |
| Adverb density | <1% | Warned |

## Genre Modules

### Thriller
- Fast pacing (2,000-3,500 words/chapter)
- Cliffhanger endings mandatory
- Try-fail cycles
- No convenient coincidences

### Romance
- Dual POV recommended
- HEA/HFN mandatory
- Chemistry building through banter + touch escalation
- Emotional arc = main plot

### Fantasy
- Magic system with clear rules and costs
- World-building through action (no info-dumps)
- Quest structure support
- Iceberg principle (know 10x more than shown)

## Advanced Usage

### Adding New Genre

Create `config/genres/your-genre.md` with:
- Pacing requirements
- Structure guidelines
- Forbidden patterns for this genre
- Required elements

### Custom Quality Rules

Edit `scripts/quality_gate.py` to add:
- Custom forbidden patterns
- Genre-specific checks
- Auto-fix strategies

### Continuity Extensions

Modify `scripts/continuity_tracker.py` to track:
- Magic system usage
- Timeline chronology
- World-building facts
- Custom story elements

## Dependencies

### Required
- Python 3.8+
- Standard library only for core functionality

### Optional (for full KDP formatting)
- Pandoc (`apt-get install pandoc` or `brew install pandoc`)
- XeLaTeX (for print PDF: `apt-get install texlive-xetex`)

### For Claude API Integration (Advanced)
```bash
pip install anthropic
```

Then modify `scripts/orchestrator.py` to call Claude API in `generate_chapter()`.

## Output Expectations

This system produces **publication-ready drafts** requiring:

✅ Produces:
- Consistent characters and continuity
- Genre-appropriate pacing and structure
- Clean prose free of AI-tell markers
- Proper formatting for KDP

⚠️ Still needs:
- Developmental edit review (overall arc cohesion)
- Line edit pass (prose refinement)
- Copy edit (grammar, consistency)
- Proofreading

**This is not a replacement for professional editing**, but reduces revision cycles significantly.

## Cost Estimates

For 80,000-word novel (≈25 chapters):
- Using Claude API: ~$15-25 depending on model
- Using Claude Code CLI: Included in Pro subscription
- Time: 2-4 hours autonomous operation

## Troubleshooting

### Quality Gate Fails
```bash
# Run with verbose output
python3 scripts/quality_gate.py workspace/book/chapters/chapter_001.md

# Manually review issues in output JSON
```

### Continuity Issues
```bash
# Check current state
python3 scripts/continuity_tracker.py workspace/book summary

# Review tracking files
cat workspace/book/continuity/*.json
```

### KDP Formatting Fails
```bash
# Check pandoc installed
which pandoc

# Test on single chapter
python3 scripts/kdp_formatter.py test.md output/
```

## Examples

See `examples/` directory for:
- Sample source material
- Complete generated book
- Quality reports
- Production logs

## Contributing

To add features:
1. Test with `tests/run_tests.py`
2. Update relevant documentation
3. Ensure autonomous operation (no manual intervention)

## License

MIT - Use for commercial or personal projects

## Credits

Based on craft principles from:
- Save The Cat! (Blake Snyder)
- Romancing The Beat (Gwen Hayes)
- Sanderson's Laws of Magic
- Scene & Sequel structure (Dwight Swain)
- Show Don't Tell principles
