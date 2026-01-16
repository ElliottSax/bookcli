"""
Name Fixer - Handles character name consistency.

Fixes:
- Inconsistent character name spellings
- Name variations (nicknames vs full names)
- Pronoun/name mismatches
"""

import re
import json
from typing import Dict, List, Optional, Set, Tuple
from collections import Counter

from .base import BaseFixer, BookContext
from lib.logging_config import get_logger
from lib.api_client import get_api_client, extract_json_from_response

logger = get_logger(__name__)


class NameFixer(BaseFixer):
    """
    Fixes character name inconsistencies across chapters.

    Uses AI to:
    - Detect name variations
    - Determine canonical names
    - Apply consistent naming

    Optimizations:
    - Skips AI call if fewer than MIN_VARIATIONS_FOR_AI variations found
    - Uses heuristics for simple cases before calling AI
    """

    # Minimum number of variations to warrant an AI call
    MIN_VARIATIONS_FOR_AI = 3

    def __init__(self, context: BookContext, use_ai: bool = True):
        """
        Initialize name fixer.

        Args:
            context: Book context
            use_ai: Whether to use AI for name analysis (default True)
        """
        super().__init__(context)
        self.use_ai = use_ai
        self._name_mappings: Dict[str, str] = {}

    def describe(self) -> str:
        return "Fix character name inconsistencies"

    def fix(self) -> int:
        """Apply name consistency fixes."""
        if not self.use_ai:
            return self.fix_known_variations()

        # First, detect name variations
        variations = self.detect_name_variations()

        if not variations:
            logger.debug("No name variations detected")
            return 0

        # Count total variation pairs
        total_variations = sum(len(v) for v in variations.values())

        # Skip AI call for trivial cases - use heuristics instead
        if total_variations < self.MIN_VARIATIONS_FOR_AI:
            logger.info(f"Only {total_variations} variations found - using heuristics instead of AI")
            return self._apply_heuristic_fixes(variations)

        # Get canonical mappings from AI
        mappings = self.get_canonical_mappings(variations)

        if not mappings:
            return 0

        # Apply fixes
        return self.apply_name_mappings(mappings)

    def _apply_heuristic_fixes(self, variations: Dict[str, List[str]]) -> int:
        """
        Apply simple heuristic fixes without AI.

        Handles obvious cases like:
        - Typos (Jon -> John when John exists)
        - Case variations (john -> John)

        Args:
            variations: Dict of potential name variations

        Returns:
            Number of chapters modified
        """
        mappings = {}
        known_names = set(self.context.get_character_names())

        for name, similar in variations.items():
            for variant in similar:
                # If one is in story bible, prefer that
                if name in known_names and variant not in known_names:
                    mappings[variant] = name
                elif variant in known_names and name not in known_names:
                    mappings[name] = variant
                # Prefer longer name (John over Jon, Michael over Mike)
                elif len(name) > len(variant) + 1:
                    mappings[variant] = name
                elif len(variant) > len(name) + 1:
                    mappings[name] = variant

        if not mappings:
            return 0

        logger.info(f"Applying {len(mappings)} heuristic name fixes")
        return self.apply_name_mappings(mappings)

    def detect_name_variations(self) -> Dict[str, List[str]]:
        """
        Detect potential name variations in the text.

        Returns:
            Dict mapping base names to potential variations
        """
        # Get known character names from story bible
        known_names = set(self.context.get_character_names())

        # Extract all capitalized words that might be names
        all_names: Counter = Counter()

        for content in self.context.chapters.values():
            # Find capitalized words (potential names)
            words = re.findall(r'\b[A-Z][a-z]+\b', content)
            all_names.update(words)

        # Filter to likely character names (appear multiple times)
        frequent_names = {name for name, count in all_names.items() if count >= 3}

        # Find potential variations
        variations: Dict[str, List[str]] = {}

        for name in frequent_names:
            # Look for similar names (edit distance, common prefixes)
            similar = self._find_similar_names(name, frequent_names)
            if similar:
                variations[name] = similar

        return variations

    def _find_similar_names(self, name: str, all_names: Set[str]) -> List[str]:
        """Find names similar to the given name."""
        similar = []

        for other in all_names:
            if other == name:
                continue

            # Check for common prefix (at least 3 chars)
            if len(name) >= 3 and len(other) >= 3:
                if name[:3].lower() == other[:3].lower():
                    similar.append(other)
                    continue

            # Check for one being substring of other
            if name.lower() in other.lower() or other.lower() in name.lower():
                similar.append(other)
                continue

        return similar

    def get_canonical_mappings(self, variations: Dict[str, List[str]]) -> Dict[str, str]:
        """
        Use AI to determine canonical name mappings.

        Args:
            variations: Dict of potential name variations

        Returns:
            Dict mapping variant names to canonical names
        """
        if not variations:
            return {}

        # Build prompt for AI
        prompt = f"""Analyze these potential character name variations and determine which are the same character.

Variations found:
{json.dumps(variations, indent=2)}

Story context:
- Characters from story bible: {self.context.get_character_names()}

For each group of similar names, determine:
1. If they refer to the same character
2. What the canonical (correct) name should be

Return a JSON object mapping variant names to their canonical form.
Only include mappings where you're confident they're the same character.

Example output:
{{"Jonh": "John", "Johnny": "John", "J.": "John"}}

Return ONLY the JSON object, no explanation."""

        client = get_api_client()
        response = client.call(prompt, max_tokens=1000, temperature=0.3)

        if not response.success:
            logger.warning(f"AI call failed for name mappings: {response.error}")
            return {}

        mappings = extract_json_from_response(response.content)

        if not mappings or not isinstance(mappings, dict):
            logger.warning("Could not parse name mappings from AI response")
            return {}

        # Validate mappings
        valid_mappings = {}
        for variant, canonical in mappings.items():
            if isinstance(variant, str) and isinstance(canonical, str):
                if variant != canonical and len(variant) > 0 and len(canonical) > 0:
                    valid_mappings[variant] = canonical

        self._name_mappings = valid_mappings
        return valid_mappings

    def apply_name_mappings(self, mappings: Dict[str, str]) -> int:
        """
        Apply name mappings to all chapters.

        Args:
            mappings: Dict mapping variant names to canonical names

        Returns:
            Number of chapters modified
        """
        if not mappings:
            return 0

        fixes = 0

        for num, content in self.context.chapters.items():
            original = content

            for variant, canonical in mappings.items():
                # Use word boundary matching to avoid partial replacements
                pattern = r'\b' + re.escape(variant) + r'\b'
                content = re.sub(pattern, canonical, content)

            if content != original:
                self._save_chapter(num, content)
                self._log_fix(num, f"Fixed name variations")
                fixes += 1

        return fixes

    def fix_known_variations(self) -> int:
        """
        Fix common known name variations without AI.

        Returns:
            Number of chapters modified
        """
        # Common typo patterns
        common_fixes = [
            # Double letters
            (r'\b(\w+)([a-z])\2{2,}(\w*)\b', r'\1\2\2\3'),
        ]

        fixes = 0

        for num, content in self.context.chapters.items():
            original = content

            for pattern, replacement in common_fixes:
                content = re.sub(pattern, replacement, content)

            if content != original:
                self._save_chapter(num, content)
                self._log_fix(num, "Fixed name typos")
                fixes += 1

        return fixes

    def get_name_frequency(self) -> Dict[str, int]:
        """
        Get frequency count of all potential character names.

        Returns:
            Dict mapping names to occurrence counts
        """
        all_names: Counter = Counter()

        for content in self.context.chapters.values():
            # Find capitalized words
            words = re.findall(r'\b[A-Z][a-z]+\b', content)
            all_names.update(words)

        # Filter out common words
        common_words = {
            'The', 'He', 'She', 'They', 'It', 'We', 'You', 'But', 'And',
            'That', 'This', 'What', 'When', 'Where', 'Why', 'How', 'Who',
            'Chapter', 'Part', 'Book', 'Then', 'Now', 'Here', 'There',
        }

        return {
            name: count
            for name, count in all_names.items()
            if name not in common_words and count >= 3
        }
