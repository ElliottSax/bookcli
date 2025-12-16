"""
Marketing module for Book Factory
Generates marketing copy, blurbs, and promotional content
"""

from .marketing_copy_generator import (
    MarketingCopyGenerator,
    MarketingCopy,
    CopyType
)

__all__ = [
    'MarketingCopyGenerator',
    'MarketingCopy',
    'CopyType'
]