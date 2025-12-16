"""
Enhanced Detail Density Analyzer for Book Factory
Implements first-pass excellence improvements from IMPROVEMENT_PLAN.md
"""

import re
import json
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple, Set
from dataclasses import dataclass, asdict
from collections import Counter
from enum import Enum

logger = logging.getLogger(__name__)


class DetailType(Enum):
    """Types of details to track."""
    SENSORY = "sensory"  # sight, sound, smell, taste, touch
    PHYSICAL = "physical"  # body language, physical reactions
    ENVIRONMENTAL = "environmental"  # weather, lighting, atmosphere
    TEMPORAL = "temporal"  # time references, pacing
    EMOTIONAL = "emotional"  # internal feelings, reactions
    OBSESSIVE = "obsessive"  # microscopic, counting, measuring
    MATERIAL = "material"  # textures, materials, objects
    SPATIAL = "spatial"  # distances, sizes, positions


@dataclass
class DetailMetrics:
    """Metrics for detail analysis."""
    total_details: int
    details_per_1000_words: float
    detail_types: Dict[DetailType, int]
    sensory_coverage: Dict[str, int]  # sight, sound, smell, taste, touch
    obsessive_details: List[str]
    weak_sections: List[Tuple[int, int]]  # (start_word, end_word) with low detail
    recurring_motifs: Dict[str, int]
    character_tics: Dict[str, List[str]]
    detail_quality_score: float  # 0-100
    recommendations: List[str]


class EnhancedDetailAnalyzer:
    """
    Advanced detail analysis for first-pass excellence.
    Features:
    - Obsessive detail counting (hands, temperature, measurements)
    - Sensory anchor tracking
    - Recurring motif detection
    - Character tic identification
    - Weak section flagging
    - Auto-improvement suggestions
    """

    # Obsessive detail patterns
    OBSESSIVE_PATTERNS = {
        'counting': [
            r'\b(one|two|three|four|five|six|seven|eight|nine|ten|\d+)\s+\w+',
            r'\b(first|second|third|fourth|fifth)\s+\w+',
            r'\b(counted|counting|number\w*)\b',
            r'\b(exactly|precisely|specifically)\s+\d+',
        ],
        'measuring': [
            r'\b\d+\s*(feet|inches|meters|yards|centimeters|millimeters)\b',
            r'\b(distance|length|width|height|depth)\s+\w+\s+\d+',
            r'\b(measured|measuring|measurement)\b',
            r'\b\d+\s*(degrees|percent|minutes|seconds)\b',
        ],
        'temperature': [
            r'\b(cold|warm|hot|freezing|burning|cool|chilly|frigid|scorching)\b',
            r'\b\d+\s*degrees?\b',
            r'\b(temperature|thermal|heat|warmth|coolness)\b',
            r'\b(shiver\w*|sweat\w*|goosebumps|flush\w*)\b',
        ],
        'hands': [
            r'\b(finger\w*|thumb\w*|palm\w*|knuckle\w*|nail\w*|wrist\w*)\b',
            r'\b(grip\w*|grasp\w*|clutch\w*|hold\w*|touch\w*)\b',
            r'\b(left|right)\s+hand\b',
            r'\b(fist\w*|clench\w*|squeeze\w*)\b',
        ],
        'texture': [
            r'\b(rough|smooth|soft|hard|silky|coarse|grainy|slippery)\b',
            r'\b(texture\w*|surface|feel|felt like)\b',
            r'\b(velvet|silk|cotton|leather|metal|wood|glass)\b',
        ],
        'micro_movements': [
            r'\b(twitch\w*|trembl\w*|quiver\w*|shudder\w*|flinch\w*)\b',
            r'\b(blink\w*|squint\w*|narrow\w*|widen\w*)\s+\w*eyes?\b',
            r'\b(jaw\s+(clench\w*|tighten\w*|work\w*))\b',
            r'\b(nostril\w*|eyebrow\w*|lip\w*|muscle\w*)\s+(twitch\w*|move\w*)\b',
        ]
    }

    # Sensory detail patterns
    SENSORY_PATTERNS = {
        'sight': [
            r'\b(saw|looked|gazed|stared|glimpsed|spotted|noticed|observed)\b',
            r'\b(color\w*|bright|dark|shadow\w*|light\w*|glow\w*)\b',
            r'\b(red|blue|green|yellow|black|white|gray|brown|purple|orange)\b',
        ],
        'sound': [
            r'\b(heard|listened|sounded|echoed|whispered|shouted|screamed)\b',
            r'\b(quiet|loud|silent|noise|bang|crash|thud|click|buzz|hum)\b',
            r'\b(voice|tone|pitch|volume|rhythm|melody)\b',
        ],
        'smell': [
            r'\b(smelled|scent|odor|aroma|fragrance|stench|reek|whiff)\b',
            r'\b(sweet|sour|bitter|acrid|musty|fresh|stale)\b',
            r'\b(perfume|cologne|smoke|coffee|food|flowers)\b',
        ],
        'taste': [
            r'\b(tasted|flavor|savor|tongue|palate|bitter|sweet|sour|salty)\b',
            r'\b(delicious|disgusting|bland|spicy|tangy)\b',
        ],
        'touch': [
            r'\b(felt|touched|pressed|rubbed|stroked|caressed|brushed)\b',
            r'\b(pressure|weight|heavy|light|firm|gentle)\b',
            r'\b(wet|dry|sticky|slippery|rough|smooth)\b',
        ]
    }

    # Genre-specific detail requirements
    GENRE_REQUIREMENTS = {
        'romance': {
            'min_details_per_1000': 5.0,
            'required_types': [DetailType.PHYSICAL, DetailType.EMOTIONAL, DetailType.SENSORY],
            'focus_areas': ['touch', 'hands', 'temperature', 'micro_movements']
        },
        'thriller': {
            'min_details_per_1000': 4.0,
            'required_types': [DetailType.ENVIRONMENTAL, DetailType.TEMPORAL, DetailType.SPATIAL],
            'focus_areas': ['counting', 'measuring', 'spatial', 'sound']
        },
        'fantasy': {
            'min_details_per_1000': 4.5,
            'required_types': [DetailType.MATERIAL, DetailType.SENSORY, DetailType.ENVIRONMENTAL],
            'focus_areas': ['texture', 'sight', 'smell', 'material']
        },
        'mystery': {
            'min_details_per_1000': 4.0,
            'required_types': [DetailType.OBSESSIVE, DetailType.SPATIAL, DetailType.TEMPORAL],
            'focus_areas': ['counting', 'measuring', 'micro_movements', 'sight']
        },
        'sci-fi': {
            'min_details_per_1000': 4.5,
            'required_types': [DetailType.MATERIAL, DetailType.SPATIAL, DetailType.SENSORY],
            'focus_areas': ['texture', 'temperature', 'measuring', 'sight']
        }
    }

    def __init__(self, genre: str = "general"):
        """
        Initialize the detail analyzer.

        Args:
            genre: Book genre for specific requirements
        """
        self.genre = genre.lower()
        self.requirements = self.GENRE_REQUIREMENTS.get(
            self.genre,
            {
                'min_details_per_1000': 3.0,
                'required_types': [DetailType.SENSORY, DetailType.PHYSICAL],
                'focus_areas': ['sensory', 'physical']
            }
        )

    def analyze(self, text: str) -> DetailMetrics:
        """
        Analyze detail density and quality.

        Args:
            text: Chapter or book text

        Returns:
            DetailMetrics with analysis results
        """
        word_count = len(text.split())
        if word_count == 0:
            return DetailMetrics(
                total_details=0,
                details_per_1000_words=0,
                detail_types={},
                sensory_coverage={},
                obsessive_details=[],
                weak_sections=[],
                recurring_motifs={},
                character_tics={},
                detail_quality_score=0,
                recommendations=["Text is empty"]
            )

        # Count different types of details
        detail_types = self._count_detail_types(text)

        # Count obsessive details
        obsessive_details = self._extract_obsessive_details(text)

        # Analyze sensory coverage
        sensory_coverage = self._analyze_sensory_coverage(text)

        # Find weak sections
        weak_sections = self._find_weak_sections(text)

        # Detect recurring motifs
        recurring_motifs = self._detect_recurring_motifs(text)

        # Identify character tics
        character_tics = self._identify_character_tics(text)

        # Calculate total details
        total_details = sum(detail_types.values())
        details_per_1000 = (total_details / word_count) * 1000 if word_count > 0 else 0

        # Calculate quality score
        quality_score = self._calculate_quality_score(
            details_per_1000,
            detail_types,
            sensory_coverage,
            len(obsessive_details),
            len(weak_sections)
        )

        # Generate recommendations
        recommendations = self._generate_recommendations(
            details_per_1000,
            detail_types,
            sensory_coverage,
            weak_sections
        )

        return DetailMetrics(
            total_details=total_details,
            details_per_1000_words=details_per_1000,
            detail_types=detail_types,
            sensory_coverage=sensory_coverage,
            obsessive_details=obsessive_details[:20],  # Top 20
            weak_sections=weak_sections,
            recurring_motifs=recurring_motifs,
            character_tics=character_tics,
            detail_quality_score=quality_score,
            recommendations=recommendations
        )

    def enhance_text(self, text: str, metrics: DetailMetrics) -> str:
        """
        Auto-enhance text with suggested details.

        Args:
            text: Original text
            metrics: Analysis metrics

        Returns:
            Enhanced text with injected details
        """
        enhanced = text

        # Inject details in weak sections
        for start, end in metrics.weak_sections[:3]:  # Fix top 3 weak sections
            section = self._extract_section(text, start, end)
            enhanced_section = self._inject_details(section)
            enhanced = enhanced.replace(section, enhanced_section, 1)

        return enhanced

    def _count_detail_types(self, text: str) -> Dict[DetailType, int]:
        """Count different types of details."""
        counts = {}

        # Count obsessive details
        obsessive_count = 0
        for category, patterns in self.OBSESSIVE_PATTERNS.items():
            for pattern in patterns:
                obsessive_count += len(re.findall(pattern, text, re.IGNORECASE))
        counts[DetailType.OBSESSIVE] = obsessive_count

        # Count sensory details
        sensory_count = 0
        for sense, patterns in self.SENSORY_PATTERNS.items():
            for pattern in patterns:
                sensory_count += len(re.findall(pattern, text, re.IGNORECASE))
        counts[DetailType.SENSORY] = sensory_count

        # Count physical details
        physical_patterns = [
            r'\b(gesture\w*|motion\w*|movement|posture|stance)\b',
            r'\b(lean\w*|bend\w*|stretch\w*|reach\w*|turn\w*)\b',
            r'\b(nod\w*|shake\w*|shrug\w*|wave\w*|point\w*)\b',
        ]
        physical_count = 0
        for pattern in physical_patterns:
            physical_count += len(re.findall(pattern, text, re.IGNORECASE))
        counts[DetailType.PHYSICAL] = physical_count

        # Count environmental details
        environmental_patterns = [
            r'\b(weather|rain|sun|wind|cloud|storm|snow)\b',
            r'\b(room|wall|door|window|floor|ceiling)\b',
            r'\b(tree|grass|sky|ground|earth|water)\b',
        ]
        environmental_count = 0
        for pattern in environmental_patterns:
            environmental_count += len(re.findall(pattern, text, re.IGNORECASE))
        counts[DetailType.ENVIRONMENTAL] = environmental_count

        # Count temporal details
        temporal_patterns = [
            r'\b(second|minute|hour|day|week|month|year)\b',
            r'\b(morning|afternoon|evening|night|dawn|dusk)\b',
            r'\b(before|after|during|while|then|now|later)\b',
        ]
        temporal_count = 0
        for pattern in temporal_patterns:
            temporal_count += len(re.findall(pattern, text, re.IGNORECASE))
        counts[DetailType.TEMPORAL] = temporal_count

        # Count emotional details
        emotional_patterns = [
            r'\b(feel|felt|feeling|emotion\w*)\b',
            r'\b(happy|sad|angry|afraid|excited|nervous)\b',
            r'\b(love\w*|hate\w*|fear\w*|joy\w*|sorrow\w*)\b',
        ]
        emotional_count = 0
        for pattern in emotional_patterns:
            emotional_count += len(re.findall(pattern, text, re.IGNORECASE))
        counts[DetailType.EMOTIONAL] = emotional_count

        # Count material details
        material_patterns = [
            r'\b(metal|wood|plastic|fabric|stone|glass|paper)\b',
            r'\b(steel|iron|gold|silver|copper|brass)\b',
            r'\b(concrete|brick|marble|granite)\b',
        ]
        material_count = 0
        for pattern in material_patterns:
            material_count += len(re.findall(pattern, text, re.IGNORECASE))
        counts[DetailType.MATERIAL] = material_count

        # Count spatial details
        spatial_patterns = [
            r'\b(near|far|close|distant|next to|beside|behind|in front)\b',
            r'\b(left|right|up|down|above|below|between)\b',
            r'\b(inside|outside|within|beyond|across)\b',
        ]
        spatial_count = 0
        for pattern in spatial_patterns:
            spatial_count += len(re.findall(pattern, text, re.IGNORECASE))
        counts[DetailType.SPATIAL] = spatial_count

        return counts

    def _extract_obsessive_details(self, text: str) -> List[str]:
        """Extract obsessive detail examples."""
        obsessive_details = []

        for category, patterns in self.OBSESSIVE_PATTERNS.items():
            for pattern in patterns:
                matches = re.finditer(pattern, text, re.IGNORECASE)
                for match in matches:
                    # Get context around match (30 chars before and after)
                    start = max(0, match.start() - 30)
                    end = min(len(text), match.end() + 30)
                    context = text[start:end].strip()

                    # Clean up context
                    if start > 0:
                        context = "..." + context
                    if end < len(text):
                        context = context + "..."

                    obsessive_details.append(f"[{category}] {context}")

        return obsessive_details

    def _analyze_sensory_coverage(self, text: str) -> Dict[str, int]:
        """Analyze coverage of different senses."""
        coverage = {}

        for sense, patterns in self.SENSORY_PATTERNS.items():
            count = 0
            for pattern in patterns:
                count += len(re.findall(pattern, text, re.IGNORECASE))
            coverage[sense] = count

        return coverage

    def _find_weak_sections(self, text: str, section_size: int = 500) -> List[Tuple[int, int]]:
        """Find sections with low detail density."""
        words = text.split()
        weak_sections = []

        # Analyze in chunks
        for i in range(0, len(words), section_size // 2):  # Overlap by half
            section = ' '.join(words[i:i + section_size])
            if not section:
                continue

            # Count details in section
            detail_count = 0
            for patterns in self.OBSESSIVE_PATTERNS.values():
                for pattern in patterns:
                    detail_count += len(re.findall(pattern, section, re.IGNORECASE))

            for patterns in self.SENSORY_PATTERNS.values():
                for pattern in patterns:
                    detail_count += len(re.findall(pattern, section, re.IGNORECASE))

            # Calculate density
            section_words = len(section.split())
            density = (detail_count / section_words) * 1000 if section_words > 0 else 0

            # Flag if below threshold
            if density < self.requirements['min_details_per_1000'] * 0.5:  # 50% of target
                weak_sections.append((i, min(i + section_size, len(words))))

        return weak_sections[:5]  # Return top 5 weak sections

    def _detect_recurring_motifs(self, text: str) -> Dict[str, int]:
        """Detect recurring motifs and patterns."""
        motifs = {}

        # Look for repeated phrases (3+ words)
        words = text.lower().split()
        for n in [3, 4, 5]:  # Phrase lengths
            for i in range(len(words) - n + 1):
                phrase = ' '.join(words[i:i + n])

                # Skip common phrases
                if any(common in phrase for common in
                      ['he said', 'she said', 'it was', 'there was', 'in the', 'of the']):
                    continue

                # Count occurrences
                count = text.lower().count(phrase)
                if count >= 3:  # Appears 3+ times
                    motifs[phrase] = count

        # Sort by frequency
        return dict(sorted(motifs.items(), key=lambda x: x[1], reverse=True)[:10])

    def _identify_character_tics(self, text: str) -> Dict[str, List[str]]:
        """Identify character-specific tics and patterns."""
        tics = {}

        # Find character names (simplified - looks for capitalized words)
        potential_names = re.findall(r'\b[A-Z][a-z]+\b', text)
        name_counts = Counter(potential_names)

        # Get top 5 most frequent names (likely characters)
        character_names = [name for name, count in name_counts.most_common(5) if count > 3]

        for name in character_names:
            character_tics = []

            # Find sentences mentioning this character
            sentences = re.findall(r'[^.!?]*\b' + name + r'\b[^.!?]*[.!?]', text)

            for sentence in sentences[:20]:  # Analyze first 20 mentions
                # Look for physical tics
                for pattern in self.OBSESSIVE_PATTERNS['micro_movements']:
                    if re.search(pattern, sentence, re.IGNORECASE):
                        tic_match = re.search(pattern, sentence, re.IGNORECASE)
                        if tic_match:
                            character_tics.append(tic_match.group())

                # Look for hand movements
                for pattern in self.OBSESSIVE_PATTERNS['hands']:
                    if re.search(pattern, sentence, re.IGNORECASE):
                        hand_match = re.search(pattern, sentence, re.IGNORECASE)
                        if hand_match:
                            character_tics.append(hand_match.group())

            if character_tics:
                # Get unique tics
                tics[name] = list(set(character_tics))[:5]

        return tics

    def _calculate_quality_score(
        self,
        details_per_1000: float,
        detail_types: Dict[DetailType, int],
        sensory_coverage: Dict[str, int],
        obsessive_count: int,
        weak_section_count: int
    ) -> float:
        """Calculate overall detail quality score."""
        score = 0.0

        # Density score (40 points)
        target_density = self.requirements['min_details_per_1000']
        if details_per_1000 >= target_density:
            score += 40
        else:
            score += 40 * (details_per_1000 / target_density)

        # Type coverage score (20 points)
        required_types = self.requirements['required_types']
        covered_types = sum(1 for dt in required_types if detail_types.get(dt, 0) > 0)
        score += 20 * (covered_types / len(required_types)) if required_types else 20

        # Sensory coverage score (15 points)
        senses_covered = sum(1 for count in sensory_coverage.values() if count > 0)
        score += 15 * (senses_covered / 5)  # 5 senses total

        # Obsessive detail bonus (15 points)
        if obsessive_count >= 10:
            score += 15
        else:
            score += 15 * (obsessive_count / 10)

        # Weak section penalty (10 points)
        if weak_section_count == 0:
            score += 10
        elif weak_section_count <= 2:
            score += 5
        # else no points

        return min(100, score)

    def _generate_recommendations(
        self,
        details_per_1000: float,
        detail_types: Dict[DetailType, int],
        sensory_coverage: Dict[str, int],
        weak_sections: List[Tuple[int, int]]
    ) -> List[str]:
        """Generate specific recommendations for improvement."""
        recommendations = []

        # Density recommendations
        target_density = self.requirements['min_details_per_1000']
        if details_per_1000 < target_density:
            deficit = target_density - details_per_1000
            recommendations.append(
                f"Increase detail density by {deficit:.1f} details per 1000 words"
            )

        # Type coverage recommendations
        for detail_type in self.requirements['required_types']:
            if detail_types.get(detail_type, 0) < 5:
                recommendations.append(
                    f"Add more {detail_type.value} details (currently: {detail_types.get(detail_type, 0)})"
                )

        # Sensory recommendations
        for sense in ['sight', 'sound', 'smell', 'taste', 'touch']:
            if sensory_coverage.get(sense, 0) < 2:
                recommendations.append(f"Include more {sense} descriptions")

        # Focus area recommendations
        for focus in self.requirements.get('focus_areas', []):
            recommendations.append(f"Emphasize {focus} details for {self.genre} genre")

        # Weak section recommendations
        if weak_sections:
            recommendations.append(
                f"Strengthen {len(weak_sections)} weak sections with low detail density"
            )

        # Specific suggestions by genre
        if self.genre == 'romance':
            recommendations.append("Add more hand descriptions and micro-movements during intimate scenes")
            recommendations.append("Include temperature and texture details for emotional moments")
        elif self.genre == 'thriller':
            recommendations.append("Add precise measurements and time references for tension")
            recommendations.append("Include more spatial details during action sequences")
        elif self.genre == 'fantasy':
            recommendations.append("Describe material properties of magical objects")
            recommendations.append("Add more sensory details for worldbuilding")

        return recommendations[:7]  # Top 7 recommendations

    def _extract_section(self, text: str, start_word: int, end_word: int) -> str:
        """Extract a section of text by word indices."""
        words = text.split()
        return ' '.join(words[start_word:end_word])

    def _inject_details(self, section: str) -> str:
        """Inject appropriate details into a section."""
        # This is a placeholder for actual detail injection logic
        # In practice, this would use context-aware generation

        # Simple example: Add sensory details after periods
        enhanced = section

        # Add a temperature detail
        if 'walked' in section.lower():
            enhanced = enhanced.replace('walked', 'walked through the cool air', 1)

        # Add a texture detail
        if 'touched' in section.lower():
            enhanced = enhanced.replace('touched', 'touched the rough surface', 1)

        # Add a sound detail
        if 'room' in section.lower():
            enhanced = enhanced.replace('room', 'quiet room', 1)

        return enhanced

    def generate_detail_report(
        self,
        metrics: DetailMetrics,
        output_path: Optional[Path] = None
    ) -> str:
        """
        Generate detailed analysis report.

        Args:
            metrics: Analysis metrics
            output_path: Optional path to save report

        Returns:
            Report text
        """
        report_lines = [
            "=" * 60,
            "ENHANCED DETAIL ANALYSIS REPORT",
            "=" * 60,
            "",
            f"Genre: {self.genre.title()}",
            f"Target Density: {self.requirements['min_details_per_1000']:.1f} details/1000 words",
            "",
            "METRICS",
            "-" * 30,
            f"Total Details: {metrics.total_details}",
            f"Details per 1000 words: {metrics.details_per_1000_words:.2f}",
            f"Quality Score: {metrics.detail_quality_score:.1f}/100",
            "",
            "DETAIL TYPE BREAKDOWN",
            "-" * 30,
        ]

        for detail_type, count in sorted(metrics.detail_types.items(), key=lambda x: x[1], reverse=True):
            report_lines.append(f"{detail_type.value.title()}: {count}")

        report_lines.extend([
            "",
            "SENSORY COVERAGE",
            "-" * 30,
        ])

        for sense, count in metrics.sensory_coverage.items():
            status = "✓" if count > 2 else "✗"
            report_lines.append(f"{status} {sense.title()}: {count}")

        report_lines.extend([
            "",
            "OBSESSIVE DETAILS (Top 5)",
            "-" * 30,
        ])

        for detail in metrics.obsessive_details[:5]:
            report_lines.append(f"• {detail}")

        if metrics.recurring_motifs:
            report_lines.extend([
                "",
                "RECURRING MOTIFS",
                "-" * 30,
            ])

            for motif, count in list(metrics.recurring_motifs.items())[:5]:
                report_lines.append(f"• \"{motif}\" ({count}x)")

        if metrics.character_tics:
            report_lines.extend([
                "",
                "CHARACTER TICS",
                "-" * 30,
            ])

            for character, tics in metrics.character_tics.items():
                report_lines.append(f"{character}: {', '.join(tics[:3])}")

        report_lines.extend([
            "",
            "RECOMMENDATIONS",
            "-" * 30,
        ])

        for i, rec in enumerate(metrics.recommendations, 1):
            report_lines.append(f"{i}. {rec}")

        report_lines.extend([
            "",
            "=" * 60,
        ])

        report = "\n".join(report_lines)

        if output_path:
            output_path.write_text(report, encoding='utf-8')
            logger.info(f"Report saved to {output_path}")

        return report