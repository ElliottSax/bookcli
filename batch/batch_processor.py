"""
Batch Processing System for Book Factory
Enables parallel generation of multiple books with resource optimization
"""

import json
import logging
import asyncio
import concurrent.futures
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple, Callable
from dataclasses import dataclass, asdict
from datetime import datetime
from enum import Enum
import multiprocessing
import queue
import threading
import time
import psutil
import sqlite3

logger = logging.getLogger(__name__)


class JobStatus(Enum):
    """Job status states."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    RETRYING = "retrying"


class JobPriority(Enum):
    """Job priority levels."""
    LOW = 0
    NORMAL = 1
    HIGH = 2
    CRITICAL = 3


@dataclass
class BatchJob:
    """Batch processing job."""
    job_id: str
    book_title: str
    genre: str
    outline: str

    # Configuration
    target_words: int = 30000
    chapters: int = 20
    quality_level: str = "high"

    # Scheduling
    priority: JobPriority = JobPriority.NORMAL
    status: JobStatus = JobStatus.PENDING
    created_at: str = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None

    # Progress
    current_chapter: int = 0
    progress_percentage: float = 0.0

    # Results
    output_path: Optional[Path] = None
    quality_score: Optional[float] = None
    generation_cost: Optional[float] = None
    error_message: Optional[str] = None

    # Metadata
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()
        if self.metadata is None:
            self.metadata = {}


class BatchProcessor:
    """
    Batch processing system for parallel book generation.
    Features:
    - Parallel job execution
    - Resource management
    - Priority queuing
    - Progress tracking
    - Auto-scaling
    - Failure recovery
    """

    def __init__(
        self,
        workspace: Path,
        max_workers: Optional[int] = None,
        max_memory_gb: float = 4.0,
        enable_gpu: bool = False
    ):
        """
        Initialize batch processor.

        Args:
            workspace: Working directory
            max_workers: Maximum parallel workers (auto-detect if None)
            max_memory_gb: Maximum memory usage
            enable_gpu: Enable GPU acceleration if available
        """
        self.workspace = Path(workspace)
        self.workspace.mkdir(parents=True, exist_ok=True)

        # Resource limits
        self.max_workers = max_workers or self._calculate_optimal_workers()
        self.max_memory_gb = max_memory_gb
        self.enable_gpu = enable_gpu

        # Job management
        self.job_queue = queue.PriorityQueue()
        self.active_jobs: Dict[str, BatchJob] = {}
        self.completed_jobs: Dict[str, BatchJob] = {}
        self.failed_jobs: Dict[str, BatchJob] = {}

        # Database
        self.db_path = self.workspace / "batch_jobs.db"
        self._init_database()

        # Thread pool for parallel execution
        self.executor = concurrent.futures.ThreadPoolExecutor(
            max_workers=self.max_workers
        )

        # Monitoring
        self.monitor_thread = None
        self.stop_monitoring = threading.Event()
        self.stats = {
            'total_jobs': 0,
            'completed': 0,
            'failed': 0,
            'total_words': 0,
            'total_cost': 0.0,
            'average_quality': 0.0
        }

    def _init_database(self):
        """Initialize job tracking database."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS batch_jobs (
                job_id TEXT PRIMARY KEY,
                book_title TEXT NOT NULL,
                genre TEXT NOT NULL,
                status TEXT NOT NULL,
                priority INTEGER DEFAULT 1,
                created_at TEXT NOT NULL,
                started_at TEXT,
                completed_at TEXT,
                progress REAL DEFAULT 0.0,
                output_path TEXT,
                quality_score REAL,
                generation_cost REAL,
                error_message TEXT,
                data JSON NOT NULL
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS batch_stats (
                stat_date TEXT PRIMARY KEY,
                total_jobs INTEGER DEFAULT 0,
                completed_jobs INTEGER DEFAULT 0,
                failed_jobs INTEGER DEFAULT 0,
                total_words INTEGER DEFAULT 0,
                total_cost REAL DEFAULT 0.0,
                average_quality REAL DEFAULT 0.0,
                average_time_minutes REAL DEFAULT 0.0
            )
        """)

        conn.commit()
        conn.close()

    def submit_job(
        self,
        book_title: str,
        genre: str,
        outline: str,
        priority: JobPriority = JobPriority.NORMAL,
        **kwargs
    ) -> BatchJob:
        """
        Submit a new batch job.

        Args:
            book_title: Book title
            genre: Book genre
            outline: Book outline
            priority: Job priority
            **kwargs: Additional job parameters

        Returns:
            BatchJob object
        """
        job = BatchJob(
            job_id=self._generate_job_id(),
            book_title=book_title,
            genre=genre,
            outline=outline,
            priority=priority,
            **kwargs
        )

        # Add to queue
        self.job_queue.put((-priority.value, job.created_at, job))

        # Save to database
        self._save_job(job)

        # Update stats
        self.stats['total_jobs'] += 1

        logger.info(f"Submitted job {job.job_id}: {book_title}")
        return job

    def submit_batch(
        self,
        jobs_data: List[Dict[str, Any]],
        priority: JobPriority = JobPriority.NORMAL
    ) -> List[BatchJob]:
        """
        Submit multiple jobs at once.

        Args:
            jobs_data: List of job specifications
            priority: Default priority for all jobs

        Returns:
            List of BatchJob objects
        """
        jobs = []

        for job_spec in jobs_data:
            job = self.submit_job(
                book_title=job_spec.get('title', 'Untitled'),
                genre=job_spec.get('genre', 'general'),
                outline=job_spec.get('outline', ''),
                priority=job_spec.get('priority', priority),
                target_words=job_spec.get('target_words', 30000),
                chapters=job_spec.get('chapters', 20)
            )
            jobs.append(job)

        logger.info(f"Submitted batch of {len(jobs)} jobs")
        return jobs

    def process_jobs(
        self,
        generator_func: Callable,
        max_concurrent: Optional[int] = None
    ):
        """
        Process jobs in the queue.

        Args:
            generator_func: Function to generate books
            max_concurrent: Maximum concurrent jobs
        """
        max_concurrent = max_concurrent or self.max_workers

        # Start monitoring
        self._start_monitoring()

        # Process jobs
        futures = []

        while not self.job_queue.empty() or futures:
            # Submit new jobs up to limit
            while len(futures) < max_concurrent and not self.job_queue.empty():
                try:
                    _, _, job = self.job_queue.get_nowait()
                    future = self.executor.submit(
                        self._process_single_job,
                        job,
                        generator_func
                    )
                    futures.append((future, job))
                except queue.Empty:
                    break

            # Check completed futures
            completed = []
            for future, job in futures:
                if future.done():
                    completed.append((future, job))

                    try:
                        result = future.result()
                        self.completed_jobs[job.job_id] = job
                        self.stats['completed'] += 1
                        logger.info(f"Completed job {job.job_id}")
                    except Exception as e:
                        job.status = JobStatus.FAILED
                        job.error_message = str(e)
                        self.failed_jobs[job.job_id] = job
                        self.stats['failed'] += 1
                        logger.error(f"Job {job.job_id} failed: {e}")

            # Remove completed futures
            for item in completed:
                futures.remove(item)

            # Brief sleep to prevent CPU spinning
            time.sleep(0.1)

        # Stop monitoring
        self._stop_monitoring()

        logger.info("Batch processing complete")

    async def process_jobs_async(
        self,
        generator_func: Callable,
        max_concurrent: int = 5
    ):
        """
        Process jobs asynchronously.

        Args:
            generator_func: Async function to generate books
            max_concurrent: Maximum concurrent jobs
        """
        semaphore = asyncio.Semaphore(max_concurrent)
        tasks = []

        while not self.job_queue.empty():
            try:
                _, _, job = self.job_queue.get_nowait()
                task = asyncio.create_task(
                    self._process_job_async(job, generator_func, semaphore)
                )
                tasks.append(task)
            except queue.Empty:
                break

        # Wait for all tasks
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Process results
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Async job failed: {result}")
                self.stats['failed'] += 1
            else:
                self.stats['completed'] += 1

        logger.info(f"Async batch processing complete: {len(results)} jobs")

    def get_job_status(self, job_id: str) -> Optional[BatchJob]:
        """
        Get status of a specific job.

        Args:
            job_id: Job identifier

        Returns:
            BatchJob or None
        """
        # Check active jobs
        if job_id in self.active_jobs:
            return self.active_jobs[job_id]

        # Check completed jobs
        if job_id in self.completed_jobs:
            return self.completed_jobs[job_id]

        # Check failed jobs
        if job_id in self.failed_jobs:
            return self.failed_jobs[job_id]

        # Check database
        return self._load_job(job_id)

    def get_batch_status(self) -> Dict[str, Any]:
        """
        Get overall batch processing status.

        Returns:
            Status dictionary
        """
        return {
            'queued': self.job_queue.qsize(),
            'active': len(self.active_jobs),
            'completed': len(self.completed_jobs),
            'failed': len(self.failed_jobs),
            'stats': self.stats,
            'resources': {
                'workers': self.max_workers,
                'memory_usage_gb': self._get_memory_usage(),
                'cpu_usage_percent': psutil.cpu_percent()
            }
        }

    def cancel_job(self, job_id: str) -> bool:
        """
        Cancel a pending or running job.

        Args:
            job_id: Job identifier

        Returns:
            Success status
        """
        # Find job in queue
        temp_queue = []
        cancelled = False

        while not self.job_queue.empty():
            priority, timestamp, job = self.job_queue.get()
            if job.job_id == job_id:
                job.status = JobStatus.CANCELLED
                self._save_job(job)
                cancelled = True
                logger.info(f"Cancelled job {job_id}")
            else:
                temp_queue.append((priority, timestamp, job))

        # Restore queue
        for item in temp_queue:
            self.job_queue.put(item)

        # Cancel if running
        if job_id in self.active_jobs:
            # Note: Actual cancellation depends on generator implementation
            self.active_jobs[job_id].status = JobStatus.CANCELLED
            cancelled = True

        return cancelled

    def retry_failed_jobs(self) -> int:
        """
        Retry all failed jobs.

        Returns:
            Number of jobs retried
        """
        retried = 0

        for job_id, job in list(self.failed_jobs.items()):
            job.status = JobStatus.RETRYING
            job.error_message = None

            # Re-queue job
            self.job_queue.put((-job.priority.value, job.created_at, job))

            # Remove from failed list
            del self.failed_jobs[job_id]

            retried += 1
            logger.info(f"Retrying job {job_id}")

        return retried

    def optimize_resources(self):
        """Optimize resource allocation based on current load."""
        # Get system resources
        cpu_count = psutil.cpu_count()
        memory_available = psutil.virtual_memory().available / (1024**3)  # GB

        # Calculate optimal workers
        cpu_based = cpu_count - 1  # Leave one core free
        memory_based = int(memory_available / 0.5)  # 0.5GB per worker

        optimal = min(cpu_based, memory_based, 10)  # Cap at 10

        if optimal != self.max_workers:
            logger.info(f"Adjusting workers from {self.max_workers} to {optimal}")
            self.max_workers = optimal

            # Recreate executor with new worker count
            self.executor.shutdown(wait=False)
            self.executor = concurrent.futures.ThreadPoolExecutor(
                max_workers=self.max_workers
            )

    def _process_single_job(
        self,
        job: BatchJob,
        generator_func: Callable
    ) -> BatchJob:
        """Process a single job."""
        try:
            # Update status
            job.status = JobStatus.RUNNING
            job.started_at = datetime.now().isoformat()
            self.active_jobs[job.job_id] = job
            self._save_job(job)

            # Generate book
            result = generator_func(
                title=job.book_title,
                genre=job.genre,
                outline=job.outline,
                target_words=job.target_words,
                chapters=job.chapters,
                progress_callback=lambda p: self._update_progress(job.job_id, p)
            )

            # Update job with results
            job.status = JobStatus.COMPLETED
            job.completed_at = datetime.now().isoformat()
            job.output_path = result.get('output_path')
            job.quality_score = result.get('quality_score')
            job.generation_cost = result.get('cost')
            job.progress_percentage = 100.0

            # Update stats
            if job.quality_score:
                self.stats['average_quality'] = (
                    (self.stats['average_quality'] * self.stats['completed'] +
                     job.quality_score) / (self.stats['completed'] + 1)
                )
            if job.generation_cost:
                self.stats['total_cost'] += job.generation_cost

            # Save and cleanup
            self._save_job(job)
            del self.active_jobs[job.job_id]

            return job

        except Exception as e:
            job.status = JobStatus.FAILED
            job.error_message = str(e)
            job.completed_at = datetime.now().isoformat()
            self._save_job(job)

            if job.job_id in self.active_jobs:
                del self.active_jobs[job.job_id]

            raise

    async def _process_job_async(
        self,
        job: BatchJob,
        generator_func: Callable,
        semaphore: asyncio.Semaphore
    ) -> BatchJob:
        """Process job asynchronously."""
        async with semaphore:
            try:
                job.status = JobStatus.RUNNING
                job.started_at = datetime.now().isoformat()

                # Run generator
                result = await generator_func(
                    title=job.book_title,
                    genre=job.genre,
                    outline=job.outline,
                    target_words=job.target_words,
                    chapters=job.chapters
                )

                job.status = JobStatus.COMPLETED
                job.completed_at = datetime.now().isoformat()
                job.output_path = result.get('output_path')
                job.quality_score = result.get('quality_score')
                job.generation_cost = result.get('cost')

                self._save_job(job)
                return job

            except Exception as e:
                job.status = JobStatus.FAILED
                job.error_message = str(e)
                self._save_job(job)
                raise

    def _update_progress(self, job_id: str, progress: float):
        """Update job progress."""
        if job_id in self.active_jobs:
            self.active_jobs[job_id].progress_percentage = progress

    def _calculate_optimal_workers(self) -> int:
        """Calculate optimal number of workers."""
        cpu_count = psutil.cpu_count()
        memory_gb = psutil.virtual_memory().total / (1024**3)

        # Basic heuristic: 1 worker per 2 CPUs, max 1 per 2GB RAM
        cpu_based = max(1, cpu_count // 2)
        memory_based = max(1, int(memory_gb // 2))

        return min(cpu_based, memory_based, 8)  # Cap at 8

    def _get_memory_usage(self) -> float:
        """Get current memory usage in GB."""
        process = psutil.Process()
        return process.memory_info().rss / (1024**3)

    def _start_monitoring(self):
        """Start resource monitoring thread."""
        self.stop_monitoring.clear()
        self.monitor_thread = threading.Thread(target=self._monitor_resources)
        self.monitor_thread.start()

    def _stop_monitoring(self):
        """Stop resource monitoring."""
        self.stop_monitoring.set()
        if self.monitor_thread:
            self.monitor_thread.join()

    def _monitor_resources(self):
        """Monitor system resources."""
        while not self.stop_monitoring.is_set():
            memory_usage = self._get_memory_usage()

            if memory_usage > self.max_memory_gb:
                logger.warning(f"Memory usage ({memory_usage:.1f}GB) exceeds limit")
                # Could implement throttling here

            time.sleep(10)  # Check every 10 seconds

    def _generate_job_id(self) -> str:
        """Generate unique job ID."""
        import hashlib
        timestamp = datetime.now().isoformat()
        random_val = hash(timestamp)
        data = f"{timestamp}_{random_val}"
        return hashlib.md5(data.encode()).hexdigest()[:12]

    def _save_job(self, job: BatchJob):
        """Save job to database."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            INSERT OR REPLACE INTO batch_jobs
            (job_id, book_title, genre, status, priority,
             created_at, started_at, completed_at, progress,
             output_path, quality_score, generation_cost,
             error_message, data)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            job.job_id, job.book_title, job.genre,
            job.status.value, job.priority.value,
            job.created_at, job.started_at, job.completed_at,
            job.progress_percentage,
            str(job.output_path) if job.output_path else None,
            job.quality_score, job.generation_cost,
            job.error_message,
            json.dumps(asdict(job))
        ))

        conn.commit()
        conn.close()

    def _load_job(self, job_id: str) -> Optional[BatchJob]:
        """Load job from database."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            "SELECT data FROM batch_jobs WHERE job_id = ?",
            (job_id,)
        )

        result = cursor.fetchone()
        conn.close()

        if result:
            job_data = json.loads(result[0])
            job_data['status'] = JobStatus(job_data['status'])
            job_data['priority'] = JobPriority(job_data['priority'])
            if job_data.get('output_path'):
                job_data['output_path'] = Path(job_data['output_path'])
            return BatchJob(**job_data)

        return None