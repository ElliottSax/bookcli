"""
Text Fixer - Handles mechanical text quality issues.

Fixes:
- Doubled/tripled names (e.g., "Maya Chen Chen Chen")
- Unprocessed placeholders (e.g., "(primary setting)")
- LLM instruction artifacts (e.g., "**Target: 2500 words**")
- Duplicate content (repeated chapters/paragraphs)
- Repetitive AI phrases
"""

import re
from typing import List, Tuple, Set, Pattern

from .base import BaseFixer, BookContext
from lib.logging_config import get_logger

logger = get_logger(__name__)


# Pre-compiled LLM instruction artifact patterns (compiled once at module load)
LLM_ARTIFACTS: List[Pattern] = [
    re.compile(r'\*\*Target:\s*\d+\+?\s*words?\*\*', re.MULTILINE | re.IGNORECASE),
    re.compile(r'\*\*Additional Requirements:\*\*', re.MULTILINE | re.IGNORECASE),
    re.compile(r'\*\*Completed Chapter:\*\*', re.MULTILINE | re.IGNORECASE),
    re.compile(r'\*\*Requirements:\*\*', re.MULTILINE | re.IGNORECASE),
    re.compile(r'\*\*Word Count Target:\*\*', re.MULTILINE | re.IGNORECASE),
    re.compile(r'\*\*Chapter Requirements:\*\*', re.MULTILINE | re.IGNORECASE),
    re.compile(r'^\d+\.\s+Add\s+(?:more\s+)?sensory details.*$', re.MULTILINE | re.IGNORECASE),
    re.compile(r'^\d+\.\s+Expand\s+dialogue.*$', re.MULTILINE | re.IGNORECASE),
    re.compile(r'^\d+\.\s+Add\s+internal\s+thoughts.*$', re.MULTILINE | re.IGNORECASE),
    re.compile(r'^\d+\.\s+Describe\s+settings.*$', re.MULTILINE | re.IGNORECASE),
    re.compile(r'^\d+\.\s+Show\s+emotions.*$', re.MULTILINE | re.IGNORECASE),
    re.compile(r'^\d+\.\s+Add\s+tension.*$', re.MULTILINE | re.IGNORECASE),
]

# Pre-compiled placeholder patterns (pattern, replacement)
PLACEHOLDER_PATTERNS: List[Tuple[Pattern, str]] = [
    (re.compile(r'\s*\(primary\s+setting\)', re.IGNORECASE), ''),
    (re.compile(r'\s*\(primary\s+location\)', re.IGNORECASE), ''),
    (re.compile(r'\s*\(protagonist\)', re.IGNORECASE), ''),
    (re.compile(r'\s*\(antagonist\)', re.IGNORECASE), ''),
    (re.compile(r'\s*\(setting\)', re.IGNORECASE), ''),
    (re.compile(r'\s*\(location\)', re.IGNORECASE), ''),
    (re.compile(r'The City \(Exterior\)', re.IGNORECASE), 'the city'),
    (re.compile(r'\s*\([^)]*(?:primary|setting|location|protagonist|antagonist)[^)]*\)', re.IGNORECASE), ''),
]

# Pre-compiled overused AI phrase patterns
REPETITIVE_PHRASE_PATTERNS: List[Pattern] = [
    re.compile(r'(?:like\s+)?a\s+(?:key\s+turning|doorway\s+opening)\s+in\s+(?:her|his|their)\s+mind', re.IGNORECASE),
    re.compile(r'seemed\s+to\s+(?:haunt|fill|seep\s+into)\s+(?:her|his|their)\s+(?:very\s+)?soul', re.IGNORECASE),
    re.compile(r'(?:a\s+)?sense\s+of\s+\w+\s+that\s+seemed\s+to\s+(?:seep|creep|spread)', re.IGNORECASE),
    re.compile(r'(?:like\s+)?a\s+punch\s+to\s+the\s+gut', re.IGNORECASE),
    re.compile(r'(?:like\s+)?a\s+wake-?up\s+call', re.IGNORECASE),
    re.compile(r'a\s+living,?\s+breathing\s+(?:entity|thing|creature)', re.IGNORECASE),
    re.compile(r'seemed\s+to\s+(?:pour|flow|stream)\s+out\s+(?:of|from)\s+(?:her|him|them)', re.IGNORECASE),
    re.compile(r'(?:like\s+)?a\s+challenge,?\s+a\s+doorway', re.IGNORECASE),
    re.compile(r'the\s+sensation\s+like\s+a', re.IGNORECASE),
    re.compile(r'the\s+sound\s+like\s+a', re.IGNORECASE),
    re.compile(r'the\s+smell\s+like\s+a', re.IGNORECASE),
    re.compile(r'the\s+(?:feeling|thought|image)\s+like\s+a', re.IGNORECASE),
]

# Pre-compiled common patterns
TRIPLE_WORD = re.compile(r'\b(\w+)\s+\1\s+\1\b', re.IGNORECASE)
DOUBLE_WORD = re.compile(r'\b(\w+)\s+\1\b', re.IGNORECASE)
DOUBLE_PHRASE = re.compile(r'\b(\w+\s+\w+)\s+\1\b', re.IGNORECASE)
MULTIPLE_SPACES = re.compile(r'[ \t]+')
SPACE_BEFORE_PUNCT = re.compile(r' +([.,;:!?])')
LEADING_SPACES = re.compile(r'\n +')
TRAILING_SPACES = re.compile(r' +\n')
MULTIPLE_NEWLINES = re.compile(r'\n{3,}')


class TextFixer(BaseFixer):
    """
    Fixes mechanical text issues without requiring AI calls.

    This fixer handles:
    - Doubled/tripled names
    - Unprocessed placeholders
    - LLM artifacts
    - Duplicate content
    - Repetitive phrases
    """

    def describe(self) -> str:
        return "Fix doubled names, placeholders, LLM artifacts, and duplicates"

    def fix(self) -> int:
        """Apply all text fixes."""
        total = 0
        total += self.fix_doubled_names()
        total += self.fix_placeholders()
        total += self.fix_llm_artifacts()
        total += self.fix_duplicate_content()
        # Note: repetitive phrases detection only, no auto-fix
        return total

    def fix_doubled_names(self) -> int:
        """
        Fix doubled/tripled names like 'Maya Chen Chen Chen'.

        Uses multiple passes to handle nested cases.

        Returns:
            Number of chapters fixed
        """
        fixes = 0

        for num, content in self.context.chapters.items():
            original = content

            # Multiple passes for nested cases
            for _ in range(3):
                prev_content = content

                # Use pre-compiled patterns
                content = TRIPLE_WORD.sub(r'\1', content)
                content = DOUBLE_WORD.sub(r'\1', content)
                content = DOUBLE_PHRASE.sub(r'\1', content)

                if content == prev_content:
                    break

            if content != original:
                self._save_chapter(num, content)
                self._log_fix(num, "Fixed doubled names")
                fixes += 1

        return fixes

    def fix_placeholders(self) -> int:
        """
        Remove unprocessed placeholder text.

        Returns:
            Number of chapters fixed
        """
        # Get actual location from story bible for smart replacement
        location_name = self.context.get_setting()

        fixes = 0

        for num, content in self.context.chapters.items():
            original = content

            for pattern, replacement in PLACEHOLDER_PATTERNS:
                # Check if this is a location-related pattern
                pattern_str = pattern.pattern.lower()
                if 'setting' in pattern_str or 'location' in pattern_str:
                    actual_replacement = location_name
                else:
                    actual_replacement = replacement

                content = pattern.sub(actual_replacement, content)

            # Clean up using pre-compiled patterns
            content = MULTIPLE_SPACES.sub(' ', content)
            content = SPACE_BEFORE_PUNCT.sub(r'\1', content)
            content = LEADING_SPACES.sub('\n', content)
            content = TRAILING_SPACES.sub('\n', content)

            if content != original:
                self._save_chapter(num, content)
                self._log_fix(num, "Removed placeholders")
                fixes += 1

        return fixes

    def fix_llm_artifacts(self) -> int:
        """
        Remove LLM instruction artifacts that leaked into output.

        Returns:
            Number of chapters fixed
        """
        fixes = 0

        for num, content in self.context.chapters.items():
            original = content

            # Use pre-compiled patterns
            for pattern in LLM_ARTIFACTS:
                content = pattern.sub('', content)

            # Clean up extra blank lines
            content = MULTIPLE_NEWLINES.sub('\n\n', content)

            if content != original:
                self._save_chapter(num, content)
                self._log_fix(num, "Removed LLM artifacts")
                fixes += 1

        return fixes

    def fix_duplicate_content(self) -> int:
        """
        Fix chapters with duplicated content.

        Detects:
        - Full chapter duplication (same content repeated)
        - Paragraph-level duplication

        Returns:
            Number of chapters fixed
        """
        fixes = 0

        for num, content in self.context.chapters.items():
            original = content

            # Check for half-chapter duplication
            half_point = len(content) // 2
            first_half = content[:half_point].strip()

            if len(first_half) > 500:
                second_half = content[half_point:]

                # Check if first part appears in second part
                check = first_half[:200]
                if check in second_half:
                    dup_start = second_half.find(check)
                    if dup_start != -1:
                        content = content[:half_point + dup_start].strip()
                        self._save_chapter(num, content)
                        self._log_fix(num, "Removed duplicated chapter content")
                        fixes += 1
                        continue

            # Check for paragraph-level duplicates
            paragraphs = content.split('\n\n')
            if len(paragraphs) > 5:
                seen: Set[str] = set()
                unique_paragraphs = []

                for para in paragraphs:
                    # Normalize for comparison
                    normalized = ' '.join(para.split()).lower()

                    if len(normalized) > 100:  # Only check substantial paragraphs
                        if normalized not in seen:
                            seen.add(normalized)
                            unique_paragraphs.append(para)
                    else:
                        unique_paragraphs.append(para)

                if len(unique_paragraphs) < len(paragraphs):
                    content = '\n\n'.join(unique_paragraphs)
                    self._save_chapter(num, content)
                    self._log_fix(num, "Removed duplicate paragraphs")
                    fixes += 1

        return fixes

    def detect_repetitive_phrases(self) -> dict:
        """
        Detect overused AI phrases across the book.

        Returns:
            Dict mapping phrases to occurrence counts
        """
        phrase_counts = {}

        for pattern in REPETITIVE_PHRASE_PATTERNS:
            count = 0
            for content in self.context.chapters.values():
                matches = pattern.findall(content)
                count += len(matches)

            if count > 0:
                phrase_counts[pattern.pattern] = count

        return phrase_counts

    def get_stats(self) -> dict:
        """
        Get statistics about text issues in the book.

        Returns:
            Dict with counts of each issue type
        """
        stats = {
            'doubled_names': 0,
            'placeholders': 0,
            'llm_artifacts': 0,
            'duplicate_paragraphs': 0,
            'repetitive_phrases': 0,
        }

        for content in self.context.chapters.values():
            # Count doubled names using pre-compiled pattern
            stats['doubled_names'] += len(DOUBLE_WORD.findall(content))

            # Count placeholders
            for pattern, _ in PLACEHOLDER_PATTERNS:
                stats['placeholders'] += len(pattern.findall(content))

            # Count LLM artifacts
            for pattern in LLM_ARTIFACTS:
                stats['llm_artifacts'] += len(pattern.findall(content))

            # Count repetitive phrases
            for pattern in REPETITIVE_PHRASE_PATTERNS:
                stats['repetitive_phrases'] += len(pattern.findall(content))

        return stats
