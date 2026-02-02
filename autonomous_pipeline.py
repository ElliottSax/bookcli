#!/usr/bin/env python3
"""
Fully Autonomous Book Production Pipeline
Runs perpetually on Oracle Cloud workers.
Handles: concept generation -> writing -> editing -> quality improvement -> finalization

Uses centralized lib/ modules for API calls, logging, and configuration.
Uses fixers/ module for quality improvements (deduplication from local QualityPipeline).
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
from lib.unified_generator import UnifiedBookGenerator, GenerationConfig
from lib.quality_scorer import QualityScorer
from lib.checkpoint import CheckpointManager, ProcessingStage, BookStatus
from lib.backup import BackupManager
from lib.copyright_guard import CopyrightGuard
from lib.notifications import send_notification

# Modular fixers for quality improvement
from fixers import BookContext, QualityFixer, TextFixer, CoherencyFixer

# Generation Guard - prevents quality issues during generation
try:
    from generation_guard import GenerationGuard
    GUARD_AVAILABLE = True
except ImportError:
    GUARD_AVAILABLE = False


# Compatibility wrappers for deprecated imports
class ConceptGenerator:
    """Compatibility wrapper - delegates to UnifiedBookGenerator."""
    def __init__(self, output_dir):
        self._generator = UnifiedBookGenerator(output_dir)

    def generate_concept(self, genre=None, subgenre=None, trope=None):
        return self._generator.generate_concept(genre=genre, subgenre=subgenre, trope=trope)


class BookWriter:
    """Compatibility wrapper - delegates to UnifiedBookGenerator."""
    def __init__(self, output_dir=None):
        # Will be set when write_book is called
        self._generator = None
        self._output_dir = output_dir

    def write_book(self, concept, book_dir, **kwargs):
        if self._generator is None:
            self._generator = UnifiedBookGenerator(book_dir.parent if book_dir else Path('.'))
        return self._generator.generate_book(concept, **kwargs)


# Quality Gate compatibility
class QualityGate:
    """Compatibility wrapper for QualityGate."""
    def __init__(self):
        self.scorer = QualityScorer()

    def check(self, content: str) -> dict:
        report = self.scorer.analyze(content)
        return {'passed': report.passed, 'score': report.score, 'issues': report.warnings}


def create_quality_enhanced_prompt(base_prompt: str, quality_report=None) -> str:
    """Compatibility function for quality-enhanced prompts."""
    if quality_report and hasattr(quality_report, 'get_prompt_additions'):
        return base_prompt + quality_report.get_prompt_additions()
    return base_prompt


QUALITY_GATE_AVAILABLE = True

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


class QualityPipeline:
    """
    Runs all quality improvement passes on a book.

    This is a thin wrapper around the fixers module that provides
    the same interface as before for backwards compatibility.
    The actual implementation is in fixers/quality_fixer.py.
    """

    def run_quality_pass(self, book_dir: Path) -> Dict:
        """
        Run all quality improvements on a book.

        Uses the fixers module (QualityFixer and TextFixer) for actual work.
        Creates backups before modifications and saves checkpoints.
        """
        stats = {"chapters_improved": 0, "total_improvements": 0}

        chapters = sorted(book_dir.glob("chapter_*.md"))
        if not chapters:
            return stats

        logger.info(f"  Running quality pass on {len(chapters)} chapters")

        # Initialize checkpoint and backup managers
        checkpoint_mgr = CheckpointManager(book_dir)
        backup_mgr = BackupManager(book_dir)

        # Create backup before modifications
        backup_mgr.backup_all_chapters()
        logger.info("  Created backup of all chapters")

        # Save checkpoint for quality stage
        checkpoint_mgr.save(
            ProcessingStage.QUALITY_CHECKS,
            chapter=0,
            total=len(chapters),
        )

        # Create book context
        context = BookContext(book_dir)

        # Run text fixes first (doubled names, LLM artifacts, etc.)
        text_fixer = TextFixer(context)
        text_fixes = text_fixer.fix()
        stats["total_improvements"] += text_fixes

        # Re-load context after text fixes
        context = BookContext(book_dir)

        # Run coherency fixes (generation loops, duplications)
        # This catches paragraph/dialogue/sentence repetition from LLM generation
        coherency_fixer = CoherencyFixer(
            context,
            fix_loops=True,
            fix_duplicates=True,
            aggressive=False
        )
        coherency_fixes = coherency_fixer.fix()
        stats["total_improvements"] += coherency_fixes
        stats["coherency_fixes"] = coherency_fixes

        # Re-load context after coherency fixes
        context = BookContext(book_dir)

        # Run quality fixes (AI-isms, sensory, dialogue, tension, expansion, endings)
        quality_fixer = QualityFixer(
            context,
            expand_short=True,
            fix_pov=True,
            fix_ai_isms=True,
            add_sensory=True,
            add_tension=True,
            improve_dialogue=True,
            improve_endings=True,
        )
        quality_stats = quality_fixer.run_full_quality_pass()

        # Aggregate stats
        total_quality = sum(quality_stats.values())
        stats["chapters_improved"] = total_quality
        stats["total_improvements"] += total_quality
        stats["details"] = quality_stats

        # Update checkpoint
        checkpoint_mgr.save(
            ProcessingStage.QUALITY_CHECKS,
            chapter=len(chapters),
            total=len(chapters),
            metadata={"quality_stats": quality_stats},
        )

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

        prompt = config.prompts.story_bible_generation.format(
            title=concept.get('title'),
            genre=concept.get('genre'),
            subgenre=concept.get('subgenre'),
            premise=concept.get('premise'),
            first_chapter=first_chapter,
            last_chapter=last_chapter
        )

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
        self.concept_gen = ConceptGenerator(OUTPUT_DIR)
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
        """Produce a single complete book with checkpoint/recovery support."""
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

        # Check if book already completed
        if (book_dir / ".complete").exists():
            logger.info(f"Book already complete: {title}")
            return True

        book_dir.mkdir(parents=True, exist_ok=True)

        # Initialize checkpoint manager
        checkpoint_mgr = CheckpointManager(book_dir)

        # Save concept
        (book_dir / "concept.json").write_text(json.dumps(concept, indent=2))

        # Save initial checkpoint
        checkpoint_mgr.save(ProcessingStage.CONCEPT)

        logger.info("WRITING BOOK")
        if not self.writer.write_book(concept, book_dir):
            logger.error("Failed to write book")
            checkpoint_mgr.mark_failed("Failed to write book")
            return False

        # Save checkpoint after writing
        checkpoint_mgr.save(ProcessingStage.EDITING)

        logger.info("RUNNING QUALITY PIPELINE")
        stats = self.quality.run_quality_pass(book_dir)
        logger.info(f"Quality improvements: {stats}")

        logger.info("GENERATING STORY BIBLE")
        if not self.bible_gen.generate(book_dir, concept):
            logger.warning("Failed to generate story bible")

        # Save checkpoint before finalization
        checkpoint_mgr.save(ProcessingStage.FINALIZATION)

        logger.info("FINALIZING BOOK")
        if self.finalizer.finalize(book_dir, concept):
            # Mark as complete in checkpoint
            checkpoint_mgr.mark_completed(metadata={"stats": stats})
            logger.info(f"SUCCESS: {title} complete!")
            return True

        checkpoint_mgr.mark_failed("Failed finalization quality check")
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
                    logger.warning(f"Error producing book. Total errors in a row: {errors_in_row}")

                if errors_in_row >= 3:
                    logger.warning(f"Too many errors ({errors_in_row}), backing off for 5 minutes")
                    send_notification(
                        subject="BookCLI Pipeline Backoff",
                        message=f"The pipeline has encountered {errors_in_row} consecutive errors and is backing off for 5 minutes."
                    )
                    time.sleep(300)
                    errors_in_row = 0
                else:
                    time.sleep(30)

            except KeyboardInterrupt:
                logger.info("Pipeline stopped by user")
                break
            except Exception as e:
                logger.error(f"Unexpected error: {e}", exc_info=True)
                errors_in_row += 1
                send_notification(
                    subject="BookCLI Pipeline Critical Error",
                    message=f"The pipeline has encountered an unexpected error: {e}"
                )
                time.sleep(60)


if __name__ == "__main__":
    pipeline = AutonomousPipeline()
    pipeline.run_forever()
