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
                # Patterns are pre-compiled, use pattern.search() directly
                if pattern.search(test):
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
            # Paragraphs must be > 100 chars normalized to be checked for duplicates
            # Also need > 5 paragraphs total for detection to trigger
            long_para = "This is a paragraph with enough content to trigger the duplicate detection logic which requires paragraphs to be over one hundred characters long."
            content = f"""Chapter 1

{long_para}

This is paragraph two with different content here that is also fairly long to be substantial.

Another paragraph here to increase the count of paragraphs in this chapter.

{long_para}

Yet another paragraph to ensure we have more than five paragraphs total.

Final paragraph here with some extra content.
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
            assert result.count("This is a paragraph with enough content") == 1


class TestGenerationLoopFixer:
    """Tests for fix_generation_loops method."""

    def test_removes_heavily_repeated_sentences(self):
        """Should remove sentences that repeat more than 3 times."""
        with tempfile.TemporaryDirectory() as tmpdir:
            book_dir = Path(tmpdir)

            # Create chapter with repeated sentence (>3 times)
            repeated = "This sentence appears too many times in the text."
            content = f"""Chapter 1

First paragraph with normal content.

{repeated} Some other text. {repeated} More text here.

{repeated} Another paragraph. {repeated} And more.

Final paragraph with unique content here.
"""
            (book_dir / "chapter_01.md").write_text(content)
            (book_dir / "story_bible.json").write_text("{}")

            context = BookContext(book_dir)
            fixer = TextFixer(context)
            fixes = fixer.fix_generation_loops()

            # Should have removed duplicates (keeping only first occurrence)
            result = context.chapters[1]
            # Count should be 1 (only first occurrence kept)
            assert result.count("This sentence appears too many times") == 1

    def test_removes_near_duplicate_paragraphs_by_jaccard(self):
        """Should remove paragraphs with >80% Jaccard similarity."""
        with tempfile.TemporaryDirectory() as tmpdir:
            book_dir = Path(tmpdir)

            # Two paragraphs with very similar content (high Jaccard similarity)
            para1 = "The quick brown fox jumps over the lazy dog and runs into the forest looking for food and shelter from the rain"
            para2 = "The quick brown fox jumps over the lazy dog and runs into the forest searching for food and shelter from the rain"
            content = f"""Chapter 1

{para1}

Normal unique content here that is completely different from other paragraphs.

{para2}

Another unique paragraph with totally different content for the chapter.
"""
            (book_dir / "chapter_01.md").write_text(content)
            (book_dir / "story_bible.json").write_text("{}")

            context = BookContext(book_dir)
            fixer = TextFixer(context)
            fixes = fixer.fix_generation_loops()

            # Should have detected similarity and removed near-duplicate
            result = context.chapters[1]
            # Only one of the similar paragraphs should remain
            assert result.count("quick brown fox") == 1

    def test_preserves_unique_content(self):
        """Should not remove unique sentences or paragraphs."""
        with tempfile.TemporaryDirectory() as tmpdir:
            book_dir = Path(tmpdir)

            content = """Chapter 1

First paragraph with completely unique content.

Second paragraph is also unique and different.

Third paragraph has its own distinct text.
"""
            (book_dir / "chapter_01.md").write_text(content)
            (book_dir / "story_bible.json").write_text("{}")

            context = BookContext(book_dir)
            original_content = context.chapters[1]
            fixer = TextFixer(context)
            fixes = fixer.fix_generation_loops()

            # No fixes should be applied to unique content
            # Note: minor whitespace normalization may occur
            assert "First paragraph" in context.chapters[1]
            assert "Second paragraph" in context.chapters[1]
            assert "Third paragraph" in context.chapters[1]

    def test_ignores_short_sentences(self):
        """Should not process sentences shorter than 20 chars."""
        with tempfile.TemporaryDirectory() as tmpdir:
            book_dir = Path(tmpdir)

            # Short repeated sentences should be ignored
            content = """Chapter 1

She ran. She ran. She ran. She ran. She ran.

Longer unique paragraph content here with more words for testing purposes.
"""
            (book_dir / "chapter_01.md").write_text(content)
            (book_dir / "story_bible.json").write_text("{}")

            context = BookContext(book_dir)
            fixer = TextFixer(context)
            fixer.fix_generation_loops()

            # Short sentences should still be present (all of them)
            result = context.chapters[1]
            assert result.count("She ran.") >= 4  # At least 4 should remain

    def test_ignores_small_paragraphs(self):
        """Should not check Jaccard similarity on paragraphs with <10 words."""
        with tempfile.TemporaryDirectory() as tmpdir:
            book_dir = Path(tmpdir)

            # Small similar paragraphs shouldn't trigger similarity check
            content = """Chapter 1

Hello there.

Hello there.

Hello there.

Longer paragraph here with more content to make the test valid.
"""
            (book_dir / "chapter_01.md").write_text(content)
            (book_dir / "story_bible.json").write_text("{}")

            context = BookContext(book_dir)
            fixer = TextFixer(context)
            fixer.fix_generation_loops()

            # Small paragraphs should be preserved (not checked by Jaccard)
            result = context.chapters[1]
            assert result.count("Hello there.") >= 2  # At least 2 should remain
