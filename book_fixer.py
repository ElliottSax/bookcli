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

Runs automatically after story bible generation.
"""

import os
import sys
import json
import re
import time
import logging
from pathlib import Path
from typing import Optional, Dict, List, Tuple, Set
from dataclasses import dataclass
from collections import Counter

import requests

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler('/mnt/e/projects/bookcli/book_fixer.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# API Keys - from environment variables (set via GitHub Secrets or local .env)
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
OPENROUTER_KEY = os.environ.get("OPENROUTER_KEY", "")
TOGETHER_KEY = os.environ.get("TOGETHER_KEY", "")
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")
CEREBRAS_API_KEY = os.environ.get("CEREBRAS_API_KEY", "")
CLOUDFLARE_TOKEN = os.environ.get("CLOUDFLARE_API_TOKEN", "")
CLOUDFLARE_ACCOUNT = os.environ.get("CLOUDFLARE_ACCOUNT_ID", "")
FIREWORKS_API_KEY = os.environ.get("FIREWORKS_API_KEY", "")

FICTION_DIR = Path("/mnt/e/projects/bookcli/output/fiction")

# Quality thresholds
MIN_CHAPTER_WORDS = 2500
MIN_BOOK_WORDS = 30000
MAX_REPEATED_PHRASES = 3


def call_deepseek(prompt: str, max_tokens: int = 8000) -> Optional[str]:
    """Call DeepSeek API."""
    try:
        response = requests.post(
            "https://api.deepseek.com/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": "deepseek-chat",
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": max_tokens,
                "temperature": 0.7,
            },
            timeout=300
        )
        if response.status_code == 200:
            return response.json()["choices"][0]["message"]["content"]
    except Exception as e:
        logger.error(f"DeepSeek error: {e}")
    return None


def call_groq(prompt: str, max_tokens: int = 8000) -> Optional[str]:
    """Call Groq API (free tier)."""
    try:
        response = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {GROQ_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": "llama-3.3-70b-versatile",
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": max_tokens,
                "temperature": 0.7,
            },
            timeout=300
        )
        if response.status_code == 200:
            return response.json()["choices"][0]["message"]["content"]
        elif response.status_code == 429:
            logger.warning("Groq rate limited")
    except Exception as e:
        logger.error(f"Groq error: {e}")
    return None


def call_openrouter(prompt: str, max_tokens: int = 8000) -> Optional[str]:
    """Call OpenRouter API (free models)."""
    try:
        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {OPENROUTER_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": "meta-llama/llama-3.2-3b-instruct:free",
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": min(max_tokens, 4000),  # Free tier limit
                "temperature": 0.7,
            },
            timeout=300
        )
        if response.status_code == 200:
            return response.json()["choices"][0]["message"]["content"]
        elif response.status_code == 429:
            logger.warning("OpenRouter rate limited")
    except Exception as e:
        logger.error(f"OpenRouter error: {e}")
    return None


def call_together(prompt: str, max_tokens: int = 8000) -> Optional[str]:
    """Call Together AI API."""
    try:
        response = requests.post(
            "https://api.together.xyz/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {TOGETHER_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": "meta-llama/Llama-3.3-70B-Instruct-Turbo",
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": max_tokens,
                "temperature": 0.7,
            },
            timeout=300
        )
        if response.status_code == 200:
            return response.json()["choices"][0]["message"]["content"]
        elif response.status_code == 429:
            logger.warning("Together rate limited")
    except Exception as e:
        logger.error(f"Together error: {e}")
    return None


def call_github(prompt: str, max_tokens: int = 8000) -> Optional[str]:
    """Call GitHub Models API (free)."""
    try:
        response = requests.post(
            "https://models.inference.ai.azure.com/chat/completions",
            headers={
                "Authorization": f"Bearer {GITHUB_TOKEN}",
                "Content-Type": "application/json"
            },
            json={
                "model": "gpt-4o-mini",
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": min(max_tokens, 4000),
                "temperature": 0.7,
            },
            timeout=300
        )
        if response.status_code == 200:
            return response.json()["choices"][0]["message"]["content"]
        elif response.status_code == 429:
            logger.warning("GitHub Models rate limited")
    except Exception as e:
        logger.error(f"GitHub Models error: {e}")
    return None


def call_cerebras(prompt: str, max_tokens: int = 8000) -> Optional[str]:
    """Call Cerebras API (very fast inference)."""
    try:
        response = requests.post(
            "https://api.cerebras.ai/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {CEREBRAS_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": "llama3.1-8b",
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": min(max_tokens, 8000),
                "temperature": 0.7,
            },
            timeout=300
        )
        if response.status_code == 200:
            return response.json()["choices"][0]["message"]["content"]
        elif response.status_code == 429:
            logger.warning("Cerebras rate limited")
    except Exception as e:
        logger.error(f"Cerebras error: {e}")
    return None


def call_cloudflare(prompt: str, max_tokens: int = 8000) -> Optional[str]:
    """Call Cloudflare Workers AI."""
    try:
        response = requests.post(
            f"https://api.cloudflare.com/client/v4/accounts/{CLOUDFLARE_ACCOUNT}/ai/run/@cf/meta/llama-3.1-8b-instruct",
            headers={
                "Authorization": f"Bearer {CLOUDFLARE_TOKEN}",
                "Content-Type": "application/json"
            },
            json={
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": min(max_tokens, 4000),
            },
            timeout=300
        )
        if response.status_code == 200:
            data = response.json()
            if data.get("success") and data.get("result", {}).get("response"):
                return data["result"]["response"]
        elif response.status_code == 429:
            logger.warning("Cloudflare rate limited")
    except Exception as e:
        logger.error(f"Cloudflare error: {e}")
    return None


def call_fireworks(prompt: str, max_tokens: int = 8000) -> Optional[str]:
    """Call Fireworks AI API."""
    try:
        response = requests.post(
            "https://api.fireworks.ai/inference/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {FIREWORKS_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": "accounts/fireworks/models/llama-v3p3-70b-instruct",
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": min(max_tokens, 8000),
                "temperature": 0.7,
            },
            timeout=300
        )
        if response.status_code == 200:
            return response.json()["choices"][0]["message"]["content"]
        elif response.status_code == 429:
            logger.warning("Fireworks rate limited")
    except Exception as e:
        logger.error(f"Fireworks error: {e}")
    return None


# Round-robin index for load balancing
_api_index = 0

def call_api(prompt: str, max_tokens: int = 8000) -> Optional[str]:
    """Call API with round-robin across all free APIs."""
    global _api_index

    # All free APIs in order (8 providers now)
    apis = [
        ("Groq", call_groq),
        ("Cerebras", call_cerebras),
        ("Together", call_together),
        ("Fireworks", call_fireworks),
        ("GitHub", call_github),
        ("Cloudflare", call_cloudflare),
        ("OpenRouter", call_openrouter),
        ("DeepSeek", call_deepseek),
    ]

    # Try starting from current index, round-robin
    for i in range(len(apis)):
        idx = (_api_index + i) % len(apis)
        name, func = apis[idx]
        result = func(prompt, max_tokens)
        if result:
            logger.info(f"Success via {name}")
            _api_index = (idx + 1) % len(apis)  # Next call starts with next API
            return result

    logger.error("All APIs failed")
    return None


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

    # =========================================================================
    # ANALYSIS PHASE
    # =========================================================================

    def analyze_name_inconsistencies(self) -> List[NameMapping]:
        """Use AI to find all name variations and determine canonical names."""

        all_text = self._get_all_text()[:15000]  # First 15k chars

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
  }},
  {{
    "canonical": "Eleanor Hargrove",
    "variants": ["Ellie Hargrove", "Eleanor Hart", "Elle"],
    "role": "protagonist"
  }}
]

IMPORTANT:
- Only include characters with ACTUAL inconsistencies (multiple different names)
- Don't include nicknames that are intentionally used (like "Ellie" for "Eleanor" if consistent)
- Focus on ERRORS like completely different surnames or first names
- Return ONLY valid JSON array, no other text"""

        result = call_api(prompt, 2000)
        mappings = []

        if result:
            try:
                if "```json" in result:
                    result = result.split("```json")[1].split("```")[0]
                elif "```" in result:
                    result = result.split("```")[1].split("```")[0]

                data = json.loads(result)
                for item in data:
                    if item.get("variants"):
                        mappings.append(NameMapping(
                            canonical=item["canonical"],
                            variants=item["variants"],
                            role=item.get("role", "supporting")
                        ))
            except json.JSONDecodeError:
                pass

        self.name_mappings = mappings
        return mappings

    def analyze_pov_consistency(self) -> Optional[str]:
        """Check if POV is consistent across chapters."""
        pov_by_chapter = {}

        for num, content in self.chapters.items():
            # Count first-person pronouns
            first_person = len(re.findall(r'\bI\b(?!\')|\bmy\b|\bme\b|\bmyself\b', content, re.IGNORECASE))
            # Count third-person
            third_person = len(re.findall(r'\b(he|she|they)\b', content, re.IGNORECASE))

            total = first_person + third_person
            if total > 0:
                first_ratio = first_person / total
                if first_ratio > 0.6:
                    pov_by_chapter[num] = "first"
                elif first_ratio < 0.2:
                    pov_by_chapter[num] = "third"
                else:
                    pov_by_chapter[num] = "mixed"

        # Check for inconsistency
        povs = list(set(pov_by_chapter.values()))
        if len(povs) > 1 and "mixed" not in povs:
            # Real inconsistency
            dominant = Counter(pov_by_chapter.values()).most_common(1)[0][0]
            self.issues.append(BookIssue(
                issue_type="pov_inconsistency",
                description=f"POV shifts detected. Dominant: {dominant}",
                affected_chapters=[n for n, p in pov_by_chapter.items() if p != dominant]
            ))
            return dominant

        return None

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

    def analyze_setting_consistency(self) -> List[Tuple[str, str]]:
        """Find setting/location name inconsistencies."""
        # This uses the story bible's key_fixes_needed if available
        if self.story_bible and "key_fixes_needed" in self.story_bible:
            fixes = self.story_bible["key_fixes_needed"]
            for fix in fixes:
                if "setting" in fix.lower() or "location" in fix.lower() or "place" in fix.lower():
                    self.issues.append(BookIssue(
                        issue_type="setting_inconsistency",
                        description=fix,
                        affected_chapters=list(self.chapters.keys())
                    ))
        return []

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
                        # Use word boundaries to avoid partial matches
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

        # Get story bible context
        protagonist = "the protagonist"
        if self.story_bible:
            chars = self.story_bible.get("characters", [])
            if isinstance(chars, list) and chars:
                # Characters is a list of character dicts
                protagonist = chars[0].get("name", "the protagonist") if isinstance(chars[0], dict) else "the protagonist"
            elif isinstance(chars, dict):
                # Characters is a dict with roles as keys
                protag = chars.get("protagonist", {})
                protagonist = protag.get("name", "the protagonist") if isinstance(protag, dict) else "the protagonist"

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

        result = call_api(prompt, 8000)
        if result and len(result) > len(content) * 0.7:  # At least 70% of original length
            self.chapters[chapter_num] = result
            self._save_chapter(chapter_num, result)
            return True

        return False

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
            return True  # Already long enough

        # Get context from story bible
        context = ""
        if self.story_bible:
            chars = self.story_bible.get('characters', [])
            if isinstance(chars, list) and chars and isinstance(chars[0], dict):
                protagonist_name = chars[0].get('name', 'Unknown')
            elif isinstance(chars, dict):
                protagonist_name = chars.get('protagonist', {}).get('name', 'Unknown') if isinstance(chars.get('protagonist'), dict) else 'Unknown'
            else:
                protagonist_name = 'Unknown'

            narrative_voice = self.story_bible.get('narrative_voice', {})
            tone = narrative_voice.get('tone', 'engaging') if isinstance(narrative_voice, dict) else 'engaging'

            context = f"""
GENRE: {self.story_bible.get('genre', 'fiction')}
PROTAGONIST: {protagonist_name}
TONE: {tone}
"""

        # Get previous chapter summary for context
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

        result = call_api(prompt, 8000)
        if result:
            new_words = len(result.split())
            if new_words > current_words * 1.3:  # At least 30% longer
                self.chapters[chapter_num] = result
                self._save_chapter(chapter_num, result)
                logger.info(f"    Expanded chapter {chapter_num}: {current_words} → {new_words} words")
                return True

        return False

    def fix_setting_inconsistencies(self) -> int:
        """Fix setting/location name inconsistencies using AI."""
        fixes = 0

        # Get canonical setting names from story bible
        if not self.story_bible:
            return 0

        setting = self.story_bible.get("setting", {})
        if not setting:
            return 0

        # Build list of canonical names
        canonical_settings = []
        if "primary_location" in setting:
            canonical_settings.append(setting["primary_location"])
        if "university_name" in setting:
            canonical_settings.append(setting["university_name"])

        # Use AI to find and fix inconsistencies
        all_text_sample = self._get_all_text()[:10000]

        prompt = f"""Find and list all location/setting name variations in this text that should be standardized.

CANONICAL SETTINGS FROM STORY BIBLE:
{json.dumps(setting, indent=2)}

TEXT SAMPLE:
{all_text_sample}

Return a JSON object mapping variant names to canonical names:
{{
  "variant_name": "canonical_name",
  "St. Mary's Cathedral": "Cathedral of the Sacred Heart",
  "New Haven": "Eldridge"
}}

Only include ACTUAL inconsistencies. Return empty {{}} if none found."""

        result = call_api(prompt, 1000)
        if result:
            try:
                if "```json" in result:
                    result = result.split("```json")[1].split("```")[0]
                elif "```" in result:
                    result = result.split("```")[1].split("```")[0]

                mappings = json.loads(result)

                for variant, canonical in mappings.items():
                    if variant and canonical and variant != canonical:
                        for num, content in self.chapters.items():
                            pattern = r'\b' + re.escape(variant) + r'\b'
                            new_content = re.sub(pattern, canonical, content)
                            if new_content != content:
                                self.chapters[num] = new_content
                                self._save_chapter(num, new_content)
                                fixes += 1

            except json.JSONDecodeError:
                pass

        self.fixes_applied += fixes
        return fixes

    # =========================================================================
    # MAIN PIPELINE
    # =========================================================================

    def run_full_fix(self) -> Dict:
        """Run the complete fix pipeline."""
        logger.info(f"Fixing: {self.book_dir.name}")

        results = {
            "book": self.book_dir.name,
            "issues_found": 0,
            "fixes_applied": 0,
            "details": []
        }

        # 1. Analyze and fix name inconsistencies
        logger.info("  [1/4] Analyzing name inconsistencies...")
        name_mappings = self.analyze_name_inconsistencies()
        if name_mappings:
            logger.info(f"    Found {len(name_mappings)} name inconsistencies")
            name_fixes = self.fix_name_inconsistencies()
            results["details"].append(f"Fixed {name_fixes} name inconsistencies")
            results["issues_found"] += len(name_mappings)

        # 2. Analyze and fix POV inconsistencies
        logger.info("  [2/4] Analyzing POV consistency...")
        dominant_pov = self.analyze_pov_consistency()
        if dominant_pov:
            pov_issues = [i for i in self.issues if i.issue_type == "pov_inconsistency"]
            if pov_issues:
                logger.info(f"    Found POV issues in {len(pov_issues[0].affected_chapters)} chapters")
                pov_fixes = self.fix_pov_inconsistency(dominant_pov)
                results["details"].append(f"Fixed {pov_fixes} POV inconsistencies")
                results["issues_found"] += len(pov_issues[0].affected_chapters)

        # 3. Analyze and fix setting inconsistencies
        logger.info("  [3/4] Analyzing setting consistency...")
        self.analyze_setting_consistency()
        setting_fixes = self.fix_setting_inconsistencies()
        if setting_fixes:
            results["details"].append(f"Fixed {setting_fixes} setting inconsistencies")
            results["issues_found"] += setting_fixes

        # 4. Expand short chapters
        logger.info("  [4/4] Checking chapter lengths...")
        short_chapters = self.analyze_chapter_quality()
        if short_chapters:
            logger.info(f"    Found {len(short_chapters)} short chapters")
            expansion_fixes = self.expand_short_chapters()
            results["details"].append(f"Expanded {expansion_fixes} short chapters")
            results["issues_found"] += len(short_chapters)

        results["fixes_applied"] = self.fixes_applied

        # Save fix report
        report_path = self.book_dir / "fix_report.json"
        report_path.write_text(json.dumps(results, indent=2))

        # Update story bible to mark as fixed
        if self.story_bible:
            self.story_bible["quality_fixed"] = True
            self.story_bible["fixes_applied"] = results["details"]
            (self.book_dir / "story_bible.json").write_text(
                json.dumps(self.story_bible, indent=2)
            )

        return results


def fix_single_book(book_dir: Path) -> Dict:
    """Fix a single book."""
    fixer = BookFixer(book_dir)
    return fixer.run_full_fix()


def get_books_needing_fixes() -> List[Path]:
    """Get books that need fixing (have story bible but not fixed yet)."""
    books = []

    for book_dir in FICTION_DIR.iterdir():
        if not book_dir.is_dir():
            continue

        story_bible_path = book_dir / "story_bible.json"
        if not story_bible_path.exists():
            continue

        # Check if already fixed
        try:
            bible = json.loads(story_bible_path.read_text())
            if bible.get("quality_fixed"):
                continue
        except json.JSONDecodeError:
            continue

        # Check if has chapters
        chapters = list(book_dir.glob("chapter_*.md"))
        if len(chapters) >= 3:
            books.append(book_dir)

    return books


def main():
    """Main fix loop."""
    logger.info("=" * 60)
    logger.info("BOOK FIXER - Automatic Quality Improvement")
    logger.info("=" * 60)

    books = get_books_needing_fixes()
    logger.info(f"Found {len(books)} books needing fixes")

    if not books:
        logger.info("All books with story bibles have been fixed!")
        return

    total_issues = 0
    total_fixes = 0

    for i, book_dir in enumerate(books, 1):
        logger.info(f"\n[{i}/{len(books)}] {book_dir.name}")

        try:
            results = fix_single_book(book_dir)
            total_issues += results["issues_found"]
            total_fixes += results["fixes_applied"]

            if results["details"]:
                for detail in results["details"]:
                    logger.info(f"    ✓ {detail}")

        except Exception as e:
            logger.error(f"  Error fixing {book_dir.name}: {e}")

        # Rate limiting
        time.sleep(5)

    logger.info("\n" + "=" * 60)
    logger.info("FIX COMPLETE")
    logger.info(f"  Total issues found: {total_issues}")
    logger.info(f"  Total fixes applied: {total_fixes}")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
