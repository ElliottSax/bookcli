"""
Analytics module for Book Factory
Tracks and predicts book success metrics
"""

from .success_tracker import (
    SuccessAnalytics,
    BookPerformance,
    SuccessPredictor,
    MetricType
)

__all__ = [
    'SuccessAnalytics',
    'BookPerformance',
    'SuccessPredictor',
    'MetricType'
]