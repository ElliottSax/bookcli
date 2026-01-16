#!/usr/bin/env python3
"""
Book Fixer - Automatic Quality Improvement Pipeline
====================================================

Fixes:
1. Character name inconsistencies
2. Setting/location name inconsistencies
3. Plot holes and continuity errors
4. POV/tense inconsistencies
5. Low-quality or short chapters
6. Doubled names, placeholders, LLM artifacts

Uses centralized lib/ modules for API calls, logging, and configuration.
"""

import json
import re
import time
import argparse
from pathlib import Path
from typing import Optional, Dict, List, Tuple, Set
from dataclasses import dataclass
from collections import Counter

# Centralized lib modules
from lib.logging_config import setup_logging, get_logger
from lib.config import get_config
from lib.api_client import call_llm, get_api_client, extract_json_from_response

# Initialize
setup_logging()
logger = get_logger(__name__)
config = get_config()

# Paths from config
FICTION_DIR = config.paths.fiction_dir

# Quality thresholds from config
MIN_CHAPTER_WORDS = config.quality.min_chapter_words
TARGET_CHAPTER_WORDS = config.quality.target_chapter_words
MAX_REPEATED_PHRASES = config.quality.max_repeated_phrases

# Pre-compiled regex patterns for LLM instruction artifacts (compiled once at module load)
LLM_ARTIFACTS = [
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
PLACEHOLDER_PATTERNS = [
    (re.compile(r'\s*\(primary\s+setting\)', re.IGNORECASE), ''),
    (re.compile(r'\s*\(primary\s+location\)', re.IGNORECASE), ''),
    (re.compile(r'\s*\(protagonist\)', re.IGNORECASE), ''),
    (re.compile(r'\s*\(antagonist\)', re.IGNORECASE), ''),
    (re.compile(r'\s*\(setting\)', re.IGNORECASE), ''),
    (re.compile(r'\s*\(location\)', re.IGNORECASE), ''),
    (re.compile(r'The City \(Exterior\)', re.IGNORECASE), 'the city'),
    (re.compile(r'\s*\([^)]*(?:primary|setting|location|protagonist|antagonist)[^)]*\)', re.IGNORECASE), ''),
]

# Pre-compiled overused/repetitive AI phrase patterns
REPETITIVE_PHRASE_PATTERNS = [
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

# Pre-compiled common patterns used multiple times
POV_FIRST_PERSON = re.compile(r'\b(I|me|my|mine|myself)\b', re.IGNORECASE)
POV_SECOND_PERSON = re.compile(r'\b(you|your|yours|yourself)\b', re.IGNORECASE)
POV_THIRD_PERSON = re.compile(r'\b(he|she|they|his|her|their|him|them)\b', re.IGNORECASE)
TRIPLE_WORD = re.compile(r'\b(\w+)\s+\1\s+\1\b', re.IGNORECASE)
DOUBLE_WORD = re.compile(r'\b(\w+)\s+\1\b', re.IGNORECASE)
DOUBLE_PHRASE = re.compile(r'\b(\w+\s+\w+)\s+\1\b', re.IGNORECASE)
MULTIPLE_SPACES = re.compile(r'[ \t]+')
SPACE_BEFORE_PUNCT = re.compile(r' +([.,;:!?])')
LEADING_SPACES = re.compile(r'\n +')
TRAILING_SPACES = re.compile(r' +\n')
MULTIPLE_NEWLINES = re.compile(r'\n{3,}')


@dataclass
class BookIssue:
    """Represents an issue found in a book."""
    issue_type: str  # name_inconsistency, pov_shift, short_chapter, etc.
    description: str
    affected_chapters: List[int]
    fix_applied: bool = False


@dataclass
class NameMapping:
    """Maps variant names to canonical name."""
    canonical: str
    variants: List[str]
    role: str  # protagonist, antagonist, supporting


class BookFixer:
    """Fixes quality issues in a book."""

    def __init__(self, book_dir: Path):
        self.book_dir = book_dir
        self.story_bible = self._load_story_bible()
        self.chapters = self._load_chapters()
        self.issues: List[BookIssue] = []
        self.name_mappings: List[NameMapping] = []
        self.fixes_applied = 0

    def _load_story_bible(self) -> Optional[Dict]:
        """Load story bible if exists."""
        path = self.book_dir / "story_bible.json"
        if path.exists():
            try:
                return json.loads(path.read_text())
            except json.JSONDecodeError:
                return None
        return None

    def _load_chapters(self) -> Dict[int, str]:
        """Load all chapters."""
        chapters = {}
        for chapter_file in sorted(self.book_dir.glob("chapter_*.md")):
            try:
                num = int(chapter_file.stem.split("_")[1])
                chapters[num] = chapter_file.read_text()
            except (ValueError, IndexError):
                continue
        return chapters

    def _save_chapter(self, chapter_num: int, content: str):
        """Save a chapter."""
        path = self.book_dir / f"chapter_{chapter_num:02d}.md"
        path.write_text(content)

    def _get_all_text(self) -> str:
        """Get all chapter text combined."""
        return "\n\n".join(self.chapters.values())

    def _get_setting_name(self) -> str:
        """Get primary setting name from story bible."""
        if not self.story_bible:
            return "the estate"

        setting = self.story_bible.get("setting", {})
        if isinstance(setting, str):
            return setting

        if isinstance(setting, dict):
            for key in ["primary_location", "name", "location"]:
                value = setting.get(key)
                if isinstance(value, str) and value:
                    return value

        return "the estate"

    # =========================================================================
    # ANALYSIS PHASE
    # =========================================================================

    def analyze_name_inconsistencies(self) -> List[NameMapping]:
        """Use AI to find all name variations and determine canonical names."""
        all_text = self._get_all_text()[:15000]

        prompt = f"""Analyze this book text and find ALL character name inconsistencies.

BOOK TEXT:
{all_text}

For each character that appears with multiple name variations, determine:
1. The CANONICAL name (most appropriate/frequent)
2. All VARIANT names used
3. The character's role

Return as JSON array:
[
  {{
    "canonical": "Dr. Victor Blackwood",
    "variants": ["Dr. Blackthorn", "Victor Blackthorn", "Professor Blackwood"],
    "role": "antagonist"
  }}
]

IMPORTANT:
- Only include characters with ACTUAL inconsistencies (multiple different names)
- Don't include nicknames that are intentionally used
- Focus on ERRORS like completely different surnames or first names
- Return ONLY valid JSON array, no other text"""

        result = call_llm(prompt, max_tokens=2000)
        mappings = []

        if result:
            data = extract_json_from_response(result)
            if data and isinstance(data, list):
                for item in data:
                    if isinstance(item, dict) and "canonical" in item and "variants" in item:
                        mappings.append(NameMapping(
                            canonical=item["canonical"],
                            variants=item.get("variants", []),
                            role=item.get("role", "unknown")
                        ))

        self.name_mappings = mappings
        return mappings

    def analyze_pov_consistency(self) -> str:
        """Detect the dominant POV and find inconsistencies."""
        pov_counts = {"first": 0, "second": 0, "third": 0}

        for content in self.chapters.values():
            first_person = len(POV_FIRST_PERSON.findall(content))
            second_person = len(POV_SECOND_PERSON.findall(content))
            third_person = len(POV_THIRD_PERSON.findall(content))

            if first_person > second_person and first_person > third_person:
                pov_counts["first"] += 1
            elif second_person > first_person and second_person > third_person:
                pov_counts["second"] += 1
            else:
                pov_counts["third"] += 1

        dominant_pov = max(pov_counts, key=pov_counts.get)

        # Find chapters with wrong POV
        for num, content in self.chapters.items():
            first_person = len(re.findall(r'\b(I|me|my|mine|myself)\b', content, re.IGNORECASE))
            second_person = len(re.findall(r'\b(you|your|yours|yourself)\b', content, re.IGNORECASE))
            third_person = len(re.findall(r'\b(he|she|they|his|her|their|him|them)\b', content, re.IGNORECASE))

            chapter_pov = "third"
            if first_person > second_person and first_person > third_person:
                chapter_pov = "first"
            elif second_person > first_person and second_person > third_person:
                chapter_pov = "second"

            if chapter_pov != dominant_pov:
                self.issues.append(BookIssue(
                    issue_type="pov_inconsistency",
                    description=f"Chapter {num} uses {chapter_pov}-person but book is {dominant_pov}-person",
                    affected_chapters=[num]
                ))

        return dominant_pov

    def analyze_chapter_quality(self) -> List[int]:
        """Find chapters that are too short or low quality."""
        short_chapters = []

        for num, content in self.chapters.items():
            word_count = len(content.split())
            if word_count < MIN_CHAPTER_WORDS:
                short_chapters.append(num)
                self.issues.append(BookIssue(
                    issue_type="short_chapter",
                    description=f"Chapter {num} only has {word_count} words (min: {MIN_CHAPTER_WORDS})",
                    affected_chapters=[num]
                ))

        return short_chapters

    # =========================================================================
    # FIX PHASE
    # =========================================================================

    def fix_name_inconsistencies(self) -> int:
        """Replace all variant names with canonical names."""
        if not self.name_mappings:
            self.analyze_name_inconsistencies()

        fixes = 0

        for mapping in self.name_mappings:
            logger.info(f"  Fixing: {mapping.variants} → {mapping.canonical}")

            for num, content in self.chapters.items():
                original = content
                for variant in mapping.variants:
                    if variant != mapping.canonical:
                        pattern = r'\b' + re.escape(variant) + r'\b'
                        content = re.sub(pattern, mapping.canonical, content)

                if content != original:
                    self.chapters[num] = content
                    self._save_chapter(num, content)
                    fixes += 1

        self.fixes_applied += fixes
        return fixes

    def fix_pov_inconsistency(self, target_pov: str) -> int:
        """Rewrite chapters with wrong POV."""
        fixes = 0

        for issue in self.issues:
            if issue.issue_type == "pov_inconsistency" and not issue.fix_applied:
                for chapter_num in issue.affected_chapters:
                    if self._rewrite_chapter_pov(chapter_num, target_pov):
                        fixes += 1
                issue.fix_applied = True

        self.fixes_applied += fixes
        return fixes

    def _rewrite_chapter_pov(self, chapter_num: int, target_pov: str) -> bool:
        """Rewrite a chapter to fix POV."""
        if chapter_num not in self.chapters:
            return False

        content = self.chapters[chapter_num]
        protagonist = self._get_protagonist_name()

        prompt = f"""Rewrite this chapter to use consistent {target_pov}-person POV.

PROTAGONIST: {protagonist}

ORIGINAL CHAPTER:
{content[:8000]}

REQUIREMENTS:
1. Convert ALL narration to {target_pov}-person POV
2. Keep the same plot events and dialogue
3. Maintain the same chapter length
4. Keep character voices distinct
5. Preserve emotional beats

Write the COMPLETE rewritten chapter:"""

        result = call_llm(prompt, max_tokens=8000)
        if result and len(result) > len(content) * 0.7:
            self.chapters[chapter_num] = result
            self._save_chapter(chapter_num, result)
            return True

        return False

    def _get_protagonist_name(self) -> str:
        """Get protagonist name from story bible."""
        if not self.story_bible:
            return "the protagonist"

        chars = self.story_bible.get("characters", [])
        if isinstance(chars, list) and chars:
            if isinstance(chars[0], dict):
                return chars[0].get("name", "the protagonist")
        elif isinstance(chars, dict):
            protag = chars.get("protagonist", {})
            if isinstance(protag, dict):
                return protag.get("name", "the protagonist")

        return "the protagonist"

    def expand_short_chapters(self) -> int:
        """Expand chapters that are too short."""
        fixes = 0

        for issue in self.issues:
            if issue.issue_type == "short_chapter" and not issue.fix_applied:
                for chapter_num in issue.affected_chapters:
                    if self._expand_chapter(chapter_num):
                        fixes += 1
                issue.fix_applied = True

        self.fixes_applied += fixes
        return fixes

    def _expand_chapter(self, chapter_num: int) -> bool:
        """Expand a short chapter."""
        if chapter_num not in self.chapters:
            return False

        content = self.chapters[chapter_num]
        current_words = len(content.split())

        if current_words >= MIN_CHAPTER_WORDS:
            return True

        context = self._get_story_context()
        prev_summary = ""
        if chapter_num > 1 and (chapter_num - 1) in self.chapters:
            prev_content = self.chapters[chapter_num - 1]
            prev_summary = f"\nPREVIOUS CHAPTER ENDING:\n{prev_content[-1500:]}"

        prompt = f"""Expand this chapter to at least {MIN_CHAPTER_WORDS} words while maintaining quality.

{context}
{prev_summary}

CURRENT CHAPTER ({current_words} words):
{content}

EXPANSION REQUIREMENTS:
1. Add MORE sensory details (sight, sound, smell, touch, taste)
2. Expand dialogue with natural back-and-forth
3. Add internal thoughts/reactions
4. Describe settings and atmosphere more richly
5. Show emotions through physical actions
6. Add tension and pacing beats
7. Target: {MIN_CHAPTER_WORDS}+ words

Write the COMPLETE expanded chapter:"""

        result = call_llm(prompt, max_tokens=8000)
        if result:
            new_words = len(result.split())
            if new_words > current_words * 1.3:
                self.chapters[chapter_num] = result
                self._save_chapter(chapter_num, result)
                logger.info(f"    Expanded chapter {chapter_num}: {current_words} → {new_words} words")
                return True

        return False

    def _get_story_context(self) -> str:
        """Get story context from story bible."""
        if not self.story_bible:
            return ""

        protagonist = self._get_protagonist_name()
        narrative_voice = self.story_bible.get('narrative_voice', {})
        tone = narrative_voice.get('tone', 'engaging') if isinstance(narrative_voice, dict) else 'engaging'

        return f"""
GENRE: {self.story_bible.get('genre', 'fiction')}
PROTAGONIST: {protagonist}
TONE: {tone}
"""

    def fix_setting_inconsistencies(self) -> int:
        """Fix setting/location name inconsistencies using AI."""
        if not self.story_bible:
            return 0

        all_text = self._get_all_text()[:10000]

        prompt = f"""Analyze this book text and find setting/location name inconsistencies.

BOOK TEXT:
{all_text}

STORY BIBLE SETTING:
{json.dumps(self.story_bible.get('setting', {}), indent=2)}

Find locations mentioned inconsistently and return a JSON object mapping variant names to canonical names:
{{"variant1": "canonical1", "variant2": "canonical1"}}

Return ONLY the JSON object."""

        result = call_llm(prompt, max_tokens=1000)
        if not result:
            return 0

        mappings = extract_json_from_response(result)
        if not mappings or not isinstance(mappings, dict):
            return 0

        fixes = 0
        for variant, canonical in mappings.items():
            if isinstance(variant, str) and isinstance(canonical, str) and variant != canonical:
                for num, content in self.chapters.items():
                    original = content
                    pattern = r'\b' + re.escape(variant) + r'\b'
                    content = re.sub(pattern, canonical, content)

                    if content != original:
                        self.chapters[num] = content
                        self._save_chapter(num, content)
                        fixes += 1

        self.fixes_applied += fixes
        return fixes

    # =========================================================================
    # TEXT FIXES (No AI calls)
    # =========================================================================

    def fix_doubled_names(self) -> int:
        """Fix doubled/tripled names like 'Maya Chen Chen Chen'."""
        fixes = 0

        for num, content in self.chapters.items():
            original = content

            for _ in range(3):  # Multiple passes
                prev_content = content
                content = TRIPLE_WORD.sub(r'\1', content)
                content = DOUBLE_WORD.sub(r'\1', content)
                content = DOUBLE_PHRASE.sub(r'\1', content)
                if content == prev_content:
                    break

            if content != original:
                self.chapters[num] = content
                self._save_chapter(num, content)
                fixes += 1
                logger.info(f"    Fixed doubled names in chapter {num}")

        self.fixes_applied += fixes
        return fixes

    def fix_unprocessed_placeholders(self) -> int:
        """Fix unprocessed placeholder text like '(primary setting)'."""
        fixes = 0
        location_name = self._get_setting_name()

        for num, content in self.chapters.items():
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
                self.chapters[num] = content
                self._save_chapter(num, content)
                fixes += 1
                logger.info(f"    Fixed placeholders in chapter {num}")

        self.fixes_applied += fixes
        return fixes

    def fix_llm_artifacts(self) -> int:
        """Remove LLM instruction artifacts that leaked into the output."""
        fixes = 0

        for num, content in self.chapters.items():
            original = content

            # Use pre-compiled patterns
            for pattern in LLM_ARTIFACTS:
                content = pattern.sub('', content)

            content = MULTIPLE_NEWLINES.sub('\n\n', content)

            if content != original:
                self.chapters[num] = content
                self._save_chapter(num, content)
                fixes += 1
                logger.info(f"    Removed LLM artifacts from chapter {num}")

        self.fixes_applied += fixes
        return fixes

    def fix_duplicate_content(self) -> int:
        """Fix chapters that have duplicated content."""
        fixes = 0

        for num, content in self.chapters.items():
            original = content

            # Check for half-chapter duplication
            half_point = len(content) // 2
            first_half = content[:half_point].strip()

            if len(first_half) > 500:
                second_half = content[half_point:]
                check = first_half[:200]
                if check in second_half:
                    dup_start = second_half.find(check)
                    if dup_start != -1:
                        content = content[:half_point + dup_start].strip()
                        self.chapters[num] = content
                        self._save_chapter(num, content)
                        fixes += 1
                        logger.info(f"    Removed duplicated content from chapter {num}")
                        continue

            # Check for paragraph-level duplicates
            paragraphs = content.split('\n\n')
            if len(paragraphs) > 5:
                seen: Set[str] = set()
                unique_paragraphs = []

                for para in paragraphs:
                    normalized = ' '.join(para.split()).lower()
                    if len(normalized) > 100:
                        if normalized not in seen:
                            seen.add(normalized)
                            unique_paragraphs.append(para)
                    else:
                        unique_paragraphs.append(para)

                if len(unique_paragraphs) < len(paragraphs):
                    content = '\n\n'.join(unique_paragraphs)
                    self.chapters[num] = content
                    self._save_chapter(num, content)
                    fixes += 1
                    logger.info(f"    Removed duplicate paragraphs from chapter {num}")

        self.fixes_applied += fixes
        return fixes

    def fix_repetitive_phrases(self) -> int:
        """Detect and log repetitive AI phrases (detection only, no auto-fix)."""
        detections = 0

        for num, content in self.chapters.items():
            for pattern in REPETITIVE_PHRASE_PATTERNS:
                matches = pattern.findall(content)
                if len(matches) > MAX_REPEATED_PHRASES:
                    detections += 1

        if detections > 0:
            logger.info(f"    Detected {detections} repetitive phrase patterns")

        return 0  # No auto-fix for this

    # =========================================================================
    # MAIN FIX PIPELINE
    # =========================================================================

    def run_full_fix(self) -> Dict:
        """Run all fixes in order."""
        results = {
            "book": self.book_dir.name,
            "issues_found": 0,
            "fixes_applied": 0,
            "details": []
        }

        # Text fixes first (no AI calls)
        doubled_fixes = self.fix_doubled_names()
        if doubled_fixes:
            results["details"].append(f"Fixed doubled names in {doubled_fixes} chapters")

        placeholder_fixes = self.fix_unprocessed_placeholders()
        if placeholder_fixes:
            results["details"].append(f"Fixed placeholders in {placeholder_fixes} chapters")

        artifact_fixes = self.fix_llm_artifacts()
        if artifact_fixes:
            results["details"].append(f"Removed LLM artifacts from {artifact_fixes} chapters")

        duplicate_fixes = self.fix_duplicate_content()
        if duplicate_fixes:
            results["details"].append(f"Fixed duplicates in {duplicate_fixes} chapters")

        # Analysis
        self.analyze_name_inconsistencies()
        dominant_pov = self.analyze_pov_consistency()
        self.analyze_chapter_quality()

        results["issues_found"] = len(self.issues)

        # AI-based fixes
        if self.name_mappings:
            name_fixes = self.fix_name_inconsistencies()
            if name_fixes:
                results["details"].append(f"Fixed name inconsistencies in {name_fixes} chapters")

        pov_fixes = self.fix_pov_inconsistency(dominant_pov)
        if pov_fixes:
            results["details"].append(f"Fixed POV in {pov_fixes} chapters")

        chapter_fixes = self.expand_short_chapters()
        if chapter_fixes:
            results["details"].append(f"Expanded {chapter_fixes} short chapters")

        setting_fixes = self.fix_setting_inconsistencies()
        if setting_fixes:
            results["details"].append(f"Fixed setting inconsistencies in {setting_fixes} chapters")

        results["fixes_applied"] = self.fixes_applied

        # Mark as fixed in story bible
        if self.story_bible and results["fixes_applied"] > 0:
            self.story_bible["quality_fixed"] = True
            self.story_bible["fixes_applied"] = results["fixes_applied"]
            bible_path = self.book_dir / "story_bible.json"
            bible_path.write_text(json.dumps(self.story_bible, indent=2))

        return results


def get_books_needing_fixes() -> List[Path]:
    """Get all books that haven't been fixed yet."""
    books = []

    for book_dir in FICTION_DIR.iterdir():
        if not book_dir.is_dir():
            continue

        story_bible_path = book_dir / "story_bible.json"
        if not story_bible_path.exists():
            continue

        try:
            bible = json.loads(story_bible_path.read_text())
            if bible.get("quality_fixed"):
                continue
        except json.JSONDecodeError:
            continue

        chapters = list(book_dir.glob("chapter_*.md"))
        if len(chapters) >= 3:
            books.append(book_dir)

    return books


def get_all_books() -> List[Path]:
    """Get all books with chapters (regardless of fix status)."""
    books = []

    for book_dir in FICTION_DIR.iterdir():
        if not book_dir.is_dir():
            continue

        chapters = list(book_dir.glob("chapter_*.md"))
        if len(chapters) >= 3:
            books.append(book_dir)

    return books


def main():
    """Main fix loop."""
    parser = argparse.ArgumentParser(description="Book Fixer - Automatic Quality Improvement")
    parser.add_argument("--rerun", action="store_true",
                       help="Re-run fixes on all books, including already-fixed ones")
    parser.add_argument("--book", type=str,
                       help="Fix a specific book by name")
    parser.add_argument("--limit", type=int, default=None,
                       help="Limit number of books to process")
    parser.add_argument("--text-only", action="store_true",
                       help="Only run text fixes (doubled names, placeholders, etc.) - no AI calls")
    args = parser.parse_args()

    logger.info("=" * 60)
    logger.info("BOOK FIXER - Automatic Quality Improvement")
    logger.info("=" * 60)

    if args.book:
        book_path = FICTION_DIR / args.book
        if not book_path.exists():
            matches = [d for d in FICTION_DIR.iterdir() if args.book.lower() in d.name.lower()]
            if matches:
                book_path = matches[0]
            else:
                logger.error(f"Book not found: {args.book}")
                return
        books = [book_path]
    elif args.rerun:
        books = get_all_books()
    else:
        books = get_books_needing_fixes()

    if args.limit:
        books = books[:args.limit]

    logger.info(f"Found {len(books)} books to process")

    if not books:
        logger.info("No books to process!")
        return

    total_issues = 0
    total_fixes = 0

    for i, book_dir in enumerate(books, 1):
        logger.info(f"\n[{i}/{len(books)}] {book_dir.name}")

        try:
            fixer = BookFixer(book_dir)

            if args.text_only:
                results = {
                    "book": book_dir.name,
                    "issues_found": 0,
                    "fixes_applied": 0,
                    "details": []
                }

                doubled_fixes = fixer.fix_doubled_names()
                if doubled_fixes:
                    results["details"].append(f"Fixed doubled names in {doubled_fixes} chapters")
                    results["issues_found"] += doubled_fixes

                placeholder_fixes = fixer.fix_unprocessed_placeholders()
                if placeholder_fixes:
                    results["details"].append(f"Fixed placeholders in {placeholder_fixes} chapters")
                    results["issues_found"] += placeholder_fixes

                artifact_fixes = fixer.fix_llm_artifacts()
                if artifact_fixes:
                    results["details"].append(f"Removed LLM artifacts from {artifact_fixes} chapters")
                    results["issues_found"] += artifact_fixes

                duplicate_fixes = fixer.fix_duplicate_content()
                if duplicate_fixes:
                    results["details"].append(f"Fixed duplicates in {duplicate_fixes} chapters")
                    results["issues_found"] += duplicate_fixes

                results["fixes_applied"] = fixer.fixes_applied
            else:
                results = fixer.run_full_fix()

            total_issues += results["issues_found"]
            total_fixes += results["fixes_applied"]

            if results["details"]:
                for detail in results["details"]:
                    logger.info(f"    ✓ {detail}")

        except Exception as e:
            logger.error(f"  Error fixing {book_dir.name}: {e}")
            import traceback
            traceback.print_exc()

        time.sleep(1 if args.text_only else config.pipeline.delay_between_books)

    logger.info("\n" + "=" * 60)
    logger.info("FIX COMPLETE")
    logger.info(f"  Total issues found: {total_issues}")
    logger.info(f"  Total fixes applied: {total_fixes}")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
