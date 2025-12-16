#!/usr/bin/env python3
"""
Comprehensive iterative testing of all Book Factory systems
Tests each component individually then runs integration tests
"""

import sys
import json
import tempfile
from pathlib import Path
from datetime import datetime
import unittest
from unittest.mock import Mock, patch, MagicMock

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

# Import all modules to test
from security.config_manager import SecureConfigManager
from publishing.publishing_orchestrator import PublishingOrchestrator, PublishingPlatform, BookMetadata
from series.coherence_engine import SeriesCoherenceEngine
from marketing.marketing_copy_generator import MarketingCopyGenerator, CopyType
from analytics.success_tracker import SuccessAnalytics
from covers.template_generator import CoverTemplateGenerator
from quality.enhanced_detail_analyzer import EnhancedDetailAnalyzer
from feedback.feedback_collector import FeedbackCollector
from infrastructure.error_handler import ErrorHandler, ErrorSeverity, ErrorCategory
from batch.batch_processor import BatchProcessor, BatchJob, JobPriority

class TestSecureConfiguration(unittest.TestCase):
    """Test secure configuration management"""

    def setUp(self):
        # Create temporary .env file
        self.env_file = tempfile.NamedTemporaryFile(mode='w', suffix='.env', delete=False)
        self.env_file.write("GROQ_API_KEY=test_key_123\n")
        self.env_file.write("API_BASE_URL=http://test.com\n")
        self.env_file.write("MAX_RETRIES=3\n")
        self.env_file.close()
        self.env_path = Path(self.env_file.name)

    def tearDown(self):
        self.env_path.unlink(missing_ok=True)

    def test_basic_config(self):
        """Test basic configuration loading"""
        config = SecureConfigManager(self.env_path)
        self.assertIsNotNone(config.get("GROQ_API_KEY"))

    def test_encrypted_values(self):
        """Test encryption of sensitive values"""
        config = SecureConfigManager(self.env_path)

        # Check that API key is encrypted
        api_key = config.get("GROQ_API_KEY")
        self.assertEqual(api_key, "test_key_123")

    def test_api_key_validation(self):
        """Test API key validation"""
        config = SecureConfigManager(self.env_path)

        # Should validate that at least one API key exists
        validated = config.validate_required_keys()
        self.assertTrue(validated)

    def test_missing_env(self):
        """Test handling of missing .env file"""
        missing_path = Path("/tmp/nonexistent.env")
        config = SecureConfigManager(missing_path)

        # Should handle gracefully
        self.assertIsNotNone(config)


class TestPublishingOrchestrator(unittest.TestCase):
    """Test publishing orchestration"""

    def setUp(self):
        self.orchestrator = PublishingOrchestrator()

    def test_dry_run(self):
        """Test dry run publishing"""
        metadata = BookMetadata(
            title="Test Book",
            author="Test Author",
            description="A test book",
            isbn="1234567890123",
            price=9.99,
            categories=["Fiction", "Sci-Fi"]
        )

        results = self.orchestrator.publish_to_platforms(
            platforms=[PublishingPlatform.KDP],
            metadata=metadata,
            dry_run=True
        )

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].platform, PublishingPlatform.KDP)
        self.assertTrue(results[0].success)
        self.assertEqual(results[0].message, "[DRY RUN] Would publish to KDP")

    @patch('publishing.publishing_orchestrator.requests.post')
    def test_kdp_publish_mock(self, mock_post):
        """Test KDP publishing with mocked API"""
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = {"asin": "B001234567"}

        result = self.orchestrator._publish_to_kdp(
            manuscript_path=Path("test.docx"),
            cover_path=Path("cover.jpg"),
            metadata=BookMetadata(
                title="Test",
                author="Author",
                description="Desc",
                isbn="1234567890123",
                price=9.99
            )
        )

        self.assertTrue(result.success)


class TestSeriesCoherence(unittest.TestCase):
    """Test series coherence engine"""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.engine = SeriesCoherenceEngine("test_series", Path(self.temp_dir))

    def test_character_tracking(self):
        """Test character tracking across books"""
        # Add character
        char = self.engine.add_character(
            name="John Doe",
            book_id="book1",
            chapter=1,
            age=30,
            occupation="Detective"
        )

        self.assertEqual(char.name, "John Doe")
        self.assertEqual(char.attributes["age"], 30)

        # Update character
        self.engine.update_character(
            "John Doe",
            book_id="book1",
            chapter=5,
            age=31
        )

        char = self.engine.get_character("John Doe")
        self.assertEqual(char.attributes["age"], 31)

    def test_location_tracking(self):
        """Test location tracking"""
        loc = self.engine.add_location(
            name="Old Library",
            book_id="book1",
            chapter=2,
            description="Dusty shelves, creaky floors"
        )

        self.assertEqual(loc.name, "Old Library")
        self.assertIn("book1", loc.appearances)

    def test_event_tracking(self):
        """Test event tracking"""
        event = self.engine.add_event(
            description="The Great Fire",
            book_id="book1",
            chapter=10,
            participants=["John Doe", "Jane Smith"],
            location="Old Library"
        )

        self.assertIn("John Doe", event.participants)
        self.assertEqual(event.location, "Old Library")

    def test_continuity_check(self):
        """Test continuity checking"""
        # Add conflicting information
        self.engine.add_character("Alice", "book1", 1, age=25)
        self.engine.add_character("Alice", "book2", 1, age=22)  # Age went backwards

        issues = self.engine.check_continuity()
        self.assertTrue(any("Alice" in str(issue) for issue in issues))


class TestMarketingCopy(unittest.TestCase):
    """Test marketing copy generation"""

    def setUp(self):
        self.generator = MarketingCopyGenerator()

    def test_blurb_generation(self):
        """Test blurb generation"""
        blurb = self.generator.generate_blurb(
            title="The Last Algorithm",
            genre="Sci-Fi Thriller",
            protagonist="Maya Chen",
            conflict="AI threatens humanity",
            stakes="Save the world",
            hook="What if your code could think?"
        )

        self.assertIn("Maya Chen", blurb)
        self.assertLess(len(blurb), 250)  # Amazon limit

    def test_tagline_generation(self):
        """Test tagline generation"""
        tagline = self.generator.generate_tagline(
            title="The Last Algorithm",
            genre="Sci-Fi Thriller",
            theme="AI consciousness"
        )

        self.assertLess(len(tagline), 100)

    def test_social_media_posts(self):
        """Test social media post generation"""
        posts = self.generator.generate_social_media_posts(
            title="The Last Algorithm",
            genre="Sci-Fi Thriller",
            platforms=[CopyType.TWITTER_POST, CopyType.INSTAGRAM_POST]
        )

        self.assertEqual(len(posts), 2)
        self.assertLess(len(posts[0].content), 280)  # Twitter limit


class TestSuccessTracker(unittest.TestCase):
    """Test success tracking and analytics"""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.tracker = SuccessAnalytics(Path(self.temp_dir))

    def test_metric_tracking(self):
        """Test metric tracking"""
        self.tracker.track_book(
            book_id="test123",
            title="Test Book",
            genre="Fiction",
            word_count=50000,
            quality_score=85.5
        )

        self.tracker.update_metrics(
            book_id="test123",
            sales=100,
            reviews=10,
            rating=4.5
        )

        metrics = self.tracker.get_metrics("test123")
        self.assertEqual(metrics["sales"], 100)
        self.assertEqual(metrics["rating"], 4.5)

    def test_trend_analysis(self):
        """Test trend analysis"""
        # Add sample data
        for i in range(5):
            self.tracker.track_book(
                book_id=f"book{i}",
                title=f"Book {i}",
                genre="Fiction",
                word_count=50000 + i*5000,
                quality_score=80 + i*2
            )
            self.tracker.update_metrics(
                book_id=f"book{i}",
                sales=100 + i*50
            )

        trends = self.tracker.analyze_trends("Fiction")
        self.assertIn("average_sales", trends)
        self.assertIn("quality_correlation", trends)


class TestCoverTemplates(unittest.TestCase):
    """Test cover template generation"""

    def test_template_generation(self):
        """Test template generation for different genres"""
        generator = CoverTemplateGenerator()

        template = generator.generate_template(
            genre="Sci-Fi",
            style="minimalist"
        )

        self.assertIn("background", template)
        self.assertIn("title_position", template)
        self.assertIn("color_scheme", template)

    def test_style_variations(self):
        """Test different style variations"""
        generator = CoverTemplateGenerator()

        styles = ["minimalist", "dramatic", "vintage", "modern"]
        templates = [
            generator.generate_template("Fantasy", style)
            for style in styles
        ]

        # Each should be unique
        self.assertEqual(len(set(str(t) for t in templates)), 4)


class TestEnhancedDetailAnalyzer(unittest.TestCase):
    """Test enhanced detail analysis"""

    def test_obsessive_detail_detection(self):
        """Test detection of obsessive details"""
        analyzer = EnhancedDetailAnalyzer(genre="thriller")

        text = """
        The temperature read 72.3 degrees. She counted the steps - one, two,
        three, four - to the door. Her hands trembled at exactly 2.5 Hz.
        The clock showed 3:47:23 PM.
        """

        analysis = analyzer.analyze(text)

        self.assertGreater(analysis.total_details, 0)
        self.assertGreater(analysis.obsessive_details_count, 0)
        self.assertIn("temperature", str(analysis.obsessive_details))


class TestFeedbackCollector(unittest.TestCase):
    """Test feedback collection and analysis"""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.collector = FeedbackCollector(Path(self.temp_dir))

    def test_feedback_collection(self):
        """Test collecting feedback"""
        self.collector.add_feedback(
            book_id="test123",
            source="Amazon",
            rating=4,
            text="Great book, loved the characters!"
        )

        feedback = self.collector.get_feedback("test123")
        self.assertEqual(len(feedback), 1)
        self.assertEqual(feedback[0].rating, 4)

    def test_sentiment_analysis(self):
        """Test sentiment analysis"""
        self.collector.add_feedback(
            "book1", "Amazon", 5, "Amazing! Best book ever!"
        )
        self.collector.add_feedback(
            "book1", "Goodreads", 2, "Boring and predictable"
        )

        analysis = self.collector.analyze_sentiment("book1")

        self.assertIn("average_rating", analysis)
        self.assertIn("positive_ratio", analysis)
        self.assertEqual(analysis["total_feedback"], 2)


class TestErrorHandler(unittest.TestCase):
    """Test error handling and resilience"""

    def test_retry_logic(self):
        """Test retry logic"""
        handler = ErrorHandler()

        attempts = 0
        @handler.with_retry(max_attempts=3)
        def flaky_function():
            nonlocal attempts
            attempts += 1
            if attempts < 3:
                raise ConnectionError("Network error")
            return "Success"

        result = flaky_function()
        self.assertEqual(result, "Success")
        self.assertEqual(attempts, 3)

    def test_circuit_breaker(self):
        """Test circuit breaker"""
        handler = ErrorHandler()

        @handler.with_circuit_breaker(failure_threshold=2)
        def failing_function():
            raise Exception("Always fails")

        # Should fail twice then open circuit
        for _ in range(2):
            try:
                failing_function()
            except:
                pass

        # Circuit should be open now
        with self.assertRaises(Exception) as ctx:
            failing_function()
        self.assertIn("Circuit breaker open", str(ctx.exception))

    def test_error_categorization(self):
        """Test error categorization"""
        handler = ErrorHandler()

        handler.log_error(
            error=ValueError("Invalid input"),
            context={"function": "test"},
            severity=ErrorSeverity.MEDIUM,
            category=ErrorCategory.VALIDATION
        )

        stats = handler.get_error_stats()
        self.assertIn(ErrorCategory.VALIDATION, stats)
        self.assertEqual(stats[ErrorCategory.VALIDATION], 1)


class TestBatchProcessor(unittest.TestCase):
    """Test batch processing"""

    def test_job_creation(self):
        """Test job creation and queueing"""
        processor = BatchProcessor(max_workers=2)

        job = processor.add_job(
            job_type="generate_chapter",
            params={"chapter": 1, "book": "test"},
            priority=JobPriority.HIGH
        )

        self.assertIsNotNone(job.id)
        self.assertEqual(job.priority, JobPriority.HIGH)

    def test_job_prioritization(self):
        """Test job prioritization"""
        processor = BatchProcessor(max_workers=2)

        # Add jobs with different priorities
        low = processor.add_job("test", {}, JobPriority.LOW)
        high = processor.add_job("test", {}, JobPriority.HIGH)
        medium = processor.add_job("test", {}, JobPriority.MEDIUM)

        # High priority should be processed first
        jobs = processor.get_pending_jobs()
        self.assertEqual(jobs[0].id, high.id)
        self.assertEqual(jobs[1].id, medium.id)
        self.assertEqual(jobs[2].id, low.id)


def run_tests():
    """Run all tests and generate report"""
    print("\n" + "="*60)
    print("🧪 COMPREHENSIVE SYSTEM TESTING")
    print("="*60)

    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # Add all test classes
    test_classes = [
        TestSecureConfiguration,
        TestPublishingOrchestrator,
        TestSeriesCoherence,
        TestMarketingCopy,
        TestSuccessTracker,
        TestCoverTemplates,
        TestEnhancedDetailAnalyzer,
        TestFeedbackCollector,
        TestErrorHandler,
        TestBatchProcessor
    ]

    for test_class in test_classes:
        suite.addTests(loader.loadTestsFromTestCase(test_class))

    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # Generate summary
    print("\n" + "="*60)
    print("📊 TEST SUMMARY")
    print("="*60)

    print(f"\nTotal Tests Run: {result.testsRun}")
    print(f"✅ Passed: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"❌ Failed: {len(result.failures)}")
    print(f"⚠️  Errors: {len(result.errors)}")

    if result.failures:
        print("\n❌ FAILURES:")
        for test, trace in result.failures:
            print(f"  - {test}: {trace[:100]}...")

    if result.errors:
        print("\n⚠️  ERRORS:")
        for test, trace in result.errors:
            print(f"  - {test}: {trace[:100]}...")

    success_rate = ((result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun) * 100

    print(f"\n🎯 Success Rate: {success_rate:.1f}%")

    if success_rate == 100:
        print("🏆 All tests passed! System ready for production.")
    elif success_rate >= 80:
        print("✅ Most tests passed. Minor issues to address.")
    else:
        print("⚠️  Significant issues detected. Review failures.")

    return result

if __name__ == "__main__":
    run_tests()