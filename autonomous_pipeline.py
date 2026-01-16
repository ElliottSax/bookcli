#!/usr/bin/env python3
"""
Fully Autonomous Book Production Pipeline
Runs perpetually on Oracle Cloud workers.
Handles: concept generation -> writing -> editing -> quality improvement -> finalization

Uses centralized lib/ modules for API calls, logging, and configuration.
"""

import os
import json
import time
import random
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, List

# Centralized lib modules
from lib.logging_config import setup_logging, get_logger
from lib.config import get_config
from lib.api_client import call_llm, extract_json_from_response

# Generation Guard - prevents quality issues during generation
try:
    from generation_guard import GenerationGuard
    GUARD_AVAILABLE = True
except ImportError:
    GUARD_AVAILABLE = False

# Initialize
setup_logging()
config = get_config()

# Configuration - can be overridden by environment variables
WORKER_ID = os.environ.get("WORKER_ID", "worker-1")
OUTPUT_DIR = Path(os.environ.get("OUTPUT_DIR", str(config.paths.fiction_dir)))

# Quality thresholds from config
MIN_CHAPTER_WORDS = config.quality.min_chapter_words
TARGET_CHAPTER_WORDS = config.quality.target_chapter_words
CHAPTERS_PER_BOOK = config.quality.chapters_per_book

# Get logger with worker ID in the name
logger = get_logger(f"pipeline.{WORKER_ID}")

if not GUARD_AVAILABLE:
    logger.warning("generation_guard not available - running without inline validation")

# Genre definitions for concept generation
GENRES = {
    "romance": {
        "subgenres": ["contemporary", "historical", "paranormal", "dark", "romantic comedy", "second chance", "enemies to lovers"],
        "tropes": ["fake dating", "forced proximity", "grumpy/sunshine", "billionaire", "small town", "slow burn", "forbidden love"]
    },
    "thriller": {
        "subgenres": ["psychological", "domestic", "legal", "medical", "techno-thriller", "conspiracy"],
        "tropes": ["unreliable narrator", "missing person", "dark secret", "revenge", "trapped", "double cross"]
    },
    "fantasy": {
        "subgenres": ["epic", "urban", "romantasy", "dark fantasy", "portal", "fairy tale retelling"],
        "tropes": ["chosen one", "found family", "morally grey hero", "enemies to lovers", "hidden identity", "magic system"]
    },
    "mystery": {
        "subgenres": ["cozy", "police procedural", "amateur sleuth", "noir", "locked room", "historical"],
        "tropes": ["small town secrets", "cold case", "serial killer", "heist", "whodunit", "red herrings"]
    },
    "scifi": {
        "subgenres": ["space opera", "cyberpunk", "dystopian", "first contact", "time travel", "AI/robots"],
        "tropes": ["last survivor", "generation ship", "clone identity", "rebellion", "first contact", "simulation"]
    },
    "horror": {
        "subgenres": ["supernatural", "psychological", "cosmic", "folk horror", "haunted house", "body horror"],
        "tropes": ["isolation", "cursed object", "unreliable reality", "possession", "ancient evil", "survival"]
    },
    "literary": {
        "subgenres": ["family saga", "coming of age", "historical fiction", "social commentary", "magical realism"],
        "tropes": ["generational trauma", "identity crisis", "homecoming", "secrets revealed", "transformation"]
    },
    "self_help": {
        "subgenres": ["productivity", "psychology", "finance", "health", "relationships", "career"],
        "tropes": ["framework", "case studies", "actionable steps", "mindset shift", "habit building"]
    }
}


class ConceptGenerator:
    """Generates unique book concepts."""

    def __init__(self):
        self.generated_titles = self._load_existing_titles()

    def _load_existing_titles(self) -> set:
        """Load titles of already generated books."""
        titles = set()
        if OUTPUT_DIR.exists():
            for book_dir in OUTPUT_DIR.iterdir():
                if book_dir.is_dir():
                    titles.add(book_dir.name.lower().replace("_", " "))
        return titles

    def generate_concept(self) -> Optional[Dict]:
        """Generate a unique book concept."""
        genre = random.choice(list(GENRES.keys()))
        genre_info = GENRES[genre]
        subgenre = random.choice(genre_info["subgenres"])
        trope = random.choice(genre_info["tropes"])

        prompt = f"""Generate a unique, marketable book concept.

Genre: {genre} ({subgenre})
Trope: {trope}

Return a JSON object with:
{{
    "title": "Compelling, marketable title (5 words max)",
    "subtitle": "Optional subtitle for non-fiction",
    "genre": "{genre}",
    "subgenre": "{subgenre}",
    "trope": "{trope}",
    "premise": "2-3 sentence hook that would appear on book cover",
    "protagonist": "Name and brief description",
    "conflict": "Main conflict or problem",
    "setting": "Time and place",
    "tone": "Overall tone (dark, light, humorous, etc.)",
    "target_audience": "Who will read this",
    "comparable_titles": ["Title 1", "Title 2"]
}}

Make the concept fresh and commercially viable. Avoid clichés."""

        result = call_llm(prompt, max_tokens=1500, temperature=0.8)
        if not result:
            return None

        concept = extract_json_from_response(result)
        if not concept:
            return None

        # Check for duplicate title
        title = concept.get("title", "").lower()
        if title in self.generated_titles:
            logger.info(f"Duplicate title detected: {title}, regenerating...")
            return None

        self.generated_titles.add(title)
        return concept


class BookWriter:
    """Writes complete books from concepts."""

    def create_outline(self, concept: Dict) -> Optional[Dict]:
        """Create a chapter-by-chapter outline."""
        prompt = f"""Create a detailed {CHAPTERS_PER_BOOK}-chapter outline for this book:

Title: {concept.get('title')}
Genre: {concept.get('genre')} / {concept.get('subgenre')}
Premise: {concept.get('premise')}
Protagonist: {concept.get('protagonist')}
Conflict: {concept.get('conflict')}
Setting: {concept.get('setting')}

Return a JSON object with:
{{
    "chapters": [
        {{
            "number": 1,
            "title": "Chapter title",
            "summary": "2-3 sentence summary of what happens",
            "key_events": ["Event 1", "Event 2", "Event 3"],
            "character_development": "What the protagonist learns/experiences",
            "ending_hook": "How the chapter ends to keep readers engaged"
        }}
    ]
}}

Ensure strong pacing with rising action, a midpoint twist, dark moment, and satisfying climax."""

        result = call_llm(prompt, max_tokens=4000, temperature=0.7)
        if not result:
            return None

        return extract_json_from_response(result)

    def write_chapter(self, concept: Dict, outline: Dict, chapter_num: int, previous_summary: str = "") -> Optional[str]:
        """Write a single chapter."""
        chapter_info = outline["chapters"][chapter_num - 1]

        context = f"Previous events: {previous_summary}" if previous_summary else "This is the opening chapter."

        prompt = f"""Write Chapter {chapter_num} of "{concept.get('title')}".

Genre: {concept.get('genre')} / {concept.get('subgenre')}
Tone: {concept.get('tone')}

Chapter Title: {chapter_info.get('title')}
Chapter Summary: {chapter_info.get('summary')}
Key Events: {', '.join(chapter_info.get('key_events', []))}
Character Development: {chapter_info.get('character_development')}
Ending Hook: {chapter_info.get('ending_hook')}

{context}

Write a complete chapter of approximately {TARGET_CHAPTER_WORDS} words.

Requirements:
- Start with an engaging hook
- Include vivid sensory details (sight, sound, smell, touch)
- Write natural, distinctive dialogue
- Show character emotions through actions and internal thoughts
- End with the specified hook to keep readers turning pages
- Vary sentence length and paragraph structure
- Avoid clichés and AI-isms like "I cannot", "As an AI", etc.

Write the chapter now:"""

        return call_llm(prompt, max_tokens=5000, temperature=0.8)

    def write_book(self, concept: Dict, book_dir: Path) -> bool:
        """Write an entire book with inline quality validation."""
        logger.info(f"Creating outline for: {concept.get('title')}")

        outline = self.create_outline(concept)
        if not outline or "chapters" not in outline:
            logger.error("Failed to create outline")
            return False

        # Save outline
        (book_dir / "outline.json").write_text(json.dumps(outline, indent=2))

        # Initialize generation guard for inline validation
        guard = None
        if GUARD_AVAILABLE:
            try:
                guard = GenerationGuard(book_dir)
                guard.create_story_bible_from_outline(concept, outline)
                logger.info("  Generation guard active - inline validation enabled")
            except Exception as e:
                logger.warning(f"  Could not initialize generation guard: {e}")
                guard = None

        # Write chapters with validation
        previous_summaries = []
        for i in range(1, CHAPTERS_PER_BOOK + 1):
            logger.info(f"  Writing chapter {i}/{CHAPTERS_PER_BOOK}")

            previous_summary = " ".join(previous_summaries[-3:]) if previous_summaries else ""
            chapter = None

            # Try up to 3 times with validation
            max_attempts = 3 if guard else 1
            for attempt in range(max_attempts):
                chapter = self.write_chapter(concept, outline, i, previous_summary)
                if not chapter:
                    continue

                # Validate with guard if available
                if guard:
                    result = guard.validate_chapter(i, chapter)
                    if result.passed:
                        break
                    else:
                        logger.warning(f"    Chapter {i} validation failed (attempt {attempt + 1}/{max_attempts})")
                        for issue in result.issues[:2]:
                            logger.warning(f"      - {issue}")

                        if attempt < max_attempts - 1 and result.should_regenerate:
                            hint_text = guard.get_regeneration_prompt_additions(result)
                            previous_summary = previous_summary + hint_text
                            time.sleep(2)
                else:
                    break

            if not chapter:
                logger.error(f"Failed to write chapter {i}")
                return False

            # Save chapter
            chapter_file = book_dir / f"chapter_{i:02d}.md"
            chapter_file.write_text(f"# Chapter {i}: {outline['chapters'][i-1].get('title', '')}\n\n{chapter}")

            # Update guard tracking
            if guard:
                guard.update_tracking(i, chapter)

            # Update summary for next chapter
            previous_summaries.append(outline['chapters'][i-1].get('summary', ''))

            time.sleep(config.pipeline.delay_between_chapters)

        return True


class QualityPipeline:
    """Runs all quality improvement passes on a book."""

    def fix_ai_isms(self, text: str) -> str:
        """Remove AI-isms and improve natural flow."""
        ai_patterns = [
            "I cannot", "As an AI", "I don't have", "I'm not able",
            "delve", "tapestry", "vibrant", "multifaceted", "Moreover",
            "Furthermore", "Additionally", "It's important to note",
            "In conclusion", "To summarize"
        ]

        if not any(p.lower() in text.lower() for p in ai_patterns):
            return text

        prompt = f"""Remove AI-isms and improve this text. Replace:
- "Moreover/Furthermore/Additionally" with natural transitions
- "delve/tapestry/vibrant/multifaceted" with simpler words
- Any robotic or unnatural phrasing

Keep the same meaning and length. Return ONLY the improved text.

{text[:3000]}"""

        result = call_llm(prompt, max_tokens=4000, temperature=0.5)
        return result if result else text

    def add_sensory_details(self, text: str) -> str:
        """Add sensory details to prose."""
        sensory_words = ['smell', 'taste', 'hear', 'sound', 'feel', 'texture', 'cold', 'warm', 'bright', 'dark']
        if any(w in text.lower() for w in sensory_words):
            return text

        prompt = f"""Add 2-3 sensory details to this passage. Include sight, sound, smell, or touch.
Keep the same meaning and approximate length. Return ONLY the improved text.

{text[:2000]}"""

        result = call_llm(prompt, max_tokens=3000, temperature=0.6)
        return result if result else text

    def improve_dialogue(self, text: str) -> str:
        """Make dialogue more distinctive."""
        if text.count('"') < 4:
            return text

        prompt = f"""Improve the dialogue in this passage:
- Give each character a distinctive voice
- Add beats and reactions between dialogue
- Make conversations feel more natural

Keep the same plot points. Return ONLY the improved text.

{text[:3000]}"""

        result = call_llm(prompt, max_tokens=4000, temperature=0.7)
        return result if result else text

    def add_tension(self, text: str) -> str:
        """Add subtle tension to flat scenes."""
        tension_words = ['suddenly', 'danger', 'fear', 'threat', 'secret', 'hidden', 'urgent']
        if any(w in text.lower() for w in tension_words):
            return text

        prompt = f"""Add subtle tension to this passage through:
- Internal worry or doubt
- Environmental unease
- Time pressure
- Interpersonal friction

Keep the same plot. Return ONLY the improved text.

{text[:2000]}"""

        result = call_llm(prompt, max_tokens=3000, temperature=0.7)
        return result if result else text

    def improve_ending(self, text: str, is_final: bool = False) -> str:
        """Strengthen chapter endings."""
        words = text.split()
        if len(words) < 300:
            return text

        ending = ' '.join(words[-300:])
        beginning = ' '.join(words[:-300])

        if is_final:
            prompt = f"""Improve this final chapter ending to be more satisfying and emotionally resonant.
Give proper closure while leaving hope. Return ONLY the improved ending (about 300 words).

{ending}"""
        else:
            prompt = f"""Improve this chapter ending to create a stronger hook.
Add suspense, a revelation, or emotional cliff-hanger. Return ONLY the improved ending (about 300 words).

{ending}"""

        result = call_llm(prompt, max_tokens=500, temperature=0.7)
        if result and len(result.split()) > 100:
            return beginning + ' ' + result
        return text

    def expand_short_chapter(self, text: str) -> str:
        """Expand chapters that are too short."""
        words = len(text.split())
        if words >= MIN_CHAPTER_WORDS:
            return text

        prompt = f"""Expand this chapter to approximately {TARGET_CHAPTER_WORDS} words by:
- Adding detailed scene descriptions
- Expanding dialogue with reactions
- Including character thoughts and emotions
- Adding transitional scenes

Keep the same plot points. Return ONLY the expanded chapter.

{text}"""

        result = call_llm(prompt, max_tokens=5000, temperature=0.7)
        if result and len(result.split()) > words + 500:
            return result
        return text

    def run_quality_pass(self, book_dir: Path) -> Dict:
        """Run all quality improvements on a book."""
        stats = {"chapters_improved": 0, "total_improvements": 0}

        chapters = sorted(book_dir.glob("chapter_*.md"))
        if not chapters:
            return stats

        for i, chapter_file in enumerate(chapters):
            logger.info(f"  Quality pass on {chapter_file.name}")
            text = chapter_file.read_text()
            original_text = text

            # Run all improvement passes
            text = self.fix_ai_isms(text)
            text = self.add_sensory_details(text)
            text = self.improve_dialogue(text)
            text = self.add_tension(text)
            text = self.expand_short_chapter(text)

            # Improve ending
            is_final = (i == len(chapters) - 1)
            text = self.improve_ending(text, is_final=is_final)

            if text != original_text:
                chapter_file.write_text(text)
                stats["chapters_improved"] += 1
                stats["total_improvements"] += 1

            time.sleep(1)

        return stats


class StoryBibleGenerator:
    """Creates story bibles for completed books."""

    def generate(self, book_dir: Path, concept: Dict) -> bool:
        """Generate a comprehensive story bible."""
        chapters = sorted(book_dir.glob("chapter_*.md"))
        if not chapters:
            return False

        first_chapter = chapters[0].read_text()[:2000]
        last_chapter = chapters[-1].read_text()[-2000:]

        prompt = f"""Create a comprehensive story bible for this book.

Title: {concept.get('title')}
Genre: {concept.get('genre')} / {concept.get('subgenre')}
Premise: {concept.get('premise')}

Opening excerpt:
{first_chapter}

Ending excerpt:
{last_chapter}

Return a JSON object with:
{{
    "title": "{concept.get('title')}",
    "genre": "{concept.get('genre')}",
    "subgenre": "{concept.get('subgenre')}",
    "setting": {{
        "time_period": "When the story takes place",
        "locations": ["Location 1", "Location 2"],
        "atmosphere": "Overall mood/atmosphere"
    }},
    "characters": [
        {{
            "name": "Character name",
            "role": "protagonist/antagonist/supporting",
            "description": "Physical and personality description",
            "arc": "Character development throughout the story"
        }}
    ],
    "themes": ["Theme 1", "Theme 2", "Theme 3"],
    "narrative_voice": "POV and tense description",
    "tone": "Overall tone",
    "plot_summary": "2-3 paragraph plot summary"
}}"""

        result = call_llm(prompt, max_tokens=2000, temperature=0.6)
        if not result:
            return False

        bible = extract_json_from_response(result)
        if bible:
            (book_dir / "story_bible.json").write_text(json.dumps(bible, indent=2))
            return True

        return False


class BookFinalizer:
    """Finalizes books with metadata and quality checks."""

    def generate_metadata(self, book_dir: Path, concept: Dict) -> Dict:
        """Generate book metadata for publishing."""
        word_count = 0
        chapters = sorted(book_dir.glob("chapter_*.md"))
        for chapter in chapters:
            word_count += len(chapter.read_text().split())

        metadata = {
            "title": concept.get("title"),
            "subtitle": concept.get("subtitle", ""),
            "genre": concept.get("genre"),
            "subgenre": concept.get("subgenre"),
            "premise": concept.get("premise"),
            "word_count": word_count,
            "chapter_count": len(chapters),
            "target_audience": concept.get("target_audience", ""),
            "comparable_titles": concept.get("comparable_titles", []),
            "generated_at": datetime.now().isoformat(),
            "worker_id": WORKER_ID,
            "quality_passed": True
        }

        (book_dir / "metadata.json").write_text(json.dumps(metadata, indent=2))
        return metadata

    def quality_check(self, book_dir: Path) -> bool:
        """Verify book meets quality standards."""
        chapters = sorted(book_dir.glob("chapter_*.md"))

        if len(chapters) < CHAPTERS_PER_BOOK:
            logger.warning(f"Book has only {len(chapters)} chapters, expected {CHAPTERS_PER_BOOK}")
            return False

        total_words = 0
        for chapter in chapters:
            words = len(chapter.read_text().split())
            if words < 1000:
                logger.warning(f"{chapter.name} is too short: {words} words")
                return False
            total_words += words

        if total_words < 30000:
            logger.warning(f"Book is too short: {total_words} words")
            return False

        required = ["outline.json", "story_bible.json", "metadata.json"]
        for req in required:
            if not (book_dir / req).exists():
                logger.warning(f"Missing required file: {req}")
                return False

        return True

    def finalize(self, book_dir: Path, concept: Dict) -> bool:
        """Run final quality check and generate metadata."""
        self.generate_metadata(book_dir, concept)

        if self.quality_check(book_dir):
            (book_dir / ".complete").write_text(datetime.now().isoformat())
            logger.info(f"Book finalized successfully: {concept.get('title')}")
            return True

        return False


class AutonomousPipeline:
    """Main orchestrator for the autonomous book production pipeline."""

    def __init__(self):
        self.concept_gen = ConceptGenerator()
        self.writer = BookWriter()
        self.quality = QualityPipeline()
        self.bible_gen = StoryBibleGenerator()
        self.finalizer = BookFinalizer()

        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    def sanitize_title(self, title: str) -> str:
        """Convert title to valid directory name."""
        import re
        sanitized = re.sub(r'[^\w\s-]', '', title)
        sanitized = re.sub(r'\s+', '_', sanitized)
        return sanitized[:100]

    def produce_book(self) -> bool:
        """Produce a single complete book."""
        logger.info("=" * 60)
        logger.info("GENERATING NEW BOOK CONCEPT")

        concept = None
        for attempt in range(5):
            concept = self.concept_gen.generate_concept()
            if concept:
                break
            time.sleep(5)

        if not concept:
            logger.error("Failed to generate concept after 5 attempts")
            return False

        title = concept.get("title", "Untitled")
        logger.info(f"Concept: {title}")
        logger.info(f"Genre: {concept.get('genre')} / {concept.get('subgenre')}")

        book_dir = OUTPUT_DIR / self.sanitize_title(title)
        if book_dir.exists():
            logger.info(f"Book already exists: {title}")
            return True

        book_dir.mkdir(parents=True, exist_ok=True)

        (book_dir / "concept.json").write_text(json.dumps(concept, indent=2))

        logger.info("WRITING BOOK")
        if not self.writer.write_book(concept, book_dir):
            logger.error("Failed to write book")
            return False

        logger.info("RUNNING QUALITY PIPELINE")
        stats = self.quality.run_quality_pass(book_dir)
        logger.info(f"Quality improvements: {stats}")

        logger.info("GENERATING STORY BIBLE")
        if not self.bible_gen.generate(book_dir, concept):
            logger.warning("Failed to generate story bible")

        logger.info("FINALIZING BOOK")
        if self.finalizer.finalize(book_dir, concept):
            logger.info(f"SUCCESS: {title} complete!")
            return True

        logger.warning(f"Book incomplete: {title}")
        return False

    def run_forever(self):
        """Run the pipeline perpetually."""
        logger.info("=" * 60)
        logger.info(f"AUTONOMOUS PIPELINE STARTED - {WORKER_ID}")
        logger.info(f"Output directory: {OUTPUT_DIR}")
        logger.info("=" * 60)

        books_produced = 0
        errors_in_row = 0

        while True:
            try:
                if self.produce_book():
                    books_produced += 1
                    errors_in_row = 0
                    logger.info(f"Total books produced: {books_produced}")
                else:
                    errors_in_row += 1

                if errors_in_row >= 3:
                    logger.warning(f"Too many errors ({errors_in_row}), backing off for 5 minutes")
                    time.sleep(300)
                    errors_in_row = 0
                else:
                    time.sleep(30)

            except KeyboardInterrupt:
                logger.info("Pipeline stopped by user")
                break
            except Exception as e:
                logger.error(f"Unexpected error: {e}")
                errors_in_row += 1
                time.sleep(60)


if __name__ == "__main__":
    pipeline = AutonomousPipeline()
    pipeline.run_forever()
