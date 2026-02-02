"""
BookCLI Fixers - Modular text quality improvement tools.

Each fixer handles a single category of quality issues:
- TextFixer: Doubled names, placeholders, LLM artifacts, duplicates
- NameFixer: Character name consistency across chapters
- QualityFixer: POV, dialogue, pacing, sensory details, tension, endings
- CoherencyFixer: Generation loops, content duplications, consistency

These fixers are used by:
- book_fixer.py: Main CLI tool
- autonomous_pipeline.py: Automated book production
- master_quality_pipeline.py: Batch quality improvement
"""

from .base import BaseFixer, BookContext, FixerPipeline
from .text_fixer import TextFixer
from .name_fixer import NameFixer
from .quality_fixer import QualityFixer
from .hook_strengthener import HookStrengthener, analyze_book_hooks
from .variety_fixer import VarietyFixer, analyze_book_variety
from .coherency_fixer import CoherencyFixer

__all__ = [
    'BaseFixer',
    'BookContext',
    'FixerPipeline',
    'TextFixer',
    'NameFixer',
    'QualityFixer',
    'HookStrengthener',
    'analyze_book_hooks',
    'VarietyFixer',
    'analyze_book_variety',
    'CoherencyFixer',
]
