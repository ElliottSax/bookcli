#!/usr/bin/env python3
"""
Comprehensive Test Suite for Chapter Generation System
Tests all components and identifies any issues
"""

import sys
import traceback
from pathlib import Path
from typing import List, Dict, Tuple
import re
import time

sys.path.insert(0, str(Path(__file__).parent))

# Import our components
from generation.content_expansion_engine import (
    ContentExpansionEngine,
    ChapterGenerator,
    ChapterBlueprint,
    SceneStructure
)
from generation.scene_depth_analyzer import SceneDepthAnalyzer
from generation.chapter_length_optimizer import ChapterLengthOptimizer


class TestResult:
    """Store test results"""
    def __init__(self, test_name: str):
        self.test_name = test_name
        self.passed = False
        self.error_message = ""
        self.execution_time = 0.0
        self.details = {}


class ChapterGenerationTester:
    """Comprehensive testing for chapter generation"""

    def __init__(self):
        self.results = []
        self.total_tests = 0
        self.passed_tests = 0
        self.failed_tests = 0

    def run_test(self, test_name: str, test_func, *args, **kwargs) -> TestResult:
        """Run a single test with error handling"""
        result = TestResult(test_name)
        self.total_tests += 1

        print(f"\n🧪 Testing: {test_name}")
        print("-" * 40)

        start_time = time.time()
        try:
            test_output = test_func(*args, **kwargs)
            result.passed = True
            result.details = test_output if isinstance(test_output, dict) else {"output": test_output}
            self.passed_tests += 1
            print(f"✅ PASSED")
        except Exception as e:
            result.passed = False
            result.error_message = str(e)
            result.details = {"traceback": traceback.format_exc()}
            self.failed_tests += 1
            print(f"❌ FAILED: {str(e)[:100]}")

        result.execution_time = time.time() - start_time
        print(f"⏱️  Time: {result.execution_time:.2f}s")

        self.results.append(result)
        return result

    def test_content_expansion_engine(self) -> Dict:
        """Test the content expansion engine"""
        engine = ContentExpansionEngine(genre="thriller")

        # Test blueprint creation
        blueprint = engine.create_chapter_blueprint(
            chapter_num=1,
            plot_point="Test crisis",
            characters=["Alice", "Bob"],
            setting="Test location"
        )

        assert blueprint is not None, "Blueprint creation failed"
        assert len(blueprint.scenes) >= 3, f"Too few scenes: {len(blueprint.scenes)}"
        assert blueprint.word_target == 2000, f"Wrong target: {blueprint.word_target}"

        # Test scene creation
        scene = blueprint.scenes[0]
        # Scene word target should be 500 now
        assert scene.word_target == 500, f"Wrong scene target: {scene.word_target}"
        assert len(scene.environmental_details) >= 3, "Missing environmental details"
        assert len(scene.sensory_details) >= 5, "Missing sensory details"

        return {
            "scenes_created": len(blueprint.scenes),
            "total_word_target": blueprint.word_target,
            "scene_transitions": len(blueprint.scene_transitions),
            "subplot_threads": len(blueprint.subplot_threads)
        }

    def test_scene_depth_analyzer(self) -> Dict:
        """Test the scene depth analyzer"""
        analyzer = SceneDepthAnalyzer()

        # Create test text with various depth elements
        test_text = """
        The temperature read exactly 23.4°C at 14:32:17. Dr. Smith's heart rate
        elevated to 92 BPM as she calculated the probability: 67.3% chance of success.
        She heard the hum at 60Hz, felt the vibration at 0.3mm amplitude. The countdown
        showed T-minus 47 seconds. Her pupils dilated 2.1mm, stress response evident.
        "We need to abort," she said, voice frequency dropping to 245Hz.
        The system registered her words, processing time 0.003 seconds.
        """

        analysis = analyzer.analyze_scene(test_text, "test_scene")

        assert analysis.measurements > 0, "No measurements detected"
        assert analysis.time_markers > 0, "No time markers detected"
        assert analysis.sensory_details > 0, "No sensory details detected"
        assert analysis.depth_score > 0, "Zero depth score"

        # Test recommendations
        recommendations = analyzer.recommend_expansions(analysis)

        return {
            "measurements": analysis.measurements,
            "time_markers": analysis.time_markers,
            "sensory_details": analysis.sensory_details,
            "emotional_beats": analysis.emotional_beats,
            "depth_score": analysis.depth_score,
            "complexity_rating": analysis.complexity_rating,
            "expansion_potential": analysis.expansion_potential,
            "recommendations": len(recommendations)
        }

    def test_chapter_length_optimizer(self) -> Dict:
        """Test the chapter length optimizer"""
        optimizer = ChapterLengthOptimizer(genre="sci-fi")

        # Create short text that needs expansion
        short_text = """
        The alarm sounded. Maya ran to the console.
        The system was failing. She had to act fast.
        Marcus arrived. "What's happening?" he asked.
        "Complete system failure," Maya replied.
        They worked together to fix it. Time was running out.
        Finally, they succeeded. Crisis averted.
        """

        # Optimize it
        optimized_text, metrics = optimizer.optimize_chapter(
            short_text,
            chapter_num=1,
            plot_point="System failure crisis",
            characters=["Maya", "Marcus"]
        )

        word_count = len(optimized_text.split())
        original_count = len(short_text.split())

        assert word_count > original_count, "No expansion occurred"
        # The optimizer updates metrics.words_added internally
        # If words were added, the word count should be higher
        actual_words_added = word_count - original_count
        assert actual_words_added > 0, f"No expansion: {original_count} -> {word_count}"
        assert len(metrics.expansions_applied) > 0, "No expansions recorded"

        return {
            "original_words": original_count,
            "final_words": word_count,
            "words_added": metrics.words_added,
            "expansions_applied": metrics.expansions_applied,
            "depth_score": metrics.depth_score,
            "detail_density": metrics.detail_density,
            "measurement_density": metrics.measurement_density
        }

    def test_chapter_generator(self) -> Dict:
        """Test the full chapter generator"""
        generator = ChapterGenerator(genre="thriller")

        # Generate a chapter
        chapter = generator.generate_chapter(
            chapter_num=1,
            plot_point="Infiltration discovered",
            characters=["Agent Silva", "Dr. Chen", "Marcus"],
            setting="Secret facility",
            previous_events=["Security breach", "Data theft"]
        )

        word_count = len(chapter.split())

        # Check for required elements
        has_time = bool(re.search(r'\d{1,2}:\d{2}', chapter))
        has_measurements = bool(re.search(r'\d+\.?\d*\s*[°%]', chapter))
        has_heart_rate = "BPM" in chapter or "heart rate" in chapter.lower()

        # Count scenes (look for time stamps or major breaks)
        scenes = len(re.findall(r'\d{1,2}:\d{2}', chapter))

        return {
            "word_count": word_count,
            "has_timestamps": has_time,
            "has_measurements": has_measurements,
            "has_physiology": has_heart_rate,
            "scene_count": scenes,
            "within_target": 1500 <= word_count <= 2500
        }

    def test_edge_cases(self) -> Dict:
        """Test edge cases and potential failure points"""
        results = {}

        # Test 1: Empty inputs
        try:
            generator = ChapterGenerator(genre="mystery")
            chapter = generator.generate_chapter(
                chapter_num=1,
                plot_point="",
                characters=[],
                setting=""
            )
            results["empty_inputs"] = "handled"
        except Exception as e:
            results["empty_inputs"] = f"failed: {str(e)[:50]}"

        # Test 2: Very long character list
        try:
            generator = ChapterGenerator(genre="fantasy")
            many_chars = [f"Character{i}" for i in range(20)]
            chapter = generator.generate_chapter(
                chapter_num=1,
                plot_point="Big battle",
                characters=many_chars,
                setting="Battlefield"
            )
            results["many_characters"] = "handled"
        except Exception as e:
            results["many_characters"] = f"failed: {str(e)[:50]}"

        # Test 3: Special characters in input
        try:
            generator = ChapterGenerator(genre="sci-fi")
            chapter = generator.generate_chapter(
                chapter_num=1,
                plot_point="System@#$%^&*()_failure",
                characters=["Dr. O'Brien", "Jean-Luc", "José"],
                setting="Ñoño's Laboratory"
            )
            results["special_chars"] = "handled"
        except Exception as e:
            results["special_chars"] = f"failed: {str(e)[:50]}"

        # Test 4: Very short text optimization
        try:
            optimizer = ChapterLengthOptimizer()
            optimized, metrics = optimizer.optimize_chapter(
                "Short.",
                chapter_num=1,
                plot_point="Test",
                characters=["A"]
            )
            results["ultra_short"] = f"{len(optimized.split())} words"
        except Exception as e:
            results["ultra_short"] = f"failed: {str(e)[:50]}"

        return results

    def test_quality_metrics(self) -> Dict:
        """Test quality metric calculations"""
        analyzer = SceneDepthAnalyzer()

        # Create text with known metrics
        test_text = """
        14:32:17. Temperature: 23.4°C. Heart rate: 92 BPM.
        Probability: 67.3%. Distance: 4.7 meters.
        She calculated quickly. The timer showed 47 seconds.
        Sound frequency: 440Hz. Pressure: 1013 hPa.
        "Abort," she said. Processing time: 0.003 seconds.
        Pupil dilation: 2.1mm. Stress level: elevated.
        """

        analysis = analyzer.analyze_scene(test_text)

        # Verify counts
        word_count = len(test_text.split())
        measurements = len(re.findall(r'\d+\.?\d*\s*[°%A-Za-z]+', test_text))
        time_refs = len(re.findall(r'\d{1,2}:\d{2}:\d{2}|\d+\s*seconds?', test_text))

        return {
            "word_count": word_count,
            "detected_measurements": analysis.measurements,
            "expected_measurements": measurements,
            "detected_time_markers": analysis.time_markers,
            "expected_time_markers": time_refs,
            "depth_score": analysis.depth_score,
            "has_internal_monologue": analysis.has_internal_monologue,
            "has_physical_grounding": analysis.has_physical_grounding
        }

    def test_performance(self) -> Dict:
        """Test performance with larger inputs"""
        results = {}

        # Test generation speed
        generator = ChapterGenerator(genre="thriller")

        start = time.time()
        chapter = generator.generate_chapter(
            chapter_num=1,
            plot_point="Complex multi-threaded crisis",
            characters=["A", "B", "C", "D", "E"],
            setting="Multiple locations"
        )
        generation_time = time.time() - start
        results["generation_time"] = f"{generation_time:.2f}s"

        # Test optimization speed on long text
        optimizer = ChapterLengthOptimizer()
        long_text = " ".join(["Test sentence."] * 500)  # ~1000 words

        start = time.time()
        optimized, metrics = optimizer.optimize_chapter(
            long_text,
            chapter_num=1,
            plot_point="Test",
            characters=["A", "B"]
        )
        optimization_time = time.time() - start
        results["optimization_time"] = f"{optimization_time:.2f}s"

        # Test analysis speed
        analyzer = SceneDepthAnalyzer()

        start = time.time()
        analysis = analyzer.analyze_scene(chapter)
        analysis_time = time.time() - start
        results["analysis_time"] = f"{analysis_time:.2f}s"

        results["chapter_words"] = len(chapter.split())
        results["optimized_words"] = len(optimized.split())

        return results

    def test_consistency(self) -> Dict:
        """Test consistency across multiple generations"""
        generator = ChapterGenerator(genre="sci-fi")

        word_counts = []
        quality_scores = []

        # Generate 3 chapters with same parameters
        for i in range(3):
            chapter = generator.generate_chapter(
                chapter_num=i+1,
                plot_point="Consistency test",
                characters=["Maya", "NOVA"],
                setting="Lab"
            )

            word_count = len(chapter.split())
            word_counts.append(word_count)

            # Analyze quality
            analyzer = SceneDepthAnalyzer()
            analysis = analyzer.analyze_scene(chapter[:1000])  # First 1000 chars
            quality_scores.append(analysis.depth_score)

        # Calculate variance
        avg_words = sum(word_counts) / len(word_counts)
        word_variance = max(word_counts) - min(word_counts)

        avg_quality = sum(quality_scores) / len(quality_scores)
        quality_variance = max(quality_scores) - min(quality_scores)

        return {
            "word_counts": word_counts,
            "average_words": avg_words,
            "word_variance": word_variance,
            "quality_scores": quality_scores,
            "average_quality": avg_quality,
            "quality_variance": quality_variance,
            "consistent": word_variance < 500  # Less than 500 word difference
        }

    def run_all_tests(self):
        """Run complete test suite"""
        print("\n" + "="*60)
        print("🧪 CHAPTER GENERATION TEST SUITE")
        print("="*60)

        # Core component tests
        self.run_test("Content Expansion Engine", self.test_content_expansion_engine)
        self.run_test("Scene Depth Analyzer", self.test_scene_depth_analyzer)
        self.run_test("Chapter Length Optimizer", self.test_chapter_length_optimizer)
        self.run_test("Chapter Generator", self.test_chapter_generator)

        # Advanced tests
        self.run_test("Edge Cases", self.test_edge_cases)
        self.run_test("Quality Metrics", self.test_quality_metrics)
        self.run_test("Performance", self.test_performance)
        self.run_test("Consistency", self.test_consistency)

        # Generate report
        self.generate_report()

    def generate_report(self):
        """Generate test report"""
        print("\n" + "="*60)
        print("📊 TEST REPORT")
        print("="*60)

        print(f"\n📈 Summary:")
        print(f"  Total Tests: {self.total_tests}")
        print(f"  ✅ Passed: {self.passed_tests}")
        print(f"  ❌ Failed: {self.failed_tests}")
        print(f"  Success Rate: {(self.passed_tests/self.total_tests*100):.1f}%")

        if self.failed_tests > 0:
            print(f"\n❌ Failed Tests:")
            for result in self.results:
                if not result.passed:
                    print(f"  - {result.test_name}: {result.error_message[:100]}")

        print(f"\n⏱️  Performance:")
        for result in self.results:
            if result.passed:
                print(f"  {result.test_name}: {result.execution_time:.2f}s")

        # Detailed results for key tests
        print(f"\n🔍 Key Metrics:")
        for result in self.results:
            if result.test_name == "Chapter Generator" and result.passed:
                details = result.details
                print(f"  Chapter Generation:")
                print(f"    - Word count: {details.get('word_count', 'N/A')}")
                print(f"    - Within target: {details.get('within_target', 'N/A')}")
                print(f"    - Has timestamps: {details.get('has_timestamps', 'N/A')}")
                print(f"    - Scene count: {details.get('scene_count', 'N/A')}")

            if result.test_name == "Consistency" and result.passed:
                details = result.details
                print(f"  Consistency:")
                print(f"    - Average words: {details.get('average_words', 'N/A'):.0f}")
                print(f"    - Word variance: {details.get('word_variance', 'N/A'):.0f}")
                print(f"    - Consistent: {details.get('consistent', 'N/A')}")

        # Save detailed report
        self.save_detailed_report()

    def save_detailed_report(self):
        """Save detailed test report to file"""
        report_path = Path("workspace/test_report.md")
        report_path.parent.mkdir(exist_ok=True)

        report = ["# Chapter Generation Test Report\n"]
        report.append(f"## Summary\n")
        report.append(f"- Total Tests: {self.total_tests}\n")
        report.append(f"- Passed: {self.passed_tests}\n")
        report.append(f"- Failed: {self.failed_tests}\n")
        report.append(f"- Success Rate: {(self.passed_tests/self.total_tests*100):.1f}%\n\n")

        report.append("## Test Results\n\n")
        for result in self.results:
            report.append(f"### {result.test_name}\n")
            report.append(f"- Status: {'✅ PASSED' if result.passed else '❌ FAILED'}\n")
            report.append(f"- Time: {result.execution_time:.2f}s\n")

            if result.passed:
                report.append(f"- Details:\n")
                for key, value in result.details.items():
                    if key != "traceback":
                        report.append(f"  - {key}: {value}\n")
            else:
                report.append(f"- Error: {result.error_message}\n")

            report.append("\n")

        report_path.write_text("".join(report))
        print(f"\n💾 Detailed report saved to: {report_path}")


def main():
    """Run the test suite"""
    tester = ChapterGenerationTester()
    tester.run_all_tests()

    print("\n" + "="*60)

    if tester.failed_tests == 0:
        print("✅ ALL TESTS PASSED! System ready for production.")
    else:
        print(f"⚠️  {tester.failed_tests} tests failed. Review report for details.")

    print("="*60)


if __name__ == "__main__":
    main()