"""
Quality Fixer - Handles narrative quality issues.

Fixes:
- POV consistency
- Short chapters (expansion)
- Dialogue depth
- Show don't tell
- AI-isms removal
- Sensory details enhancement
- Tension improvement
- Chapter endings

Optimizations:
- Caches POV detection per chapter
- Batches multiple quality improvements into single API calls when possible
- Pre-compiles POV detection regex patterns
- Skips chapters that don't need improvement (sensory/tension checks)
"""

import re
from typing import Optional, List, Tuple, Dict

from .base import BaseFixer, BookContext
from lib.logging_config import get_logger
from lib.api_client import get_api_client
from lib.config import get_config

# Import patterns from consolidated pattern library
from lib.patterns import (
    POV_FIRST,
    POV_SECOND,
    POV_THIRD,
    TELLING_PATTERNS,
    AI_ISM_WORDS as AI_PATTERNS,
    SENSORY_WORDS,
    TENSION_WORDS,
)

logger = get_logger(__name__)


class QualityFixer(BaseFixer):
    """
    Fixes narrative quality issues using AI assistance.

    Handles:
    - POV consistency across chapters
    - Expanding short chapters
    - Improving dialogue depth
    - Converting telling to showing

    Optimizations:
    - Caches POV detection to avoid recomputing
    - Batches short chapter expansions when multiple need fixing
    - Uses pre-compiled regex patterns
    """

    # Maximum chapters to batch in a single expansion call
    MAX_BATCH_SIZE = 3

    def __init__(
        self,
        context: BookContext,
        expand_short: bool = True,
        fix_pov: bool = True,
        fix_ai_isms: bool = True,
        add_sensory: bool = False,
        add_tension: bool = False,
        improve_dialogue: bool = False,
        improve_endings: bool = False,
        show_dont_tell: bool = False,
        add_dialogue_depth: bool = False,
        min_words: Optional[int] = None,
        use_batching: bool = True,
    ):
        """
        Initialize quality fixer.

        Args:
            context: Book context
            expand_short: Whether to expand short chapters
            fix_pov: Whether to fix POV inconsistencies
            fix_ai_isms: Whether to fix AI-isms
            add_sensory: Whether to add sensory details
            add_tension: Whether to add tension to flat scenes
            improve_dialogue: Whether to improve dialogue
            improve_endings: Whether to improve chapter endings
            show_dont_tell: Whether to convert telling to showing
            add_dialogue_depth: Whether to add subtext/depth to dialogue
            min_words: Minimum words per chapter (uses config default if None)
            use_batching: Whether to batch multiple expansions (default True)
        """
        super().__init__(context)
        self.expand_short = expand_short
        self.fix_pov = fix_pov
        self._fix_ai_isms = fix_ai_isms
        self.add_sensory = add_sensory
        self._add_tension = add_tension
        self._improve_dialogue = improve_dialogue
        self._improve_endings = improve_endings
        self._show_dont_tell = show_dont_tell
        self._add_dialogue_depth = add_dialogue_depth
        self.use_batching = use_batching

        config = get_config().quality
        self.min_words = min_words or config.min_chapter_words
        self.target_words = config.target_chapter_words
        self.min_paragraph_length = getattr(config, 'min_paragraph_length', 50)
        self.min_dialogue_quotes = getattr(config, 'min_dialogue_quotes', 4)

        # Cache for POV detection
        self._pov_cache: Dict[int, str] = {}

    def describe(self) -> str:
        parts = []
        if self.fix_pov:
            parts.append("POV consistency")
        if self.expand_short:
            parts.append("expand short chapters")
        if self._fix_ai_isms:
            parts.append("AI-isms")
        if self.add_sensory:
            parts.append("sensory details")
        if self._add_tension:
            parts.append("tension")
        if self._improve_dialogue:
            parts.append("dialogue")
        if self._improve_endings:
            parts.append("endings")
        if self._show_dont_tell:
            parts.append("show don't tell")
        if self._add_dialogue_depth:
            parts.append("dialogue depth")
        return f"Fix: {', '.join(parts)}" if parts else "Quality fixer (no fixes enabled)"

    def fix(self) -> int:
        """Apply quality fixes."""
        total = 0

        # Basic mechanical fixes first
        if self._fix_ai_isms:
            total += self.fix_ai_isms()

        # Show don't tell conversion (before other enhancements)
        if self._show_dont_tell:
            total += self.convert_telling_to_showing()

        # Enhancement passes
        if self.add_sensory:
            total += self.add_sensory_details()

        if self._improve_dialogue:
            total += self.improve_dialogue()

        if self._add_dialogue_depth:
            total += self.add_dialogue_subtext()

        if self._add_tension:
            total += self.add_tension_to_scenes()

        # Structural fixes
        if self.fix_pov:
            total += self.fix_pov_consistency()

        if self.expand_short:
            if self.use_batching:
                total += self.expand_short_chapters_batched()
            else:
                total += self.expand_short_chapters()

        # Endings last
        if self._improve_endings:
            total += self.improve_endings()

        return total

    def fix_pov_consistency(self) -> int:
        """
        Fix POV inconsistencies across chapters.

        Detects the dominant POV and fixes chapters that deviate.

        Returns:
            Number of chapters fixed
        """
        # Detect POV for each chapter
        chapter_povs = {}
        for num, content in self.context.chapters.items():
            pov = self._detect_pov(content)
            chapter_povs[num] = pov

        # Find dominant POV
        pov_counts = {}
        for pov in chapter_povs.values():
            pov_counts[pov] = pov_counts.get(pov, 0) + 1

        if not pov_counts:
            return 0

        dominant_pov = max(pov_counts, key=pov_counts.get)

        # Fix chapters with wrong POV
        fixes = 0
        for num, pov in chapter_povs.items():
            if pov != dominant_pov and pov != 'unknown':
                fixed = self._convert_pov(num, pov, dominant_pov)
                if fixed:
                    fixes += 1

        return fixes

    def _detect_pov(self, content: str, chapter_num: Optional[int] = None) -> str:
        """
        Detect the POV of a chapter.

        Uses pre-compiled patterns and caches results for efficiency.

        Args:
            content: Chapter content
            chapter_num: Optional chapter number for caching

        Returns:
            'first', 'second', 'third', or 'unknown'
        """
        # Check cache first
        if chapter_num is not None and chapter_num in self._pov_cache:
            return self._pov_cache[chapter_num]

        # Count POV indicators using pre-compiled patterns
        first_person = len(POV_FIRST.findall(content))
        second_person = len(POV_SECOND.findall(content))
        third_person = len(POV_THIRD.findall(content))

        # Normalize by content length
        # Use 33% threshold (lowered from 40%) to catch more POV inconsistencies
        total = first_person + second_person + third_person
        if total < 10:
            result = 'unknown'
        elif first_person / total > 0.33:
            result = 'first'
        elif second_person / total > 0.33:
            result = 'second'
        elif third_person / total > 0.33:
            result = 'third'
        else:
            result = 'unknown'

        # Cache result
        if chapter_num is not None:
            self._pov_cache[chapter_num] = result

        return result

    def _convert_pov(self, chapter_num: int, from_pov: str, to_pov: str) -> bool:
        """
        Convert a chapter from one POV to another.

        Args:
            chapter_num: Chapter number
            from_pov: Current POV
            to_pov: Target POV

        Returns:
            True if conversion was successful
        """
        content = self.context.chapters[chapter_num]

        prompt = f"""Convert this chapter from {from_pov} person to {to_pov} person POV.

Maintain the same story events, dialogue, and descriptions.
Only change the pronouns and perspective.

Current chapter:
{content[:8000]}

Return ONLY the converted chapter text, no explanation."""

        client = get_api_client()
        response = client.call(prompt, max_tokens=6000, temperature=0.3)

        if not response.success or not response.content:
            logger.warning(f"POV conversion failed for chapter {chapter_num}")
            return False

        # Validate conversion
        new_pov = self._detect_pov(response.content)
        if new_pov != to_pov:
            logger.warning(f"POV conversion produced wrong POV: {new_pov} instead of {to_pov}")
            return False

        self._save_chapter(chapter_num, response.content)
        self._log_fix(chapter_num, f"Converted POV from {from_pov} to {to_pov}")
        return True

    def expand_short_chapters(self) -> int:
        """
        Expand chapters that are too short.

        Returns:
            Number of chapters expanded
        """
        fixes = 0

        for num, content in self.context.chapters.items():
            word_count = len(content.split())

            if word_count < self.min_words:
                expanded = self._expand_chapter(num, content, word_count)
                if expanded:
                    fixes += 1

        return fixes

    def _expand_chapter(self, chapter_num: int, content: str, current_words: int) -> bool:
        """
        Expand a short chapter.

        Args:
            chapter_num: Chapter number
            content: Current chapter content
            current_words: Current word count

        Returns:
            True if expansion was successful
        """
        # Get context from adjacent chapters
        prev_content = self.context.chapters.get(chapter_num - 1, "")[-2000:]
        next_content = self.context.chapters.get(chapter_num + 1, "")[:2000]

        prompt = f"""This chapter is too short ({current_words} words, target: {self.target_words}).
Expand it while maintaining consistency with the story.

Previous chapter context (ending):
{prev_content}

Current chapter to expand:
{content}

Next chapter context (beginning):
{next_content}

Instructions:
1. Add sensory details and atmosphere
2. Expand character thoughts and reactions
3. Add natural dialogue where appropriate
4. Maintain the same plot points and pacing
5. Target word count: {self.target_words}

Return ONLY the expanded chapter text."""

        client = get_api_client()
        response = client.call(prompt, max_tokens=6000, temperature=0.7)

        if not response.success or not response.content:
            logger.warning(f"Chapter expansion failed for chapter {chapter_num}")
            return False

        new_word_count = len(response.content.split())

        # Validate expansion
        if new_word_count < current_words:
            logger.warning(f"Expansion made chapter shorter: {new_word_count} < {current_words}")
            return False

        if new_word_count < self.min_words:
            logger.warning(f"Expansion still too short: {new_word_count} < {self.min_words}")
            # Still save if it's an improvement
            if new_word_count > current_words * 1.2:
                self._save_chapter(chapter_num, response.content)
                self._log_fix(chapter_num, f"Partially expanded ({current_words} -> {new_word_count} words)")
                return True
            return False

        self._save_chapter(chapter_num, response.content)
        self._log_fix(chapter_num, f"Expanded ({current_words} -> {new_word_count} words)")
        return True

    def get_chapter_stats(self) -> List[dict]:
        """
        Get statistics for each chapter.

        Returns:
            List of dicts with chapter stats
        """
        stats = []

        for num, content in sorted(self.context.chapters.items()):
            word_count = len(content.split())
            pov = self._detect_pov(content)
            dialogue_count = content.count('"')

            stats.append({
                'chapter': num,
                'words': word_count,
                'pov': pov,
                'dialogue_quotes': dialogue_count,
                'is_short': word_count < self.min_words,
            })

        return stats

    def analyze_quality(self) -> dict:
        """
        Analyze overall quality of the book.

        Returns:
            Dict with quality metrics
        """
        stats = self.get_chapter_stats()

        total_words = sum(s['words'] for s in stats)
        avg_words = total_words / len(stats) if stats else 0
        short_chapters = sum(1 for s in stats if s['is_short'])

        pov_distribution = {}
        for s in stats:
            pov = s['pov']
            pov_distribution[pov] = pov_distribution.get(pov, 0) + 1

        return {
            'total_chapters': len(stats),
            'total_words': total_words,
            'avg_words_per_chapter': round(avg_words),
            'short_chapters': short_chapters,
            'pov_distribution': pov_distribution,
            'has_pov_inconsistency': len(pov_distribution) > 2,
        }

    # ==================== AI-ism Fixes ====================

    def fix_ai_isms(self) -> int:
        """
        Remove AI-isms and improve natural flow in chapters.

        Detects patterns like "Moreover", "Furthermore", "delve", etc.
        and uses LLM to rewrite affected passages.

        Returns:
            Number of chapters fixed
        """
        fixes = 0

        for num, content in self.context.chapters.items():
            # Check if chapter has AI-isms
            text_lower = content.lower()
            if not any(p.lower() in text_lower for p in AI_PATTERNS):
                continue

            # Process in chunks if chapter is very long (>6000 chars)
            # to stay within token limits while fixing ALL content
            if len(content) > 6000:
                # Split into ~5000 char chunks with overlap
                fixed_content = self._fix_ai_isms_chunked(content)
                if fixed_content:
                    self._save_chapter(num, fixed_content)
                    self._log_fix(num, "Removed AI-isms")
                    fixes += 1
                continue

            prompt = f"""Remove AI-isms and improve this text. Replace:
- "Moreover/Furthermore/Additionally" with natural transitions
- "delve/tapestry/vibrant/multifaceted" with simpler words
- "testament to/myriad/plethora/cacophony" with plain language
- "symphony of/weight of/etched in/shrouded in" with clearer phrasing
- Any robotic or unnatural phrasing

Keep the same meaning and length. Return ONLY the improved text.

{content}"""

            client = get_api_client()
            response = client.call(prompt, max_tokens=6000, temperature=0.5)

            if response.success and response.content:
                # Validate response isn't truncated (must be at least 70% of original length)
                original_words = len(content.split())
                new_words = len(response.content.split())

                if new_words < original_words * 0.7:
                    logger.warning(
                        f"Chapter {num}: AI-ism fix response too short "
                        f"({new_words} vs {original_words} words), skipping"
                    )
                    continue

                # Check for LLM response prefixes that leaked through
                bad_prefixes = ["here is", "here's the", "i've ", "i have "]
                first_line = response.content.split('\n')[0].lower().strip()
                if any(first_line.startswith(p) for p in bad_prefixes):
                    logger.warning(f"Chapter {num}: AI-ism fix has LLM prefix, skipping")
                    continue

                self._save_chapter(num, response.content)
                self._log_fix(num, "Removed AI-isms")
                fixes += 1

        return fixes

    def _fix_ai_isms_chunked(self, content: str, chunk_size: int = 5000) -> Optional[str]:
        """
        Fix AI-isms in long content by processing in chunks.

        Args:
            content: Full chapter content
            chunk_size: Maximum characters per chunk

        Returns:
            Fixed content or None if processing failed
        """
        # Split into paragraphs to avoid breaking mid-sentence
        paragraphs = content.split('\n\n')
        chunks = []
        current_chunk = []
        current_size = 0

        for para in paragraphs:
            para_size = len(para) + 2  # +2 for \n\n
            if current_size + para_size > chunk_size and current_chunk:
                chunks.append('\n\n'.join(current_chunk))
                current_chunk = [para]
                current_size = para_size
            else:
                current_chunk.append(para)
                current_size += para_size

        if current_chunk:
            chunks.append('\n\n'.join(current_chunk))

        # Process each chunk
        fixed_chunks = []
        client = get_api_client()

        for chunk in chunks:
            # Skip chunks without AI-isms
            chunk_lower = chunk.lower()
            if not any(p.lower() in chunk_lower for p in AI_PATTERNS):
                fixed_chunks.append(chunk)
                continue

            prompt = f"""Remove AI-isms and improve this text. Replace:
- "Moreover/Furthermore/Additionally" with natural transitions
- "delve/tapestry/vibrant/multifaceted" with simpler words
- "testament to/myriad/plethora/cacophony" with plain language
- "symphony of/weight of/etched in/shrouded in" with clearer phrasing
- Any robotic or unnatural phrasing

Keep the same meaning and length. Return ONLY the improved text.

{chunk}"""

            response = client.call(prompt, max_tokens=6000, temperature=0.5)

            if response.success and response.content:
                # Validate response isn't truncated
                original_words = len(chunk.split())
                new_words = len(response.content.split())

                if new_words < original_words * 0.7:
                    logger.warning(f"AI-ism chunk fix too short ({new_words} vs {original_words}), keeping original")
                    fixed_chunks.append(chunk)
                    continue

                # Check for LLM response prefixes
                bad_prefixes = ["here is", "here's the", "i've ", "i have "]
                first_line = response.content.split('\n')[0].lower().strip()
                if any(first_line.startswith(p) for p in bad_prefixes):
                    logger.warning("AI-ism chunk has LLM prefix, keeping original")
                    fixed_chunks.append(chunk)
                    continue

                fixed_chunks.append(response.content)
            else:
                fixed_chunks.append(chunk)  # Keep original on failure

        return '\n\n'.join(fixed_chunks)

    # ==================== Sensory Details ====================

    def add_sensory_details(self) -> int:
        """
        Add sensory details to prose that lacks them.

        Checks for presence of sensory words and adds details via LLM
        for chapters that need enhancement.

        Returns:
            Number of chapters enhanced
        """
        fixes = 0

        for num, content in self.context.chapters.items():
            # Skip if already has sensory details
            text_lower = content.lower()
            if any(w in text_lower for w in SENSORY_WORDS):
                continue

            prompt = f"""Add 2-3 sensory details to this passage. Include sight, sound, smell, or touch.
Keep the same meaning and approximate length. Return ONLY the improved text.

{content[:2000]}"""

            client = get_api_client()
            response = client.call(prompt, max_tokens=3000, temperature=0.6)

            if response.success and response.content:
                self._save_chapter(num, response.content)
                self._log_fix(num, "Added sensory details")
                fixes += 1

        return fixes

    # ==================== Dialogue Improvement ====================

    def improve_dialogue(self) -> int:
        """
        Make dialogue more distinctive and natural.

        Adds dialogue beats, character reactions, and distinctive voices.

        Returns:
            Number of chapters improved
        """
        fixes = 0

        for num, content in self.context.chapters.items():
            # Skip if minimal dialogue
            if content.count('"') < 4:
                continue

            prompt = f"""Improve the dialogue in this passage:
- Give each character a distinctive voice
- Add beats and reactions between dialogue
- Make conversations feel more natural

Keep the same plot points. Return ONLY the improved text.

{content[:3000]}"""

            client = get_api_client()
            response = client.call(prompt, max_tokens=4000, temperature=0.7)

            if response.success and response.content:
                self._save_chapter(num, response.content)
                self._log_fix(num, "Improved dialogue")
                fixes += 1

        return fixes

    # ==================== Tension Enhancement ====================

    def add_tension_to_scenes(self) -> int:
        """
        Add subtle tension to flat scenes.

        Detects chapters lacking tension and enhances them via LLM.

        Returns:
            Number of chapters enhanced
        """
        fixes = 0

        for num, content in self.context.chapters.items():
            # Skip if already has tension elements
            text_lower = content.lower()
            if any(w in text_lower for w in TENSION_WORDS):
                continue

            prompt = f"""Add subtle tension to this passage through:
- Internal worry or doubt
- Environmental unease
- Time pressure
- Interpersonal friction

Keep the same plot. Return ONLY the improved text.

{content[:2000]}"""

            client = get_api_client()
            response = client.call(prompt, max_tokens=3000, temperature=0.7)

            if response.success and response.content:
                self._save_chapter(num, response.content)
                self._log_fix(num, "Added tension")
                fixes += 1

        return fixes

    # ==================== Ending Improvement ====================

    def improve_endings(self) -> int:
        """
        Strengthen chapter endings with hooks or satisfying conclusions.

        Improves chapter endings to create stronger hooks or,
        for the final chapter, a more satisfying conclusion.

        Returns:
            Number of chapters improved
        """
        fixes = 0
        chapters = sorted(self.context.chapters.items())
        total_chapters = len(chapters)

        for i, (num, content) in enumerate(chapters):
            words = content.split()
            if len(words) < 300:
                continue

            ending = ' '.join(words[-300:])
            beginning = ' '.join(words[:-300])

            is_final = (i == total_chapters - 1)

            if is_final:
                prompt = f"""Improve this final chapter ending to be more satisfying and emotionally resonant.
Give proper closure while leaving hope. Return ONLY the improved ending (about 300 words).

{ending}"""
            else:
                prompt = f"""Improve this chapter ending to create a stronger hook.
Add suspense, a revelation, or emotional cliff-hanger. Return ONLY the improved ending (about 300 words).

{ending}"""

            client = get_api_client()
            response = client.call(prompt, max_tokens=500, temperature=0.7)

            if response.success and response.content and len(response.content.split()) > 100:
                new_content = beginning + ' ' + response.content
                self._save_chapter(num, new_content)
                self._log_fix(num, "Improved ending" + (" (final)" if is_final else ""))
                fixes += 1

        return fixes

    # ==================== Show Don't Tell ====================

    def convert_telling_to_showing(self) -> int:
        """
        Convert "telling" passages to "showing".

        Detects patterns like "was angry", "felt nervous" and converts
        them to show emotions through actions, physical sensations,
        and dialogue.

        Returns:
            Number of passages converted
        """
        fixes = 0

        for num, content in self.context.chapters.items():
            paragraphs = content.split('\n\n')
            telling_paragraphs = self._find_telling_passages(paragraphs)

            if not telling_paragraphs:
                continue

            # Convert up to 3 telling passages per chapter
            for idx, para in telling_paragraphs[:3]:
                improved = self._convert_paragraph_to_showing(para)

                if improved:
                    paragraphs[idx] = improved
                    fixes += 1

            if fixes > 0:
                new_content = '\n\n'.join(paragraphs)
                self._save_chapter(num, new_content)
                self._log_fix(num, f"Converted {min(len(telling_paragraphs), 3)} telling passages")

        return fixes

    def _find_telling_passages(self, paragraphs: List[str]) -> List[Tuple[int, str]]:
        """
        Find paragraphs that "tell" instead of "show".

        Args:
            paragraphs: List of paragraph strings

        Returns:
            List of (index, paragraph) tuples for telling paragraphs
        """
        telling = []

        for i, para in enumerate(paragraphs):
            if len(para) < self.min_paragraph_length:
                continue

            for pattern in TELLING_PATTERNS:
                if pattern.search(para):
                    telling.append((i, para))
                    break

        return telling

    def _convert_paragraph_to_showing(self, para: str) -> Optional[str]:
        """
        Convert a telling paragraph to showing using LLM.

        Args:
            para: Paragraph text to convert

        Returns:
            Improved paragraph or None if conversion failed
        """
        prompt = f"""Convert this "telling" passage to "showing".
Instead of stating emotions directly, show them through:
- Physical sensations and body language
- Actions and dialogue
- Sensory details

Keep the same meaning. Return ONLY the improved passage.

{para}"""

        client = get_api_client()
        response = client.call(prompt, max_tokens=500, temperature=0.6)

        if response.success and response.content and len(response.content) > 50:
            return response.content

        return None

    # ==================== Dialogue Depth ====================

    def add_dialogue_subtext(self) -> int:
        """
        Add subtext and depth to dialogue.

        Enhances dialogue by adding:
        - What characters are really thinking vs saying
        - Meaningful pauses and reactions
        - Physical beats between lines
        - Unspoken tension or emotion

        Returns:
            Number of chapters improved
        """
        fixes = 0

        for num, content in self.context.chapters.items():
            # Skip if minimal dialogue
            if content.count('"') < self.min_dialogue_quotes:
                continue

            prompt = f"""Add subtext and depth to the dialogue in this passage.
- Add what characters are really thinking vs saying
- Include meaningful pauses and reactions
- Add physical beats between lines
- Show unspoken tension or emotion
Keep same plot. Return ONLY the improved text.

{content[:3500]}"""

            client = get_api_client()
            response = client.call(prompt, max_tokens=4000, temperature=0.7)

            if response.success and response.content and len(response.content) > 1000:
                self._save_chapter(num, response.content)
                self._log_fix(num, "Added dialogue depth/subtext")
                fixes += 1

        return fixes

    # ==================== Full Quality Pass ====================

    def run_full_quality_pass(self) -> Dict[str, int]:
        """
        Run all quality improvements on the book.

        This is a convenience method that enables all quality passes
        and returns detailed statistics.

        Returns:
            Dict with counts for each type of improvement
        """
        stats = {
            'ai_isms_fixed': 0,
            'show_dont_tell': 0,
            'sensory_added': 0,
            'dialogue_improved': 0,
            'dialogue_depth': 0,
            'tension_added': 0,
            'pov_fixed': 0,
            'chapters_expanded': 0,
            'endings_improved': 0,
        }

        stats['ai_isms_fixed'] = self.fix_ai_isms()
        stats['show_dont_tell'] = self.convert_telling_to_showing()
        stats['sensory_added'] = self.add_sensory_details()
        stats['dialogue_improved'] = self.improve_dialogue()
        stats['dialogue_depth'] = self.add_dialogue_subtext()
        stats['tension_added'] = self.add_tension_to_scenes()
        stats['pov_fixed'] = self.fix_pov_consistency()

        if self.use_batching:
            stats['chapters_expanded'] = self.expand_short_chapters_batched()
        else:
            stats['chapters_expanded'] = self.expand_short_chapters()

        stats['endings_improved'] = self.improve_endings()

        return stats

    def expand_short_chapters_batched(self) -> int:
        """
        Expand short chapters using batched API calls.

        Instead of one API call per chapter, batches multiple short chapters
        into a single call when they are consecutive or when there are many.

        Returns:
            Number of chapters expanded
        """
        # Find all short chapters
        short_chapters = []
        for num, content in self.context.chapters.items():
            word_count = self.context.get_word_count(num)
            if word_count < self.min_words:
                short_chapters.append((num, content, word_count))

        if not short_chapters:
            return 0

        logger.info(f"Found {len(short_chapters)} short chapters to expand")

        # If only 1-2 short chapters, use regular expansion
        if len(short_chapters) <= 2:
            fixes = 0
            for num, content, words in short_chapters:
                if self._expand_chapter(num, content, words):
                    fixes += 1
            return fixes

        # Batch expansion for 3+ short chapters
        fixes = 0

        # Process in batches
        for i in range(0, len(short_chapters), self.MAX_BATCH_SIZE):
            batch = short_chapters[i:i + self.MAX_BATCH_SIZE]
            batch_fixes = self._expand_chapter_batch(batch)
            fixes += batch_fixes

        return fixes

    def _expand_chapter_batch(self, chapters: List[Tuple[int, str, int]]) -> int:
        """
        Expand multiple chapters in a single API call.

        Args:
            chapters: List of (chapter_num, content, word_count) tuples

        Returns:
            Number of chapters successfully expanded
        """
        if not chapters:
            return 0

        # Build combined prompt
        chapter_sections = []
        for num, content, words in chapters:
            chapter_sections.append(f"""
=== CHAPTER {num} (Current: {words} words, Target: {self.target_words} words) ===
{content[:4000]}
{'...[truncated]...' if len(content) > 4000 else ''}
""")

        prompt = f"""Expand the following {len(chapters)} short chapters.
Each chapter needs to be expanded to approximately {self.target_words} words.

For each chapter:
1. Add sensory details and atmosphere
2. Expand character thoughts and reactions
3. Add natural dialogue where appropriate
4. Maintain the same plot points and pacing

{"".join(chapter_sections)}

Return each expanded chapter in this format:
=== CHAPTER [number] ===
[expanded chapter content]

Return ONLY the expanded chapters, no explanation."""

        client = get_api_client()
        # Use more tokens for batch (cap at 6000 for DeepSeek's 8192 limit with overhead)
        max_tokens = 4000 * len(chapters)
        response = client.call(prompt, max_tokens=min(max_tokens, 6000), temperature=0.7)

        if not response.success or not response.content:
            logger.warning("Batch expansion API call failed, falling back to individual expansion")
            # Fall back to individual expansion
            fixes = 0
            for num, content, words in chapters:
                if self._expand_chapter(num, content, words):
                    fixes += 1
            return fixes

        # Parse response and extract chapters
        fixes = 0
        for num, original_content, original_words in chapters:
            # Extract this chapter from response
            expanded = self._extract_chapter_from_batch(response.content, num)

            if expanded:
                new_words = len(expanded.split())

                # Validate expansion - require full min_words threshold (not 80%)
                if new_words >= original_words and new_words >= self.min_words:
                    self._save_chapter(num, expanded)
                    self._log_fix(num, f"Batch expanded ({original_words} -> {new_words} words)")
                    fixes += 1
                elif new_words >= original_words * 1.5 and new_words >= self.min_words * 0.9:
                    # Accept partial improvement
                    self._save_chapter(num, expanded)
                    self._log_fix(num, f"Partially batch expanded ({original_words} -> {new_words} words)")
                    fixes += 1
                else:
                    logger.warning(f"Chapter {num} batch expansion too short: {new_words} words")
            else:
                logger.warning(f"Could not extract chapter {num} from batch response")

        return fixes

    def _extract_chapter_from_batch(self, response: str, chapter_num: int) -> Optional[str]:
        """
        Extract a specific chapter from a batch expansion response.

        Args:
            response: Full API response
            chapter_num: Chapter number to extract

        Returns:
            Extracted chapter content or None
        """
        import re

        # Try to find chapter marker
        patterns = [
            rf'===\s*CHAPTER\s*{chapter_num}\s*===\s*(.*?)(?====\s*CHAPTER|\Z)',
            rf'CHAPTER\s*{chapter_num}[:\s]+(.*?)(?=CHAPTER\s*\d+|\Z)',
            rf'#{1,3}\s*Chapter\s*{chapter_num}\s*(.*?)(?=#{1,3}\s*Chapter|\Z)',
        ]

        for pattern in patterns:
            match = re.search(pattern, response, re.DOTALL | re.IGNORECASE)
            if match:
                content = match.group(1).strip()
                if len(content) > 200:  # Minimum viable chapter
                    return content

        return None
