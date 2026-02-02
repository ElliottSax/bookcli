#!/usr/bin/env python3
"""
Consolidated Quality Pipeline
==============================
Unified quality fix orchestration for all modes:
- Local: Process books in local directory
- Distributed: Sync from Oracle Cloud + process locally
- Batch: Parallel processing with state tracking

Consolidates functionality from:
- master_quality_pipeline.py
- unified_quality_pipeline.py
- quality_pipeline_manager.py
"""

import json
import shutil
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from datetime import datetime
from dataclasses import dataclass, asdict

from lib.logging_config import setup_logging, get_logger
from lib.backup import BackupManager
from lib.quality_scorer import QualityScorer
from lib.parallel_quality_processor import ParallelQualityProcessor

setup_logging()
logger = get_logger(__name__)


@dataclass
class PipelineState:
    """Track pipeline progress across runs."""
    mode: str  # local, distributed, batch
    started_at: str
    completed_books: List[str]
    failed_books: List[str]
    current_stage: str  # text, names, coherency, ai, quality, complete
    total_books: int
    completed_count: int

    def to_dict(self) -> Dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict) -> 'PipelineState':
        return cls(**data)

    @classmethod
    def load(cls, state_file: Path) -> Optional['PipelineState']:
        """Load state from JSON file."""
        if not state_file.exists():
            return None
        try:
            data = json.loads(state_file.read_text())
            return cls.from_dict(data)
        except Exception as e:
            logger.warning(f"Could not load state: {e}")
            return None

    def save(self, state_file: Path):
        """Save state to JSON file."""
        try:
            state_file.write_text(json.dumps(self.to_dict(), indent=2))
        except Exception as e:
            logger.error(f"Could not save state: {e}")


class QualityPipeline:
    """
    Base quality pipeline with common fix orchestration.

    Fix sequence:
    1. Text fixes (AI-isms, corruption, patterns)
    2. Name consistency fixes
    3. Coherency fixes (loops, duplicates)
    4. AI quality improvements
    5. Final quality validation
    """

    def __init__(self, fiction_dir: Path, mode: str = "local",
                 enable_backup: bool = True, parallel: bool = False):
        """
        Initialize quality pipeline.

        Args:
            fiction_dir: Directory containing book subdirectories
            mode: Pipeline mode (local, distributed, batch)
            enable_backup: Create backups before fixes
            parallel: Use parallel processing for batch operations
        """
        self.fiction_dir = Path(fiction_dir)
        self.mode = mode
        self.enable_backup = enable_backup
        self.parallel = parallel

        self.state_file = self.fiction_dir / ".quality_pipeline_state.json"
        self.state = PipelineState.load(self.state_file)

        if enable_backup:
            self.backup_manager = BackupManager()

        self.scorer = QualityScorer()

        if parallel:
            self.parallel_processor = ParallelQualityProcessor()

    def get_books(self) -> List[Path]:
        """Get list of book directories to process."""
        if not self.fiction_dir.exists():
            logger.error(f"Fiction directory not found: {self.fiction_dir}")
            return []

        books = [
            d for d in self.fiction_dir.iterdir()
            if d.is_dir() and not d.name.startswith('.')
        ]

        logger.info(f"Found {len(books)} book directories")
        return books

    def should_process_book(self, book_dir: Path) -> bool:
        """Check if book should be processed based on state."""
        if not self.state:
            return True

        book_name = book_dir.name

        # Skip already completed books
        if book_name in self.state.completed_books:
            logger.info(f"Skipping {book_name} (already completed)")
            return False

        return True

    def create_backup(self, book_dir: Path, stage: str):
        """Create backup before applying fixes."""
        if not self.enable_backup:
            return

        try:
            self.backup_manager.create_backup(
                book_dir,
                description=f"Before {stage} fixes"
            )
            logger.info(f"  Backup created for {stage}")
        except Exception as e:
            logger.warning(f"  Backup creation failed: {e}")

    def run_text_fixes(self, book_dir: Path) -> bool:
        """
        Run text pattern fixes.

        Includes:
        - AI-ism removal
        - Corruption fixes
        - Text pattern cleanup
        """
        try:
            from fixers.text_fixer import fix_text_patterns
            from fixers.artifact_cleaner import clean_ai_artifacts
            from fixers.corruption_fixer import fix_corruption

            logger.info("Running text fixes...")
            self.create_backup(book_dir, "text_fixes")

            # Apply fixes
            fix_text_patterns(book_dir)
            clean_ai_artifacts(book_dir)
            fix_corruption(book_dir)

            return True
        except Exception as e:
            logger.error(f"Text fixes failed: {e}")
            return False

    def run_name_fixes(self, book_dir: Path) -> bool:
        """Run name consistency fixes."""
        try:
            from fixers.name_fixer import ensure_name_consistency

            logger.info("Running name fixes...")
            self.create_backup(book_dir, "name_fixes")

            ensure_name_consistency(book_dir)
            return True
        except Exception as e:
            logger.error(f"Name fixes failed: {e}")
            return False

    def run_coherency_fixes(self, book_dir: Path) -> bool:
        """Run coherency and loop detection fixes."""
        try:
            from fixers.coherency_fixer import fix_coherency_issues

            logger.info("Running coherency fixes...")
            self.create_backup(book_dir, "coherency_fixes")

            fix_coherency_issues(book_dir)
            return True
        except Exception as e:
            logger.error(f"Coherency fixes failed: {e}")
            return False

    def run_ai_quality_fixes(self, book_dir: Path) -> bool:
        """Run AI-based quality improvements."""
        try:
            from fixers.quality_fixer import improve_chapter_quality

            logger.info("Running AI quality fixes...")
            self.create_backup(book_dir, "ai_quality")

            improve_chapter_quality(book_dir)
            return True
        except Exception as e:
            logger.error(f"AI quality fixes failed: {e}")
            return False

    def validate_quality(self, book_dir: Path) -> Tuple[float, Dict]:
        """
        Validate book quality after fixes.

        Returns:
            (average_score, metrics_dict)
        """
        try:
            chapters = sorted(book_dir.glob("chapter_*.md"))
            if not chapters:
                return 0.0, {}

            scores = []
            for chapter_file in chapters:
                content = chapter_file.read_text()
                report = self.scorer.analyze(content)
                scores.append(report.score)

            avg_score = sum(scores) / len(scores)

            metrics = {
                "average_score": avg_score,
                "chapter_count": len(chapters),
                "min_score": min(scores),
                "max_score": max(scores)
            }

            return avg_score, metrics
        except Exception as e:
            logger.error(f"Quality validation failed: {e}")
            return 0.0, {}

    def process_book(self, book_dir: Path) -> bool:
        """
        Process single book through full quality pipeline.

        Returns:
            True if successful, False otherwise
        """
        logger.info("=" * 60)
        logger.info(f"Processing: {book_dir.name}")
        logger.info("=" * 60)

        try:
            # Get baseline quality
            score_before, _ = self.validate_quality(book_dir)
            logger.info(f"Quality before fixes: {score_before:.1f}/100")

            # Run fix sequence
            stages = [
                ("text", self.run_text_fixes),
                ("names", self.run_name_fixes),
                ("coherency", self.run_coherency_fixes),
                ("ai_quality", self.run_ai_quality_fixes)
            ]

            for stage_name, stage_func in stages:
                logger.info(f"\nStage: {stage_name}")
                if not stage_func(book_dir):
                    logger.warning(f"  Stage {stage_name} had issues")

            # Validate final quality
            score_after, metrics = self.validate_quality(book_dir)
            logger.info(f"\nQuality after fixes: {score_after:.1f}/100")
            logger.info(f"Improvement: {score_after - score_before:+.1f} points")
            logger.info(f"Metrics: {metrics}")

            # Update state
            if self.state:
                self.state.completed_books.append(book_dir.name)
                self.state.completed_count += 1
                self.state.save(self.state_file)

            return True

        except Exception as e:
            logger.error(f"Book processing failed: {e}")

            if self.state:
                self.state.failed_books.append(book_dir.name)
                self.state.save(self.state_file)

            return False

    def run(self):
        """Run the quality pipeline."""
        logger.info(f"Starting Quality Pipeline ({self.mode} mode)")
        logger.info(f"Fiction directory: {self.fiction_dir}")

        books = self.get_books()
        if not books:
            logger.error("No books found to process")
            return

        # Initialize state if needed
        if not self.state:
            self.state = PipelineState(
                mode=self.mode,
                started_at=datetime.now().isoformat(),
                completed_books=[],
                failed_books=[],
                current_stage="text",
                total_books=len(books),
                completed_count=0
            )
            self.state.save(self.state_file)

        # Process books
        processed = 0
        for book_dir in books:
            if not self.should_process_book(book_dir):
                continue

            if self.process_book(book_dir):
                processed += 1

        # Final summary
        logger.info("\n" + "=" * 60)
        logger.info("PIPELINE COMPLETE")
        logger.info("=" * 60)
        logger.info(f"Books processed: {processed}/{len(books)}")
        logger.info(f"Completed: {len(self.state.completed_books)}")
        logger.info(f"Failed: {len(self.state.failed_books)}")

        if self.state.failed_books:
            logger.warning(f"Failed books: {', '.join(self.state.failed_books)}")


class DistributedPipeline(QualityPipeline):
    """
    Pipeline with Oracle Cloud synchronization.

    Extends base pipeline with:
    - Sync from Oracle Cloud before processing
    - Optional push back to cloud after processing
    """

    def __init__(self, fiction_dir: Path, oracle_host: Optional[str] = None,
                 sync_before: bool = True, sync_after: bool = False, **kwargs):
        """
        Initialize distributed pipeline.

        Args:
            fiction_dir: Local directory for books
            oracle_host: Oracle Cloud host for rsync
            sync_before: Sync from cloud before processing
            sync_after: Sync to cloud after processing
            **kwargs: Additional arguments for base pipeline
        """
        super().__init__(fiction_dir, mode="distributed", **kwargs)
        self.oracle_host = oracle_host
        self.sync_before = sync_before
        self.sync_after = sync_after

    def sync_from_oracle(self) -> bool:
        """Sync books from Oracle Cloud."""
        if not self.oracle_host:
            logger.warning("No Oracle host configured, skipping sync")
            return False

        try:
            logger.info(f"Syncing from Oracle: {self.oracle_host}")

            # Use rsync for efficient sync
            import subprocess
            cmd = [
                "rsync", "-avz", "--progress",
                f"{self.oracle_host}:/fiction/",
                str(self.fiction_dir) + "/"
            ]

            result = subprocess.run(cmd, capture_output=True, text=True)

            if result.returncode == 0:
                logger.info("Sync from Oracle successful")
                return True
            else:
                logger.error(f"Sync failed: {result.stderr}")
                return False

        except Exception as e:
            logger.error(f"Oracle sync error: {e}")
            return False

    def sync_to_oracle(self) -> bool:
        """Sync books to Oracle Cloud."""
        if not self.oracle_host:
            return False

        try:
            logger.info(f"Syncing to Oracle: {self.oracle_host}")

            import subprocess
            cmd = [
                "rsync", "-avz", "--progress",
                str(self.fiction_dir) + "/",
                f"{self.oracle_host}:/fiction/"
            ]

            result = subprocess.run(cmd, capture_output=True, text=True)

            if result.returncode == 0:
                logger.info("Sync to Oracle successful")
                return True
            else:
                logger.error(f"Sync failed: {result.stderr}")
                return False

        except Exception as e:
            logger.error(f"Oracle sync error: {e}")
            return False

    def run(self):
        """Run distributed pipeline with cloud sync."""
        # Sync from cloud first
        if self.sync_before:
            self.sync_from_oracle()

        # Run base pipeline
        super().run()

        # Sync back to cloud
        if self.sync_after:
            self.sync_to_oracle()


class BatchPipeline(QualityPipeline):
    """
    Parallel batch processing pipeline.

    Extends base pipeline with:
    - Parallel processing of multiple books
    - Progress tracking
    - Resource management
    """

    def __init__(self, fiction_dir: Path, max_workers: int = 4, **kwargs):
        """
        Initialize batch pipeline.

        Args:
            fiction_dir: Directory containing books
            max_workers: Maximum parallel workers
            **kwargs: Additional arguments for base pipeline
        """
        super().__init__(fiction_dir, mode="batch", parallel=True, **kwargs)
        self.max_workers = max_workers

    def run(self):
        """Run batch pipeline with parallel processing."""
        logger.info(f"Starting Batch Pipeline (parallel mode)")
        logger.info(f"Max workers: {self.max_workers}")

        books = self.get_books()
        if not books:
            logger.error("No books found to process")
            return

        # Filter books to process
        books_to_process = [
            book for book in books
            if self.should_process_book(book)
        ]

        logger.info(f"Processing {len(books_to_process)} books in parallel")

        # Use parallel processor
        if self.parallel_processor:
            results = self.parallel_processor.process_books(
                books_to_process,
                max_workers=self.max_workers
            )

            # Update state
            for book_dir, success in results.items():
                if success and self.state:
                    self.state.completed_books.append(book_dir.name)
                    self.state.completed_count += 1
                elif not success and self.state:
                    self.state.failed_books.append(book_dir.name)

            if self.state:
                self.state.save(self.state_file)

        # Summary
        logger.info("\n" + "=" * 60)
        logger.info("BATCH PIPELINE COMPLETE")
        logger.info("=" * 60)
        if self.state:
            logger.info(f"Completed: {len(self.state.completed_books)}")
            logger.info(f"Failed: {len(self.state.failed_books)}")


def main():
    """CLI entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Consolidated Quality Pipeline")
    parser.add_argument("--mode", choices=["local", "distributed", "batch"],
                       default="local", help="Pipeline mode")
    parser.add_argument("--fiction-dir", type=str,
                       default="/mnt/e/projects/bookcli/output/fiction",
                       help="Fiction directory")
    parser.add_argument("--oracle-host", type=str,
                       help="Oracle host for distributed mode")
    parser.add_argument("--no-backup", action="store_true",
                       help="Disable backups")
    parser.add_argument("--max-workers", type=int, default=4,
                       help="Max workers for batch mode")

    args = parser.parse_args()

    fiction_dir = Path(args.fiction_dir)

    if args.mode == "local":
        pipeline = QualityPipeline(
            fiction_dir,
            enable_backup=not args.no_backup
        )
    elif args.mode == "distributed":
        pipeline = DistributedPipeline(
            fiction_dir,
            oracle_host=args.oracle_host,
            enable_backup=not args.no_backup
        )
    elif args.mode == "batch":
        pipeline = BatchPipeline(
            fiction_dir,
            max_workers=args.max_workers,
            enable_backup=not args.no_backup
        )

    pipeline.run()


if __name__ == "__main__":
    main()
