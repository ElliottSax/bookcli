#!/usr/bin/env python3
"""
⚠️  DEPRECATION NOTICE (2026-02-01) ⚠️
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
This file has been DEPRECATED. Use instead:

    lib/quality_dashboard.py

The quality dashboard provides comprehensive monitoring with better
visualization and real-time statistics.

New Usage:
    from lib.quality_dashboard import QualityDashboard

    dashboard = QualityDashboard(fiction_dir)
    dashboard.show()

Migration Guide: See REFACTORING_COMPLETE_2026_02.md
Quick Start: See REFACTORING_QUICK_START.md
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Monitor expansion progress and run quality agents when complete
"""

import os
import sys
import time
import subprocess
from pathlib import Path
from datetime import datetime

from lib.logging_config import setup_logging, get_logger

FICTION_DIR = Path("/mnt/e/projects/bookcli/output/fiction")
BOOKS_DIR = Path("/mnt/e/projects/bookcli/output/books")
TARGET_WORDS = 30000

setup_logging()
logger = get_logger(__name__)

def count_books_status():
    """Count books at target vs remaining"""
    fic_done = fic_total = nf_done = nf_total = 0

    for d in FICTION_DIR.iterdir():
        if d.is_dir():
            chapters = list(d.glob("chapter_*.md"))
            if chapters:
                fic_total += 1
                words = sum(len(c.read_text().split()) for c in chapters)
                if words >= TARGET_WORDS:
                    fic_done += 1

    for d in BOOKS_DIR.iterdir():
        if d.is_dir():
            chapters = list(d.glob("chapter_*.md"))
            if chapters:
                nf_total += 1
                words = sum(len(c.read_text().split()) for c in chapters)
                if words >= TARGET_WORDS:
                    nf_done += 1

    return {
        'fiction_done': fic_done,
        'fiction_total': fic_total,
        'nonfiction_done': nf_done,
        'nonfiction_total': nf_total,
        'remaining': (fic_total - fic_done) + (nf_total - nf_done)
    }

def run_quality_agents():
    """Run EXHAUSTIVE quality improvement pipeline on all books"""
    logger.info("=" * 60)
    logger.info("STARTING EXHAUSTIVE QUALITY PIPELINE")
    logger.info("=" * 60)

    base_dir = Path("/mnt/e/projects/bookcli")
    env = os.environ.copy()
    # API key should be set in environment - don't hardcode

    # Full quality pipeline in optimal order:
    quality_phases = [
        # Phase 1: Content Quality
        ("ai_ism_fixer.py", "AI-ism Removal"),
        ("dialogue_improver.py", "Dialogue Enhancement"),
        ("prose_polisher.py", "Prose Polish"),

        # Phase 2: Structure Quality
        ("pacing_improver.py", "Pacing Improvement"),
        ("ending_improver.py", "Ending Enhancement"),

        # Phase 3: Deep Fixes
        ("fix_quality_issues.py", "Quality Issues Fix"),
        ("book_fixer.py", "Book Fixer"),

        # Phase 4: Final Polish
        ("final_polish.py", "Final Polish"),
        ("markup_meta_cleaner.py", "Markup Cleanup"),
    ]

    # Filter to scripts that exist
    available = [(s, n) for s, n in quality_phases if (base_dir / s).exists()]
    logger.info(f"Running {len(available)} quality scripts in sequence:")
    for script, name in available:
        logger.info(f"  - {name} ({script})")

    # Run each phase sequentially for best results
    for script, name in available:
        logger.info(f"\n{'='*40}")
        logger.info(f"PHASE: {name}")
        logger.info(f"{'='*40}")

        script_path = base_dir / script
        try:
            result = subprocess.run(
                ["/mnt/e/projects/pod/venv/bin/python3", str(script_path)],
                env=env,
                cwd=str(base_dir),
                timeout=7200,  # 2 hour timeout per script
                capture_output=True,
                text=True
            )
            logger.info(f"{name}: Completed (exit code {result.returncode})")
            if result.returncode != 0:
                logger.warning(f"  stderr: {result.stderr[:500] if result.stderr else 'none'}")
        except subprocess.TimeoutExpired:
            logger.warning(f"{name}: Timed out after 2 hours")
        except Exception as e:
            logger.error(f"{name}: Error - {e}")

        time.sleep(10)  # Brief pause between phases

    logger.info("\n" + "=" * 60)
    logger.info("QUALITY PIPELINE COMPLETE")
    logger.info("=" * 60)

def main():
    logger.info("=" * 60)
    logger.info("EXPANSION MONITOR STARTED")
    logger.info(f"Will check in 8 hours, then hourly if needed")
    logger.info("=" * 60)

    # Initial status
    status = count_books_status()
    logger.info(f"Initial: Fiction {status['fiction_done']}/{status['fiction_total']}, "
                f"Non-fiction {status['nonfiction_done']}/{status['nonfiction_total']}, "
                f"Remaining: {status['remaining']}")

    # Wait 8 hours for first check
    logger.info("Waiting 8 hours for first check...")
    time.sleep(8 * 60 * 60)  # 8 hours

    # Check loop
    while True:
        status = count_books_status()
        logger.info(f"Status: Fiction {status['fiction_done']}/{status['fiction_total']}, "
                    f"Non-fiction {status['nonfiction_done']}/{status['nonfiction_total']}, "
                    f"Remaining: {status['remaining']}")

        if status['remaining'] == 0:
            logger.info("ALL BOOKS EXPANDED TO TARGET!")
            run_quality_agents()
            break
        else:
            logger.info(f"{status['remaining']} books remaining. Checking again in 1 hour...")
            time.sleep(60 * 60)  # 1 hour

    logger.info("Monitor complete")

if __name__ == "__main__":
    main()
