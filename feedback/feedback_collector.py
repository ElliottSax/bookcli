"""
Feedback Collector System for Book Factory
Collects and analyzes reader feedback for continuous improvement
"""

import json
import sqlite3
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime
from enum import Enum
import statistics
from textblob import TextBlob
import re

logger = logging.getLogger(__name__)


class FeedbackType(Enum):
    """Types of feedback."""
    REVIEW = "review"
    RATING = "rating"
    BETA_READER = "beta_reader"
    SURVEY = "survey"
    COMMENT = "comment"
    RETURN = "return"
    DNF = "did_not_finish"  # Reader didn't finish
    HIGHLIGHT = "highlight"  # Reader highlighted passage
    NOTE = "note"  # Reader note/annotation


class SentimentCategory(Enum):
    """Sentiment categories."""
    VERY_POSITIVE = "very_positive"  # 4.5-5 stars
    POSITIVE = "positive"  # 3.5-4.5 stars
    NEUTRAL = "neutral"  # 2.5-3.5 stars
    NEGATIVE = "negative"  # 1.5-2.5 stars
    VERY_NEGATIVE = "very_negative"  # 0-1.5 stars


@dataclass
class Feedback:
    """Individual feedback item."""
    id: str
    book_id: str
    type: FeedbackType
    source: str  # Amazon, Goodreads, Beta Reader, etc.
    rating: Optional[float] = None
    text: Optional[str] = None
    timestamp: str = None
    reader_id: Optional[str] = None

    # Analysis results
    sentiment_score: Optional[float] = None
    sentiment_category: Optional[SentimentCategory] = None
    topics: List[str] = None
    issues: List[str] = None
    praises: List[str] = None

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()
        if self.topics is None:
            self.topics = []
        if self.issues is None:
            self.issues = []
        if self.praises is None:
            self.praises = []


@dataclass
class BookFeedbackSummary:
    """Aggregated feedback summary for a book."""
    book_id: str
    total_feedback: int
    average_rating: float
    rating_distribution: Dict[int, int]  # star -> count

    # Sentiment analysis
    average_sentiment: float
    sentiment_distribution: Dict[SentimentCategory, int]

    # Common themes
    common_praises: List[Tuple[str, int]]  # (topic, count)
    common_issues: List[Tuple[str, int]]
    suggested_improvements: List[str]

    # Reader behavior
    completion_rate: float
    return_rate: float
    recommendation_rate: float

    # Time analysis
    feedback_trend: List[Dict[str, Any]]  # Rating over time


class FeedbackCollector:
    """
    Collects and analyzes reader feedback for improvement.
    Features:
    - Multi-source feedback collection
    - Sentiment analysis
    - Topic extraction
    - Issue identification
    - Improvement suggestions
    - Trend analysis
    """

    # Keywords for different aspects
    ASPECT_KEYWORDS = {
        'plot': ['plot', 'story', 'storyline', 'narrative', 'events', 'twist', 'ending'],
        'characters': ['character', 'protagonist', 'hero', 'heroine', 'personality', 'development'],
        'writing': ['writing', 'prose', 'style', 'language', 'grammar', 'editing', 'typos'],
        'pacing': ['pacing', 'slow', 'fast', 'boring', 'exciting', 'drag', 'rush'],
        'worldbuilding': ['world', 'setting', 'universe', 'description', 'atmosphere'],
        'dialogue': ['dialogue', 'conversation', 'speaking', 'said', 'talk'],
        'romance': ['romance', 'love', 'relationship', 'chemistry', 'kiss', 'passion'],
        'action': ['action', 'fight', 'battle', 'combat', 'chase', 'exciting'],
        'emotion': ['emotion', 'feel', 'feeling', 'cry', 'laugh', 'moved', 'touching'],
        'originality': ['original', 'unique', 'fresh', 'predictable', 'cliche', 'formulaic']
    }

    # Issue indicators
    ISSUE_PATTERNS = {
        'repetitive': [r'\brepetit\w*\b', r'\bsame\s+\w+\s+over\b', r'\btoo\s+many\s+times\b'],
        'confusion': [r'\bconfus\w*\b', r"\bdidn't understand\b", r'\bunclear\b', r'\blost\b'],
        'unrealistic': [r'\bunrealistic\b', r'\bunbelievable\b', r"\bdidn't buy\b", r'\bimplausible\b'],
        'boring': [r'\bboring\b', r'\bdull\b', r'\btedious\b', r'\bslow\b', r'\bdrag\w*\b'],
        'errors': [r'\btypo\w*\b', r'\berror\w*\b', r'\bmistake\w*\b', r'\bgrammar\b'],
        'shallow': [r'\bshallow\b', r'\bflat\b', r'\bone-dimensional\b', r'\bunderdeveloped\b'],
        'rushed': [r'\brushed\b', r'\btoo fast\b', r'\babrupt\b', r'\bsudden\b'],
        'dnf': [r"\bdidn't finish\b", r'\bDNF\b', r'\bgave up\b', r'\bstopped reading\b'],
        'disappointing': [r'\bdisappoint\w*\b', r'\blet down\b', r'\bexpected more\b']
    }

    # Praise indicators
    PRAISE_PATTERNS = {
        'engaging': [r'\bengaging\b', r'\bgripping\b', r'\bcompelling\b', r'\baddictive\b'],
        'beautiful': [r'\bbeautiful\w*\b', r'\bgorgeou\w*\b', r'\blovely\b', r'\bstunning\b'],
        'emotional': [r'\bemotional\b', r'\bmoving\b', r'\btouching\b', r'\bcried\b', r'\btears\b'],
        'funny': [r'\bfunny\b', r'\bhilarious\b', r'\blaugh\w*\b', r'\bhumor\w*\b', r'\bamusing\b'],
        'original': [r'\boriginal\b', r'\bunique\b', r'\bfresh\b', r'\binnovative\b', r'\bcreative\b'],
        'well_written': [r'\bwell[\s-]written\b', r'\bbeautifully written\b', r'\bexcellent writing\b'],
        'page_turner': [r'\bpage[\s-]turner\b', r"\bcouldn't put\w* down\b", r'\ball night\b'],
        'recommended': [r'\brecommend\w*\b', r'\bmust read\b', r'\bloved it\b', r'\bamazing\b'],
        'perfect': [r'\bperfect\w*\b', r'\bflawless\b', r'\bexcellent\b', r'\bbrilliant\b']
    }

    def __init__(self, workspace: Path):
        """
        Initialize feedback collector.

        Args:
            workspace: Path to feedback storage
        """
        self.workspace = Path(workspace)
        self.workspace.mkdir(parents=True, exist_ok=True)

        # Database
        self.db_path = self.workspace / "feedback.db"
        self._init_database()

        # Cache
        self.feedback_cache: Dict[str, List[Feedback]] = {}

        # Load existing feedback
        self._load_feedback()

    def _init_database(self):
        """Initialize feedback database."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Feedback table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS feedback (
                id TEXT PRIMARY KEY,
                book_id TEXT NOT NULL,
                type TEXT NOT NULL,
                source TEXT NOT NULL,
                rating REAL,
                text TEXT,
                timestamp TEXT,
                reader_id TEXT,
                sentiment_score REAL,
                sentiment_category TEXT,
                data JSON NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Aggregated metrics table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS book_metrics (
                book_id TEXT PRIMARY KEY,
                average_rating REAL,
                total_reviews INTEGER,
                average_sentiment REAL,
                completion_rate REAL,
                return_rate REAL,
                data JSON NOT NULL,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Improvement suggestions table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS improvements (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                book_id TEXT NOT NULL,
                category TEXT NOT NULL,
                suggestion TEXT NOT NULL,
                frequency INTEGER DEFAULT 1,
                priority TEXT DEFAULT 'medium',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        conn.commit()
        conn.close()

    def collect_feedback(
        self,
        book_id: str,
        type: FeedbackType,
        source: str,
        rating: Optional[float] = None,
        text: Optional[str] = None,
        reader_id: Optional[str] = None
    ) -> Feedback:
        """
        Collect a piece of feedback.

        Args:
            book_id: Book identifier
            type: Type of feedback
            source: Where feedback came from
            rating: Optional rating (1-5)
            text: Optional text content
            reader_id: Optional reader identifier

        Returns:
            Analyzed Feedback object
        """
        # Create feedback object
        feedback = Feedback(
            id=self._generate_feedback_id(book_id, source),
            book_id=book_id,
            type=type,
            source=source,
            rating=rating,
            text=text,
            reader_id=reader_id
        )

        # Analyze if text provided
        if text:
            feedback = self._analyze_feedback(feedback)

        # Store in cache and database
        if book_id not in self.feedback_cache:
            self.feedback_cache[book_id] = []
        self.feedback_cache[book_id].append(feedback)

        self._save_feedback(feedback)

        logger.info(f"Collected {type.value} feedback for book {book_id}")
        return feedback

    def bulk_import_reviews(
        self,
        book_id: str,
        reviews: List[Dict[str, Any]],
        source: str = "Amazon"
    ) -> int:
        """
        Bulk import reviews.

        Args:
            book_id: Book identifier
            reviews: List of review dictionaries
            source: Review source

        Returns:
            Number of reviews imported
        """
        count = 0

        for review in reviews:
            try:
                self.collect_feedback(
                    book_id=book_id,
                    type=FeedbackType.REVIEW,
                    source=source,
                    rating=review.get('rating'),
                    text=review.get('text', review.get('content')),
                    reader_id=review.get('reviewer_id', review.get('author'))
                )
                count += 1
            except Exception as e:
                logger.error(f"Failed to import review: {e}")

        logger.info(f"Imported {count} reviews for book {book_id}")
        return count

    def analyze_book_feedback(self, book_id: str) -> BookFeedbackSummary:
        """
        Analyze all feedback for a book.

        Args:
            book_id: Book identifier

        Returns:
            Comprehensive feedback summary
        """
        feedback_list = self.feedback_cache.get(book_id, [])

        if not feedback_list:
            logger.warning(f"No feedback found for book {book_id}")
            return None

        # Calculate basic metrics
        ratings = [f.rating for f in feedback_list if f.rating]
        avg_rating = statistics.mean(ratings) if ratings else 0

        # Rating distribution
        rating_dist = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
        for rating in ratings:
            rating_dist[int(rating)] = rating_dist.get(int(rating), 0) + 1

        # Sentiment analysis
        sentiments = [f.sentiment_score for f in feedback_list if f.sentiment_score is not None]
        avg_sentiment = statistics.mean(sentiments) if sentiments else 0

        sentiment_dist = {cat: 0 for cat in SentimentCategory}
        for f in feedback_list:
            if f.sentiment_category:
                sentiment_dist[f.sentiment_category] += 1

        # Extract common themes
        all_praises = []
        all_issues = []

        for f in feedback_list:
            all_praises.extend(f.praises or [])
            all_issues.extend(f.issues or [])

        common_praises = self._count_themes(all_praises)
        common_issues = self._count_themes(all_issues)

        # Generate improvement suggestions
        suggestions = self._generate_improvement_suggestions(
            common_issues,
            feedback_list
        )

        # Calculate behavior metrics
        completion_rate = self._calculate_completion_rate(feedback_list)
        return_rate = self._calculate_return_rate(feedback_list)
        recommendation_rate = self._calculate_recommendation_rate(feedback_list)

        # Trend analysis
        feedback_trend = self._analyze_feedback_trend(feedback_list)

        return BookFeedbackSummary(
            book_id=book_id,
            total_feedback=len(feedback_list),
            average_rating=avg_rating,
            rating_distribution=rating_dist,
            average_sentiment=avg_sentiment,
            sentiment_distribution=sentiment_dist,
            common_praises=common_praises[:10],
            common_issues=common_issues[:10],
            suggested_improvements=suggestions,
            completion_rate=completion_rate,
            return_rate=return_rate,
            recommendation_rate=recommendation_rate,
            feedback_trend=feedback_trend
        )

    def get_actionable_insights(
        self,
        book_id: str,
        min_frequency: int = 3
    ) -> Dict[str, Any]:
        """
        Get actionable insights from feedback.

        Args:
            book_id: Book identifier
            min_frequency: Minimum frequency for an issue to be actionable

        Returns:
            Dictionary of actionable insights
        """
        summary = self.analyze_book_feedback(book_id)

        if not summary:
            return {}

        insights = {
            'critical_issues': [],
            'quick_wins': [],
            'strengths_to_maintain': [],
            'reader_preferences': [],
            'improvement_priority': []
        }

        # Identify critical issues (mentioned frequently)
        for issue, count in summary.common_issues:
            if count >= min_frequency:
                severity = self._assess_issue_severity(issue, count, summary.total_feedback)
                insights['critical_issues'].append({
                    'issue': issue,
                    'frequency': count,
                    'severity': severity,
                    'impact_on_rating': self._estimate_rating_impact(issue, summary)
                })

        # Identify quick wins (easy fixes with high impact)
        if 'errors' in [i[0] for i in summary.common_issues]:
            insights['quick_wins'].append({
                'action': 'Fix typos and grammatical errors',
                'effort': 'low',
                'impact': 'high',
                'estimated_rating_improvement': 0.3
            })

        if 'confusion' in [i[0] for i in summary.common_issues]:
            insights['quick_wins'].append({
                'action': 'Clarify confusing plot points',
                'effort': 'medium',
                'impact': 'high',
                'estimated_rating_improvement': 0.4
            })

        # Identify strengths to maintain
        for praise, count in summary.common_praises:
            if count >= min_frequency:
                insights['strengths_to_maintain'].append({
                    'strength': praise,
                    'frequency': count,
                    'reader_impact': 'positive'
                })

        # Extract reader preferences
        insights['reader_preferences'] = self._extract_reader_preferences(
            summary,
            self.feedback_cache.get(book_id, [])
        )

        # Priority ranking
        insights['improvement_priority'] = self._rank_improvements(
            summary.suggested_improvements,
            summary.common_issues
        )

        return insights

    def compare_books(
        self,
        book_ids: List[str]
    ) -> Dict[str, Any]:
        """
        Compare feedback across multiple books.

        Args:
            book_ids: List of book IDs to compare

        Returns:
            Comparative analysis
        """
        comparisons = {
            'books': {},
            'best_practices': [],
            'common_issues': [],
            'success_patterns': []
        }

        summaries = {}
        for book_id in book_ids:
            summary = self.analyze_book_feedback(book_id)
            if summary:
                summaries[book_id] = summary
                comparisons['books'][book_id] = {
                    'rating': summary.average_rating,
                    'sentiment': summary.average_sentiment,
                    'total_feedback': summary.total_feedback
                }

        if len(summaries) < 2:
            return comparisons

        # Find best practices from highest rated books
        sorted_books = sorted(
            summaries.items(),
            key=lambda x: x[1].average_rating,
            reverse=True
        )

        if sorted_books:
            best_book_id, best_summary = sorted_books[0]
            comparisons['best_practices'] = [
                praise[0] for praise in best_summary.common_praises[:5]
            ]

        # Find common issues across books
        all_issues = []
        for summary in summaries.values():
            all_issues.extend([issue[0] for issue in summary.common_issues])

        issue_counts = {}
        for issue in all_issues:
            issue_counts[issue] = issue_counts.get(issue, 0) + 1

        comparisons['common_issues'] = [
            issue for issue, count in issue_counts.items()
            if count >= len(summaries) * 0.5  # Issue in 50%+ of books
        ]

        # Identify success patterns
        high_rated = [
            book_id for book_id, summary in summaries.items()
            if summary.average_rating >= 4.0
        ]

        if high_rated:
            success_patterns = set()
            for book_id in high_rated:
                summary = summaries[book_id]
                for praise, _ in summary.common_praises[:3]:
                    success_patterns.add(praise)

            comparisons['success_patterns'] = list(success_patterns)

        return comparisons

    def _analyze_feedback(self, feedback: Feedback) -> Feedback:
        """Analyze feedback text for sentiment and topics."""
        if not feedback.text:
            return feedback

        # Sentiment analysis using TextBlob
        try:
            blob = TextBlob(feedback.text)
            feedback.sentiment_score = blob.sentiment.polarity  # -1 to 1

            # Categorize sentiment
            if feedback.sentiment_score >= 0.5:
                feedback.sentiment_category = SentimentCategory.VERY_POSITIVE
            elif feedback.sentiment_score >= 0.1:
                feedback.sentiment_category = SentimentCategory.POSITIVE
            elif feedback.sentiment_score >= -0.1:
                feedback.sentiment_category = SentimentCategory.NEUTRAL
            elif feedback.sentiment_score >= -0.5:
                feedback.sentiment_category = SentimentCategory.NEGATIVE
            else:
                feedback.sentiment_category = SentimentCategory.VERY_NEGATIVE
        except Exception as e:
            logger.error(f"Sentiment analysis failed: {e}")

        # Extract topics
        feedback.topics = self._extract_topics(feedback.text)

        # Identify issues
        feedback.issues = self._identify_issues(feedback.text)

        # Identify praises
        feedback.praises = self._identify_praises(feedback.text)

        return feedback

    def _extract_topics(self, text: str) -> List[str]:
        """Extract topics from text."""
        topics = []
        text_lower = text.lower()

        for aspect, keywords in self.ASPECT_KEYWORDS.items():
            for keyword in keywords:
                if keyword in text_lower:
                    topics.append(aspect)
                    break

        return list(set(topics))

    def _identify_issues(self, text: str) -> List[str]:
        """Identify issues mentioned in text."""
        issues = []

        for issue_type, patterns in self.ISSUE_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, text, re.IGNORECASE):
                    issues.append(issue_type)
                    break

        return list(set(issues))

    def _identify_praises(self, text: str) -> List[str]:
        """Identify praises in text."""
        praises = []

        for praise_type, patterns in self.PRAISE_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, text, re.IGNORECASE):
                    praises.append(praise_type)
                    break

        return list(set(praises))

    def _count_themes(self, themes: List[str]) -> List[Tuple[str, int]]:
        """Count and rank themes."""
        theme_counts = {}
        for theme in themes:
            theme_counts[theme] = theme_counts.get(theme, 0) + 1

        return sorted(theme_counts.items(), key=lambda x: x[1], reverse=True)

    def _generate_improvement_suggestions(
        self,
        common_issues: List[Tuple[str, int]],
        feedback_list: List[Feedback]
    ) -> List[str]:
        """Generate specific improvement suggestions."""
        suggestions = []

        issue_dict = dict(common_issues)

        # Map issues to suggestions
        if issue_dict.get('repetitive', 0) > 2:
            suggestions.append("Reduce repetitive phrases and vary sentence structure")

        if issue_dict.get('confusion', 0) > 2:
            suggestions.append("Clarify plot points and character motivations")

        if issue_dict.get('boring', 0) > 2:
            suggestions.append("Increase pacing in middle chapters")

        if issue_dict.get('errors', 0) > 1:
            suggestions.append("Conduct thorough proofreading for typos and grammar")

        if issue_dict.get('shallow', 0) > 2:
            suggestions.append("Deepen character development and backstories")

        if issue_dict.get('rushed', 0) > 2:
            suggestions.append("Expand climax and resolution scenes")

        if issue_dict.get('unrealistic', 0) > 2:
            suggestions.append("Improve realism in character reactions and plot events")

        # Add rating-based suggestions
        ratings = [f.rating for f in feedback_list if f.rating]
        if ratings and statistics.mean(ratings) < 3.5:
            suggestions.append("Consider significant revision based on reader feedback")

        return suggestions[:7]  # Top 7 suggestions

    def _calculate_completion_rate(self, feedback_list: List[Feedback]) -> float:
        """Calculate book completion rate."""
        dnf_count = sum(1 for f in feedback_list if f.type == FeedbackType.DNF)
        total = len(feedback_list)

        if total == 0:
            return 0

        return (total - dnf_count) / total * 100

    def _calculate_return_rate(self, feedback_list: List[Feedback]) -> float:
        """Calculate return rate."""
        return_count = sum(1 for f in feedback_list if f.type == FeedbackType.RETURN)
        total = len(feedback_list)

        return (return_count / total * 100) if total > 0 else 0

    def _calculate_recommendation_rate(self, feedback_list: List[Feedback]) -> float:
        """Calculate recommendation rate."""
        recommend_count = sum(
            1 for f in feedback_list
            if f.praises and 'recommended' in f.praises
        )
        total = len(feedback_list)

        return (recommend_count / total * 100) if total > 0 else 0

    def _analyze_feedback_trend(self, feedback_list: List[Feedback]) -> List[Dict[str, Any]]:
        """Analyze rating trends over time."""
        # Sort by timestamp
        sorted_feedback = sorted(
            [f for f in feedback_list if f.rating],
            key=lambda x: x.timestamp
        )

        if not sorted_feedback:
            return []

        # Group by month
        monthly_data = {}
        for f in sorted_feedback:
            month = f.timestamp[:7]  # YYYY-MM
            if month not in monthly_data:
                monthly_data[month] = []
            monthly_data[month].append(f.rating)

        # Calculate monthly averages
        trend = []
        for month, ratings in sorted(monthly_data.items()):
            trend.append({
                'month': month,
                'average_rating': statistics.mean(ratings),
                'count': len(ratings)
            })

        return trend

    def _assess_issue_severity(
        self,
        issue: str,
        frequency: int,
        total_feedback: int
    ) -> str:
        """Assess severity of an issue."""
        percentage = (frequency / total_feedback * 100) if total_feedback > 0 else 0

        if percentage >= 30:
            return 'critical'
        elif percentage >= 15:
            return 'high'
        elif percentage >= 5:
            return 'medium'
        else:
            return 'low'

    def _estimate_rating_impact(
        self,
        issue: str,
        summary: BookFeedbackSummary
    ) -> float:
        """Estimate impact of fixing an issue on rating."""
        # Simplified estimation
        impact_map = {
            'errors': 0.3,
            'confusion': 0.4,
            'boring': 0.5,
            'shallow': 0.3,
            'rushed': 0.2,
            'repetitive': 0.2,
            'unrealistic': 0.3
        }

        return impact_map.get(issue, 0.1)

    def _extract_reader_preferences(
        self,
        summary: BookFeedbackSummary,
        feedback_list: List[Feedback]
    ) -> List[Dict[str, Any]]:
        """Extract reader preferences from feedback."""
        preferences = []

        # Analyze what readers liked most
        if summary.common_praises:
            top_praise = summary.common_praises[0][0]
            preferences.append({
                'preference': f"Readers love {top_praise}",
                'evidence': f"Mentioned in {summary.common_praises[0][1]} reviews"
            })

        # Analyze what readers disliked most
        if summary.common_issues:
            top_issue = summary.common_issues[0][0]
            preferences.append({
                'preference': f"Readers dislike {top_issue}",
                'evidence': f"Mentioned in {summary.common_issues[0][1]} reviews"
            })

        return preferences

    def _rank_improvements(
        self,
        suggestions: List[str],
        issues: List[Tuple[str, int]]
    ) -> List[Dict[str, Any]]:
        """Rank improvements by priority."""
        ranked = []

        for i, suggestion in enumerate(suggestions[:5]):
            priority = 'high' if i < 2 else 'medium' if i < 4 else 'low'
            ranked.append({
                'suggestion': suggestion,
                'priority': priority,
                'estimated_effort': 'medium',  # Would need more analysis
                'estimated_impact': 'high' if priority == 'high' else 'medium'
            })

        return ranked

    def _generate_feedback_id(self, book_id: str, source: str) -> str:
        """Generate unique feedback ID."""
        import hashlib
        timestamp = datetime.now().isoformat()
        data = f"{book_id}_{source}_{timestamp}"
        return hashlib.md5(data.encode()).hexdigest()[:12]

    def _save_feedback(self, feedback: Feedback):
        """Save feedback to database."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            INSERT OR REPLACE INTO feedback
            (id, book_id, type, source, rating, text, timestamp,
             reader_id, sentiment_score, sentiment_category, data)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (feedback.id, feedback.book_id, feedback.type.value,
              feedback.source, feedback.rating, feedback.text,
              feedback.timestamp, feedback.reader_id,
              feedback.sentiment_score,
              feedback.sentiment_category.value if feedback.sentiment_category else None,
              json.dumps(asdict(feedback))))

        conn.commit()
        conn.close()

    def _load_feedback(self):
        """Load feedback from database."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("SELECT data FROM feedback")

        for row in cursor.fetchall():
            feedback_data = json.loads(row[0])

            # Convert string enums back to enum types
            feedback_data['type'] = FeedbackType(feedback_data['type'])
            if feedback_data.get('sentiment_category'):
                feedback_data['sentiment_category'] = SentimentCategory(
                    feedback_data['sentiment_category']
                )

            feedback = Feedback(**feedback_data)

            if feedback.book_id not in self.feedback_cache:
                self.feedback_cache[feedback.book_id] = []
            self.feedback_cache[feedback.book_id].append(feedback)

        conn.close()

        logger.info(f"Loaded feedback for {len(self.feedback_cache)} books")