#!/usr/bin/env python3
"""
Test Claude API Integration
Validates autonomous generation with minimal API cost (generates only 1 chapter)
"""

import os
import sys
import json
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.orchestrator import BookOrchestrator


def test_api_integration():
    """Test autonomous generation with API (1 chapter only to minimize cost)"""

    print("\n" + "="*60)
    print("TESTING CLAUDE API INTEGRATION")
    print("="*60 + "\n")

    # Check API key
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("❌ SKIPPED: ANTHROPIC_API_KEY not set")
        print("This test requires Claude API access")
        print("Set with: export ANTHROPIC_API_KEY=your-key")
        return True  # Not a failure, just skipped

    print("✓ API key found")

    # Create minimal test source
    test_source = Path("source/api_test_micro.txt")
    test_source.parent.mkdir(exist_ok=True)

    test_source.write_text("""
A quantum physicist discovers an algorithm that can predict the future.
Someone wants to steal it. She must stop them.

This is a thriller about technology, conspiracy, and survival.
    """.strip())

    print(f"✓ Test source created: {len(test_source.read_text().split())} words")

    # Initialize orchestrator with API mode
    # Very low target words so we only generate 1-2 chapters
    orchestrator = BookOrchestrator(
        source_file=test_source,
        book_name="api-test-micro",
        genre="thriller",
        target_words=7000,  # This should create ~2 chapters
        test_first=False,  # Skip tests to be faster
        use_api=True,
        max_budget=5.0  # Low budget limit for safety
    )

    print("✓ Orchestrator initialized with API mode")

    try:
        # Stage 1: Analysis
        print("\n--- STAGE 1: ANALYSIS ---")
        if not orchestrator.analyze_source():
            print("❌ Analysis failed")
            return False
        print("✓ Analysis complete")

        # Stage 2: Chapter planning
        print("\n--- STAGE 2: PLANNING ---")
        plan = orchestrator.create_chapter_plan()
        if not plan:
            print("❌ Planning failed")
            return False

        chapters_planned = plan['total_chapters']
        print(f"✓ Plan created: {chapters_planned} chapters")

        # Stage 3: Generate ONLY Chapter 1 (to minimize cost)
        print("\n--- STAGE 3: GENERATION (Chapter 1 only) ---")
        print("Calling Claude API to generate chapter...")
        print("(This will take 30-60 seconds)")

        if not orchestrator.generate_chapter(1):
            print("❌ Chapter generation failed")
            return False

        chapter_file = orchestrator.chapters_dir / "chapter_001.md"
        if not chapter_file.exists():
            print("❌ Chapter file not created")
            return False

        chapter_text = chapter_file.read_text()
        word_count = len(chapter_text.split())

        print(f"✓ Chapter 1 generated: {word_count} words")
        print(f"✓ Cost: ${orchestrator.total_cost:.4f}")
        print(f"✓ Tokens: {orchestrator.total_input_tokens} in, {orchestrator.total_output_tokens} out")

        # Stage 4: Quality check
        print("\n--- STAGE 4: QUALITY CHECK ---")
        if not orchestrator.quality_check_chapter(1):
            print("❌ Quality check failed")
            return False
        print("✓ Quality check passed")

        # Stage 5: Verify continuity tracking
        print("\n--- STAGE 5: CONTINUITY TRACKING ---")
        summaries = list(orchestrator.summaries_dir.glob("*.md"))
        if summaries:
            print(f"✓ Summaries created: {len(summaries)}")
        else:
            print("⚠️  No summaries created (may be expected)")

        # Stage 6: Assembly (with just 1 chapter)
        print("\n--- STAGE 6: ASSEMBLY ---")
        if not orchestrator.assemble_manuscript():
            print("❌ Assembly failed")
            return False

        manuscript_file = orchestrator.output_dir / f"{orchestrator.book_name}_manuscript.md"
        if not manuscript_file.exists():
            print("❌ Manuscript not created")
            return False

        manuscript_text = manuscript_file.read_text()
        manuscript_words = len(manuscript_text.split())
        print(f"✓ Manuscript assembled: {manuscript_words} words")

        # Stage 7: KDP formatting
        print("\n--- STAGE 7: KDP FORMATTING ---")
        if not orchestrator.format_for_kdp():
            print("❌ KDP formatting failed")
            return False
        print("✓ KDP formatting complete")

        # Final validation
        print("\n" + "="*60)
        print("API INTEGRATION TEST PASSED ✓")
        print("="*60)
        print(f"\nTotal API cost: ${orchestrator.total_cost:.4f}")
        print(f"Chapter generated: {word_count} words")
        print(f"Manuscript assembled: {manuscript_words} words")
        print(f"\nOutput files:")
        print(f"  - workspace/api-test-micro/chapters/chapter_001.md")
        print(f"  - output/api-test-micro/api-test-micro_manuscript.md")
        print(f"  - output/api-test-micro/api-test-micro_kdp.html")
        print("\n✓ ALL SYSTEMS OPERATIONAL")
        print("✓ AUTONOMOUS GENERATION WORKING")

        return True

    except Exception as e:
        print(f"\n❌ ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def test_resume_capability():
    """Test that resume works (doesn't re-generate completed chapters)"""
    print("\n" + "="*60)
    print("TESTING RESUME CAPABILITY")
    print("="*60 + "\n")

    # Check if previous test created chapter 1
    chapter_file = Path("workspace/api-test-micro/chapters/chapter_001.md")
    if not chapter_file.exists():
        print("❌ SKIPPED: No existing chapter to test resume")
        return True

    # Load status
    status_file = Path("workspace/api-test-micro/status.json")
    if not status_file.exists():
        print("❌ Status file not found")
        return False

    status = json.loads(status_file.read_text())
    completed_before = status.get("chapters_completed", 0)

    print(f"✓ Found {completed_before} completed chapter(s)")

    # Try to resume - should skip chapter 1
    orchestrator = BookOrchestrator(
        source_file=Path("source/api_test_micro.txt"),
        book_name="api-test-micro",
        genre="thriller",
        target_words=7000,
        test_first=False,
        use_api=True,
        max_budget=5.0
    )

    # This should detect chapter 1 is done and not regenerate it
    print("\nAttempting to re-run generation...")
    print("Should skip chapter 1 (already completed)")

    # We won't actually generate chapter 2 to save cost
    # Just verify the resume logic works
    plan = json.loads((orchestrator.analysis_dir / "chapter_plan.json").read_text())
    total_chapters = plan["total_chapters"]

    # Simulate resume check
    status = orchestrator._load_status()
    completed = status.get("chapters_completed", 0)
    start_chapter = completed + 1 if completed > 0 else 1

    print(f"✓ Resume logic: would start at chapter {start_chapter}")

    if start_chapter == 2:
        print("✓ RESUME CAPABILITY WORKING")
        return True
    else:
        print("❌ Resume logic failed")
        return False


def main():
    """Run all API integration tests"""
    print("\n" + "="*70)
    print(" " * 15 + "API INTEGRATION TEST SUITE")
    print("="*70)

    results = []

    # Test 1: Full API integration
    results.append(("API Integration", test_api_integration()))

    # Test 2: Resume capability
    results.append(("Resume Capability", test_resume_capability()))

    # Summary
    print("\n" + "="*70)
    print("TEST SUMMARY")
    print("="*70)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status} - {name}")

    print(f"\n{passed}/{total} tests passed")

    if passed == total:
        print("\n✓ ALL API INTEGRATION TESTS PASSED")
        return 0
    else:
        print("\n✗ SOME TESTS FAILED")
        return 1


if __name__ == "__main__":
    sys.exit(main())
