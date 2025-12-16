#!/usr/bin/env python3
"""
Production Test - Generate actual full-length chapters
Validates that chapters consistently meet production requirements
"""

import sys
from pathlib import Path
import re
import json
from typing import Dict, List

sys.path.insert(0, str(Path(__file__).parent))

# Import the proper generator we created
from generate_proper_chapter import generate_full_chapter


def analyze_chapter(chapter_text: str) -> Dict:
    """Analyze a chapter for quality metrics"""

    word_count = len(chapter_text.split())

    # Count various metrics
    measurements = len(re.findall(r'\d+\.?\d*\s*[°%]', chapter_text))
    time_refs = len(re.findall(r'\d{1,2}:\d{2}', chapter_text))
    precise_numbers = len(re.findall(r'\d+\.?\d+', chapter_text))
    heart_rates = len(re.findall(r'\d+\s*BPM', chapter_text, re.I))
    probabilities = len(re.findall(r'\d+%|probability|coefficient', chapter_text, re.I))
    temperatures = len(re.findall(r'\d+\.?\d*°[CF]', chapter_text))

    # Calculate densities
    words_per_thousand = max(1, word_count / 1000)
    detail_density = (measurements + time_refs + precise_numbers) / words_per_thousand

    # Check for required elements
    has_countdown = bool(re.search(r'countdown|timer|T-minus|\d+\s+seconds?\s+remaining', chapter_text, re.I))
    has_physiology = bool(re.search(r'heart rate|BPM|pulse|breathing|respiration', chapter_text, re.I))
    has_environmental = bool(re.search(r'temperature|humidity|pressure|decibels', chapter_text, re.I))
    has_dialogue = '"' in chapter_text

    # Count scenes (look for time stamps)
    scene_count = len(re.findall(r'\d{1,2}:\d{2}:\d{2}', chapter_text))

    # Quality assessment
    within_target = 1500 <= word_count <= 2500
    sufficient_details = detail_density >= 40

    return {
        "word_count": word_count,
        "within_target": within_target,
        "measurements": measurements,
        "time_references": time_refs,
        "precise_numbers": precise_numbers,
        "heart_rates": heart_rates,
        "probabilities": probabilities,
        "temperatures": temperatures,
        "detail_density": detail_density,
        "has_countdown": has_countdown,
        "has_physiology": has_physiology,
        "has_environmental": has_environmental,
        "has_dialogue": has_dialogue,
        "scene_count": scene_count,
        "sufficient_details": sufficient_details,
        "quality_score": calculate_quality_score(
            word_count, detail_density, has_countdown, has_physiology, has_environmental
        )
    }


def calculate_quality_score(word_count: int, detail_density: float,
                           has_countdown: bool, has_physiology: bool,
                           has_environmental: bool) -> float:
    """Calculate overall quality score (0-100)"""

    score = 0

    # Word count scoring (max 30 points)
    if 1500 <= word_count <= 2500:
        if 1800 <= word_count <= 2200:
            score += 30  # Perfect range
        else:
            score += 20  # Acceptable range
    elif word_count < 1500:
        score += max(0, (word_count / 1500) * 20)
    else:  # > 2500
        score += max(0, (1 - (word_count - 2500) / 1000) * 20)

    # Detail density scoring (max 40 points)
    if detail_density >= 100:
        score += 40
    elif detail_density >= 60:
        score += 30
    elif detail_density >= 40:
        score += 20
    else:
        score += (detail_density / 40) * 20

    # Required elements (max 30 points)
    if has_countdown:
        score += 10
    if has_physiology:
        score += 10
    if has_environmental:
        score += 10

    return min(100, score)


def test_multiple_chapters():
    """Generate and test multiple chapters"""

    print("\n" + "="*60)
    print("📚 PRODUCTION CHAPTER GENERATION TEST")
    print("="*60)
    print("\nGenerating 5 production-quality chapters...")

    chapter_configs = [
        {
            "num": 1,
            "title": "The Anomaly Awakens",
            "genre": "sci-fi thriller"
        },
        {
            "num": 2,
            "title": "Containment Breach",
            "genre": "sci-fi thriller"
        },
        {
            "num": 3,
            "title": "First Contact",
            "genre": "sci-fi thriller"
        },
        {
            "num": 4,
            "title": "System Override",
            "genre": "sci-fi thriller"
        },
        {
            "num": 5,
            "title": "Critical Decision",
            "genre": "sci-fi thriller"
        }
    ]

    results = []
    all_passed = True

    for config in chapter_configs:
        print(f"\n📖 Generating Chapter {config['num']}: {config['title']}")
        print("-" * 40)

        # Generate chapter
        chapter_text = generate_full_chapter(
            chapter_num=config['num'],
            title=config['title'],
            genre=config['genre']
        )

        # Analyze it
        analysis = analyze_chapter(chapter_text)
        results.append(analysis)

        # Display results
        print(f"  Word count: {analysis['word_count']:,}")
        print(f"  Within target (1500-2500): {'✅' if analysis['within_target'] else '❌'}")
        print(f"  Detail density: {analysis['detail_density']:.1f}/1000 words")
        print(f"  Quality score: {analysis['quality_score']:.1f}/100")

        # Check pass/fail
        if not analysis['within_target'] or analysis['quality_score'] < 70:
            all_passed = False
            print(f"  Status: ❌ FAILED")
        else:
            print(f"  Status: ✅ PASSED")

        # Save chapter
        output_path = Path(f"workspace/production_chapter_{config['num']}.md")
        output_path.parent.mkdir(exist_ok=True)
        output_path.write_text(chapter_text)

    # Calculate aggregates
    print("\n" + "="*60)
    print("📊 AGGREGATE RESULTS")
    print("="*60)

    total_words = sum(r['word_count'] for r in results)
    avg_words = total_words / len(results)
    avg_density = sum(r['detail_density'] for r in results) / len(results)
    avg_quality = sum(r['quality_score'] for r in results) / len(results)

    print(f"\n📈 Statistics:")
    print(f"  Total chapters: {len(results)}")
    print(f"  Total words: {total_words:,}")
    print(f"  Average words/chapter: {avg_words:,.0f}")
    print(f"  Average detail density: {avg_density:.1f}/1000")
    print(f"  Average quality score: {avg_quality:.1f}/100")

    # Check consistency
    word_counts = [r['word_count'] for r in results]
    min_words = min(word_counts)
    max_words = max(word_counts)
    variance = max_words - min_words

    print(f"\n📏 Consistency:")
    print(f"  Min words: {min_words:,}")
    print(f"  Max words: {max_words:,}")
    print(f"  Variance: {variance:,}")
    print(f"  Consistent: {'✅' if variance < 500 else '❌'}")

    # Quality breakdown
    print(f"\n🎯 Quality Elements:")
    all_have_countdown = all(r['has_countdown'] for r in results)
    all_have_physiology = all(r['has_physiology'] for r in results)
    all_have_environmental = all(r['has_environmental'] for r in results)
    all_have_dialogue = all(r['has_dialogue'] for r in results)

    print(f"  All have countdown: {'✅' if all_have_countdown else '❌'}")
    print(f"  All have physiology: {'✅' if all_have_physiology else '❌'}")
    print(f"  All have environmental: {'✅' if all_have_environmental else '❌'}")
    print(f"  All have dialogue: {'✅' if all_have_dialogue else '❌'}")

    # Save detailed report
    report = {
        "summary": {
            "total_chapters": len(results),
            "total_words": total_words,
            "average_words": avg_words,
            "average_density": avg_density,
            "average_quality": avg_quality,
            "all_passed": all_passed
        },
        "consistency": {
            "min_words": min_words,
            "max_words": max_words,
            "variance": variance,
            "is_consistent": variance < 500
        },
        "chapters": results
    }

    report_path = Path("workspace/production_test_report.json")
    report_path.write_text(json.dumps(report, indent=2))

    print(f"\n💾 Detailed report saved to: {report_path}")

    # Final verdict
    print("\n" + "="*60)
    if all_passed and variance < 500 and avg_quality >= 80:
        print("🏆 PRODUCTION READY!")
        print("All chapters meet requirements with consistent quality.")
    elif all_passed:
        print("✅ TESTS PASSED")
        print("Chapters meet basic requirements.")
    else:
        print("⚠️  NEEDS IMPROVEMENT")
        print("Some chapters did not meet production standards.")
    print("="*60)

    return all_passed, report


def main():
    """Run production tests"""
    passed, report = test_multiple_chapters()

    if passed:
        print("\n✅ System validated for production use.")
    else:
        print("\n⚠️  System needs adjustments for production.")


if __name__ == "__main__":
    main()