#!/usr/bin/env python3
"""
Quality Predictor - Predicts likely quality issues from outline/context

Analyzes chapter outline and continuity context to flag potential problems
before generation, allowing for outline improvements.
"""

import re
from typing import Dict, List
from dataclasses import dataclass


@dataclass
class QualityFlag:
    """A potential quality issue"""
    issue: str
    severity: str  # 'HIGH', 'MEDIUM', 'LOW'
    fix: str
    impact: str  # Which quality dimension this affects


class QualityPredictor:
    """Predicts likely quality score from outline/context"""

    def predict_from_outline(self, outline: str, context: Dict) -> Dict:
        """
        Predict likely quality score and flag potential issues

        Args:
            outline: Chapter outline text
            context: Dictionary with keys:
                - character_count: Number of characters
                - event_count: Number of events in outline
                - word_target: Target word count
                - obsession_anchors: List of character obsessions
                - detail_specs: Specific details mentioned in outline

        Returns:
            Dictionary with prediction results
        """
        flags = []

        # Extract info from outline
        events = self._extract_events(outline)
        detail_specs = self._count_detail_specifications(outline)
        emotional_beats = self._count_emotional_beats(outline)
        obsession_mentions = self._count_obsession_mentions(outline, context.get('obsession_anchors', []))

        # Flag 1: Too many events (will rush, lose depth)
        word_target = context.get('word_target', 3000)
        words_per_event = word_target / len(events) if events else word_target

        if len(events) > 8:
            flags.append(QualityFlag(
                issue='TOO_MANY_EVENTS',
                severity='HIGH',
                fix=f'Reduce from {len(events)} to 5-7 events OR increase word target to {len(events) * 400}+',
                impact='Emotional depth, detail density - events will be rushed'
            ))
        elif words_per_event < 300:
            flags.append(QualityFlag(
                issue='INSUFFICIENT_WORDS_PER_EVENT',
                severity='MEDIUM',
                fix=f'Each event needs ~400 words minimum. Current: {int(words_per_event)} words/event',
                impact='Detail density, time dilation - key moments will be rushed'
            ))

        # Flag 2: Missing detail specifications
        if detail_specs < len(events) * 0.5:
            flags.append(QualityFlag(
                issue='MISSING_DETAIL_SPECS',
                severity='MEDIUM',
                fix='Add specific details to outline: exact measurements, colors, textures, sounds',
                impact='Obsession depth - generic descriptions likely'
            ))

        # Flag 3: Weak emotional beats
        if emotional_beats == 0:
            flags.append(QualityFlag(
                issue='NO_EMOTIONAL_BEATS',
                severity='HIGH',
                fix='Add emotional moments: vulnerability, fear, desire, joy, grief',
                impact='Emotional impact - chapter will feel flat'
            ))
        elif emotional_beats < 3:
            flags.append(QualityFlag(
                issue='FEW_EMOTIONAL_BEATS',
                severity='MEDIUM',
                fix=f'Increase from {emotional_beats} to 4+ emotional beats',
                impact='Emotional impact - chapter may feel shallow'
            ))

        # Flag 4: No obsession anchors
        if obsession_mentions == 0:
            flags.append(QualityFlag(
                issue='NO_OBSESSION_ANCHORS',
                severity='HIGH',
                fix='Define character obsessions: what they count, notice, or track repeatedly',
                impact='Voice distinctiveness, obsession depth - character will lack specificity'
            ))

        # Flag 5: Generic verbs (walked, went, said, looked)
        generic_verbs = len(re.findall(r'\b(walked|went|said|looked|saw|heard|felt)\b', outline, re.IGNORECASE))
        if generic_verbs > len(events):
            flags.append(QualityFlag(
                issue='GENERIC_VERBS_IN_OUTLINE',
                severity='LOW',
                fix='Replace generic verbs with specific actions in outline',
                impact='Prose quality - generic outline → generic prose'
            ))

        # Flag 6: Telling language in outline
        telling_markers = ['realizes', 'learns', 'understands', 'knows', 'feels']
        telling_count = sum(outline.lower().count(marker) for marker in telling_markers)

        if telling_count > 3:
            flags.append(QualityFlag(
                issue='TELLING_IN_OUTLINE',
                severity='MEDIUM',
                fix='Replace "realizes/learns/understands" with specific actions/choices',
                impact='Thematic subtlety - will lead to telling instead of showing'
            ))

        # Flag 7: No physical/sensory anchors
        sensory_words = ['sound', 'smell', 'taste', 'texture', 'temperature', 'color']
        sensory_count = sum(outline.lower().count(word) for word in sensory_words)

        if sensory_count == 0:
            flags.append(QualityFlag(
                issue='NO_SENSORY_ANCHORS',
                severity='MEDIUM',
                fix='Add sensory details to outline: sounds, smells, textures, temperatures',
                impact='Detail density, immersion - chapter will lack sensory grounding'
            ))

        # Flag 8: Plot-heavy vs character-heavy balance
        plot_words = ['then', 'next', 'after', 'meanwhile', 'later']
        character_words = ['fear', 'want', 'desire', 'struggle', 'choice']

        plot_count = sum(outline.lower().count(word) for word in plot_words)
        character_count = sum(outline.lower().count(word) for word in character_words)

        if plot_count > character_count * 2:
            flags.append(QualityFlag(
                issue='TOO_PLOT_FOCUSED',
                severity='MEDIUM',
                fix='Add character interiority: fears, desires, internal conflicts',
                impact='Emotional impact, character depth - events without emotion'
            ))

        # Predict overall quality based on flags
        predicted_quality = self._calculate_prediction(flags)

        return {
            'predicted_quality': predicted_quality,
            'confidence': self._calculate_confidence(flags),
            'flags': flags,
            'event_count': len(events),
            'detail_spec_count': detail_specs,
            'emotional_beat_count': emotional_beats,
            'obsession_mention_count': obsession_mentions,
            'words_per_event': int(words_per_event) if events else 0
        }

    def _extract_events(self, outline: str) -> List[str]:
        """Extract events from outline (numbered lists, bullet points, etc.)"""
        events = []

        # Method 1: Numbered lists (1., 2., 3.)
        numbered = re.findall(r'^\s*\d+[\.)]\s+(.+)$', outline, re.MULTILINE)
        events.extend(numbered)

        # Method 2: Bullet points (-, *, •)
        bullets = re.findall(r'^\s*[-*•]\s+(.+)$', outline, re.MULTILINE)
        events.extend(bullets)

        # Method 3: Sentences (if no lists found)
        if not events:
            sentences = re.split(r'[.!?]\s+', outline)
            events = [s.strip() for s in sentences if len(s.split()) > 3]

        return events

    def _count_detail_specifications(self, outline: str) -> int:
        """Count specific details mentioned in outline"""
        count = 0

        # Numbers (exact measurements)
        count += len(re.findall(r'\b\d+\.?\d*\s*(cm|meters?|feet|inches?|°[CF]|degrees|seconds?|minutes?)\b', outline, re.IGNORECASE))

        # Specific colors
        count += len(re.findall(r'\b(crimson|azure|silver|golden|jade|obsidian|ivory|scarlet|emerald)\b', outline, re.IGNORECASE))

        # Specific textures
        count += len(re.findall(r'\b(rough|smooth|silken|coarse|velvety|gritty|calloused)\b', outline, re.IGNORECASE))

        # Specific sounds
        count += len(re.findall(r'\b(whisper|roar|hiss|clang|thud|chime|echo)\b', outline, re.IGNORECASE))

        return count

    def _count_emotional_beats(self, outline: str) -> int:
        """Count emotional moments in outline"""
        emotional_keywords = [
            'afraid', 'fear', 'terror', 'panic',
            'love', 'desire', 'want', 'crave',
            'grief', 'sorrow', 'mourn',
            'joy', 'delight', 'happy',
            'anger', 'rage', 'fury',
            'vulnerable', 'exposed', 'raw',
            'hope', 'despair', 'longing'
        ]

        count = sum(
            len(re.findall(rf'\b{keyword}\b', outline, re.IGNORECASE))
            for keyword in emotional_keywords
        )

        return count

    def _count_obsession_mentions(self, outline: str, obsession_anchors: List[str]) -> int:
        """Count mentions of character obsessions"""
        if not obsession_anchors:
            return 0

        count = sum(
            len(re.findall(rf'\b{anchor}\b', outline, re.IGNORECASE))
            for anchor in obsession_anchors
        )

        return count

    def _calculate_prediction(self, flags: List[QualityFlag]) -> float:
        """Calculate predicted quality score based on flags"""

        # Start at 8.5 (perfect)
        score = 8.5

        # Deduct based on severity
        severity_penalties = {
            'HIGH': 1.0,
            'MEDIUM': 0.5,
            'LOW': 0.2
        }

        for flag in flags:
            score -= severity_penalties.get(flag.severity, 0)

        # Floor at 5.0
        return max(5.0, round(score, 1))

    def _calculate_confidence(self, flags: List[QualityFlag]) -> str:
        """Calculate confidence in prediction"""
        if len(flags) == 0:
            return 'HIGH'
        elif len(flags) <= 2:
            return 'MEDIUM'
        else:
            return 'LOW'

    def format_report(self, prediction: Dict) -> str:
        """Format prediction as readable report"""
        lines = []

        lines.append("=" * 70)
        lines.append("QUALITY PREDICTION (PRE-GENERATION)")
        lines.append("=" * 70)
        lines.append("")

        # Prediction
        lines.append(f"Predicted quality: {prediction['predicted_quality']}/10")
        lines.append(f"Confidence: {prediction['confidence']}")
        lines.append("")

        # Stats
        lines.append("Outline analysis:")
        lines.append(f"  - Events: {prediction['event_count']}")
        lines.append(f"  - Detail specifications: {prediction['detail_spec_count']}")
        lines.append(f"  - Emotional beats: {prediction['emotional_beat_count']}")
        lines.append(f"  - Obsession mentions: {prediction['obsession_mention_count']}")
        if prediction['words_per_event'] > 0:
            lines.append(f"  - Words per event: {prediction['words_per_event']}")
        lines.append("")

        # Flags
        if prediction['flags']:
            lines.append(f"Issues found ({len(prediction['flags'])}):")
            lines.append("")

            for i, flag in enumerate(prediction['flags'], 1):
                lines.append(f"{i}. [{flag.severity}] {flag.issue}")
                lines.append(f"   Impact: {flag.impact}")
                lines.append(f"   Fix: {flag.fix}")
                lines.append("")
        else:
            lines.append("✓ No issues detected - outline looks good!")
            lines.append("")

        # Recommendation
        if prediction['predicted_quality'] >= 8.0:
            lines.append("RECOMMENDATION: Outline is ready for generation ✓")
        elif prediction['predicted_quality'] >= 7.0:
            lines.append("RECOMMENDATION: Address MEDIUM/HIGH issues before generation")
        else:
            lines.append("RECOMMENDATION: Revise outline - address all HIGH issues")

        return '\n'.join(lines)


def main():
    """Test the quality predictor"""

    # Test 1: Good outline
    good_outline = """
    Chapter 3: The Morning After

    1. Catherine wakes to sunlight (first time without helmet - 36.8°C warmth)
    2. Watches Elara work forge (counts 17 hammer strikes per minute)
    3. Breakfast scene: relearning taste (honey, cinnamon, overwhelming sensory)
    4. Foot examination: silver scars, deformed bones, fear of being ordinary
    5. REVELATION: threads embedded in bones (2 months to live, surgical extraction)
    6. Catherine's vulnerability: "I'm afraid of being responsible for failures"
    7. Love confession: "I love you" (Catherine to Elara, 38 days counted)
    8. Elara can't say it back: terror of loss (mother's death, afraid to fail again)

    Emotional arc: Hope → domestic intimacy → devastating truth → raw vulnerability
    Obsessions: Elara counts heartbeats (74 BPM), Catherine tracks temperature
    """

    # Test 2: Weak outline
    weak_outline = """
    Chapter 3: Stuff Happens

    Catherine wakes up. They have breakfast. She learns about the surgery.
    They talk about their feelings. She says I love you. Elara doesn't say it back.
    They go to sleep.
    """

    predictor = QualityPredictor()

    print("TEST 1: Strong outline (should predict 8.0+)")
    print("-" * 70)
    result1 = predictor.predict_from_outline(good_outline, {
        'word_target': 3500,
        'obsession_anchors': ['counted', 'heartbeats', 'temperature', 'scars']
    })
    print(predictor.format_report(result1))
    print("\n" * 2)

    print("TEST 2: Weak outline (should predict <7.0)")
    print("-" * 70)
    result2 = predictor.predict_from_outline(weak_outline, {
        'word_target': 3500,
        'obsession_anchors': []
    })
    print(predictor.format_report(result2))


if __name__ == "__main__":
    main()
