"""
Generation module for Book Factory
Enhanced chapter generation with proper length and rich content
"""

from .content_expansion_engine import (
    ContentExpansionEngine,
    ChapterGenerator,
    ChapterBlueprint,
    SceneStructure,
    ExpansionType
)

from .scene_depth_analyzer import (
    SceneDepthAnalyzer,
    SceneDepthAnalysis,
    DepthMetric
)

from .chapter_length_optimizer import (
    ChapterLengthOptimizer,
    ChapterMetrics,
    OptimizationStrategy
)

__all__ = [
    'ContentExpansionEngine',
    'ChapterGenerator',
    'ChapterBlueprint',
    'SceneStructure',
    'ExpansionType',
    'SceneDepthAnalyzer',
    'SceneDepthAnalysis',
    'DepthMetric',
    'ChapterLengthOptimizer',
    'ChapterMetrics',
    'OptimizationStrategy'
]