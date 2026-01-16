"""
Unit tests for fixers/text_fixer.py
"""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import tempfile
import os

import sys
sys.path.insert(0, str(__file__).rsplit('/tests/', 1)[0])

from fixers.base import BookContext
from fixers.text_fixer import TextFixer


@pytest.fixture
def temp_book_dir():
    """Create a temporary book directory with chapters."""
    with tempfile.TemporaryDirectory() as tmpdir:
        book_dir = Path(tmpdir)

        # Create sample chapters
        (book_dir / "chapter_01.md").write_text(
            "Chapter 1\n\nMaya Chen Chen Chen walked into the room."
        )
        (book_dir / "chapter_02.md").write_text(
            "Chapter 2\n\nThe The city was dark."
        )
        (book_dir / "chapter_03.md").write_text(
            "Chapter 3\n\n**Target: 2500 words**\n\nNormal content here."
        )
        (book_dir / "chapter_04.md").write_text(
            "Chapter 4\n\nShe walked to the (primary setting)."
        )

        # Create story bible
        (book_dir / "story_bible.json").write_text(
            '{"setting": {"primary_location": "grand library"}}'
        )

        yield book_dir


@pytest.fixture
def book_context(temp_book_dir):
    """Create a BookContext from the temp directory."""
    return BookContext(temp_book_dir)


class TestTextFixer:
    """Tests for TextFixer class."""

    def test_fix_doubled_names_triple(self, book_context):
        """Should fix tripled names."""
        fixer = TextFixer(book_context)
        fixes = fixer.fix_doubled_names()

        assert fixes >= 1
        assert "Maya Chen Chen Chen" not in book_context.chapters[1]
        assert "Maya Chen" in book_context.chapters[1]

    def test_fix_doubled_names_double(self, book_context):
        """Should fix doubled words."""
        fixer = TextFixer(book_context)
        fixes = fixer.fix_doubled_names()

        assert "The The" not in book_context.chapters[2]
        assert "The city" in book_context.chapters[2]

    def test_fix_llm_artifacts(self, book_context):
        """Should remove LLM artifacts."""
        fixer = TextFixer(book_context)
        fixes = fixer.fix_llm_artifacts()

        assert fixes >= 1
        assert "**Target:" not in book_context.chapters[3]
        assert "Normal content here" in book_context.chapters[3]

    def test_fix_placeholders(self, book_context):
        """Should remove placeholder text."""
        fixer = TextFixer(book_context)
        fixes = fixer.fix_placeholders()

        assert fixes >= 1
        assert "(primary setting)" not in book_context.chapters[4]

    def test_fix_all(self, book_context):
        """fix() should apply all fixes."""
        fixer = TextFixer(book_context)
        total = fixer.fix()

        assert total >= 3  # At least 3 types of fixes applied

    def test_get_stats(self, book_context):
        """Should return statistics about issues."""
        fixer = TextFixer(book_context)
        stats = fixer.get_stats()

        assert 'doubled_names' in stats
        assert 'placeholders' in stats
        assert 'llm_artifacts' in stats

    def test_describe(self, book_context):
        """Should return description."""
        fixer = TextFixer(book_context)
        description = fixer.describe()

        assert isinstance(description, str)
        assert len(description) > 0


class TestTextFixerPatterns:
    """Test specific pattern matching."""

    def test_doubled_name_case_insensitive(self):
        """Should match doubled names regardless of case."""
        import re
        pattern = r'\b(\w+)\s+\1\b'

        assert re.search(pattern, "The the", re.IGNORECASE)
        assert re.search(pattern, "MAYA MAYA", re.IGNORECASE)

    def test_triple_word_pattern(self):
        """Should match tripled words."""
        import re
        pattern = r'\b(\w+)\s+\1\s+\1\b'

        assert re.search(pattern, "word word word", re.IGNORECASE)
        assert re.search(pattern, "Chen Chen Chen", re.IGNORECASE)

    def test_llm_artifact_patterns(self):
        """Should match LLM artifacts."""
        import re
        from fixers.text_fixer import LLM_ARTIFACTS

        test_cases = [
            "**Target: 2500 words**",
            "**Target: 3000+ words**",
            "**Additional Requirements:**",
            "**Word Count Target:**",
        ]

        for test in test_cases:
            matched = False
            for pattern in LLM_ARTIFACTS:
                if re.search(pattern, test, re.IGNORECASE | re.MULTILINE):
                    matched = True
                    break
            assert matched, f"Pattern should match: {test}"


class TestDuplicateDetection:
    """Tests for duplicate content detection."""

    def test_detects_paragraph_duplicates(self):
        """Should detect duplicated paragraphs."""
        with tempfile.TemporaryDirectory() as tmpdir:
            book_dir = Path(tmpdir)

            # Create chapter with duplicate paragraph
            content = """Chapter 1

This is paragraph one with enough content to be checked.

This is paragraph two with different content here.

This is paragraph one with enough content to be checked.

Final paragraph here.
"""
            (book_dir / "chapter_01.md").write_text(content)
            (book_dir / "story_bible.json").write_text("{}")

            context = BookContext(book_dir)
            fixer = TextFixer(context)
            fixes = fixer.fix_duplicate_content()

            # Should have removed duplicate
            assert fixes >= 1
            # Count occurrences of the duplicate paragraph
            result = context.chapters[1]
            assert result.count("This is paragraph one") == 1
