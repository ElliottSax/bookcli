"""
Unit tests for fixers/base.py BookContext class
"""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch
import tempfile
import json

import sys
sys.path.insert(0, str(__file__).rsplit('/tests/', 1)[0])

from fixers.base import BookContext, BaseFixer, FixerPipeline


@pytest.fixture
def temp_book_dir():
    """Create a temporary book directory with chapters."""
    with tempfile.TemporaryDirectory() as tmpdir:
        book_dir = Path(tmpdir)

        # Create sample chapters
        (book_dir / "chapter_01.md").write_text(
            "Chapter 1\n\nThis is the first chapter with some content."
        )
        (book_dir / "chapter_02.md").write_text(
            "Chapter 2\n\nThis is the second chapter with more content here."
        )
        (book_dir / "chapter_03.md").write_text(
            "Chapter 3\n\nThis is the third chapter with even more content."
        )

        # Create story bible
        (book_dir / "story_bible.json").write_text(json.dumps({
            "characters": {
                "Maya Chen": {"role": "protagonist", "age": 28},
                "John Smith": {"role": "antagonist"}
            },
            "setting": {
                "primary_location": "New York City",
                "time_period": "present day"
            },
            "protagonist": {"name": "Maya Chen"}
        }))

        yield book_dir


@pytest.fixture
def book_context(temp_book_dir):
    """Create a BookContext from the temp directory."""
    return BookContext(temp_book_dir)


class TestBookContextInit:
    """Tests for BookContext initialization."""

    def test_loads_chapters(self, book_context):
        """Should load all chapter files."""
        assert len(book_context.chapters) == 3
        assert 1 in book_context.chapters
        assert 2 in book_context.chapters
        assert 3 in book_context.chapters

    def test_chapters_have_content(self, book_context):
        """Chapters should have their content."""
        assert "first chapter" in book_context.chapters[1]
        assert "second chapter" in book_context.chapters[2]

    def test_loads_story_bible(self, book_context):
        """Should load story bible."""
        assert 'characters' in book_context.story_bible
        assert 'setting' in book_context.story_bible

    def test_handles_missing_story_bible(self):
        """Should handle missing story bible gracefully."""
        with tempfile.TemporaryDirectory() as tmpdir:
            book_dir = Path(tmpdir)
            (book_dir / "chapter_01.md").write_text("Content")

            context = BookContext(book_dir)
            assert context.story_bible == {}

    def test_handles_invalid_story_bible(self):
        """Should handle invalid JSON in story bible."""
        with tempfile.TemporaryDirectory() as tmpdir:
            book_dir = Path(tmpdir)
            (book_dir / "chapter_01.md").write_text("Content")
            (book_dir / "story_bible.json").write_text("not valid json{{{")

            context = BookContext(book_dir)
            assert context.story_bible == {}


class TestBookContextProperties:
    """Tests for BookContext properties."""

    def test_name_property(self, book_context, temp_book_dir):
        """name should return directory name."""
        assert book_context.name == temp_book_dir.name

    def test_chapter_count_property(self, book_context):
        """chapter_count should return number of chapters."""
        assert book_context.chapter_count == 3


class TestBookContextCaching:
    """Tests for BookContext caching behavior."""

    def test_character_names_cached(self, book_context):
        """Character names should be cached after first call."""
        # First call
        names1 = book_context.get_character_names()
        assert book_context._cached_character_names is not None

        # Second call should return cached value
        names2 = book_context.get_character_names()
        assert names1 == names2

    def test_setting_cached(self, book_context):
        """Setting should be cached after first call."""
        # First call
        setting1 = book_context.get_setting()
        assert book_context._cached_setting is not None

        # Second call should return cached value
        setting2 = book_context.get_setting()
        assert setting1 == setting2

    def test_word_counts_cached(self, book_context):
        """Word counts should be cached after first call."""
        # First call
        count1 = book_context.get_word_count(1)
        assert book_context._cached_word_counts is not None
        assert 1 in book_context._cached_word_counts

        # Second call should use cache
        count2 = book_context.get_word_count(1)
        assert count1 == count2

    def test_total_words_cached(self, book_context):
        """Total words should be cached after first call."""
        # First call
        total1 = book_context.get_total_words()
        assert book_context._cached_total_words is not None

        # Second call should return cached value
        total2 = book_context.get_total_words()
        assert total1 == total2

    def test_invalidate_cache(self, book_context):
        """invalidate_cache should clear all cached values."""
        # Populate caches
        book_context.get_character_names()
        book_context.get_setting()
        book_context.get_word_count(1)
        book_context.get_total_words()

        # Invalidate
        book_context.invalidate_cache()

        assert book_context._cached_character_names is None
        assert book_context._cached_setting is None
        assert book_context._cached_word_counts is None
        assert book_context._cached_total_words is None

    def test_save_chapter_invalidates_word_cache(self, book_context):
        """Saving a chapter should invalidate word count caches."""
        # Populate cache
        book_context.get_word_count(1)
        book_context.get_total_words()

        # Save chapter
        book_context.save_chapter(1, "New content with different word count")

        # Caches should be invalidated
        assert book_context._cached_word_counts is None
        assert book_context._cached_total_words is None


class TestBookContextCharacterExtraction:
    """Tests for character name extraction."""

    def test_extracts_from_dict_characters(self, book_context):
        """Should extract names from dict-style characters."""
        names = book_context.get_character_names()

        assert "Maya Chen" in names
        assert "John Smith" in names

    def test_extracts_protagonist(self, book_context):
        """Should extract protagonist name."""
        names = book_context.get_character_names()

        # Protagonist is added separately
        assert "Maya Chen" in names

    def test_handles_list_characters(self):
        """Should handle list-style character definitions."""
        with tempfile.TemporaryDirectory() as tmpdir:
            book_dir = Path(tmpdir)
            (book_dir / "chapter_01.md").write_text("Content")
            (book_dir / "story_bible.json").write_text(json.dumps({
                "characters": [
                    {"name": "Alice"},
                    {"name": "Bob"},
                    "Charlie"  # String directly
                ]
            }))

            context = BookContext(book_dir)
            names = context.get_character_names()

            assert "Alice" in names
            assert "Bob" in names
            assert "Charlie" in names


class TestBookContextSettingExtraction:
    """Tests for setting extraction."""

    def test_extracts_primary_location(self, book_context):
        """Should extract primary_location from setting."""
        setting = book_context.get_setting()
        assert setting == "New York City"

    def test_handles_string_setting(self):
        """Should handle string setting."""
        with tempfile.TemporaryDirectory() as tmpdir:
            book_dir = Path(tmpdir)
            (book_dir / "chapter_01.md").write_text("Content")
            (book_dir / "story_bible.json").write_text(json.dumps({
                "setting": "A magical forest"
            }))

            context = BookContext(book_dir)
            setting = context.get_setting()
            assert setting == "A magical forest"

    def test_default_setting(self):
        """Should return default if no setting found."""
        with tempfile.TemporaryDirectory() as tmpdir:
            book_dir = Path(tmpdir)
            (book_dir / "chapter_01.md").write_text("Content")
            (book_dir / "story_bible.json").write_text("{}")

            context = BookContext(book_dir)
            setting = context.get_setting()
            assert setting == "the estate"  # Default


class TestBookContextSaveChapter:
    """Tests for chapter saving."""

    def test_save_chapter_updates_content(self, book_context):
        """Should update chapter content in memory."""
        new_content = "New chapter content"
        book_context.save_chapter(1, new_content)

        assert book_context.chapters[1] == new_content

    def test_save_chapter_writes_file(self, book_context, temp_book_dir):
        """Should write content to file."""
        new_content = "New chapter content for file"
        book_context.save_chapter(1, new_content)

        file_content = (temp_book_dir / "chapter_01.md").read_text()
        assert file_content == new_content

    def test_save_chapter_returns_success(self, book_context):
        """Should return True on success."""
        result = book_context.save_chapter(1, "New content")
        assert result is True


class TestFixerPipeline:
    """Tests for FixerPipeline class."""

    def test_pipeline_creation(self, book_context):
        """Should create pipeline with context."""
        pipeline = FixerPipeline(book_context)
        assert pipeline.context == book_context
        assert len(pipeline.fixers) == 0

    def test_add_fixer_chaining(self, book_context):
        """add() should return self for chaining."""
        # Create a mock fixer class
        class MockFixer(BaseFixer):
            def fix(self):
                return 0
            def describe(self):
                return "Mock fixer"

        pipeline = FixerPipeline(book_context)
        result = pipeline.add(MockFixer)

        assert result is pipeline  # Should return self
        assert len(pipeline.fixers) == 1

    def test_pipeline_run(self, book_context):
        """run() should execute all fixers."""
        class MockFixer(BaseFixer):
            def fix(self):
                return 5
            def describe(self):
                return "Mock"

        pipeline = FixerPipeline(book_context)
        pipeline.add(MockFixer)
        pipeline.add(MockFixer)

        total = pipeline.run()
        assert total == 10  # 5 + 5


class TestBaseFixer:
    """Tests for BaseFixer abstract class."""

    def test_cannot_instantiate_directly(self, book_context):
        """Should not be able to instantiate BaseFixer directly."""
        with pytest.raises(TypeError):
            BaseFixer(book_context)

    def test_subclass_must_implement_fix(self, book_context):
        """Subclass must implement fix()."""
        class IncompleteFixer(BaseFixer):
            def describe(self):
                return "Incomplete"

        with pytest.raises(TypeError):
            IncompleteFixer(book_context)

    def test_subclass_must_implement_describe(self, book_context):
        """Subclass must implement describe()."""
        class IncompleteFixer(BaseFixer):
            def fix(self):
                return 0

        with pytest.raises(TypeError):
            IncompleteFixer(book_context)

    def test_valid_subclass(self, book_context):
        """Valid subclass should work."""
        class ValidFixer(BaseFixer):
            def fix(self):
                return 1
            def describe(self):
                return "Valid fixer"

        fixer = ValidFixer(book_context)
        assert fixer.fix() == 1
        assert fixer.describe() == "Valid fixer"
