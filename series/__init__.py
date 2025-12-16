"""
Series module for Book Factory
Manages consistency across multi-book series
"""

from .coherence_engine import (
    SeriesCoherenceEngine,
    Character,
    Location,
    Event,
    Relationship,
    ElementType
)

__all__ = [
    'SeriesCoherenceEngine',
    'Character',
    'Location',
    'Event',
    'Relationship',
    'ElementType'
]