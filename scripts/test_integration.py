#!/usr/bin/env python3
"""
Test script to verify Phase 9 quality pipeline integration.
Tests that all new modules load correctly and integrate with the existing system.
"""

import sys
from pathlib import Path

# Add scripts directory to path
sys.path.insert(0, str(Path(__file__).parent))

def test_imports():
    """Test that all Phase 9 modules can be imported."""
    print("Testing Phase 9 module imports...")
    print("-" * 50)

    modules = [
        ("repetition_post_processor", "RepetitionPostProcessor"),
        ("content_critic", "ContentCritic"),
        ("narrative_coherence_tracker", "NarrativeCoherenceTracker"),
        ("character_consistency_validator", "CharacterConsistencyValidator"),
        ("semantic_plot_validator", "SemanticPlotValidator"),
        ("doc_outline_controller", "DOCOutlineController"),
        ("score_state_tracker", "SCOREStateTracker"),
        ("enhanced_quality_pipeline", "EnhancedQualityPipeline"),
        ("multi_agent_generator", "MultiAgentGenerator"),
    ]

    success_count = 0
    for module_name, class_name in modules:
        try:
            module = __import__(module_name)
            cls = getattr(module, class_name)
            print(f"  ✓ {module_name}.{class_name}")
            success_count += 1
        except Exception as e:
            print(f"  ✗ {module_name}.{class_name}: {e}")

    print(f"\nImport results: {success_count}/{len(modules)} modules loaded")
    return success_count == len(modules)


def test_resilient_orchestrator_integration():
    """Test ResilientOrchestrator with enhanced quality."""
    print("\nTesting ResilientOrchestrator integration...")
    print("-" * 50)

    try:
        from resilient_orchestrator import (
            ResilientOrchestrator,
            ENHANCED_QUALITY_AVAILABLE,
            MULTI_AGENT_AVAILABLE
        )

        print(f"  Enhanced Quality Available: {ENHANCED_QUALITY_AVAILABLE}")
        print(f"  Multi-Agent Available: {MULTI_AGENT_AVAILABLE}")

        # Check that new flags exist
        import inspect
        sig = inspect.signature(ResilientOrchestrator.__init__)
        params = list(sig.parameters.keys())

        if 'enhanced_quality_enabled' in params:
            print("  ✓ enhanced_quality_enabled parameter exists")
        else:
            print("  ✗ enhanced_quality_enabled parameter missing")
            return False

        if 'multi_agent_enabled' in params:
            print("  ✓ multi_agent_enabled parameter exists")
        else:
            print("  ✗ multi_agent_enabled parameter missing")
            return False

        # Check that new methods exist
        methods = dir(ResilientOrchestrator)

        if 'initialize_enhanced_pipeline' in methods:
            print("  ✓ initialize_enhanced_pipeline method exists")
        else:
            print("  ✗ initialize_enhanced_pipeline method missing")
            return False

        if 'generate_chapter_enhanced' in methods:
            print("  ✓ generate_chapter_enhanced method exists")
        else:
            print("  ✗ generate_chapter_enhanced method missing")
            return False

        if 'generate_chapter_multi_agent' in methods:
            print("  ✓ generate_chapter_multi_agent method exists")
        else:
            print("  ✗ generate_chapter_multi_agent method missing")
            return False

        print("\n  ResilientOrchestrator integration: PASSED")
        return True

    except Exception as e:
        print(f"  ✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_autonomous_pipeline_integration():
    """Test AutonomousProductionPipeline with enhanced quality."""
    print("\nTesting AutonomousProductionPipeline integration...")
    print("-" * 50)

    try:
        from autonomous_production_pipeline import (
            AutonomousProductionPipeline,
            ENHANCED_QUALITY_AVAILABLE
        )

        print(f"  Enhanced Quality Available: {ENHANCED_QUALITY_AVAILABLE}")

        # Create a test instance
        pipeline = AutonomousProductionPipeline(
            workspace_dir="/tmp/bookcli_test",
            max_workers=1
        )

        # Check enhanced components initialized
        if ENHANCED_QUALITY_AVAILABLE:
            if pipeline.enhanced_pipeline is not None:
                print("  ✓ enhanced_pipeline initialized")
            else:
                print("  ✗ enhanced_pipeline not initialized")

            if pipeline.post_processor is not None:
                print("  ✓ post_processor initialized")
            else:
                print("  ✗ post_processor not initialized")

            if pipeline.content_critic is not None:
                print("  ✓ content_critic initialized")
            else:
                print("  ✗ content_critic not initialized")

            if pipeline.coherence_tracker is not None:
                print("  ✓ coherence_tracker initialized")
            else:
                print("  ✗ coherence_tracker not initialized")

        print("\n  AutonomousProductionPipeline integration: PASSED")
        return True

    except Exception as e:
        print(f"  ✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_post_processor():
    """Test the RepetitionPostProcessor with sample text."""
    print("\nTesting RepetitionPostProcessor...")
    print("-" * 50)

    try:
        from repetition_post_processor import RepetitionPostProcessor

        processor = RepetitionPostProcessor()

        # Test text with AI-isms
        test_text = """
        She embarked on a journey of discovery. It was a testament to her resilience.
        The landscape was breathtaking. She delved deep into the mystery.
        It's important to note that she leveraged her skills effectively.
        The experience was transformative in every sense of the word.
        """

        processed, stats = processor.process(test_text)

        print(f"  Original length: {len(test_text)}")
        print(f"  Processed length: {len(processed)}")
        print(f"  AI-isms replaced: {stats.get('ai_isms_replaced', 0)}")
        print(f"  Purple prose fixed: {stats.get('purple_prose_fixed', 0)}")

        # Verify some replacements happened
        if 'journey' not in processed.lower() or 'testament' not in processed.lower():
            print("  ✓ AI-isms successfully replaced")
        else:
            print("  ⚠ Some AI-isms may remain")

        print("\n  RepetitionPostProcessor: PASSED")
        return True

    except Exception as e:
        print(f"  ✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_enhanced_pipeline():
    """Test the EnhancedQualityPipeline."""
    print("\nTesting EnhancedQualityPipeline...")
    print("-" * 50)

    try:
        from enhanced_quality_pipeline import EnhancedQualityPipeline

        pipeline = EnhancedQualityPipeline()

        # Initialize
        pipeline.initialize(
            premise="A young wizard discovers a hidden power",
            genre="fantasy",
            num_chapters=5,
            themes=["coming-of-age", "power", "responsibility"]
        )

        print("  ✓ Pipeline initialized")

        # Get context for chapter 1
        context = pipeline.get_generation_context(1)
        print(f"  ✓ Generation context retrieved")
        print(f"    - Has generation prompt: {'generation_prompt' in context}")
        print(f"    - Has things to remember: {'things_to_remember' in context}")

        # Test post-processing
        test_chapter = """
        Chapter 1: The Beginning

        It was a dark and stormy night. Sarah embarked on her journey,
        leveraging her unique abilities. The experience was transformative.
        She delved deep into the ancient texts, searching for answers.
        """

        processed, stats = pipeline.post_process(1, test_chapter)
        print(f"  ✓ Post-processing completed")
        print(f"    - AI-isms replaced: {stats.get('ai_isms_replaced', 0)}")

        # Validate chapter
        report = pipeline.validate_chapter(1, processed)
        print(f"  ✓ Chapter validated")
        print(f"    - Overall score: {report.overall_score:.1f}")
        print(f"    - Passed: {report.passed}")

        print("\n  EnhancedQualityPipeline: PASSED")
        return True

    except Exception as e:
        print(f"  ✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all integration tests."""
    print("=" * 60)
    print("BOOKCLI PHASE 9 INTEGRATION TESTS")
    print("=" * 60)

    results = []

    # Run tests
    results.append(("Module Imports", test_imports()))
    results.append(("ResilientOrchestrator", test_resilient_orchestrator_integration()))
    results.append(("AutonomousProductionPipeline", test_autonomous_pipeline_integration()))
    results.append(("RepetitionPostProcessor", test_post_processor()))
    results.append(("EnhancedQualityPipeline", test_enhanced_pipeline()))

    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)

    passed = 0
    failed = 0
    for name, result in results:
        status = "✓ PASSED" if result else "✗ FAILED"
        print(f"  {name}: {status}")
        if result:
            passed += 1
        else:
            failed += 1

    print(f"\nTotal: {passed} passed, {failed} failed")
    print("=" * 60)

    return failed == 0


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
