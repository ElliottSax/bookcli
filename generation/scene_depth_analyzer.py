"""
Scene Depth Analyzer - Ensures each scene has sufficient depth
No fluff - analyzes substantive content and narrative complexity
"""

from dataclasses import dataclass, field
from typing import List, Dict, Tuple, Optional
from enum import Enum
import re


class DepthMetric(Enum):
    """Metrics for measuring scene depth"""
    CHARACTER_LAYERS = "character_layers"        # Internal/external character depth
    ACTION_GRANULARITY = "action_granularity"   # Level of action detail
    SENSORY_RICHNESS = "sensory_richness"       # Sensory detail depth
    TEMPORAL_PRECISION = "temporal_precision"    # Time-based specificity
    SPATIAL_COMPLEXITY = "spatial_complexity"    # Spatial relationships
    EMOTIONAL_NUANCE = "emotional_nuance"       # Emotional complexity
    CAUSAL_CHAINS = "causal_chains"            # Cause-effect relationships
    DIALOGUE_LAYERS = "dialogue_layers"         # Dialogue depth (text/subtext)


@dataclass
class SceneDepthAnalysis:
    """Analysis of scene depth and complexity"""
    scene_id: str
    word_count: int
    depth_scores: Dict[DepthMetric, float] = field(default_factory=dict)

    # Specific counts
    character_thoughts: int = 0
    physical_details: int = 0
    measurements: int = 0
    time_markers: int = 0
    sensory_details: int = 0
    emotional_beats: int = 0
    action_beats: int = 0
    dialogue_exchanges: int = 0

    # Depth indicators
    has_internal_monologue: bool = False
    has_physical_grounding: bool = False
    has_environmental_detail: bool = False
    has_micro_tensions: bool = False
    has_subtext: bool = False

    # Overall metrics
    depth_score: float = 0.0  # 0-100
    complexity_rating: str = ""  # "shallow", "moderate", "deep", "rich"
    expansion_potential: int = 0  # Estimated words that could be added


class SceneDepthAnalyzer:
    """
    Analyzes scene depth to ensure substantive content.
    Identifies areas for meaningful expansion without fluff.
    """

    # Minimum depth requirements
    MIN_REQUIREMENTS = {
        'character_thoughts': 3,    # At least 3 internal thoughts
        'measurements': 5,          # At least 5 precise measurements
        'sensory_details': 7,       # At least 7 sensory observations
        'action_beats': 5,          # At least 5 distinct actions
        'time_markers': 3,          # At least 3 time references
        'emotional_beats': 4,       # At least 4 emotional moments
    }

    # Patterns for detecting depth elements
    DEPTH_PATTERNS = {
        'measurements': [
            r'\d+\.?\d*\s*(°C|°F|degrees|celsius|fahrenheit)',
            r'\d+\.?\d*\s*(meters?|feet|inches|cm|mm|km)',
            r'\d+\.?\d*\s*(seconds?|minutes?|hours?|ms)',
            r'\d+\.?\d*\s*(BPM|beats per minute|heart rate)',
            r'\d+\.?\d*\s*(Hz|kHz|MHz|hertz|frequency)',
            r'\d+\.?\d*\s*(%|percent|percentage)',
            r'\d+\.?\d*\s*(kg|g|mg|pounds?|ounces?)',
            r'\d+\.?\d*\s*(watts?|joules?|newtons?)',
            r'\d+\.?\d*\s*(lux|lumens?|candela)',
            r'\d+\.?\d*\s*(Pa|hPa|bar|psi|pressure)',
        ],
        'time_markers': [
            r'\d{1,2}:\d{2}(?::\d{2})?(?:\s*[AP]M)?',
            r'(exactly|precisely|approximately)\s+\d+\.?\d*\s*(seconds?|minutes?|hours?)',
            r'(countdown|timer|clock).*\d+',
            r'T-minus\s+\d+',
            r'\d+\.?\d*\s*seconds?\s+(later|earlier|ago)',
        ],
        'sensory_words': [
            r'(saw|glimpsed|observed|noticed|perceived)',
            r'(heard|listened|sound|noise|whisper|echo)',
            r'(felt|touched|texture|smooth|rough|cold|warm|hot)',
            r'(smelled|scent|odor|aroma|fragrance|stench)',
            r'(tasted|flavor|sweet|sour|bitter|salty|umami)',
            r'(vibration|pressure|weight|resistance)',
        ],
        'emotional_indicators': [
            r'(heart rate|pulse|BPM)',
            r'(adrenaline|cortisol|endorphins|dopamine)',
            r'(pupils? dilated|constricted)',
            r'(breathing|breath|respiration)',
            r'(tension|relaxation|stiffened|loosened)',
            r'(sweat|perspiration|clammy|dry)',
        ],
        'internal_thought': [
            r'(realized|understood|calculated|assessed|evaluated)',
            r'(wondered|pondered|considered|contemplated)',
            r'(remembered|recalled|recollected)',
            r'(decided|chose|determined|resolved)',
            r'(feared|hoped|wished|dreaded)',
        ]
    }

    def analyze_scene(self, scene_text: str, scene_id: str = "scene") -> SceneDepthAnalysis:
        """Analyze the depth and complexity of a scene"""

        analysis = SceneDepthAnalysis(
            scene_id=scene_id,
            word_count=len(scene_text.split())
        )

        # Count specific elements
        analysis.measurements = self._count_measurements(scene_text)
        analysis.time_markers = self._count_time_markers(scene_text)
        analysis.sensory_details = self._count_sensory_details(scene_text)
        analysis.emotional_beats = self._count_emotional_beats(scene_text)
        analysis.character_thoughts = self._count_internal_thoughts(scene_text)
        analysis.action_beats = self._count_action_beats(scene_text)
        analysis.dialogue_exchanges = self._count_dialogue(scene_text)

        # Check for depth indicators
        analysis.has_internal_monologue = self._has_internal_monologue(scene_text)
        analysis.has_physical_grounding = self._has_physical_grounding(scene_text)
        analysis.has_environmental_detail = self._has_environmental_detail(scene_text)
        analysis.has_micro_tensions = self._has_micro_tensions(scene_text)
        analysis.has_subtext = self._has_subtext(scene_text)

        # Calculate depth scores for each metric
        analysis.depth_scores = self._calculate_depth_scores(analysis)

        # Calculate overall depth score
        analysis.depth_score = self._calculate_overall_depth(analysis)

        # Determine complexity rating
        analysis.complexity_rating = self._rate_complexity(analysis.depth_score)

        # Calculate expansion potential
        analysis.expansion_potential = self._estimate_expansion_potential(analysis)

        return analysis

    def _count_measurements(self, text: str) -> int:
        """Count precise measurements in text"""
        count = 0
        for pattern in self.DEPTH_PATTERNS['measurements']:
            matches = re.findall(pattern, text, re.IGNORECASE)
            count += len(matches)
        return count

    def _count_time_markers(self, text: str) -> int:
        """Count time references"""
        count = 0
        for pattern in self.DEPTH_PATTERNS['time_markers']:
            matches = re.findall(pattern, text, re.IGNORECASE)
            count += len(matches)
        return count

    def _count_sensory_details(self, text: str) -> int:
        """Count sensory descriptions"""
        count = 0
        for pattern in self.DEPTH_PATTERNS['sensory_words']:
            matches = re.findall(pattern, text, re.IGNORECASE)
            count += len(matches)
        return count

    def _count_emotional_beats(self, text: str) -> int:
        """Count emotional/physical response indicators"""
        count = 0
        for pattern in self.DEPTH_PATTERNS['emotional_indicators']:
            matches = re.findall(pattern, text, re.IGNORECASE)
            count += len(matches)
        return count

    def _count_internal_thoughts(self, text: str) -> int:
        """Count internal thought indicators"""
        count = 0
        for pattern in self.DEPTH_PATTERNS['internal_thought']:
            matches = re.findall(pattern, text, re.IGNORECASE)
            count += len(matches)
        return count

    def _count_action_beats(self, text: str) -> int:
        """Count distinct action beats"""
        # Look for action verbs in past tense
        action_verbs = r'\b(moved|stepped|turned|grabbed|pushed|pulled|jumped|ran|walked|struck|hit|dodged|blocked|threw|caught|lifted|dropped|opened|closed|activated|initiated)\b'
        matches = re.findall(action_verbs, text, re.IGNORECASE)
        return len(matches)

    def _count_dialogue(self, text: str) -> int:
        """Count dialogue exchanges"""
        # Count quotation pairs
        quotes = re.findall(r'"[^"]+?"', text)
        return len(quotes)

    def _has_internal_monologue(self, text: str) -> bool:
        """Check for internal monologue"""
        return self._count_internal_thoughts(text) >= 3

    def _has_physical_grounding(self, text: str) -> bool:
        """Check for physical grounding of emotions"""
        physical_patterns = [
            r'(heart|pulse|breathing|muscles?|shoulders?|jaw|fists?|hands?)',
            r'(tensed|relaxed|clenched|trembled|shook|stiffened)',
        ]
        for pattern in physical_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return True
        return False

    def _has_environmental_detail(self, text: str) -> bool:
        """Check for environmental descriptions"""
        env_patterns = [
            r'(temperature|humidity|pressure|lighting|shadows)',
            r'(walls?|ceiling|floor|corners?|doors?|windows?)',
            r'(sounds?|echoes?|vibrations?|hums?|buzzes?)',
        ]
        count = 0
        for pattern in env_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                count += 1
        return count >= 3

    def _has_micro_tensions(self, text: str) -> bool:
        """Check for small tension moments"""
        tension_patterns = [
            r'(pause|hesitation|silence|stillness)',
            r'(almost|nearly|barely|just)',
            r'(waiting|watching|listening|observing)',
        ]
        count = 0
        for pattern in tension_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                count += 1
        return count >= 2

    def _has_subtext(self, text: str) -> bool:
        """Check for subtext indicators"""
        subtext_patterns = [
            r'(but|however|although|despite|nevertheless)',
            r'(seemed|appeared|looked like|as if|as though)',
            r'(underneath|beneath|behind|beyond)',
        ]
        count = 0
        for pattern in subtext_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                count += 1
        return count >= 2

    def _calculate_depth_scores(self, analysis: SceneDepthAnalysis) -> Dict[DepthMetric, float]:
        """Calculate individual depth scores"""
        scores = {}

        # Character layers (internal + external)
        scores[DepthMetric.CHARACTER_LAYERS] = min(100, (
            (analysis.character_thoughts * 10) +
            (10 if analysis.has_internal_monologue else 0) +
            (10 if analysis.has_physical_grounding else 0)
        ))

        # Action granularity
        scores[DepthMetric.ACTION_GRANULARITY] = min(100, (
            analysis.action_beats * 15
        ))

        # Sensory richness
        scores[DepthMetric.SENSORY_RICHNESS] = min(100, (
            analysis.sensory_details * 10
        ))

        # Temporal precision
        scores[DepthMetric.TEMPORAL_PRECISION] = min(100, (
            analysis.time_markers * 20
        ))

        # Spatial complexity
        scores[DepthMetric.SPATIAL_COMPLEXITY] = min(100, (
            analysis.measurements * 8 +
            (20 if analysis.has_environmental_detail else 0)
        ))

        # Emotional nuance
        scores[DepthMetric.EMOTIONAL_NUANCE] = min(100, (
            analysis.emotional_beats * 15 +
            (10 if analysis.has_subtext else 0)
        ))

        # Causal chains
        scores[DepthMetric.CAUSAL_CHAINS] = min(100, (
            (20 if analysis.has_micro_tensions else 0) +
            (20 if "because" in str(analysis) else 0) +
            (20 if "therefore" in str(analysis) else 0)
        ))

        # Dialogue layers
        scores[DepthMetric.DIALOGUE_LAYERS] = min(100, (
            analysis.dialogue_exchanges * 10 +
            (20 if analysis.has_subtext else 0)
        ))

        return scores

    def _calculate_overall_depth(self, analysis: SceneDepthAnalysis) -> float:
        """Calculate overall depth score"""

        if not analysis.depth_scores:
            return 0.0

        # Weighted average of all depth scores
        weights = {
            DepthMetric.CHARACTER_LAYERS: 0.20,
            DepthMetric.ACTION_GRANULARITY: 0.15,
            DepthMetric.SENSORY_RICHNESS: 0.15,
            DepthMetric.TEMPORAL_PRECISION: 0.10,
            DepthMetric.SPATIAL_COMPLEXITY: 0.10,
            DepthMetric.EMOTIONAL_NUANCE: 0.15,
            DepthMetric.CAUSAL_CHAINS: 0.05,
            DepthMetric.DIALOGUE_LAYERS: 0.10,
        }

        total_score = 0.0
        for metric, weight in weights.items():
            total_score += analysis.depth_scores.get(metric, 0) * weight

        return min(100, total_score)

    def _rate_complexity(self, depth_score: float) -> str:
        """Rate scene complexity based on depth score"""
        if depth_score >= 80:
            return "rich"
        elif depth_score >= 60:
            return "deep"
        elif depth_score >= 40:
            return "moderate"
        else:
            return "shallow"

    def _estimate_expansion_potential(self, analysis: SceneDepthAnalysis) -> int:
        """Estimate how many words could be meaningfully added"""

        potential = 0

        # Check against minimum requirements
        if analysis.character_thoughts < self.MIN_REQUIREMENTS['character_thoughts']:
            potential += (self.MIN_REQUIREMENTS['character_thoughts'] - analysis.character_thoughts) * 30

        if analysis.measurements < self.MIN_REQUIREMENTS['measurements']:
            potential += (self.MIN_REQUIREMENTS['measurements'] - analysis.measurements) * 15

        if analysis.sensory_details < self.MIN_REQUIREMENTS['sensory_details']:
            potential += (self.MIN_REQUIREMENTS['sensory_details'] - analysis.sensory_details) * 20

        if analysis.action_beats < self.MIN_REQUIREMENTS['action_beats']:
            potential += (self.MIN_REQUIREMENTS['action_beats'] - analysis.action_beats) * 25

        if analysis.time_markers < self.MIN_REQUIREMENTS['time_markers']:
            potential += (self.MIN_REQUIREMENTS['time_markers'] - analysis.time_markers) * 10

        if analysis.emotional_beats < self.MIN_REQUIREMENTS['emotional_beats']:
            potential += (self.MIN_REQUIREMENTS['emotional_beats'] - analysis.emotional_beats) * 20

        # Add potential for missing depth indicators
        if not analysis.has_internal_monologue:
            potential += 100
        if not analysis.has_physical_grounding:
            potential += 80
        if not analysis.has_environmental_detail:
            potential += 60
        if not analysis.has_micro_tensions:
            potential += 40
        if not analysis.has_subtext:
            potential += 50

        return potential

    def recommend_expansions(self, analysis: SceneDepthAnalysis) -> List[str]:
        """Recommend specific expansions to increase depth"""

        recommendations = []

        # Check each depth metric
        for metric, score in analysis.depth_scores.items():
            if score < 60:  # Below threshold
                if metric == DepthMetric.CHARACTER_LAYERS:
                    recommendations.append(
                        "Add internal monologue: character calculations, assessments, memories"
                    )
                elif metric == DepthMetric.ACTION_GRANULARITY:
                    recommendations.append(
                        "Break actions into micro-beats with timing and measurements"
                    )
                elif metric == DepthMetric.SENSORY_RICHNESS:
                    recommendations.append(
                        "Layer in sensory data: frequencies, intensities, durations"
                    )
                elif metric == DepthMetric.TEMPORAL_PRECISION:
                    recommendations.append(
                        "Add precise time markers and countdowns"
                    )
                elif metric == DepthMetric.SPATIAL_COMPLEXITY:
                    recommendations.append(
                        "Include spatial measurements and environmental parameters"
                    )
                elif metric == DepthMetric.EMOTIONAL_NUANCE:
                    recommendations.append(
                        "Ground emotions physically: heart rate, temperature, hormones"
                    )
                elif metric == DepthMetric.CAUSAL_CHAINS:
                    recommendations.append(
                        "Show cause-effect relationships with probability calculations"
                    )
                elif metric == DepthMetric.DIALOGUE_LAYERS:
                    recommendations.append(
                        "Add subtext with vocal analysis and micro-expressions"
                    )

        # Check minimum requirements
        if analysis.measurements < self.MIN_REQUIREMENTS['measurements']:
            recommendations.append(
                f"Add {self.MIN_REQUIREMENTS['measurements'] - analysis.measurements} more precise measurements"
            )

        if analysis.sensory_details < self.MIN_REQUIREMENTS['sensory_details']:
            recommendations.append(
                f"Add {self.MIN_REQUIREMENTS['sensory_details'] - analysis.sensory_details} more sensory observations"
            )

        return recommendations