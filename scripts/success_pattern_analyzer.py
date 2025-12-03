#!/usr/bin/env python3
"""
Success Pattern Analyzer - Phase 5 Priority 1.2
Analyzes reader feedback to identify success patterns and failure points
"""

import json
import sqlite3
import numpy as np
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Set
from dataclasses import dataclass
from collections import defaultdict, Counter
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
import warnings
warnings.filterwarnings('ignore')


@dataclass
class SuccessPattern:
    """Identified pattern that correlates with success"""
    pattern_id: str
    pattern_type: str  # 'structural', 'thematic', 'stylistic', 'pacing'
    description: str
    success_correlation: float  # -1 to 1
    frequency: int  # How often seen
    examples: List[Dict]
    recommendations: List[str]

    def to_dict(self) -> Dict:
        return {
            'pattern_id': self.pattern_id,
            'pattern_type': self.pattern_type,
            'description': self.description,
            'success_correlation': self.success_correlation,
            'frequency': self.frequency,
            'examples': self.examples,
            'recommendations': self.recommendations
        }


@dataclass
class ChapterAnalysis:
    """Analysis of a single chapter's performance"""
    chapter_num: int
    avg_rating: float
    abandonment_rate: float
    highlight_density: float  # Highlights per 1000 words
    reading_speed: float  # Words per minute
    engagement_score: float  # Composite metric
    identified_issues: List[str]
    improvement_suggestions: List[str]


class SuccessPatternAnalyzer:
    """Analyzes feedback to identify patterns of success and failure"""

    def __init__(self, feedback_db_path: str = "feedback.db"):
        """Initialize pattern analyzer"""
        self.db_path = Path(feedback_db_path)
        self.patterns: List[SuccessPattern] = []
        self.chapter_analyses: Dict[str, Dict[int, ChapterAnalysis]] = {}

        # Success thresholds
        self.success_thresholds = {
            'rating': 8.0,
            'completion': 70.0,
            'engagement': 7.5,
            'abandonment': 10.0  # Max acceptable %
        }

        # Pattern templates
        self.known_patterns = self._load_known_patterns()

    def _load_known_patterns(self) -> Dict:
        """Load known success/failure patterns"""
        return {
            'structural': {
                'strong_opening': {
                    'indicator': 'high_ch1_rating',
                    'description': 'Strong first chapter hooks readers',
                    'weight': 0.3
                },
                'midpoint_twist': {
                    'indicator': 'rating_spike_middle',
                    'description': 'Major revelation/twist at midpoint maintains interest',
                    'weight': 0.2
                },
                'satisfying_ending': {
                    'indicator': 'high_final_rating',
                    'description': 'Ending meets/exceeds expectations',
                    'weight': 0.3
                },
                'consistent_pacing': {
                    'indicator': 'stable_reading_speed',
                    'description': 'Even pacing throughout',
                    'weight': 0.2
                }
            },
            'engagement': {
                'highlight_worthy': {
                    'indicator': 'high_highlight_rate',
                    'description': 'Memorable prose that readers highlight',
                    'weight': 0.25
                },
                'page_turner': {
                    'indicator': 'long_reading_sessions',
                    'description': 'Readers continue for multiple chapters',
                    'weight': 0.35
                },
                'discussion_driver': {
                    'indicator': 'high_comment_rate',
                    'description': 'Content sparks reader discussion',
                    'weight': 0.2
                },
                'completion_driver': {
                    'indicator': 'high_completion_rate',
                    'description': 'Readers finish the book',
                    'weight': 0.2
                }
            },
            'quality': {
                'consistent_quality': {
                    'indicator': 'low_rating_variance',
                    'description': 'Quality remains consistent',
                    'weight': 0.3
                },
                'improving_trajectory': {
                    'indicator': 'rising_chapter_ratings',
                    'description': 'Book gets better as it progresses',
                    'weight': 0.25
                },
                'no_weak_chapters': {
                    'indicator': 'min_rating_above_threshold',
                    'description': 'No chapters below quality threshold',
                    'weight': 0.45
                }
            }
        }

    def analyze_book_success(self, book_id: str) -> Dict:
        """Comprehensive success analysis for a book"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        # Get all feedback for this book
        cursor.execute("""
            SELECT feedback_type, chapter_num, data
            FROM feedback
            WHERE book_id = ?
        """, (book_id,))

        feedback_by_type = defaultdict(list)
        for row in cursor.fetchall():
            feedback_by_type[row[0]].append({
                'chapter': row[1],
                'data': json.loads(row[2])
            })

        conn.close()

        # Analyze patterns
        patterns = []

        # 1. Structural patterns
        structural = self._analyze_structural_patterns(feedback_by_type)
        patterns.extend(structural)

        # 2. Engagement patterns
        engagement = self._analyze_engagement_patterns(feedback_by_type)
        patterns.extend(engagement)

        # 3. Quality patterns
        quality = self._analyze_quality_patterns(feedback_by_type)
        patterns.extend(quality)

        # 4. Failure points
        failures = self._identify_failure_points(feedback_by_type)

        # Calculate overall success score
        success_score = self._calculate_success_score(patterns)

        return {
            'book_id': book_id,
            'success_score': success_score,
            'success_patterns': [p.to_dict() for p in patterns if p.success_correlation > 0.5],
            'failure_patterns': [p.to_dict() for p in patterns if p.success_correlation < -0.3],
            'critical_failures': failures,
            'recommendations': self._generate_recommendations(patterns, failures)
        }

    def _analyze_structural_patterns(self, feedback: Dict) -> List[SuccessPattern]:
        """Analyze structural success patterns"""
        patterns = []

        # Check for strong opening
        chapter_ratings = self._extract_chapter_ratings(feedback)
        if chapter_ratings and 1 in chapter_ratings:
            if chapter_ratings[1] >= self.success_thresholds['rating']:
                patterns.append(SuccessPattern(
                    pattern_id='strong_opening_detected',
                    pattern_type='structural',
                    description='First chapter rated highly - effective hook',
                    success_correlation=0.8,
                    frequency=1,
                    examples=[{'chapter_1_rating': chapter_ratings[1]}],
                    recommendations=['Maintain this opening quality in future books']
                ))

        # Check for midpoint engagement
        if chapter_ratings:
            mid_chapter = max(chapter_ratings.keys()) // 2
            if mid_chapter in chapter_ratings:
                mid_rating = chapter_ratings[mid_chapter]
                avg_before = np.mean([r for c, r in chapter_ratings.items() if c < mid_chapter])
                if mid_rating > avg_before * 1.1:  # 10% spike
                    patterns.append(SuccessPattern(
                        pattern_id='midpoint_twist_effective',
                        pattern_type='structural',
                        description='Midpoint creates engagement spike',
                        success_correlation=0.7,
                        frequency=1,
                        examples=[{'midpoint_rating': mid_rating, 'avg_before': avg_before}],
                        recommendations=['Strong midpoint twists drive engagement']
                    ))

        return patterns

    def _analyze_engagement_patterns(self, feedback: Dict) -> List[SuccessPattern]:
        """Analyze reader engagement patterns"""
        patterns = []

        # Highlight density analysis
        highlights = feedback.get('highlight', [])
        if highlights:
            highlight_chapters = Counter([h['chapter'] for h in highlights if h['chapter']])
            if highlight_chapters:
                avg_highlights = np.mean(list(highlight_chapters.values()))
                if avg_highlights > 5:  # More than 5 highlights per chapter average
                    patterns.append(SuccessPattern(
                        pattern_id='highly_quotable',
                        pattern_type='engagement',
                        description='High highlight rate indicates memorable prose',
                        success_correlation=0.75,
                        frequency=len(highlights),
                        examples=highlight_chapters.most_common(3),
                        recommendations=['Prose quality resonates with readers']
                    ))

        # Completion analysis
        completions = feedback.get('completion', [])
        if completions:
            completion_rates = [c['data']['completion_percentage'] for c in completions]
            avg_completion = np.mean(completion_rates)
            if avg_completion >= self.success_thresholds['completion']:
                patterns.append(SuccessPattern(
                    pattern_id='high_completion',
                    pattern_type='engagement',
                    description='Readers finish the book at high rates',
                    success_correlation=0.9,
                    frequency=len(completions),
                    examples=[{'avg_completion': avg_completion}],
                    recommendations=['Story maintains reader interest throughout']
                ))

        return patterns

    def _analyze_quality_patterns(self, feedback: Dict) -> List[SuccessPattern]:
        """Analyze quality consistency patterns"""
        patterns = []

        chapter_ratings = self._extract_chapter_ratings(feedback)
        if chapter_ratings:
            ratings = list(chapter_ratings.values())
            variance = np.var(ratings)
            min_rating = min(ratings)

            # Check consistency
            if variance < 0.5:  # Low variance
                patterns.append(SuccessPattern(
                    pattern_id='consistent_quality',
                    pattern_type='quality',
                    description='Quality remains consistent across chapters',
                    success_correlation=0.6,
                    frequency=len(ratings),
                    examples=[{'variance': variance, 'ratings': ratings[:5]}],
                    recommendations=['Consistency builds reader trust']
                ))

            # Check for no weak chapters
            if min_rating >= self.success_thresholds['rating'] - 1:
                patterns.append(SuccessPattern(
                    pattern_id='no_weak_links',
                    pattern_type='quality',
                    description='All chapters meet quality threshold',
                    success_correlation=0.8,
                    frequency=len(ratings),
                    examples=[{'min_rating': min_rating}],
                    recommendations=['No weak chapters ensures reader retention']
                ))

        return patterns

    def _identify_failure_points(self, feedback: Dict) -> List[Dict]:
        """Identify critical failure points"""
        failures = []

        # Abandonment analysis
        abandonments = feedback.get('abandonment', [])
        if abandonments:
            abandonment_chapters = Counter([a['chapter'] for a in abandonments if a['chapter']])
            for chapter, count in abandonment_chapters.most_common(3):
                if count >= 2:  # Multiple readers abandoned at same point
                    failures.append({
                        'type': 'high_abandonment',
                        'chapter': chapter,
                        'severity': 'critical' if count > 3 else 'moderate',
                        'count': count,
                        'recommendation': f'Chapter {chapter} needs major revision - common abandonment point'
                    })

        # Low rating chapters
        chapter_ratings = self._extract_chapter_ratings(feedback)
        for chapter, rating in chapter_ratings.items():
            if rating < 6.0:  # Below 6 is problematic
                failures.append({
                    'type': 'low_rating',
                    'chapter': chapter,
                    'severity': 'critical' if rating < 5 else 'moderate',
                    'rating': rating,
                    'recommendation': f'Chapter {chapter} underperforms (rating: {rating:.1f})'
                })

        return failures

    def _extract_chapter_ratings(self, feedback: Dict) -> Dict[int, float]:
        """Extract chapter ratings from feedback"""
        chapter_ratings = {}
        ratings_data = feedback.get('chapter_rating', [])

        for rating in ratings_data:
            if rating['chapter']:
                chapter = rating['chapter']
                if chapter not in chapter_ratings:
                    chapter_ratings[chapter] = []
                chapter_ratings[chapter].append(rating['data']['rating'])

        # Average ratings per chapter
        return {ch: np.mean(ratings) for ch, ratings in chapter_ratings.items()}

    def _calculate_success_score(self, patterns: List[SuccessPattern]) -> float:
        """Calculate overall success score from patterns"""
        if not patterns:
            return 5.0  # Neutral

        positive_weight = sum(p.success_correlation for p in patterns if p.success_correlation > 0)
        negative_weight = abs(sum(p.success_correlation for p in patterns if p.success_correlation < 0))

        # Normalize to 0-10 scale
        score = 5 + (positive_weight - negative_weight) * 2
        return max(0, min(10, score))

    def _generate_recommendations(self, patterns: List[SuccessPattern],
                                 failures: List[Dict]) -> List[str]:
        """Generate actionable recommendations"""
        recommendations = []

        # Add pattern-based recommendations
        for pattern in patterns:
            if pattern.success_correlation > 0.6:
                recommendations.extend(pattern.recommendations)

        # Add failure-based recommendations
        for failure in failures:
            recommendations.append(failure['recommendation'])

        # Add general recommendations
        if not any(p.pattern_id == 'strong_opening_detected' for p in patterns):
            recommendations.append('Strengthen first chapter - critical for reader retention')

        if not any(p.pattern_type == 'engagement' for p in patterns):
            recommendations.append('Increase engagement elements (cliffhangers, revelations)')

        return recommendations[:10]  # Top 10 recommendations

    def compare_books(self, book_ids: List[str]) -> Dict:
        """Compare success patterns across multiple books"""
        comparisons = {}

        for book_id in book_ids:
            analysis = self.analyze_book_success(book_id)
            comparisons[book_id] = {
                'success_score': analysis['success_score'],
                'top_patterns': analysis['success_patterns'][:3],
                'critical_issues': len(analysis['critical_failures'])
            }

        # Identify common success factors
        all_patterns = []
        for book_id, data in comparisons.items():
            all_patterns.extend([p['pattern_id'] for p in data['top_patterns']])

        common_patterns = Counter(all_patterns).most_common(5)

        return {
            'individual_scores': comparisons,
            'common_success_factors': common_patterns,
            'best_performer': max(comparisons.items(), key=lambda x: x[1]['success_score'])[0],
            'needs_improvement': [bid for bid, data in comparisons.items()
                                 if data['critical_issues'] > 0]
        }


def demonstrate_pattern_analysis():
    """Demonstrate success pattern analysis"""
    print("="*60)
    print("SUCCESS PATTERN ANALYZER")
    print("="*60)

    # First, create some test feedback data
    from feedback_collector import FeedbackCollector

    collector = FeedbackCollector("test_analysis.db")

    # Simulate feedback for successful book
    book_id = "successful-book"
    print(f"\n📚 Generating feedback for: {book_id}")

    # Simulate strong opening (high Chapter 1 ratings)
    for i in range(10):
        collector.collect_rating(book_id, f"reader_{i}", np.random.uniform(8.5, 9.5), 1)

    # Simulate good overall ratings
    for i in range(10):
        collector.collect_rating(book_id, f"reader_{i}", np.random.uniform(8.0, 9.0))

    # Simulate high completion
    for i in range(10):
        collector.collect_reading_session(
            book_id, f"reader_{i}",
            list(range(1, 20)),
            60, 95.0
        )

    # Simulate highlights
    for i in range(5):
        collector.collect_highlight(
            book_id, f"reader_{i}", 1,
            "Amazing opening line", 0, 50
        )

    collector._flush_cache()

    # Analyze patterns
    analyzer = SuccessPatternAnalyzer("test_analysis.db")

    print("\n🔍 Analyzing success patterns...")
    analysis = analyzer.analyze_book_success(book_id)

    print(f"\n📊 SUCCESS ANALYSIS")
    print("-"*40)
    print(f"Success Score: {'█' * int(analysis['success_score'])}{'░' * (10 - int(analysis['success_score']))} {analysis['success_score']:.1f}/10")

    print("\n✨ Success Patterns Identified:")
    for pattern in analysis['success_patterns'][:5]:
        print(f"  • {pattern['description']}")
        print(f"    Correlation: {pattern['success_correlation']:.2f}")

    if analysis['critical_failures']:
        print("\n⚠️ Critical Issues:")
        for failure in analysis['critical_failures']:
            print(f"  • Chapter {failure['chapter']}: {failure['type']}")

    print("\n💡 Recommendations:")
    for i, rec in enumerate(analysis['recommendations'][:5], 1):
        print(f"  {i}. {rec}")

    # Clean up
    Path("test_analysis.db").unlink(missing_ok=True)

    print("\n✅ Pattern analysis complete!")

    return analysis


if __name__ == "__main__":
    demonstrate_pattern_analysis()