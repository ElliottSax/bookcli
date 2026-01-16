"""
BookCLI Fixers - Modular text quality improvement tools.

Each fixer handles a single category of quality issues:
- TextFixer: Doubled names, placeholders, LLM artifacts, duplicates
- NameFixer: Character name consistency across chapters
- QualityFixer: POV consistency, dialogue depth, pacing
"""

from .base import BaseFixer, BookContext
from .text_fixer import TextFixer
from .name_fixer import NameFixer
from .quality_fixer import QualityFixer

__all__ = [
    'BaseFixer',
    'BookContext',
    'TextFixer',
    'NameFixer',
    'QualityFixer',
]
