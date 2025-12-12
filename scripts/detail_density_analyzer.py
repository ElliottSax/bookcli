#!/usr/bin/env python3
"""
Detail Density Analyzer - Real Implementation
Part of Quality Improvement Plan P0

Counts obsessive details to enforce ultra_tier_prompts.yaml requirements:
- Target: 3+ obsessive details per 1000 words
- Includes: measurements, counting, temperatures, physical specs, sensory precision
"""

import re
from typing import Dict, List, Tuple
from dataclasses import dataclass
from collections import defaultdict


@dataclass
class DetailAnalysis:
    """Results of detail density analysis"""
    total_words: int
    measurements: int
    counting: int
    precision: int
    temperatures: int
    physical_specs: int
    sensory_details: int
    heart_rate_mentions: int
    breath_tracking: int
    distance_measurement: int

    total_details: int
    density_per_1k: float
    meets_target: bool
    examples: List[str]

    def to_dict(self) -> Dict:
        return {
            'total_words': self.total_words,
            'measurements': self.measurements,
            'counting': self.counting,
            'precision': self.precision,
            'temperatures': self.temperatures,
            'physical_specs': self.physical_specs,
            'sensory_details': self.sensory_details,
            'heart_rate_mentions': self.heart_rate_mentions,
            'breath_tracking': self.breath_tracking,
            'distance_measurement': self.distance_measurement,
            'total_details': self.total_details,
            'density_per_1k': round(self.density_per_1k, 2),
            'meets_target': self.meets_target,
            'target': 3.0,
            'examples': self.examples[:10]
        }


class DetailDensityAnalyzer:
    """
    Analyzes text for obsessive detail density.

    Based on ultra_tier_prompts.yaml requirements:
    - Physical measurements (exact heights, distances, temperatures)
    - Counting rituals (heartbeats, steps, objects, time intervals)
    - Sensory specificity (not "warm" but "36.4°C")
    - Microscopic focus (scars, calluses, exact features)
    """

    def __init__(self, target_density: float = 3.0):
        """
        Initialize analyzer.

        Args:
            target_density: Minimum obsessive details per 1000 words
        """
        self.target_density = target_density

        # Regex patterns for different detail types
        self.patterns = {
            'measurements': [
                r'\b\d+\.?\d*\s?(degrees?|cm|mm|m\b|meters?|kilometers?|miles?|feet|inches?)',
                r'\b\d+\.?\d*°[CF]',
                r'\b\d+\s?BPM\b',
                r'\b\d+\s?(seconds?|minutes?|hours?|days?|weeks?|months?|years?)',
                r'\b\d+\.?\d*\s?percent',
            ],
            'counting': [
                r'\bcounted?(?:\s+\w+){0,3}:\s*\d+',  # "counted heartbeats: 74"
                r'\b\d+\s+(?:heartbeats?|breaths?|seconds?|steps?|times?|pieces?|threads?|scars?|freckles?)',
                r'\bevery\s+\d+\s+(?:seconds?|minutes?|heartbeats?)',
                r'\b(?:one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|thirteen|fourteen|fifteen|sixteen|seventeen|eighteen|nineteen|twenty)\s+(?:heartbeats?|breaths?|seconds?|freckles?|scars?|threads?)',
            ],
            'precision': [
                r'\bexact(?:ly)?\s+\d+',
                r'\bprecise(?:ly)?\s+\d+',
                r'\bspecific(?:ally)?.*?\d+',
                r'\b\d+\s+(?:freckles?|scars?|threads?|lines?|marks?|beats?)',
            ],
            'temperatures': [
                r'\b\d+\.?\d*°[CF]\b',
                r'\b(?:temperature|temp)\s+(?:of\s+|at\s+|was\s+)?\d+',
                r'\b\d+\s+degrees?\s+(?:Celsius|Fahrenheit)',
            ],
            'physical_specs': [
                r'\b\d+\s?cm\b',
                r'\b\d+\s?mm\b',
                r'\b\d+\s?(?:feet|ft)\s+\d+\s?(?:inches|in)\b',
                r'\b\d+\'\d+"?\b',  # 6'2"
                r'\b\d+\.?\d*\s+(?:kilograms?|kg|pounds?|lbs?)\b',
            ],
            'sensory_details': [
                r'\b(?:tasted?|smelled?|felt)\s+(?:like|of)\s+\w+',
                r'\b(?:rough|smooth|soft|hard|warm|cold|hot|cool|sharp|dull)\s+(?:to|against)\s+(?:the|her|his)\s+(?:touch|skin|fingers?|palm)',
                r'\b(?:sounded?|smelled?|tasted?|felt)\s+like\s+',
            ],
            'heart_rate': [
                r'\b\d+\s+(?:beats?|BPM)\s+per\s+minute',
                r'\bheart(?:beat)?\s+(?:at\s+)?\d+',
                r'\bpulse\s+(?:at\s+|of\s+)?\d+',
                r'\b\d+\s+BPM\b',
            ],
            'breath_tracking': [
                r'\b\d+\s+breaths?\s+per\s+minute',
                r'\bbreath(?:ing)?\s+(?:at\s+)?\d+',
                r'\b(?:shallow|deep|rapid|slow|steady)\s+(?:breathing|breaths?)',
                r'\bbreath\s+(?:caught|stuttered|quickened|slowed|deepened)',
            ],
            'distance_measurement': [
                r'\b\d+\s+(?:centimeters?|cm|millimeters?|mm|meters?|m)\s+(?:between|away|apart|from)',
                r'\b(?:twenty|thirty|forty|fifty|sixty|seventy|eighty|ninety)\s+(?:centimeters?|cm)\b',
                r'\bdistance\s+(?:of\s+|was\s+)?\d+',
            ]
        }

    def count_obsessive_details(self, text: str) -> DetailAnalysis:
        """
        Count all obsessive detail types in text.

        Args:
            text: Chapter or section text

        Returns:
            DetailAnalysis with counts and density
        """
        counts = defaultdict(int)
        all_examples = []

        # Count each pattern type
        for category, pattern_list in self.patterns.items():
            for pattern in pattern_list:
                matches = list(re.finditer(pattern, text, re.IGNORECASE))
                counts[category] += len(matches)

                # Collect examples (up to 3 per pattern)
                for match in matches[:3]:
                    # Get surrounding context (20 words before/after)
                    start = max(0, match.start() - 100)
                    end = min(len(text), match.end() + 100)
                    context = text[start:end].replace('\n', ' ').strip()

                    all_examples.append({
                        'type': category,
                        'match': match.group(),
                        'context': context
                    })

        # Calculate totals
        word_count = len(text.split())
        total_details = sum(counts.values())
        density_per_1k = (total_details / word_count * 1000) if word_count > 0 else 0
        meets_target = density_per_1k >= self.target_density

        return DetailAnalysis(
            total_words=word_count,
            measurements=counts['measurements'],
            counting=counts['counting'],
            precision=counts['precision'],
            temperatures=counts['temperatures'],
            physical_specs=counts['physical_specs'],
            sensory_details=counts['sensory_details'],
            heart_rate_mentions=counts['heart_rate'],
            breath_tracking=counts['breath_tracking'],
            distance_measurement=counts['distance_measurement'],
            total_details=total_details,
            density_per_1k=density_per_1k,
            meets_target=meets_target,
            examples=[f"{ex['type']}: {ex['match']}" for ex in all_examples[:15]]
        )

    def get_score(self, text: str) -> float:
        """
        Get detail density score (0-100).

        Score calculation:
        - 3.0+ details/1k words = 100 points
        - Scales linearly from 0-3.0
        """
        analysis = self.count_obsessive_details(text)

        if analysis.density_per_1k >= self.target_density:
            return 100.0

        # Scale from 0 to 100 based on density
        score = (analysis.density_per_1k / self.target_density) * 100
        return min(100.0, max(0.0, score))

    def get_recommendations(self, text: str) -> List[str]:
        """
        Get specific recommendations for improving detail density.

        Args:
            text: Chapter text

        Returns:
            List of actionable recommendations
        """
        analysis = self.count_obsessive_details(text)
        recommendations = []

        if analysis.meets_target:
            return ["Detail density meets target. Excellent work!"]

        deficit = self.target_density - analysis.density_per_1k
        needed = int((deficit / 1000) * analysis.total_words)

        recommendations.append(
            f"Add approximately {needed} more obsessive details to reach target"
        )

        # Specific recommendations based on low categories
        if analysis.counting < 5:
            recommendations.append(
                "Add counting rituals: heartbeats, breaths, seconds, objects (target: 5+ per chapter)"
            )

        if analysis.heart_rate_mentions < 2:
            recommendations.append(
                "Include heart rate mentions in emotional scenes (target: 2+ per chapter)"
            )

        if analysis.breath_tracking < 2:
            recommendations.append(
                "Track breathing patterns during tension/intimacy (target: 2+ per chapter)"
            )

        if analysis.temperatures < 3:
            recommendations.append(
                "Add temperature measurements (body temp, environment, touch) (target: 3+ per chapter)"
            )

        if analysis.physical_specs < 5:
            recommendations.append(
                "Include exact physical measurements (distances, heights, sizes) (target: 5+ per chapter)"
            )

        return recommendations


if __name__ == "__main__":
    # Quick test
    analyzer = DetailDensityAnalyzer()
    test_text = """
    Elara counted Catherine's heartbeats. 74 per minute. 12 beats faster than this morning.
    Temperature: 35.8°C. Twenty centimeters between them.
    """
    result = analyzer.count_obsessive_details(test_text)
    print(f"Density: {result.density_per_1k:.2f}/1k words")
    print(f"Meets target: {result.meets_target}")
