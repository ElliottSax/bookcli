#!/usr/bin/env python3
"""
Multi-Pass Chapter Generator - Generates multiple versions and selects the best

Core ultra-tier technique: Generate 5-7 versions per chapter, score each,
select highest quality. This is more effective than post-processing fixes.
"""

import subprocess
import json
from pathlib import Path
from typing import List, Tuple, Optional
from dataclasses import dataclass
import sys

# Add scripts dir to path for imports
sys.path.insert(0, str(Path(__file__).parent))
from multi_dimensional_scorer import MultiDimensionalScorer, ScoringResult


@dataclass
class GenerationAttempt:
    """Single generation attempt with score"""
    version: int
    text: str
    score: ScoringResult


class MultiPassGenerator:
    """Generates multiple chapter versions and selects best"""

    def __init__(self, config_path="config/core_rules.yaml", attempts=5):
        """
        Initialize multi-pass generator

        Args:
            config_path: Path to core rules configuration
            attempts: Number of versions to generate (default: 5)
        """
        self.config_path = Path(config_path)
        self.attempts = attempts
        self.scorer = MultiDimensionalScorer()

    def generate_chapter(
        self,
        source_file: Path,
        outline: str,
        chapter_num: int,
        output_path: Optional[Path] = None,
        provider: str = "anthropic",
        verbose: bool = True
    ) -> Tuple[str, ScoringResult]:
        """
        Generate multiple chapter versions and return the best

        Args:
            source_file: Path to source material file
            outline: Chapter outline/prompt
            chapter_num: Chapter number
            output_path: Where to save best version (optional)
            provider: AI provider to use (anthropic, openai, etc.)
            verbose: Print progress information

        Returns:
            Tuple of (best_chapter_text, score_result)
        """

        if verbose:
            print(f"\nGenerating {self.attempts} versions of Chapter {chapter_num}...")
            print("="*60)

        attempts: List[GenerationAttempt] = []

        for version in range(1, self.attempts + 1):
            if verbose:
                print(f"\nVersion {version}/{self.attempts}:")
                print("-" * 40)

            # Generate this version
            chapter_text = self._generate_single_version(
                source_file,
                outline,
                chapter_num,
                version,
                provider,
                verbose
            )

            # Score it
            score = self.scorer.score(chapter_text)

            if verbose:
                print(f"  Score: {score.total:.1f}/10")
                print(f"    Emotional Impact: {score.scores['emotional_impact']:.1f}")
                print(f"    Voice: {score.scores['voice_distinctiveness']:.1f}")

            attempts.append(GenerationAttempt(
                version=version,
                text=chapter_text,
                score=score
            ))

        # Select best version
        best = max(attempts, key=lambda a: a.score.total)

        if verbose:
            print("\n" + "="*60)
            print(f"BEST: Version {best.version} - Score: {best.score.total:.1f}/10")
            print("="*60)

            # Show all scores for comparison
            print("\nAll versions:")
            for attempt in sorted(attempts, key=lambda a: a.score.total, reverse=True):
                marker = "★" if attempt.version == best.version else " "
                print(f"{marker} v{attempt.version}: {attempt.score.total:.1f}/10")

        # Save best version if output path provided
        if output_path:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, 'w') as f:
                f.write(best.text)

            if verbose:
                print(f"\n✓ Best version saved to {output_path}")

        return best.text, best.score

    def _generate_single_version(
        self,
        source_file: Path,
        outline: str,
        chapter_num: int,
        version: int,
        provider: str,
        verbose: bool
    ) -> str:
        """
        Generate a single chapter version

        Uses the existing chapter generation infrastructure but with
        temperature/randomness to produce different versions
        """

        # Build prompt
        prompt = self._build_generation_prompt(outline, chapter_num, version)

        # Call AI provider
        # For now, use a simple API call - in production this would integrate
        # with the full orchestrator's generation system

        if provider == "anthropic":
            chapter_text = self._call_anthropic(source_file, prompt, verbose)
        elif provider == "openai":
            chapter_text = self._call_openai(source_file, prompt, verbose)
        else:
            raise ValueError(f"Unsupported provider: {provider}")

        return chapter_text

    def _build_generation_prompt(self, outline: str, chapter_num: int, version: int) -> str:
        """Build the generation prompt for this version"""

        # Add slight variation prompts for each version to encourage diversity
        variation_prompts = [
            "",  # v1: baseline
            "\n\nFocus on physical sensations and visceral details.",
            "\n\nEmphasize character voice and distinctive language patterns.",
            "\n\nLean into emotional specificity and grounded moments.",
            "\n\nExperiment with sentence rhythm variety and fragments.",
            "\n\nPrioritize showing over telling, trust reader inference.",
            "\n\nGo deeper on 1-2 obsessive details (hands, sensation, etc.).",
        ]

        variation = variation_prompts[version % len(variation_prompts)]

        return f"""{outline}{variation}

Remember:
- Show don't tell
- Specific over generic emotions
- Let themes emerge through action
- Sentence rhythm variety
- Trust the reader"""

    def _call_anthropic(self, source_file: Path, prompt: str, verbose: bool) -> str:
        """Call Anthropic API to generate chapter"""

        # This is a simplified version - in production would use the full
        # orchestrator's generation logic with continuity tracking, etc.

        # Read source material
        if source_file.exists():
            with open(source_file, 'r') as f:
                source_content = f.read()[:2000]  # Truncate for API limits
        else:
            source_content = ""

        # For now, return placeholder
        # TODO: Integrate with actual API call
        placeholder = f"""# Generated Chapter

{prompt}

[This would be actual generated content from Anthropic API]

The chapter would be generated based on the prompt above, with the source
material context provided. Multiple versions would have natural variation
due to the LLM's inherent randomness.
"""

        return placeholder

    def _call_openai(self, source_file: Path, prompt: str, verbose: bool) -> str:
        """Call OpenAI API to generate chapter"""

        # Similar to Anthropic but with OpenAI
        placeholder = f"""# Generated Chapter (OpenAI)

{prompt}

[OpenAI generated content would go here]
"""

        return placeholder


def main():
    """Test multi-pass generator"""
    import argparse

    parser = argparse.ArgumentParser(description="Multi-pass chapter generator")
    parser.add_argument("source", type=Path, help="Source material file")
    parser.add_argument("outline", type=str, help="Chapter outline/prompt")
    parser.add_argument("chapter_num", type=int, help="Chapter number")
    parser.add_argument("--output", "-o", type=Path, help="Output file for best version")
    parser.add_argument("--attempts", "-n", type=int, default=5, help="Number of versions to generate")
    parser.add_argument("--provider", "-p", type=str, default="anthropic", choices=["anthropic", "openai"])
    parser.add_argument("--quiet", "-q", action="store_true", help="Suppress progress output")

    args = parser.parse_args()

    generator = MultiPassGenerator(attempts=args.attempts)

    best_text, best_score = generator.generate_chapter(
        source_file=args.source,
        outline=args.outline,
        chapter_num=args.chapter_num,
        output_path=args.output,
        provider=args.provider,
        verbose=not args.quiet
    )

    print(f"\nFinal score: {best_score.total:.1f}/10")
    print(f"Pass: {'Yes' if best_score.passed else 'No'}")


if __name__ == "__main__":
    main()
