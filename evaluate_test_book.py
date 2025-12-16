#!/usr/bin/env python3
"""
Comprehensive Quality Evaluation for Test Book
Uses all new quality systems to analyze the generated book
"""

import sys
import json
from pathlib import Path
from datetime import datetime

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

# Import quality modules
from quality.enhanced_detail_analyzer import EnhancedDetailAnalyzer, DetailType
from scripts.detail_density_analyzer import DetailDensityAnalyzer
from scripts.physical_grounding_checker import PhysicalGroundingChecker
from scripts.show_vs_tell_analyzer import ShowVsTellAnalyzer
from scripts.quality_gate_enforcer import QualityGateEnforcer
import scripts.comprehensive_quality_validator as validator

def evaluate_chapter(chapter_path: Path, chapter_num: int):
    """Evaluate a single chapter."""
    print(f"\n{'='*60}")
    print(f"CHAPTER {chapter_num} EVALUATION")
    print(f"{'='*60}\n")

    # Read chapter
    text = chapter_path.read_text(encoding='utf-8')
    word_count = len(text.split())

    print(f"📝 Word Count: {word_count:,} words")

    # 1. Enhanced Detail Analysis
    print("\n📊 ENHANCED DETAIL ANALYSIS:")
    print("-" * 40)

    detail_analyzer = EnhancedDetailAnalyzer(genre="sci-fi")
    detail_metrics = detail_analyzer.analyze(text)

    print(f"Total Details: {detail_metrics.total_details}")
    print(f"Details per 1000 words: {detail_metrics.details_per_1000_words:.2f}")
    print(f"Quality Score: {detail_metrics.detail_quality_score:.1f}/100")

    print("\nDetail Type Breakdown:")
    for detail_type, count in sorted(detail_metrics.detail_types.items(),
                                     key=lambda x: x[1], reverse=True):
        print(f"  • {detail_type.value.title()}: {count}")

    print("\nSensory Coverage:")
    for sense, count in detail_metrics.sensory_coverage.items():
        status = "✓" if count > 2 else "✗"
        print(f"  {status} {sense.title()}: {count}")

    print("\nTop Obsessive Details:")
    for i, detail in enumerate(detail_metrics.obsessive_details[:3], 1):
        print(f"  {i}. {detail[:100]}...")

    # 2. Original Detail Density
    print("\n📈 DETAIL DENSITY ANALYSIS:")
    print("-" * 40)

    density_analyzer = DetailDensityAnalyzer()
    density_analysis = density_analyzer.count_obsessive_details(text)

    # Convert to score (density of 3+ per 1000 words = 100)
    density_score = min(100, (density_analysis.density_per_1k / 3.0) * 100)

    print(f"Detail Density Score: {density_score:.1f}/100")
    print(f"Total Obsessive Details: {density_analysis.total_details}")
    print(f"Density per 1000 words: {density_analysis.density_per_1k:.2f}")
    print(f"Meets Target (3/1000): {'✓' if density_analysis.meets_target else '✗'}")

    # 3. Physical Grounding
    print("\n🏃 PHYSICAL GROUNDING ANALYSIS:")
    print("-" * 40)

    grounding_checker = PhysicalGroundingChecker()
    grounding_analysis = grounding_checker.check_physical_grounding(text)
    grounding_score = grounding_analysis.to_dict()

    print(f"Physical Grounding Score: {grounding_score['score']:.1f}/100")
    print(f"Grounded Emotions: {grounding_score['grounded_emotions']}")
    print(f"Ungrounded Emotions: {grounding_score['ungrounded_emotions']}")
    print(f"Grounding Ratio: {grounding_score['grounding_ratio']:.2f}")
    print(f"Pass Check: {'✓' if grounding_score['pass'] else '✗'}")

    # 4. Show vs Tell
    print("\n✨ SHOW VS TELL ANALYSIS:")
    print("-" * 40)

    show_tell_analyzer = ShowVsTellAnalyzer()
    show_tell_analysis = show_tell_analyzer.analyze_show_vs_tell(text)
    show_tell_score = show_tell_analysis.to_dict()

    print(f"Show vs Tell Score: {show_tell_score['score']:.1f}/100")
    print(f"Show Count: {show_tell_score['show_count']}")
    print(f"Tell Count: {show_tell_score['tell_count']}")
    print(f"Show Ratio: {show_tell_score['show_ratio']:.2f}")
    print(f"Pass Check: {'✓' if show_tell_score['pass'] else '✗'}")

    # 5. Quality Gates
    print("\n🚪 QUALITY GATE CHECK:")
    print("-" * 40)

    gate_enforcer = QualityGateEnforcer()
    gate_report = gate_enforcer.check_chapter(text, chapter_num)
    gate_result = gate_report.to_dict()

    print(f"Overall Pass: {'✅ PASSED' if gate_result['passed_all_gates'] else '❌ FAILED'}")
    print(f"Total Score: {gate_result['total_score']:.1f}/100")

    print("\nGate Results:")
    for gate in gate_result['gates']:
        status = "✅" if gate['passed'] else "❌"
        print(f"  {status} {gate['name']}: Score {gate['score']:.0f} (Target: {gate['target']})")

    # 6. Comprehensive Validation
    print("\n🔍 COMPREHENSIVE VALIDATION:")
    print("-" * 40)

    # Run all validators
    validation_results = {}

    # Structure validators
    validation_results['chapter_length'] = validator.validate_chapter_length_consistency(text)
    validation_results['scene_breaks'] = validator.validate_scene_break_usage(text)
    validation_results['paragraph_structure'] = validator.validate_paragraph_structure(text)

    # Character validators
    validation_results['dialogue'] = validator.validate_dialogue_quality(text)
    validation_results['character_voice'] = validator.validate_character_voice_distinction(text)

    # Style validators
    validation_results['sentence_variety'] = validator.validate_sentence_variety(text)
    validation_results['pacing'] = validator.validate_pacing_variation(text)

    # Technical validators
    validation_results['grammar'] = validator.validate_grammar_and_spelling(text)
    validation_results['formatting'] = validator.validate_formatting_consistency(text)

    passed_count = sum(1 for r in validation_results.values() if r['passed'])
    total_count = len(validation_results)

    print(f"Validation Pass Rate: {passed_count}/{total_count} ({passed_count/total_count*100:.1f}%)")

    print("\nValidation Details:")
    for check, result in validation_results.items():
        status = "✅" if result['passed'] else "❌"
        print(f"  {status} {check}: {result.get('reason', 'Passed')}")

    # Calculate overall chapter score
    overall_score = (
        detail_metrics.detail_quality_score * 0.25 +
        density_score * 0.15 +
        grounding_score['score'] * 0.20 +
        show_tell_score['score'] * 0.20 +
        gate_result['total_score'] * 0.20
    )

    print(f"\n⭐ OVERALL CHAPTER SCORE: {overall_score:.1f}/100")

    return {
        'chapter': chapter_num,
        'word_count': word_count,
        'detail_score': detail_metrics.detail_quality_score,
        'density_score': density_score,
        'grounding_score': grounding_score['score'],
        'show_tell_score': show_tell_score['score'],
        'gate_score': gate_result['total_score'],
        'overall_score': overall_score,
        'passed_gates': gate_result['passed_all_gates'],
        'validation_pass_rate': passed_count/total_count*100
    }

def main():
    """Run comprehensive evaluation."""
    print("\n" + "="*60)
    print("📚 COMPREHENSIVE BOOK QUALITY EVALUATION")
    print("="*60)
    print("\nBook: The Last Algorithm")
    print("Genre: Sci-Fi Thriller")
    print("Evaluation Date:", datetime.now().strftime("%Y-%m-%d %H:%M"))

    # Find chapters
    workspace = Path("workspace/test-book")
    chapters = sorted(workspace.glob("chapter_*.md"))

    if not chapters:
        print("❌ No chapters found!")
        return

    print(f"Found {len(chapters)} chapters to evaluate")

    # Evaluate each chapter
    all_results = []

    for chapter_path in chapters:
        chapter_num = int(chapter_path.stem.split('_')[1])
        result = evaluate_chapter(chapter_path, chapter_num)
        all_results.append(result)

    # Generate book-level summary
    print("\n" + "="*60)
    print("📊 BOOK-LEVEL SUMMARY")
    print("="*60)

    total_words = sum(r['word_count'] for r in all_results)
    avg_detail_score = sum(r['detail_score'] for r in all_results) / len(all_results)
    avg_density_score = sum(r['density_score'] for r in all_results) / len(all_results)
    avg_grounding_score = sum(r['grounding_score'] for r in all_results) / len(all_results)
    avg_show_tell_score = sum(r['show_tell_score'] for r in all_results) / len(all_results)
    avg_gate_score = sum(r['gate_score'] for r in all_results) / len(all_results)
    avg_overall = sum(r['overall_score'] for r in all_results) / len(all_results)

    print(f"\n📈 AGGREGATE METRICS:")
    print(f"  • Total Word Count: {total_words:,}")
    print(f"  • Average Chapter Length: {total_words/len(all_results):,.0f}")
    print(f"  • Chapters Passing Gates: {sum(1 for r in all_results if r['passed_gates'])}/{len(all_results)}")

    print(f"\n🎯 AVERAGE SCORES:")
    print(f"  • Detail Quality: {avg_detail_score:.1f}/100")
    print(f"  • Detail Density: {avg_density_score:.1f}/100")
    print(f"  • Physical Grounding: {avg_grounding_score:.1f}/100")
    print(f"  • Show vs Tell: {avg_show_tell_score:.1f}/100")
    print(f"  • Quality Gates: {avg_gate_score:.1f}/100")

    print(f"\n⭐ OVERALL BOOK SCORE: {avg_overall:.1f}/100")

    # Quality assessment
    if avg_overall >= 85:
        assessment = "EXCELLENT - Publication Ready"
        emoji = "🏆"
    elif avg_overall >= 75:
        assessment = "GOOD - Minor Improvements Needed"
        emoji = "✅"
    elif avg_overall >= 65:
        assessment = "FAIR - Moderate Improvements Needed"
        emoji = "⚠️"
    else:
        assessment = "NEEDS WORK - Significant Improvements Required"
        emoji = "❌"

    print(f"\n{emoji} QUALITY ASSESSMENT: {assessment}")

    # Recommendations
    print(f"\n💡 KEY RECOMMENDATIONS:")

    if avg_detail_score < 70:
        print("  • Increase obsessive details (temperature, counting, measurements)")
    if avg_density_score < 70:
        print("  • Add more sensory and micro-details throughout")
    if avg_grounding_score < 70:
        print("  • Ground more emotions with physical manifestations")
    if avg_show_tell_score < 70:
        print("  • Convert telling statements to showing through action")
    if avg_gate_score < 70:
        print("  • Focus on meeting quality gate requirements")

    # Save report
    report = {
        'book_title': 'The Last Algorithm',
        'genre': 'Sci-Fi Thriller',
        'evaluation_date': datetime.now().isoformat(),
        'total_words': total_words,
        'chapters': len(all_results),
        'scores': {
            'detail_quality': avg_detail_score,
            'detail_density': avg_density_score,
            'physical_grounding': avg_grounding_score,
            'show_vs_tell': avg_show_tell_score,
            'quality_gates': avg_gate_score,
            'overall': avg_overall
        },
        'assessment': assessment,
        'chapter_results': all_results
    }

    report_path = workspace / "quality_evaluation_report.json"
    report_path.write_text(json.dumps(report, indent=2), encoding='utf-8')

    print(f"\n📄 Full report saved to: {report_path}")
    print("\n" + "="*60)
    print("✅ EVALUATION COMPLETE")
    print("="*60)

if __name__ == "__main__":
    main()