#!/usr/bin/env python3
"""
Iterative testing - test each module independently
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

def test_module(name, test_func):
    """Test a single module"""
    try:
        print(f"\n{'='*50}")
        print(f"Testing: {name}")
        print(f"{'='*50}")
        test_func()
        print(f"✅ {name} - PASSED")
        return True
    except Exception as e:
        print(f"❌ {name} - FAILED: {str(e)}")
        return False

def test_security():
    """Test security module"""
    from security.config_manager import SecureConfigManager
    # Create with missing file - should handle gracefully
    config = SecureConfigManager(Path("/tmp/missing.env"))
    assert config is not None
    print("  - Config manager created")

def test_publishing():
    """Test publishing module"""
    from publishing.publishing_orchestrator import PublishingOrchestrator, BookMetadata
    orch = PublishingOrchestrator()

    metadata = BookMetadata(
        title="Test",
        author="Author",
        description="Desc",
        isbn="1234567890123",
        price=9.99
    )

    # Test dry run
    from publishing.publishing_orchestrator import PublishingPlatform
    results = orch.publish_to_platforms([PublishingPlatform.KDP], metadata, dry_run=True)
    assert len(results) == 1
    print(f"  - Dry run: {results[0].message}")

def test_series():
    """Test series coherence"""
    from series.coherence_engine import SeriesCoherenceEngine
    import tempfile

    temp_dir = tempfile.mkdtemp()
    engine = SeriesCoherenceEngine("test", Path(temp_dir))

    # Add character
    char = engine.add_character("Alice", "book1", 1, age=25)
    assert char.name == "Alice"
    print(f"  - Added character: {char.name}")

    # Add location
    loc = engine.add_location("Library", "book1", 2, description="Old library")
    assert loc.name == "Library"
    print(f"  - Added location: {loc.name}")

def test_marketing():
    """Test marketing copy generation"""
    from marketing.marketing_copy_generator import MarketingCopyGenerator
    gen = MarketingCopyGenerator()

    blurb = gen.generate_blurb(
        title="Test Book",
        genre="Fiction",
        protagonist="Hero",
        conflict="Big problem",
        stakes="Everything",
        hook="What if?"
    )
    assert len(blurb) < 250  # Amazon limit
    print(f"  - Generated blurb: {len(blurb)} chars")

def test_analytics():
    """Test analytics"""
    from analytics.success_tracker import SuccessAnalytics
    import tempfile

    analytics = SuccessAnalytics(Path(tempfile.mkdtemp()))

    # Track book
    analytics.track_book(
        book_id="test123",
        title="Test",
        genre="Fiction",
        word_count=50000,
        quality_score=85.0
    )

    metrics = analytics.get_metrics("test123")
    assert metrics["word_count"] == 50000
    print(f"  - Tracked book: {metrics['title']}")

def test_covers():
    """Test cover templates"""
    from covers.template_generator import CoverTemplateGenerator
    gen = CoverTemplateGenerator()

    template = gen.generate_template("Fantasy", "minimalist")
    assert "background" in template
    assert "title_position" in template
    print(f"  - Generated template: {template['style']}")

def test_quality():
    """Test quality analyzer"""
    from quality.enhanced_detail_analyzer import EnhancedDetailAnalyzer

    analyzer = EnhancedDetailAnalyzer(genre="thriller")
    text = "The temperature was exactly 72.3 degrees."

    analysis = analyzer.analyze(text)
    assert analysis.total_details > 0
    print(f"  - Found {analysis.total_details} details")

def test_feedback():
    """Test feedback collector"""
    from feedback.feedback_collector import FeedbackCollector
    import tempfile

    collector = FeedbackCollector(Path(tempfile.mkdtemp()))

    collector.add_feedback(
        book_id="test123",
        source="Amazon",
        rating=5,
        text="Great book!"
    )

    feedback = collector.get_feedback("test123")
    assert len(feedback) == 1
    print(f"  - Collected feedback: rating {feedback[0].rating}")

def test_error_handler():
    """Test error handling"""
    from infrastructure.error_handler import ErrorHandler, ErrorSeverity

    handler = ErrorHandler()

    # Test retry
    attempts = 0
    @handler.with_retry(max_attempts=2)
    def retry_func():
        nonlocal attempts
        attempts += 1
        if attempts < 2:
            raise ValueError("Retry me")
        return "Success"

    result = retry_func()
    assert result == "Success"
    assert attempts == 2
    print(f"  - Retry logic: {attempts} attempts")

def test_batch():
    """Test batch processing"""
    from batch.batch_processor import BatchProcessor, JobPriority

    processor = BatchProcessor(max_workers=2)

    job = processor.add_job(
        job_type="test",
        params={"test": True},
        priority=JobPriority.HIGH
    )

    assert job.id is not None
    print(f"  - Created job: {job.id}")

def main():
    """Run all tests"""
    print("\n" + "="*60)
    print("🧪 ITERATIVE MODULE TESTING")
    print("="*60)

    tests = [
        ("Security Config", test_security),
        ("Publishing Orchestrator", test_publishing),
        ("Series Coherence", test_series),
        ("Marketing Copy", test_marketing),
        ("Success Analytics", test_analytics),
        ("Cover Templates", test_covers),
        ("Quality Analyzer", test_quality),
        ("Feedback Collector", test_feedback),
        ("Error Handler", test_error_handler),
        ("Batch Processor", test_batch),
    ]

    results = []
    for name, test_func in tests:
        passed = test_module(name, test_func)
        results.append((name, passed))

    # Summary
    print("\n" + "="*60)
    print("📊 TEST SUMMARY")
    print("="*60)

    passed_count = sum(1 for _, passed in results if passed)
    total = len(results)

    print(f"\nTotal: {total} modules")
    print(f"✅ Passed: {passed_count}")
    print(f"❌ Failed: {total - passed_count}")
    print(f"🎯 Success Rate: {passed_count/total*100:.1f}%")

    print("\nDetails:")
    for name, passed in results:
        status = "✅" if passed else "❌"
        print(f"  {status} {name}")

    if passed_count == total:
        print("\n🏆 All modules passed!")
    elif passed_count >= total * 0.8:
        print("\n✅ Most modules working correctly")
    else:
        print("\n⚠️  Several modules need fixes")

if __name__ == "__main__":
    main()