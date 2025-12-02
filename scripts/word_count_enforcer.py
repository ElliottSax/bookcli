#!/usr/bin/env python3
"""
Word Count Enforcer - Validates word counts and suggests fixes

Ensures chapters hit target word count ±15% tolerance
Provides specific suggestions for expansion or cutting
"""

import re
from typing import Dict, List, Tuple
from dataclasses import dataclass


@dataclass
class Scene:
    """A scene within a chapter"""
    start: int
    end: int
    text: str
    word_count: int
    type: str  # 'action', 'dialogue', 'introspection', 'description'


class WordCountEnforcer:
    """Validates word count and suggests expansion/cutting strategies"""

    def __init__(self, tolerance: float = 0.15):
        """
        Args:
            tolerance: Acceptable variance from target (default: 15%)
        """
        self.tolerance = tolerance

    def validate(self, text: str, target: int) -> Dict:
        """
        Validate word count and suggest fixes

        Args:
            text: Chapter text
            target: Target word count

        Returns:
            Dictionary with validation results and suggestions
        """
        actual = len(text.split())
        min_words = int(target * (1 - self.tolerance))
        max_words = int(target * (1 + self.tolerance))

        # Check if within acceptable range
        passed = min_words <= actual <= max_words

        result = {
            'passed': passed,
            'actual': actual,
            'target': target,
            'min_acceptable': min_words,
            'max_acceptable': max_words,
            'variance': actual - target,
            'variance_pct': round((actual - target) / target * 100, 1)
        }

        if actual < min_words:
            # Too short - need to expand
            result['action'] = 'EXPAND'
            result['deficit'] = min_words - actual
            result['suggestions'] = self._suggest_expansion_points(text, result['deficit'])

        elif actual > max_words:
            # Too long - need to cut
            result['action'] = 'CUT'
            result['excess'] = actual - max_words
            result['suggestions'] = self._suggest_cut_points(text, result['excess'])

        else:
            # Just right
            result['action'] = 'NONE'
            result['suggestions'] = []

        return result

    def _suggest_expansion_points(self, text: str, deficit: int) -> List[Dict]:
        """
        Suggest where and how to expand text

        Strategies:
        1. Identify key emotional moments (expand with physical grounding)
        2. Find intimate scenes (expand with sensory details)
        3. Locate action sequences (expand with time dilation)
        4. Find sparse descriptions (expand with obsessive details)
        """
        suggestions = []

        # Analyze text structure
        scenes = self._identify_scenes(text)

        # Strategy 1: Find emotional moments (keywords: felt, realized, thought, wondered)
        emotional_scenes = [
            s for s in scenes
            if any(keyword in s.text.lower() for keyword in [
                'felt', 'realized', 'thought', 'wondered', 'knew', 'understood',
                'afraid', 'angry', 'sad', 'happy', 'nervous', 'anxious'
            ])
        ]

        if emotional_scenes:
            suggestions.append({
                'strategy': 'Expand emotional moments with physical grounding',
                'locations': [s.start for s in emotional_scenes[:3]],
                'words_to_add': deficit // 3,
                'technique': 'Replace generic emotions with physical sensations + memory + action',
                'example': '✗ "She felt nervous" → ✓ "Her hands trembled. She counted to ten, trying to steady them. Failed at seven."'
            })

        # Strategy 2: Find intimate moments (keywords: kiss, touch, held, close)
        intimate_scenes = [
            s for s in scenes
            if any(keyword in s.text.lower() for keyword in [
                'kiss', 'touch', 'held', 'close', 'hand', 'eyes', 'looked', 'stared'
            ])
        ]

        if intimate_scenes:
            suggestions.append({
                'strategy': 'Expand intimate moments with time dilation (3× longer)',
                'locations': [s.start for s in intimate_scenes[:3]],
                'words_to_add': deficit // 3,
                'technique': 'Add: temperature, duration, breath rate, heartbeat, distance measurement',
                'example': 'First kiss should be 200-400 words, not 50. Include all 5 senses + counting.'
            })

        # Strategy 3: Find dialogue-heavy sections (lots of quotes)
        dialogue_scenes = [s for s in scenes if s.type == 'dialogue']

        if dialogue_scenes:
            suggestions.append({
                'strategy': 'Add action beats and introspection between dialogue',
                'locations': [s.start for s in dialogue_scenes[:3]],
                'words_to_add': deficit // 4,
                'technique': 'Between dialogue lines, add: physical reactions, sensory details, internal thoughts',
                'example': '"I love you," she said. [ADD: Her voice caught. Elara counted three heartbeats before responding. Her hands trembled—visible this time, no hiding it.]'
            })

        # Strategy 4: Find short paragraphs (< 50 words) that could be expanded
        short_paragraphs = self._find_short_paragraphs(text, max_words=50)

        if short_paragraphs:
            suggestions.append({
                'strategy': 'Expand sparse descriptions with obsessive details',
                'locations': [p['start'] for p in short_paragraphs[:5]],
                'words_to_add': deficit // 5,
                'technique': 'Add: exact measurements, counting rituals, microscopic focus on hands/eyes',
                'example': 'Every description should include at least 2 sensory details and 1 specific measurement.'
            })

        # If still need more words, suggest new depth scenes
        remaining_deficit = deficit - sum(s.get('words_to_add', 0) for s in suggestions)
        if remaining_deficit > 100:
            suggestions.append({
                'strategy': 'Insert new depth scenes (not filler plot)',
                'locations': [],
                'words_to_add': remaining_deficit,
                'technique': 'Add scenes focused on: obsessive noticing, sensory grounding, internal processing',
                'example': 'Character examines hands in detail (200 words), counts heartbeats while waiting (150 words), catalogs room details when anxious (200 words).'
            })

        return suggestions

    def _suggest_cut_points(self, text: str, excess: int) -> List[Dict]:
        """
        Suggest where and how to cut text

        Strategies:
        1. Remove weak exposition (telling not showing)
        2. Cut redundant dialogue
        3. Condense repetitive descriptions
        4. Remove unnecessary adverbs and filter words
        """
        suggestions = []

        # Strategy 1: Find exposition (keywords: was, were, had been, etc.)
        exposition_markers = [
            r'\b(was|were|had been|had done|explained|realized that|understood that|knew that)\b'
        ]

        exposition_count = sum(
            len(re.findall(pattern, text, re.IGNORECASE))
            for pattern in exposition_markers
        )

        if exposition_count > 10:
            suggestions.append({
                'strategy': 'Cut weak exposition (telling instead of showing)',
                'estimated_savings': exposition_count * 5,  # Rough estimate
                'technique': 'Delete sentences with "was/were/had been". Show through action instead.',
                'example': '✗ "She was afraid of the dark" → ✓ "She avoided the unlit hallway. Took the long way."'
            })

        # Strategy 2: Find filter words (saw, heard, felt, noticed, seemed)
        filter_words = ['saw', 'heard', 'felt', 'noticed', 'seemed', 'appeared', 'looked like']
        filter_count = sum(
            len(re.findall(rf'\b{word}\b', text, re.IGNORECASE))
            for word in filter_words
        )

        if filter_count > 5:
            suggestions.append({
                'strategy': 'Remove filter words (saw/heard/felt/noticed)',
                'estimated_savings': filter_count * 3,
                'technique': 'Show the thing directly instead of filtering through perception',
                'example': '✗ "She saw the door open" → ✓ "The door opened"'
            })

        # Strategy 3: Find dialogue attribution overkill
        attribution_count = len(re.findall(r'"[^"]*"\s+\w+\s+said', text))

        if attribution_count > 20:
            suggestions.append({
                'strategy': 'Simplify dialogue attribution',
                'estimated_savings': attribution_count * 2,
                'technique': 'Use "said" or remove attribution entirely (implied speaker)',
                'example': '✗ "Hello," she muttered softly → ✓ "Hello," she said  OR  ✓ "Hello."'
            })

        # Strategy 4: Find redundant phrases
        redundant_patterns = [
            r'\bvery\s+\w+\b',
            r'\breally\s+\w+\b',
            r'\bquite\s+\w+\b',
            r'\bsomewhat\s+\w+\b',
            r'\brather\s+\w+\b',
        ]

        redundant_count = sum(
            len(re.findall(pattern, text, re.IGNORECASE))
            for pattern in redundant_patterns
        )

        if redundant_count > 5:
            suggestions.append({
                'strategy': 'Remove weak modifiers (very/really/quite)',
                'estimated_savings': redundant_count * 1,
                'technique': 'Delete modifiers, use stronger base words',
                'example': '✗ "very big" → ✓ "enormous"  OR  ✗ "really fast" → ✓ "sprinted"'
            })

        # Calculate total estimated savings
        total_savings = sum(s.get('estimated_savings', 0) for s in suggestions)

        # If still need to cut more, suggest condensing scenes
        if total_savings < excess:
            remaining = excess - total_savings
            suggestions.append({
                'strategy': 'Condense weakest scenes',
                'estimated_savings': remaining,
                'technique': 'Identify low-impact scenes and reduce by 30-50%',
                'example': 'Cut: redundant dialogue, unnecessary description, weak transitions'
            })

        return suggestions

    def _identify_scenes(self, text: str) -> List[Scene]:
        """
        Identify scenes within chapter text

        Uses paragraph breaks and content analysis to detect scene boundaries
        """
        scenes = []

        # Split by double newlines (paragraph breaks)
        paragraphs = re.split(r'\n\n+', text)

        current_pos = 0
        for para in paragraphs:
            if not para.strip():
                continue

            word_count = len(para.split())
            scene_type = self._classify_scene_type(para)

            scenes.append(Scene(
                start=current_pos,
                end=current_pos + len(para),
                text=para,
                word_count=word_count,
                type=scene_type
            ))

            current_pos += len(para) + 2  # Account for paragraph break

        return scenes

    def _classify_scene_type(self, text: str) -> str:
        """Classify a scene as action, dialogue, introspection, or description"""

        # Count dialogue (quotes)
        quote_count = text.count('"')

        # Count introspection keywords
        introspection_keywords = ['thought', 'wondered', 'realized', 'knew', 'remembered', 'felt']
        introspection_count = sum(text.lower().count(kw) for kw in introspection_keywords)

        # Count action verbs
        action_verbs = ['walked', 'ran', 'grabbed', 'threw', 'jumped', 'fell', 'struck', 'pushed']
        action_count = sum(text.lower().count(verb) for verb in action_verbs)

        # Classify based on dominant feature
        if quote_count > 4:
            return 'dialogue'
        elif introspection_count > 2:
            return 'introspection'
        elif action_count > 2:
            return 'action'
        else:
            return 'description'

    def _find_short_paragraphs(self, text: str, max_words: int = 50) -> List[Dict]:
        """Find paragraphs shorter than threshold"""
        paragraphs = re.split(r'\n\n+', text)
        short = []

        current_pos = 0
        for para in paragraphs:
            word_count = len(para.split())
            if 10 < word_count < max_words:  # Ignore very short (single sentences)
                short.append({
                    'start': current_pos,
                    'word_count': word_count,
                    'text': para[:100] + '...' if len(para) > 100 else para
                })

            current_pos += len(para) + 2

        return short

    def format_report(self, validation: Dict) -> str:
        """Format validation results as readable report"""
        lines = []

        lines.append("=" * 70)
        lines.append("WORD COUNT VALIDATION")
        lines.append("=" * 70)
        lines.append("")

        # Stats
        lines.append(f"Target: {validation['target']} words")
        lines.append(f"Acceptable range: {validation['min_acceptable']}-{validation['max_acceptable']} words (±{int(self.tolerance*100)}%)")
        lines.append(f"Actual: {validation['actual']} words")
        lines.append(f"Variance: {validation['variance']:+d} words ({validation['variance_pct']:+.1f}%)")
        lines.append(f"Status: {'✓ PASS' if validation['passed'] else '✗ FAIL'}")
        lines.append("")

        # Action needed
        if validation['action'] == 'EXPAND':
            lines.append(f"ACTION REQUIRED: ADD {validation['deficit']} words")
            lines.append("")
            lines.append("EXPANSION STRATEGIES:")
            for i, suggestion in enumerate(validation['suggestions'], 1):
                lines.append(f"\n{i}. {suggestion['strategy']}")
                if 'words_to_add' in suggestion:
                    lines.append(f"   Target: +{suggestion['words_to_add']} words")
                lines.append(f"   Technique: {suggestion['technique']}")
                lines.append(f"   Example: {suggestion['example']}")

        elif validation['action'] == 'CUT':
            lines.append(f"ACTION REQUIRED: CUT {validation['excess']} words")
            lines.append("")
            lines.append("CUTTING STRATEGIES:")
            for i, suggestion in enumerate(validation['suggestions'], 1):
                lines.append(f"\n{i}. {suggestion['strategy']}")
                if 'estimated_savings' in suggestion:
                    lines.append(f"   Savings: ~{suggestion['estimated_savings']} words")
                lines.append(f"   Technique: {suggestion['technique']}")
                lines.append(f"   Example: {suggestion['example']}")

        else:
            lines.append("No action needed - word count within acceptable range ✓")

        return '\n'.join(lines)


def main():
    """Test the word count enforcer"""

    # Test: Too short
    short_text = " ".join(["Word"] * 1200)  # 1200 words

    # Test: Too long
    long_text = " ".join(["Word"] * 4500)  # 4500 words

    # Test: Just right
    good_text = " ".join(["Word"] * 3200)  # 3200 words

    enforcer = WordCountEnforcer(tolerance=0.15)

    print("TEST 1: Too short (1200 words, target 3500)")
    print("-" * 70)
    result1 = enforcer.validate(short_text, target=3500)
    print(enforcer.format_report(result1))
    print("\n" * 2)

    print("TEST 2: Too long (4500 words, target 3500)")
    print("-" * 70)
    result2 = enforcer.validate(long_text, target=3500)
    print(enforcer.format_report(result2))
    print("\n" * 2)

    print("TEST 3: Just right (3200 words, target 3500)")
    print("-" * 70)
    result3 = enforcer.validate(good_text, target=3500)
    print(enforcer.format_report(result3))


if __name__ == "__main__":
    main()
