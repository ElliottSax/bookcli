# Ultra-Tier Fiction Generation System

**Goal**: Transform Book Factory from producing mid-tier publishable fiction (7/10) to producing top-tier, indistinguishable-from-human fiction (8.5+/10).

## System Overview

The ultra-tier system implements three core strategies:

1. **Multi-Dimensional Scoring** - Objective quality measurement across 5 dimensions
2. **Humanization Pipeline** - Apply authorial voice, emotional depth, thematic subtlety
3. **Multi-Pass Generation** - Generate multiple versions, select the best

## Components

### 1. Multi-Dimensional Scorer (`scripts/multi_dimensional_scorer.py`)

Scores fiction across 5 weighted dimensions:

- **Emotional Impact (25%)**: Specific vs generic emotions, physical grounding
- **Prose Beauty (25%)**: Sentence rhythm, metaphor, sensory language
- **Obsession Depth (20%)**: Recurring authorial obsessions (hands, magic sensation)
- **Thematic Subtlety (15%)**: Show vs tell, paradox preservation
- **Voice Distinctiveness (15%)**: Fragments, verbal tics, unique patterns

**Pass threshold**: 7.5/10 total

**Usage**:
```bash
python3 scripts/multi_dimensional_scorer.py path/to/chapter.md
```

**Output**:
```
Overall Score: 7.1/10 ✗ FAIL

Dimension Scores:
  emotional_impact: 6.0/10
  prose_beauty: 8.8/10
  obsession_depth: 7.9/10
  thematic_subtlety: 6.0/10
  voice_distinctiveness: 6.0/10
```

### 2. Humanizer (`scripts/humanizer.py`)

Applies authorial voice and humanization transformations:

**Transformations**:
- Inject obsessions (hands as identity, magic as physical sensation, philosophical paradox)
- Deepen emotions (replace generic with specific sensory memories)
- Soften themes (remove explicit statements, trust reader inference)
- Apply voice patterns (fragments, "Not X. Y.", single-word paragraphs)
- Add subtle inconsistencies (15% of chapters)

**Configuration**:
- `config/authorial_voice.yaml` - Voice profile, obsessions, verbal patterns
- `config/emotional_depth.yaml` - Emotion transformation templates
- `config/thematic_subtlety.yaml` - Theme reduction rules

**Usage**:
```bash
# Humanize a chapter file
python3 scripts/humanizer.py path/to/chapter.md chapter_number

# Test on sample text
python3 scripts/humanizer.py
```

**Key Finding**: Humanization as post-processing provides minimal improvement (+0.1 points). Most effective when integrated at generation time.

### 3. Multi-Pass Generator (`scripts/multi_pass_generator.py`)

Generates multiple chapter versions and selects the best:

**Process**:
1. Generate N versions (default: 5) with prompt variations
2. Score each version using multi_dimensional_scorer
3. Select version with highest total score
4. Return best version

**Prompt Variations**:
- v1: Baseline
- v2: Focus on physical sensations
- v3: Emphasize character voice
- v4: Lean into emotional specificity
- v5: Experiment with sentence rhythm
- v6: Show over tell
- v7: Obsessive detail depth

**Usage**:
```bash
python3 scripts/multi_pass_generator.py \\
  source/material.txt \\
  "Chapter outline here" \\
  chapter_number \\
  --output path/to/output.md \\
  --attempts 5 \\
  --provider anthropic
```

**Status**: Framework complete, needs integration with orchestrator's API calling infrastructure.

## Configuration Files

### `config/authorial_voice.yaml`

Defines distinctive authorial personality:

```yaml
primary_obsessions:
  hands_as_identity:
    frequency: 0.35  # 35% of passages
    manifestations:
      - "Characters examine hands during stress/reflection"
      - "Hands described with specific detail (scars, calluses, marks)"

  magic_as_physical_sensation:
    frequency: 0.40
    sensory_vocabulary:
      temperature: ["cold-silver", "warm-gold", "bone-deep heat"]
      texture: ["oily", "sticky", "sharp"]
      pain: ["burned", "ached", "split-lip wound"]

  philosophical_paradox:
    frequency: 0.25
    core_paradoxes:
      - "Healing through harm, harm through healing"
      - "Saving someone = destroying who they were"

verbal_patterns:
  sentence_constructions:
    - pattern: "Not X. Y."
      example: "Not fear. Exhaustion."
      frequency: "2-3 per chapter"

  fragments:
    frequency: "2-3 per chapter"
    examples: ["Counted them again.", "Died.", "Still here."]
```

### `config/emotional_depth.yaml`

Emotion transformation templates:

```yaml
emotions:
  grief:
    physical_sensations:
      - "throat closed—airless crushing"
      - "chest cavity hollowed out"
    memory_anchors:
      - "from the funeral"
      - "like when Dad died"
    character_actions:
      - "swallowed hard"
      - "kept walking"
    examples:
      - "Marcus's throat closed—that familiar airless crush from the funeral..."
```

### `config/thematic_subtlety.yaml`

Theme reduction and subtlety rules:

```yaml
heavy_handed_patterns:
  - "teaches (us|them|him|her) that"
  - "learned that"
  - "realized that"

transformations:
  explicit_to_symbolic:
    before: "Failure teaches limits, limits teach wisdom..."
    after: "Lily looked at her scars. They didn't hurt anymore..."
    technique: "Physical symbol + character acceptance + no explanation"
```

## Test Results

### Chapter Quality Baseline

**Chapter 1** (Portal setup):
- Original: 6.5/10
- After humanization: 6.5/10 (no change)
- Analysis: No emotions/themes to transform

**Chapter 3** (Training begins):
- Original: 7.0/10
- After humanization: 7.0/10 (minimal change)
- Analysis: Already decent quality, post-processing ineffective

### Multi-Pass Simulation

**Chapter 3** with 5 simulated attempts:
- Best version: 7.1/10 (+0.1 improvement)
- Improvement source: emotional_impact (5.5 → 6.0)
- Limitation: Simulation used post-processing, not true regeneration

**Key Insight**: Real multi-pass generation with different API calls and prompt variations would show larger improvements.

## Integration Guide

### Current Integration Status

1. **Orchestrator Integration**: `scripts/orchestrator.py` modified to call humanizer during quality checking
2. **Multi-Pass Integration**: Not yet integrated (framework exists but needs API connection)

### Recommended Integration Approach

**Option A: Post-Processing (Current)**
```python
# In orchestrator.quality_check_chapter():
1. Generate chapter
2. Humanize chapter
3. Quality gate check
4. Continue if passed
```

**Option B: Multi-Pass (Recommended)**
```python
# In orchestrator.generate_chapter():
1. Generate 5 versions with prompt variations
2. Score each version
3. Select best version
4. Quality gate check on best
5. If failed, regenerate with feedback
```

### To Enable Multi-Pass Generation

Modify `scripts/orchestrator.py`:

```python
def generate_chapter_multipass(self, chapter_num: int, attempts: int = 5):
    """Generate multiple versions and select best"""

    best_score = 0
    best_text = None

    for attempt in range(1, attempts + 1):
        # Generate version with variation
        prompt_variation = self._get_prompt_variation(attempt)

        chapter_text = self._call_api(
            prompt=self.base_prompt + prompt_variation,
            # ... other params
        )

        # Score it
        score = self.scorer.score(chapter_text)

        if score.total > best_score:
            best_score = score.total
            best_text = chapter_text

    return best_text, best_score
```

## Performance Impact

### Scoring Overhead
- Time per chapter: ~0.5 seconds
- Negligible impact on generation pipeline

### Humanization Overhead
- Time per chapter: ~1 second
- Applies multiple regex transformations
- Acceptable for post-processing

### Multi-Pass Overhead
- Time per chapter: ~5x normal generation time (for 5 attempts)
- Trades speed for quality
- Recommended for final production, not rapid iteration

## Next Steps

1. **Integrate Multi-Pass into Orchestrator**: Modify orchestrator to support --multi-pass flag
2. **Test on Real Generation**: Generate new chapters with multi-pass enabled
3. **Tune Scoring Weights**: Adjust dimension weights based on what matters most
4. **Expand Humanization Config**: Add more genre-specific obsessions and voice patterns
5. **Build Foundation System**: Implement 500k word foundation generator (iceberg principle)

## Advanced: Iceberg Principle (Not Yet Implemented)

The true ultra-tier approach requires:

1. **Foundation Development** (500k words):
   - Complete world bible
   - Character archaeology (full backstories)
   - Thematic web (paradox mapping)
   - Vision statement

2. **Depth-First Generation**:
   - Generate 10x content, use 1x
   - Multiple character POVs, select best
   - Alternate scene approaches, select most compelling

3. **Risk Budget**:
   - Deliberately break 3-5 conventions
   - Variable chapter lengths
   - Ambiguous endings
   - Unconventional structure

This level of sophistication requires fundamental architecture changes beyond post-processing or multi-pass selection.

## Conclusion

**What Works**:
- Multi-dimensional scoring provides objective quality measurement
- Multi-pass generation (when fully implemented) can improve quality by generating diversity and selecting best
- Configuration-driven humanization allows easy tuning of voice/style

**What Doesn't Work**:
- Post-processing humanization on already-generated text (minimal improvement)
- Trying to "fix" AI writing after generation

**The Path Forward**:
- Integrate multi-pass generation into orchestrator for real API calls
- Focus on generation-time quality (prompt engineering, multi-pass selection)
- Build foundation development system for true depth-first approach

**Current Capability**: 7.0/10 (competent mid-tier)
**Target Capability**: 8.5+/10 (top-tier, indistinguishable from human)
**Gap**: Requires generation-time improvements, not post-processing fixes
