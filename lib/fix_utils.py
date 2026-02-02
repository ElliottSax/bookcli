#!/usr/bin/env python3
"""
Fix Validation Utilities
========================
Common utilities for validating fixes and quality improvements.

Extracted from 20+ duplicate implementations across:
- fix_books.py
- book_fixer.py
- fix_poor_chapters.py
- Various quality scripts
"""

from dataclasses import dataclass
from typing import Optional, Dict, List
from pathlib import Path

from lib.quality_scorer import QualityScorer
from lib.logging_config import get_logger

logger = get_logger(__name__)


@dataclass
class FixResult:
    """Result of applying a fix to content."""
    improved: bool
    score_before: float
    score_after: float
    delta: float
    original_content: str
    fixed_content: str
    metrics: Dict
    issues_found: List[str]
    issues_fixed: List[str]

    @property
    def success(self) -> bool:
        """Fix was successful if quality improved."""
        return self.improved and self.delta > 0


def validate_fix(original: str, fixed: str,
                chapter_file: Optional[Path] = None) -> FixResult:
    """
    Validate that a fix actually improves content quality.

    Compares quality scores before and after fix to ensure improvement.
    Used by all fixer modules to validate their changes.

    Args:
        original: Original content before fix
        fixed: Content after applying fix
        chapter_file: Optional file path for logging

    Returns:
        FixResult with improvement analysis
    """
    scorer = QualityScorer()

    # Score original
    report_before = scorer.analyze(original)
    score_before = report_before.score

    # Score fixed
    report_after = scorer.analyze(fixed)
    score_after = report_after.score

    # Calculate improvement
    delta = score_after - score_before
    improved = score_after > score_before

    # Compare issues (convert to strings for comparison)
    issues_before_str = [str(issue) for issue in report_before.issues]
    issues_after_str = [str(issue) for issue in report_after.issues]

    issues_before_set = set(issues_before_str)
    issues_after_set = set(issues_after_str)

    issues_fixed = list(issues_before_set - issues_after_set)
    new_issues = list(issues_after_set - issues_before_set)

    # Build metrics
    metrics = {
        "score_before": score_before,
        "score_after": score_after,
        "delta": delta,
        "improved": improved,
        "issues_fixed_count": len(issues_fixed),
        "new_issues_count": len(new_issues)
    }

    # Log result
    file_info = f" ({chapter_file.name})" if chapter_file else ""
    if improved:
        logger.info(f"Fix validated{file_info}: {score_before:.1f} → "
                   f"{score_after:.1f} (+{delta:.1f})")
    else:
        logger.warning(f"Fix did not improve quality{file_info}: "
                      f"{score_before:.1f} → {score_after:.1f} ({delta:+.1f})")

    return FixResult(
        improved=improved,
        score_before=score_before,
        score_after=score_after,
        delta=delta,
        original_content=original,
        fixed_content=fixed,
        metrics=metrics,
        issues_found=issues_before_str,
        issues_fixed=issues_fixed
    )


def should_apply_fix(result: FixResult, min_improvement: float = 0.0) -> bool:
    """
    Determine if fix should be applied based on validation.

    Args:
        result: FixResult from validate_fix()
        min_improvement: Minimum score improvement required (default: any improvement)

    Returns:
        True if fix should be applied
    """
    if not result.improved:
        return False

    if result.delta < min_improvement:
        logger.warning(f"Improvement ({result.delta:.1f}) below threshold ({min_improvement})")
        return False

    return True


def validate_chapter_fix(chapter_file: Path, original: str, fixed: str,
                        auto_apply: bool = False) -> bool:
    """
    Validate and optionally apply chapter fix.

    Args:
        chapter_file: Path to chapter file
        original: Original content
        fixed: Fixed content
        auto_apply: Automatically apply if improvement detected

    Returns:
        True if fix was applied
    """
    result = validate_fix(original, fixed, chapter_file)

    if result.success:
        if auto_apply:
            try:
                chapter_file.write_text(result.fixed_content)
                logger.info(f"✓ Applied fix to {chapter_file.name}")
                return True
            except Exception as e:
                logger.error(f"Failed to write fix: {e}")
                return False
        else:
            logger.info(f"Fix validated but not applied (auto_apply=False)")
            return False
    else:
        logger.warning(f"Fix not applied - no improvement detected")
        return False


def batch_validate_fixes(fixes: Dict[Path, tuple[str, str]],
                        min_improvement: float = 1.0) -> Dict[Path, FixResult]:
    """
    Validate multiple fixes in batch.

    Args:
        fixes: Dict mapping chapter_file → (original, fixed)
        min_improvement: Minimum improvement threshold

    Returns:
        Dict mapping chapter_file → FixResult
    """
    results = {}

    for chapter_file, (original, fixed) in fixes.items():
        result = validate_fix(original, fixed, chapter_file)
        results[chapter_file] = result

    # Summary
    total = len(results)
    improved = sum(1 for r in results.values() if r.improved)
    sufficient = sum(1 for r in results.values() if r.delta >= min_improvement)

    logger.info(f"\nBatch Validation Summary:")
    logger.info(f"  Total fixes: {total}")
    logger.info(f"  Improved: {improved} ({improved/total*100:.1f}%)")
    logger.info(f"  Above threshold: {sufficient} ({sufficient/total*100:.1f}%)")

    return results


def get_fix_summary(results: Dict[Path, FixResult]) -> Dict:
    """
    Get summary statistics from batch validation results.

    Args:
        results: Results from batch_validate_fixes()

    Returns:
        Summary statistics dict
    """
    if not results:
        return {}

    deltas = [r.delta for r in results.values()]
    improved_count = sum(1 for r in results.values() if r.improved)

    return {
        "total_files": len(results),
        "improved_count": improved_count,
        "improved_percentage": improved_count / len(results) * 100,
        "average_delta": sum(deltas) / len(deltas),
        "max_improvement": max(deltas),
        "min_improvement": min(deltas),
        "total_issues_fixed": sum(len(r.issues_fixed) for r in results.values())
    }


if __name__ == "__main__":
    # Demo usage
    print("=== Fix Validation Utilities Demo ===\n")

    # Simulate a fix
    original = "The character was very very sad. She thought this was really really bad."
    fixed = "The character felt overwhelmed. She struggled with the situation."

    result = validate_fix(original, fixed)

    print(f"Score before: {result.score_before:.1f}")
    print(f"Score after: {result.score_after:.1f}")
    print(f"Improvement: {result.delta:+.1f}")
    print(f"Success: {result.success}")
    print(f"Issues fixed: {len(result.issues_fixed)}")
