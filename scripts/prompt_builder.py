#!/usr/bin/env python3
"""
Prompt Builder - Constructs enhanced prompts with few-shot examples

Integrates few-shot examples, quality requirements, and variation strategies
to build prompts that guide LLMs toward 8.5+/10 quality.
"""

import yaml
from pathlib import Path
from typing import List, Dict, Optional
from dataclasses import dataclass


@dataclass
class PromptComponents:
    """Components of an enhanced prompt"""
    base_prompt: str
    examples: List[Dict]
    requirements: str
    variation_focus: Optional[str] = None


class PromptBuilder:
    """Builds enhanced prompts with few-shot examples"""

    def __init__(self, config_dir="config"):
        self.config_dir = Path(config_dir)

        # Load configurations
        self.examples = self._load_examples()
        self.templates = self._load_templates()
        self.requirements = self._load_requirements()

    def _load_examples(self) -> Dict:
        """Load few-shot examples"""
        path = self.config_dir / "few_shot_examples.yaml"
        try:
            with open(path, 'r') as f:
                data = yaml.safe_load(f)
                return data.get('examples', {})
        except FileNotFoundError:
            print(f"Warning: {path} not found, using no examples")
            return {}

    def _load_templates(self) -> Dict:
        """Load prompt templates"""
        path = self.config_dir / "prompt_templates.yaml"
        try:
            with open(path, 'r') as f:
                data = yaml.safe_load(f)
                return data.get('templates', {})
        except FileNotFoundError:
            print(f"Warning: {path} not found, using basic templates")
            return {}

    def _load_requirements(self) -> Dict:
        """Load core quality requirements and ultra-tier prompts"""
        # Try loading ultra-tier prompts first
        ultra_path = self.config_dir / "ultra_tier_prompts.yaml"
        try:
            with open(ultra_path, 'r') as f:
                ultra_data = yaml.safe_load(f)
                return {
                    'core': ultra_data.get('core_requirements', ''),
                    'genre': ultra_data.get('genre_requirements', {}),
                    'word_count': ultra_data.get('word_count_guidance', ''),
                    'checkpoints': ultra_data.get('quality_checkpoints', ''),
                    'ultra_examples': ultra_data.get('examples', {})
                }
        except FileNotFoundError:
            # Fallback to prompt_templates.yaml
            path = self.config_dir / "prompt_templates.yaml"
            try:
                with open(path, 'r') as f:
                    data = yaml.safe_load(f)
                    return {
                        'core': data.get('core_requirements', ''),
                        'genre': {},
                        'word_count': '',
                        'checkpoints': '',
                        'ultra_examples': {}
                    }
            except FileNotFoundError:
                return {
                    'core': self._get_default_requirements(),
                    'genre': {},
                    'word_count': '',
                    'checkpoints': '',
                    'ultra_examples': {}
                }

    def _get_default_requirements(self) -> str:
        """Default quality requirements"""
        return """
CRITICAL QUALITY REQUIREMENTS:

1. SPECIFICITY: Replace ALL generic emotions
   ✗ "felt sad/angry/afraid"
   ✓ Physical sensation + specific memory + character action

2. SHOW THEMES: Never state "learned/realized/understood that"
   ✓ Show character making choice, reader infers meaning

3. VOICE: Include 3-5 fragments, vary rhythm, go obsessive on 1-2 details

4. TRUST READER: Leave questions unanswered, add contradictions
"""

    def build_chapter_prompt(
        self,
        chapter_num: int,
        outline: str,
        context: str,
        source_excerpt: str,
        variation_focus: Optional[str] = None,
        num_examples: int = 2,
        target_words: int = 3000,
        genre: str = "fantasy"
    ) -> str:
        """
        Build complete enhanced prompt for chapter generation

        Args:
            chapter_num: Chapter number
            outline: Chapter outline/plan
            context: Continuity context (previous chapters, character states)
            source_excerpt: Relevant source material excerpt
            variation_focus: Optional focus (emotion/voice/theme/depth/risk/balanced)
            num_examples: Number of few-shot examples to include (default: 2)
            target_words: Target word count for chapter (default: 3000)
            genre: Genre for genre-specific requirements (default: "fantasy")

        Returns:
            Complete prompt string
        """

        # Select appropriate examples
        examples = self._select_examples(variation_focus, num_examples)

        # Calculate word count bounds
        min_words = int(target_words * 0.85)
        max_words = int(target_words * 1.15)

        # Build prompt sections
        prompt_parts = []

        # Header
        prompt_parts.append(f"You are generating Chapter {chapter_num} of a {genre} novel.")
        prompt_parts.append(f"\nTARGET QUALITY: 8.0-8.5/10 - Exceptional, memorable, distinctive")
        prompt_parts.append(f"TARGET WORD COUNT: {target_words} words (Range: {min_words}-{max_words})\n")

        # Outline
        prompt_parts.append("CHAPTER OUTLINE:")
        prompt_parts.append(outline)
        prompt_parts.append("")

        # Context
        if context:
            prompt_parts.append("CONTINUITY CONTEXT:")
            prompt_parts.append(context)
            prompt_parts.append("")

        # Source material
        if source_excerpt:
            prompt_parts.append("SOURCE MATERIAL:")
            prompt_parts.append(source_excerpt)
            prompt_parts.append("")

        # Core quality requirements (with word count parameters filled in)
        core_reqs = self.requirements['core'].format(
            target_words=target_words,
            min_words=min_words,
            max_words=max_words
        )
        prompt_parts.append(core_reqs)
        prompt_parts.append("")

        # Genre-specific requirements
        if genre in self.requirements['genre']:
            prompt_parts.append(f"\n{genre.upper()}-SPECIFIC REQUIREMENTS:")
            prompt_parts.append(self.requirements['genre'][genre])
            prompt_parts.append("")

        # Word count guidance
        if self.requirements['word_count']:
            prompt_parts.append("\nWORD COUNT STRATEGY:")
            prompt_parts.append(self.requirements['word_count'].format(
                target_words=target_words,
                min_words=min_words,
                max_words=max_words
            ))
            prompt_parts.append("")

        # Few-shot examples
        if examples:
            prompt_parts.append("EXAMPLES OF TARGET QUALITY:")
            prompt_parts.append("="*60)
            for i, example in enumerate(examples, 1):
                prompt_parts.append(f"\nExample {i}: {example['name']}")
                prompt_parts.append(f"Score: {example['score']}/10")
                prompt_parts.append(f"\n{example['good_version']}")
                prompt_parts.append(f"\nWhy this works: {example['why_it_works'][:200]}...")
                prompt_parts.append("-"*60)

        # Variation focus (if specified)
        if variation_focus:
            focus_instruction = self._get_focus_instruction(variation_focus)
            prompt_parts.append(f"\nSPECIFIC FOCUS FOR THIS VERSION:")
            prompt_parts.append(focus_instruction)
            prompt_parts.append("")

        # Quality checkpoints
        if self.requirements['checkpoints']:
            prompt_parts.append("\nQUALITY CHECKPOINTS:")
            prompt_parts.append(self.requirements['checkpoints'].format(
                min_words=min_words,
                max_words=max_words
            ))
            prompt_parts.append("")

        # Final instructions
        prompt_parts.append("\nGenerate the complete chapter text using these techniques.")
        prompt_parts.append("Every sentence should be defensible as the best way to convey this moment.")
        prompt_parts.append("Trust the reader. Show don't tell. Go deep on obsessions.")
        prompt_parts.append(f"CRITICAL: Hit {min_words}-{max_words} word count. Add depth (not filler) if short.")

        return "\n".join(prompt_parts)

    def _select_examples(self, variation_focus: Optional[str], num_examples: int) -> List[Dict]:
        """Select appropriate few-shot examples based on focus"""

        # Prefer ultra-tier examples if available
        ultra_examples = self.requirements.get('ultra_examples', {})

        if ultra_examples:
            # Ultra-tier examples available - use them
            selected = []

            # Map focus to ultra-tier example keys
            ultra_mapping = {
                'emotion': ['emotion_focused', 'depth_focused'],
                'depth': ['depth_focused', 'emotion_focused'],
                'balanced': ['depth_focused', 'emotion_focused'],
                None: ['depth_focused', 'emotion_focused']
            }

            example_keys = ultra_mapping.get(variation_focus, ultra_mapping[None])

            for key in example_keys[:num_examples]:
                if key in ultra_examples:
                    example_data = ultra_examples[key]
                    selected.append({
                        'name': example_data.get('name', key.replace('_', ' ').title()),
                        'score': example_data.get('score', 8.5),
                        'good_version': example_data.get('text', ''),
                        'why_it_works': example_data.get('why_it_works', ''),
                        'technique': ''
                    })

            if selected:
                return selected

        # Fallback to regular examples
        if not self.examples:
            return []

        # Define example selection strategies
        strategies = {
            'emotion': ['emotional_specificity_grief', 'emotional_specificity_fear'],
            'voice': ['voice_distinctiveness_obsessive', 'prose_beauty_rhythm'],
            'theme': ['thematic_subtlety_paradox', 'risk_taking_structure'],
            'depth': ['voice_distinctiveness_obsessive', 'thematic_subtlety_paradox'],
            'risk': ['risk_taking_structure', 'thematic_subtlety_paradox'],
            'balanced': ['balanced_excellence', 'emotional_specificity_grief'],
            None: ['balanced_excellence', 'emotional_specificity_grief']  # Default
        }

        # Get example keys for this focus
        example_keys = strategies.get(variation_focus, strategies[None])

        # Build example list
        selected = []
        for key in example_keys[:num_examples]:
            if key in self.examples:
                example_data = self.examples[key]
                selected.append({
                    'name': key.replace('_', ' ').title(),
                    'score': example_data.get('score', 8.5),
                    'good_version': example_data.get('good_version', ''),
                    'why_it_works': example_data.get('why_it_works', ''),
                    'technique': example_data.get('technique', '')
                })

        return selected

    def _get_focus_instruction(self, variation_focus: str) -> str:
        """Get specific instruction for variation focus"""

        instructions = {
            'emotion': """
Focus on EMOTIONAL SPECIFICITY:
- Replace every "felt X" with physical sensation + memory + action
- Ground all emotions in body (throat, hands, chest, stomach)
- Use specific memories as anchors (funeral, hospital, specific moment)
- Show coping actions (swallowed, clenched, kept walking)

Example format: "Marcus's throat closed—that airless crush from the funeral.
He swallowed hard. Kept walking."
""",
            'voice': """
Focus on VOICE DISTINCTIVENESS:
- Include 5+ sentence fragments
- Use "Not X. Y." pattern 3+ times
- Vary sentence length (3-word minimum to 40-word maximum)
- Go obsessive on hands OR magic sensation (microscopic detail)
- Single-word paragraphs for emphasis

Create unmistakable rhythm and pattern.
""",
            'theme': """
Focus on THEMATIC SUBTLETY:
- DELETE every "learned/realized/understood that"
- Show character making choice without explaining why
- Add contradictions (says X, shows Y)
- Leave central question unanswered
- Use physical symbols without explanation

Reader does the interpretive work.
""",
            'depth': """
Focus on OBSESSIVE DEPTH:
- Spend 3× normal words on obsessive details
- Microscopic examination of hands OR magic sensation
- Quantify everything (exact counts, measurements, timings)
- Layer meanings (surface + implication + symbol)

Go absurdly deep on 1-2 elements.
""",
            'risk': """
Focus on RISK-TAKING:
- Non-linear time (start after event, withhold details)
- Deliberate omissions (don't explain everything)
- Ambiguous ending (resist resolution)
- Trust reader discomfort
- Break expected structure

Make bold structural choices.
""",
            'balanced': """
Focus on BALANCED EXCELLENCE:
- Combine all techniques at 8+ level
- Specific emotions with physical grounding
- Distinctive voice with rhythm variation
- Subtle themes shown through action
- Obsessive detail on 1-2 elements
- Trust the reader completely

All dimensions strong simultaneously.
"""
        }

        return instructions.get(variation_focus, instructions['balanced'])

    def get_variation_focuses(self) -> List[str]:
        """Get list of available variation focuses"""
        return ['emotion', 'voice', 'theme', 'depth', 'risk', 'balanced']


def main():
    """Test prompt builder"""
    builder = PromptBuilder()

    # Test building a prompt
    outline = """
    Chapter 3: Marcus confronts the Weavers demanding answers about his role.
    Learns he's meant to kill a human to prevent Veil collapse. Must decide
    whether to accept mission or find another way.
    """

    context = """
    Previous chapters: Marcus transported to magical world, survived Binding ritual,
    training with Kira (Mender mentor). Has discovered he's a "key" but doesn't
    know what that means yet.
    """

    source = """
    Core conflict: Marcus is idealistic, believes healing > killing. Weavers are
    pragmatic, see killing as necessary. Central paradox: healing through harm.
    """

    # Build baseline prompt
    print("BASELINE PROMPT")
    print("="*70)
    prompt = builder.build_chapter_prompt(
        chapter_num=3,
        outline=outline,
        context=context,
        source_excerpt=source,
        num_examples=2
    )
    print(prompt[:1000], "...\n\n")

    # Build emotion-focused variation
    print("EMOTION-FOCUSED VARIATION")
    print("="*70)
    prompt_emotion = builder.build_chapter_prompt(
        chapter_num=3,
        outline=outline,
        context=context,
        source_excerpt=source,
        variation_focus='emotion',
        num_examples=2
    )
    print(prompt_emotion[:1000], "...\n")


if __name__ == "__main__":
    main()
