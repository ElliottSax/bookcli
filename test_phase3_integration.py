#!/usr/bin/env python3
"""
Test Phase 3 Integration: Iterative First-Pass Generation

Tests the complete pipeline:
1. Quality prediction from outline
2. Chapter generation
3. Detail density analysis
4. Word count validation
5. Iterative enhancement
"""

import sys
from pathlib import Path

# Add scripts directory to path
sys.path.insert(0, str(Path(__file__).parent / "scripts"))

from detail_density_analyzer import DetailDensityAnalyzer
from word_count_enforcer import WordCountEnforcer
from quality_predictor import QualityPredictor


def test_phase3_pipeline():
    """Test Phase 3 integration with example outline and chapter"""

    print("="*60)
    print("PHASE 3 INTEGRATION TEST")
    print("="*60)

    # Initialize analyzers
    detail_analyzer = DetailDensityAnalyzer()
    word_count_enforcer = WordCountEnforcer()
    quality_predictor = QualityPredictor()

    # Sample outline (Chapter 13 style)
    outline = """
Chapter 13: Marcus confronts his mission
Target length: 3500 words

Marcus must decide whether to accept the assassination mission.
He debates with Kira about the morality of killing.
Flashback to his life before the portal.
Decision point: accepts mission with conditions.
"""

    context = {
        "character_count": 3,
        "thread_count": 5
    }

    # STEP 1: Quality Prediction
    print("\n" + "="*60)
    print("STEP 1: QUALITY PREDICTION FROM OUTLINE")
    print("="*60)

    prediction = quality_predictor.predict_from_outline(outline, context)

    print(f"\nPredicted quality: {prediction['predicted_quality']:.1f}/10")
    print(f"Confidence: {prediction['confidence']}")
    print(f"\nIssues found: {len(prediction['flags'])}")

    for flag in prediction['flags']:
        print(f"  [{flag.severity}] {flag.issue}")
        print(f"    Fix: {flag.fix}")

    # Sample generated chapter (simulated)
    sample_chapter = """
Marcus stood in the training hall, his hands clenched. The decision weighed on him.

"You have to understand," Kira said, moving closer. "This isn't murder. It's prevention."

He thought back to his old life. The coffee shop. The morning routine. Everything had been so simple.

"I'll do it," he finally said. "But on my terms."

Kira nodded. "That's all we ask."

The training would begin tomorrow.
""" * 20  # Repeat to get ~1400 words

    # STEP 2: Detail Density Analysis
    print("\n" + "="*60)
    print("STEP 2: DETAIL DENSITY ANALYSIS")
    print("="*60)

    density_result = detail_analyzer.analyze(sample_chapter, target_density=3.0)

    print(f"\nWord count: {density_result['word_count']}")
    print(f"Total details found: {density_result['total_details']}")
    print(f"Density: {density_result['density']:.2f} per 1000 words")
    print(f"Target: 3.0 per 1000 words")
    print(f"Status: {'✓ PASS' if density_result['passed'] else '✗ FAIL'}")

    if not density_result['passed']:
        if 'details_needed' in density_result:
            print(f"\nNeeds {density_result['details_needed']} more obsessive details")
        print("\nDetail types found:")
        for dtype, count in density_result.get('detail_types', {}).items():
            print(f"  {dtype}: {count}")
        if not density_result.get('detail_types'):
            print("  (No obsessive details found)")

    # STEP 3: Word Count Validation
    print("\n" + "="*60)
    print("STEP 3: WORD COUNT VALIDATION")
    print("="*60)

    wc_result = word_count_enforcer.validate(sample_chapter, target=3500)

    print(f"\nTarget: {wc_result['target']} words")
    print(f"Acceptable range: {wc_result['min_acceptable']}-{wc_result['max_acceptable']} words (±15%)")
    print(f"Actual: {wc_result['actual']} words")

    if wc_result['passed']:
        print(f"Status: ✓ PASS")
    else:
        variance_pct = ((wc_result['actual'] - wc_result['target']) / wc_result['target']) * 100
        print(f"Variance: {variance_pct:+.1f}%")
        print(f"Status: ✗ FAIL")

        if 'action' in wc_result:
            print(f"\nACTION REQUIRED: {wc_result['action']}")

            if wc_result['action'] == 'ADD_DEPTH':
                print(f"Need to add: {wc_result['deficit']} words")
            elif wc_result['action'] == 'CUT_WEAK':
                print(f"Need to cut: {wc_result['excess']} words")

            print("\nExpansion/Cutting strategies:")
            for i, strategy in enumerate(wc_result.get('strategies', []), 1):
                print(f"{i}. {strategy['strategy']}: {strategy['target_words']:+d} words")

    # STEP 4: Enhancement Recommendations
    print("\n" + "="*60)
    print("STEP 4: ENHANCEMENT RECOMMENDATIONS")
    print("="*60)

    needs_enhancement = []

    if not density_result['passed']:
        needs_enhancement.append("ADD_DEPTH (detail density below target)")

    if not wc_result['passed']:
        if wc_result.get('action') == 'ADD_DEPTH':
            needs_enhancement.append("EXPAND_CONTENT (word count below target)")
        elif wc_result.get('action') == 'CUT_WEAK':
            needs_enhancement.append("CUT_WEAK (word count above target)")

    if needs_enhancement:
        print("\nEnhancements needed:")
        for enhancement in needs_enhancement:
            print(f"  - {enhancement}")

        print("\nIterative enhancement loop would:")
        print("  1. Identify weak sections (low detail density)")
        print("  2. Enhance those sections with LLM")
        print("  3. Re-analyze enhanced chapter")
        print("  4. Repeat until targets met (max 2 iterations)")
    else:
        print("\n✓ Chapter meets all quality targets!")
        print("No enhancement needed.")

    # STEP 5: Summary
    print("\n" + "="*60)
    print("PHASE 3 PIPELINE SUMMARY")
    print("="*60)

    print(f"\nPredicted quality: {prediction['predicted_quality']:.1f}/10")
    print(f"Detail density: {density_result['density']:.2f}/1000 words {'✓' if density_result['passed'] else '✗'}")
    print(f"Word count: {wc_result['actual']}/{wc_result['target']} words {'✓' if wc_result['passed'] else '✗'}")
    print(f"\nEnhancements needed: {len(needs_enhancement)}")

    if not needs_enhancement:
        print("\n✓✓✓ CHAPTER READY FOR PUBLICATION ✓✓✓")
    else:
        print("\n→ Iterative enhancement recommended")

    print("\n" + "="*60)
    print("TEST COMPLETE")
    print("="*60)


if __name__ == "__main__":
    test_phase3_pipeline()
