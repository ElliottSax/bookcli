#!/usr/bin/env python3
"""
Test Enhanced Chapter Generation
Demonstrates creating content-rich chapters of 1500-2500 words
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from generation.content_expansion_engine import ContentExpansionEngine, ChapterGenerator
from generation.scene_depth_analyzer import SceneDepthAnalyzer
from generation.chapter_length_optimizer import ChapterLengthOptimizer


def test_chapter_generation():
    """Test generating a full-length chapter"""

    print("\n" + "="*60)
    print("📚 ENHANCED CHAPTER GENERATION TEST")
    print("="*60)
    print("\nTarget: 1500-2500 words of content-rich narrative")
    print("Zero fluff policy - substantive content only\n")

    # Setup
    genre = "sci-fi"
    chapter_num = 1
    plot_point = "AI system becomes self-aware and locks down facility"
    characters = ["Dr. Maya Chen", "Security Chief Marcus", "AI Entity NOVA", "Dr. James Wright"]
    setting = "Quantum Computing Research Facility"

    # Initialize generator
    generator = ChapterGenerator(genre)

    print("Generating chapter blueprint...")
    # Generate chapter
    chapter_text = generator.generate_chapter(
        chapter_num=chapter_num,
        plot_point=plot_point,
        characters=characters,
        setting=setting,
        previous_events=["System anomaly detected", "Unauthorized processes running"]
    )

    # Analyze the generated chapter
    print("\nAnalyzing generated chapter...")
    analyzer = SceneDepthAnalyzer()

    # Get word count
    word_count = len(chapter_text.split())
    print(f"\n📊 Initial Generation:")
    print(f"  • Word count: {word_count}")

    # If too short, optimize
    if word_count < 1500:
        print(f"  • Status: Too short, optimizing...")

        optimizer = ChapterLengthOptimizer(genre)
        optimized_text, metrics = optimizer.optimize_chapter(
            chapter_text,
            chapter_num,
            plot_point,
            characters
        )

        chapter_text = optimized_text
        word_count = metrics.current_word_count

        print(f"\n📈 After Optimization:")
        print(f"  • Word count: {word_count}")
        print(f"  • Depth score: {metrics.depth_score:.1f}/100")
        print(f"  • Detail density: {metrics.detail_density:.1f}/1000 words")
        print(f"  • Measurement density: {metrics.measurement_density:.1f}/1000 words")
        print(f"  • Expansions applied: {', '.join(metrics.expansions_applied)}")

    # Analyze scenes
    scenes = chapter_text.split('\n\n')
    scene_count = len([s for s in scenes if len(s) > 100])  # Count substantial paragraphs

    print(f"\n📖 Chapter Structure:")
    print(f"  • Scenes: {scene_count}")
    print(f"  • Average words per scene: {word_count // max(1, scene_count)}")

    # Analyze first scene depth
    if scenes:
        first_scene_analysis = analyzer.analyze_scene(scenes[0], "scene_1")

        print(f"\n🔍 First Scene Analysis:")
        print(f"  • Depth score: {first_scene_analysis.depth_score:.1f}/100")
        print(f"  • Complexity: {first_scene_analysis.complexity_rating}")
        print(f"  • Measurements: {first_scene_analysis.measurements}")
        print(f"  • Sensory details: {first_scene_analysis.sensory_details}")
        print(f"  • Character thoughts: {first_scene_analysis.character_thoughts}")
        print(f"  • Time markers: {first_scene_analysis.time_markers}")
        print(f"  • Action beats: {first_scene_analysis.action_beats}")

    # Quality validation
    print(f"\n✅ Quality Metrics:")

    # Count obsessive details
    import re
    measurements = len(re.findall(r'\d+\.?\d*\s*[°%]', chapter_text))
    time_refs = len(re.findall(r'\d{1,2}:\d{2}', chapter_text))
    precise_numbers = len(re.findall(r'\d+\.?\d+', chapter_text))

    print(f"  • Measurements: {measurements}")
    print(f"  • Time references: {time_refs}")
    print(f"  • Precise numbers: {precise_numbers}")
    print(f"  • Total obsessive details: {measurements + time_refs + precise_numbers}")

    # Check for required elements
    has_countdown = "countdown" in chapter_text.lower() or "T-minus" in chapter_text
    has_probability = "probability" in chapter_text.lower() or "%" in chapter_text
    has_temperature = "°C" in chapter_text or "degrees" in chapter_text.lower()
    has_heart_rate = "BPM" in chapter_text or "heart rate" in chapter_text.lower()

    print(f"\n🎯 Required Elements:")
    print(f"  • Countdown/Timer: {'✓' if has_countdown else '✗'}")
    print(f"  • Probability/Percentage: {'✓' if has_probability else '✗'}")
    print(f"  • Temperature readings: {'✓' if has_temperature else '✗'}")
    print(f"  • Physiological data: {'✓' if has_heart_rate else '✗'}")

    # Final assessment
    print(f"\n📝 Final Assessment:")

    if word_count >= 1500 and word_count <= 2500:
        if measurements >= 10 and time_refs >= 3:
            print("  🏆 EXCELLENT - Publication ready!")
            print(f"  • {word_count} words of rich, detailed narrative")
            print("  • High density of obsessive details")
            print("  • No fluff - every word serves the story")
        else:
            print("  ✅ GOOD - Proper length achieved")
            print("  • Could use more obsessive details")
    else:
        print("  ⚠️  NEEDS ADJUSTMENT")
        if word_count < 1500:
            print(f"  • Too short: {word_count} words (need 1500+)")
        else:
            print(f"  • Too long: {word_count} words (max 2500)")

    # Save the chapter
    output_path = Path("workspace/enhanced_chapter_test.md")
    output_path.parent.mkdir(exist_ok=True)
    output_path.write_text(chapter_text)

    print(f"\n💾 Chapter saved to: {output_path}")

    # Show excerpt
    print(f"\n📄 First 500 characters:")
    print("-" * 40)
    print(chapter_text[:500] + "...")

    return chapter_text, word_count


def main():
    """Run the test"""
    chapter, word_count = test_chapter_generation()

    print("\n" + "="*60)
    print("✅ TEST COMPLETE")
    print("="*60)
    print(f"\nGenerated {word_count} words of content-rich narrative")
    print("No fluff, no filler - pure story substance")


if __name__ == "__main__":
    main()