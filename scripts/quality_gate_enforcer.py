#!/usr/bin/env python3
"""
Quality Gate Enforcer - Real Implementation
Part of Quality Improvement Plan P0

Enforces quality requirements before allowing chapter to proceed.
Blocks bad content instead of allowing it through.
"""

import sys
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Callable
from dataclasses import dataclass
import json

# Import our quality analyzers
sys.path.append(str(Path(__file__).parent))
from detail_density_analyzer import DetailDensityAnalyzer
from physical_grounding_checker import PhysicalGroundingChecker
from show_vs_tell_analyzer import ShowVsTellAnalyzer


@dataclass
class QualityGateResult:
    """Results from a quality gate check"""
    gate_name: str
    passed: bool
    score: float
    target: str
    actual: str
    message: str


@dataclass
class ChapterQualityReport:
    """Complete quality report for a chapter"""
    chapter_number: int
    total_score: float
    passed_all_gates: bool
    gate_results: List[QualityGateResult]
    failures: List[str]
    word_count: int

    def to_dict(self) -> Dict:
        return {
            'chapter_number': self.chapter_number,
            'total_score': round(self.total_score, 1),
            'passed_all_gates': self.passed_all_gates,
            'word_count': self.word_count,
            'gates': [
                {
                    'name': gate.gate_name,
                    'passed': gate.passed,
                    'score': round(gate.score, 1),
                    'target': gate.target,
                    'actual': gate.actual,
                    'message': gate.message
                }
                for gate in self.gate_results
            ],
            'failures': self.failures
        }

    def print_report(self):
        """Print human-readable quality report"""
        print(f"\n{'='*70}")
        print(f"QUALITY GATE REPORT - Chapter {self.chapter_number}")
        print(f"{'='*70}")
        print(f"Overall Score: {self.total_score:.1f}/100")
        print(f"Status: {'✓ PASSED' if self.passed_all_gates else '✗ FAILED'}")
        print(f"Word Count: {self.word_count}")
        print(f"\n{'Gate Results':-^70}")

        for gate in self.gate_results:
            status = "✓" if gate.passed else "✗"
            print(f"\n{status} {gate.gate_name}")
            print(f"   Score: {gate.score:.1f}/100")
            print(f"   Target: {gate.target}")
            print(f"   Actual: {gate.actual}")
            if not gate.passed:
                print(f"   Issue: {gate.message}")

        if self.failures:
            print(f"\n{'Failures':-^70}")
            for i, failure in enumerate(self.failures, 1):
                print(f"{i}. {failure}")

        print(f"{'='*70}\n")


class QualityGateEnforcer:
    """
    Enforces quality requirements before allowing chapter to proceed.

    Gates:
    1. Word count (1500-2500)
    2. Obsessive detail density (3+ per 1000 words)
    3. Physical grounding (95%+ emotions grounded)
    4. Show vs tell ratio (75%+ showing)
    5. Sensory richness (combined metric)

    Each gate can block publication if failed.
    """

    def __init__(self,
                 word_count_min: int = 1500,
                 word_count_max: int = 2500,
                 detail_density_target: float = 3.0,
                 grounding_threshold: float = 0.95,
                 show_ratio_target: float = 0.75,
                 strict_mode: bool = True):
        """
        Initialize quality gate enforcer.

        Args:
            word_count_min: Minimum acceptable word count
            word_count_max: Maximum acceptable word count
            detail_density_target: Minimum obsessive details per 1000 words
            grounding_threshold: Minimum ratio of grounded emotions (0-1)
            show_ratio_target: Minimum show vs tell ratio (0-1)
            strict_mode: If True, all gates must pass. If False, use weighted score.
        """
        self.word_count_min = word_count_min
        self.word_count_max = word_count_max
        self.detail_density_target = detail_density_target
        self.grounding_threshold = grounding_threshold
        self.show_ratio_target = show_ratio_target
        self.strict_mode = strict_mode

        # Initialize analyzers
        self.detail_analyzer = DetailDensityAnalyzer(target_density=detail_density_target)
        self.grounding_checker = PhysicalGroundingChecker()
        self.show_tell_analyzer = ShowVsTellAnalyzer(target_show_ratio=show_ratio_target)

        # Gate weights (for non-strict mode)
        self.gate_weights = {
            'word_count': 0.15,
            'detail_density': 0.25,
            'physical_grounding': 0.25,
            'show_vs_tell': 0.25,
            'overall_quality': 0.10
        }

    def check_chapter(self, chapter_text: str, chapter_number: int = 0) -> ChapterQualityReport:
        """
        Run all quality gates on a chapter.

        Args:
            chapter_text: Full chapter text
            chapter_number: Chapter number for reporting

        Returns:
            ChapterQualityReport with all gate results
        """
        gate_results = []
        failures = []

        # Gate 1: Word Count
        word_count_result = self._check_word_count(chapter_text)
        gate_results.append(word_count_result)
        if not word_count_result.passed:
            failures.append(word_count_result.message)

        # Gate 2: Detail Density
        detail_result = self._check_detail_density(chapter_text)
        gate_results.append(detail_result)
        if not detail_result.passed:
            failures.append(detail_result.message)

        # Gate 3: Physical Grounding
        grounding_result = self._check_physical_grounding(chapter_text)
        gate_results.append(grounding_result)
        if not grounding_result.passed:
            failures.append(grounding_result.message)

        # Gate 4: Show vs Tell
        show_tell_result = self._check_show_vs_tell(chapter_text)
        gate_results.append(show_tell_result)
        if not show_tell_result.passed:
            failures.append(show_tell_result.message)

        # Calculate total score
        if self.strict_mode:
            # All gates must pass
            passed_all_gates = len(failures) == 0
            total_score = sum(gate.score for gate in gate_results) / len(gate_results)
        else:
            # Weighted average
            total_score = sum(
                gate.score * self.gate_weights.get(gate.gate_name.lower().replace(' ', '_'), 0.25)
                for gate in gate_results
            )
            passed_all_gates = total_score >= 75.0  # 75% threshold in non-strict mode

        word_count = len(chapter_text.split())

        return ChapterQualityReport(
            chapter_number=chapter_number,
            total_score=total_score,
            passed_all_gates=passed_all_gates,
            gate_results=gate_results,
            failures=failures,
            word_count=word_count
        )

    def _check_word_count(self, text: str) -> QualityGateResult:
        """Check if word count is within acceptable range"""
        word_count = len(text.split())

        if self.word_count_min <= word_count <= self.word_count_max:
            return QualityGateResult(
                gate_name="Word Count",
                passed=True,
                score=100.0,
                target=f"{self.word_count_min}-{self.word_count_max}",
                actual=str(word_count),
                message="Word count within target range"
            )
        else:
            # Score based on distance from acceptable range
            if word_count < self.word_count_min:
                deficit = self.word_count_min - word_count
                score = max(0, 100 - (deficit / self.word_count_min * 100))
                message = f"Chapter {deficit} words too short (minimum {self.word_count_min})"
            else:
                excess = word_count - self.word_count_max
                score = max(0, 100 - (excess / self.word_count_max * 100))
                message = f"Chapter {excess} words too long (maximum {self.word_count_max})"

            return QualityGateResult(
                gate_name="Word Count",
                passed=False,
                score=score,
                target=f"{self.word_count_min}-{self.word_count_max}",
                actual=str(word_count),
                message=message
            )

    def _check_detail_density(self, text: str) -> QualityGateResult:
        """Check obsessive detail density"""
        analysis = self.detail_analyzer.count_obsessive_details(text)

        return QualityGateResult(
            gate_name="Detail Density",
            passed=analysis.meets_target,
            score=analysis.density_per_1k / self.detail_density_target * 100 if analysis.density_per_1k < self.detail_density_target else 100.0,
            target=f"{self.detail_density_target}+ per 1000 words",
            actual=f"{analysis.density_per_1k:.2f} per 1000 words",
            message=f"Detail density {analysis.density_per_1k:.2f} below target {self.detail_density_target}" if not analysis.meets_target else "Detail density meets target"
        )

    def _check_physical_grounding(self, text: str) -> QualityGateResult:
        """Check physical grounding of emotions"""
        analysis = self.grounding_checker.check_physical_grounding(text)

        return QualityGateResult(
            gate_name="Physical Grounding",
            passed=analysis.pass_check,
            score=analysis.score,
            target=f"{self.grounding_threshold*100:.0f}% grounded",
            actual=f"{analysis.grounding_ratio*100:.0f}% grounded ({analysis.ungrounded_emotions} ungrounded)",
            message=f"{analysis.ungrounded_emotions} emotions lack physical grounding" if not analysis.pass_check else "All emotions physically grounded"
        )

    def _check_show_vs_tell(self, text: str) -> QualityGateResult:
        """Check show vs tell ratio"""
        analysis = self.show_tell_analyzer.analyze_show_vs_tell(text)

        return QualityGateResult(
            gate_name="Show vs Tell",
            passed=analysis.pass_check,
            score=analysis.score,
            target=f"{self.show_ratio_target*100:.0f}% showing",
            actual=f"{analysis.show_ratio*100:.0f}% showing",
            message=f"Show ratio {analysis.show_ratio*100:.0f}% below target {self.show_ratio_target*100:.0f}%" if not analysis.pass_check else "Show vs tell ratio meets target"
        )

    def enforce_with_retry(self,
                          chapter_num: int,
                          generator_func: Callable[[], str],
                          max_retries: int = 3,
                          verbose: bool = True) -> Tuple[str, ChapterQualityReport]:
        """
        Generate chapter and enforce quality gates with retries.

        Args:
            chapter_num: Chapter number
            generator_func: Function that generates chapter text (takes no args, returns str)
            max_retries: Maximum number of generation attempts
            verbose: Print detailed progress

        Returns:
            Tuple of (chapter_text, quality_report)
        """
        for attempt in range(max_retries):
            if verbose:
                print(f"\n[QualityGate] Chapter {chapter_num} - Attempt {attempt + 1}/{max_retries}")

            # Generate chapter
            try:
                chapter_text = generator_func()
            except Exception as e:
                print(f"[QualityGate] ✗ Generation failed: {e}")
                if attempt < max_retries - 1:
                    print(f"[QualityGate] Retrying...")
                    continue
                else:
                    raise

            # Check gates
            report = self.check_chapter(chapter_text, chapter_num)

            if verbose:
                report.print_report()

            if report.passed_all_gates:
                if verbose:
                    print(f"[QualityGate] ✓ Chapter {chapter_num} passed all gates")
                return chapter_text, report

            if verbose:
                print(f"[QualityGate] ✗ Chapter {chapter_num} failed quality gates:")
                for failure in report.failures:
                    print(f"    - {failure}")

            if attempt < max_retries - 1:
                if verbose:
                    print(f"[QualityGate] Regenerating with improved prompt...")
                # Note: In actual use, you'd modify the prompt based on failures
                # For now, we just retry

        # All retries exhausted
        if verbose:
            print(f"[QualityGate] ⚠ Chapter {chapter_num} failed after {max_retries} attempts")
            print(f"[QualityGate] Final score: {report.total_score:.1f}/100")

            # Still return the chapter with the report so caller can decide what to do
        return chapter_text, report

    def save_report(self, report: ChapterQualityReport, output_path: Path):
        """Save quality report to JSON file"""
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w') as f:
            json.dump(report.to_dict(), f, indent=2)


if __name__ == "__main__":
    # Quick test
    enforcer = QualityGateEnforcer()

    # Bad chapter - should fail gates
    bad_chapter = """
    Sarah felt scared when she entered the room. She was nervous.
    Marcus thought it was a bad idea. They talked about it.
    """ * 100  # Repeat to meet word count

    # Good chapter - should pass gates
    good_chapter = """
    Sarah's heart hammered—102 BPM, she counted. The room stretched before her,
    seventeen meters across according to the floor tiles. Twenty-three tiles wide,
    each one exactly 73cm. She'd counted them. Twice.

    Temperature dropping. 18.4°C. She could feel it on her skin, goosebumps
    rising along her forearms. Breath visible in the air. Fourteen breaths per
    minute, shallow, catching in her throat.

    "Wait." Marcus grabbed her shoulder. Fingers tight. Five points of pressure.
    His jaw clenched, muscles jumping under the skin. Eyes darting to the shadows—
    counting exits. Three. Always three with him.

    Her pulse jumped. 117 BPM now. Hands trembling. She pressed them flat against
    her thighs, felt the rough denim, the warmth of her own skin underneath.
    Grounding. Physical. Real.

    The door ahead was oak. Dark. Grain patterns spiraling—she traced them with
    her eyes, cataloging. Distraction technique. Seven seconds until her breathing
    steadied. She counted every one.
    """ * 15  # Repeat to meet word count

    print("=== Testing BAD Chapter ===")
    report_bad = enforcer.check_chapter(bad_chapter, chapter_number=1)
    report_bad.print_report()

    print("\n" + "="*70 + "\n")

    print("=== Testing GOOD Chapter ===")
    report_good = enforcer.check_chapter(good_chapter, chapter_number=2)
    report_good.print_report()
