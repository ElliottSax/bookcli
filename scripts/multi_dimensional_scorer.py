#!/usr/bin/env python3
"""
Multi-Dimensional Scorer - Scores fiction across multiple quality dimensions

Evaluates vision alignment, emotional impact, prose beauty, obsession depth,
thematic complexity, and overall quality.
"""

import re
import yaml
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Dict
from collections import Counter

@dataclass
class ScoringResult:
    """Result of multi-dimensional scoring"""
    scores: Dict[str, float] = field(default_factory=dict)
    total: float = 0.0
    passed: bool = False
    details: Dict = field(default_factory=dict)

    def __str__(self):
        lines = [f"Overall Score: {self.total:.1f}/10 {'✓ PASS' if self.passed else '✗ FAIL'}"]
        lines.append("\nDimension Scores:")
        for dimension, score in self.scores.items():
            lines.append(f"  {dimension}: {score:.1f}/10")
        return '\n'.join(lines)

class MultiDimensionalScorer:
    """Scores fiction across multiple dimensions"""

    def __init__(self, config_dir="config"):
        """Initialize with configuration files"""
        self.config_dir = Path(config_dir)

        # Load configurations
        try:
            self.voice_config = self._load_yaml('authorial_voice.yaml')
            self.emotion_config = self._load_yaml('emotional_depth.yaml')
            self.theme_config = self._load_yaml('thematic_subtlety.yaml')
        except FileNotFoundError as e:
            print(f"Warning: Could not load config file: {e}")
            self.voice_config = {}
            self.emotion_config = {}
            self.theme_config = {}

    def _load_yaml(self, filename):
        """Load YAML configuration file"""
        path = self.config_dir / filename
        with open(path, 'r') as f:
            return yaml.safe_load(f)

    def score(self, text: str) -> ScoringResult:
        """
        Comprehensive scoring across all dimensions

        Args:
            text: Chapter or passage text to score

        Returns:
            ScoringResult with scores and details
        """

        scores = {
            'emotional_impact': self._score_emotion(text),
            'prose_beauty': self._score_prose(text),
            'obsession_depth': self._score_obsessions(text),
            'thematic_subtlety': self._score_themes(text),
            'voice_distinctiveness': self._score_voice(text),
        }

        # Weighted total
        weights = {
            'emotional_impact': 0.25,
            'prose_beauty': 0.25,
            'obsession_depth': 0.20,
            'thematic_subtlety': 0.15,
            'voice_distinctiveness': 0.15,
        }

        total = sum(scores[k] * weights[k] for k in scores)

        return ScoringResult(
            scores=scores,
            total=total,
            passed=total >= 7.5,  # Pass threshold
            details={'weights': weights}
        )

    def _score_emotion(self, text: str) -> float:
        """Score emotional specificity and impact"""

        score = 0.0

        # Count specific vs generic emotions
        if self.emotion_config:
            generic_patterns = self.emotion_config.get('generic_emotion_patterns', [])
            generic_count = sum(
                len(re.findall(pattern, text, re.IGNORECASE))
                for pattern in generic_patterns
            )

            # Detect specific emotional moments
            specific_markers = [
                'throat closed',
                'chest tightened',
                'hands shook',
                'stomach dropped',
                'breath caught',
            ]

            specific_count = sum(
                text.lower().count(marker)
                for marker in specific_markers
            )

            # Score based on ratio
            total_emotions = generic_count + specific_count
            if total_emotions > 0:
                specificity_ratio = specific_count / total_emotions
                score += specificity_ratio * 4.0  # Up to 4 points
            else:
                score += 2.0  # Default if no emotions found

            # Check for memory anchors
            memory_markers = ['remembered', 'like when', 'reminded', 'that smell', 'that feeling']
            memory_count = sum(text.lower().count(m) for m in memory_markers)
            score += min(memory_count * 0.5, 2.0)  # Up to 2 points

            # Check for coping actions
            action_markers = ['swallowed', 'clenched', 'forced', 'kept', "didn't let"]
            action_count = sum(text.lower().count(m) for m in action_markers)
            score += min(action_count * 0.5, 2.0)  # Up to 2 points

            # Physical grounding
            body_parts = ['hands', 'throat', 'chest', 'stomach', 'eyes']
            body_count = sum(text.lower().count(part) for part in body_parts)
            score += min(body_count * 0.2, 2.0)  # Up to 2 points

        else:
            score = 5.0  # Default if config not loaded

        return min(score, 10.0)

    def _score_prose(self, text: str) -> float:
        """Score prose beauty and craft"""

        score = 0.0

        # Sentence rhythm variety
        sentences = re.split(r'[.!?]+', text)
        sentence_lengths = [len(s.split()) for s in sentences if s.strip()]

        if sentence_lengths:
            # Check for variety in length
            min_len = min(sentence_lengths)
            max_len = max(sentence_lengths)
            avg_len = sum(sentence_lengths) / len(sentence_lengths)

            variety = (max_len - min_len) / avg_len if avg_len > 0 else 0
            score += min(variety * 1.5, 2.5)  # Up to 2.5 points for variety

            # Fragments present (very short sentences)
            fragments = sum(1 for l in sentence_lengths if l <= 3)
            score += min(fragments * 0.3, 1.5)  # Up to 1.5 points

        # Word choice precision (look for compound descriptions)
        compound_pattern = r'\w+-\w+'  # hyphenated descriptions
        compounds = len(re.findall(compound_pattern, text))
        score += min(compounds * 0.2, 2.0)  # Up to 2 points

        # Metaphor/simile presence
        metaphor_markers = [' like ', ' as ', ' seemed ', ' felt like ']
        metaphors = sum(text.lower().count(m) for m in metaphor_markers)
        score += min(metaphors * 0.3, 2.0)  # Up to 2 points

        # Sensory language
        sensory_words = ['cold', 'warm', 'sharp', 'soft', 'rough', 'smooth', 'bitter', 'sweet']
        sensory_count = sum(text.lower().count(w) for w in sensory_words)
        score += min(sensory_count * 0.2, 2.0)  # Up to 2 points

        return min(score, 10.0)

    def _score_obsessions(self, text: str) -> float:
        """Score obsessive depth (hands, magic sensation)"""

        score = 0.0

        if not self.voice_config:
            return 5.0

        # Check hands obsession
        hand_mentions = text.lower().count('hand')
        hand_imagery = sum([
            text.lower().count('fingers'),
            text.lower().count('palm'),
            text.lower().count('knuckles'),
            text.lower().count('fist'),
        ])

        hands_total = hand_mentions + hand_imagery
        score += min(hands_total * 0.4, 3.0)  # Up to 3 points

        # Check for hand detail (not just mentions)
        hand_detail_markers = ['marked', 'scarred', 'trembled', 'clenched', 'examined']
        hand_details = sum(
            1 for marker in hand_detail_markers
            if marker in text.lower() and 'hand' in text.lower()
        )
        score += min(hand_details * 0.8, 2.0)  # Up to 2 points

        # Check magic sensation obsession
        sensation_words = [
            'burned', 'ached', 'pulsed', 'throbbed', 'seared',
            'channels', 'channeling', 'channeled'
        ]
        sensation_count = sum(text.lower().count(w) for w in sensation_words)
        score += min(sensation_count * 0.3, 3.0)  # Up to 3 points

        # Check for obsessive detail (longer descriptions)
        # Look for magic description paragraphs
        paragraphs = text.split('\n\n')
        magic_paragraphs = [
            p for p in paragraphs
            if 'channel' in p.lower() or 'magic' in p.lower()
        ]

        if magic_paragraphs:
            avg_magic_para_length = sum(len(p.split()) for p in magic_paragraphs) / len(magic_paragraphs)
            if avg_magic_para_length > 50:  # Obsessively detailed
                score += 2.0

        return min(score, 10.0)

    def _score_themes(self, text: str) -> float:
        """Score thematic subtlety (show vs tell)"""

        score = 5.0  # Start at middle

        if not self.theme_config:
            return score

        # Penalize heavy-handed statements
        heavy_patterns = self.theme_config.get('heavy_handed_patterns', [])
        heavy_count = sum(
            len(re.findall(pattern, text, re.IGNORECASE))
            for pattern in heavy_patterns
        )

        score -= heavy_count * 1.0  # -1 point per heavy-handed statement

        # Reward subtle techniques
        # Symbolic moments (scars, hands as symbols)
        if 'scar' in text.lower() and 'reminded' not in text.lower():
            score += 1.0  # Symbolic object without explaining

        # Unanswered questions
        unanswered_pattern = r'\?\s*\n\s*\n'  # Question followed by paragraph break
        unanswered = len(re.findall(unanswered_pattern, text))
        score += min(unanswered * 1.0, 2.0)

        # Paradox preservation
        paradox_markers = [
            'both true',
            'yes and no',
            'neither',
            'both right',
            'both wrong',
        ]
        paradoxes = sum(text.lower().count(m) for m in paradox_markers)
        score += min(paradoxes * 1.5, 2.0)

        return max(0, min(score, 10.0))

    def _score_voice(self, text: str) -> float:
        """Score voice distinctiveness"""

        score = 0.0

        # Fragment usage
        sentences = re.split(r'[.!?]+', text)
        fragments = sum(1 for s in sentences if s.strip() and len(s.split()) <= 3)
        score += min(fragments * 0.5, 2.0)

        # "Not X. Y." pattern
        not_x_y_pattern = r'\bNot \w+\.\s+\w+'
        not_x_y_count = len(re.findall(not_x_y_pattern, text))
        score += min(not_x_y_count * 1.0, 2.0)

        # Single-word paragraphs
        paragraphs = text.split('\n\n')
        single_word = sum(1 for p in paragraphs if len(p.split()) == 1)
        score += min(single_word * 1.5, 2.0)

        # Favorite words presence
        favorite_words = ['thread', 'pulse', 'fracture', 'visceral']
        favorite_count = sum(text.lower().count(w) for w in favorite_words)
        score += min(favorite_count * 0.3, 2.0)

        # Synesthesia (describing one sense with another)
        synesthesia_patterns = [
            r'cold \w+ light',
            r'sharp \w+ smell',
            r'heavy silence',
        ]
        synesthesia_count = sum(
            len(re.findall(pattern, text, re.IGNORECASE))
            for pattern in synesthesia_patterns
        )
        score += min(synesthesia_count * 1.0, 2.0)

        return min(score, 10.0)

def main():
    """Test scorer on sample text or file"""
    import sys

    scorer = MultiDimensionalScorer()

    # Check if file path provided
    if len(sys.argv) > 1:
        file_path = sys.argv[1]
        with open(file_path, 'r') as f:
            text = f.read()
        print(f"SCORING FILE: {file_path}")
    else:
        # Use sample text
        text = """
        Marcus walked to the Mender wing, hands clenched.

        His channels ached. Not sharp—deeper. Bone-deep. The kind that made you want
        to crack every joint, release pressure that had nowhere to go.

        The binding mark pulsed. Three-beat rhythm. His channels recognized magic like
        tongue finding split-lip wound. There. Always there.

        Evan's workshop stood open. Green light pulsed inside—healing magic, constant.

        Lily lay unconscious. Black corruption spread across her skin like frost on windows.

        Marcus stopped.

        Looked at his hands.

        Marked. Scarred. Capable of healing or harm. Had separated Lyara and Thomas.
        Had taught Lily technique that led here.

        What good were his hands?

        Evan glanced up. "Your channels?"

        "Still hurt."

        "They will. Weeks." Evan's hands moved through air, finding threads. "Scar tissue
        doesn't flex like healthy channel."

        His hands knew their purpose.

        Marcus looked at his own hands. Fifteen years old. Already carrying maps of
        every choice.

        They hurt.

        They'd keep hurting.

        Tomorrow, he'd use them anyway.
        """
        print("SCORING SAMPLE TEXT:")

    print("="*60)

    result = scorer.score(text)

    print(result)
    print("\nDetails:")
    for dimension, score in result.scores.items():
        print(f"  {dimension}: {score:.1f}/10")
        if score >= 8.0:
            print(f"    ✓ Excellent")
        elif score >= 7.0:
            print(f"    ✓ Good")
        elif score >= 6.0:
            print(f"    ~ Adequate")
        else:
            print(f"    ✗ Needs improvement")

if __name__ == '__main__':
    main()
