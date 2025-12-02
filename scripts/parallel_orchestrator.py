#!/usr/bin/env python3
"""
Parallel Orchestrator for Concurrent Chapter Generation
Phase 4, Priority 1.1: Async/Parallel Generation

Speeds up book generation by processing multiple chapters concurrently
while maintaining quality through the Phase 3 iterative system.
"""

import asyncio
import json
import time
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor
import threading

# Import base orchestrator
from orchestrator import BookOrchestrator


@dataclass
class ChapterTask:
    """Represents a chapter generation task"""
    chapter_num: int
    status: str  # 'pending', 'running', 'completed', 'failed'
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    error: Optional[str] = None
    retry_count: int = 0
    word_count: Optional[int] = None


class RateLimiter:
    """Rate limiter for API calls"""

    def __init__(self, max_calls: int, period_seconds: int):
        self.max_calls = max_calls
        self.period_seconds = period_seconds
        self.calls = []
        self.lock = threading.Lock()

    async def acquire(self):
        """Wait if necessary to respect rate limits"""
        while True:
            now = time.time()
            with self.lock:
                # Remove old calls outside the period
                self.calls = [t for t in self.calls if now - t < self.period_seconds]

                if len(self.calls) < self.max_calls:
                    self.calls.append(now)
                    return

            # Wait before checking again
            await asyncio.sleep(0.1)


class ProgressTracker:
    """Tracks generation progress across all chapters"""

    def __init__(self, total_chapters: int):
        self.total_chapters = total_chapters
        self.tasks: Dict[int, ChapterTask] = {}
        self.lock = threading.Lock()
        self.start_time = time.time()

    def update_task(self, chapter_num: int, **kwargs):
        """Update task status"""
        with self.lock:
            if chapter_num not in self.tasks:
                self.tasks[chapter_num] = ChapterTask(chapter_num=chapter_num, status='pending')

            for key, value in kwargs.items():
                setattr(self.tasks[chapter_num], key, value)

    def get_progress(self) -> Dict:
        """Get current progress statistics"""
        with self.lock:
            completed = sum(1 for t in self.tasks.values() if t.status == 'completed')
            running = sum(1 for t in self.tasks.values() if t.status == 'running')
            failed = sum(1 for t in self.tasks.values() if t.status == 'failed')
            pending = self.total_chapters - completed - running - failed

            elapsed = time.time() - self.start_time

            # Calculate ETA
            if completed > 0:
                avg_time_per_chapter = elapsed / completed
                remaining = self.total_chapters - completed
                eta_seconds = avg_time_per_chapter * remaining
            else:
                eta_seconds = None

            return {
                'total': self.total_chapters,
                'completed': completed,
                'running': running,
                'failed': failed,
                'pending': pending,
                'elapsed_seconds': elapsed,
                'eta_seconds': eta_seconds,
                'tasks': dict(self.tasks)
            }

    def print_progress(self):
        """Print formatted progress bar"""
        progress = self.get_progress()

        completed = progress['completed']
        total = progress['total']
        percentage = (completed / total * 100) if total > 0 else 0

        # Progress bar
        bar_length = 40
        filled = int(bar_length * completed / total)
        bar = '█' * filled + '░' * (bar_length - filled)

        # Time formatting
        elapsed = time.strftime('%H:%M:%S', time.gmtime(progress['elapsed_seconds']))
        if progress['eta_seconds']:
            eta = time.strftime('%H:%M:%S', time.gmtime(progress['eta_seconds']))
        else:
            eta = 'calculating...'

        # Status line
        status_line = f"\r[{bar}] {percentage:.1f}% | "
        status_line += f"✓ {completed} | ⟳ {progress['running']} | ✗ {progress['failed']} | "
        status_line += f"Elapsed: {elapsed} | ETA: {eta}"

        print(status_line, end='', flush=True)


class AsyncBookOrchestrator(BookOrchestrator):
    """
    Async version of BookOrchestrator with parallel generation capability

    Extends the base orchestrator to support concurrent chapter generation
    while maintaining all quality features from Phase 1-3.
    """

    def __init__(self, *args,
                 max_concurrent: int = 3,
                 rate_limit_calls: int = 100,
                 rate_limit_period: int = 3600,
                 **kwargs):
        """
        Initialize async orchestrator

        Args:
            max_concurrent: Maximum chapters to generate simultaneously
            rate_limit_calls: Maximum API calls allowed
            rate_limit_period: Period for rate limit (seconds)
            *args, **kwargs: Passed to parent BookOrchestrator
        """
        super().__init__(*args, **kwargs)

        self.max_concurrent = max_concurrent
        self.rate_limiter = RateLimiter(rate_limit_calls, rate_limit_period)
        self.progress_tracker = None
        self.executor = ThreadPoolExecutor(max_workers=max_concurrent)

        self._log(f"Async orchestrator initialized with {max_concurrent} concurrent workers")

    async def generate_chapter_async(self, chapter_num: int, chapter_plan: dict,
                                    context: dict, max_retries: int = 3) -> bool:
        """
        Async wrapper for chapter generation

        Uses ThreadPoolExecutor to run synchronous generation in thread pool
        while maintaining async interface.
        """
        # Update progress
        self.progress_tracker.update_task(chapter_num, status='running', start_time=time.time())
        self.progress_tracker.print_progress()

        try:
            # Acquire rate limit token
            await self.rate_limiter.acquire()

            # Run synchronous generation in thread pool
            loop = asyncio.get_event_loop()

            # Create a partial function with all needed arguments
            generate_fn = lambda: self._generate_chapter_sync(
                chapter_num, chapter_plan, context, max_retries
            )

            # Run in executor
            success = await loop.run_in_executor(self.executor, generate_fn)

            if success:
                # Get word count if file exists
                chapter_file = self.chapters_dir / f"chapter_{chapter_num:03d}.md"
                if chapter_file.exists():
                    word_count = len(chapter_file.read_text().split())
                else:
                    word_count = None

                self.progress_tracker.update_task(
                    chapter_num,
                    status='completed',
                    end_time=time.time(),
                    word_count=word_count
                )
            else:
                self.progress_tracker.update_task(
                    chapter_num,
                    status='failed',
                    end_time=time.time(),
                    error='Generation failed'
                )

            self.progress_tracker.print_progress()
            return success

        except Exception as e:
            self._log(f"Async generation error for chapter {chapter_num}: {str(e)}", "ERROR")
            self.progress_tracker.update_task(
                chapter_num,
                status='failed',
                end_time=time.time(),
                error=str(e)
            )
            self.progress_tracker.print_progress()
            return False

    def _generate_chapter_sync(self, chapter_num: int, chapter_plan: dict,
                              context: dict, max_retries: int) -> bool:
        """
        Synchronous chapter generation (runs in thread pool)

        This is the actual generation logic that will run in parallel.
        Uses the Phase 3 iterative system for quality.
        """
        try:
            # Use the parent class generation methods
            # This will automatically use iterative mode if available
            if self.use_api:
                # Check which mode to use
                if self.multi_pass_attempts > 1 and self.scorer:
                    return self._generate_chapter_multipass(
                        chapter_num, chapter_plan, context, max_retries
                    )
                elif self.detail_analyzer and self.word_count_enforcer:
                    return self._generate_chapter_iterative(
                        chapter_num, chapter_plan, context, max_retries
                    )
                else:
                    prompt = self._create_chapter_prompt(chapter_num, chapter_plan, context)
                    return self._generate_chapter_with_api(chapter_num, prompt, max_retries)
            else:
                # Prompt-only mode
                prompt = self._create_chapter_prompt(chapter_num, chapter_plan, context)
                prompt_file = self.workspace / f"prompt_ch{chapter_num}.md"
                prompt_file.write_text(prompt)
                return True

        except Exception as e:
            self._log(f"Sync generation error for chapter {chapter_num}: {str(e)}", "ERROR")
            return False

    async def generate_chapters_parallel(self, chapter_numbers: List[int],
                                        resume: bool = True) -> Dict:
        """
        Generate multiple chapters in parallel

        Args:
            chapter_numbers: List of chapter numbers to generate
            resume: Skip chapters that already exist

        Returns:
            Dictionary with generation results
        """
        # Load chapter plan
        plan_file = self.analysis_dir / "chapter_plan.json"
        if not plan_file.exists():
            self._log("Chapter plan not found, creating basic plan", "WARN")
            self.create_chapter_plan()

        plan = json.loads(plan_file.read_text())

        # Filter chapters to generate
        chapters_to_generate = []
        for chapter_num in chapter_numbers:
            chapter_file = self.chapters_dir / f"chapter_{chapter_num:03d}.md"
            if resume and chapter_file.exists():
                self._log(f"Skipping chapter {chapter_num} (already exists)")
            else:
                chapters_to_generate.append(chapter_num)

        if not chapters_to_generate:
            self._log("All chapters already generated")
            return {'generated': [], 'skipped': chapter_numbers}

        # Initialize progress tracker
        self.progress_tracker = ProgressTracker(len(chapters_to_generate))

        self._log(f"\n{'='*60}")
        self._log(f"PARALLEL GENERATION: {len(chapters_to_generate)} chapters")
        self._log(f"Concurrency: {self.max_concurrent} simultaneous")
        self._log(f"Chapters: {chapters_to_generate}")
        self._log(f"{'='*60}\n")

        start_time = time.time()

        # Create semaphore for concurrency limit
        semaphore = asyncio.Semaphore(self.max_concurrent)

        async def generate_with_semaphore(chapter_num: int):
            async with semaphore:
                # Get context and plan for this chapter
                chapter_plan = plan["chapters"][chapter_num - 1]

                # Get context from continuity tracker
                context = {}  # Simplified for async demo

                return await self.generate_chapter_async(
                    chapter_num, chapter_plan, context
                )

        # Generate all chapters concurrently (limited by semaphore)
        tasks = [generate_with_semaphore(num) for num in chapters_to_generate]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Process results
        generated = []
        failed = []
        for chapter_num, result in zip(chapters_to_generate, results):
            if isinstance(result, Exception):
                failed.append((chapter_num, str(result)))
            elif result:
                generated.append(chapter_num)
            else:
                failed.append((chapter_num, "Generation returned False"))

        # Final progress
        print()  # New line after progress bar

        elapsed = time.time() - start_time
        self._log(f"\n{'='*60}")
        self._log(f"PARALLEL GENERATION COMPLETE")
        self._log(f"Time: {time.strftime('%H:%M:%S', time.gmtime(elapsed))}")
        self._log(f"Generated: {len(generated)} chapters")
        self._log(f"Failed: {len(failed)} chapters")

        if generated:
            # Calculate statistics
            avg_time = elapsed / len(generated) if generated else 0
            self._log(f"Average time per chapter: {avg_time:.1f} seconds")

            # Show word counts
            total_words = 0
            for chapter_num in generated:
                chapter_file = self.chapters_dir / f"chapter_{chapter_num:03d}.md"
                if chapter_file.exists():
                    words = len(chapter_file.read_text().split())
                    total_words += words

            self._log(f"Total words generated: {total_words:,}")

            # Calculate cost if using API
            if self.use_api and self.total_cost > 0:
                self._log(f"Total cost: ${self.total_cost:.2f}")
                self._log(f"Average cost per chapter: ${self.total_cost/len(generated):.4f}")

        if failed:
            self._log("\nFailed chapters:")
            for chapter_num, error in failed:
                self._log(f"  Chapter {chapter_num}: {error}")

        self._log(f"{'='*60}\n")

        return {
            'generated': generated,
            'failed': failed,
            'elapsed_seconds': elapsed,
            'total_words': total_words if generated else 0,
            'total_cost': self.total_cost
        }

    async def generate_all_chapters_async(self, resume: bool = True):
        """
        Generate all chapters in the book using parallel processing

        This replaces generate_all_chapters() with an async version.
        """
        # Load plan to get total chapters
        plan = json.loads((self.analysis_dir / "chapter_plan.json").read_text())
        total_chapters = plan["total_chapters"]

        # Generate chapter list
        chapter_numbers = list(range(1, total_chapters + 1))

        # Run parallel generation
        results = await self.generate_chapters_parallel(chapter_numbers, resume)

        # Update status
        status = self._load_status()
        status["chapters_completed"] = len(results['generated'])
        status["parallel_generation"] = True
        status["generation_time_seconds"] = results['elapsed_seconds']
        self._save_status(status)

        return results


async def compare_performance():
    """
    Compare sequential vs parallel generation performance
    """
    print("="*60)
    print("PERFORMANCE COMPARISON: Sequential vs Parallel")
    print("="*60)

    # Test configuration
    test_chapters = [1, 2, 3, 4, 5]  # Generate 5 chapters

    # Test source
    test_source = Path("test_parallel_source.txt")
    test_source.write_text("""
    Test book for parallel generation.
    Chapter 1: Introduction
    Chapter 2: Development
    Chapter 3: Conflict
    Chapter 4: Resolution
    Chapter 5: Conclusion
    """)

    # Sequential generation
    print("\n--- SEQUENTIAL GENERATION ---")
    start_time = time.time()

    seq_orchestrator = BookOrchestrator(
        source_file=test_source,
        book_name="test-sequential",
        genre="fantasy",
        target_words=20000,
        test_first=False,
        use_api=False
    )

    # Create basic plan
    seq_orchestrator.analyze_source()
    seq_orchestrator.create_chapter_plan()

    # Generate chapters sequentially
    for chapter_num in test_chapters:
        seq_orchestrator.generate_chapter(chapter_num)

    seq_time = time.time() - start_time
    print(f"Sequential time: {seq_time:.2f} seconds")

    # Parallel generation
    print("\n--- PARALLEL GENERATION ---")
    start_time = time.time()

    async_orchestrator = AsyncBookOrchestrator(
        source_file=test_source,
        book_name="test-parallel",
        genre="fantasy",
        target_words=20000,
        test_first=False,
        use_api=False,
        max_concurrent=3
    )

    # Create basic plan
    async_orchestrator.analyze_source()
    async_orchestrator.create_chapter_plan()

    # Generate chapters in parallel
    await async_orchestrator.generate_chapters_parallel(test_chapters, resume=False)

    parallel_time = time.time() - start_time
    print(f"Parallel time: {parallel_time:.2f} seconds")

    # Results
    print("\n" + "="*60)
    print("RESULTS")
    print("="*60)
    print(f"Sequential: {seq_time:.2f}s")
    print(f"Parallel:   {parallel_time:.2f}s")
    print(f"Speedup:    {seq_time/parallel_time:.2f}x")
    print(f"Time saved: {seq_time - parallel_time:.2f}s ({(1 - parallel_time/seq_time)*100:.1f}%)")

    # Cleanup
    test_source.unlink()
    import shutil
    for workspace in ["test-sequential", "test-parallel"]:
        path = Path("workspace") / workspace
        if path.exists():
            shutil.rmtree(path)


def main():
    """
    Demo async parallel generation
    """
    import argparse

    parser = argparse.ArgumentParser(description="Parallel Book Generation")
    parser.add_argument("--source", help="Source file path")
    parser.add_argument("--book-name", help="Book name")
    parser.add_argument("--chapters", nargs="+", type=int, help="Specific chapters to generate")
    parser.add_argument("--max-concurrent", type=int, default=3, help="Max concurrent generations")
    parser.add_argument("--compare", action="store_true", help="Run performance comparison")

    args = parser.parse_args()

    if args.compare:
        # Run performance comparison
        asyncio.run(compare_performance())
    elif args.source and args.book_name:
        # Run parallel generation
        orchestrator = AsyncBookOrchestrator(
            source_file=args.source,
            book_name=args.book_name,
            genre="fantasy",
            test_first=False,
            use_api=False,
            max_concurrent=args.max_concurrent
        )

        if args.chapters:
            # Generate specific chapters
            asyncio.run(orchestrator.generate_chapters_parallel(args.chapters))
        else:
            # Generate all chapters
            asyncio.run(orchestrator.generate_all_chapters_async())
    else:
        print("Usage:")
        print("  Compare performance:  python3 parallel_orchestrator.py --compare")
        print("  Generate chapters:    python3 parallel_orchestrator.py --source file.txt --book-name mybook")
        print("  Specific chapters:    python3 parallel_orchestrator.py --source file.txt --book-name mybook --chapters 1 2 3")


if __name__ == "__main__":
    main()