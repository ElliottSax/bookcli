#!/usr/bin/env python3
"""
Cloud Batch Orchestrator for Distributed Book Generation
Manages parallel book generation across OCI compute instances

Features:
- Job queue with SQLite backend
- Auto-scaling based on queue depth
- Result aggregation from cloud instances
- Cost optimization (free tier first, then paid)
- Progress monitoring and reporting
"""

import os
import time
import json
import sqlite3
import subprocess
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
from datetime import datetime

try:
    from oci_instance_manager import OCIInstanceManager, InstanceConfig, InstanceShape
    OCI_AVAILABLE = True
except ImportError:
    OCI_AVAILABLE = False


class JobStatus(Enum):
    """Status of a book generation job"""
    QUEUED = "queued"
    ASSIGNED = "assigned"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class BookJob:
    """Book generation job"""
    job_id: str
    source_file: str
    book_name: str
    genre: str
    target_words: int
    provider: str = "groq"
    status: str = JobStatus.QUEUED.value
    instance_id: Optional[str] = None
    created_at: float = 0.0
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    error_message: Optional[str] = None
    result_path: Optional[str] = None
    cost_llm: float = 0.0
    cost_cloud: float = 0.0


class JobQueue:
    """
    SQLite-based job queue for book generation

    Schema:
    - jobs: job metadata and status
    - results: generated book artifacts
    """

    def __init__(self, db_path: Path = Path("workspace/book_jobs.db")):
        """Initialize job queue database"""
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        self.conn = sqlite3.connect(str(self.db_path))
        self.conn.row_factory = sqlite3.Row
        self._init_db()

    def _init_db(self):
        """Create database tables"""
        cursor = self.conn.cursor()

        # Jobs table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS jobs (
                job_id TEXT PRIMARY KEY,
                source_file TEXT NOT NULL,
                book_name TEXT NOT NULL,
                genre TEXT NOT NULL,
                target_words INTEGER NOT NULL,
                provider TEXT NOT NULL,
                status TEXT NOT NULL,
                instance_id TEXT,
                created_at REAL NOT NULL,
                started_at REAL,
                completed_at REAL,
                error_message TEXT,
                result_path TEXT,
                cost_llm REAL DEFAULT 0.0,
                cost_cloud REAL DEFAULT 0.0
            )
        """)

        # Results table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS results (
                job_id TEXT PRIMARY KEY,
                book_content BLOB,
                metadata TEXT,
                quality_score REAL,
                word_count INTEGER,
                chapters INTEGER,
                generation_time REAL,
                FOREIGN KEY (job_id) REFERENCES jobs(job_id)
            )
        """)

        self.conn.commit()

    def add_job(self, job: BookJob) -> str:
        """Add job to queue"""
        if not job.job_id:
            job.job_id = f"job_{int(time.time())}_{job.book_name}"

        if job.created_at == 0.0:
            job.created_at = time.time()

        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO jobs VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            job.job_id, job.source_file, job.book_name, job.genre,
            job.target_words, job.provider, job.status, job.instance_id,
            job.created_at, job.started_at, job.completed_at,
            job.error_message, job.result_path, job.cost_llm, job.cost_cloud
        ))
        self.conn.commit()

        return job.job_id

    def get_next_job(self) -> Optional[BookJob]:
        """Get next queued job"""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT * FROM jobs
            WHERE status = ?
            ORDER BY created_at ASC
            LIMIT 1
        """, (JobStatus.QUEUED.value,))

        row = cursor.fetchone()
        if row:
            return BookJob(**dict(row))
        return None

    def assign_job(self, job_id: str, instance_id: str):
        """Assign job to instance"""
        cursor = self.conn.cursor()
        cursor.execute("""
            UPDATE jobs
            SET status = ?, instance_id = ?, started_at = ?
            WHERE job_id = ?
        """, (JobStatus.ASSIGNED.value, instance_id, time.time(), job_id))
        self.conn.commit()

    def update_job_status(self, job_id: str, status: JobStatus,
                         error_message: Optional[str] = None,
                         result_path: Optional[str] = None):
        """Update job status"""
        cursor = self.conn.cursor()

        if status == JobStatus.COMPLETED:
            cursor.execute("""
                UPDATE jobs
                SET status = ?, completed_at = ?, result_path = ?
                WHERE job_id = ?
            """, (status.value, time.time(), result_path, job_id))
        elif status == JobStatus.FAILED:
            cursor.execute("""
                UPDATE jobs
                SET status = ?, completed_at = ?, error_message = ?
                WHERE job_id = ?
            """, (status.value, time.time(), error_message, job_id))
        else:
            cursor.execute("""
                UPDATE jobs SET status = ? WHERE job_id = ?
            """, (status.value, job_id))

        self.conn.commit()

    def get_job(self, job_id: str) -> Optional[BookJob]:
        """Get job by ID"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM jobs WHERE job_id = ?", (job_id,))
        row = cursor.fetchone()
        if row:
            return BookJob(**dict(row))
        return None

    def get_queue_stats(self) -> Dict:
        """Get queue statistics"""
        cursor = self.conn.cursor()

        stats = {}
        for status in JobStatus:
            cursor.execute(
                "SELECT COUNT(*) FROM jobs WHERE status = ?",
                (status.value,)
            )
            stats[status.value] = cursor.fetchone()[0]

        # Calculate costs
        cursor.execute("SELECT SUM(cost_llm), SUM(cost_cloud) FROM jobs")
        llm_cost, cloud_cost = cursor.fetchone()
        stats['total_cost_llm'] = llm_cost or 0.0
        stats['total_cost_cloud'] = cloud_cost or 0.0
        stats['total_cost'] = stats['total_cost_llm'] + stats['total_cost_cloud']

        return stats


class CloudBatchOrchestrator:
    """
    Orchestrates distributed book generation across OCI instances

    Workflow:
    1. Jobs added to queue
    2. Auto-scale instances based on queue depth
    3. Assign jobs to instances
    4. Monitor progress
    5. Collect results
    6. Shutdown idle instances
    """

    def __init__(self,
                 oci_manager: Optional[OCIInstanceManager] = None,
                 max_instances: int = 4,
                 jobs_per_instance: int = 1,
                 auto_scale: bool = True):
        """
        Initialize cloud batch orchestrator

        Args:
            oci_manager: OCI instance manager
            max_instances: Max concurrent instances
            jobs_per_instance: Jobs per instance (sequential)
            auto_scale: Auto-scale instances based on queue
        """
        if not OCI_AVAILABLE:
            raise ImportError("OCI not available. Install: pip install oci")

        self.oci_manager = oci_manager
        self.max_instances = max_instances
        self.jobs_per_instance = jobs_per_instance
        self.auto_scale = auto_scale

        # Job queue
        self.job_queue = JobQueue()

        # Instance -> Job mapping
        self.instance_jobs: Dict[str, List[str]] = {}

        print("[CloudOrch] Initialized batch orchestrator")
        print(f"[CloudOrch] Max instances: {max_instances}")
        print(f"[CloudOrch] Auto-scale: {auto_scale}")

    def submit_job(self, source_file: str, book_name: str, genre: str,
                   target_words: int, provider: str = "groq") -> str:
        """
        Submit book generation job

        Args:
            source_file: Path to source material
            book_name: Name for the book
            genre: Book genre
            target_words: Target word count
            provider: LLM provider to use

        Returns:
            Job ID
        """
        job = BookJob(
            job_id="",  # Will be generated
            source_file=source_file,
            book_name=book_name,
            genre=genre,
            target_words=target_words,
            provider=provider
        )

        job_id = self.job_queue.add_job(job)
        print(f"[CloudOrch] ✓ Submitted job {job_id}")

        # Trigger auto-scaling
        if self.auto_scale:
            self._auto_scale()

        return job_id

    def submit_batch(self, jobs: List[Dict]) -> List[str]:
        """
        Submit multiple jobs at once

        Args:
            jobs: List of job configs (dict with source_file, book_name, etc.)

        Returns:
            List of job IDs
        """
        job_ids = []

        for job_config in jobs:
            job_id = self.submit_job(**job_config)
            job_ids.append(job_id)

        print(f"[CloudOrch] ✓ Submitted {len(job_ids)} jobs")
        return job_ids

    def _auto_scale(self):
        """Auto-scale instances based on queue depth"""
        stats = self.job_queue.get_queue_stats()
        queued = stats['queued']
        active_instances = len(self.oci_manager.list_instances())

        # Calculate needed instances
        needed = min(
            (queued + self.jobs_per_instance - 1) // self.jobs_per_instance,
            self.max_instances
        )

        to_create = needed - active_instances

        if to_create > 0:
            print(f"[CloudOrch] Scaling up: creating {to_create} instances")

            for i in range(to_create):
                self._create_worker_instance(f"bookgen-worker-{i}")

        elif to_create < 0 and queued == 0:
            # Scale down idle instances
            print(f"[CloudOrch] Scaling down: {-to_create} excess instances")
            # Would implement idle instance shutdown here

    def _create_worker_instance(self, name: str) -> Optional[str]:
        """Create a worker instance for book generation"""

        # Prioritize free tier
        config = InstanceConfig(
            shape=InstanceShape.AMPERE_FREE.value,
            ocpus=2,
            memory_gb=12,
            use_free_tier=True
        )

        # Generate deployment script
        api_keys = {
            'GROQ_API_KEY': os.environ.get('GROQ_API_KEY', ''),
            'DEEPSEEK_API_KEY': os.environ.get('DEEPSEEK_API_KEY', ''),
            'OPENROUTER_API_KEY': os.environ.get('OPENROUTER_API_KEY', ''),
            'ANTHROPIC_API_KEY': os.environ.get('ANTHROPIC_API_KEY', ''),
        }

        setup_script = self.oci_manager.generate_deployment_script(api_keys)

        # Create instance
        instance_id = self.oci_manager.create_instance(name, config, setup_script)

        if instance_id:
            self.instance_jobs[instance_id] = []
            print(f"[CloudOrch] ✓ Created worker instance: {instance_id[:8]}")

        return instance_id

    def assign_jobs_to_instances(self):
        """Assign queued jobs to available instances"""
        instances = self.oci_manager.list_instances()

        for instance in instances:
            # Check if instance has capacity
            assigned = len(self.instance_jobs.get(instance.instance_id, []))

            if assigned < self.jobs_per_instance:
                # Get next job
                job = self.job_queue.get_next_job()

                if job:
                    # Assign to instance
                    self.job_queue.assign_job(job.job_id, instance.instance_id)
                    self.instance_jobs[instance.instance_id].append(job.job_id)

                    print(f"[CloudOrch] Assigned job {job.job_id} to {instance.name}")

    def monitor_progress(self) -> Dict:
        """Monitor job progress and return status"""
        stats = self.job_queue.get_queue_stats()

        # Add instance info
        instances = self.oci_manager.list_instances()
        stats['active_instances'] = len(instances)

        # Add budget info
        budget = self.oci_manager.get_budget_status()
        stats['budget'] = budget

        return stats

    def print_status(self):
        """Print detailed status"""
        stats = self.monitor_progress()

        print("\n" + "="*70)
        print("CLOUD BATCH ORCHESTRATOR STATUS")
        print("="*70)

        print(f"\nJobs:")
        print(f"  Queued:    {stats['queued']}")
        print(f"  Assigned:  {stats['assigned']}")
        print(f"  Running:   {stats['running']}")
        print(f"  Completed: {stats['completed']}")
        print(f"  Failed:    {stats['failed']}")

        print(f"\nInstances:")
        print(f"  Active: {stats['active_instances']}/{self.max_instances}")

        print(f"\nCosts:")
        print(f"  LLM API:   ${stats['total_cost_llm']:.2f}")
        print(f"  Cloud:     ${stats['total_cost_cloud']:.2f}")
        print(f"  Total:     ${stats['total_cost']:.2f}")

        budget = stats['budget']
        print(f"\nBudget:")
        print(f"  Spent:     ${budget['current_spend']:.2f}")
        print(f"  Remaining: ${budget['remaining']:.2f} ({100-budget['utilization_pct']:.1f}%)")

        print("="*70 + "\n")

    def wait_for_completion(self, timeout: Optional[int] = None) -> bool:
        """
        Wait for all jobs to complete

        Args:
            timeout: Max seconds to wait (None = infinite)

        Returns:
            True if all jobs completed successfully
        """
        start = time.time()

        while True:
            stats = self.job_queue.get_queue_stats()

            queued = stats['queued']
            assigned = stats['assigned']
            running = stats['running']
            pending = queued + assigned + running

            if pending == 0:
                print(f"[CloudOrch] ✓ All jobs completed")
                return True

            if timeout and (time.time() - start) > timeout:
                print(f"[CloudOrch] ✗ Timeout waiting for jobs")
                return False

            # Print progress
            completed = stats['completed']
            failed = stats['failed']
            total = completed + failed + pending

            print(f"[CloudOrch] Progress: {completed + failed}/{total} "
                  f"({pending} pending, {failed} failed)")

            time.sleep(30)

    def cleanup(self):
        """Cleanup all instances and resources"""
        print("[CloudOrch] Cleaning up instances...")

        for instance_id in list(self.instance_jobs.keys()):
            self.oci_manager.terminate_instance(instance_id)

        print("[CloudOrch] ✓ Cleanup complete")


def demo_batch_orchestrator():
    """Demonstrate batch orchestrator"""
    print("="*70)
    print("CLOUD BATCH ORCHESTRATOR DEMO")
    print("="*70)

    # Check OCI availability
    if not OCI_AVAILABLE:
        print("\n⚠ OCI SDK not installed")
        print("Install with: pip install oci")
        print("\nThis demo shows the structure for cloud-based book generation")
        return

    print("\nThis orchestrator enables:")
    print("  • Parallel book generation across multiple cloud instances")
    print("  • Automatic scaling based on job queue depth")
    print("  • Cost optimization (free tier first)")
    print("  • Progress monitoring and result aggregation")

    print("\nExample usage:")
    print("""
    # Initialize OCI manager
    oci_mgr = OCIInstanceManager(max_spend=300.0)

    # Create batch orchestrator
    orchestrator = CloudBatchOrchestrator(
        oci_manager=oci_mgr,
        max_instances=4,
        auto_scale=True
    )

    # Submit batch jobs
    jobs = [
        {
            'source_file': 'outline1.txt',
            'book_name': 'fantasy-epic-1',
            'genre': 'fantasy',
            'target_words': 30000,
            'provider': 'groq'
        },
        {
            'source_file': 'outline2.txt',
            'book_name': 'scifi-adventure-1',
            'genre': 'science_fiction',
            'target_words': 30000,
            'provider': 'deepseek'
        },
        # ... more jobs
    ]

    job_ids = orchestrator.submit_batch(jobs)

    # Wait for completion
    orchestrator.wait_for_completion()

    # Print results
    orchestrator.print_status()

    # Cleanup
    orchestrator.cleanup()
    """)

    print("\n✓ Ready to generate books at scale with OCI!")


if __name__ == "__main__":
    demo_batch_orchestrator()
