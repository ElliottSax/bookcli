"""
Comprehensive Test Suite for Book Factory
Tests all major components and integration points
"""

import unittest
import sys
import json
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import tempfile
import shutil

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

# Import modules to test
from security.config_manager import SecureConfigManager, get_config
from publishing.publishing_orchestrator import PublishingOrchestrator, BookMetadata, PublishingPlatform
from series.coherence_engine import SeriesCoherenceEngine, Character, Location, Event
from marketing.marketing_copy_generator import MarketingCopyGenerator, CopyType
from analytics.success_tracker import SuccessAnalytics, BookPerformance, MetricType
from quality.enhanced_detail_analyzer import EnhancedDetailAnalyzer, DetailType
from feedback.feedback_collector import FeedbackCollector, FeedbackType, Feedback
from covers.template_generator import TemplateGenerator, CoverStyle
from infrastructure.error_handler import ErrorHandler, ErrorSeverity, ErrorCategory


class TestSecurityModule(unittest.TestCase):
    """Test security and configuration management."""

    def setUp(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.env_file = Path(self.temp_dir) / '.env'

        # Create test .env file
        self.env_file.write_text("""
GROQ_API_KEY=test_groq_key_123
DEEPSEEK_API_KEY=test_deepseek_key_456
ENCRYPTION_KEY=test_encryption_key_789
DATABASE_PATH=/tmp/test.db
LOG_LEVEL=DEBUG
        """)

    def tearDown(self):
        """Clean up test environment."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_config_loading(self):
        """Test configuration loading from .env file."""
        config = SecureConfigManager(self.env_file)

        # Check non-sensitive value
        self.assertEqual(config.get('LOG_LEVEL'), 'DEBUG')

        # Check that API keys are encrypted in config
        self.assertEqual(config.config.get('GROQ_API_KEY'), '***ENCRYPTED***')

        # But can be retrieved decrypted
        actual_key = config.get('GROQ_API_KEY')
        self.assertEqual(actual_key, 'test_groq_key_123')

    def test_provider_validation(self):
        """Test LLM provider validation."""
        config = SecureConfigManager(self.env_file)
        providers = config.validate_providers()

        self.assertIn('groq', providers)
        self.assertIn('deepseek', providers)
        self.assertEqual(len(providers), 2)

    def test_safe_config_export(self):
        """Test safe configuration export (masked sensitive values)."""
        config = SecureConfigManager(self.env_file)
        safe_config = config.get_safe_config()

        # API keys should be masked
        self.assertTrue(safe_config['GROQ_API_KEY'].startswith('test'))
        self.assertTrue('***' in safe_config['GROQ_API_KEY'] or '...' in safe_config['GROQ_API_KEY'])


class TestPublishingModule(unittest.TestCase):
    """Test publishing orchestrator."""

    def setUp(self):
        """Set up test environment."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.orchestrator = PublishingOrchestrator(self.temp_dir)

    def tearDown(self):
        """Clean up."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_metadata_preparation(self):
        """Test book metadata preparation."""
        metadata = self.orchestrator.prepare_book_for_publishing(
            title="Test Book",
            author="Test Author",
            description="Test description",
            manuscript_file=Path("test.md"),
            genre="Fantasy",
            keywords=["magic", "adventure"]
        )

        self.assertEqual(metadata.title, "Test Book")
        self.assertEqual(metadata.author, "Test Author")
        self.assertIsNotNone(metadata.publication_date)
        self.assertEqual(len(metadata.keywords), 2)

    def test_pricing_optimization(self):
        """Test pricing optimization."""
        recommendations = self.orchestrator.optimize_pricing(
            base_price=2.99,
            market_analysis=False
        )

        self.assertIn('base_price', recommendations)
        self.assertIn('platform_specific', recommendations)
        self.assertEqual(recommendations['base_price'], 2.99)

    def test_category_optimization(self):
        """Test category optimization."""
        categories = self.orchestrator.optimize_categories(
            genre="fantasy",
            keywords=["magic", "quest", "dragon"]
        )

        self.assertIn('KDP', categories)
        self.assertIn('BISAC', categories)
        self.assertIsInstance(categories['KDP'], list)

    def test_keyword_generation(self):
        """Test keyword generation."""
        keywords = self.orchestrator.generate_keywords(
            title="The Magic Quest",
            description="A thrilling adventure with dragons and magic",
            genre="fantasy"
        )

        self.assertIsInstance(keywords, list)
        self.assertTrue(len(keywords) > 0)
        self.assertIn('fantasy', keywords)


class TestSeriesModule(unittest.TestCase):
    """Test series coherence engine."""

    def setUp(self):
        """Set up test environment."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.engine = SeriesCoherenceEngine("Test Series", self.temp_dir)

    def tearDown(self):
        """Clean up."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_character_tracking(self):
        """Test character addition and tracking."""
        character = self.engine.add_character(
            name="John Doe",
            book_id="book1",
            chapter=1,
            age=30,
            occupation="Detective"
        )

        self.assertEqual(character.name, "John Doe")
        self.assertEqual(character.age, 30)
        self.assertIn(character.id, self.engine.characters)

    def test_location_tracking(self):
        """Test location tracking."""
        location = self.engine.add_location(
            name="Mystery City",
            type="city",
            description="A dark and mysterious city",
            book_id="book1"
        )

        self.assertEqual(location.name, "Mystery City")
        self.assertEqual(location.type, "city")
        self.assertIn(location.id, self.engine.locations)

    def test_event_tracking(self):
        """Test event tracking."""
        event = self.engine.add_event(
            name="The Discovery",
            description="Detective finds crucial evidence",
            book_id="book1",
            chapter=5
        )

        self.assertEqual(event.name, "The Discovery")
        self.assertEqual(event.chapter, 5)
        self.assertIn(event.id, self.engine.events)

    def test_consistency_checking(self):
        """Test consistency violation detection."""
        # Add a deceased character
        character = self.engine.add_character(
            name="Victim",
            book_id="book1",
            chapter=1
        )
        character.status = "deceased"

        # Check consistency with text mentioning deceased character
        violations = self.engine.check_consistency(
            "book2",
            "Victim walked into the room and smiled."
        )

        self.assertTrue(len(violations) > 0)
        self.assertEqual(violations[0]['type'], 'character_status')


class TestMarketingModule(unittest.TestCase):
    """Test marketing copy generator."""

    def setUp(self):
        """Set up test environment."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.generator = MarketingCopyGenerator(self.temp_dir)

    def tearDown(self):
        """Clean up."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_blurb_generation(self):
        """Test blurb generation."""
        manuscript = "This is a test story about adventure and magic."

        suite = self.generator.generate_complete_marketing_suite(
            manuscript=manuscript,
            title="Test Book",
            author="Test Author",
            genre="Fantasy",
            target_audience="Young Adult"
        )

        self.assertIn('tagline', suite)
        self.assertIn('short_blurb', suite)
        self.assertIn('amazon_description', suite)

        # Check tagline is short
        self.assertTrue(len(suite['tagline'].content.split()) < 20)

    def test_platform_optimization(self):
        """Test platform-specific optimization."""
        long_copy = "A" * 500  # Long text

        # Optimize for BookBub (300 char limit)
        optimized = self.generator.optimize_for_platform(
            long_copy,
            'bookbub'
        )

        self.assertTrue(len(optimized) <= 300)

    def test_keyword_extraction(self):
        """Test keyword extraction from manuscript."""
        manuscript = "The brave knight fought the dragon with magic sword in the enchanted forest."

        keywords = self.generator._extract_keywords(manuscript, "fantasy")

        self.assertIn('magic', keywords)
        self.assertTrue(len(keywords) > 0)


class TestAnalyticsModule(unittest.TestCase):
    """Test success analytics."""

    def setUp(self):
        """Set up test environment."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.analytics = SuccessAnalytics(self.temp_dir)

    def tearDown(self):
        """Clean up."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_book_tracking(self):
        """Test book performance tracking."""
        book = self.analytics.track_book(
            book_id="test_book_1",
            title="Test Book",
            genre="Fantasy",
            quality_score=85.5,
            word_count=50000,
            generation_cost=0.05
        )

        self.assertEqual(book.book_id, "test_book_1")
        self.assertEqual(book.quality_score, 85.5)
        self.assertIn("test_book_1", self.analytics.books)

    def test_metrics_update(self):
        """Test metrics update."""
        # Track a book first
        self.analytics.track_book(
            book_id="test_book_1",
            title="Test Book",
            genre="Fantasy",
            quality_score=85.5,
            word_count=50000,
            generation_cost=0.05
        )

        # Update metrics
        success = self.analytics.update_metrics(
            book_id="test_book_1",
            date="2024-01-01",
            metrics={
                MetricType.SALES: 100,
                MetricType.RATING: 4.5,
                MetricType.REVIEWS: 25
            }
        )

        self.assertTrue(success)
        book = self.analytics.books["test_book_1"]
        self.assertEqual(book.total_sales, 100)
        self.assertEqual(book.average_rating, 4.5)

    def test_roi_calculation(self):
        """Test ROI calculation."""
        # Track a book
        book = self.analytics.track_book(
            book_id="test_book_1",
            title="Test Book",
            genre="Fantasy",
            quality_score=85.5,
            word_count=50000,
            generation_cost=0.05,
            price=2.99
        )

        # Add some sales
        self.analytics.update_metrics(
            book_id="test_book_1",
            date="2024-01-01",
            metrics={
                MetricType.SALES: 100,
                MetricType.REVENUE: 299.0
            }
        )

        roi = self.analytics.calculate_roi("test_book_1")

        self.assertIn('revenue', roi)
        self.assertIn('roi_percentage', roi)
        self.assertIn('profit', roi)
        self.assertGreater(roi['roi_percentage'], 0)


class TestQualityModule(unittest.TestCase):
    """Test enhanced detail analyzer."""

    def setUp(self):
        """Set up test environment."""
        self.analyzer = EnhancedDetailAnalyzer(genre="fantasy")

    def test_detail_analysis(self):
        """Test detail density analysis."""
        text = """
        The cold wind bit through her thin jacket as she counted exactly seven
        steps to the door. Her fingers, numb and trembling, fumbled with the
        brass handle. The metal felt like ice against her palm. She could hear
        the distant echo of footsteps - one, two, three, four - growing closer.
        The rough wooden door creaked open, revealing darkness that smelled of
        damp earth and old leather.
        """

        metrics = self.analyzer.analyze(text)

        self.assertGreater(metrics.total_details, 0)
        self.assertGreater(metrics.details_per_1000_words, 0)
        self.assertIn(DetailType.OBSESSIVE, metrics.detail_types)
        self.assertIn('touch', metrics.sensory_coverage)
        self.assertTrue(len(metrics.obsessive_details) > 0)

    def test_sensory_coverage(self):
        """Test sensory coverage detection."""
        text = """
        She saw the bright red sunset. The air smelled of roses and fresh bread.
        She could taste the sweetness on her tongue and hear the birds singing.
        The silk felt smooth against her skin.
        """

        metrics = self.analyzer.analyze(text)
        coverage = metrics.sensory_coverage

        self.assertGreater(coverage['sight'], 0)
        self.assertGreater(coverage['smell'], 0)
        self.assertGreater(coverage['taste'], 0)
        self.assertGreater(coverage['sound'], 0)
        self.assertGreater(coverage['touch'], 0)

    def test_quality_scoring(self):
        """Test quality score calculation."""
        good_text = """
        Her fingers traced exactly seventeen grooves in the ancient stone wall,
        each one precisely three millimeters deep. The temperature dropped two
        degrees with every step down the spiral staircase. She counted: one
        mississippi, two mississippi, timing her descent. The copper taste of
        fear filled her mouth as her left hand gripped the iron railing, knuckles
        white, joints aching from the cold that seeped through her wool gloves.
        """ * 10  # Repeat to get enough words

        metrics = self.analyzer.analyze(good_text)

        self.assertGreater(metrics.detail_quality_score, 50)
        self.assertTrue(len(metrics.recommendations) > 0)


class TestFeedbackModule(unittest.TestCase):
    """Test feedback collector."""

    def setUp(self):
        """Set up test environment."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.collector = FeedbackCollector(self.temp_dir)

    def tearDown(self):
        """Clean up."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_feedback_collection(self):
        """Test feedback collection."""
        feedback = self.collector.collect_feedback(
            book_id="test_book_1",
            type=FeedbackType.REVIEW,
            source="Amazon",
            rating=4.5,
            text="Great book! Loved the characters and plot."
        )

        self.assertEqual(feedback.book_id, "test_book_1")
        self.assertEqual(feedback.rating, 4.5)
        self.assertIsNotNone(feedback.sentiment_score)

    def test_sentiment_analysis(self):
        """Test sentiment analysis."""
        positive_feedback = self.collector.collect_feedback(
            book_id="test_book_1",
            type=FeedbackType.REVIEW,
            source="Test",
            text="Amazing! Absolutely loved it! Best book ever!"
        )

        negative_feedback = self.collector.collect_feedback(
            book_id="test_book_2",
            type=FeedbackType.REVIEW,
            source="Test",
            text="Terrible. Boring. Waste of time. Hated it."
        )

        self.assertGreater(positive_feedback.sentiment_score, 0)
        self.assertLess(negative_feedback.sentiment_score, 0)

    def test_issue_identification(self):
        """Test issue identification in feedback."""
        feedback = self.collector.collect_feedback(
            book_id="test_book_1",
            type=FeedbackType.REVIEW,
            source="Test",
            text="The book was confusing and had too many typos. Very repetitive."
        )

        self.assertIn('confusion', feedback.issues)
        self.assertIn('errors', feedback.issues)
        self.assertIn('repetitive', feedback.issues)


class TestErrorHandling(unittest.TestCase):
    """Test error handling system."""

    def setUp(self):
        """Set up test environment."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.error_handler = ErrorHandler(self.temp_dir)

    def tearDown(self):
        """Clean up."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_error_handling(self):
        """Test basic error handling."""
        try:
            raise ValueError("Test error")
        except Exception as e:
            context = self.error_handler.handle_error(
                e,
                severity=ErrorSeverity.MEDIUM,
                category=ErrorCategory.VALIDATION,
                module="test",
                function="test_function"
            )

        self.assertEqual(context.severity, ErrorSeverity.MEDIUM)
        self.assertEqual(context.category, ErrorCategory.VALIDATION)
        self.assertEqual(context.message, "Test error")
        self.assertIsNotNone(context.recovery_action)

    def test_retry_with_backoff(self):
        """Test retry with exponential backoff."""
        call_count = 0

        def failing_function():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ConnectionError("Network error")
            return "Success"

        result = self.error_handler.retry_with_backoff(
            failing_function,
            max_retries=3,
            backoff_base=0.1  # Fast for testing
        )

        self.assertEqual(result, "Success")
        self.assertEqual(call_count, 3)

    def test_error_statistics(self):
        """Test error statistics tracking."""
        # Generate some errors
        for i in range(5):
            try:
                raise ValueError(f"Test error {i}")
            except Exception as e:
                self.error_handler.handle_error(
                    e,
                    severity=ErrorSeverity.LOW if i < 3 else ErrorSeverity.HIGH
                )

        stats = self.error_handler.get_error_statistics()

        self.assertEqual(stats['total_errors'], 5)
        self.assertIn('low', stats['by_severity'])
        self.assertIn('high', stats['by_severity'])


class TestIntegration(unittest.TestCase):
    """Integration tests for multiple modules."""

    def setUp(self):
        """Set up test environment."""
        self.temp_dir = Path(tempfile.mkdtemp())

    def tearDown(self):
        """Clean up."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_quality_to_analytics_flow(self):
        """Test flow from quality analysis to analytics tracking."""
        # Analyze text quality
        analyzer = EnhancedDetailAnalyzer(genre="fantasy")
        text = "The cold wind howled through the ancient forest." * 100
        metrics = analyzer.analyze(text)

        # Track in analytics
        analytics = SuccessAnalytics(self.temp_dir)
        book = analytics.track_book(
            book_id="test_book",
            title="Test",
            genre="Fantasy",
            quality_score=metrics.detail_quality_score,
            word_count=len(text.split()),
            generation_cost=0.05
        )

        self.assertEqual(book.quality_score, metrics.detail_quality_score)

    def test_feedback_to_improvement_flow(self):
        """Test flow from feedback to improvement suggestions."""
        # Collect feedback
        collector = FeedbackCollector(self.temp_dir)

        for i in range(10):
            collector.collect_feedback(
                book_id="test_book",
                type=FeedbackType.REVIEW,
                source="Test",
                rating=3.0 if i < 5 else 4.5,
                text="Confusing plot" if i < 5 else "Great story"
            )

        # Get actionable insights
        insights = collector.get_actionable_insights("test_book", min_frequency=3)

        self.assertIn('critical_issues', insights)
        self.assertTrue(len(insights['critical_issues']) > 0)


def run_tests():
    """Run all tests."""
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # Add all test classes
    test_classes = [
        TestSecurityModule,
        TestPublishingModule,
        TestSeriesModule,
        TestMarketingModule,
        TestAnalyticsModule,
        TestQualityModule,
        TestFeedbackModule,
        TestErrorHandling,
        TestIntegration
    ]

    for test_class in test_classes:
        suite.addTests(loader.loadTestsFromTestCase(test_class))

    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # Print summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print(f"Success rate: {((result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun * 100):.1f}%")

    return result.wasSuccessful()


if __name__ == '__main__':
    success = run_tests()
    sys.exit(0 if success else 1)