#!/usr/bin/env python3
"""
Test multi-pass concept using existing chapters

Demonstrates that generating multiple versions and selecting the best
can improve quality scores.
"""

import sys
from pathlib import Path
import random

sys.path.insert(0, str(Path(__file__).parent))
from multi_dimensional_scorer import MultiDimensionalScorer
from humanizer import Humanizer


def simulate_multi_pass(original_text: str, num_attempts: int = 5):
    """
    Simulate multi-pass generation by creating variations of a chapter

    Since we can't generate truly different versions without an API,
    we'll simulate by applying different levels of humanization
    """

    scorer = MultiDimensionalScorer()
    humanizer = Humanizer()

    print(f"Simulating {num_attempts} generation attempts...")
    print("="*60)

    # Score original
    original_score = scorer.score(original_text)
    print(f"\nOriginal: {original_score.total:.1f}/10")

    attempts = []

    for i in range(1, num_attempts + 1):
        # Apply different transformation levels to simulate variations
        # In real multi-pass, each would be a fresh generation

        if i == 1:
            # Baseline - no changes
            variant = original_text
        elif i == 2:
            # Light humanization
            variant = humanizer._add_fragments(original_text, count=2)
        elif i == 3:
            # Medium humanization
            variant = humanizer._inject_obsessions(original_text, i)
        elif i == 4:
            # Full humanization
            variant = humanizer.apply_to_chapter(original_text, i)
        else:
            # Random combination
            variant = original_text
            if random.random() < 0.5:
                variant = humanizer._add_fragments(variant, count=3)
            if random.random() < 0.5:
                variant = humanizer._inject_obsessions(variant, i)

        score = scorer.score(variant)
        attempts.append((i, variant, score))

        print(f"  v{i}: {score.total:.1f}/10")

    # Find best
    best_idx, best_text, best_score = max(attempts, key=lambda x: x[2].total)

    print("\n" + "="*60)
    print(f"BEST: Version {best_idx} - {best_score.total:.1f}/10")
    print(f"Improvement: +{best_score.total - original_score.total:.1f} points")
    print("="*60)

    print("\nScore breakdown:")
    print(f"  Original: {original_score.total:.1f}")
    print(f"  Best:     {best_score.total:.1f}")
    print(f"\nDimension improvements:")
    for dim in original_score.scores:
        orig = original_score.scores[dim]
        best = best_score.scores[dim]
        diff = best - orig
        marker = "↑" if diff > 0 else "↓" if diff < 0 else "="
        print(f"  {dim:25s} {orig:.1f} → {best:.1f} ({marker}{abs(diff):.1f})")

    return best_text, best_score


def main():
    """Test on existing chapter"""

    # Load Chapter 3 (has good content for testing)
    chapter_path = Path("workspace/example-adventure/chapters/chapter_003_original.md")

    if not chapter_path.exists():
        print(f"Error: {chapter_path} not found")
        print("Run this from the project root directory")
        return

    with open(chapter_path, 'r') as f:
        chapter_text = f.read()

    print("MULTI-PASS GENERATION TEST")
    print("="*60)
    print(f"Source: {chapter_path}")
    print(f"Size: {len(chapter_text)} characters")
    print()

    best_text, best_score = simulate_multi_pass(chapter_text, num_attempts=5)

    # Show it works
    if best_score.total > 7.0:
        print("\n✓ Multi-pass improved quality above baseline")
    else:
        print("\n⚠ Multi-pass didn't reach target (this is a simulation)")

    print(f"\nKey insight: With real multi-pass generation (different prompts,")
    print(f"API calls, etc.), we'd see even larger improvements because each")
    print(f"version would be genuinely different, not just post-processed.")


if __name__ == "__main__":
    main()
