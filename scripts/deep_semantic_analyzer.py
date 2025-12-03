#!/usr/bin/env python3
"""
Deep Semantic Analyzer - Phase 6 Priority 1
Advanced analysis for narrative coherence, themes, symbolism, and subtext
"""

import re
import json
import hashlib
import numpy as np
from typing import Dict, List, Tuple, Optional, Set
from dataclasses import dataclass, field
from collections import defaultdict, Counter
from pathlib import Path
import spacy
import nltk
from nltk.sentiment import SentimentIntensityAnalyzer
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import networkx as nx

# Download required NLTK data
try:
    nltk.download('vader_lexicon', quiet=True)
    nltk.download('punkt', quiet=True)
    nltk.download('averaged_perceptron_tagger', quiet=True)
except:
    pass


@dataclass
class StoryDNA:
    """Core narrative elements that define a story"""
    protagonist: Dict[str, any]
    antagonist: Optional[Dict[str, any]]
    central_conflict: str
    themes: List[str]
    setting: Dict[str, str]
    narrative_arc: str  # e.g., 'hero_journey', 'tragedy', 'comedy'
    point_of_view: str
    tone: str
    genre_markers: List[str]

    def similarity_to(self, other: 'StoryDNA') -> float:
        """Calculate similarity between two story DNAs"""
        score = 0.0

        # Theme overlap
        theme_overlap = len(set(self.themes) & set(other.themes))
        score += theme_overlap * 0.2

        # Same narrative arc
        if self.narrative_arc == other.narrative_arc:
            score += 0.3

        # Similar tone
        if self.tone == other.tone:
            score += 0.2

        return min(1.0, score)


@dataclass
class ThematicThread:
    """A theme that runs through the narrative"""
    theme: str
    occurrences: List[Tuple[int, str]]  # (chapter, context)
    strength: float  # 0-1
    evolution: List[float]  # Strength per chapter
    symbols: List[str]  # Associated symbols
    keywords: List[str]  # Associated words


@dataclass
class SymbolicElement:
    """A symbolic element in the story"""
    symbol: str
    meaning: str
    appearances: List[Tuple[int, str]]  # (chapter, context)
    significance: float  # 0-1
    associations: List[str]  # What it's associated with


@dataclass
class NarrativeCoherence:
    """Measure of story coherence"""
    overall_score: float  # 0-1
    plot_consistency: float
    character_consistency: float
    thematic_consistency: float
    temporal_consistency: float
    causal_consistency: float
    contradictions: List[Dict[str, any]]
    gaps: List[Dict[str, any]]
    strengths: List[str]


class DeepSemanticAnalyzer:
    """Advanced semantic analysis for narrative understanding"""

    def __init__(self):
        """Initialize analyzer with NLP models"""
        try:
            self.nlp = spacy.load("en_core_web_sm")
        except:
            # Fallback if spaCy model not installed
            self.nlp = None

        self.sia = SentimentIntensityAnalyzer()
        self.vectorizer = TfidfVectorizer(max_features=1000, stop_words='english')

        # Archetypal patterns
        self.archetypes = self._load_archetypes()

        # Theme lexicons
        self.theme_lexicons = self._load_theme_lexicons()

        # Symbol database
        self.symbol_meanings = self._load_symbol_database()

    def _load_archetypes(self) -> Dict:
        """Load narrative archetype patterns"""
        return {
            'hero_journey': {
                'stages': [
                    'ordinary_world', 'call_to_adventure', 'refusal',
                    'meeting_mentor', 'crossing_threshold', 'tests',
                    'approach', 'ordeal', 'reward', 'road_back',
                    'resurrection', 'return_elixir'
                ],
                'keywords': ['journey', 'quest', 'hero', 'adventure', 'destiny']
            },
            'tragedy': {
                'stages': [
                    'exposition', 'rising_action', 'climax',
                    'falling_action', 'catastrophe'
                ],
                'keywords': ['doom', 'fate', 'fall', 'hubris', 'tragic']
            },
            'comedy': {
                'stages': [
                    'exposition', 'rising_action', 'climax',
                    'falling_action', 'resolution'
                ],
                'keywords': ['humor', 'misunderstanding', 'marriage', 'reconciliation']
            },
            'rebirth': {
                'stages': [
                    'fall', 'regression', 'rock_bottom',
                    'redemption', 'transformation'
                ],
                'keywords': ['redemption', 'transformation', 'renewal', 'change']
            }
        }

    def _load_theme_lexicons(self) -> Dict[str, List[str]]:
        """Load lexicons for theme detection"""
        return {
            'love': ['love', 'romance', 'heart', 'passion', 'affection', 'desire', 'kiss', 'embrace'],
            'death': ['death', 'dying', 'mortality', 'grave', 'funeral', 'loss', 'grief', 'mourn'],
            'power': ['power', 'control', 'authority', 'dominance', 'rule', 'command', 'force', 'strength'],
            'identity': ['identity', 'self', 'who', 'being', 'existence', 'purpose', 'meaning', 'essence'],
            'freedom': ['freedom', 'liberty', 'independence', 'escape', 'liberation', 'free', 'chains', 'prison'],
            'justice': ['justice', 'fair', 'right', 'wrong', 'law', 'judgment', 'truth', 'moral'],
            'redemption': ['redemption', 'forgiveness', 'atonement', 'salvation', 'redeem', 'forgive', 'save'],
            'sacrifice': ['sacrifice', 'give up', 'surrender', 'martyr', 'offering', 'cost', 'price'],
            'betrayal': ['betrayal', 'betray', 'treachery', 'deception', 'lie', 'deceit', 'false', 'trust'],
            'family': ['family', 'mother', 'father', 'parent', 'child', 'sibling', 'blood', 'kin']
        }

    def _load_symbol_database(self) -> Dict[str, str]:
        """Load common literary symbols and their meanings"""
        return {
            'water': 'purification, renewal, life',
            'fire': 'passion, destruction, transformation',
            'light': 'knowledge, truth, goodness',
            'darkness': 'ignorance, evil, mystery',
            'journey': 'life, growth, discovery',
            'mountain': 'challenge, achievement, spiritual ascent',
            'garden': 'paradise, innocence, fertility',
            'desert': 'isolation, spiritual drought, testing',
            'mirror': 'self-reflection, truth, vanity',
            'door': 'opportunity, transition, mystery',
            'key': 'solution, access, power',
            'crown': 'authority, responsibility, achievement',
            'sword': 'conflict, justice, power',
            'rose': 'love, beauty, mortality',
            'snake': 'temptation, evil, rebirth',
            'bird': 'freedom, soul, messenger',
            'tree': 'life, growth, connection',
            'circle': 'wholeness, eternity, cycles',
            'cross': 'sacrifice, faith, intersection',
            'labyrinth': 'confusion, journey, discovery'
        }

    def extract_story_dna(self, text: str) -> StoryDNA:
        """Extract fundamental story elements"""
        # Extract protagonist (most mentioned character)
        characters = self._extract_characters(text)
        protagonist = characters[0] if characters else {'name': 'Unknown', 'traits': []}

        # Extract themes
        themes = self._detect_themes(text)

        # Identify narrative arc
        narrative_arc = self._identify_narrative_arc(text)

        # Detect setting
        setting = self._extract_setting(text)

        # Analyze tone
        tone = self._analyze_tone(text)

        # Extract genre markers
        genre_markers = self._extract_genre_markers(text)

        return StoryDNA(
            protagonist=protagonist,
            antagonist=characters[1] if len(characters) > 1 else None,
            central_conflict=self._extract_central_conflict(text),
            themes=themes,
            setting=setting,
            narrative_arc=narrative_arc,
            point_of_view=self._detect_pov(text),
            tone=tone,
            genre_markers=genre_markers
        )

    def _extract_characters(self, text: str) -> List[Dict]:
        """Extract and analyze characters"""
        characters = []

        if self.nlp:
            doc = self.nlp(text[:100000])  # Limit for performance

            # Find named entities that are people
            people = [ent.text for ent in doc.ents if ent.label_ == "PERSON"]
            people_counts = Counter(people)

            # Top 5 most mentioned characters
            for name, count in people_counts.most_common(5):
                characters.append({
                    'name': name,
                    'mentions': count,
                    'traits': self._extract_character_traits(text, name)
                })
        else:
            # Fallback: Simple proper noun detection
            words = text.split()
            capitalized = [w for w in words if w and w[0].isupper()]
            counts = Counter(capitalized)

            for name, count in counts.most_common(5):
                if count > 5:  # Mentioned at least 5 times
                    characters.append({
                        'name': name,
                        'mentions': count,
                        'traits': []
                    })

        return characters

    def _extract_character_traits(self, text: str, character: str) -> List[str]:
        """Extract traits associated with a character"""
        traits = []

        # Find sentences mentioning the character
        sentences = text.split('.')
        char_sentences = [s for s in sentences if character.lower() in s.lower()]

        # Look for adjectives near character name
        trait_words = ['brave', 'clever', 'kind', 'cruel', 'wise', 'foolish',
                      'strong', 'weak', 'beautiful', 'ugly', 'young', 'old']

        for sentence in char_sentences[:20]:  # Analyze first 20 mentions
            for trait in trait_words:
                if trait in sentence.lower():
                    traits.append(trait)

        return list(set(traits))[:5]  # Return top 5 unique traits

    def _detect_themes(self, text: str) -> List[str]:
        """Detect major themes in the text"""
        text_lower = text.lower()
        theme_scores = {}

        for theme, keywords in self.theme_lexicons.items():
            score = sum(1 for keyword in keywords if keyword in text_lower)
            theme_scores[theme] = score / len(keywords)  # Normalize by keyword count

        # Return themes with significant presence (>0.1 normalized score)
        themes = [theme for theme, score in theme_scores.items() if score > 0.1]
        return sorted(themes, key=lambda t: theme_scores[t], reverse=True)[:5]

    def _identify_narrative_arc(self, text: str) -> str:
        """Identify the narrative archetype"""
        text_lower = text.lower()
        arc_scores = {}

        for arc_name, arc_data in self.archetypes.items():
            score = sum(1 for keyword in arc_data['keywords'] if keyword in text_lower)
            arc_scores[arc_name] = score

        if arc_scores:
            return max(arc_scores, key=arc_scores.get)
        return 'unknown'

    def _extract_setting(self, text: str) -> Dict[str, str]:
        """Extract setting information"""
        setting = {
            'time_period': 'unknown',
            'location': 'unknown',
            'atmosphere': 'unknown'
        }

        # Time period detection
        if any(word in text.lower() for word in ['spaceship', 'laser', 'android', 'cyber']):
            setting['time_period'] = 'future'
        elif any(word in text.lower() for word in ['sword', 'castle', 'knight', 'dragon']):
            setting['time_period'] = 'medieval'
        elif any(word in text.lower() for word in ['smartphone', 'internet', 'computer', 'email']):
            setting['time_period'] = 'contemporary'

        # Location detection (simplified)
        if 'city' in text.lower():
            setting['location'] = 'urban'
        elif 'forest' in text.lower() or 'mountain' in text.lower():
            setting['location'] = 'nature'
        elif 'space' in text.lower() or 'planet' in text.lower():
            setting['location'] = 'space'

        # Atmosphere
        sentiment = self.sia.polarity_scores(text[:5000])
        if sentiment['neg'] > 0.3:
            setting['atmosphere'] = 'dark'
        elif sentiment['pos'] > 0.3:
            setting['atmosphere'] = 'light'
        else:
            setting['atmosphere'] = 'neutral'

        return setting

    def _extract_central_conflict(self, text: str) -> str:
        """Extract the central conflict"""
        conflict_keywords = {
            'vs': 'versus',
            'against': 'opposition',
            'fight': 'combat',
            'struggle': 'internal',
            'battle': 'war',
            'conflict': 'direct'
        }

        for keyword, conflict_type in conflict_keywords.items():
            if keyword in text.lower():
                # Find context around keyword
                index = text.lower().find(keyword)
                context = text[max(0, index-50):min(len(text), index+50)]
                return f"{conflict_type}: {context[:50]}..."

        return "undefined conflict"

    def _detect_pov(self, text: str) -> str:
        """Detect point of view"""
        first_person_count = text.lower().count(' i ') + text.lower().count(' me ') + text.lower().count(' my ')
        second_person_count = text.lower().count(' you ') + text.lower().count(' your ')
        third_person_count = text.lower().count(' he ') + text.lower().count(' she ') + text.lower().count(' they ')

        counts = {
            'first_person': first_person_count,
            'second_person': second_person_count,
            'third_person': third_person_count
        }

        return max(counts, key=counts.get)

    def _analyze_tone(self, text: str) -> str:
        """Analyze overall tone"""
        sentiment = self.sia.polarity_scores(text[:10000])

        if sentiment['compound'] > 0.5:
            return 'optimistic'
        elif sentiment['compound'] < -0.5:
            return 'pessimistic'
        elif sentiment['neu'] > 0.7:
            return 'neutral'
        else:
            return 'mixed'

    def _extract_genre_markers(self, text: str) -> List[str]:
        """Extract genre-specific markers"""
        markers = []

        genre_indicators = {
            'fantasy': ['magic', 'wizard', 'dragon', 'spell', 'enchanted'],
            'sci-fi': ['spaceship', 'alien', 'robot', 'laser', 'planet'],
            'mystery': ['detective', 'clue', 'murder', 'investigation', 'suspect'],
            'romance': ['love', 'kiss', 'heart', 'passion', 'embrace'],
            'horror': ['terror', 'fear', 'blood', 'scream', 'monster'],
            'thriller': ['danger', 'chase', 'escape', 'conspiracy', 'threat']
        }

        text_lower = text.lower()
        for genre, keywords in genre_indicators.items():
            if any(keyword in text_lower for keyword in keywords):
                markers.append(genre)

        return markers

    def analyze_thematic_threads(self, chapters: List[str]) -> List[ThematicThread]:
        """Trace themes through the narrative"""
        threads = []

        for theme, keywords in self.theme_lexicons.items():
            occurrences = []
            evolution = []

            for i, chapter in enumerate(chapters):
                chapter_lower = chapter.lower()
                theme_count = sum(1 for keyword in keywords if keyword in chapter_lower)

                if theme_count > 0:
                    # Find context
                    for keyword in keywords:
                        if keyword in chapter_lower:
                            idx = chapter_lower.find(keyword)
                            context = chapter[max(0, idx-30):min(len(chapter), idx+30)]
                            occurrences.append((i+1, context))
                            break

                    evolution.append(theme_count / len(keywords))
                else:
                    evolution.append(0.0)

            if occurrences:  # Theme is present
                threads.append(ThematicThread(
                    theme=theme,
                    occurrences=occurrences[:10],  # Top 10 occurrences
                    strength=np.mean(evolution),
                    evolution=evolution,
                    symbols=self._find_associated_symbols(theme),
                    keywords=keywords[:5]
                ))

        return sorted(threads, key=lambda t: t.strength, reverse=True)

    def _find_associated_symbols(self, theme: str) -> List[str]:
        """Find symbols associated with a theme"""
        associations = {
            'love': ['rose', 'heart', 'ring', 'garden'],
            'death': ['darkness', 'grave', 'shadow', 'cross'],
            'power': ['crown', 'sword', 'throne', 'scepter'],
            'freedom': ['bird', 'key', 'door', 'sky'],
            'redemption': ['light', 'water', 'cross', 'sunrise']
        }

        return associations.get(theme, [])

    def detect_symbolic_layers(self, text: str) -> List[SymbolicElement]:
        """Detect and analyze symbolic elements"""
        symbols = []
        text_lower = text.lower()

        for symbol, meaning in self.symbol_meanings.items():
            if symbol in text_lower:
                appearances = []

                # Find all appearances
                index = 0
                while True:
                    index = text_lower.find(symbol, index)
                    if index == -1:
                        break
                    context = text[max(0, index-50):min(len(text), index+50)]
                    chapter_num = text[:index].count('\n\n') + 1  # Estimate chapter
                    appearances.append((chapter_num, context))
                    index += len(symbol)

                if appearances:
                    symbols.append(SymbolicElement(
                        symbol=symbol,
                        meaning=meaning,
                        appearances=appearances[:5],  # Top 5 appearances
                        significance=len(appearances) / 100.0,  # Normalize
                        associations=self._find_symbol_associations(text, symbol)
                    ))

        return sorted(symbols, key=lambda s: s.significance, reverse=True)[:10]

    def _find_symbol_associations(self, text: str, symbol: str) -> List[str]:
        """Find what a symbol is associated with in the text"""
        associations = []
        sentences = text.split('.')

        for sentence in sentences:
            if symbol in sentence.lower():
                # Extract nouns from sentence (simplified)
                words = sentence.split()
                nouns = [w for w in words if w[0].isupper() and w != symbol.capitalize()]
                associations.extend(nouns)

        return list(set(associations))[:5]

    def compute_narrative_coherence(self, chapters: List[str]) -> NarrativeCoherence:
        """Compute multi-dimensional narrative coherence"""

        # Plot consistency: Check if events follow logically
        plot_consistency = self._analyze_plot_consistency(chapters)

        # Character consistency: Check if characters behave consistently
        character_consistency = self._analyze_character_consistency(chapters)

        # Thematic consistency: Check if themes are maintained
        thematic_consistency = self._analyze_thematic_consistency(chapters)

        # Temporal consistency: Check timeline coherence
        temporal_consistency = self._analyze_temporal_consistency(chapters)

        # Causal consistency: Check cause-effect relationships
        causal_consistency = self._analyze_causal_consistency(chapters)

        # Find contradictions and gaps
        contradictions = self._find_contradictions(chapters)
        gaps = self._find_narrative_gaps(chapters)

        # Identify strengths
        strengths = self._identify_strengths(chapters)

        # Calculate overall score
        overall_score = np.mean([
            plot_consistency,
            character_consistency,
            thematic_consistency,
            temporal_consistency,
            causal_consistency
        ])

        return NarrativeCoherence(
            overall_score=overall_score,
            plot_consistency=plot_consistency,
            character_consistency=character_consistency,
            thematic_consistency=thematic_consistency,
            temporal_consistency=temporal_consistency,
            causal_consistency=causal_consistency,
            contradictions=contradictions,
            gaps=gaps,
            strengths=strengths
        )

    def _analyze_plot_consistency(self, chapters: List[str]) -> float:
        """Analyze plot consistency across chapters"""
        if len(chapters) < 2:
            return 1.0

        # Compare consecutive chapters for continuity
        similarities = []

        for i in range(len(chapters) - 1):
            if chapters[i] and chapters[i+1]:
                # Use TF-IDF to compare chapters
                try:
                    tfidf = self.vectorizer.fit_transform([chapters[i], chapters[i+1]])
                    similarity = cosine_similarity(tfidf[0:1], tfidf[1:2])[0][0]
                    similarities.append(similarity)
                except:
                    similarities.append(0.5)  # Default if analysis fails

        return np.mean(similarities) if similarities else 0.5

    def _analyze_character_consistency(self, chapters: List[str]) -> float:
        """Check if characters maintain consistent traits"""
        character_scores = []

        # Track character mentions across chapters
        all_characters = set()
        chapter_characters = []

        for chapter in chapters:
            chars = set(self._extract_characters(chapter))
            chars_names = {c['name'] for c in chars}
            chapter_characters.append(chars_names)
            all_characters.update(chars_names)

        # Check if main characters appear consistently
        if all_characters:
            for char in all_characters:
                appearances = sum(1 for chars in chapter_characters if char in chars)
                consistency = appearances / len(chapters)
                character_scores.append(consistency)

        return np.mean(character_scores) if character_scores else 0.5

    def _analyze_thematic_consistency(self, chapters: List[str]) -> float:
        """Check if themes are maintained throughout"""
        if not chapters:
            return 0.5

        # Get themes for each chapter
        chapter_themes = []
        for chapter in chapters:
            themes = self._detect_themes(chapter)
            chapter_themes.append(set(themes))

        if not chapter_themes:
            return 0.5

        # Check theme overlap between consecutive chapters
        overlaps = []
        for i in range(len(chapter_themes) - 1):
            if chapter_themes[i] and chapter_themes[i+1]:
                overlap = len(chapter_themes[i] & chapter_themes[i+1])
                max_themes = max(len(chapter_themes[i]), len(chapter_themes[i+1]))
                if max_themes > 0:
                    overlaps.append(overlap / max_themes)

        return np.mean(overlaps) if overlaps else 0.5

    def _analyze_temporal_consistency(self, chapters: List[str]) -> float:
        """Check timeline consistency"""
        # Simplified: Look for time markers and check they're sequential
        time_markers = ['morning', 'afternoon', 'evening', 'night', 'dawn',
                       'monday', 'tuesday', 'wednesday', 'thursday', 'friday',
                       'saturday', 'sunday', 'january', 'february', 'march']

        timeline_score = 1.0

        for chapter in chapters:
            chapter_lower = chapter.lower()

            # Check for contradictory time statements
            if 'morning' in chapter_lower and 'night' in chapter_lower[:1000]:
                timeline_score -= 0.1  # Potential issue if both in opening

        return max(0.0, timeline_score)

    def _analyze_causal_consistency(self, chapters: List[str]) -> float:
        """Check cause-effect relationships"""
        causal_keywords = ['because', 'therefore', 'thus', 'so', 'consequently',
                          'as a result', 'due to', 'owing to', 'hence']

        causal_count = 0
        total_sentences = 0

        for chapter in chapters:
            sentences = chapter.split('.')
            total_sentences += len(sentences)

            for sentence in sentences:
                if any(keyword in sentence.lower() for keyword in causal_keywords):
                    causal_count += 1

        # Good stories have clear causality
        causal_ratio = causal_count / max(total_sentences, 1)

        # Ideal range: 0.05 - 0.15 (5-15% of sentences show causality)
        if 0.05 <= causal_ratio <= 0.15:
            return 1.0
        elif causal_ratio < 0.05:
            return causal_ratio / 0.05  # Too few causal connections
        else:
            return max(0.5, 1.0 - (causal_ratio - 0.15))  # Too many

    def _find_contradictions(self, chapters: List[str]) -> List[Dict]:
        """Find potential contradictions in the narrative"""
        contradictions = []

        # Track facts across chapters
        facts = defaultdict(list)

        for i, chapter in enumerate(chapters):
            # Extract simple facts (character descriptions, locations, etc.)
            if 'was dead' in chapter and 'was alive' in chapter:
                contradictions.append({
                    'chapter': i+1,
                    'type': 'life_status',
                    'description': 'Character death/life contradiction'
                })

        return contradictions[:5]  # Top 5 contradictions

    def _find_narrative_gaps(self, chapters: List[str]) -> List[Dict]:
        """Find gaps in the narrative"""
        gaps = []

        for i in range(len(chapters) - 1):
            if chapters[i] and chapters[i+1]:
                # Check if there's a large semantic jump
                try:
                    tfidf = self.vectorizer.fit_transform([chapters[i][-1000:], chapters[i+1][:1000]])
                    similarity = cosine_similarity(tfidf[0:1], tfidf[1:2])[0][0]

                    if similarity < 0.2:  # Very low similarity suggests a gap
                        gaps.append({
                            'between_chapters': (i+1, i+2),
                            'similarity': similarity,
                            'description': 'Potential narrative discontinuity'
                        })
                except:
                    pass

        return gaps[:3]  # Top 3 gaps

    def _identify_strengths(self, chapters: List[str]) -> List[str]:
        """Identify narrative strengths"""
        strengths = []

        # Check for strong opening
        if chapters and chapters[0]:
            first_sentence = chapters[0].split('.')[0]
            if len(first_sentence) < 100 and '?' in first_sentence or '!' in first_sentence:
                strengths.append("Strong, engaging opening")

        # Check for thematic depth
        all_text = ' '.join(chapters)
        themes = self._detect_themes(all_text)
        if len(themes) >= 3:
            strengths.append(f"Rich thematic content: {', '.join(themes[:3])}")

        # Check for symbolic layers
        symbols = self.detect_symbolic_layers(all_text)
        if len(symbols) >= 3:
            strengths.append("Multiple symbolic layers present")

        return strengths

    def generate_coherence_report(self, analysis: NarrativeCoherence) -> str:
        """Generate a human-readable coherence report"""
        report = []
        report.append("="*60)
        report.append("NARRATIVE COHERENCE ANALYSIS")
        report.append("="*60)
        report.append(f"\n📊 Overall Coherence Score: {analysis.overall_score:.2f}/1.00")

        # Score breakdown
        report.append("\n📈 Component Scores:")
        report.append(f"  • Plot Consistency:      {analysis.plot_consistency:.2f}")
        report.append(f"  • Character Consistency: {analysis.character_consistency:.2f}")
        report.append(f"  • Thematic Consistency:  {analysis.thematic_consistency:.2f}")
        report.append(f"  • Temporal Consistency:  {analysis.temporal_consistency:.2f}")
        report.append(f"  • Causal Consistency:    {analysis.causal_consistency:.2f}")

        # Strengths
        if analysis.strengths:
            report.append("\n✨ Narrative Strengths:")
            for strength in analysis.strengths:
                report.append(f"  • {strength}")

        # Issues
        if analysis.contradictions:
            report.append("\n⚠️ Contradictions Found:")
            for contradiction in analysis.contradictions[:3]:
                report.append(f"  • Chapter {contradiction['chapter']}: {contradiction['description']}")

        if analysis.gaps:
            report.append("\n🔍 Narrative Gaps:")
            for gap in analysis.gaps[:3]:
                report.append(f"  • Between chapters {gap['between_chapters'][0]}-{gap['between_chapters'][1]}")

        # Recommendations
        report.append("\n💡 Recommendations:")
        if analysis.plot_consistency < 0.7:
            report.append("  • Strengthen plot connections between chapters")
        if analysis.character_consistency < 0.7:
            report.append("  • Ensure characters appear consistently throughout")
        if analysis.thematic_consistency < 0.7:
            report.append("  • Maintain thematic threads across all chapters")

        report.append("\n" + "="*60)

        return "\n".join(report)


def demonstrate_semantic_analysis():
    """Demonstrate deep semantic analysis capabilities"""
    print("="*60)
    print("DEEP SEMANTIC ANALYZER DEMONSTRATION")
    print("="*60)

    # Sample text for analysis
    sample_chapters = [
        """Chapter 1: The Beginning

        Sarah stood at the edge of the cliff, looking down at the churning waters below.
        The key in her hand felt heavy, a burden she had carried for too long. Behind her,
        the ancient forest whispered secrets in a language she was only beginning to understand.

        "You don't have to do this," Marcus said, stepping out from the shadows.

        But she did. The prophecy was clear. The door must be opened, the circle completed.
        Her journey had brought her here, through fire and water, light and darkness.

        She thought of her mother's words: "Power comes with a price, but freedom is priceless."
        The rose in her pocket, withered now, was all that remained of her old life.

        With trembling hands, she inserted the key into the ancient lock...""",

        """Chapter 2: The Revelation

        The door opened to reveal a mirror, reflecting not her face but her soul. Sarah gasped
        as she saw the truth - she was both the hero and the villain of her own story.

        Marcus stood beside her, his presence a reminder of the betrayal that had set everything
        in motion. "The prophecy," he whispered, "it was about redemption, not destruction."

        The forest grew silent, as if holding its breath. The water below had calmed, reflecting
        the full moon like a silver coin. This was the moment of choice, the crossroads of destiny.

        Sarah remembered the labyrinth of her dreams, the endless corridors that always led back
        to this moment. The snake that had appeared in every vision, shedding its skin, being reborn.

        "I understand now," she said, stepping through the doorway into the light beyond..."""
    ]

    # Initialize analyzer
    analyzer = DeepSemanticAnalyzer()

    # 1. Extract Story DNA
    print("\n🧬 STORY DNA EXTRACTION")
    print("-"*40)

    full_text = " ".join(sample_chapters)
    story_dna = analyzer.extract_story_dna(full_text)

    print(f"Protagonist: {story_dna.protagonist['name']}")
    print(f"Themes: {', '.join(story_dna.themes[:3]) if story_dna.themes else 'None detected'}")
    print(f"Narrative Arc: {story_dna.narrative_arc}")
    print(f"POV: {story_dna.point_of_view}")
    print(f"Tone: {story_dna.tone}")
    print(f"Genre Markers: {', '.join(story_dna.genre_markers) if story_dna.genre_markers else 'None'}")

    # 2. Analyze Thematic Threads
    print("\n🎭 THEMATIC THREADS")
    print("-"*40)

    threads = analyzer.analyze_thematic_threads(sample_chapters)

    for thread in threads[:3]:
        print(f"\nTheme: {thread.theme.capitalize()}")
        print(f"  Strength: {'█' * int(thread.strength * 10)}{'░' * (10 - int(thread.strength * 10))} {thread.strength:.2f}")
        print(f"  Keywords: {', '.join(thread.keywords[:3])}")
        print(f"  Symbols: {', '.join(thread.symbols[:3]) if thread.symbols else 'None'}")

    # 3. Detect Symbolic Layers
    print("\n🔮 SYMBOLIC ELEMENTS")
    print("-"*40)

    symbols = analyzer.detect_symbolic_layers(full_text)

    for symbol in symbols[:5]:
        print(f"\nSymbol: {symbol.symbol}")
        print(f"  Meaning: {symbol.meaning}")
        print(f"  Appearances: {len(symbol.appearances)}")
        print(f"  Significance: {'█' * int(symbol.significance * 10)}{'░' * (10 - int(symbol.significance * 10))}")

    # 4. Compute Narrative Coherence
    print("\n📊 NARRATIVE COHERENCE")
    print("-"*40)

    coherence = analyzer.compute_narrative_coherence(sample_chapters)

    # Generate and print report
    report = analyzer.generate_coherence_report(coherence)
    print(report)

    # 5. Advanced Insights
    print("\n🎯 ADVANCED INSIGHTS")
    print("-"*40)

    # Subtext detection
    if 'mirror' in full_text and 'soul' in full_text:
        print("✓ Subtext detected: Self-reflection and identity crisis")

    if 'key' in full_text and 'door' in full_text:
        print("✓ Metaphor detected: Transition and opportunity")

    if story_dna.narrative_arc == 'rebirth':
        print("✓ Transformation narrative identified")

    # Quality assessment
    quality_score = coherence.overall_score * 10
    print(f"\n📈 Semantic Quality Score: {quality_score:.1f}/10")

    if quality_score >= 8:
        print("   Status: Publication-ready depth")
    elif quality_score >= 6:
        print("   Status: Good foundation, needs enrichment")
    else:
        print("   Status: Requires semantic enhancement")

    print("\n✅ Deep semantic analysis complete!")

    return {
        'story_dna': story_dna,
        'themes': threads,
        'symbols': symbols,
        'coherence': coherence
    }


if __name__ == "__main__":
    demonstrate_semantic_analysis()