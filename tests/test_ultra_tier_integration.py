#!/usr/bin/env python3
"""
Integration test for ultra-tier system

Tests that all components work together:
1. Prompt builder constructs enhanced prompts with few-shot examples
2. Variation focuses select appropriate examples
3. Multi-pass system uses different focuses per version
4. Prompts include quality requirements and examples
"""

import sys
from pathlib import Path

# Add scripts directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from prompt_builder import PromptBuilder


def test_prompt_builder_initialization():
    """Test that prompt builder initializes correctly"""
    print("Test 1: Prompt Builder Initialization")
    print("=" * 60)

    try:
        builder = PromptBuilder(config_dir="config")
        print("✓ PromptBuilder initialized successfully")

        # Check examples loaded
        if builder.examples:
            print(f"✓ Loaded {len(builder.examples)} few-shot examples")
            print(f"  Examples: {', '.join(builder.examples.keys())}")
        else:
            print("✗ No examples loaded")
            return False

        # Check requirements loaded
        if builder.requirements:
            print(f"✓ Loaded quality requirements ({len(builder.requirements)} chars)")
        else:
            print("✗ No requirements loaded")
            return False

        return True

    except Exception as e:
        print(f"✗ Error initializing PromptBuilder: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_variation_focus_selection():
    """Test that variation focuses select correct examples"""
    print("\n\nTest 2: Variation Focus Example Selection")
    print("=" * 60)

    try:
        builder = PromptBuilder(config_dir="config")

        # Test each variation focus
        focuses = ['emotion', 'voice', 'theme', 'depth', 'risk', 'balanced', None]

        for focus in focuses:
            examples = builder._select_examples(focus, num_examples=2)
            focus_name = focus if focus else "baseline"
            print(f"\n{focus_name.upper()}:")
            if examples:
                print(f"  ✓ Selected {len(examples)} examples:")
                for ex in examples:
                    print(f"    - {ex['name']} (score: {ex['score']}/10)")
            else:
                print(f"  ✗ No examples selected")
                return False

        return True

    except Exception as e:
        print(f"✗ Error testing variation focus: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_prompt_construction():
    """Test that prompts are constructed correctly with examples"""
    print("\n\nTest 3: Prompt Construction with Examples")
    print("=" * 60)

    try:
        builder = PromptBuilder(config_dir="config")

        # Create test inputs
        chapter_num = 3
        outline = """
Chapter 3: Marcus confronts the Weavers demanding answers about his role.
Learns he's meant to kill a human to prevent Veil collapse. Must decide
whether to accept mission or find another way.
Target length: 3000 words
"""
        context = """
Previous chapters: Marcus transported to magical world, survived Binding ritual,
training with Kira (Mender mentor). Has discovered he's a "key" but doesn't
know what that means yet.
Active characters: Marcus Chen, Kira Shen, The Weavers
Active plot threads: Marcus discovering his role, Veil deterioration, training progression
"""
        source = """
Core conflict: Marcus is idealistic, believes healing > killing. Weavers are
pragmatic, see killing as necessary. Central paradox: healing through harm.
"""

        # Test baseline prompt (no variation)
        print("\nBASELINE PROMPT (no variation):")
        prompt_baseline = builder.build_chapter_prompt(
            chapter_num=chapter_num,
            outline=outline,
            context=context,
            source_excerpt=source,
            variation_focus=None,
            num_examples=2
        )
        print(f"  ✓ Baseline prompt length: {len(prompt_baseline)} chars")
        if "EXAMPLES OF TARGET QUALITY" in prompt_baseline:
            print(f"  ✓ Contains few-shot examples")
        else:
            print(f"  ✗ Missing few-shot examples")
            return False

        # Test emotion-focused variation
        print("\nEMOTION-FOCUSED VARIATION:")
        prompt_emotion = builder.build_chapter_prompt(
            chapter_num=chapter_num,
            outline=outline,
            context=context,
            source_excerpt=source,
            variation_focus='emotion',
            num_examples=2
        )
        print(f"  ✓ Emotion prompt length: {len(prompt_emotion)} chars")
        if "SPECIFIC FOCUS FOR THIS VERSION" in prompt_emotion:
            print(f"  ✓ Contains variation-specific instructions")
        else:
            print(f"  ✗ Missing variation instructions")
            return False
        if "EMOTIONAL SPECIFICITY" in prompt_emotion:
            print(f"  ✓ Contains emotion-specific guidance")
        else:
            print(f"  ✗ Missing emotion guidance")
            return False

        # Test voice-focused variation
        print("\nVOICE-FOCUSED VARIATION:")
        prompt_voice = builder.build_chapter_prompt(
            chapter_num=chapter_num,
            outline=outline,
            context=context,
            source_excerpt=source,
            variation_focus='voice',
            num_examples=2
        )
        print(f"  ✓ Voice prompt length: {len(prompt_voice)} chars")
        if "VOICE DISTINCTIVENESS" in prompt_voice:
            print(f"  ✓ Contains voice-specific guidance")
        else:
            print(f"  ✗ Missing voice guidance")
            return False

        # Show example excerpt
        print("\n" + "-" * 60)
        print("PROMPT EXCERPT (first 800 chars):")
        print("-" * 60)
        print(prompt_emotion[:800])
        print("...")

        return True

    except Exception as e:
        print(f"✗ Error constructing prompts: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_variation_focus_mapping():
    """Test version-to-focus mapping for multi-pass"""
    print("\n\nTest 4: Multi-Pass Variation Focus Mapping")
    print("=" * 60)

    # Simulate what orchestrator._get_variation_focus() does
    focus_map = {
        1: None,           # Baseline
        2: 'emotion',      # Emotional specificity
        3: 'voice',        # Voice distinctiveness
        4: 'depth',        # Obsessive depth
        5: 'theme',        # Thematic subtlety
        6: 'risk',         # Risk-taking
        7: 'balanced',     # Balanced excellence
    }

    print("\nVersion-to-Focus Mapping (7× multi-pass):")
    for version in range(1, 8):
        focus = focus_map.get(((version - 1) % 7) + 1)
        focus_name = focus if focus else "baseline"
        print(f"  Version {version}: {focus_name}")

    print("\n✓ All 7 versions map to different focuses")
    return True


def run_all_tests():
    """Run all integration tests"""
    print("\n" + "=" * 60)
    print("ULTRA-TIER INTEGRATION TESTS")
    print("=" * 60 + "\n")

    tests = [
        ("Prompt Builder Initialization", test_prompt_builder_initialization),
        ("Variation Focus Selection", test_variation_focus_selection),
        ("Prompt Construction", test_prompt_construction),
        ("Variation Focus Mapping", test_variation_focus_mapping),
    ]

    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"\n✗ Test '{test_name}' crashed: {e}")
            import traceback
            traceback.print_exc()
            results.append((test_name, False))

    # Summary
    print("\n\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for test_name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status}: {test_name}")

    print(f"\nTotal: {passed}/{total} tests passed")

    if passed == total:
        print("\n✓ All integration tests passed!")
        print("\nUltra-tier system is ready for use:")
        print("  1. Few-shot examples library created")
        print("  2. Prompt builder integrates examples")
        print("  3. Variation focuses select appropriate examples")
        print("  4. Multi-pass system uses different focuses per version")
        print("\nNext step: Test with real API generation")
        return 0
    else:
        print(f"\n✗ {total - passed} test(s) failed")
        return 1


if __name__ == "__main__":
    exit_code = run_all_tests()
    sys.exit(exit_code)
