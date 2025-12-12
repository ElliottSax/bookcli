#!/usr/bin/env python3
"""
Physical Grounding Checker - Real Implementation
Part of Quality Improvement Plan P1

Verifies all emotions have physical manifestations.
Requirement from ultra_tier_prompts.yaml: "Ground EVERYTHING physically"
"""

import re
from typing import Dict, List, Tuple
from dataclasses import dataclass


@dataclass
class GroundingViolation:
    """Details of an ungrounded emotion"""
    sentence: str
    emotion_word: str
    line_number: int
    context: str


@dataclass
class GroundingAnalysis:
    """Results of physical grounding analysis"""
    total_emotions: int
    grounded_emotions: int
    ungrounded_emotions: int
    grounding_ratio: float
    violations: List[GroundingViolation]
    score: float
    pass_check: bool

    def to_dict(self) -> Dict:
        return {
            'total_emotions': self.total_emotions,
            'grounded_emotions': self.grounded_emotions,
            'ungrounded_emotions': self.ungrounded_emotions,
            'grounding_ratio': round(self.grounding_ratio, 2),
            'score': round(self.score, 1),
            'pass': self.pass_check,
            'target': '100% grounded',
            'violations': [
                {
                    'sentence': v.sentence[:150],
                    'emotion': v.emotion_word,
                    'line': v.line_number
                }
                for v in self.violations[:10]
            ]
        }


class PhysicalGroundingChecker:
    """
    Checks that all emotions are grounded in physical descriptions.

    Bad: "She felt afraid."
    Good: "Heart hammering 110 BPM. Hands trembling. Afraid."

    Bad: "He was happy."
    Good: "The grin split his face before he could stop it. Chest warm."
    """

    def __init__(self):
        # Emotion words that require physical grounding
        self.emotion_words = {
            # Fear/anxiety
            'afraid', 'scared', 'terrified', 'frightened', 'nervous',
            'anxious', 'worried', 'panicked', 'fearful', 'uneasy',

            # Anger
            'angry', 'furious', 'enraged', 'mad', 'irritated',
            'annoyed', 'frustrated', 'rage', 'anger', 'pissed',

            # Sadness
            'sad', 'depressed', 'miserable', 'unhappy', 'heartbroken',
            'devastated', 'grief', 'sorrow', 'melancholy',

            # Joy/happiness
            'happy', 'joyful', 'delighted', 'pleased', 'cheerful',
            'elated', 'ecstatic', 'joy', 'happiness', 'bliss',

            # Love/affection
            'love', 'loved', 'adore', 'cherish', 'affection',
            'tender', 'fondness', 'desire', 'longing', 'yearning',

            # Excitement
            'excited', 'thrilled', 'eager', 'enthusiastic',
            'anticipation', 'exhilarated',

            # Disgust
            'disgusted', 'repulsed', 'revolted', 'nauseous',

            # Surprise
            'surprised', 'shocked', 'startled', 'astonished',
            'amazed', 'stunned',

            # Shame/embarrassment
            'ashamed', 'embarrassed', 'humiliated', 'mortified',

            # Confusion
            'confused', 'bewildered', 'puzzled', 'perplexed',
        }

        # Physical grounding indicators
        self.physical_markers = {
            # Cardiovascular
            'heart', 'heartbeat', 'pulse', 'BPM', 'beats per minute',
            'chest', 'pounding', 'racing', 'hammering', 'fluttering',
            'throbbing', 'thumping',

            # Respiratory
            'breath', 'breathing', 'breathe', 'inhale', 'exhale',
            'lungs', 'air', 'gasp', 'pant', 'wheeze', 'shallow',

            # Temperature
            'hot', 'cold', 'warm', 'cool', 'temperature', 'sweat',
            'sweating', 'shiver', 'shivering', 'chill', 'flush',
            'flushed', 'burning', 'freezing', '°C', '°F',

            # Muscular/skeletal
            'trembl', 'shak', 'clench', 'tense', 'tight', 'rigid',
            'stiff', 'muscles', 'fist', 'jaw', 'shoulders', 'knees',
            'weak', 'knot', 'coil',

            # Skin/touch
            'skin', 'goosebumps', 'prickling', 'tingling', 'numb',
            'crawl', 'electric', 'touch', 'pressure',

            # Digestive/visceral
            'stomach', 'nausea', 'bile', 'throat', 'gulp', 'swallow',
            'churn', 'twist', 'knot', 'hollow', 'sink', 'drop',

            # Eyes/tears
            'tears', 'crying', 'eyes burn', 'vision blur', 'blink',
            'sting', 'water', 'wet',

            # Voice/speech
            'voice crack', 'whisper', 'choke', 'stammer', 'stutter',
            'quiver', 'rasp', 'hoarse', 'thick',

            # Movement/behavior
            'froze', 'freeze', 'frozen', 'still', 'motionless',
            'flinch', 'recoil', 'step back', 'stumble', 'stagger',

            # Hands/extremities
            'hands', 'fingers', 'palm', 'grip', 'grasp',
            'feet', 'toes', 'curl',
        }

        # Common "telling" phrases to flag (these are violations)
        self.telling_patterns = [
            r'\b(?:felt|feeling|feel)\s+({emotions})',
            r'\b(?:was|were|am|is|being)\s+({emotions})',
            r'\bmade\s+(?:her|him|them)\s+(?:feel\s+)?({emotions})',
            r'\b({emotions})\s+(?:filled|washed over|consumed|overtook)',
        ]

    def check_physical_grounding(self, text: str) -> GroundingAnalysis:
        """
        Check if all emotions in text have physical grounding.

        Args:
            text: Chapter or section text

        Returns:
            GroundingAnalysis with violations and score
        """
        violations = []
        grounded_count = 0
        total_emotions = 0

        # Split into sentences
        sentences = self._split_sentences(text)

        for i, sentence in enumerate(sentences):
            sentence_lower = sentence.lower()

            # Check if sentence contains emotion words
            emotions_found = [
                word for word in self.emotion_words
                if re.search(rf'\b{word}\w*\b', sentence_lower)
            ]

            if not emotions_found:
                continue

            total_emotions += len(emotions_found)

            # Check context (current + next 2 sentences) for physical markers
            context_window = 3
            context_start = max(0, i - 1)
            context_end = min(len(sentences), i + context_window)
            context = ' '.join(sentences[context_start:context_end]).lower()

            # Check if ANY physical marker appears in context
            has_physical = any(
                marker.lower() in context
                for marker in self.physical_markers
            )

            if has_physical:
                grounded_count += len(emotions_found)
            else:
                # This is a violation
                for emotion in emotions_found:
                    violations.append(GroundingViolation(
                        sentence=sentence.strip(),
                        emotion_word=emotion,
                        line_number=i + 1,
                        context=sentences[context_start:context_end][0][:200] if context_start < len(sentences) else ""
                    ))

        # Calculate metrics
        if total_emotions == 0:
            # No emotions found - this might be an issue itself, but we'll pass
            grounding_ratio = 1.0
            score = 100.0
            pass_check = True
        else:
            grounding_ratio = grounded_count / total_emotions
            score = grounding_ratio * 100
            pass_check = grounding_ratio >= 0.95  # Allow 5% ungrounded for edge cases

        return GroundingAnalysis(
            total_emotions=total_emotions,
            grounded_emotions=grounded_count,
            ungrounded_emotions=len(violations),
            grounding_ratio=grounding_ratio,
            violations=violations,
            score=score,
            pass_check=pass_check
        )

    def get_recommendations(self, text: str) -> List[str]:
        """
        Get specific recommendations for improving physical grounding.

        Args:
            text: Chapter text

        Returns:
            List of actionable recommendations
        """
        analysis = self.check_physical_grounding(text)
        recommendations = []

        if analysis.pass_check:
            return ["Physical grounding meets target. Excellent work!"]

        recommendations.append(
            f"Found {analysis.ungrounded_emotions} ungrounded emotions. "
            f"Add physical descriptions for each."
        )

        # Group violations by emotion type
        emotion_types = {}
        for violation in analysis.violations:
            emotion = violation.emotion_word
            if emotion not in emotion_types:
                emotion_types[emotion] = []
            emotion_types[emotion].append(violation)

        # Provide specific examples
        for emotion, viols in list(emotion_types.items())[:5]:
            recommendations.append(
                f"Emotion '{emotion}' appears {len(viols)} times ungrounded. "
                f"Add: heart rate, breathing, body sensations, temperature."
            )

        # General recommendations
        recommendations.append(
            "Physical grounding examples:\n"
            "  - Heart rate: '102 BPM', 'heart hammering', 'pulse racing'\n"
            "  - Breathing: 'breath caught', 'shallow breathing', 'gasping'\n"
            "  - Body: 'hands trembling', 'stomach dropped', 'chest tight'\n"
            "  - Temperature: 'skin went cold', '36.2°C', 'sweat on palms'"
        )

        return recommendations

    def _split_sentences(self, text: str) -> List[str]:
        """
        Split text into sentences.
        Handles some edge cases like abbreviations and dialogue.
        """
        # Simple sentence splitter (could be improved)
        text = text.replace('\n\n', ' PARAGRAPH_BREAK ')
        text = text.replace('\n', ' ')

        # Split on sentence boundaries
        sentences = re.split(r'(?<=[.!?])\s+(?=[A-Z"])', text)

        # Filter out very short fragments
        sentences = [s.strip() for s in sentences if len(s.strip()) > 10]

        return sentences

    def get_score(self, text: str) -> float:
        """
        Get physical grounding score (0-100).

        Returns:
            Score based on grounding ratio
        """
        analysis = self.check_physical_grounding(text)
        return analysis.score


if __name__ == "__main__":
    # Quick test
    checker = PhysicalGroundingChecker()

    # Bad example - ungrounded
    bad_text = """
    Sarah felt afraid. She was scared of the dark room.
    Marcus felt happy to see her.
    """

    # Good example - grounded
    good_text = """
    Sarah's heart hammered. 112 BPM. Hands trembling. The dark room—
    couldn't breathe. Chest tight.
    Marcus's face split into a grin. Chest warm. Couldn't stop smiling.
    """

    print("=== Bad Example (Ungrounded) ===")
    result = checker.check_physical_grounding(bad_text)
    print(f"Score: {result.score:.1f}/100")
    print(f"Grounded: {result.grounded_emotions}/{result.total_emotions}")
    print(f"Violations: {len(result.violations)}")

    print("\n=== Good Example (Grounded) ===")
    result = checker.check_physical_grounding(good_text)
    print(f"Score: {result.score:.1f}/100")
    print(f"Grounded: {result.grounded_emotions}/{result.total_emotions}")
    print(f"Violations: {len(result.violations)}")
