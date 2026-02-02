#!/usr/bin/env python3
"""
Unified Quality Pipeline - Consolidates all quality fix passes into one.

⚠️  DEPRECATION NOTICE (2026-02-01) ⚠️
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
This file has been DEPRECATED and replaced by:

    lib/quality_pipeline.py (QualityPipeline mode)

New Usage:
    from lib.quality_pipeline import QualityPipeline
    pipeline = QualityPipeline(
        fiction_dir,
        mode="local",
        enable_backup=True
    )
    pipeline.run()

Benefits of new module:
- Unified with distributed and batch modes
- Better state tracking
- Consistent API with other pipelines
- Single source of truth

Migration Guide: See REFACTORING_COMPLETE_2026_02.md
Quick Start: See REFACTORING_QUICK_START.md
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

ORIGINAL DOCUMENTATION:
Replaces:
- run_quality.py (TextFixer, QualityFixer)
- run_quality_fixes.py (VarietyFixer, HookStrengthener, CoherencyFixer)

Creates single consolidated marker with detailed state tracking.

Benefits:
- Single pass through all books
- No redundant re-processing
- Smart skip logic (incremental fixes)
- Content hash tracking (avoid timestamp false positives)
- Proper quality validation (real scores, not placeholders)
"""

import sys
import time
import json
import hashlib
import argparse
from pathlib import Path
from typing import Dict, List, Optional, Set
from datetime import datetime
from dataclasses import dataclass, asdict

from dotenv import load_dotenv
load_dotenv()

from lib.logging_config import setup_logging, get_logger
from lib.config import get_config
from lib.checkpoint import CheckpointManager, ProcessingStage, BookStatus
from lib.backup import BackupManager
from lib.quality_validators import validate_book
from fixers import (
    BookContext, TextFixer, NameFixer, QualityFixer,
    VarietyFixer, HookStrengthener, CoherencyFixer
)

setup_logging()
logger = get_logger(__name__)
config = get_config()

# All directories containing books to process
BOOK_DIRS = [
    config.paths.fiction_dir,
    config.paths.output_dir / "books",
]

# Unified marker version
UNIFIED_MARKER_VERSION = 1

# Fix types that can be applied
FIX_TYPES = [
    'text_fixes',       # TextFixer (doubled names, placeholders, LLM artifacts)
    'name_fixes',       # NameFixer (character name consistency)
    'coherency_fixes',  # CoherencyFixer (generation loops, duplicates)
    'ai_ism_fixes',     # QualityFixer (AI-isms removal)
    'pov_fixes',        # QualityFixer (POV consistency)
    'expansion_fixes',  # QualityFixer (short chapter expansion)
    'variety_fixes',    # VarietyFixer (repetitive patterns)
    'hook_fixes',       # HookStrengthener (chapter 1 opening)
]


@dataclass
class FixState:
    """State of a specific fix type."""
    applied: bool = False
    timestamp: float = 0
    content_hash: str = ""
    count: int = 0
    error: Optional[str] = None


@dataclass
class UnifiedMarker:
    """Unified quality marker - tracks all fix states."""
    version: int
    created: float
    updated: float
    book_hash: str  # Hash of all chapter content
    fix_states: Dict[str, FixState]
    validation_scores: Dict = None  # Real quality validation scores
    needs_revalidation: bool = False


def compute_book_hash(book_dir: Path) -> str:
    """Compute hash of all chapter content."""
    hasher = hashlib.sha256()
    chapters = sorted(book_dir.glob("chapter_*.md"))

    for chapter in chapters:
        try:
            content = chapter.read_bytes()
            hasher.update(content)
        except (OSError, IOError) as e:
            logger.debug(f"Could not read {chapter}: {e}")

    return hasher.hexdigest()


def read_unified_marker(book_dir: Path) -> Optional[UnifiedMarker]:
    """Read unified quality marker."""
    marker_file = book_dir / ".quality_unified"

    if not marker_file.exists():
        return None

    try:
        data = json.loads(marker_file.read_text())

        # Convert fix_states back to FixState objects
        fix_states = {}
        for fix_type, state_dict in data.get('fix_states', {}).items():
            fix_states[fix_type] = FixState(**state_dict)

        return UnifiedMarker(
            version=data['version'],
            created=data['created'],
            updated=data['updated'],
            book_hash=data['book_hash'],
            fix_states=fix_states,
            validation_scores=data.get('validation_scores'),
            needs_revalidation=data.get('needs_revalidation', False)
        )

    except Exception as e:
        logger.debug(f"Could not parse unified marker for {book_dir.name}: {e}")
        return None


def write_unified_marker(book_dir: Path, marker: UnifiedMarker) -> None:
    """Write unified quality marker."""
    marker_file = book_dir / ".quality_unified"

    # Convert FixState objects to dicts
    fix_states_dict = {
        fix_type: asdict(state)
        for fix_type, state in marker.fix_states.items()
    }

    data = {
        'version': marker.version,
        'created': marker.created,
        'updated': marker.updated,
        'book_hash': marker.book_hash,
        'fix_states': fix_states_dict,
        'validation_scores': marker.validation_scores,
        'needs_revalidation': marker.needs_revalidation
    }

    marker_file.write_text(json.dumps(data, indent=2))


def needs_reprocessing(book_dir: Path, marker: Optional[UnifiedMarker],
                      requested_fixes: Set[str]) -> Tuple[bool, List[str]]:
    """
    Determine if book needs reprocessing and which fixes to apply.

    Returns:
        (needs_processing, fixes_to_apply)
    """
    # No marker = need full processing
    if not marker:
        return True, list(requested_fixes)

    # Check if content changed
    current_hash = compute_book_hash(book_dir)
    if current_hash != marker.book_hash:
        logger.debug(f"{book_dir.name}: Content hash changed, full reprocess")
        return True, list(requested_fixes)

    # Check which requested fixes haven't been applied
    fixes_needed = []
    for fix_type in requested_fixes:
        state = marker.fix_states.get(fix_type)

        # Fix not applied yet
        if not state or not state.applied:
            fixes_needed.append(fix_type)
            continue

        # Fix had an error last time
        if state.error:
            fixes_needed.append(fix_type)
            continue

    # Need validation if requested and not done
    if marker.needs_revalidation:
        return True, fixes_needed

    return len(fixes_needed) > 0, fixes_needed


def run_unified_quality_pipeline(
    book_dir: Path,
    fixes_to_apply: List[str],
    use_llm: bool = True,
    validate_quality: bool = True
) -> Dict:
    """
    Run unified quality pipeline on a single book.

    Args:
        book_dir: Path to book directory
        fixes_to_apply: List of fix types to apply
        use_llm: Whether to use LLM for AI-powered fixes
        validate_quality: Whether to run quality validation

    Returns:
        Dict with stats and results
    """
    stats = {fix_type: 0 for fix_type in FIX_TYPES}
    stats['error'] = None
    stats['validation_scores'] = None

    try:
        # Read or create marker
        marker = read_unified_marker(book_dir)
        if not marker:
            marker = UnifiedMarker(
                version=UNIFIED_MARKER_VERSION,
                created=time.time(),
                updated=time.time(),
                book_hash=compute_book_hash(book_dir),
                fix_states={},
                needs_revalidation=validate_quality
            )

        # Create backup before modifications
        backup_mgr = BackupManager(book_dir)
        backups = backup_mgr.backup_all_chapters()
        logger.info(f"  Created {len(backups)} backups")

        # Save checkpoint
        checkpoint_mgr = CheckpointManager(book_dir)
        context = BookContext(book_dir)
        checkpoint_mgr.save(
            ProcessingStage.QUALITY_CHECKS,
            chapter=0,
            total=context.chapter_count
        )

        # ===== PASS 1: TEXT FIXES (No LLM) =====
        if 'text_fixes' in fixes_to_apply:
            context = BookContext(book_dir)
            text_fixer = TextFixer(context)
            count = text_fixer.fix()
            stats['text_fixes'] = count

            marker.fix_states['text_fixes'] = FixState(
                applied=True,
                timestamp=time.time(),
                content_hash=compute_book_hash(book_dir),
                count=count
            )

        # ===== PASS 2: NAME CONSISTENCY (No LLM) =====
        if 'name_fixes' in fixes_to_apply:
            context = BookContext(book_dir)
            name_fixer = NameFixer(context)
            count = name_fixer.fix()
            stats['name_fixes'] = count

            marker.fix_states['name_fixes'] = FixState(
                applied=True,
                timestamp=time.time(),
                content_hash=compute_book_hash(book_dir),
                count=count
            )

        # ===== PASS 3: COHERENCY FIXES (No LLM) =====
        if 'coherency_fixes' in fixes_to_apply:
            context = BookContext(book_dir)
            coherency_fixer = CoherencyFixer(
                context,
                fix_loops=True,
                fix_duplicates=True,
                aggressive=False
            )
            count = coherency_fixer.fix()
            stats['coherency_fixes'] = count

            marker.fix_states['coherency_fixes'] = FixState(
                applied=True,
                timestamp=time.time(),
                content_hash=compute_book_hash(book_dir),
                count=count
            )

        # ===== PASS 4: QUALITY FIXES (LLM) =====
        if use_llm:
            # Reload context after previous fixes
            context = BookContext(book_dir)

            # AI-ism removal
            if 'ai_ism_fixes' in fixes_to_apply:
                quality_fixer = QualityFixer(
                    context,
                    expand_short=False,
                    fix_pov=False,
                    fix_ai_isms=True,
                    add_sensory=False,
                    add_tension=False,
                    improve_dialogue=False,
                    improve_endings=False,
                    show_dont_tell=False,
                    add_dialogue_depth=False,
                )
                count = quality_fixer.fix()
                stats['ai_ism_fixes'] = count

                marker.fix_states['ai_ism_fixes'] = FixState(
                    applied=True,
                    timestamp=time.time(),
                    content_hash=compute_book_hash(book_dir),
                    count=count
                )

            # POV consistency
            if 'pov_fixes' in fixes_to_apply:
                context = BookContext(book_dir)  # Reload
                quality_fixer = QualityFixer(
                    context,
                    expand_short=False,
                    fix_pov=True,
                    fix_ai_isms=False,
                    add_sensory=False,
                    add_tension=False,
                    improve_dialogue=False,
                    improve_endings=False,
                    show_dont_tell=False,
                    add_dialogue_depth=False,
                )
                count = quality_fixer.fix()
                stats['pov_fixes'] = count

                marker.fix_states['pov_fixes'] = FixState(
                    applied=True,
                    timestamp=time.time(),
                    content_hash=compute_book_hash(book_dir),
                    count=count
                )

            # Short chapter expansion
            if 'expansion_fixes' in fixes_to_apply:
                context = BookContext(book_dir)  # Reload
                quality_fixer = QualityFixer(
                    context,
                    expand_short=True,
                    fix_pov=False,
                    fix_ai_isms=False,
                    add_sensory=False,
                    add_tension=False,
                    improve_dialogue=False,
                    improve_endings=False,
                    show_dont_tell=False,
                    add_dialogue_depth=False,
                )
                count = quality_fixer.fix()
                stats['expansion_fixes'] = count

                marker.fix_states['expansion_fixes'] = FixState(
                    applied=True,
                    timestamp=time.time(),
                    content_hash=compute_book_hash(book_dir),
                    count=count
                )

            # Variety improvements
            if 'variety_fixes' in fixes_to_apply:
                context = BookContext(book_dir)  # Reload
                variety_fixer = VarietyFixer(context, use_llm=True, threshold=5)
                count = variety_fixer.fix()
                stats['variety_fixes'] = count

                marker.fix_states['variety_fixes'] = FixState(
                    applied=True,
                    timestamp=time.time(),
                    content_hash=compute_book_hash(book_dir),
                    count=count
                )

            # Hook strengthening (chapter 1 only)
            if 'hook_fixes' in fixes_to_apply:
                context = BookContext(book_dir)  # Reload
                hook_fixer = HookStrengthener(context, chapters_to_fix=[1])
                count = hook_fixer.fix()
                stats['hook_fixes'] = count

                marker.fix_states['hook_fixes'] = FixState(
                    applied=True,
                    timestamp=time.time(),
                    content_hash=compute_book_hash(book_dir),
                    count=count
                )

        # ===== PASS 5: QUALITY VALIDATION =====
        if validate_quality:
            context = BookContext(book_dir)  # Reload final state
            chapters = [context.chapters[num] for num in sorted(context.chapters.keys())]
            validation_result = validate_book(chapters)

            marker.validation_scores = validation_result['summary']
            marker.needs_revalidation = False
            stats['validation_scores'] = validation_result['summary']

            logger.info(f"  Validation: {validation_result['summary']['overall_score']:.1f}/100")

        # Update marker with final state
        marker.updated = time.time()
        marker.book_hash = compute_book_hash(book_dir)
        write_unified_marker(book_dir, marker)

        # Mark checkpoint complete
        total_fixes = sum(v for k, v in stats.items() if k != 'error' and k != 'validation_scores')
        checkpoint_mgr.save(
            ProcessingStage.QUALITY_CHECKS,
            chapter=context.chapter_count,
            total=context.chapter_count,
            status=BookStatus.COMPLETED,
            metadata={'fixes': total_fixes}
        )

    except Exception as e:
        stats['error'] = str(e)
        logger.error(f"  Error: {e}")

    return stats


def get_all_books() -> List[Path]:
    """Get all book directories from all configured locations."""
    all_books = []

    for book_dir in BOOK_DIRS:
        if book_dir.exists():
            books = [d for d in book_dir.iterdir() if d.is_dir() and not d.name.startswith('.')]
            # Only include directories that have chapter files
            books_with_chapters = []
            for b in books:
                try:
                    next(b.glob("chapter_*.md"))
                    books_with_chapters.append(b)
                except StopIteration:
                    pass
            all_books.extend(books_with_chapters)
            logger.info(f"Found {len(books_with_chapters)} books in {book_dir}")

    return sorted(all_books, key=lambda x: x.name)


def migrate_old_markers(book_dir: Path) -> Optional[UnifiedMarker]:
    """
    Migrate old separate marker files to unified marker.

    Looks for:
    - .quality_processed (old run_quality.py marker)
    - .variety_fixed (old run_quality_fixes.py marker)
    - Other fix-specific markers

    Returns:
        UnifiedMarker with migrated state, or None if no old markers found
    """
    old_markers = {
        'text_fixes': book_dir / ".quality_processed",
        'variety_fixes': book_dir / ".variety_fixed",
        'hook_fixes': book_dir / ".hooks_strengthened",
        'ai_ism_fixes': book_dir / ".ai_isms_fixed",
        'pov_fixes': book_dir / ".pov_fixed",
    }

    fix_states = {}
    found_any = False

    for fix_type, marker_file in old_markers.items():
        if marker_file.exists():
            found_any = True
            fix_states[fix_type] = FixState(
                applied=True,
                timestamp=marker_file.stat().st_mtime,
                content_hash="",  # Unknown
                count=0  # Unknown
            )

    if not found_any:
        return None

    # Create unified marker from old markers
    return UnifiedMarker(
        version=UNIFIED_MARKER_VERSION,
        created=time.time(),
        updated=time.time(),
        book_hash=compute_book_hash(book_dir),
        fix_states=fix_states,
        needs_revalidation=True  # Re-validate after migration
    )


def main():
    """Process all books with unified quality pipeline."""
    parser = argparse.ArgumentParser(
        description="Unified quality pipeline - all fixes in one pass",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                      # Process all books (smart skip)
  %(prog)s --force              # Reprocess all books
  %(prog)s --migrate            # Migrate old markers to unified
  %(prog)s --validate-only      # Only run quality validation
  %(prog)s --no-llm             # Skip LLM-based fixes (faster)
  %(prog)s --fixes text,name    # Only apply specific fixes
        """
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Reprocess all books regardless of markers"
    )
    parser.add_argument(
        "--migrate",
        action="store_true",
        help="Migrate old separate markers to unified markers"
    )
    parser.add_argument(
        "--validate-only",
        action="store_true",
        help="Only run quality validation, no fixes"
    )
    parser.add_argument(
        "--no-llm",
        action="store_true",
        help="Skip LLM-based fixes (text/name/coherency only)"
    )
    parser.add_argument(
        "--fixes",
        type=str,
        help="Comma-separated list of fix types to apply"
    )

    args = parser.parse_args()

    # Determine which fixes to apply
    if args.validate_only:
        requested_fixes = set()
        validate_quality = True
    elif args.fixes:
        requested_fixes = set(args.fixes.split(','))
        validate_quality = True
    else:
        # Default: all fixes
        requested_fixes = set(FIX_TYPES)
        validate_quality = True

    # Check if API is available for LLM-based fixes
    available_apis = config.api.get_available_apis()
    use_llm = len(available_apis) > 0 and not args.no_llm

    if use_llm:
        logger.info(f"API available ({available_apis[0]}) - LLM-based fixes enabled")
    else:
        logger.info("No API keys configured - running text fixes only (no LLM)")
        # Remove LLM-dependent fixes
        requested_fixes -= {'ai_ism_fixes', 'pov_fixes', 'expansion_fixes', 'variety_fixes', 'hook_fixes'}

    # Get all books
    books = get_all_books()

    if not books:
        logger.error("No books found in any configured directory")
        sys.exit(1)

    # Handle migration mode
    if args.migrate:
        logger.info("Migrating old markers to unified format...")
        migrated = 0
        for book_dir in books:
            marker = migrate_old_markers(book_dir)
            if marker:
                write_unified_marker(book_dir, marker)
                migrated += 1
                logger.info(f"  Migrated: {book_dir.name}")
        logger.info(f"Migrated {migrated} books")
        return

    # Determine which books need processing
    to_process = []
    for book_dir in books:
        marker = read_unified_marker(book_dir)

        if args.force:
            to_process.append((book_dir, list(requested_fixes)))
        else:
            needs_proc, fixes_needed = needs_reprocessing(book_dir, marker, requested_fixes)
            if needs_proc:
                to_process.append((book_dir, fixes_needed))

    if not to_process:
        logger.info("No books need processing!")
        logger.info("All books are up to date with requested fixes")
        logger.info("Use --force to reprocess all books anyway")
        return

    logger.info(f"Processing {len(to_process)} books")
    logger.info(f"Requested fixes: {', '.join(requested_fixes)}")
    logger.info("=" * 60)

    # Process books
    success = 0
    total_stats = {fix_type: 0 for fix_type in FIX_TYPES}
    start_time = time.time()

    for i, (book_dir, fixes_needed) in enumerate(to_process, 1):
        logger.info(f"[{i}/{len(to_process)}] Processing: {book_dir.name}")
        logger.info(f"  Fixes needed: {', '.join(fixes_needed)}")

        stats = run_unified_quality_pipeline(
            book_dir,
            fixes_needed,
            use_llm=use_llm,
            validate_quality=validate_quality
        )

        if stats['error']:
            logger.warning(f"  Failed: {stats['error']}")
        else:
            # Log results
            fix_summary = []
            for fix_type in FIX_TYPES:
                if stats[fix_type] > 0:
                    fix_summary.append(f"{fix_type}: {stats[fix_type]}")
                    total_stats[fix_type] += stats[fix_type]

            if fix_summary:
                logger.info(f"  " + ", ".join(fix_summary))

            success += 1

        time.sleep(0.5)  # Brief pause between books

    elapsed = time.time() - start_time

    logger.info("=" * 60)
    logger.info(f"COMPLETE: {success}/{len(to_process)} books processed in {elapsed/60:.1f} minutes")
    for fix_type, count in total_stats.items():
        if count > 0:
            logger.info(f"  {fix_type}: {count}")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
