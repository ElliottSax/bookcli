#!/usr/bin/env python3
"""
Narrative Coherence Tracking System for Fiction

Ensures consistency and logical flow across all chapters of a novel by:
- Tracking characters, their traits, and state changes
- Maintaining consistent world-building facts
- Building progressive complexity and tension
- Creating smooth transitions between chapters
- Detecting contradictions, timeline issues, and plot holes

Enhanced for fiction generation with character arc tracking and plot thread management.
"""

import re
import logging
from typing import Dict, List, Set, Tuple, Optional, Any
from collections import defaultdict
from dataclasses import dataclass, field
import json


@dataclass
class CharacterState:
    """Tracks a character's current state across chapters."""
    name: str
    physical_description: Dict[str, str] = field(default_factory=dict)  # eye_color, hair, etc.
    location: str = ""
    emotional_state: str = ""
    injuries: List[str] = field(default_factory=list)
    possessions: List[str] = field(default_factory=list)
    relationships: Dict[str, str] = field(default_factory=dict)  # other_char -> relationship
    knowledge: Set[str] = field(default_factory=set)  # things character knows
    last_seen_chapter: int = 0


@dataclass
class PlotThread:
    """Tracks a subplot or plot element."""
    name: str
    introduced_chapter: int
    status: str  # "active", "resolved", "abandoned"
    description: str
    related_characters: List[str] = field(default_factory=list)
    checkpoints: List[Tuple[int, str]] = field(default_factory=list)  # (chapter, event)


@dataclass
class WorldFact:
    """A fact about the world that must remain consistent."""
    fact_type: str  # "geography", "magic_rule", "history", "technology"
    description: str
    introduced_chapter: int
    references: List[int] = field(default_factory=list)  # chapters that reference it


@dataclass
class CoherenceReport:
    """Report on narrative coherence across the book."""
    overall_score: float  # 0-100
    character_consistency: float
    plot_coherence: float
    timeline_accuracy: float
    world_consistency: float
    transition_quality: float

    contradictions: List[Dict[str, Any]] = field(default_factory=list)
    unresolved_threads: List[str] = field(default_factory=list)
    character_issues: List[str] = field(default_factory=list)
    timeline_issues: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)


class NarrativeCoherenceTracker:
    """
    Tracks narrative coherence across novel chapters to ensure
    consistent characters, plot, world-building, and pacing.
    """

    def __init__(self, logger: Optional[logging.Logger] = None):
        """Initialize the coherence tracker."""
        self.logger = logger or logging.getLogger(__name__)

        # Character tracking
        self.characters: Dict[str, CharacterState] = {}

        # Plot tracking
        self.plot_threads: Dict[str, PlotThread] = {}
        self.main_plot_points: List[Tuple[int, str]] = []  # (chapter, event)

        # World tracking
        self.world_facts: Dict[str, WorldFact] = {}
        self.locations: Dict[str, Dict[str, Any]] = {}  # location -> properties

        # Timeline tracking
        self.timeline: List[Tuple[int, str, str]] = []  # (chapter, time_marker, event)
        self.current_in_story_time: str = ""

        # Chapter tracking
        self.chapter_summaries: Dict[int, str] = {}
        self.chapter_pov: Dict[int, str] = {}  # chapter -> POV character
        self.chapter_locations: Dict[int, List[str]] = {}

        # Transition tracking
        self.chapter_endings: Dict[int, str] = {}
        self.chapter_openings: Dict[int, str] = {}

    def track_chapter(self, chapter_num: int, content: str,
                     pov_character: Optional[str] = None) -> Dict[str, Any]:
        """
        Track coherence elements in a chapter.

        Args:
            chapter_num: Chapter number (1-indexed)
            content: Chapter content
            pov_character: POV character name (if known)

        Returns:
            Dictionary of tracked elements and any issues found
        """
        self.logger.info(f"Tracking coherence for chapter {chapter_num}")

        issues = []

        # Extract and track characters
        characters_found = self._extract_characters(content, chapter_num)
        char_issues = self._validate_character_consistency(characters_found, chapter_num)
        issues.extend(char_issues)

        # Extract plot elements
        plot_events = self._extract_plot_events(content, chapter_num)

        # Extract world facts
        world_elements = self._extract_world_facts(content, chapter_num)
        world_issues = self._validate_world_consistency(world_elements, chapter_num)
        issues.extend(world_issues)

        # Track timeline
        time_markers = self._extract_timeline(content, chapter_num)
        timeline_issues = self._validate_timeline(time_markers, chapter_num)
        issues.extend(timeline_issues)

        # Track locations
        locations = self._extract_locations(content)
        self.chapter_locations[chapter_num] = locations

        # Generate summary
        summary = self._generate_chapter_summary(content)
        self.chapter_summaries[chapter_num] = summary

        # Track transitions
        self._track_transitions(content, chapter_num)

        if pov_character:
            self.chapter_pov[chapter_num] = pov_character

        return {
            'characters_tracked': len(characters_found),
            'plot_events': len(plot_events),
            'world_facts': len(world_elements),
            'locations': locations,
            'issues': issues,
            'summary': summary
        }

    def _extract_characters(self, content: str, chapter_num: int) -> Dict[str, Dict]:
        """Extract character mentions and their states."""
        characters_found = {}

        # Common character name patterns
        # Capitalized words that appear with action verbs
        name_pattern = r'\b([A-Z][a-z]{2,15})\b'
        potential_names = set(re.findall(name_pattern, content))

        # Filter to likely character names (appear with verbs)
        action_verbs = ['said', 'asked', 'replied', 'walked', 'ran', 'looked', 'turned',
                       'thought', 'felt', 'saw', 'heard', 'knew', 'wanted', 'needed']

        for name in potential_names:
            # Check if name appears with action verbs
            for verb in action_verbs:
                if re.search(rf'\b{name}\b\s+{verb}', content, re.IGNORECASE):
                    characters_found[name] = self._extract_character_state(name, content)
                    break
                if re.search(rf'{verb}\s+\w+\s+{name}', content, re.IGNORECASE):
                    characters_found[name] = self._extract_character_state(name, content)
                    break

        # Update character tracking
        for name, state in characters_found.items():
            if name not in self.characters:
                self.characters[name] = CharacterState(name=name)

            char = self.characters[name]
            char.last_seen_chapter = chapter_num

            # Update physical description if found
            for attr, value in state.get('physical', {}).items():
                if attr not in char.physical_description:
                    char.physical_description[attr] = value

            # Update emotional state
            if state.get('emotion'):
                char.emotional_state = state['emotion']

            # Update location
            if state.get('location'):
                char.location = state['location']

        return characters_found

    def _extract_character_state(self, name: str, content: str) -> Dict:
        """Extract current state information for a character."""
        state = {'physical': {}, 'emotion': '', 'location': ''}

        # Physical descriptions
        eye_match = re.search(rf"{name}'s\s+(\w+)\s+eyes", content, re.IGNORECASE)
        if eye_match:
            state['physical']['eyes'] = eye_match.group(1)

        hair_match = re.search(rf"{name}'s\s+(\w+)\s+hair", content, re.IGNORECASE)
        if hair_match:
            state['physical']['hair'] = hair_match.group(1)

        # Emotional state
        emotion_patterns = [
            rf'{name}\s+(?:felt|was)\s+(\w+)',
            rf'{name}\s+\w+\s+(?:angrily|sadly|happily|nervously|anxiously)',
        ]
        for pattern in emotion_patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                state['emotion'] = match.group(1) if match.lastindex else match.group(0)
                break

        return state

    def _validate_character_consistency(self, characters_found: Dict,
                                        chapter_num: int) -> List[str]:
        """Check for character consistency issues."""
        issues = []

        for name, current_state in characters_found.items():
            if name in self.characters:
                stored = self.characters[name]

                # Check physical description consistency
                for attr, value in current_state.get('physical', {}).items():
                    if attr in stored.physical_description:
                        if stored.physical_description[attr].lower() != value.lower():
                            issues.append(
                                f"Character inconsistency: {name}'s {attr} was "
                                f"'{stored.physical_description[attr]}' but is now '{value}' "
                                f"in chapter {chapter_num}"
                            )

        return issues

    def _extract_plot_events(self, content: str, chapter_num: int) -> List[str]:
        """Extract major plot events from chapter."""
        events = []

        # Look for major event indicators
        event_patterns = [
            r'(?:finally|suddenly|at last),?\s+(\w+\s+\w+\s+\w+)',
            r'(?:discovered|revealed|learned)\s+that\s+([^.]+)',
            r'(?:the truth|the secret)\s+(?:was|about)\s+([^.]+)',
            r'(?:killed|died|betrayed|escaped|captured)\s+([^.]+)',
        ]

        for pattern in event_patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            events.extend(matches[:3])  # Limit per pattern

        # Add to main plot points
        for event in events[:5]:  # Top 5 events
            self.main_plot_points.append((chapter_num, event[:100]))

        return events

    def _extract_world_facts(self, content: str, chapter_num: int) -> List[Dict]:
        """Extract world-building facts."""
        facts = []

        # Geography patterns
        geo_pattern = r'(?:the|a)\s+(\w+\s+(?:mountains?|forests?|rivers?|cities?|kingdoms?|towns?))[^.]*'
        geo_matches = re.findall(geo_pattern, content, re.IGNORECASE)
        for match in geo_matches:
            fact_key = match.lower()
            if fact_key not in self.world_facts:
                self.world_facts[fact_key] = WorldFact(
                    fact_type="geography",
                    description=match,
                    introduced_chapter=chapter_num
                )
            else:
                self.world_facts[fact_key].references.append(chapter_num)
            facts.append({'type': 'geography', 'value': match})

        # Magic/technology rules
        rule_pattern = r'(?:magic|power|technology)\s+(?:that|which)\s+([^.]+)'
        rule_matches = re.findall(rule_pattern, content, re.IGNORECASE)
        for match in rule_matches:
            facts.append({'type': 'rule', 'value': match})

        return facts

    def _validate_world_consistency(self, facts: List[Dict],
                                   chapter_num: int) -> List[str]:
        """Check for world-building consistency issues."""
        issues = []
        # For now, just track - more sophisticated validation can be added
        return issues

    def _extract_timeline(self, content: str, chapter_num: int) -> List[str]:
        """Extract timeline markers from chapter."""
        markers = []

        time_patterns = [
            r'\b(\d+)\s+(hours?|days?|weeks?|months?|years?)\s+(?:later|earlier|ago|before|after)\b',
            r'\b(morning|afternoon|evening|night|dawn|dusk|midnight|noon)\b',
            r'\b(next day|following day|that night|the next morning)\b',
            r'\b(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)\b',
        ]

        for pattern in time_patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            if matches:
                for match in matches:
                    marker = match if isinstance(match, str) else ' '.join(match)
                    markers.append(marker)
                    self.timeline.append((chapter_num, marker, ""))

        return markers

    def _validate_timeline(self, markers: List[str], chapter_num: int) -> List[str]:
        """Check for timeline consistency issues."""
        issues = []

        # Check for impossible time jumps
        if len(self.timeline) > 1:
            prev_chapter, prev_marker, _ = self.timeline[-2] if len(self.timeline) >= 2 else (0, "", "")

            # Simple check: "years later" shouldn't be followed by "yesterday"
            if 'years later' in prev_marker.lower() and any(
                word in m.lower() for m in markers for word in ['yesterday', 'last night', 'this morning']
            ):
                issues.append(
                    f"Possible timeline inconsistency in chapter {chapter_num}: "
                    f"'{prev_marker}' followed by references to recent past"
                )

        return issues

    def _extract_locations(self, content: str) -> List[str]:
        """Extract locations mentioned in chapter."""
        locations = []

        location_patterns = [
            r'(?:in|at|to|from|inside|outside)\s+(?:the\s+)?([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)',
            r'(?:entered|left|arrived at|reached)\s+(?:the\s+)?([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)',
        ]

        for pattern in location_patterns:
            matches = re.findall(pattern, content)
            locations.extend(matches)

        return list(set(locations))[:10]  # Unique, limited

    def _generate_chapter_summary(self, content: str) -> str:
        """Generate a brief summary of chapter content."""
        sentences = re.split(r'[.!?]+', content)
        sentences = [s.strip() for s in sentences if len(s.strip()) > 30]

        if len(sentences) < 2:
            return content[:300]

        # Take first and a middle sentence
        summary = f"{sentences[0]}. {sentences[len(sentences)//2]}"
        return summary[:400]

    def _track_transitions(self, content: str, chapter_num: int):
        """Track chapter endings and openings for smooth transitions."""
        # Get last paragraph
        paragraphs = content.split('\n\n')
        paragraphs = [p.strip() for p in paragraphs if p.strip()]

        if paragraphs:
            self.chapter_endings[chapter_num] = paragraphs[-1][:200]
            self.chapter_openings[chapter_num] = paragraphs[0][:200]

    def add_plot_thread(self, name: str, chapter_num: int,
                       description: str, characters: List[str] = None):
        """Manually add a plot thread to track."""
        self.plot_threads[name] = PlotThread(
            name=name,
            introduced_chapter=chapter_num,
            status="active",
            description=description,
            related_characters=characters or []
        )

    def update_plot_thread(self, name: str, chapter_num: int,
                          event: str, resolved: bool = False):
        """Update a plot thread with new checkpoint."""
        if name in self.plot_threads:
            thread = self.plot_threads[name]
            thread.checkpoints.append((chapter_num, event))
            if resolved:
                thread.status = "resolved"

    def update_character_state(self, name: str, **updates):
        """Manually update a character's state."""
        if name not in self.characters:
            self.characters[name] = CharacterState(name=name)

        char = self.characters[name]
        for key, value in updates.items():
            if hasattr(char, key):
                setattr(char, key, value)

    def analyze_coherence(self) -> CoherenceReport:
        """
        Analyze overall book coherence and return comprehensive report.
        """
        self.logger.info("Analyzing overall narrative coherence...")

        # Calculate scores
        char_score = self._calculate_character_consistency()
        plot_score = self._calculate_plot_coherence()
        timeline_score = self._calculate_timeline_accuracy()
        world_score = self._calculate_world_consistency()
        transition_score = self._calculate_transition_quality()

        # Get issues
        contradictions = self._find_contradictions()
        unresolved = self._find_unresolved_threads()
        char_issues = self._find_character_issues()
        timeline_issues = self._find_timeline_issues()

        # Generate recommendations
        recommendations = self._generate_recommendations(
            char_score, plot_score, timeline_score, world_score, transition_score
        )

        overall = (
            char_score * 0.25 +
            plot_score * 0.25 +
            timeline_score * 0.20 +
            world_score * 0.15 +
            transition_score * 0.15
        )

        return CoherenceReport(
            overall_score=overall,
            character_consistency=char_score,
            plot_coherence=plot_score,
            timeline_accuracy=timeline_score,
            world_consistency=world_score,
            transition_quality=transition_score,
            contradictions=contradictions,
            unresolved_threads=unresolved,
            character_issues=char_issues,
            timeline_issues=timeline_issues,
            recommendations=recommendations
        )

    def _calculate_character_consistency(self) -> float:
        """Calculate character consistency score."""
        if not self.characters:
            return 100.0

        issues = 0
        for char in self.characters.values():
            # Check for incomplete descriptions
            if not char.physical_description:
                issues += 0.5
            # Check for missing in many chapters
            if char.last_seen_chapter > 0:
                total_chapters = max(self.chapter_summaries.keys()) if self.chapter_summaries else 1
                if char.last_seen_chapter < total_chapters - 3:
                    issues += 0.3  # Character disappeared

        return max(0, 100 - issues * 10)

    def _calculate_plot_coherence(self) -> float:
        """Calculate plot coherence score."""
        if not self.plot_threads:
            return 85.0  # Default if no explicit threads tracked

        resolved = sum(1 for t in self.plot_threads.values() if t.status == "resolved")
        active = sum(1 for t in self.plot_threads.values() if t.status == "active")

        if resolved + active == 0:
            return 85.0

        # Good: most threads resolved, some still active at end
        resolution_rate = resolved / (resolved + active) if (resolved + active) > 0 else 0
        return min(100, resolution_rate * 80 + 20)

    def _calculate_timeline_accuracy(self) -> float:
        """Calculate timeline accuracy score."""
        if not self.timeline:
            return 90.0

        # Simple check: timeline should generally progress forward
        issues = 0
        for i in range(1, len(self.timeline)):
            prev_ch, prev_marker, _ = self.timeline[i-1]
            curr_ch, curr_marker, _ = self.timeline[i]

            # Check for backward time jumps without flashback indicators
            if curr_ch > prev_ch:
                if any(word in curr_marker.lower() for word in ['yesterday', 'last week', 'before']):
                    if 'flashback' not in curr_marker.lower() and 'remembered' not in curr_marker.lower():
                        issues += 1

        return max(0, 100 - issues * 15)

    def _calculate_world_consistency(self) -> float:
        """Calculate world-building consistency score."""
        if not self.world_facts:
            return 90.0

        # Check that facts are referenced consistently
        well_established = sum(1 for f in self.world_facts.values() if len(f.references) >= 2)
        total = len(self.world_facts)

        return (well_established / total * 50) + 50 if total > 0 else 90.0

    def _calculate_transition_quality(self) -> float:
        """Calculate chapter transition quality."""
        if len(self.chapter_endings) < 2:
            return 90.0

        # Check for smooth transitions (ending/opening coherence)
        smooth = 0
        chapters = sorted(self.chapter_endings.keys())

        for i in range(len(chapters) - 1):
            curr_end = self.chapter_endings.get(chapters[i], "")
            next_open = self.chapter_openings.get(chapters[i + 1], "")

            # Simple check: shared key words
            end_words = set(curr_end.lower().split())
            open_words = set(next_open.lower().split())

            # Remove common words
            common = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for'}
            end_words -= common
            open_words -= common

            if end_words & open_words:  # Shared significant words
                smooth += 1

        return (smooth / (len(chapters) - 1)) * 100 if len(chapters) > 1 else 90.0

    def _find_contradictions(self) -> List[Dict]:
        """Find contradictions in the narrative."""
        contradictions = []

        # Check character physical descriptions
        for name, char in self.characters.items():
            if len(char.physical_description) > 0:
                # Would need chapter-by-chapter tracking to find changes
                pass

        return contradictions

    def _find_unresolved_threads(self) -> List[str]:
        """Find unresolved plot threads."""
        return [
            f"{t.name} (introduced ch.{t.introduced_chapter})"
            for t in self.plot_threads.values()
            if t.status == "active"
        ]

    def _find_character_issues(self) -> List[str]:
        """Find character-related issues."""
        issues = []

        if self.chapter_summaries:
            total_chapters = max(self.chapter_summaries.keys())
            for name, char in self.characters.items():
                if char.last_seen_chapter < total_chapters - 5:
                    issues.append(f"{name} disappeared after chapter {char.last_seen_chapter}")

        return issues

    def _find_timeline_issues(self) -> List[str]:
        """Find timeline-related issues."""
        return []  # Implementation depends on specific timeline tracking

    def _generate_recommendations(self, char: float, plot: float,
                                 time: float, world: float, trans: float) -> List[str]:
        """Generate improvement recommendations."""
        recs = []

        if char < 80:
            recs.append("Review character descriptions for consistency across chapters")
        if plot < 70:
            recs.append("Ensure all plot threads reach resolution")
        if time < 80:
            recs.append("Check timeline markers for logical progression")
        if world < 70:
            recs.append("Reinforce world-building facts with additional references")
        if trans < 70:
            recs.append("Improve chapter transitions with connecting elements")

        return recs

    def get_context_for_chapter(self, chapter_num: int) -> Dict[str, Any]:
        """
        Get relevant context for generating the next chapter.

        Returns previous chapter summary, active characters,
        unresolved threads, and current timeline position.
        """
        context = {
            'previous_summary': self.chapter_summaries.get(chapter_num - 1, ""),
            'previous_ending': self.chapter_endings.get(chapter_num - 1, ""),
            'active_characters': [
                {'name': c.name, 'location': c.location, 'emotional_state': c.emotional_state}
                for c in self.characters.values()
                if c.last_seen_chapter >= chapter_num - 2
            ],
            'active_plot_threads': [
                {'name': t.name, 'description': t.description, 'last_event': t.checkpoints[-1][1] if t.checkpoints else ""}
                for t in self.plot_threads.values()
                if t.status == "active"
            ],
            'current_locations': self.chapter_locations.get(chapter_num - 1, []),
            'timeline_position': self.timeline[-1] if self.timeline else None,
        }

        return context

    def to_json(self) -> str:
        """Export tracker state to JSON for persistence."""
        state = {
            'characters': {
                name: {
                    'name': c.name,
                    'physical': c.physical_description,
                    'location': c.location,
                    'emotional_state': c.emotional_state,
                    'last_seen': c.last_seen_chapter
                }
                for name, c in self.characters.items()
            },
            'plot_threads': {
                name: {
                    'name': t.name,
                    'status': t.status,
                    'introduced': t.introduced_chapter,
                    'checkpoints': t.checkpoints
                }
                for name, t in self.plot_threads.items()
            },
            'chapter_summaries': self.chapter_summaries,
            'timeline': self.timeline
        }
        return json.dumps(state, indent=2)

    def from_json(self, json_str: str):
        """Load tracker state from JSON."""
        state = json.loads(json_str)

        for name, data in state.get('characters', {}).items():
            self.characters[name] = CharacterState(
                name=data['name'],
                physical_description=data.get('physical', {}),
                location=data.get('location', ''),
                emotional_state=data.get('emotional_state', ''),
                last_seen_chapter=data.get('last_seen', 0)
            )

        for name, data in state.get('plot_threads', {}).items():
            self.plot_threads[name] = PlotThread(
                name=data['name'],
                status=data['status'],
                introduced_chapter=data['introduced'],
                description="",
                checkpoints=data.get('checkpoints', [])
            )

        self.chapter_summaries = state.get('chapter_summaries', {})
        self.timeline = state.get('timeline', [])


def format_coherence_report(report: CoherenceReport) -> str:
    """Format coherence report for display."""
    lines = [
        "=" * 60,
        "NARRATIVE COHERENCE REPORT",
        "=" * 60,
        f"Overall Score: {report.overall_score:.1f}/100",
        "",
        "Category Scores:",
        f"  Character Consistency: {report.character_consistency:.1f}%",
        f"  Plot Coherence:        {report.plot_coherence:.1f}%",
        f"  Timeline Accuracy:     {report.timeline_accuracy:.1f}%",
        f"  World Consistency:     {report.world_consistency:.1f}%",
        f"  Transition Quality:    {report.transition_quality:.1f}%",
    ]

    if report.contradictions:
        lines.append(f"\nContradictions Found ({len(report.contradictions)}):")
        for c in report.contradictions[:5]:
            lines.append(f"  - {c}")

    if report.unresolved_threads:
        lines.append(f"\nUnresolved Plot Threads ({len(report.unresolved_threads)}):")
        for t in report.unresolved_threads[:5]:
            lines.append(f"  - {t}")

    if report.character_issues:
        lines.append(f"\nCharacter Issues ({len(report.character_issues)}):")
        for i in report.character_issues[:5]:
            lines.append(f"  - {i}")

    if report.recommendations:
        lines.append("\nRecommendations:")
        for r in report.recommendations:
            lines.append(f"  * {r}")

    lines.append("=" * 60)
    return "\n".join(lines)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    # Demo usage
    tracker = NarrativeCoherenceTracker()

    # Track some sample chapters
    ch1 = """
    Marcus stood at the edge of the cliff, his blue eyes scanning the horizon.
    The ancient sword hung at his side, a relic from his father's collection.
    Elena approached from behind. "We need to move," she said urgently.
    The morning sun cast long shadows as they began their journey to the mountains.
    """

    ch2 = """
    Three days later, Marcus and Elena reached the mountain pass.
    His blue eyes narrowed as he spotted movement ahead.
    The sword felt heavy at his hip. He had not drawn it since they left.
    Elena touched his arm. "I see them too," she whispered.
    """

    result1 = tracker.track_chapter(1, ch1)
    print(f"Chapter 1: {result1}")

    result2 = tracker.track_chapter(2, ch2)
    print(f"Chapter 2: {result2}")

    # Analyze coherence
    report = tracker.analyze_coherence()
    print(format_coherence_report(report))

    # Get context for next chapter
    context = tracker.get_context_for_chapter(3)
    print("\nContext for Chapter 3:")
    print(json.dumps(context, indent=2, default=str))
