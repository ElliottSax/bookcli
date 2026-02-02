"""
Text Fixer - Handles mechanical text quality issues.

Fixes:
- Doubled/tripled names (e.g., "Maya Chen Chen Chen")
- Unprocessed placeholders (e.g., "(primary setting)")
- LLM instruction artifacts (e.g., "**Target: 2500 words**")
- Duplicate content (repeated chapters/paragraphs)
- Generation loops (repeated sentences across chapter)
- Repetitive AI phrases
"""

import re
from collections import Counter
from typing import List, Tuple, Set, Pattern, Dict

from .base import BaseFixer, BookContext
from lib.logging_config import get_logger

# Import patterns from consolidated pattern library
from lib.patterns import (
    AI_ARTIFACT_PATTERNS as LLM_ARTIFACTS,
    PLACEHOLDER_PATTERNS,
    REPETITIVE_PHRASE_PATTERNS,
    TRIPLE_WORD,
    DOUBLE_WORD,
    DOUBLE_PHRASE,
    MULTIPLE_SPACES,
    SPACE_BEFORE_PUNCT,
    LEADING_SPACES,
    TRAILING_SPACES,
    MULTIPLE_NEWLINES,
)

logger = get_logger(__name__)


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
        total += self.fix_generation_loops()
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

    def fix_generation_loops(self) -> int:
        """
        Fix generation loops where sentences repeat excessively.

        This handles AI generation bugs where:
        - Sentences repeat more than 3 times across the chapter
        - Near-duplicate paragraphs (>80% Jaccard similarity)

        Returns:
            Number of chapters fixed
        """
        fixes = 0

        for num, content in self.context.chapters.items():
            original = content
            original_size = len(content)

            # PHASE 1: Global sentence deduplication
            all_sentences = re.findall(r'[^.!?]+[.!?]+', content)

            # Build mapping of lowercase -> original sentences
            lowercase_to_originals: Dict[str, Set[str]] = {}
            for s in all_sentences:
                s_stripped = s.strip()
                if len(s_stripped) > 20:
                    lower = s_stripped.lower()
                    if lower not in lowercase_to_originals:
                        lowercase_to_originals[lower] = set()
                    lowercase_to_originals[lower].add(s_stripped)

            global_sent_counts = Counter(
                s.strip().lower() for s in all_sentences if len(s.strip()) > 20
            )

            # Get all original forms of heavily repeated sentences (>5 times to avoid removing legitimate emphasis)
            heavily_repeated: Set[str] = set()
            for lower, count in global_sent_counts.items():
                if count > 5:
                    heavily_repeated.update(lowercase_to_originals.get(lower, set()))

            sentences_removed = 0

            if heavily_repeated:
                # Remove all but the first occurrence of each heavily repeated sentence
                for repeated_sent in heavily_repeated:
                    pattern = re.escape(repeated_sent)
                    matches = list(re.finditer(pattern, content))

                    if len(matches) > 1:
                        # Remove all but the first occurrence (going backwards to preserve indices)
                        for match in reversed(matches[1:]):
                            start, end = match.start(), match.end()
                            # Remove the sentence and any following whitespace
                            while end < len(content) and content[end] in ' \t':
                                end += 1
                            content = content[:start] + content[end:]
                            sentences_removed += 1

            # PHASE 2: Near-duplicate paragraph removal using Jaccard similarity
            paragraphs = re.split(r'\n\s*\n', content)
            unique_paragraphs = []
            paragraphs_removed = 0

            for para in paragraphs:
                para_stripped = para.strip()
                if not para_stripped:
                    continue

                is_duplicate = False
                para_words = set(para_stripped.lower().split())

                # Check Jaccard similarity against existing paragraphs
                if len(para_words) > 10:  # Only check substantial paragraphs
                    for existing in unique_paragraphs:
                        existing_words = set(existing.lower().split())
                        if len(existing_words) > 10:
                            intersection = len(para_words & existing_words)
                            union = len(para_words | existing_words)
                            similarity = intersection / union if union > 0 else 0
                            if similarity > 0.95:  # Require 95% match to avoid removing similar-but-different content
                                is_duplicate = True
                                paragraphs_removed += 1
                                break

                if not is_duplicate:
                    unique_paragraphs.append(para_stripped)

            if paragraphs_removed > 0 or sentences_removed > 0:
                content = '\n\n'.join(unique_paragraphs)
                if not content.endswith('\n'):
                    content += '\n'

                bytes_removed = original_size - len(content)
                if bytes_removed > 0:
                    self._save_chapter(num, content)
                    self._log_fix(
                        num,
                        f"Fixed generation loops ({sentences_removed} sentences, "
                        f"{paragraphs_removed} paragraphs, {bytes_removed:,} bytes removed)"
                    )
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
