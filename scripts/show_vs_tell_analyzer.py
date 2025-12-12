#!/usr/bin/env python3
"""
Show vs Tell Analyzer - Real Implementation
Part of Quality Improvement Plan P1

Analyzes text for showing (good) vs telling (bad) ratio.
Target from ultra_tier_prompts.yaml: Maximize showing, minimize telling
"""

import re
from typing import Dict, List, Tuple
from dataclasses import dataclass
from collections import defaultdict


@dataclass
class TellingExample:
    """Example of telling (to be minimized)"""
    text: str
    pattern_type: str
    line_number: int
    suggestion: str


@dataclass
class ShowTellAnalysis:
    """Results of show vs tell analysis"""
    total_words: int
    tell_count: int
    show_count: int
    show_ratio: float
    score: float
    pass_check: bool
    telling_examples: List[TellingExample]
    show_examples: List[str]

    def to_dict(self) -> Dict:
        return {
            'total_words': self.total_words,
            'tell_count': self.tell_count,
            'show_count': self.show_count,
            'show_ratio': round(self.show_ratio, 2),
            'score': round(self.score, 1),
            'pass': self.pass_check,
            'target_ratio': 0.75,
            'telling_examples': [
                {
                    'text': ex.text[:100],
                    'type': ex.pattern_type,
                    'suggestion': ex.suggestion
                }
                for ex in self.telling_examples[:10]
            ],
            'show_examples': self.show_examples[:10]
        }


class ShowVsTellAnalyzer:
    """
    Analyzes text for showing vs telling.

    TELLING (minimize):
    - "She felt scared" → emotion name with felt/was
    - "He thought about it" → internal state directly stated
    - "She was angry" → emotion as adjective

    SHOWING (maximize):
    - Dialogue with action/reaction
    - Physical manifestations
    - Specific actions and behaviors
    - Sensory details
    """

    def __init__(self, target_show_ratio: float = 0.75):
        """
        Initialize analyzer.

        Args:
            target_show_ratio: Minimum ratio of showing to total (default 75%)
        """
        self.target_show_ratio = target_show_ratio

        # TELLING patterns (bad - minimize these)
        self.tell_patterns = {
            'felt_emotion': {
                'pattern': r'\b(felt|feeling|feel)\s+(scared|afraid|angry|sad|happy|excited|nervous|anxious|worried|relieved|guilty|ashamed|embarrassed|proud|confident|confused|surprised|shocked|disgusted|frustrated|annoyed|grateful|hopeful|hopeless|helpless|overwhelmed|calm|peaceful|content|disappointed|devastated|heartbroken|jealous|envious|lonely|tired|exhausted|energized|motivated|inspired|bored|interested|curious|suspicious|uncertain|determined|defeated|triumphant)\w*',
                'suggestion': 'Replace with physical manifestation (heart rate, breathing, body reaction)'
            },
            'was_emotion': {
                'pattern': r'\b(was|were|am|is|being)\s+(scared|afraid|angry|sad|happy|excited|nervous|anxious|worried|relieved|guilty|ashamed|embarrassed|proud|confident|confused|surprised|shocked|disgusted|frustrated|annoyed|grateful|hopeful|hopeless|helpless|overwhelmed|calm|peaceful|content|disappointed|devastated|heartbroken|jealous|envious|lonely|tired|exhausted|energized|motivated|inspired|bored|interested|curious|suspicious|uncertain|determined|defeated|triumphant)\w*',
                'suggestion': 'Show emotion through action/dialogue/physical reaction'
            },
            'thought_verb': {
                'pattern': r'\b(thought|thinking|think|knew|know|knowing|realized|realize|realizing|understood|understand|understanding|believed|believe|believing|wondered|wonder|wondering|considered|consider|considering|remembered|remember|remembering|forgot|forget|forgetting|decided|decide|deciding|hoped|hope|hoping|wished|wish|wishing)\s+',
                'suggestion': 'Show through dialogue, action, or inference rather than stating thoughts'
            },
            'adverb_dialogue': {
                'pattern': r'"\s*[^"]+"\s*(?:he|she|they|[A-Z]\w+)\s+(said|asked|replied|answered|responded|whispered|shouted|yelled|screamed|muttered|murmured)\s+(angrily|sadly|happily|nervously|anxiously|excitedly|quietly|loudly|softly|harshly|gently|firmly|weakly|strongly|confidently|uncertainly|hesitantly|eagerly|reluctantly|impatiently|patiently)',
                'suggestion': 'Remove adverb, show emotion through dialogue content or action'
            },
            'made_feel': {
                'pattern': r'\bmade\s+(?:her|him|them|me)\s+(?:feel\s+)?(?:scared|afraid|angry|sad|happy|excited|nervous|anxious|worried)',
                'suggestion': 'Show the reaction instead of stating causation'
            },
            'emotion_filled': {
                'pattern': r'(?:fear|anger|sadness|happiness|joy|excitement|anxiety|worry|guilt|shame|pride|confusion|surprise|disgust|frustration)\s+(?:filled|washed over|consumed|overtook|flooded|swept through)',
                'suggestion': 'Show physical symptoms of the emotion'
            }
        }

        # SHOWING patterns (good - maximize these)
        self.show_patterns = {
            'dialogue_with_action': {
                'pattern': r'"[^"]{10,}"[^.!?]{0,50}(?:he|she|they|[A-Z]\w+)\s+(?:grabbed|slammed|whispered|muttered|turned|stepped|moved|ran|walked|froze|flinched|smiled|grinned|frowned|glanced|stared|looked|reached|pointed|shrugged|nodded|shook)',
                'weight': 2.0  # Dialogue + action is strong showing
            },
            'physical_reaction': {
                'pattern': r'\b(?:heart|pulse)\s+(?:raced|pounded|hammered|stuttered|skipped|stopped|quickened|slowed|thundered)\b',
                'weight': 2.0
            },
            'breathing_pattern': {
                'pattern': r'\b(?:breath|breathing)\s+(?:caught|quickened|shallow|deep|ragged|hitched|stopped|steadied|slowed)\b',
                'weight': 2.0
            },
            'body_language': {
                'pattern': r'\b(?:hands|fingers|fists?)\s+(?:trembled|shook|clenched|tightened|relaxed|curled|uncurled|gripped|released)\b',
                'weight': 1.5
            },
            'facial_expression': {
                'pattern': r'\b(?:eyes|jaw|mouth|face|lips)\s+(?:narrowed|widened|tightened|softened|hardened|curved|twisted|quirked|twitched)\b',
                'weight': 1.5
            },
            'specific_action': {
                'pattern': r'\b(?:grabbed|slammed|jerked|lunged|stumbled|staggered|recoiled|flinched|froze|spun|whirled|darted|rushed|bolted)\b',
                'weight': 1.0
            },
            'sensory_detail': {
                'pattern': r'\b(?:tasted|smelled|felt|sounded)\s+like\s+\w+',
                'weight': 1.5
            },
            'temperature_mention': {
                'pattern': r'\b\d+\.?\d*°[CF]\b',
                'weight': 1.0
            },
            'heart_rate_specific': {
                'pattern': r'\b\d+\s+(?:BPM|beats per minute)\b',
                'weight': 2.0
            },
            'counting_ritual': {
                'pattern': r'\bcounted?\s+\w+\s*:\s*\d+',
                'weight': 1.5
            },
            'micro_expression': {
                'pattern': r'\b(?:corner of|edge of|flicker of|ghost of|hint of|trace of)\s+(?:a\s+)?(?:smile|frown|smirk|grin|grimace)',
                'weight': 1.5
            },
            'body_temperature': {
                'pattern': r'\b(?:skin|face|cheeks|ears|neck|chest)\s+(?:went|turned|flushed|burned|cooled|froze|warmed)\b',
                'weight': 1.5
            }
        }

    def analyze_show_vs_tell(self, text: str) -> ShowTellAnalysis:
        """
        Analyze text for showing vs telling ratio.

        Args:
            text: Chapter or section text

        Returns:
            ShowTellAnalysis with counts and score
        """
        telling_examples = []
        show_examples = []

        # Count telling patterns (bad)
        tell_count = 0
        for pattern_name, pattern_info in self.tell_patterns.items():
            matches = list(re.finditer(pattern_info['pattern'], text, re.IGNORECASE))
            tell_count += len(matches)

            # Collect examples
            for match in matches[:5]:  # Up to 5 examples per pattern
                # Get surrounding context
                start = max(0, match.start() - 50)
                end = min(len(text), match.end() + 50)
                context = text[start:end].replace('\n', ' ').strip()

                telling_examples.append(TellingExample(
                    text=context,
                    pattern_type=pattern_name,
                    line_number=text[:match.start()].count('\n') + 1,
                    suggestion=pattern_info['suggestion']
                ))

        # Count showing patterns (good)
        show_count = 0
        for pattern_name, pattern_info in self.show_patterns.items():
            matches = list(re.finditer(pattern_info['pattern'], text, re.IGNORECASE))
            # Weight the count
            weight = pattern_info.get('weight', 1.0)
            show_count += len(matches) * weight

            # Collect examples
            for match in matches[:3]:  # Up to 3 examples per pattern
                start = max(0, match.start() - 50)
                end = min(len(text), match.end() + 50)
                context = text[start:end].replace('\n', ' ').strip()
                show_examples.append(f"{pattern_name}: {context[:100]}")

        # Calculate metrics
        total = tell_count + show_count
        if total == 0:
            # No patterns found - this is concerning but we'll give benefit of doubt
            show_ratio = 0.5
            score = 50.0
        else:
            show_ratio = show_count / total
            # Score: 75% showing = 100 points, scales linearly
            score = min(100.0, (show_ratio / self.target_show_ratio) * 100)

        pass_check = show_ratio >= self.target_show_ratio

        word_count = len(text.split())

        return ShowTellAnalysis(
            total_words=word_count,
            tell_count=tell_count,
            show_count=int(show_count),  # Convert from weighted float
            show_ratio=show_ratio,
            score=score,
            pass_check=pass_check,
            telling_examples=telling_examples,
            show_examples=show_examples
        )

    def get_score(self, text: str) -> float:
        """
        Get show vs tell score (0-100).

        Returns:
            Score based on showing ratio
        """
        analysis = self.analyze_show_vs_tell(text)
        return analysis.score

    def get_recommendations(self, text: str) -> List[str]:
        """
        Get specific recommendations for improving show/tell ratio.

        Args:
            text: Chapter text

        Returns:
            List of actionable recommendations
        """
        analysis = self.analyze_show_vs_tell(text)
        recommendations = []

        if analysis.pass_check:
            return ["Show vs tell ratio meets target. Excellent work!"]

        recommendations.append(
            f"Show ratio is {analysis.show_ratio:.1%}, target is {self.target_show_ratio:.0%}. "
            f"Need more showing, less telling."
        )

        # Count telling types
        telling_types = defaultdict(int)
        for example in analysis.telling_examples:
            telling_types[example.pattern_type] += 1

        # Provide specific recommendations based on most common issues
        if telling_types['felt_emotion'] > 0:
            recommendations.append(
                f"Found {telling_types['felt_emotion']} instances of 'felt [emotion]'. "
                f"Replace with physical reactions: heart rate, breathing, trembling, temperature."
            )

        if telling_types['was_emotion'] > 0:
            recommendations.append(
                f"Found {telling_types['was_emotion']} instances of 'was [emotion]'. "
                f"Show through actions, dialogue, or physical symptoms instead."
            )

        if telling_types['thought_verb'] > 0:
            recommendations.append(
                f"Found {telling_types['thought_verb']} instances of thought verbs "
                f"(thought, knew, realized). Use dialogue or inference instead."
            )

        if telling_types['adverb_dialogue'] > 0:
            recommendations.append(
                f"Found {telling_types['adverb_dialogue']} dialogue tags with adverbs. "
                f"Remove adverbs, let dialogue and action convey emotion."
            )

        # General recommendations
        recommendations.append(
            "Showing techniques to add:\n"
            "  - Physical reactions: heart rate changes, breathing patterns\n"
            "  - Body language: clenched fists, narrowed eyes, tightened jaw\n"
            "  - Specific actions: grabbed, slammed, froze, flinched\n"
            "  - Dialogue with action beats instead of emotion tags\n"
            "  - Sensory details: what character sees/hears/smells/feels"
        )

        return recommendations


if __name__ == "__main__":
    # Quick test
    analyzer = ShowVsTellAnalyzer()

    # Bad example - lots of telling
    bad_text = """
    Sarah felt scared when she entered the dark room. She was nervous about
    what she might find. Marcus thought it was a bad idea. He knew something
    was wrong. "Let's go," he said nervously. Sarah felt her fear growing.
    She was terrified now.
    """

    # Good example - showing
    good_text = """
    Sarah's heart hammered. 102 BPM. The dark room—couldn't see past the
    doorway. Hands trembling. She counted her breaths. Seven. Eight.
    Marcus grabbed her shoulder. "Let's go." Voice tight. Eyes darting
    to the shadows. Jaw clenched. His fingers dug into her arm.
    """

    print("=== Bad Example (Telling) ===")
    result = analyzer.analyze_show_vs_tell(bad_text)
    print(f"Score: {result.score:.1f}/100")
    print(f"Show ratio: {result.show_ratio:.1%}")
    print(f"Tell count: {result.tell_count}")
    print(f"Show count: {result.show_count}")

    print("\n=== Good Example (Showing) ===")
    result = analyzer.analyze_show_vs_tell(good_text)
    print(f"Score: {result.score:.1f}/100")
    print(f"Show ratio: {result.show_ratio:.1%}")
    print(f"Tell count: {result.tell_count}")
    print(f"Show count: {result.show_count}")
