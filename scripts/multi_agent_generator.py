#!/usr/bin/env python3
"""
Multi-Agent Story Generator

Incorporates best practices from:
- AIStoryWriter: Multi-stage generation (Plot → Character → Dialogue → Revision)
- NovelGenerator: Three specialist agents (Structure, Character, Scene)

Key techniques adopted:
1. Specialist agents working sequentially with full context
2. "Prose framework with embedded slots" approach
3. Persistent context database for states and facts
4. Real-time validation during generation
5. Multi-pass refinement with revision cycles
"""

import re
import logging
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
import json


class AgentRole(Enum):
    """Specialist agent roles."""
    STRUCTURE = "structure"   # Creates prose framework with slots
    CHARACTER = "character"   # Fills character development slots
    SCENE = "scene"          # Adds sensory details and action
    DIALOGUE = "dialogue"    # Handles conversation and subtext
    EDITOR = "editor"        # Final polish and consistency


class EventType(Enum):
    """Types of story events."""
    DIALOGUE = "dialogue"
    ACTION = "action"
    REVELATION = "revelation"
    CONFLICT = "conflict"
    INTERNAL = "internal"
    TRANSITION = "transition"


@dataclass
class CharacterState:
    """Complete character state tracking (from NovelGenerator)."""
    name: str
    description: str = ""
    status: str = "alive"  # alive, injured, dead, unknown
    first_appearance: int = 0
    last_location: str = ""
    emotional_state: str = "neutral"
    emotional_intensity: float = 0.5  # 0-1

    # Development tracking
    development_arc: List[Tuple[int, str]] = field(default_factory=list)  # (chapter, change)
    internal_conflicts: List[str] = field(default_factory=list)

    # Relationships
    relationships: Dict[str, str] = field(default_factory=dict)  # other -> type

    # Knowledge tracking
    knows: List[str] = field(default_factory=list)
    doesnt_know: List[str] = field(default_factory=list)


@dataclass
class ChapterEvent:
    """Story event tracking (from NovelGenerator)."""
    event_type: EventType
    description: str
    characters_involved: List[str]
    emotional_impact: float  # 1-10 scale
    plot_significance: str  # "major", "medium", "minor"
    consequences: List[str] = field(default_factory=list)


@dataclass
class DialogueBeat:
    """Dialogue with subtext (from NovelGenerator)."""
    speaker: str
    text: str
    subtext: str  # What they really mean
    revelations: List[str] = field(default_factory=list)
    emotional_tone: str = ""


@dataclass
class TimelineEntry:
    """Timeline tracking (from NovelGenerator)."""
    chapter: int
    time_elapsed: str  # "three days", "moments later"
    absolute_time: str  # "morning", "midnight"
    specific_markers: List[str] = field(default_factory=list)


@dataclass
class ChapterPlan:
    """Detailed chapter plan."""
    chapter_num: int
    objectives: List[str]
    scenes: List[Dict[str, Any]]
    character_focus: List[str]
    emotional_arc: Dict[str, str]  # start -> end
    connection_to_previous: str
    connection_to_next: str
    things_to_remember: List[str]  # "Things to Keep in Mind" from AIStoryWriter


@dataclass
class GenerationContext:
    """Full context for generation."""
    chapter_num: int
    previous_summary: str
    character_states: Dict[str, CharacterState]
    active_plot_threads: List[str]
    timeline_position: TimelineEntry
    things_to_remember: List[str]
    world_facts: List[str]


class ContextDatabase:
    """
    Persistent context database for story state.
    Tracks everything needed for coherent generation.
    """

    def __init__(self):
        self.characters: Dict[str, CharacterState] = {}
        self.events: List[ChapterEvent] = []
        self.dialogue_beats: List[DialogueBeat] = []
        self.timeline: List[TimelineEntry] = []
        self.world_facts: Dict[str, str] = {}
        self.plot_threads: Dict[str, Dict] = {}  # name -> {status, introduced, details}
        self.chapter_summaries: Dict[int, str] = {}

    def update_from_chapter(self, chapter_num: int, content: str,
                           events: List[ChapterEvent] = None):
        """Update database from generated chapter."""
        # Extract character mentions and states
        self._extract_characters(chapter_num, content)

        # Track timeline
        self._extract_timeline(chapter_num, content)

        # Add events
        if events:
            self.events.extend(events)

        # Generate summary
        self.chapter_summaries[chapter_num] = self._generate_summary(content)

    def _extract_characters(self, chapter_num: int, content: str):
        """Extract and update character states from content."""
        # Find character names (capitalized words with actions)
        name_pattern = r'\b([A-Z][a-z]{2,15})\b'
        potential_names = set(re.findall(name_pattern, content))

        action_verbs = ['said', 'asked', 'walked', 'looked', 'felt', 'thought']

        for name in potential_names:
            for verb in action_verbs:
                if re.search(rf'\b{name}\b\s+{verb}', content, re.IGNORECASE):
                    if name not in self.characters:
                        self.characters[name] = CharacterState(
                            name=name,
                            first_appearance=chapter_num
                        )

                    # Update emotional state
                    emotion_match = re.search(
                        rf'{name}\s+felt\s+(\w+)', content, re.IGNORECASE
                    )
                    if emotion_match:
                        self.characters[name].emotional_state = emotion_match.group(1)

                    # Update location
                    loc_match = re.search(
                        rf'{name}\s+(?:was|stood|sat)\s+(?:in|at)\s+(?:the\s+)?(\w+)',
                        content, re.IGNORECASE
                    )
                    if loc_match:
                        self.characters[name].last_location = loc_match.group(1)

                    break

    def _extract_timeline(self, chapter_num: int, content: str):
        """Extract timeline information from content."""
        time_patterns = [
            r'(\d+)\s+(hours?|days?|weeks?)\s+later',
            r'(morning|afternoon|evening|night|dawn|dusk)',
            r'(next day|following day|that night)',
        ]

        markers = []
        for pattern in time_patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            markers.extend([' '.join(m) if isinstance(m, tuple) else m for m in matches])

        if markers:
            entry = TimelineEntry(
                chapter=chapter_num,
                time_elapsed=markers[0] if markers else "",
                absolute_time="",
                specific_markers=markers
            )
            self.timeline.append(entry)

    def _generate_summary(self, content: str) -> str:
        """Generate brief chapter summary."""
        sentences = re.split(r'[.!?]+', content)
        sentences = [s.strip() for s in sentences if len(s.strip()) > 30]

        if len(sentences) >= 3:
            return f"{sentences[0]}. {sentences[len(sentences)//2]}. {sentences[-1]}."
        return content[:500]

    def get_things_to_remember(self, chapter_num: int) -> List[str]:
        """
        Get "Things to Keep in Mind" for next chapter.
        Key technique from AIStoryWriter.
        """
        things = []

        # Active character states
        for name, char in self.characters.items():
            if char.emotional_state != "neutral":
                things.append(f"{name} is feeling {char.emotional_state}")
            if char.last_location:
                things.append(f"{name} was last at {char.last_location}")
            if char.status != "alive":
                things.append(f"{name} is {char.status}")

        # Active plot threads
        for name, thread in self.plot_threads.items():
            if thread.get("status") == "active":
                things.append(f"Unresolved: {thread.get('details', name)}")

        # Recent timeline
        if self.timeline:
            last_time = self.timeline[-1]
            things.append(f"Time: {last_time.time_elapsed or last_time.absolute_time}")

        # Key world facts
        for fact, value in list(self.world_facts.items())[:5]:
            things.append(f"{fact}: {value}")

        return things[:15]  # Limit to 15 most relevant


class MultiAgentGenerator:
    """
    Multi-agent story generation system.

    Uses specialist agents working sequentially:
    1. Structure Agent: Creates prose framework with embedded slots
    2. Character Agent: Fills character development and emotion
    3. Scene Agent: Adds sensory details and action
    4. Dialogue Agent: Handles conversation with subtext
    5. Editor Agent: Final polish and consistency check
    """

    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger(__name__)
        self.context_db = ContextDatabase()
        self.chapter_plans: Dict[int, ChapterPlan] = {}

        # Generation stages from AIStoryWriter
        self.stages = [
            AgentRole.STRUCTURE,
            AgentRole.CHARACTER,
            AgentRole.SCENE,
            AgentRole.DIALOGUE,
            AgentRole.EDITOR
        ]

        # Revision settings
        self.max_revisions = 3
        self.min_revisions = 1

    def plan_chapter(self, chapter_num: int, outline: Dict,
                    previous_content: str = "") -> ChapterPlan:
        """
        Create detailed chapter plan.

        Args:
            chapter_num: Chapter number
            outline: Chapter outline from DOC controller
            previous_content: Previous chapter for continuity

        Returns:
            Detailed chapter plan
        """
        # Get things to remember
        things_to_remember = self.context_db.get_things_to_remember(chapter_num)

        # Extract connection from previous
        connection_prev = ""
        if previous_content:
            # Get last paragraph
            paragraphs = previous_content.split('\n\n')
            if paragraphs:
                connection_prev = paragraphs[-1][:200]

        plan = ChapterPlan(
            chapter_num=chapter_num,
            objectives=outline.get("plot_goals", []),
            scenes=outline.get("required_scenes", []),
            character_focus=outline.get("characters", []),
            emotional_arc={
                "start": outline.get("opening_emotion", "neutral"),
                "end": outline.get("closing_emotion", "neutral")
            },
            connection_to_previous=connection_prev,
            connection_to_next=outline.get("hook_for_next", ""),
            things_to_remember=things_to_remember
        )

        self.chapter_plans[chapter_num] = plan
        return plan

    def generate_chapter(self, chapter_num: int, plan: ChapterPlan,
                        llm_call: callable) -> Tuple[str, Dict]:
        """
        Generate chapter using multi-agent approach.

        Args:
            chapter_num: Chapter number
            plan: Chapter plan
            llm_call: Function to call LLM (prompt -> response)

        Returns:
            Tuple of (generated_content, generation_stats)
        """
        stats = {"stages": [], "revisions": 0}
        content = ""

        # Stage 1: Structure Agent
        self.logger.info(f"Chapter {chapter_num}: Structure Agent")
        structure_prompt = self._build_structure_prompt(plan)
        content = llm_call(structure_prompt)
        stats["stages"].append({"agent": "structure", "length": len(content)})

        # Stage 2: Character Agent
        self.logger.info(f"Chapter {chapter_num}: Character Agent")
        character_prompt = self._build_character_prompt(plan, content)
        content = llm_call(character_prompt)
        stats["stages"].append({"agent": "character", "length": len(content)})

        # Stage 3: Scene Agent
        self.logger.info(f"Chapter {chapter_num}: Scene Agent")
        scene_prompt = self._build_scene_prompt(plan, content)
        content = llm_call(scene_prompt)
        stats["stages"].append({"agent": "scene", "length": len(content)})

        # Stage 4: Dialogue Agent
        self.logger.info(f"Chapter {chapter_num}: Dialogue Agent")
        dialogue_prompt = self._build_dialogue_prompt(plan, content)
        content = llm_call(dialogue_prompt)
        stats["stages"].append({"agent": "dialogue", "length": len(content)})

        # Stage 5: Editor Agent (revision loop)
        for revision in range(self.max_revisions):
            self.logger.info(f"Chapter {chapter_num}: Editor Agent (revision {revision + 1})")
            editor_prompt = self._build_editor_prompt(plan, content)
            new_content = llm_call(editor_prompt)

            # Check if quality improved
            if self._quality_improved(content, new_content) or revision < self.min_revisions:
                content = new_content
                stats["revisions"] += 1
            else:
                break

        stats["stages"].append({"agent": "editor", "revisions": stats["revisions"]})

        # Update context database
        self.context_db.update_from_chapter(chapter_num, content)

        return content, stats

    def _build_structure_prompt(self, plan: ChapterPlan) -> str:
        """Build prompt for Structure Agent."""
        parts = [
            "You are the Structure Agent. Create a prose framework for this chapter.",
            "",
            "## Chapter Objectives:",
        ]
        for obj in plan.objectives:
            parts.append(f"- {obj}")

        parts.extend([
            "",
            "## Things to Remember (maintain continuity):",
        ])
        for thing in plan.things_to_remember:
            parts.append(f"- {thing}")

        if plan.connection_to_previous:
            parts.extend([
                "",
                "## Connection from Previous Chapter:",
                plan.connection_to_previous
            ])

        parts.extend([
            "",
            f"## Emotional Arc: {plan.emotional_arc['start']} → {plan.emotional_arc['end']}",
            "",
            "Write the chapter structure with [SLOT:type] markers for:",
            "- [SLOT:character_moment] - Character development scenes",
            "- [SLOT:sensory_detail] - Rich sensory descriptions",
            "- [SLOT:dialogue] - Important conversations",
            "",
            "Write 1500-2500 words. Include the framework AND content around slots."
        ])

        return "\n".join(parts)

    def _build_character_prompt(self, plan: ChapterPlan, current: str) -> str:
        """Build prompt for Character Agent."""
        parts = [
            "You are the Character Agent. Enhance this chapter with character development.",
            "",
            "## Current Draft:",
            current[:3000],  # First part of current
            "",
            "## Your Task:",
            "1. Find [SLOT:character_moment] markers and replace with deep character moments",
            "2. Show characters' internal states through physical reactions",
            "3. Ensure emotional arc progresses from",
            f"   {plan.emotional_arc['start']} → {plan.emotional_arc['end']}",
            "4. Show growth or change in the focus characters",
            "",
            "## Characters to Focus On:",
        ]
        for char in plan.character_focus:
            parts.append(f"- {char}")

        parts.extend([
            "",
            "Rewrite the chapter with slots filled. Maintain word count (1500-2500)."
        ])

        return "\n".join(parts)

    def _build_scene_prompt(self, plan: ChapterPlan, current: str) -> str:
        """Build prompt for Scene Agent."""
        parts = [
            "You are the Scene Agent. Add sensory richness and action.",
            "",
            "## Current Draft:",
            current[:3000],
            "",
            "## Your Task:",
            "1. Find [SLOT:sensory_detail] markers and replace with vivid descriptions",
            "2. Add physical grounding to emotions (pulse, breath, muscle tension)",
            "3. Include obsessive details (measurements, counts, precise observations)",
            "4. Balance action and reflection",
            "",
            "Guidelines:",
            "- Show don't tell",
            "- Use all five senses",
            "- Ground abstract emotions in body sensations",
            "- Add specific numbers and measurements where appropriate",
            "",
            "Rewrite with sensory enhancement. Target: 1500-2500 words."
        ]

        return "\n".join(parts)

    def _build_dialogue_prompt(self, plan: ChapterPlan, current: str) -> str:
        """Build prompt for Dialogue Agent."""
        parts = [
            "You are the Dialogue Agent. Enhance conversations with subtext.",
            "",
            "## Current Draft:",
            current[:3000],
            "",
            "## Your Task:",
            "1. Find [SLOT:dialogue] markers and create meaningful conversations",
            "2. Add subtext - what characters really mean beneath their words",
            "3. Give each character a distinct voice",
            "4. Use dialogue to reveal character and advance plot",
            "5. Break up dialogue with action beats and body language",
            "",
            "Guidelines:",
            "- No 'As you know, Bob' exposition",
            "- Characters can lie, evade, deflect",
            "- Show power dynamics through word choice",
            "- Keep exchanges punchy - rarely more than 3 lines without action",
            "",
            "Rewrite with enhanced dialogue. Target: 1500-2500 words."
        ]

        return "\n".join(parts)

    def _build_editor_prompt(self, plan: ChapterPlan, current: str) -> str:
        """Build prompt for Editor Agent."""
        parts = [
            "You are the Editor Agent. Polish this chapter for publication.",
            "",
            "## Current Draft:",
            current,
            "",
            "## Check and Fix:",
            "1. Remove AI-isms ('journey', 'delve', 'leverage', 'every fiber')",
            "2. Fix any remaining [SLOT:...] markers",
            "3. Ensure word count is 1500-2500",
            "4. Verify emotional arc completes",
            "5. Check character consistency",
            "6. Remove repetitive phrases",
            "7. Vary sentence structure and length",
            "8. Ensure chapter connects to previous and leads to next",
            "",
            "## Things to Verify (from previous content):",
        ]
        for thing in plan.things_to_remember[:5]:
            parts.append(f"- {thing}")

        parts.extend([
            "",
            "Return the polished chapter. Make minimal changes - only fix issues."
        ])

        return "\n".join(parts)

    def _quality_improved(self, old: str, new: str) -> bool:
        """Check if revision improved quality."""
        # Simple heuristics
        old_len = len(old)
        new_len = len(new)

        # Check if we're still in target range
        old_words = len(old.split())
        new_words = len(new.split())

        in_range = 1500 <= new_words <= 2500

        # Check if AI-isms reduced
        ai_isms = ['journey', 'delve', 'leverage', 'every fiber', 'wash over']
        old_ai = sum(1 for term in ai_isms if term in old.lower())
        new_ai = sum(1 for term in ai_isms if term in new.lower())

        # Check if slots remain
        old_slots = old.count('[SLOT:')
        new_slots = new.count('[SLOT:')

        # Improved if: in range, fewer AI-isms, fewer slots
        return in_range and new_ai <= old_ai and new_slots <= old_slots

    def get_generation_context(self, chapter_num: int) -> GenerationContext:
        """Get full context for chapter generation."""
        return GenerationContext(
            chapter_num=chapter_num,
            previous_summary=self.context_db.chapter_summaries.get(chapter_num - 1, ""),
            character_states=self.context_db.characters,
            active_plot_threads=[
                name for name, t in self.context_db.plot_threads.items()
                if t.get("status") == "active"
            ],
            timeline_position=self.context_db.timeline[-1] if self.context_db.timeline else TimelineEntry(0, "", ""),
            things_to_remember=self.context_db.get_things_to_remember(chapter_num),
            world_facts=list(self.context_db.world_facts.items())[:10]
        )

    def validate_chapter(self, chapter_num: int, content: str) -> Dict[str, Any]:
        """
        Real-time validation during generation.
        Checks for issues that need immediate attention.
        """
        issues = []

        # Word count
        words = len(content.split())
        if words < 1500:
            issues.append({"type": "word_count", "severity": "critical", "detail": f"Too short: {words} words"})
        elif words > 2500:
            issues.append({"type": "word_count", "severity": "major", "detail": f"Too long: {words} words"})

        # Unfilled slots
        slots = re.findall(r'\[SLOT:[^\]]+\]', content)
        if slots:
            issues.append({"type": "unfilled_slots", "severity": "critical", "detail": f"Slots remaining: {slots}"})

        # AI-isms
        ai_isms = ['journey', 'delve', 'leverage', 'every fiber', 'wash over', 'time stood still']
        found = [term for term in ai_isms if term in content.lower()]
        if found:
            issues.append({"type": "ai_isms", "severity": "major", "detail": f"AI-isms found: {found}"})

        # Repetition check
        sentences = re.split(r'[.!?]+', content)
        seen = set()
        duplicates = 0
        for sent in sentences:
            normalized = sent.lower().strip()
            if len(normalized) > 30 and normalized in seen:
                duplicates += 1
            seen.add(normalized)
        if duplicates > 0:
            issues.append({"type": "repetition", "severity": "major", "detail": f"{duplicates} duplicate sentences"})

        # Tone consistency (simple check)
        # Could be enhanced with sentiment analysis

        return {
            "valid": len([i for i in issues if i["severity"] == "critical"]) == 0,
            "issues": issues,
            "word_count": words
        }


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    # Demo
    generator = MultiAgentGenerator()

    # Create a sample plan
    plan = ChapterPlan(
        chapter_num=1,
        objectives=["Introduce protagonist", "Establish ordinary world", "Hint at conflict"],
        scenes=[{"name": "opening", "type": "establishment"}],
        character_focus=["Elena"],
        emotional_arc={"start": "boredom", "end": "curiosity"},
        connection_to_previous="",
        connection_to_next="Lead into inciting incident",
        things_to_remember=["Elena is 16 years old", "Setting is a small village", "Magic is forbidden"]
    )

    print("Chapter Plan:")
    print(f"  Objectives: {plan.objectives}")
    print(f"  Emotional Arc: {plan.emotional_arc}")
    print(f"  Things to Remember: {plan.things_to_remember}")

    # Show the structure prompt
    print("\n" + "=" * 60)
    print("Structure Agent Prompt:")
    print("=" * 60)
    prompt = generator._build_structure_prompt(plan)
    print(prompt[:1000])
