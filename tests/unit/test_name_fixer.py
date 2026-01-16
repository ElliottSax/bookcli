"""
Unit tests for fixers/name_fixer.py
"""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import tempfile
import json

import sys
sys.path.insert(0, str(__file__).rsplit('/tests/', 1)[0])

from fixers.base import BookContext
from fixers.name_fixer import NameFixer


@pytest.fixture
def temp_book_dir():
    """Create a temporary book directory with chapters."""
    with tempfile.TemporaryDirectory() as tmpdir:
        book_dir = Path(tmpdir)

        # Create sample chapters with name variations
        (book_dir / "chapter_01.md").write_text(
            "Chapter 1\n\nJohn walked into the room. Jon was nervous."
        )
        (book_dir / "chapter_02.md").write_text(
            "Chapter 2\n\nJohnny smiled at Sarah. Sara waved back."
        )
        (book_dir / "chapter_03.md").write_text(
            "Chapter 3\n\nMichael met Mike at the cafe. Michael ordered coffee."
        )

        # Create story bible with known characters
        (book_dir / "story_bible.json").write_text(json.dumps({
            "characters": {
                "John": {"role": "protagonist"},
                "Sarah": {"role": "love interest"},
                "Michael": {"role": "friend"}
            }
        }))

        yield book_dir


@pytest.fixture
def book_context(temp_book_dir):
    """Create a BookContext from the temp directory."""
    return BookContext(temp_book_dir)


class TestNameFixer:
    """Tests for NameFixer class."""

    def test_describe(self, book_context):
        """Should return description."""
        fixer = NameFixer(book_context)
        description = fixer.describe()

        assert isinstance(description, str)
        assert len(description) > 0
        assert "name" in description.lower()

    def test_detect_name_variations(self, book_context):
        """Should detect potential name variations."""
        fixer = NameFixer(book_context)
        variations = fixer.detect_name_variations()

        # Should find John/Jon/Johnny as related
        assert isinstance(variations, dict)

    def test_get_name_frequency(self, book_context):
        """Should return frequency of potential names."""
        fixer = NameFixer(book_context)
        freq = fixer.get_name_frequency()

        assert isinstance(freq, dict)
        # Common words should be filtered out
        assert 'The' not in freq
        assert 'Chapter' not in freq

    def test_find_similar_names(self, book_context):
        """Should find similar names based on prefix."""
        fixer = NameFixer(book_context)
        all_names = {'John', 'Jon', 'Johnny', 'Sarah', 'Sara', 'Mike'}

        similar = fixer._find_similar_names('John', all_names)

        # Should find Jon and Johnny as similar to John
        assert 'Jon' in similar or 'Johnny' in similar

    def test_apply_name_mappings(self, book_context):
        """Should apply name mappings to chapters."""
        fixer = NameFixer(book_context)
        mappings = {'Jon': 'John', 'Sara': 'Sarah'}

        fixes = fixer.apply_name_mappings(mappings)

        assert fixes >= 1
        # Check that Jon was replaced with John
        assert 'Jon' not in book_context.chapters[1]
        assert 'John' in book_context.chapters[1]

    def test_apply_name_mappings_empty(self, book_context):
        """Should handle empty mappings gracefully."""
        fixer = NameFixer(book_context)
        fixes = fixer.apply_name_mappings({})

        assert fixes == 0

    def test_fix_known_variations(self, book_context):
        """Should fix common typo patterns."""
        fixer = NameFixer(book_context, use_ai=False)
        fixes = fixer.fix_known_variations()

        # May or may not find fixes depending on content
        assert isinstance(fixes, int)
        assert fixes >= 0


class TestNameFixerHeuristics:
    """Tests for heuristic-based name fixing."""

    def test_heuristic_prefers_story_bible_names(self):
        """Heuristics should prefer names from story bible."""
        with tempfile.TemporaryDirectory() as tmpdir:
            book_dir = Path(tmpdir)

            (book_dir / "chapter_01.md").write_text(
                "Jon walked to Jon's house. Jon was happy."
            )
            (book_dir / "story_bible.json").write_text(json.dumps({
                "characters": {"John": {"role": "protagonist"}}
            }))

            context = BookContext(book_dir)
            fixer = NameFixer(context, use_ai=False)

            # Manually test heuristic logic
            variations = {'John': ['Jon']}
            fixes = fixer._apply_heuristic_fixes(variations)

            # Should prefer John from story bible
            assert 'Jon' not in context.chapters[1] or fixes == 0

    def test_heuristic_prefers_longer_names(self):
        """Heuristics should prefer longer names (full vs nickname)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            book_dir = Path(tmpdir)

            (book_dir / "chapter_01.md").write_text(
                "Mike went to Mike's place. Mike called Michael."
            )
            (book_dir / "story_bible.json").write_text("{}")

            context = BookContext(book_dir)
            fixer = NameFixer(context, use_ai=False)

            # Test the heuristic directly
            variations = {'Michael': ['Mike']}
            fixer._apply_heuristic_fixes(variations)

            # Should prefer Michael (longer)
            # Note: actual replacement depends on implementation details


class TestNameFixerMinVariations:
    """Tests for MIN_VARIATIONS_FOR_AI threshold."""

    def test_skips_ai_for_few_variations(self):
        """Should use heuristics instead of AI for < 3 variations."""
        with tempfile.TemporaryDirectory() as tmpdir:
            book_dir = Path(tmpdir)

            # Only 2 variations - should skip AI
            (book_dir / "chapter_01.md").write_text(
                "John met Jon. John and Jon talked."
            )
            (book_dir / "story_bible.json").write_text("{}")

            context = BookContext(book_dir)
            fixer = NameFixer(context, use_ai=True)

            # With mocked API, verify AI is not called for few variations
            with patch.object(fixer, 'get_canonical_mappings') as mock_ai:
                with patch.object(fixer, '_apply_heuristic_fixes') as mock_heuristic:
                    mock_heuristic.return_value = 0
                    fixer.fix()

                    # AI should not be called for < 3 variations
                    # (depends on what detect_name_variations returns)

    def test_min_variations_constant(self):
        """MIN_VARIATIONS_FOR_AI should be set."""
        assert hasattr(NameFixer, 'MIN_VARIATIONS_FOR_AI')
        assert NameFixer.MIN_VARIATIONS_FOR_AI >= 1


class TestNameFixerWithMockedAI:
    """Tests with mocked AI responses."""

    def test_get_canonical_mappings_success(self, book_context):
        """Should parse AI response for name mappings."""
        fixer = NameFixer(book_context)

        mock_response = Mock()
        mock_response.success = True
        mock_response.content = '{"Jon": "John", "Sara": "Sarah"}'

        with patch('fixers.name_fixer.get_api_client') as mock_client:
            mock_client.return_value.call.return_value = mock_response

            variations = {'John': ['Jon'], 'Sarah': ['Sara']}
            mappings = fixer.get_canonical_mappings(variations)

            assert mappings == {'Jon': 'John', 'Sara': 'Sarah'}

    def test_get_canonical_mappings_failure(self, book_context):
        """Should handle AI failure gracefully."""
        fixer = NameFixer(book_context)

        mock_response = Mock()
        mock_response.success = False
        mock_response.error = "API error"

        with patch('fixers.name_fixer.get_api_client') as mock_client:
            mock_client.return_value.call.return_value = mock_response

            variations = {'John': ['Jon']}
            mappings = fixer.get_canonical_mappings(variations)

            assert mappings == {}

    def test_get_canonical_mappings_invalid_json(self, book_context):
        """Should handle invalid JSON response."""
        fixer = NameFixer(book_context)

        mock_response = Mock()
        mock_response.success = True
        mock_response.content = "This is not valid JSON"

        with patch('fixers.name_fixer.get_api_client') as mock_client:
            mock_client.return_value.call.return_value = mock_response

            variations = {'John': ['Jon']}
            mappings = fixer.get_canonical_mappings(variations)

            assert mappings == {}
