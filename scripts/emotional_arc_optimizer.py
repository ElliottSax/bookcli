#!/usr/bin/env python3
"""
Emotional Arc Optimizer - Phase 6 Priority 2
Engineers optimal emotional journeys through narrative
"""

import numpy as np
import matplotlib.pyplot as plt
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, field
from collections import defaultdict
import json
from pathlib import Path
import nltk
from nltk.sentiment import SentimentIntensityAnalyzer
from scipy.interpolate import interp1d
from scipy.signal import savgol_filter
import warnings
warnings.filterwarnings('ignore')

# Download required NLTK data
try:
    nltk.download('vader_lexicon', quiet=True)
except:
    pass


@dataclass
class EmotionVector:
    """Multi-dimensional emotion representation"""
    chapter: int
    tension: float      # 0-10: Narrative tension/conflict
    joy: float         # 0-10: Happiness/positivity
    sadness: float     # 0-10: Sorrow/melancholy
    fear: float        # 0-10: Anxiety/dread
    surprise: float    # 0-10: Unexpected events
    anticipation: float # 0-10: Forward momentum
    trust: float       # 0-10: Safety/comfort
    disgust: float     # 0-10: Revulsion/rejection

    def magnitude(self) -> float:
        """Calculate overall emotional intensity"""
        emotions = [self.tension, self.joy, self.sadness, self.fear,
                   self.surprise, self.anticipation, self.trust, self.disgust]
        return np.linalg.norm(emotions)

    def dominant_emotion(self) -> str:
        """Return the strongest emotion"""
        emotions = {
            'tension': self.tension,
            'joy': self.joy,
            'sadness': self.sadness,
            'fear': self.fear,
            'surprise': self.surprise,
            'anticipation': self.anticipation,
            'trust': self.trust,
            'disgust': self.disgust
        }
        return max(emotions, key=emotions.get)


@dataclass
class EmotionalArc:
    """Complete emotional journey through narrative"""
    chapters: List[EmotionVector]
    arc_type: str  # 'man_in_hole', 'cinderella', 'tragedy', etc.
    key_moments: List[Tuple[int, str]]  # (chapter, description)
    overall_trajectory: str  # 'rising', 'falling', 'complex'
    catharsis_points: List[int]  # Chapters with emotional release
    tension_peaks: List[int]  # Chapters with maximum tension

    def get_trajectory(self) -> List[float]:
        """Get overall emotional trajectory"""
        return [ch.magnitude() for ch in self.chapters]

    def get_emotion_curve(self, emotion: str) -> List[float]:
        """Get trajectory for specific emotion"""
        return [getattr(ch, emotion) for ch in self.chapters]


@dataclass
class ArcOptimization:
    """Recommendations for emotional optimization"""
    chapter: int
    current_emotion: EmotionVector
    target_emotion: EmotionVector
    adjustments: List[str]
    priority: float  # 0-1, higher = more important
    expected_impact: float  # Predicted quality improvement


class EmotionalArcOptimizer:
    """Optimizes emotional journey for maximum reader engagement"""

    def __init__(self):
        """Initialize emotional analyzer"""
        self.sia = SentimentIntensityAnalyzer()

        # Ideal emotional arcs for different story types
        self.ideal_arcs = self._load_ideal_arcs()

        # Emotion lexicons
        self.emotion_lexicons = self._load_emotion_lexicons()

        # Pacing guidelines
        self.pacing_rules = self._load_pacing_rules()

    def _load_ideal_arcs(self) -> Dict[str, List[float]]:
        """Load ideal emotional trajectories for different story types"""
        # Normalized to 20 chapters, values 0-10
        return {
            'man_in_hole': [5, 5, 4, 3, 2, 2, 3, 4, 5, 6, 7, 7, 8, 8, 9, 9, 8, 8, 7, 7],
            'cinderella': [3, 3, 4, 5, 6, 7, 8, 8, 4, 3, 2, 3, 5, 7, 8, 9, 10, 9, 9, 8],
            'tragedy': [5, 6, 7, 7, 8, 8, 9, 9, 8, 7, 6, 5, 4, 3, 3, 2, 2, 1, 1, 1],
            'comedy': [5, 4, 3, 5, 4, 3, 5, 6, 4, 5, 7, 5, 6, 8, 7, 8, 9, 9, 9, 10],
            'hero_journey': [5, 4, 3, 4, 5, 6, 4, 3, 4, 5, 6, 7, 5, 6, 7, 8, 9, 9, 8, 7],
            'rags_to_riches': [2, 2, 3, 3, 4, 4, 5, 5, 6, 6, 7, 7, 8, 8, 9, 9, 10, 10, 9, 9],
            'rebirth': [5, 4, 3, 2, 1, 1, 2, 3, 4, 5, 6, 7, 8, 8, 9, 9, 10, 10, 9, 8],
            'voyage_return': [5, 6, 7, 8, 8, 7, 6, 5, 4, 3, 4, 5, 6, 7, 8, 8, 7, 6, 5, 5]
        }

    def _load_emotion_lexicons(self) -> Dict[str, List[str]]:
        """Load word lists for emotion detection"""
        return {
            'tension': ['conflict', 'struggle', 'fight', 'battle', 'confrontation', 'clash',
                       'tension', 'pressure', 'stress', 'strain', 'dispute', 'argument'],
            'joy': ['happy', 'joy', 'delight', 'pleasure', 'elated', 'cheerful', 'glad',
                   'smile', 'laugh', 'celebrate', 'wonderful', 'fantastic'],
            'sadness': ['sad', 'sorrow', 'grief', 'mourn', 'cry', 'tears', 'depressed',
                       'melancholy', 'despair', 'heartbreak', 'loss', 'lonely'],
            'fear': ['fear', 'afraid', 'scared', 'terrified', 'anxious', 'panic', 'dread',
                    'horror', 'nightmare', 'threat', 'danger', 'risk'],
            'surprise': ['surprise', 'shock', 'astonish', 'amaze', 'unexpected', 'sudden',
                        'startled', 'stunned', 'bewildered', 'astounded', 'revelation'],
            'anticipation': ['await', 'expect', 'anticipate', 'hope', 'look forward',
                           'prepare', 'ready', 'coming', 'imminent', 'approaching'],
            'trust': ['trust', 'believe', 'faith', 'confidence', 'rely', 'depend',
                     'secure', 'safe', 'comfort', 'assurance', 'loyalty'],
            'disgust': ['disgust', 'revulsion', 'repulsed', 'sick', 'vile', 'revolting',
                       'abhor', 'detest', 'loathe', 'despise', 'repugnant']
        }

    def _load_pacing_rules(self) -> Dict[str, Dict]:
        """Load pacing guidelines for emotional beats"""
        return {
            'tension_spacing': {
                'min_chapters_between_peaks': 3,
                'max_sustained_high': 2,  # Max chapters of sustained high tension
                'recovery_chapters': 1     # Chapters needed after peak
            },
            'emotional_variety': {
                'min_emotions_per_chapter': 2,
                'max_dominant_streak': 3   # Max chapters with same dominant emotion
            },
            'catharsis': {
                'min_buildup_chapters': 3,
                'release_magnitude': 3.0    # Minimum drop for catharsis
            }
        }

    def analyze_emotional_arc(self, chapters: List[str]) -> EmotionalArc:
        """Analyze the emotional arc of a narrative"""
        emotion_vectors = []

        for i, chapter in enumerate(chapters):
            vector = self._extract_emotions(chapter, i+1)
            emotion_vectors.append(vector)

        # Identify arc type
        arc_type = self._identify_arc_type(emotion_vectors)

        # Find key moments
        key_moments = self._identify_key_moments(emotion_vectors)

        # Determine overall trajectory
        trajectory = self._determine_trajectory(emotion_vectors)

        # Find catharsis points
        catharsis_points = self._find_catharsis_points(emotion_vectors)

        # Find tension peaks
        tension_peaks = self._find_tension_peaks(emotion_vectors)

        return EmotionalArc(
            chapters=emotion_vectors,
            arc_type=arc_type,
            key_moments=key_moments,
            overall_trajectory=trajectory,
            catharsis_points=catharsis_points,
            tension_peaks=tension_peaks
        )

    def _extract_emotions(self, text: str, chapter_num: int) -> EmotionVector:
        """Extract emotional dimensions from text"""
        text_lower = text.lower()

        # Calculate each emotion score
        emotions = {}
        for emotion, keywords in self.emotion_lexicons.items():
            score = sum(1 for keyword in keywords if keyword in text_lower)
            # Normalize to 0-10 scale
            emotions[emotion] = min(10, score * 0.5)

        # Enhance with sentiment analysis
        sentiment = self.sia.polarity_scores(text[:5000])  # Sample for speed

        # Adjust emotions based on sentiment
        if sentiment['compound'] > 0:
            emotions['joy'] = min(10, emotions.get('joy', 0) + sentiment['pos'] * 5)
            emotions['trust'] = min(10, emotions.get('trust', 0) + sentiment['pos'] * 3)
        else:
            emotions['sadness'] = min(10, emotions.get('sadness', 0) + abs(sentiment['neg']) * 5)
            emotions['fear'] = min(10, emotions.get('fear', 0) + abs(sentiment['neg']) * 3)

        # Detect tension through exclamation and questions
        emotions['tension'] = min(10, emotions.get('tension', 0) +
                                 text.count('!') * 0.1 + text.count('?') * 0.05)

        # Detect anticipation through future tense markers
        future_markers = ['will', 'going to', 'about to', 'soon', 'tomorrow']
        anticipation_count = sum(1 for marker in future_markers if marker in text_lower)
        emotions['anticipation'] = min(10, emotions.get('anticipation', 0) + anticipation_count * 0.3)

        return EmotionVector(
            chapter=chapter_num,
            tension=emotions.get('tension', 0),
            joy=emotions.get('joy', 0),
            sadness=emotions.get('sadness', 0),
            fear=emotions.get('fear', 0),
            surprise=emotions.get('surprise', 0),
            anticipation=emotions.get('anticipation', 0),
            trust=emotions.get('trust', 0),
            disgust=emotions.get('disgust', 0)
        )

    def _identify_arc_type(self, emotions: List[EmotionVector]) -> str:
        """Identify which classic arc type this follows"""
        if not emotions:
            return 'unknown'

        trajectory = [e.magnitude() for e in emotions]

        # Compare to ideal arcs
        best_match = 'unknown'
        best_correlation = 0

        for arc_name, ideal in self.ideal_arcs.items():
            # Resample trajectory to match ideal length
            if len(trajectory) != len(ideal):
                f = interp1d(np.linspace(0, 1, len(trajectory)), trajectory)
                resampled = f(np.linspace(0, 1, len(ideal)))
            else:
                resampled = trajectory

            # Calculate correlation
            correlation = np.corrcoef(resampled, ideal)[0, 1]

            if correlation > best_correlation:
                best_correlation = correlation
                best_match = arc_name

        return best_match if best_correlation > 0.3 else 'complex'

    def _identify_key_moments(self, emotions: List[EmotionVector]) -> List[Tuple[int, str]]:
        """Identify emotionally significant moments"""
        key_moments = []

        if not emotions:
            return key_moments

        magnitudes = [e.magnitude() for e in emotions]

        # Find peaks (local maxima)
        for i in range(1, len(magnitudes) - 1):
            if magnitudes[i] > magnitudes[i-1] and magnitudes[i] > magnitudes[i+1]:
                if magnitudes[i] > np.mean(magnitudes) + np.std(magnitudes):
                    key_moments.append((i+1, f"Emotional peak ({emotions[i].dominant_emotion()})"))

        # Find valleys (local minima)
        for i in range(1, len(magnitudes) - 1):
            if magnitudes[i] < magnitudes[i-1] and magnitudes[i] < magnitudes[i+1]:
                if magnitudes[i] < np.mean(magnitudes) - np.std(magnitudes):
                    key_moments.append((i+1, "Emotional valley"))

        # Find sudden changes
        for i in range(1, len(emotions)):
            change = abs(magnitudes[i] - magnitudes[i-1])
            if change > np.std(magnitudes) * 2:
                key_moments.append((i+1, "Sudden emotional shift"))

        return sorted(key_moments, key=lambda x: x[0])[:10]  # Top 10 moments

    def _determine_trajectory(self, emotions: List[EmotionVector]) -> str:
        """Determine overall emotional trajectory"""
        if not emotions:
            return 'flat'

        magnitudes = [e.magnitude() for e in emotions]

        # Linear regression to find trend
        x = np.arange(len(magnitudes))
        z = np.polyfit(x, magnitudes, 1)
        slope = z[0]

        if slope > 0.1:
            return 'rising'
        elif slope < -0.1:
            return 'falling'
        else:
            # Check for complex pattern
            std = np.std(magnitudes)
            if std > 2:
                return 'complex'
            else:
                return 'flat'

    def _find_catharsis_points(self, emotions: List[EmotionVector]) -> List[int]:
        """Find chapters with emotional release"""
        catharsis_points = []

        if len(emotions) < 3:
            return catharsis_points

        tensions = [e.tension for e in emotions]

        for i in range(2, len(tensions)):
            # Look for significant tension drop after buildup
            buildup = tensions[i-2:i]
            if all(t > 5 for t in buildup):  # High tension buildup
                if tensions[i] < 3:  # Sudden release
                    catharsis_points.append(i+1)

        return catharsis_points

    def _find_tension_peaks(self, emotions: List[EmotionVector]) -> List[int]:
        """Find chapters with maximum tension"""
        if not emotions:
            return []

        tensions = [e.tension for e in emotions]
        mean_tension = np.mean(tensions)
        std_tension = np.std(tensions)

        peaks = []
        for i, tension in enumerate(tensions):
            if tension > mean_tension + std_tension:
                peaks.append(i+1)

        return peaks

    def optimize_emotional_arc(self, current_arc: EmotionalArc,
                              target_arc_type: str = 'hero_journey',
                              genre: str = 'fantasy') -> List[ArcOptimization]:
        """Generate optimization recommendations"""
        optimizations = []

        # Get ideal arc for target type
        if target_arc_type not in self.ideal_arcs:
            target_arc_type = 'hero_journey'

        ideal_arc = self.ideal_arcs[target_arc_type]

        # Resample current arc to match ideal length
        current_trajectory = current_arc.get_trajectory()

        if len(current_trajectory) != len(ideal_arc):
            f = interp1d(np.linspace(0, 1, len(current_trajectory)),
                        current_trajectory, fill_value='extrapolate')
            current_resampled = f(np.linspace(0, 1, len(ideal_arc)))
        else:
            current_resampled = current_trajectory

        # Find chapters needing adjustment
        for i, (current_val, ideal_val) in enumerate(zip(current_resampled, ideal_arc)):
            if abs(current_val - ideal_val) > 2:  # Significant deviation
                chapter_num = min(i+1, len(current_arc.chapters))

                if chapter_num <= len(current_arc.chapters):
                    current_emotion = current_arc.chapters[chapter_num-1]
                    target_emotion = self._create_target_emotion(current_emotion, ideal_val)

                    adjustments = self._generate_adjustments(current_emotion, target_emotion, genre)

                    optimization = ArcOptimization(
                        chapter=chapter_num,
                        current_emotion=current_emotion,
                        target_emotion=target_emotion,
                        adjustments=adjustments,
                        priority=abs(current_val - ideal_val) / 10,
                        expected_impact=(ideal_val - current_val) / 10
                    )

                    optimizations.append(optimization)

        # Check pacing violations
        pacing_optimizations = self._check_pacing_violations(current_arc)
        optimizations.extend(pacing_optimizations)

        # Sort by priority
        optimizations.sort(key=lambda x: x.priority, reverse=True)

        return optimizations[:10]  # Top 10 optimizations

    def _create_target_emotion(self, current: EmotionVector, target_magnitude: float) -> EmotionVector:
        """Create target emotion vector"""
        # Scale current emotions to match target magnitude
        current_mag = current.magnitude()

        if current_mag == 0:
            scale = 1
        else:
            scale = target_magnitude / current_mag

        return EmotionVector(
            chapter=current.chapter,
            tension=min(10, current.tension * scale),
            joy=min(10, current.joy * scale),
            sadness=min(10, current.sadness * scale),
            fear=min(10, current.fear * scale),
            surprise=min(10, current.surprise * scale),
            anticipation=min(10, current.anticipation * scale),
            trust=min(10, current.trust * scale),
            disgust=min(10, current.disgust * scale)
        )

    def _generate_adjustments(self, current: EmotionVector,
                             target: EmotionVector, genre: str) -> List[str]:
        """Generate specific adjustments to reach target emotion"""
        adjustments = []

        # Tension adjustments
        tension_diff = target.tension - current.tension
        if tension_diff > 2:
            adjustments.append("Add conflict or confrontation scene")
            adjustments.append("Introduce time pressure or deadline")
            adjustments.append("Escalate existing stakes")
        elif tension_diff < -2:
            adjustments.append("Add moment of relief or resolution")
            adjustments.append("Include calming or reflective scene")

        # Joy adjustments
        joy_diff = target.joy - current.joy
        if joy_diff > 2:
            adjustments.append("Add moment of triumph or celebration")
            adjustments.append("Include humor or light-hearted interaction")
        elif joy_diff < -2:
            adjustments.append("Introduce setback or disappointment")

        # Sadness adjustments
        sadness_diff = target.sadness - current.sadness
        if sadness_diff > 2:
            adjustments.append("Add loss or sacrifice element")
            adjustments.append("Explore character's past trauma")
        elif sadness_diff < -2:
            adjustments.append("Provide hope or silver lining")

        # Fear adjustments
        fear_diff = target.fear - current.fear
        if fear_diff > 2:
            adjustments.append("Introduce threat or danger")
            adjustments.append("Add uncertainty about future")
        elif fear_diff < -2:
            adjustments.append("Provide safety or protection")

        # Surprise adjustments
        surprise_diff = target.surprise - current.surprise
        if surprise_diff > 2:
            adjustments.append("Add plot twist or revelation")
            adjustments.append("Subvert reader expectations")

        # Anticipation adjustments
        anticipation_diff = target.anticipation - current.anticipation
        if anticipation_diff > 2:
            adjustments.append("Foreshadow upcoming events")
            adjustments.append("Build toward confrontation")
            adjustments.append("Create cliffhanger ending")

        return adjustments[:5]  # Top 5 adjustments

    def _check_pacing_violations(self, arc: EmotionalArc) -> List[ArcOptimization]:
        """Check for pacing rule violations"""
        optimizations = []
        tensions = [e.tension for e in arc.chapters]

        # Check for sustained high tension
        high_tension_streak = 0
        for i, tension in enumerate(tensions):
            if tension > 7:
                high_tension_streak += 1
                if high_tension_streak > self.pacing_rules['tension_spacing']['max_sustained_high']:
                    # Need relief
                    target = EmotionVector(
                        chapter=i+1,
                        tension=4,
                        joy=arc.chapters[i].joy,
                        sadness=arc.chapters[i].sadness,
                        fear=arc.chapters[i].fear,
                        surprise=arc.chapters[i].surprise,
                        anticipation=arc.chapters[i].anticipation,
                        trust=arc.chapters[i].trust + 2,
                        disgust=arc.chapters[i].disgust
                    )

                    optimizations.append(ArcOptimization(
                        chapter=i+1,
                        current_emotion=arc.chapters[i],
                        target_emotion=target,
                        adjustments=["Add breathing room", "Include quieter moment",
                                   "Provide temporary resolution"],
                        priority=0.8,
                        expected_impact=0.3
                    ))
            else:
                high_tension_streak = 0

        # Check for emotional monotony
        for i in range(2, len(arc.chapters)):
            recent = arc.chapters[i-2:i+1]
            dominant_emotions = [e.dominant_emotion() for e in recent]

            if len(set(dominant_emotions)) == 1:  # Same dominant emotion
                # Need variety
                optimizations.append(ArcOptimization(
                    chapter=i+1,
                    current_emotion=arc.chapters[i],
                    target_emotion=arc.chapters[i],  # Keep same but adjust
                    adjustments=[f"Vary emotional tone (currently too much {dominant_emotions[0]})",
                               "Introduce contrasting emotion",
                               "Add emotional complexity"],
                    priority=0.6,
                    expected_impact=0.2
                ))

        return optimizations

    def generate_emotion_prompt_enhancements(self, optimization: ArcOptimization) -> str:
        """Generate prompt enhancements for emotional optimization"""
        prompts = []

        prompts.append(f"\n## EMOTIONAL OPTIMIZATION FOR CHAPTER {optimization.chapter}")

        # Current state
        prompts.append(f"\nCurrent emotional profile:")
        prompts.append(f"  - Dominant: {optimization.current_emotion.dominant_emotion()}")
        prompts.append(f"  - Intensity: {optimization.current_emotion.magnitude():.1f}/10")

        # Target state
        prompts.append(f"\nTarget emotional profile:")
        prompts.append(f"  - Dominant: {optimization.target_emotion.dominant_emotion()}")
        prompts.append(f"  - Intensity: {optimization.target_emotion.magnitude():.1f}/10")

        # Specific adjustments
        prompts.append(f"\nRequired adjustments:")
        for adj in optimization.adjustments:
            prompts.append(f"  • {adj}")

        # Emotional beats to hit
        prompts.append(f"\nEmotional beats to incorporate:")

        if optimization.target_emotion.tension > optimization.current_emotion.tension:
            prompts.append("  • Build tension through:")
            prompts.append("    - Unresolved questions")
            prompts.append("    - Conflicting goals")
            prompts.append("    - Time pressure")

        if optimization.target_emotion.surprise > optimization.current_emotion.surprise:
            prompts.append("  • Create surprise through:")
            prompts.append("    - Unexpected character decision")
            prompts.append("    - Hidden information revealed")
            prompts.append("    - Subverted expectation")

        return "\n".join(prompts)

    def visualize_emotional_arc(self, arc: EmotionalArc, save_path: Optional[str] = None):
        """Create visualization of emotional arc"""
        try:
            fig, axes = plt.subplots(3, 1, figsize=(12, 10))

            chapters = list(range(1, len(arc.chapters) + 1))

            # Plot 1: Overall emotional intensity
            trajectory = arc.get_trajectory()
            axes[0].plot(chapters, trajectory, 'b-', linewidth=2, label='Actual')

            # Add ideal arc if identified
            if arc.arc_type in self.ideal_arcs:
                ideal = self.ideal_arcs[arc.arc_type]
                if len(ideal) != len(trajectory):
                    f = interp1d(np.linspace(1, len(ideal), len(ideal)), ideal)
                    ideal_resampled = f(np.linspace(1, len(ideal), len(trajectory)))
                else:
                    ideal_resampled = ideal
                axes[0].plot(chapters, ideal_resampled, 'g--', alpha=0.7,
                           label=f'Ideal ({arc.arc_type})')

            axes[0].set_title('Emotional Intensity Arc')
            axes[0].set_ylabel('Intensity (0-10)')
            axes[0].legend()
            axes[0].grid(True, alpha=0.3)

            # Mark key moments
            for chapter, desc in arc.key_moments[:5]:
                axes[0].axvline(x=chapter, color='r', alpha=0.3, linestyle=':')

            # Plot 2: Individual emotions
            emotions_to_plot = ['tension', 'joy', 'sadness', 'fear']
            for emotion in emotions_to_plot:
                curve = arc.get_emotion_curve(emotion)
                axes[1].plot(chapters, curve, label=emotion.capitalize())

            axes[1].set_title('Individual Emotion Curves')
            axes[1].set_ylabel('Intensity (0-10)')
            axes[1].legend()
            axes[1].grid(True, alpha=0.3)

            # Plot 3: Emotional variety (stacked area)
            emotion_data = {
                'Tension': arc.get_emotion_curve('tension'),
                'Joy': arc.get_emotion_curve('joy'),
                'Sadness': arc.get_emotion_curve('sadness'),
                'Fear': arc.get_emotion_curve('fear'),
                'Surprise': arc.get_emotion_curve('surprise')
            }

            bottom = np.zeros(len(chapters))
            colors = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4', '#FECA57']

            for (emotion, data), color in zip(emotion_data.items(), colors):
                axes[2].bar(chapters, data, bottom=bottom, label=emotion, color=color, width=0.8)
                bottom += data

            axes[2].set_title('Emotional Composition')
            axes[2].set_xlabel('Chapter')
            axes[2].set_ylabel('Cumulative Intensity')
            axes[2].legend(loc='upper right')

            plt.tight_layout()

            if save_path:
                plt.savefig(save_path)
                print(f"Visualization saved to {save_path}")
            else:
                plt.show()

        except Exception as e:
            print(f"Visualization error: {e}")


def demonstrate_emotional_optimization():
    """Demonstrate emotional arc optimization"""
    print("="*60)
    print("EMOTIONAL ARC OPTIMIZER DEMONSTRATION")
    print("="*60)

    # Sample chapters with varying emotions
    sample_chapters = [
        # Chapter 1: Moderate start
        """The morning sun cast long shadows across the village square. Sarah felt a mixture
        of excitement and apprehension as she prepared for the journey ahead. Her mother's
        tears were still fresh in her memory, but the call of adventure was stronger.""",

        # Chapter 2: Building tension
        """Dark clouds gathered as they entered the forbidden forest. Every snap of a twig
        made her heart race. Something was following them, she was certain of it. The fear
        was almost paralyzing, but she pressed on.""",

        # Chapter 3: High tension and fear
        """The creature attacked without warning! Sarah's scream pierced the night as she
        dodged its razor-sharp claws. Terror consumed her as she ran, branches tearing at
        her clothes. This was a nightmare made real.""",

        # Chapter 4: Relief and joy
        """They had survived! As the sun rose, Sarah couldn't help but laugh with relief.
        Her companions joined in, their joy infectious. They had faced death and emerged
        victorious. The bond between them had never been stronger.""",

        # Chapter 5: Building anticipation
        """Tomorrow they would reach the ancient temple. Sarah could barely contain her
        anticipation. All their struggles had led to this moment. Soon, very soon, all
        questions would be answered. The destiny that awaited her was almost within reach."""
    ]

    # Initialize optimizer
    optimizer = EmotionalArcOptimizer()

    # Analyze current emotional arc
    print("\n📊 ANALYZING EMOTIONAL ARC")
    print("-"*40)

    current_arc = optimizer.analyze_emotional_arc(sample_chapters)

    print(f"Arc Type Detected: {current_arc.arc_type}")
    print(f"Overall Trajectory: {current_arc.overall_trajectory}")
    print(f"Tension Peaks: Chapters {current_arc.tension_peaks}")
    print(f"Catharsis Points: Chapters {current_arc.catharsis_points}")

    # Show emotional profile per chapter
    print("\n📈 CHAPTER EMOTIONAL PROFILES")
    print("-"*40)

    for vector in current_arc.chapters:
        magnitude = vector.magnitude()
        bar = '█' * int(magnitude) + '░' * (10 - int(magnitude))
        print(f"Chapter {vector.chapter}: {bar} {magnitude:.1f}/10 "
              f"(Dominant: {vector.dominant_emotion()})")

    # Key moments
    if current_arc.key_moments:
        print("\n🎭 KEY EMOTIONAL MOMENTS")
        print("-"*40)
        for chapter, description in current_arc.key_moments[:5]:
            print(f"  Chapter {chapter}: {description}")

    # Generate optimizations
    print("\n⚡ OPTIMIZATION RECOMMENDATIONS")
    print("-"*40)

    optimizations = optimizer.optimize_emotional_arc(current_arc, 'hero_journey', 'fantasy')

    for opt in optimizations[:5]:
        print(f"\n📍 Chapter {opt.chapter} (Priority: {opt.priority:.2f})")
        print(f"   Current: {opt.current_emotion.dominant_emotion()} "
              f"({opt.current_emotion.magnitude():.1f})")
        print(f"   Target: {opt.target_emotion.dominant_emotion()} "
              f"({opt.target_emotion.magnitude():.1f})")
        print(f"   Adjustments:")
        for adj in opt.adjustments[:3]:
            print(f"     • {adj}")

    # Generate prompt enhancements
    if optimizations:
        print("\n📝 PROMPT ENHANCEMENT EXAMPLE")
        print("-"*40)
        enhancement = optimizer.generate_emotion_prompt_enhancements(optimizations[0])
        print(enhancement)

    # Create visualization (text representation)
    print("\n📊 EMOTIONAL ARC VISUALIZATION")
    print("-"*40)

    trajectory = current_arc.get_trajectory()
    max_val = max(trajectory) if trajectory else 10

    for i, val in enumerate(trajectory):
        bar_length = int((val / max_val) * 30)
        bar = '█' * bar_length + '░' * (30 - bar_length)
        print(f"Ch {i+1}: {bar} {val:.1f}")

    # Summary
    print("\n✅ Emotional optimization analysis complete!")

    # Quality assessment
    avg_intensity = np.mean(trajectory)
    variation = np.std(trajectory)

    print(f"\n📈 Emotional Quality Metrics:")
    print(f"  • Average Intensity: {avg_intensity:.1f}/10")
    print(f"  • Emotional Variation: {variation:.1f}")
    print(f"  • Arc Classification: {current_arc.arc_type}")

    if avg_intensity > 6 and variation > 1.5:
        print("  • Status: Emotionally engaging narrative")
    elif avg_intensity > 4:
        print("  • Status: Moderate emotional engagement")
    else:
        print("  • Status: Needs emotional enhancement")

    return current_arc, optimizations


if __name__ == "__main__":
    demonstrate_emotional_optimization()