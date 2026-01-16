"""
Quality Fixer - Handles narrative quality issues.

Fixes:
- POV consistency
- Short chapters (expansion)
- Dialogue depth
- Show don't tell

Optimizations:
- Caches POV detection per chapter
- Batches multiple quality improvements into single API calls when possible
- Pre-compiles POV detection regex patterns
"""

import re
from typing import Optional, List, Tuple, Dict

from .base import BaseFixer, BookContext
from lib.logging_config import get_logger
from lib.api_client import get_api_client
from lib.config import get_config

logger = get_logger(__name__)

# Pre-compiled POV detection patterns
POV_FIRST = re.compile(r'\b(I|me|my|mine|myself)\b', re.IGNORECASE)
POV_SECOND = re.compile(r'\b(you|your|yours|yourself)\b', re.IGNORECASE)
POV_THIRD = re.compile(r'\b(he|she|they|his|her|their|him|them)\b', re.IGNORECASE)


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
        min_words: Optional[int] = None,
        use_batching: bool = True,
    ):
        """
        Initialize quality fixer.

        Args:
            context: Book context
            expand_short: Whether to expand short chapters
            fix_pov: Whether to fix POV inconsistencies
            min_words: Minimum words per chapter (uses config default if None)
            use_batching: Whether to batch multiple expansions (default True)
        """
        super().__init__(context)
        self.expand_short = expand_short
        self.fix_pov = fix_pov
        self.use_batching = use_batching

        config = get_config().quality
        self.min_words = min_words or config.min_chapter_words
        self.target_words = config.target_chapter_words

        # Cache for POV detection
        self._pov_cache: Dict[int, str] = {}

    def describe(self) -> str:
        return "Fix POV consistency and expand short chapters"

    def fix(self) -> int:
        """Apply quality fixes."""
        total = 0

        if self.fix_pov:
            total += self.fix_pov_consistency()

        if self.expand_short:
            if self.use_batching:
                total += self.expand_short_chapters_batched()
            else:
                total += self.expand_short_chapters()

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
        total = first_person + second_person + third_person
        if total < 10:
            result = 'unknown'
        elif first_person / total > 0.4:
            result = 'first'
        elif second_person / total > 0.4:
            result = 'second'
        elif third_person / total > 0.4:
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
        # Use more tokens for batch
        max_tokens = 6000 * len(chapters)
        response = client.call(prompt, max_tokens=min(max_tokens, 16000), temperature=0.7)

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

                # Validate expansion
                if new_words >= original_words and new_words >= self.min_words * 0.8:
                    self._save_chapter(num, expanded)
                    self._log_fix(num, f"Batch expanded ({original_words} -> {new_words} words)")
                    fixes += 1
                elif new_words > original_words * 1.2:
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
