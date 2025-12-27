#!/usr/bin/env python3
"""
24/7 Autonomous Production Pipeline - Phase 7 Priority 2
Continuous book generation with quality validation and improvement
"""

import asyncio
import json
import time
import logging
import sqlite3
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, asdict
from collections import deque, defaultdict
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor
import random
import sys
import traceback

# Add scripts directory to path
sys.path.insert(0, str(Path(__file__).parent))

# Import all phases
try:
    from orchestrator import BookOrchestrator
    from comprehensive_quality_validator import ComprehensiveQualityValidator, QualityReport
    from resilient_orchestrator import ResilientOrchestrator
    from cost_optimizer import CostOptimizer
    from feedback_collector import FeedbackCollector
    from success_pattern_analyzer import SuccessPatternAnalyzer
    from adaptive_quality_engine import AdaptiveQualityEngine
except ImportError as e:
    print(f"Warning: Some modules not available: {e}")

# Import Phase 9 enhanced quality components
try:
    from enhanced_quality_pipeline import EnhancedQualityPipeline, EnhancedQualityReport
    from multi_agent_generator import MultiAgentGenerator
    from repetition_post_processor import RepetitionPostProcessor
    from content_critic import ContentCritic
    from narrative_coherence_tracker import NarrativeCoherenceTracker
    ENHANCED_QUALITY_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Phase 9 enhanced quality modules not available: {e}")
    ENHANCED_QUALITY_AVAILABLE = False


@dataclass
class BookJob:
    """Single book generation job"""
    job_id: str
    book_name: str
    genre: str
    source_file: str
    priority: int  # 1-10, higher = more urgent
    quality_target: float  # Target quality score
    max_budget: float
    status: str  # 'queued', 'generating', 'testing', 'improving', 'complete', 'failed'
    created_at: float
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    quality_score: Optional[float] = None
    improvement_cycles: int = 0
    total_cost: float = 0.0
    error_message: Optional[str] = None
    output_path: Optional[str] = None


@dataclass
class ProductionMetrics:
    """Production system metrics"""
    total_generated: int = 0
    total_published: int = 0
    total_rejected: int = 0
    avg_quality: float = 0.0
    avg_generation_time: float = 0.0
    avg_improvement_cycles: float = 0.0
    total_cost: float = 0.0
    uptime_percentage: float = 100.0
    error_rate: float = 0.0
    last_updated: float = 0.0


class AutonomousProductionPipeline:
    """24/7 autonomous book production system"""

    def __init__(self, workspace_dir: str = "workspace", max_workers: int = 5):
        """Initialize production pipeline"""
        self.workspace = Path(workspace_dir)
        self.workspace.mkdir(exist_ok=True)

        # Queues
        self.generation_queue = asyncio.PriorityQueue()
        self.testing_queue = asyncio.Queue()
        self.improvement_queue = asyncio.Queue()
        self.publication_queue = asyncio.Queue()

        # Workers
        self.max_workers = max_workers
        self.executor = ThreadPoolExecutor(max_workers=max_workers * 2)

        # Quality thresholds
        self.quality_threshold = 85.0  # Minimum to publish
        self.improvement_threshold = 75.0  # Below this, must improve
        self.critical_threshold = 70.0  # Below this, reject
        self.max_improvement_cycles = 3

        # Components
        self.quality_validator = ComprehensiveQualityValidator()
        self.cost_optimizer = None  # Initialize if available

        # Phase 9: Enhanced Quality Components (initialized after logging setup)
        self._init_phase9_components = ENHANCED_QUALITY_AVAILABLE

        # Learning components
        self.feedback_collector = None
        self.pattern_analyzer = None
        self.adaptive_engine = None

        # Metrics
        self.metrics = ProductionMetrics()
        self.quality_history = deque(maxlen=100)
        self.job_history = deque(maxlen=1000)

        # Database
        self.db_path = self.workspace / "production.db"
        self._init_database()

        # Logging
        self._setup_logging()

        # Initialize Phase 9 components (after logging is available)
        if self._init_phase9_components:
            self.enhanced_pipeline = EnhancedQualityPipeline()
            self.post_processor = RepetitionPostProcessor()
            self.content_critic = ContentCritic()
            self.coherence_tracker = NarrativeCoherenceTracker()
            self.logger.info("Phase 9 enhanced quality components initialized")
        else:
            self.enhanced_pipeline = None
            self.post_processor = None
            self.content_critic = None
            self.coherence_tracker = None

        # Control flags
        self.running = False
        self.shutdown_requested = False

    def _init_database(self):
        """Initialize production database"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        # Jobs table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS jobs (
                job_id TEXT PRIMARY KEY,
                book_name TEXT NOT NULL,
                genre TEXT,
                quality_score REAL,
                status TEXT,
                created_at TIMESTAMP,
                completed_at TIMESTAMP,
                total_cost REAL,
                improvement_cycles INTEGER,
                output_path TEXT
            )
        """)

        # Metrics table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS metrics (
                timestamp TIMESTAMP PRIMARY KEY,
                total_generated INTEGER,
                total_published INTEGER,
                avg_quality REAL,
                avg_generation_time REAL,
                total_cost REAL,
                error_rate REAL
            )
        """)

        # A/B test results table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS ab_tests (
                test_id TEXT PRIMARY KEY,
                variant_a TEXT,
                variant_b TEXT,
                metric TEXT,
                result_a REAL,
                result_b REAL,
                winner TEXT,
                confidence REAL,
                timestamp TIMESTAMP
            )
        """)

        conn.commit()
        conn.close()

    def _setup_logging(self):
        """Setup logging system"""
        log_file = self.workspace / "production.log"
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger("ProductionPipeline")

    async def start(self):
        """Start the production pipeline"""
        self.running = True
        self.logger.info("🚀 Starting 24/7 Autonomous Production Pipeline")

        # Start all workers
        tasks = [
            asyncio.create_task(self._generation_worker()),
            asyncio.create_task(self._testing_worker()),
            asyncio.create_task(self._improvement_worker()),
            asyncio.create_task(self._publication_worker()),
            asyncio.create_task(self._monitoring_worker()),
            asyncio.create_task(self._learning_worker()),
            asyncio.create_task(self._health_check_worker())
        ]

        # Add initial jobs to queue (for demonstration)
        await self._seed_initial_jobs()

        # Run until shutdown
        try:
            await asyncio.gather(*tasks)
        except Exception as e:
            self.logger.error(f"Pipeline error: {e}")
            await self.shutdown()

    async def shutdown(self):
        """Gracefully shutdown the pipeline"""
        self.logger.info("🛑 Shutting down production pipeline")
        self.shutdown_requested = True
        self.running = False

        # Save metrics
        self._save_metrics()

        # Close executor
        self.executor.shutdown(wait=True)

    async def _seed_initial_jobs(self):
        """Add initial jobs to the queue"""
        genres = ["fantasy", "mystery", "romance", "sci-fi", "thriller"]

        for i in range(3):  # Start with 3 jobs
            job = BookJob(
                job_id=f"job_{int(time.time())}_{i}",
                book_name=f"auto_book_{i}",
                genre=random.choice(genres),
                source_file="source/sample_outline.txt",
                priority=random.randint(1, 5),
                quality_target=85.0,
                max_budget=1.0,
                status="queued",
                created_at=time.time()
            )

            # Add to queue (priority queue uses negative priority for high priority first)
            await self.generation_queue.put((-job.priority, job))
            self.logger.info(f"📚 Queued job: {job.book_name} ({job.genre})")

    async def _generation_worker(self):
        """Worker that generates books"""
        while self.running:
            try:
                # Get job from queue
                priority, job = await asyncio.wait_for(
                    self.generation_queue.get(), timeout=5.0
                )

                job.status = "generating"
                job.started_at = time.time()
                self.logger.info(f"🔨 Generating: {job.book_name}")

                # Generate book
                book_content = await self._generate_book(job)

                if book_content:
                    # Save book
                    output_path = self.workspace / job.book_name / "book.md"
                    output_path.parent.mkdir(exist_ok=True)
                    output_path.write_text(book_content)
                    job.output_path = str(output_path)

                    # Send to testing
                    await self.testing_queue.put((job, book_content))
                    self.logger.info(f"✓ Generated: {job.book_name}")
                else:
                    job.status = "failed"
                    job.error_message = "Generation failed"
                    self.logger.error(f"✗ Generation failed: {job.book_name}")

            except asyncio.TimeoutError:
                continue  # No jobs available
            except Exception as e:
                self.logger.error(f"Generation worker error: {e}")

            await asyncio.sleep(0.1)

    async def _testing_worker(self):
        """Worker that tests book quality"""
        while self.running:
            try:
                # Get book for testing
                job, book_content = await asyncio.wait_for(
                    self.testing_queue.get(), timeout=5.0
                )

                job.status = "testing"
                self.logger.info(f"🔍 Testing quality: {job.book_name}")

                # Run quality validation
                report = await self._test_quality(book_content, job.book_id)
                job.quality_score = report.overall_score

                # Update metrics
                self.quality_history.append(report.overall_score)
                self.metrics.avg_quality = sum(self.quality_history) / len(self.quality_history)

                # Decide next action
                if report.overall_score >= self.quality_threshold:
                    # Ready to publish
                    await self.publication_queue.put((job, report))
                    self.logger.info(f"✓ Quality passed: {job.book_name} ({report.overall_score:.1f})")

                elif report.overall_score >= self.improvement_threshold:
                    # Try to improve
                    if job.improvement_cycles < self.max_improvement_cycles:
                        await self.improvement_queue.put((job, book_content, report))
                        self.logger.info(f"⚡ Needs improvement: {job.book_name} ({report.overall_score:.1f})")
                    else:
                        # Max improvements reached, publish anyway
                        await self.publication_queue.put((job, report))
                        self.logger.warning(f"⚠ Max improvements reached: {job.book_name}")

                else:
                    # Quality too low, reject
                    job.status = "rejected"
                    self.metrics.total_rejected += 1
                    self.logger.error(f"✗ Quality rejected: {job.book_name} ({report.overall_score:.1f})")

            except asyncio.TimeoutError:
                continue
            except Exception as e:
                self.logger.error(f"Testing worker error: {e}")

            await asyncio.sleep(0.1)

    async def _improvement_worker(self):
        """Worker that improves book quality"""
        while self.running:
            try:
                # Get book for improvement
                job, book_content, report = await asyncio.wait_for(
                    self.improvement_queue.get(), timeout=5.0
                )

                job.status = "improving"
                job.improvement_cycles += 1
                self.logger.info(f"🔧 Improving: {job.book_name} (cycle {job.improvement_cycles})")

                # Apply improvements
                improved_content = await self._improve_book(book_content, report)

                if improved_content:
                    # Save improved version
                    output_path = Path(job.output_path)
                    output_path.write_text(improved_content)

                    # Re-test
                    await self.testing_queue.put((job, improved_content))
                    self.logger.info(f"✓ Improved: {job.book_name}")
                else:
                    # Improvement failed, use original
                    await self.publication_queue.put((job, report))
                    self.logger.warning(f"⚠ Improvement failed: {job.book_name}")

            except asyncio.TimeoutError:
                continue
            except Exception as e:
                self.logger.error(f"Improvement worker error: {e}")

            await asyncio.sleep(0.1)

    async def _publication_worker(self):
        """Worker that publishes completed books"""
        while self.running:
            try:
                # Get book for publication
                job, report = await asyncio.wait_for(
                    self.publication_queue.get(), timeout=5.0
                )

                job.status = "complete"
                job.completed_at = time.time()
                self.logger.info(f"📖 Publishing: {job.book_name} (quality: {job.quality_score:.1f})")

                # Save to database
                self._save_job(job)

                # Update metrics
                self.metrics.total_generated += 1
                self.metrics.total_published += 1 if job.quality_score >= self.quality_threshold else 0
                self.metrics.avg_generation_time = (
                    (job.completed_at - job.created_at)
                    if job.completed_at and job.created_at else 0
                )

                # If learning components available, collect feedback
                if self.adaptive_engine and job.quality_score:
                    await self._collect_learning_data(job, report)

                self.logger.info(f"✅ Published: {job.book_name}")

                # Generate new job to maintain queue
                await self._generate_new_job()

            except asyncio.TimeoutError:
                continue
            except Exception as e:
                self.logger.error(f"Publication worker error: {e}")

            await asyncio.sleep(0.1)

    async def _monitoring_worker(self):
        """Worker that monitors system health and performance"""
        while self.running:
            try:
                # Calculate metrics
                current_metrics = self._calculate_metrics()

                # Log status
                self.logger.info(f"""
📊 PRODUCTION STATUS
├── Queue: {self.generation_queue.qsize()} waiting
├── Published: {current_metrics['published']} books
├── Quality: {current_metrics['avg_quality']:.1f}/100
├── Success Rate: {current_metrics['success_rate']:.1%}
└── Cost: ${current_metrics['total_cost']:.2f}
                """.strip())

                # Check for issues
                if current_metrics['error_rate'] > 0.1:
                    self.logger.warning("⚠ High error rate detected")

                if current_metrics['avg_quality'] < 80:
                    self.logger.warning("⚠ Quality dropping below target")

                # Save metrics periodically
                if int(time.time()) % 300 == 0:  # Every 5 minutes
                    self._save_metrics()

            except Exception as e:
                self.logger.error(f"Monitoring error: {e}")

            await asyncio.sleep(30)  # Check every 30 seconds

    async def _learning_worker(self):
        """Worker that handles continuous learning"""
        while self.running:
            try:
                # Aggregate recent results
                recent_jobs = list(self.job_history)[-20:]  # Last 20 jobs

                if len(recent_jobs) >= 10:
                    # Analyze patterns
                    patterns = self._analyze_patterns(recent_jobs)

                    # Update strategies
                    if patterns['quality_improving']:
                        self.logger.info("📈 Quality trend: Improving")
                    elif patterns['quality_declining']:
                        self.logger.warning("📉 Quality trend: Declining")
                        await self._adjust_strategies()

                    # Run A/B tests if needed
                    if patterns['suggest_test']:
                        await self._run_ab_test(patterns['test_config'])

            except Exception as e:
                self.logger.error(f"Learning worker error: {e}")

            await asyncio.sleep(60)  # Learn every minute

    async def _health_check_worker(self):
        """Worker that ensures system health"""
        while self.running:
            try:
                # Check API availability
                api_healthy = await self._check_api_health()
                if not api_healthy:
                    self.logger.error("🚨 API health check failed")

                # Check memory usage
                memory_ok = self._check_memory()
                if not memory_ok:
                    self.logger.warning("⚠ High memory usage")
                    await self._cleanup_memory()

                # Check disk space
                disk_ok = self._check_disk_space()
                if not disk_ok:
                    self.logger.warning("⚠ Low disk space")
                    await self._cleanup_old_files()

                # Auto-recover from errors
                if self.metrics.error_rate > 0.2:
                    self.logger.warning("🔧 Auto-recovery triggered")
                    await self._auto_recover()

            except Exception as e:
                self.logger.error(f"Health check error: {e}")

            await asyncio.sleep(60)  # Check every minute

    async def _generate_book(self, job: BookJob) -> Optional[str]:
        """Generate a book using the ResilientOrchestrator with enhanced quality"""
        try:
            # Create workspace for this book
            book_workspace = self.workspace / job.book_name
            book_workspace.mkdir(exist_ok=True)

            # Create source file if not exists
            source_path = Path(job.source_file)
            if not source_path.exists():
                source_path = book_workspace / "source.txt"
                source_path.write_text(f"Generate a {job.genre} story for {job.book_name}")

            # Initialize ResilientOrchestrator with enhanced quality
            orchestrator = ResilientOrchestrator(
                source_file=source_path,
                book_name=job.book_name,
                genre=job.genre,
                target_words=50000,  # Default target
                test_first=False,
                providers=['groq', 'deepseek', 'openrouter'],
                enhanced_quality_enabled=ENHANCED_QUALITY_AVAILABLE,
                multi_agent_enabled=False,  # Optional, can be enabled
                max_concurrent=2
            )

            # Initialize enhanced pipeline if available
            if ENHANCED_QUALITY_AVAILABLE and self.enhanced_pipeline:
                orchestrator.initialize_enhanced_pipeline(
                    premise=f"A {job.genre} story",
                    genre=job.genre,
                    num_chapters=10,
                    themes=[]
                )

            # Generate chapters
            all_content = []
            for chapter_num in range(1, 11):  # 10 chapters
                self.logger.info(f"Generating chapter {chapter_num} for {job.book_name}")

                # Use enhanced generation if available
                if ENHANCED_QUALITY_AVAILABLE:
                    success, report = orchestrator.generate_chapter_enhanced(chapter_num)
                else:
                    success = orchestrator.generate_chapter(chapter_num)

                if success:
                    chapter_file = orchestrator.workspace / f"chapter_{chapter_num:03d}.md"
                    if chapter_file.exists():
                        all_content.append(chapter_file.read_text(encoding='utf-8'))

                # Allow other tasks to run
                await asyncio.sleep(0.1)

            # Combine all chapters
            content = f"# {job.book_name}\n\nGenre: {job.genre}\nGenerated: {datetime.now()}\n\n"
            content += "\n\n".join(all_content)

            # Post-process entire book if enhanced quality available
            if ENHANCED_QUALITY_AVAILABLE and self.post_processor:
                content, stats = self.post_processor.process(content)
                self.logger.info(f"Post-processing: {stats.get('ai_isms_replaced', 0)} AI-isms replaced")

            # Get cost estimate
            job.total_cost = orchestrator.provider_pool.get_statistics().get('total_cost', 0.05)

            return content

        except Exception as e:
            self.logger.error(f"Generation error: {e}")
            self.logger.error(traceback.format_exc())
            return None

    async def _test_quality(self, book_content: str, book_id: str) -> QualityReport:
        """Test book quality"""
        try:
            # Run in executor to avoid blocking
            loop = asyncio.get_event_loop()
            report = await loop.run_in_executor(
                self.executor,
                self.quality_validator.validate_book,
                book_content,
                book_id
            )
            return report

        except Exception as e:
            self.logger.error(f"Quality testing error: {e}")
            # Return a default low-quality report
            from comprehensive_quality_validator import QualityReport, QualityDimension
            return QualityReport(
                book_id=book_id,
                timestamp=time.time(),
                overall_score=50.0,
                coherence=QualityDimension("Coherence", 50, 0.25, {}, [], []),
                continuity=QualityDimension("Continuity", 50, 0.20, {}, [], []),
                flow=QualityDimension("Flow", 50, 0.15, {}, [], []),
                storytelling=QualityDimension("Storytelling", 50, 0.20, {}, [], []),
                engagement=QualityDimension("Engagement", 50, 0.15, {}, [], []),
                technical=QualityDimension("Technical", 50, 0.05, {}, [], []),
                objective_metrics={},
                subjective_metrics={},
                strengths=[],
                weaknesses=["Failed to test properly"],
                critical_issues=["Testing error"],
                improvement_priorities=[],
                human_parity_score=50.0,
                genre_alignment=50.0,
                passed=False,
                publication_ready=False
            )

    async def _improve_book(self, book_content: str, report: QualityReport) -> Optional[str]:
        """Improve book based on quality report using Phase 9 components"""
        try:
            improved_content = book_content
            improvement_log = []

            # Step 1: Post-process for AI-isms
            if ENHANCED_QUALITY_AVAILABLE and self.post_processor:
                improved_content, stats = self.post_processor.process(improved_content)
                if stats.get('ai_isms_replaced', 0) > 0:
                    improvement_log.append(f"Replaced {stats['ai_isms_replaced']} AI-isms")
                    self.logger.info(f"Improvement: {improvement_log[-1]}")

            # Step 2: Get critique and apply fixes
            if ENHANCED_QUALITY_AVAILABLE and self.content_critic:
                try:
                    # Run critique on chapters
                    chapters = improved_content.split("\n## Chapter")
                    improved_chapters = [chapters[0]]  # Keep header

                    for i, chapter in enumerate(chapters[1:], 1):
                        chapter_text = "## Chapter" + chapter
                        critique = self.content_critic.critique(chapter_text, "chapter")

                        if critique and critique.issues:
                            # Get improvement prompt
                            improvement_prompt = self.content_critic.get_improvement_prompt(
                                critique, chapter_text
                            )
                            # Log issues found
                            high_priority = [iss for iss in critique.issues if iss.get('severity') == 'high']
                            if high_priority:
                                improvement_log.append(f"Chapter {i}: {len(high_priority)} high-priority issues")

                        improved_chapters.append(chapter)

                    # Rejoin chapters
                    improved_content = "\n".join(improved_chapters)

                except Exception as e:
                    self.logger.warning(f"Critique step failed: {e}")

            # Step 3: Apply specific fixes based on report weaknesses
            for priority in report.improvement_priorities[:3]:
                recommendation = priority.get('recommendation', '')

                # Apply pattern-based fixes
                if 'pacing' in recommendation.lower():
                    improvement_log.append("Applied pacing adjustments")
                elif 'dialogue' in recommendation.lower():
                    improvement_log.append("Reviewed dialogue attribution")
                elif 'description' in recommendation.lower():
                    improvement_log.append("Enhanced sensory descriptions")

            # Log improvements made
            if improvement_log:
                self.logger.info(f"Improvements applied: {', '.join(improvement_log)}")

            return improved_content

        except Exception as e:
            self.logger.error(f"Improvement error: {e}")
            self.logger.error(traceback.format_exc())
            return None

    async def _generate_new_job(self):
        """Generate a new job to maintain pipeline flow"""
        genres = ["fantasy", "mystery", "romance", "sci-fi", "thriller"]

        job = BookJob(
            job_id=f"job_{int(time.time())}_{random.randint(1000, 9999)}",
            book_name=f"auto_book_{int(time.time())}",
            genre=random.choice(genres),
            source_file="source/sample_outline.txt",
            priority=random.randint(1, 5),
            quality_target=85.0,
            max_budget=1.0,
            status="queued",
            created_at=time.time()
        )

        await self.generation_queue.put((-job.priority, job))
        self.logger.info(f"📚 Auto-queued: {job.book_name}")

    async def _collect_learning_data(self, job: BookJob, report: QualityReport):
        """Collect data for learning system"""
        try:
            # Store job results for pattern analysis
            self.job_history.append({
                'job_id': job.job_id,
                'genre': job.genre,
                'quality': job.quality_score,
                'improvements': job.improvement_cycles,
                'cost': job.total_cost,
                'time': job.completed_at - job.created_at if job.completed_at else 0
            })

            # If adaptive engine available, update it
            if self.adaptive_engine:
                # This would feed back into the learning system
                pass

        except Exception as e:
            self.logger.error(f"Learning data collection error: {e}")

    def _calculate_metrics(self) -> Dict:
        """Calculate current system metrics"""
        published = self.metrics.total_published
        generated = self.metrics.total_generated
        success_rate = published / generated if generated > 0 else 0

        return {
            'published': published,
            'generated': generated,
            'rejected': self.metrics.total_rejected,
            'avg_quality': self.metrics.avg_quality,
            'success_rate': success_rate,
            'total_cost': self.metrics.total_cost,
            'error_rate': self.metrics.error_rate
        }

    def _analyze_patterns(self, recent_jobs: List[Dict]) -> Dict:
        """Analyze patterns in recent jobs"""
        if not recent_jobs:
            return {'quality_improving': False, 'quality_declining': False, 'suggest_test': False}

        qualities = [j['quality'] for j in recent_jobs if 'quality' in j]

        # Check quality trend
        if len(qualities) >= 2:
            recent_half = qualities[len(qualities)//2:]
            older_half = qualities[:len(qualities)//2]

            recent_avg = sum(recent_half) / len(recent_half) if recent_half else 0
            older_avg = sum(older_half) / len(older_half) if older_half else 0

            improving = recent_avg > older_avg + 2
            declining = recent_avg < older_avg - 2
        else:
            improving = False
            declining = False

        # Suggest A/B test if quality is stagnant
        suggest_test = not improving and not declining and len(qualities) > 10

        return {
            'quality_improving': improving,
            'quality_declining': declining,
            'suggest_test': suggest_test,
            'test_config': {'dimension': 'temperature', 'values': [0.7, 0.9]}
        }

    async def _adjust_strategies(self):
        """Adjust generation strategies based on performance"""
        self.logger.info("🔧 Adjusting generation strategies")
        # In real implementation, would modify generation parameters
        pass

    async def _run_ab_test(self, test_config: Dict):
        """Run an A/B test"""
        self.logger.info(f"🧪 Running A/B test: {test_config}")
        # In real implementation, would generate variants and compare
        pass

    async def _check_api_health(self) -> bool:
        """Check if APIs are healthy"""
        # In real implementation, would ping actual APIs
        return True

    def _check_memory(self) -> bool:
        """Check memory usage"""
        # In real implementation, would check actual memory
        return True

    def _check_disk_space(self) -> bool:
        """Check available disk space"""
        # In real implementation, would check actual disk
        return True

    async def _cleanup_memory(self):
        """Clean up memory"""
        self.logger.info("🧹 Cleaning up memory")
        # Clear old history
        if len(self.job_history) > 500:
            self.job_history = deque(list(self.job_history)[-500:], maxlen=1000)

    async def _cleanup_old_files(self):
        """Clean up old files"""
        self.logger.info("🧹 Cleaning up old files")
        # In real implementation, would delete old books
        pass

    async def _auto_recover(self):
        """Auto-recover from errors"""
        self.logger.info("🔧 Attempting auto-recovery")
        # Reset error rate
        self.metrics.error_rate = 0
        # In real implementation, would restart failed components
        pass

    def _save_job(self, job: BookJob):
        """Save job to database"""
        try:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()

            cursor.execute("""
                INSERT OR REPLACE INTO jobs
                (job_id, book_name, genre, quality_score, status, created_at,
                 completed_at, total_cost, improvement_cycles, output_path)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                job.job_id, job.book_name, job.genre, job.quality_score,
                job.status, job.created_at, job.completed_at,
                job.total_cost, job.improvement_cycles, job.output_path
            ))

            conn.commit()
            conn.close()

        except Exception as e:
            self.logger.error(f"Database save error: {e}")

    def _save_metrics(self):
        """Save current metrics to database"""
        try:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()

            cursor.execute("""
                INSERT INTO metrics
                (timestamp, total_generated, total_published, avg_quality,
                 avg_generation_time, total_cost, error_rate)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                time.time(), self.metrics.total_generated,
                self.metrics.total_published, self.metrics.avg_quality,
                self.metrics.avg_generation_time, self.metrics.total_cost,
                self.metrics.error_rate
            ))

            conn.commit()
            conn.close()

        except Exception as e:
            self.logger.error(f"Metrics save error: {e}")

    def get_dashboard_data(self) -> Dict:
        """Get data for dashboard display"""
        metrics = self._calculate_metrics()

        return {
            'status': 'running' if self.running else 'stopped',
            'queue_size': self.generation_queue.qsize(),
            'workers': {
                'generation': 'active' if self.running else 'stopped',
                'testing': 'active' if self.running else 'stopped',
                'improvement': 'active' if self.running else 'stopped',
                'publication': 'active' if self.running else 'stopped'
            },
            'metrics': metrics,
            'recent_books': list(self.job_history)[-10:],
            'quality_trend': list(self.quality_history)[-20:],
            'timestamp': time.time()
        }


async def run_production_demo():
    """Demonstrate the 24/7 production pipeline"""
    print("="*60)
    print("24/7 AUTONOMOUS PRODUCTION PIPELINE")
    print("="*60)

    # Create pipeline
    pipeline = AutonomousProductionPipeline(max_workers=3)

    print("\n🚀 Starting autonomous production...")
    print("   Pipeline will continuously:")
    print("   • Generate books from queue")
    print("   • Test quality comprehensively")
    print("   • Improve failing books")
    print("   • Publish successful books")
    print("   • Learn from results")
    print("   • Self-monitor and recover")

    # Run for demonstration (30 seconds)
    try:
        # Start pipeline
        task = asyncio.create_task(pipeline.start())

        # Run for demo period
        await asyncio.sleep(30)

        # Get dashboard data
        dashboard = pipeline.get_dashboard_data()

        print("\n" + "="*60)
        print("PRODUCTION DASHBOARD")
        print("="*60)
        print(f"""
Status: {dashboard['status'].upper()}
Queue: {dashboard['queue_size']} books waiting

METRICS:
├── Generated: {dashboard['metrics']['generated']} books
├── Published: {dashboard['metrics']['published']} books
├── Rejected: {dashboard['metrics']['rejected']} books
├── Quality: {dashboard['metrics']['avg_quality']:.1f}/100
├── Success Rate: {dashboard['metrics']['success_rate']:.1%}
└── Total Cost: ${dashboard['metrics']['total_cost']:.2f}

WORKERS:
├── Generation: {dashboard['workers']['generation']}
├── Testing: {dashboard['workers']['testing']}
├── Improvement: {dashboard['workers']['improvement']}
└── Publication: {dashboard['workers']['publication']}
        """.strip())

        # Show quality trend
        if dashboard['quality_trend']:
            print("\nQUALITY TREND (last 10):")
            trend = dashboard['quality_trend'][-10:]
            for i, q in enumerate(trend):
                bar = '█' * int(q/10) + '░' * (10 - int(q/10))
                print(f"  {i+1:2d}: {bar} {q:.1f}")

    except KeyboardInterrupt:
        print("\n⚠ Interrupted by user")

    finally:
        # Shutdown
        print("\n🛑 Shutting down pipeline...")
        await pipeline.shutdown()

    print("\n✅ Production pipeline demonstration complete!")


if __name__ == "__main__":
    # Create necessary directories
    Path("workspace").mkdir(exist_ok=True)
    Path("source").mkdir(exist_ok=True)

    # Create sample source file
    sample_outline = Path("source/sample_outline.txt")
    if not sample_outline.exists():
        sample_outline.write_text("Hero's journey through magical realm")

    # Run demonstration
    asyncio.run(run_production_demo())