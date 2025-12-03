#!/usr/bin/env python3
"""
Adaptive Quality Engine - Phase 5 Priority 2.1
Uses learned success patterns to improve generation quality
"""

import json
import time
import sqlite3
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, asdict
import numpy as np
from collections import defaultdict


@dataclass
class QualityRule:
    """Adaptive rule for quality improvement"""
    rule_id: str
    rule_type: str  # 'structural', 'stylistic', 'pacing', 'character', 'plot'
    description: str
    confidence: float  # 0-1, based on evidence
    impact: float  # Expected quality improvement
    conditions: Dict  # When to apply
    actions: List[str]  # What to do
    evidence_count: int  # Number of supporting data points
    success_rate: float  # Historical success rate

    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class AdaptivePrompt:
    """Dynamically generated prompt with learned improvements"""
    base_prompt: str
    success_patterns: List[str]
    avoid_patterns: List[str]
    quality_targets: Dict[str, float]
    special_instructions: List[str]
    expected_quality: float

    def build(self) -> str:
        """Build the enhanced prompt"""
        prompt_parts = [self.base_prompt]

        if self.success_patterns:
            prompt_parts.append("\n## SUCCESS PATTERNS TO INCORPORATE:")
            for pattern in self.success_patterns:
                prompt_parts.append(f"- {pattern}")

        if self.avoid_patterns:
            prompt_parts.append("\n## PATTERNS TO AVOID:")
            for pattern in self.avoid_patterns:
                prompt_parts.append(f"- {pattern}")

        if self.special_instructions:
            prompt_parts.append("\n## SPECIAL INSTRUCTIONS:")
            for instruction in self.special_instructions:
                prompt_parts.append(f"- {instruction}")

        if self.quality_targets:
            prompt_parts.append("\n## QUALITY TARGETS:")
            for metric, target in self.quality_targets.items():
                prompt_parts.append(f"- {metric}: {target:.1f}/10")

        return "\n".join(prompt_parts)


class AdaptiveQualityEngine:
    """Engine that learns and adapts to improve quality"""

    def __init__(self, learning_db: str = "adaptive_learning.db"):
        """Initialize adaptive engine"""
        self.db_path = Path(learning_db)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_database()

        # Learning parameters
        self.learning_rate = 0.1
        self.confidence_threshold = 0.6
        self.min_evidence = 5

        # Quality rules learned from feedback
        self.active_rules: List[QualityRule] = []
        self._load_rules()

        # Pattern weights (updated through learning)
        self.pattern_weights = self._init_pattern_weights()

    def _init_database(self):
        """Initialize learning database"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        # Quality rules table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS quality_rules (
                rule_id TEXT PRIMARY KEY,
                rule_type TEXT NOT NULL,
                description TEXT NOT NULL,
                confidence REAL NOT NULL,
                impact REAL NOT NULL,
                conditions TEXT NOT NULL,
                actions TEXT NOT NULL,
                evidence_count INTEGER DEFAULT 0,
                success_rate REAL DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Generation history table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS generation_history (
                generation_id TEXT PRIMARY KEY,
                book_id TEXT NOT NULL,
                chapter_num INTEGER,
                prompt_enhancements TEXT,
                predicted_quality REAL,
                actual_quality REAL,
                rules_applied TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Pattern effectiveness table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS pattern_effectiveness (
                pattern_id TEXT PRIMARY KEY,
                pattern_type TEXT NOT NULL,
                times_used INTEGER DEFAULT 0,
                total_quality_gain REAL DEFAULT 0,
                avg_quality_gain REAL DEFAULT 0,
                confidence REAL DEFAULT 0.5
            )
        """)

        conn.commit()
        conn.close()

    def _init_pattern_weights(self) -> Dict[str, float]:
        """Initialize pattern importance weights"""
        return {
            'strong_opening': 1.5,  # Extra weight for first chapters
            'cliffhanger_ending': 1.3,
            'character_depth': 1.2,
            'world_building': 1.1,
            'emotional_resonance': 1.2,
            'plot_twist': 1.0,
            'pacing_variation': 0.9,
            'dialogue_quality': 1.0,
            'descriptive_prose': 0.8,
            'thematic_depth': 0.9
        }

    def _load_rules(self):
        """Load active quality rules from database"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        cursor.execute("""
            SELECT rule_id, rule_type, description, confidence, impact,
                   conditions, actions, evidence_count, success_rate
            FROM quality_rules
            WHERE confidence >= ?
            ORDER BY impact DESC
        """, (self.confidence_threshold,))

        self.active_rules = []
        for row in cursor.fetchall():
            self.active_rules.append(QualityRule(
                rule_id=row[0],
                rule_type=row[1],
                description=row[2],
                confidence=row[3],
                impact=row[4],
                conditions=json.loads(row[5]),
                actions=json.loads(row[6]),
                evidence_count=row[7],
                success_rate=row[8]
            ))

        conn.close()

    def learn_from_feedback(self, book_id: str, feedback_data: Dict):
        """Learn from reader feedback to improve future generations"""
        # Extract key metrics
        avg_rating = feedback_data.get('avg_rating', 5.0)
        completion_rate = feedback_data.get('completion_rate', 50.0)
        chapter_ratings = feedback_data.get('chapter_ratings', {})
        abandonment_points = feedback_data.get('abandonment_points', [])

        # Learn new rules
        new_rules = []

        # Rule: Strong first chapter importance
        if 1 in chapter_ratings and chapter_ratings[1] > 8.0:
            if avg_rating > 8.0:  # Strong opening correlates with overall success
                new_rules.append(QualityRule(
                    rule_id=f"strong_opening_{book_id}",
                    rule_type='structural',
                    description='Invest extra effort in first chapter',
                    confidence=0.8,
                    impact=1.5,
                    conditions={'chapter_num': 1},
                    actions=[
                        'Add compelling hook in first paragraph',
                        'Introduce protagonist with immediate conflict',
                        'Create mystery or question to drive reading'
                    ],
                    evidence_count=1,
                    success_rate=avg_rating / 10
                ))

        # Rule: Avoid specific abandonment triggers
        if abandonment_points:
            most_common = abandonment_points[0]  # (chapter, count)
            if most_common[1] >= 3:  # Multiple readers abandoned
                new_rules.append(QualityRule(
                    rule_id=f"avoid_ch{most_common[0]}_issues_{book_id}",
                    rule_type='pacing',
                    description=f'Chapter {most_common[0]} needs better pacing',
                    confidence=0.7,
                    impact=1.2,
                    conditions={'chapter_num': most_common[0]},
                    actions=[
                        'Increase tension and conflict',
                        'Add subplot development',
                        'Ensure chapter ends with forward momentum'
                    ],
                    evidence_count=most_common[1],
                    success_rate=0.3  # Low success = abandonment
                ))

        # Store learned rules
        self._save_rules(new_rules)

        # Update pattern effectiveness
        self._update_pattern_effectiveness(book_id, feedback_data)

    def _save_rules(self, rules: List[QualityRule]):
        """Save new quality rules to database"""
        if not rules:
            return

        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        for rule in rules:
            cursor.execute("""
                INSERT OR REPLACE INTO quality_rules
                (rule_id, rule_type, description, confidence, impact,
                 conditions, actions, evidence_count, success_rate)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                rule.rule_id,
                rule.rule_type,
                rule.description,
                rule.confidence,
                rule.impact,
                json.dumps(rule.conditions),
                json.dumps(rule.actions),
                rule.evidence_count,
                rule.success_rate
            ))

        conn.commit()
        conn.close()

        # Reload rules
        self._load_rules()

    def _update_pattern_effectiveness(self, book_id: str, feedback_data: Dict):
        """Update effectiveness scores for patterns"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        # Calculate quality gain
        quality_gain = feedback_data.get('avg_rating', 5.0) - 7.0  # Baseline expectation

        # Update patterns that were likely used
        patterns_used = ['strong_opening', 'cliffhanger_ending']  # Would be tracked in real system

        for pattern in patterns_used:
            cursor.execute("""
                INSERT INTO pattern_effectiveness
                (pattern_id, pattern_type, times_used, total_quality_gain, avg_quality_gain, confidence)
                VALUES (?, ?, 1, ?, ?, 0.5)
                ON CONFLICT(pattern_id) DO UPDATE SET
                    times_used = times_used + 1,
                    total_quality_gain = total_quality_gain + ?,
                    avg_quality_gain = (total_quality_gain + ?) / (times_used + 1),
                    confidence = MIN(0.95, confidence + 0.05)
            """, (pattern, 'structural', quality_gain, quality_gain, quality_gain, quality_gain))

        conn.commit()
        conn.close()

    def generate_adaptive_prompt(self, chapter_num: int, base_prompt: str,
                                context: Dict) -> AdaptivePrompt:
        """Generate an enhanced prompt using learned patterns"""
        # Get applicable rules
        applicable_rules = [
            rule for rule in self.active_rules
            if self._rule_applies(rule, chapter_num, context)
        ]

        # Build success patterns to emphasize
        success_patterns = []
        avoid_patterns = []
        special_instructions = []

        for rule in applicable_rules:
            if rule.success_rate > 0.7:
                success_patterns.extend(rule.actions[:2])
            elif rule.success_rate < 0.3:
                avoid_patterns.append(rule.description)

            if rule.confidence > 0.8:
                special_instructions.extend(rule.actions)

        # Add chapter-specific enhancements
        if chapter_num == 1:
            success_patterns.append("Create an unforgettable opening line")
            success_patterns.append("Establish protagonist's core conflict immediately")

        elif chapter_num == 10:  # Midpoint
            success_patterns.append("Include major revelation or twist")
            success_patterns.append("Shift story dynamics significantly")

        elif chapter_num == 20:  # Ending
            success_patterns.append("Deliver satisfying resolution to all major threads")
            success_patterns.append("Leave reader with emotional resonance")

        # Set quality targets based on learning
        quality_targets = {
            'engagement': 8.5,
            'prose_quality': 8.0,
            'pacing': 8.0,
            'character_depth': 8.5,
            'plot_coherence': 9.0
        }

        # Adjust targets based on pattern effectiveness
        pattern_boost = self._calculate_pattern_boost(applicable_rules)
        expected_quality = 8.0 + pattern_boost

        return AdaptivePrompt(
            base_prompt=base_prompt,
            success_patterns=success_patterns[:5],  # Top 5
            avoid_patterns=avoid_patterns[:3],  # Top 3 to avoid
            quality_targets=quality_targets,
            special_instructions=special_instructions[:3],
            expected_quality=min(10, expected_quality)
        )

    def _rule_applies(self, rule: QualityRule, chapter_num: int, context: Dict) -> bool:
        """Check if a rule applies to current generation"""
        conditions = rule.conditions

        # Check chapter condition
        if 'chapter_num' in conditions:
            if conditions['chapter_num'] != chapter_num:
                return False

        # Check genre condition
        if 'genre' in conditions:
            if context.get('genre') != conditions['genre']:
                return False

        # Check other conditions
        # (Would be expanded in full implementation)

        return True

    def _calculate_pattern_boost(self, rules: List[QualityRule]) -> float:
        """Calculate expected quality boost from applied rules"""
        if not rules:
            return 0

        # Weight by confidence and impact
        total_boost = 0
        total_weight = 0

        for rule in rules:
            weight = rule.confidence * rule.evidence_count
            boost = rule.impact * rule.success_rate
            total_boost += weight * boost
            total_weight += weight

        if total_weight > 0:
            return total_boost / total_weight
        return 0

    def track_generation(self, generation_id: str, book_id: str, chapter_num: int,
                        prompt_enhancements: List[str], predicted_quality: float):
        """Track a generation for later learning"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO generation_history
            (generation_id, book_id, chapter_num, prompt_enhancements,
             predicted_quality, rules_applied)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            generation_id,
            book_id,
            chapter_num,
            json.dumps(prompt_enhancements),
            predicted_quality,
            json.dumps([r.rule_id for r in self.active_rules])
        ))

        conn.commit()
        conn.close()

    def update_with_actual_quality(self, generation_id: str, actual_quality: float):
        """Update generation record with actual quality for learning"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        cursor.execute("""
            UPDATE generation_history
            SET actual_quality = ?
            WHERE generation_id = ?
        """, (actual_quality, generation_id))

        conn.commit()
        conn.close()

        # Learn from prediction error
        self._learn_from_prediction_error(generation_id, actual_quality)

    def _learn_from_prediction_error(self, generation_id: str, actual_quality: float):
        """Adjust rules based on prediction errors"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        cursor.execute("""
            SELECT predicted_quality, rules_applied
            FROM generation_history
            WHERE generation_id = ?
        """, (generation_id,))

        result = cursor.fetchone()
        if result:
            predicted_quality, rules_applied = result
            rules_applied = json.loads(rules_applied)

            error = actual_quality - predicted_quality

            # Update rule confidence based on error
            for rule_id in rules_applied:
                cursor.execute("""
                    UPDATE quality_rules
                    SET confidence = confidence * ?,
                        success_rate = (success_rate * evidence_count + ?) / (evidence_count + 1),
                        evidence_count = evidence_count + 1
                    WHERE rule_id = ?
                """, (
                    1.1 if error > 0 else 0.9,  # Increase/decrease confidence
                    actual_quality / 10,  # Update success rate
                    rule_id
                ))

        conn.commit()
        conn.close()


def demonstrate_adaptive_engine():
    """Demonstrate adaptive quality engine"""
    print("="*60)
    print("ADAPTIVE QUALITY ENGINE")
    print("="*60)

    # Initialize engine
    engine = AdaptiveQualityEngine("test_adaptive.db")

    # Simulate learning from feedback
    print("\n📚 Learning from reader feedback...")

    feedback_data = {
        'avg_rating': 8.5,
        'completion_rate': 85.0,
        'chapter_ratings': {
            1: 9.0,  # Strong opening
            2: 8.3,
            3: 8.1,
            10: 8.8,  # Good midpoint
            20: 9.2   # Strong ending
        },
        'abandonment_points': [(7, 3)]  # 3 readers abandoned at chapter 7
    }

    engine.learn_from_feedback("test-book-001", feedback_data)

    # Generate adaptive prompt for Chapter 1
    print("\n🎯 Generating adaptive prompt for Chapter 1...")
    base_prompt = "Write Chapter 1 of a fantasy novel."

    adaptive_prompt = engine.generate_adaptive_prompt(
        chapter_num=1,
        base_prompt=base_prompt,
        context={'genre': 'fantasy'}
    )

    print("\n📝 ENHANCED PROMPT:")
    print("-"*40)
    print(adaptive_prompt.build()[:500] + "...")

    print(f"\n📊 Expected Quality: {adaptive_prompt.expected_quality:.1f}/10")

    # Simulate generation tracking
    print("\n📈 Tracking generation...")
    engine.track_generation(
        generation_id="gen_001",
        book_id="test-book-002",
        chapter_num=1,
        prompt_enhancements=adaptive_prompt.success_patterns,
        predicted_quality=adaptive_prompt.expected_quality
    )

    # Simulate quality feedback
    actual_quality = 8.7
    engine.update_with_actual_quality("gen_001", actual_quality)

    print(f"✓ Actual quality: {actual_quality}/10")
    print(f"✓ Prediction error: {actual_quality - adaptive_prompt.expected_quality:+.1f}")

    # Show learned rules
    print("\n🧠 LEARNED QUALITY RULES:")
    print("-"*40)
    for rule in engine.active_rules[:3]:
        print(f"\n• {rule.description}")
        print(f"  Type: {rule.rule_type}")
        print(f"  Confidence: {rule.confidence:.2f}")
        print(f"  Impact: {rule.impact:.2f}")
        print(f"  Actions: {rule.actions[0] if rule.actions else 'None'}")

    # Clean up
    Path("test_adaptive.db").unlink(missing_ok=True)

    print("\n✅ Adaptive engine demonstration complete!")

    return adaptive_prompt


if __name__ == "__main__":
    demonstrate_adaptive_engine()