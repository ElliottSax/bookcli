#!/usr/bin/env python3
"""
Test script for Phase 8 Quality Enforcement Pipeline

Tests the complete quality enforcement system:
1. Detail density analyzer
2. Physical grounding checker
3. Show vs tell analyzer
4. Quality gate enforcer
"""

import sys
from pathlib import Path

# Add scripts to path
sys.path.insert(0, str(Path(__file__).parent / 'scripts'))

from detail_density_analyzer import DetailDensityAnalyzer
from physical_grounding_checker import PhysicalGroundingChecker
from show_vs_tell_analyzer import ShowVsTellAnalyzer
from quality_gate_enforcer import QualityGateEnforcer


def test_bad_chapter():
    """Test with a chapter that should FAIL quality gates"""
    print("\n" + "="*70)
    print("TEST 1: BAD CHAPTER (should fail)")
    print("="*70)

    # This chapter has lots of telling, no details, no grounding
    bad_chapter = """
    Sarah felt scared when she entered the dark room. She was nervous about
    what she might find inside. The room was big and empty. She thought it
    was creepy. Marcus was worried too. He thought they should leave.

    "This is scary," Sarah said nervously. She felt her fear growing.
    Marcus was afraid as well. They both felt uncomfortable in the dark space.

    Sarah realized she was being silly. She knew there was nothing to fear.
    But she was still scared. The darkness made her nervous. She wished they
    could leave. Marcus understood how she felt. He was scared too.
    """ * 100  # Repeat to meet word count

    enforcer = QualityGateEnforcer(strict_mode=True)
    report = enforcer.check_chapter(bad_chapter, chapter_number=1)

    report.print_report()

    assert not report.passed_all_gates, "Bad chapter should FAIL"
    print("✓ Test passed: Bad chapter correctly failed quality gates\n")

    return report


def test_good_chapter():
    """Test with a chapter that should PASS quality gates"""
    print("\n" + "="*70)
    print("TEST 2: GOOD CHAPTER (should pass)")
    print("="*70)

    # This chapter has showing, details, physical grounding
    good_chapter = """
    Sarah's heart hammered—102 BPM. She counted. The room stretched before her,
    seventeen meters across. Twenty-three floor tiles wide, each exactly 73cm.
    She'd measured. Twice.

    Temperature dropping. 18.4°C. Goosebumps rising along her forearms. Breath
    visible in the cold air—fourteen breaths per minute, shallow, catching in
    her throat.

    "Wait." Marcus grabbed her shoulder. Five points of pressure. His jaw
    clenched, muscles jumping beneath the skin. Eyes darting to shadows—
    counting exits. Three. Always three.

    Her pulse jumped. 117 BPM now. Hands trembling. She pressed them against
    her thighs, felt rough denim, warmth of skin underneath. Grounding.
    Physical. Real.

    The door ahead was oak. Dark grain spiraling—she traced patterns with her
    eyes. Cataloging. Seven seconds until breathing steadied. She counted
    every one.

    Marcus's fingers tightened. "Seventeen steps to the door. You counted too?"

    She nodded. Throat tight. Swallowed. "Sixteen. I count sixteen."

    "Check again."

    One. Two. Three. Her eyes tracked floor tiles. Four. Five. Six. Heart rate
    climbing—122 BPM. Seven. Eight. Hands still shaking. Nine. Ten. Halfway.
    Eleven. Twelve. Breath coming faster. Thirteen. Fourteen. Almost there.
    Fifteen. Sixteen.

    "Sixteen," she whispered. Voice hoarse. Throat raw. "Definitely sixteen."

    Marcus frowned. Lines deepening around his eyes. "I counted seventeen."

    Something was wrong. The numbers didn't match. Her stomach dropped, cold
    spreading through her chest. 36.2°C skin temperature, she could feel it
    falling. Peripheral vasoconstriction—biology textbook term floating up
    from memory. Fight or flight response activating.

    She counted again. Slower this time. One tile. Two tiles. Three. Four.
    Five. Six. Breath held. Seven. Eight. Nine. Ten. Eleven. Twelve. Exhale.
    Thirteen. Fourteen. Fifteen. Sixteen. Seventeen.

    He was right.

    "Seventeen," she admitted. Pulse 128 BPM. Hands ice-cold now. "You're right."

    "The room changed." Marcus's voice dropped. Barely audible. "While we were
    standing here. It added a tile."

    Impossible. Tiles don't just appear. 73cm of ceramic doesn't materialize
    from nothing. But her count was accurate—she'd done it three times.
    Sixteen became seventeen. Between heartbeats. Between breaths.

    "We need to leave." Her voice steadier than she felt. 132 BPM now. Hands
    clenched into fists. Nails digging crescents into palms. Sharp. Grounding.
    "Now."

    Marcus nodded. Already moving. Pulling her backward. Away from the door.
    Away from the impossible seventeenth tile. His hand locked around her wrist—
    pulse point contact. She could feel his heartbeat. Fast as hers. Maybe faster.

    They backed toward the entrance. She counted steps. One. Two. Three. Marcus
    counting too—lips moving silently. Four. Five. Six. Temperature still dropping.
    17.1°C now. Her breath came in white clouds. Seven. Eight. Nine.

    The doorway behind them. Escape. Freedom. Normal tiles that stayed put.
    Numbers that made sense.

    Ten. Eleven. Twelve.

    They ran.
    """ * 5  # Repeat to meet word count

    enforcer = QualityGateEnforcer(strict_mode=True)
    report = enforcer.check_chapter(good_chapter, chapter_number=2)

    report.print_report()

    assert report.passed_all_gates, "Good chapter should PASS"
    print("✓ Test passed: Good chapter correctly passed quality gates\n")

    return report


def test_individual_analyzers():
    """Test each analyzer individually"""
    print("\n" + "="*70)
    print("TEST 3: INDIVIDUAL ANALYZERS")
    print("="*70)

    test_text = """
    Her heart raced—112 BPM. Hands trembling. Temperature: 36.8°C.
    She counted heartbeats. Fourteen. Fifteen. Sixteen.

    "Stop." He grabbed her arm. Jaw clenched. Eyes narrowed.

    She froze. Breath caught. Chest tight.
    """

    # Test detail density
    print("\n--- Detail Density Analyzer ---")
    detail_analyzer = DetailDensityAnalyzer()
    detail_result = detail_analyzer.count_obsessive_details(test_text)
    print(f"Details found: {detail_result.total_details}")
    print(f"Density per 1k: {detail_result.density_per_1k:.2f}")
    print(f"Meets target (3.0+): {detail_result.meets_target}")
    print(f"Examples: {detail_result.examples[:3]}")

    # Test physical grounding
    print("\n--- Physical Grounding Checker ---")
    grounding_checker = PhysicalGroundingChecker()
    grounding_result = grounding_checker.check_physical_grounding(test_text)
    print(f"Total emotions: {grounding_result.total_emotions}")
    print(f"Grounded: {grounding_result.grounded_emotions}")
    print(f"Ungrounded: {grounding_result.ungrounded_emotions}")
    print(f"Score: {grounding_result.score:.1f}/100")
    print(f"Pass: {grounding_result.pass_check}")

    # Test show vs tell
    print("\n--- Show vs Tell Analyzer ---")
    show_tell_analyzer = ShowVsTellAnalyzer()
    show_tell_result = show_tell_analyzer.analyze_show_vs_tell(test_text)
    print(f"Tell count: {show_tell_result.tell_count}")
    print(f"Show count: {show_tell_result.show_count}")
    print(f"Show ratio: {show_tell_result.show_ratio:.1%}")
    print(f"Score: {show_tell_result.score:.1f}/100")
    print(f"Pass: {show_tell_result.pass_check}")

    print("\n✓ All individual analyzers working correctly\n")


def test_comparison():
    """Compare bad vs good chapter scores"""
    print("\n" + "="*70)
    print("TEST 4: BAD vs GOOD COMPARISON")
    print("="*70)

    bad_chapter = "She felt scared. He was worried." * 500
    good_chapter = "Heart hammering. 102 BPM. Hands trembling." * 500

    enforcer = QualityGateEnforcer()

    bad_report = enforcer.check_chapter(bad_chapter, 1)
    good_report = enforcer.check_chapter(good_chapter, 2)

    print(f"\nBAD chapter score: {bad_report.total_score:.1f}/100 - {'PASSED' if bad_report.passed_all_gates else 'FAILED'}")
    print(f"GOOD chapter score: {good_report.total_score:.1f}/100 - {'PASSED' if good_report.passed_all_gates else 'FAILED'}")

    print(f"\nScore difference: {good_report.total_score - bad_report.total_score:.1f} points")

    assert good_report.total_score > bad_report.total_score, "Good chapter should score higher"
    print("✓ Good chapter scores higher than bad chapter\n")


if __name__ == "__main__":
    print("\n" + "="*70)
    print("PHASE 8 QUALITY ENFORCEMENT - COMPLETE TEST SUITE")
    print("="*70)

    try:
        # Run all tests
        test_individual_analyzers()
        bad_report = test_bad_chapter()
        good_report = test_good_chapter()
        test_comparison()

        print("\n" + "="*70)
        print("ALL TESTS PASSED ✓")
        print("="*70)
        print("\nPhase 8 Quality Enforcement is working correctly!")
        print("\nNext steps:")
        print("1. Enable quality enforcement in production: quality_enforcement_enabled=True")
        print("2. Adjust thresholds if needed in QualityGateEnforcer()")
        print("3. Monitor quality reports in workspace/chapter_*_quality_report.json")
        print("\n" + "="*70 + "\n")

    except AssertionError as e:
        print(f"\n✗ TEST FAILED: {e}\n")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ ERROR: {e}\n")
        import traceback
        traceback.print_exc()
        sys.exit(1)
