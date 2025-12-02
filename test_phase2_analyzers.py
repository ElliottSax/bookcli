#!/usr/bin/env python3
"""
Integrated test: Phase 2 analyzers working together

Demonstrates:
1. Detail density analyzer (obsessive detail counting)
2. Word count enforcer (validation + expansion/cutting suggestions)
3. Quality predictor (pre-generation quality prediction)
"""

import sys
from pathlib import Path

# Add scripts directory to path
sys.path.insert(0, str(Path(__file__).parent / "scripts"))

from detail_density_analyzer import DetailDensityAnalyzer
from word_count_enforcer import WordCountEnforcer
from quality_predictor import QualityPredictor


def main():
    print("="*80)
    print("PHASE 2 ANALYZER INTEGRATION TEST")
    print("="*80)
    print()

    # Test on Chapter 13 (existing chapter)
    print("ANALYZING EXISTING CHAPTER: Chapter 13")
    print("="*80)
    print()

    chapter_path = Path("workspace/threads-of-fire/chapters/chapter_013.md")
    with open(chapter_path, 'r') as f:
        chapter_text = f.read()

    # Remove metadata
    if '---' in chapter_text:
        chapter_text = chapter_text.split('---')[0]

    # Test 1: Detail Density Analysis
    print("1. DETAIL DENSITY ANALYSIS")
    print("-"*80)
    density_analyzer = DetailDensityAnalyzer()
    density_result = density_analyzer.analyze(chapter_text, target_density=3.0)
    print(density_analyzer.format_report(density_result))
    print("\n"*2)

    # Test 2: Word Count Validation
    print("2. WORD COUNT VALIDATION")
    print("-"*80)
    wc_enforcer = WordCountEnforcer(tolerance=0.15)
    wc_result = wc_enforcer.validate(chapter_text, target=3500)
    print(wc_enforcer.format_report(wc_result))
    print("\n"*2)

    # Test 3: Quality Prediction (from outline)
    print("3. QUALITY PREDICTION (from outline)")
    print("-"*80)

    # Chapter 13 outline
    outline = """
    Chapter 13: The Morning After (First morning without armor)

    Key scenes:
    1. Catherine wakes to real sunlight for first time in 7 years (no helmet)
    2. Comes downstairs, watches Elara work (counting habit emerging)
    3. Breakfast: Catherine relearning to eat for pleasure (porridge/honey)
    4. Elara examines Catherine's feet (silver scars, deformed bones)
    5. REVELATION: Threads still embedded in bones (must surgically extract)
    6. Elara explains: 2 months to live if not extracted, 1-2 weeks surgery
    7. High risk: permanent nerve damage, may never walk properly
    8. Catherine's fear: being "ordinary" without armor/magic
    9. CLIMAX: Catherine says "I love you" (first full confession)
    10. Elara can't say it back yet (afraid of losing Catherine)
    11. Schedule extraction for tomorrow, both anxious about what comes next

    Emotional arc: Hope → domestic intimacy → devastating revelation →
                   vulnerability → love confession → bittersweet acceptance

    Target word count: 3,500 words
    Obsession focus: Counting (steps, heartbeats, tools), temperature, hands
    """

    context = {
        'word_target': 3500,
        'obsession_anchors': ['counted', 'counting', 'heartbeats', 'temperature', 'scars', 'steps']
    }

    predictor = QualityPredictor()
    prediction_result = predictor.predict_from_outline(outline, context)
    print(predictor.format_report(prediction_result))
    print("\n"*2)

    # Summary
    print("="*80)
    print("INTEGRATED ANALYSIS SUMMARY")
    print("="*80)
    print()

    print(f"Detail density: {density_result['density']}/1000 words")
    print(f"  Target: {density_result['target_density']}/1000 words")
    print(f"  Status: {'✓ PASS' if density_result['passed'] else '✗ FAIL'}")
    print()

    print(f"Word count: {wc_result['actual']} words")
    print(f"  Target: {wc_result['target']} words (±15%)")
    print(f"  Status: {'✓ PASS' if wc_result['passed'] else '✗ FAIL'}")
    if not wc_result['passed']:
        print(f"  Action: {wc_result['action']} {wc_result.get('deficit', wc_result.get('excess', 0))} words")
    print()

    print(f"Predicted quality (from outline): {prediction_result['predicted_quality']}/10")
    print(f"  Confidence: {prediction_result['confidence']}")
    print(f"  Issues: {len(prediction_result['flags'])}")
    print()

    # Overall assessment
    print("OVERALL ASSESSMENT:")
    print()

    if density_result['passed'] and wc_result['passed']:
        print("✓ Chapter meets all technical requirements")
        print("  - Sufficient obsessive detail density")
        print("  - Word count within acceptable range")
    else:
        print("✗ Chapter needs improvements:")
        if not density_result['passed']:
            print(f"  - Add {density_result['deficit']} more obsessive details")
        if not wc_result['passed']:
            print(f"  - {wc_result['action']} {wc_result.get('deficit', wc_result.get('excess', 0))} words")

    print()
    print("These Phase 2 tools help:")
    print("  1. Measure quality (detail density analyzer)")
    print("  2. Enforce requirements (word count enforcer)")
    print("  3. Predict issues (quality predictor)")
    print()
    print("Next: Integrate into orchestrator.py for automatic analysis")
    print()


if __name__ == "__main__":
    main()
