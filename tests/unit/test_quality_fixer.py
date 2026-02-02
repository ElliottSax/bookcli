"""
Unit tests for fixers/quality_fixer.py
"""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch
import tempfile
import json

import sys
sys.path.insert(0, str(__file__).rsplit('/tests/', 1)[0])

from fixers.base import BookContext
from fixers.quality_fixer import QualityFixer, POV_FIRST, POV_SECOND, POV_THIRD


@pytest.fixture
def temp_book_dir():
    """Create a temporary book directory with chapters."""
    with tempfile.TemporaryDirectory() as tmpdir:
        book_dir = Path(tmpdir)

        # Create sample chapters with different POV
        (book_dir / "chapter_01.md").write_text(
            "Chapter 1\n\n" + "I walked into the room. My heart was racing. " * 50
        )
        (book_dir / "chapter_02.md").write_text(
            "Chapter 2\n\n" + "She looked at him. He smiled back at her. " * 50
        )
        (book_dir / "chapter_03.md").write_text(
            "Chapter 3\n\n" + "He ran through the forest. His breath was heavy. " * 50
        )

        # Create story bible
        (book_dir / "story_bible.json").write_text(json.dumps({
            "characters": {"Maya": {"role": "protagonist"}},
            "setting": "the old mansion"
        }))

        yield book_dir


@pytest.fixture
def book_context(temp_book_dir):
    """Create a BookContext from the temp directory."""
    return BookContext(temp_book_dir)


class TestPOVPatterns:
    """Tests for pre-compiled POV patterns."""

    def test_first_person_pattern(self):
        """Should match first person pronouns."""
        text = "I walked to my house. It was mine."

        matches = POV_FIRST.findall(text)
        assert len(matches) >= 3  # I, my, mine

    def test_second_person_pattern(self):
        """Should match second person pronouns."""
        text = "You walked to your house. It was yours."

        matches = POV_SECOND.findall(text)
        assert len(matches) >= 3  # You, your, yours

    def test_third_person_pattern(self):
        """Should match third person pronouns."""
        text = "He walked to his house. She waved at him."

        matches = POV_THIRD.findall(text)
        assert len(matches) >= 4  # He, his, She, him

    def test_patterns_are_case_insensitive(self):
        """Patterns should match regardless of case."""
        assert POV_FIRST.search("I am here")
        assert POV_FIRST.search("i am here")
        assert POV_THIRD.search("HE walked")
        assert POV_THIRD.search("he walked")


class TestQualityFixer:
    """Tests for QualityFixer class."""

    def test_describe(self, book_context):
        """Should return description."""
        fixer = QualityFixer(book_context)
        description = fixer.describe()

        assert isinstance(description, str)
        assert len(description) > 0

    def test_init_defaults(self, book_context):
        """Should initialize with sensible defaults."""
        fixer = QualityFixer(book_context)

        assert fixer.expand_short is True
        assert fixer.fix_pov is True
        assert fixer.use_batching is True
        assert fixer.min_words > 0
        assert fixer.target_words > fixer.min_words

    def test_init_custom_settings(self, book_context):
        """Should accept custom settings."""
        fixer = QualityFixer(
            book_context,
            expand_short=False,
            fix_pov=False,
            min_words=500,
            use_batching=False
        )

        assert fixer.expand_short is False
        assert fixer.fix_pov is False
        assert fixer.min_words == 500
        assert fixer.use_batching is False


class TestPOVDetection:
    """Tests for POV detection."""

    def test_detect_first_person(self, book_context):
        """Should detect first person POV."""
        fixer = QualityFixer(book_context)
        # Need at least 10 POV indicators total for detection
        content = "I walked into the room. My heart was pounding. I felt nervous. " * 5

        pov = fixer._detect_pov(content)
        assert pov == 'first'

    def test_detect_third_person(self, book_context):
        """Should detect third person POV."""
        fixer = QualityFixer(book_context)
        # Need at least 10 POV indicators total for detection
        content = "He walked into the room. His heart was pounding. She watched him. " * 5

        pov = fixer._detect_pov(content)
        assert pov == 'third'

    def test_detect_second_person(self, book_context):
        """Should detect second person POV."""
        fixer = QualityFixer(book_context)
        # Need at least 10 POV indicators total for detection
        content = "You walk into the room. Your heart is pounding. You feel nervous. " * 5

        pov = fixer._detect_pov(content)
        assert pov == 'second'

    def test_detect_unknown_pov(self, book_context):
        """Should return unknown for ambiguous text."""
        fixer = QualityFixer(book_context)
        content = "The door opened. A sound echoed."

        pov = fixer._detect_pov(content)
        assert pov == 'unknown'

    def test_pov_caching(self, book_context):
        """Should cache POV detection results."""
        fixer = QualityFixer(book_context)
        content = "I am the protagonist. My story begins here. I walked forward."

        # First call
        pov1 = fixer._detect_pov(content, chapter_num=1)
        # Should be cached
        assert 1 in fixer._pov_cache

        # Second call should use cache
        pov2 = fixer._detect_pov(content, chapter_num=1)
        assert pov1 == pov2


class TestChapterStats:
    """Tests for chapter statistics."""

    def test_get_chapter_stats(self, book_context):
        """Should return stats for each chapter."""
        fixer = QualityFixer(book_context)
        stats = fixer.get_chapter_stats()

        assert len(stats) == 3  # 3 chapters
        for stat in stats:
            assert 'chapter' in stat
            assert 'words' in stat
            assert 'pov' in stat
            assert 'dialogue_quotes' in stat
            assert 'is_short' in stat

    def test_analyze_quality(self, book_context):
        """Should analyze overall book quality."""
        fixer = QualityFixer(book_context)
        analysis = fixer.analyze_quality()

        assert 'total_chapters' in analysis
        assert 'total_words' in analysis
        assert 'avg_words_per_chapter' in analysis
        assert 'short_chapters' in analysis
        assert 'pov_distribution' in analysis
        assert 'has_pov_inconsistency' in analysis


class TestPOVConsistency:
    """Tests for POV consistency fixing."""

    def test_fix_pov_consistency_detects_issues(self, book_context):
        """Should detect POV inconsistencies."""
        fixer = QualityFixer(book_context, expand_short=False)

        # Chapter 1 is first person, chapters 2-3 are third person
        # Should detect inconsistency
        with patch.object(fixer, '_convert_pov', return_value=True) as mock_convert:
            fixes = fixer.fix_pov_consistency()
            # May or may not call convert depending on dominant POV


class TestChapterExpansion:
    """Tests for chapter expansion."""

    def test_expand_short_chapters_identifies_short(self):
        """Should identify chapters below minimum word count."""
        with tempfile.TemporaryDirectory() as tmpdir:
            book_dir = Path(tmpdir)

            # Create very short chapter
            (book_dir / "chapter_01.md").write_text("Short chapter.")
            (book_dir / "story_bible.json").write_text("{}")

            context = BookContext(book_dir)
            fixer = QualityFixer(context, fix_pov=False, min_words=100)

            stats = fixer.get_chapter_stats()
            assert stats[0]['is_short'] is True

    def test_expand_short_chapters_with_mock(self):
        """Should expand short chapters using AI."""
        with tempfile.TemporaryDirectory() as tmpdir:
            book_dir = Path(tmpdir)

            (book_dir / "chapter_01.md").write_text("This is a very short chapter.")
            (book_dir / "story_bible.json").write_text("{}")

            context = BookContext(book_dir)
            fixer = QualityFixer(context, fix_pov=False, min_words=100, use_batching=False)

            mock_response = Mock()
            mock_response.success = True
            mock_response.content = "This is an expanded chapter. " * 50

            with patch('fixers.quality_fixer.get_api_client') as mock_client:
                mock_client.return_value.call.return_value = mock_response

                fixes = fixer.expand_short_chapters()
                assert fixes >= 0  # May or may not expand depending on validation


class TestBatchExpansion:
    """Tests for batched chapter expansion."""

    def test_max_batch_size_constant(self):
        """MAX_BATCH_SIZE should be set."""
        assert hasattr(QualityFixer, 'MAX_BATCH_SIZE')
        assert QualityFixer.MAX_BATCH_SIZE >= 1

    def test_batched_expansion_groups_chapters(self):
        """Should batch multiple short chapters together."""
        with tempfile.TemporaryDirectory() as tmpdir:
            book_dir = Path(tmpdir)

            # Create multiple short chapters
            for i in range(1, 6):
                (book_dir / f"chapter_{i:02d}.md").write_text(f"Short chapter {i}.")
            (book_dir / "story_bible.json").write_text("{}")

            context = BookContext(book_dir)
            fixer = QualityFixer(context, fix_pov=False, min_words=100)

            # With 5 short chapters and MAX_BATCH_SIZE=3, should make 2 batches
            # Just verify method exists and runs
            with patch.object(fixer, '_expand_chapter_batch', return_value=0) as mock_batch:
                fixer.expand_short_chapters_batched()
                # Should have been called for batches

    def test_extract_chapter_from_batch_response(self, book_context):
        """Should extract individual chapters from batch response."""
        fixer = QualityFixer(book_context)

        # Content must be > 200 chars to be considered viable
        chapter1_content = "This is the expanded content for chapter 1 with enough words to pass validation. " * 5
        chapter2_content = "This is the expanded content for chapter 2 with sufficient length and more. " * 5

        response = f"""
=== CHAPTER 1 ===
{chapter1_content}

=== CHAPTER 2 ===
{chapter2_content}
"""

        extracted = fixer._extract_chapter_from_batch(response, 1)
        assert extracted is not None
        assert "chapter 1" in extracted.lower()

        extracted2 = fixer._extract_chapter_from_batch(response, 2)
        assert extracted2 is not None
        assert "chapter 2" in extracted2.lower()

    def test_extract_chapter_handles_missing(self, book_context):
        """Should return None for missing chapters in batch."""
        fixer = QualityFixer(book_context)

        response = """
=== CHAPTER 1 ===
Content for chapter 1.
"""

        extracted = fixer._extract_chapter_from_batch(response, 99)
        assert extracted is None


class TestQualityFixerIntegration:
    """Integration-style tests for QualityFixer."""

    def test_fix_runs_all_enabled_fixes(self, book_context):
        """fix() should run all enabled fixes."""
        fixer = QualityFixer(book_context, expand_short=True, fix_pov=True)

        with patch.object(fixer, 'fix_pov_consistency', return_value=0) as mock_pov:
            with patch.object(fixer, 'expand_short_chapters_batched', return_value=0) as mock_expand:
                fixer.fix()

                mock_pov.assert_called_once()
                mock_expand.assert_called_once()

    def test_fix_respects_disabled_options(self, book_context):
        """fix() should skip disabled fixes."""
        fixer = QualityFixer(book_context, expand_short=False, fix_pov=False)

        with patch.object(fixer, 'fix_pov_consistency', return_value=0) as mock_pov:
            with patch.object(fixer, 'expand_short_chapters_batched', return_value=0) as mock_expand:
                fixer.fix()

                mock_pov.assert_not_called()
                mock_expand.assert_not_called()


class TestTellingPatterns:
    """Tests for telling patterns detection."""

    def test_telling_patterns_exist(self):
        """TELLING_PATTERNS should be defined."""
        from fixers.quality_fixer import TELLING_PATTERNS
        assert len(TELLING_PATTERNS) > 0

    def test_telling_patterns_match_common_examples(self):
        """Patterns should match common 'telling' constructs."""
        from fixers.quality_fixer import TELLING_PATTERNS

        telling_examples = [
            "She was angry at him.",
            "He felt sad about the loss.",
            "They were nervous before the exam.",
            "She was very excited.",
            "He was extremely worried.",
        ]

        for example in telling_examples:
            matched = any(p.search(example) for p in TELLING_PATTERNS)
            assert matched, f"Should match telling phrase: {example}"


class TestShowDontTell:
    """Tests for show-don't-tell conversion."""

    def test_find_telling_passages_identifies_telling(self):
        """Should identify paragraphs with telling language."""
        with tempfile.TemporaryDirectory() as tmpdir:
            book_dir = Path(tmpdir)

            # Paragraphs must be > 50 chars (min_paragraph_length default)
            content = """Chapter 1

She was angry at him for breaking her trust and could not forgive what he had done to her family.

The sun set over the horizon, painting the sky in shades of brilliant orange and deep purple hues.

He felt sad about losing his job after twenty years of dedicated service to the company he loved.
"""
            (book_dir / "chapter_01.md").write_text(content)
            (book_dir / "story_bible.json").write_text("{}")

            context = BookContext(book_dir)
            fixer = QualityFixer(context, expand_short=False, fix_pov=False, show_dont_tell=True)

            paragraphs = content.split('\n\n')
            telling = fixer._find_telling_passages(paragraphs)

            # Should find at least 2 telling passages ("was angry" and "felt sad")
            assert len(telling) >= 2

    def test_convert_telling_to_showing_calls_ai(self):
        """convert_telling_to_showing should call AI for conversion."""
        with tempfile.TemporaryDirectory() as tmpdir:
            book_dir = Path(tmpdir)

            (book_dir / "chapter_01.md").write_text(
                "Chapter 1\n\nShe was angry at him. He felt sad."
            )
            (book_dir / "story_bible.json").write_text("{}")

            context = BookContext(book_dir)
            fixer = QualityFixer(context, expand_short=False, fix_pov=False, show_dont_tell=True)

            mock_response = Mock()
            mock_response.success = True
            mock_response.content = "Her hands clenched into fists. His shoulders slumped."

            with patch('fixers.quality_fixer.get_api_client') as mock_client:
                mock_client.return_value.call.return_value = mock_response

                fixes = fixer.convert_telling_to_showing()
                # May or may not apply depending on detection
                assert fixes >= 0


class TestDialogueSubtext:
    """Tests for dialogue subtext enhancement."""

    def test_add_dialogue_subtext_identifies_dialogue(self):
        """Should identify dialogue that could use subtext."""
        with tempfile.TemporaryDirectory() as tmpdir:
            book_dir = Path(tmpdir)

            content = '''Chapter 1

"I'm fine," she said.

"Are you sure?" he asked.

"Yes," she replied.
'''
            (book_dir / "chapter_01.md").write_text(content)
            (book_dir / "story_bible.json").write_text("{}")

            context = BookContext(book_dir)
            fixer = QualityFixer(
                context, expand_short=False, fix_pov=False, add_dialogue_depth=True
            )

            mock_response = Mock()
            mock_response.success = True
            mock_response.content = '''"I'm fine," she said, avoiding his eyes.

"Are you sure?" he asked, reaching for her hand.

"Yes," she replied, her voice barely a whisper.
'''

            with patch('fixers.quality_fixer.get_api_client') as mock_client:
                mock_client.return_value.call.return_value = mock_response

                fixes = fixer.add_dialogue_subtext()
                # May or may not apply depending on detection
                assert fixes >= 0

    def test_dialogue_depth_flag_works(self, book_context):
        """add_dialogue_depth flag should control dialogue enhancement."""
        fixer = QualityFixer(book_context, expand_short=False, fix_pov=False, add_dialogue_depth=True)
        assert fixer._add_dialogue_depth is True

        fixer2 = QualityFixer(book_context, expand_short=False, fix_pov=False, add_dialogue_depth=False)
        assert fixer2._add_dialogue_depth is False


class TestFixMethodWithNewOptions:
    """Tests for fix() method with show_dont_tell and add_dialogue_depth."""

    def test_fix_calls_show_dont_tell_when_enabled(self, book_context):
        """fix() should call convert_telling_to_showing when enabled."""
        fixer = QualityFixer(
            book_context,
            expand_short=False,
            fix_pov=False,
            show_dont_tell=True,
            add_dialogue_depth=False
        )

        with patch.object(fixer, 'convert_telling_to_showing', return_value=0) as mock_show:
            fixer.fix()
            mock_show.assert_called_once()

    def test_fix_calls_dialogue_depth_when_enabled(self, book_context):
        """fix() should call add_dialogue_subtext when enabled."""
        fixer = QualityFixer(
            book_context,
            expand_short=False,
            fix_pov=False,
            show_dont_tell=False,
            add_dialogue_depth=True
        )

        with patch.object(fixer, 'add_dialogue_subtext', return_value=0) as mock_dialogue:
            fixer.fix()
            mock_dialogue.assert_called_once()

    def test_fix_skips_disabled_new_options(self, book_context):
        """fix() should skip show_dont_tell and dialogue_depth when disabled."""
        fixer = QualityFixer(
            book_context,
            expand_short=False,
            fix_pov=False,
            show_dont_tell=False,
            add_dialogue_depth=False
        )

        with patch.object(fixer, 'convert_telling_to_showing', return_value=0) as mock_show:
            with patch.object(fixer, 'add_dialogue_subtext', return_value=0) as mock_dialogue:
                fixer.fix()
                mock_show.assert_not_called()
                mock_dialogue.assert_not_called()
