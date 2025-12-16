"""
Feedback module for Book Factory
Collects and analyzes reader feedback
"""

from .feedback_collector import (
    FeedbackCollector,
    Feedback,
    FeedbackType,
    BookFeedbackSummary,
    SentimentCategory
)

__all__ = [
    'FeedbackCollector',
    'Feedback',
    'FeedbackType',
    'BookFeedbackSummary',
    'SentimentCategory'
]