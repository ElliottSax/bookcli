#!/usr/bin/env python3
"""
Detail Density Analyzer - Measures obsessive detail density in fiction

Target: 3+ obsessive details per 1000 words

Obsessive details include:
- Physical measurements (exact heights, distances, temperatures)
- Counting rituals (heartbeats, steps, objects, time intervals)
- Sensory specificity (exact colors, precise sounds, specific textures)
- Repeated observations (character notices same detail multiple times)
- Microscopic focus (hands described in extreme detail)
"""

import re
from typing import Dict, List, Tuple
from dataclasses import dataclass


@dataclass
class DetailMatch:
    """A single obsessive detail found in text"""
    type: str
    text: str
    position: int
    context: str


class DetailDensityAnalyzer:
    """Analyzes fiction text for obsessive detail density"""

    def __init__(self):
        # Patterns for detecting obsessive details
        self.patterns = {
            'measurements': [
                # Temperature: 36.8°C, 98.6°F, thirty-six degrees
                r'\b\d+\.?\d*\s*°[CF]\b',
                r'\b\d+\.?\d*\s*degrees\b',
                r'\b\d+\.?\d*\s*celsius\b',
                r'\b\d+\.?\d*\s*fahrenheit\b',

                # Distance: 182cm, 6 feet, twenty meters
                r'\b\d+\.?\d*\s*(cm|centimeters?|mm|millimeters?|m|meters?)\b',
                r'\b\d+\.?\d*\s*(feet|foot|inches?|yards?|miles?)\b',

                # Weight: 2kg, 5 pounds
                r'\b\d+\.?\d*\s*(kg|kilograms?|g|grams?|lbs?|pounds?|ounces?)\b',

                # Time: 14 seconds, 3.5 minutes, 2 hours
                r'\b\d+\.?\d*\s*(seconds?|minutes?|hours?|days?|weeks?|months?|years?)\b',
            ],

            'counting': [
                # Heartbeats: 74 beats per minute, seventy-four BPM
                r'\b\d+\.?\d*\s*(beats?\s+per\s+minute|BPM|heartbeats?)\b',

                # Breath: 42 breaths per minute
                r'\b\d+\.?\d*\s*breaths?\s+per\s+minute\b',

                # Steps: seventeen steps, 30 steps
                r'\b\d+\.?\d*\s*steps?\b',

                # Objects counted: fourteen beams, 18 scars
                r'\b\d+\.?\d*\s+[a-z]+s\b',  # Generic counting

                # Explicit counting: "counted", "cataloged"
                r'\bcounted\b',
                r'\bcatalog(ed|ing)\b',
            ],

            'sensory_specific': [
                # Specific colors with modifiers: silver-gray, deep crimson
                r'\b(silver|golden|crimson|azure|jade|obsidian|ivory|ebony)[- ][a-z]+\b',

                # Texture specifics: rough-textured, silken-smooth
                r'\b(rough|smooth|silken|coarse|velvety|gritty)[- ][a-z]+\b',

                # Sound specifics: A440 pitch, perfect fourth
                r'\b[A-G]\d{3}\s*(pitch|note|tone)\b',
                r'\b(perfect|major|minor)\s+(second|third|fourth|fifth|sixth|seventh|octave)\b',

                # Taste/smell specifics with chemical names
                r'\b(ozone|copper|sulfur|petrichor|bergamot|sandalwood)\b',
            ],

            'micro_focus': [
                # Hands in detail: calluses, scars, knuckles, etc.
                r'\b(callus|calluses|scar|scars|knuckle|knuckles|palm|palms|finger|fingers|thumb|thumbs)\b',

                # Eyes in detail: iris, pupil, retina
                r'\b(iris|irises|pupil|pupils|retina|cornea)\b',

                # Physical details: veins, tendons, muscles
                r'\b(vein|veins|tendon|tendons|muscle|muscles|sinew)\b',
            ],

            'repeated_observation': [
                # Words that signal repeated noticing
                r'\bagain\b',
                r'\bstill\b',
                r'\balways\b',
                r'\bevery\s+time\b',
                r'\bonce\s+more\b',
                r'\bas\s+always\b',
            ]
        }

    def analyze(self, text: str, target_density: float = 3.0) -> Dict:
        """
        Analyze text for obsessive detail density

        Args:
            text: Text to analyze
            target_density: Target details per 1000 words (default: 3.0)

        Returns:
            Dictionary with analysis results
        """
        # Count words
        word_count = len(text.split())

        # Find all details
        details = self._find_details(text)

        # Calculate density
        density = (len(details) / word_count * 1000) if word_count > 0 else 0

        # Analyze by type
        detail_counts = {}
        for detail in details:
            detail_counts[detail.type] = detail_counts.get(detail.type, 0) + 1

        # Check if passes threshold
        passed = density >= target_density

        # Find weak sections (sections with low detail density)
        weak_sections = self._find_weak_sections(text, details, target_density)

        return {
            'passed': passed,
            'word_count': word_count,
            'total_details': len(details),
            'density': round(density, 2),
            'target_density': target_density,
            'deficit': max(0, int((target_density - density) * word_count / 1000)) if not passed else 0,
            'detail_counts': detail_counts,
            'details': details,
            'weak_sections': weak_sections,
            'suggestions': self._generate_suggestions(weak_sections) if not passed else []
        }

    def _find_details(self, text: str) -> List[DetailMatch]:
        """Find all obsessive details in text"""
        details = []

        for detail_type, patterns in self.patterns.items():
            for pattern in patterns:
                for match in re.finditer(pattern, text, re.IGNORECASE):
                    # Get context (50 chars before and after)
                    start = max(0, match.start() - 50)
                    end = min(len(text), match.end() + 50)
                    context = text[start:end].replace('\n', ' ')

                    details.append(DetailMatch(
                        type=detail_type,
                        text=match.group(),
                        position=match.start(),
                        context=context
                    ))

        # Sort by position
        details.sort(key=lambda d: d.position)

        # Deduplicate overlapping matches
        details = self._deduplicate(details)

        return details

    def _deduplicate(self, details: List[DetailMatch]) -> List[DetailMatch]:
        """Remove overlapping detail matches"""
        if not details:
            return []

        unique = [details[0]]

        for detail in details[1:]:
            # If this detail doesn't overlap with previous, keep it
            prev = unique[-1]
            if detail.position >= prev.position + len(prev.text):
                unique.append(detail)

        return unique

    def _find_weak_sections(
        self,
        text: str,
        details: List[DetailMatch],
        target_density: float
    ) -> List[Dict]:
        """
        Find sections of text with low detail density

        Divides text into ~500-word chunks and checks density
        """
        chunk_size = 500  # words per chunk
        words = text.split()
        weak_sections = []

        # Create chunks
        for i in range(0, len(words), chunk_size):
            chunk_words = words[i:i + chunk_size]
            chunk_text = ' '.join(chunk_words)
            chunk_start = len(' '.join(words[:i]))
            chunk_end = chunk_start + len(chunk_text)

            # Count details in this chunk
            chunk_details = [
                d for d in details
                if chunk_start <= d.position < chunk_end
            ]

            # Calculate chunk density
            chunk_word_count = len(chunk_words)
            chunk_density = (len(chunk_details) / chunk_word_count * 1000) if chunk_word_count > 0 else 0

            # If below target, it's a weak section
            if chunk_density < target_density:
                # Get first/last sentences for context
                sentences = chunk_text.split('.')
                preview = sentences[0][:100] + '...' if sentences else chunk_text[:100] + '...'

                weak_sections.append({
                    'start': chunk_start,
                    'end': chunk_end,
                    'word_count': chunk_word_count,
                    'detail_count': len(chunk_details),
                    'density': round(chunk_density, 2),
                    'deficit': int((target_density - chunk_density) * chunk_word_count / 1000),
                    'preview': preview
                })

        return weak_sections

    def _generate_suggestions(self, weak_sections: List[Dict]) -> List[str]:
        """Generate suggestions for improving weak sections"""
        suggestions = []

        for i, section in enumerate(weak_sections, 1):
            suggestions.append(
                f"Section {i} (words {section['start']}-{section['end']}): "
                f"Add {section['deficit']} obsessive details. "
                f"Current density: {section['density']}/1000 words. "
                f"Try: specific measurements, counting rituals, sensory details."
            )

        return suggestions

    def format_report(self, analysis: Dict) -> str:
        """Format analysis results as readable report"""
        lines = []

        lines.append("=" * 70)
        lines.append("DETAIL DENSITY ANALYSIS")
        lines.append("=" * 70)
        lines.append("")

        # Overall stats
        lines.append(f"Word count: {analysis['word_count']}")
        lines.append(f"Total obsessive details: {analysis['total_details']}")
        lines.append(f"Density: {analysis['density']} per 1000 words")
        lines.append(f"Target: {analysis['target_density']} per 1000 words")
        lines.append(f"Status: {'✓ PASS' if analysis['passed'] else '✗ FAIL'}")

        if not analysis['passed']:
            lines.append(f"Deficit: Need {analysis['deficit']} more details")

        lines.append("")

        # Detail breakdown by type
        lines.append("Detail types found:")
        for detail_type, count in sorted(analysis['detail_counts'].items(), key=lambda x: -x[1]):
            lines.append(f"  - {detail_type}: {count}")

        lines.append("")

        # Weak sections
        if analysis['weak_sections']:
            lines.append(f"Weak sections ({len(analysis['weak_sections'])} found):")
            for i, section in enumerate(analysis['weak_sections'], 1):
                lines.append(f"  {i}. Words {section['start']}-{section['end']}: "
                           f"density {section['density']}/1000 (need +{section['deficit']} details)")
                lines.append(f"     Preview: {section['preview']}")
            lines.append("")

        # Suggestions
        if analysis['suggestions']:
            lines.append("Suggestions:")
            for suggestion in analysis['suggestions']:
                lines.append(f"  - {suggestion}")

        return '\n'.join(lines)


def main():
    """Test the detail density analyzer"""

    # Test text with varying detail density
    test_high_density = """
    Elara counted Catherine's heartbeats. Seventy-four per minute. Twelve beats
    faster than this morning's sixty-two. Elevated but steady. Human normal range
    was sixty to one hundred. Catherine was healing.

    Her temperature had climbed too. Elara checked—hand to forehead, clinical,
    trying not to notice the way Catherine's eyes tracked the movement. 35.8°C.
    Up from yesterday's 35.2°C. Still below normal 36.8°C, but climbing. Point-six
    degrees in twenty-four hours.
    """

    test_low_density = """
    Catherine woke up feeling better. She looked at Elara and smiled. They had
    breakfast together, which was nice. The food tasted good. Afterward, they
    talked about their plans for the day. Catherine was happy to be free from
    the armor. Elara was glad that Catherine was improving.
    """

    analyzer = DetailDensityAnalyzer()

    print("TEST 1: High-density text (should pass)")
    print("-" * 70)
    analysis1 = analyzer.analyze(test_high_density, target_density=3.0)
    print(analyzer.format_report(analysis1))
    print("\n" * 2)

    print("TEST 2: Low-density text (should fail)")
    print("-" * 70)
    analysis2 = analyzer.analyze(test_low_density, target_density=3.0)
    print(analyzer.format_report(analysis2))


if __name__ == "__main__":
    main()
