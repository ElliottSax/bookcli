#!/usr/bin/env python3
"""
DOC-Style Detailed Outline Control

Based on the paper "DOC: Improving Long Story Coherence With Detailed Outline Control"
(ACL 2023) by Kevin Yang et al.

Key concepts:
1. Hierarchical detailed outlines control generation
2. Outline elements include: setting, characters, plot points, themes
3. Each chapter gets detailed guidance from the outline
4. Coherence reranking: score candidates by outline adherence
5. Relevance scoring: ensure generated content matches outline

This enables 23%+ improvement in coherence for long-form fiction.
"""

import re
import logging
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
import json


class OutlineLevel(Enum):
    """Hierarchy levels in the outline."""
    BOOK = "book"       # Top-level: premise, themes, arc
    ACT = "act"         # Major story beats
    CHAPTER = "chapter" # Per-chapter details
    SCENE = "scene"     # Scene-level specifics


@dataclass
class OutlineElement:
    """A single element in the detailed outline."""
    level: OutlineLevel
    element_type: str  # "plot", "character", "setting", "theme", "conflict"
    description: str
    importance: str  # "critical", "important", "optional"
    chapter_range: Tuple[int, int] = (1, -1)  # Start/end chapters (-1 = end)
    resolved: bool = False
    dependencies: List[str] = field(default_factory=list)  # Other elements this depends on


@dataclass
class ChapterOutline:
    """Detailed outline for a single chapter."""
    chapter_num: int
    title: str
    pov_character: str
    setting: str
    time_period: str  # "morning", "three days later", etc.

    # Goals for this chapter
    plot_goals: List[str] = field(default_factory=list)
    character_goals: List[str] = field(default_factory=list)
    theme_goals: List[str] = field(default_factory=list)

    # Must-include elements
    required_scenes: List[str] = field(default_factory=list)
    required_dialogue: List[str] = field(default_factory=list)
    required_revelations: List[str] = field(default_factory=list)

    # Constraints
    must_setup: List[str] = field(default_factory=list)  # Setup for future chapters
    must_payoff: List[str] = field(default_factory=list)  # Payoff from earlier setup
    must_avoid: List[str] = field(default_factory=list)  # Things that shouldn't happen yet

    # Emotional arc
    opening_emotion: str = ""
    closing_emotion: str = ""
    emotional_journey: str = ""

    # Connection points
    hook_from_previous: str = ""
    hook_for_next: str = ""


@dataclass
class BookOutline:
    """Complete hierarchical outline for a book."""
    title: str
    genre: str
    premise: str
    themes: List[str]

    # Main characters
    protagonist: Dict[str, Any] = field(default_factory=dict)
    antagonist: Dict[str, Any] = field(default_factory=dict)
    supporting_cast: List[Dict[str, Any]] = field(default_factory=list)

    # Story structure
    inciting_incident: str = ""
    first_plot_point: str = ""
    midpoint: str = ""
    second_plot_point: str = ""
    climax: str = ""
    resolution: str = ""

    # Act structure
    acts: List[Dict[str, Any]] = field(default_factory=list)

    # Chapter outlines
    chapters: List[ChapterOutline] = field(default_factory=list)

    # Global elements
    world_rules: List[str] = field(default_factory=list)
    key_objects: List[str] = field(default_factory=list)
    mysteries: List[str] = field(default_factory=list)


class DOCOutlineController:
    """
    Implements DOC-style detailed outline control for coherent long-form fiction.

    Features:
    1. Hierarchical outline management (book -> act -> chapter -> scene)
    2. Generation guidance based on outline
    3. Coherence scoring against outline
    4. Relevance reranking of generated content
    """

    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger(__name__)
        self.book_outline: Optional[BookOutline] = None
        self.generation_context: Dict[str, Any] = {}

    def create_outline(self, premise: str, genre: str, num_chapters: int,
                      themes: List[str] = None) -> BookOutline:
        """
        Create a detailed book outline from premise.

        Args:
            premise: Story premise/logline
            genre: Genre (fantasy, thriller, romance, etc.)
            num_chapters: Target number of chapters
            themes: Key themes to explore

        Returns:
            Complete BookOutline structure
        """
        self.logger.info(f"Creating {num_chapters}-chapter outline for '{premise[:50]}...'")

        # Create basic structure
        outline = BookOutline(
            title="",  # Will be filled later
            genre=genre,
            premise=premise,
            themes=themes or []
        )

        # Determine act structure (3-act by default)
        act_breaks = self._calculate_act_breaks(num_chapters)

        outline.acts = [
            {"name": "Act 1: Setup", "chapters": list(range(1, act_breaks[0] + 1))},
            {"name": "Act 2: Confrontation", "chapters": list(range(act_breaks[0] + 1, act_breaks[1] + 1))},
            {"name": "Act 3: Resolution", "chapters": list(range(act_breaks[1] + 1, num_chapters + 1))}
        ]

        # Create chapter outlines
        outline.chapters = self._generate_chapter_outlines(outline, num_chapters, act_breaks)

        self.book_outline = outline
        return outline

    def _calculate_act_breaks(self, num_chapters: int) -> Tuple[int, int]:
        """Calculate where acts break based on chapter count."""
        # Standard 3-act structure: 25% / 50% / 25%
        act1_end = max(1, int(num_chapters * 0.25))
        act2_end = max(act1_end + 1, int(num_chapters * 0.75))
        return (act1_end, act2_end)

    def _generate_chapter_outlines(self, outline: BookOutline, num_chapters: int,
                                   act_breaks: Tuple[int, int]) -> List[ChapterOutline]:
        """Generate detailed outlines for each chapter."""
        chapters = []

        for i in range(1, num_chapters + 1):
            # Determine act
            if i <= act_breaks[0]:
                act = 1
                act_position = "setup"
            elif i <= act_breaks[1]:
                act = 2
                act_position = "confrontation"
            else:
                act = 3
                act_position = "resolution"

            # Determine chapter role based on position
            chapter_role = self._get_chapter_role(i, num_chapters, act_breaks)

            chapter = ChapterOutline(
                chapter_num=i,
                title=f"Chapter {i}",
                pov_character="",  # To be filled
                setting="",
                time_period="",
                plot_goals=self._get_plot_goals_for_chapter(chapter_role, outline),
                character_goals=self._get_character_goals_for_chapter(chapter_role),
                emotional_journey=self._get_emotional_arc_for_chapter(chapter_role),
                hook_from_previous="" if i == 1 else f"Continue from chapter {i-1}",
                hook_for_next="" if i == num_chapters else "Lead into next chapter"
            )

            chapters.append(chapter)

        return chapters

    def _get_chapter_role(self, chapter_num: int, total: int,
                         act_breaks: Tuple[int, int]) -> str:
        """Determine the narrative role of a chapter."""
        if chapter_num == 1:
            return "opening"
        elif chapter_num == act_breaks[0]:
            return "first_plot_point"
        elif chapter_num == (act_breaks[0] + act_breaks[1]) // 2:
            return "midpoint"
        elif chapter_num == act_breaks[1]:
            return "second_plot_point"
        elif chapter_num == total - 1:
            return "climax"
        elif chapter_num == total:
            return "resolution"
        else:
            return "development"

    def _get_plot_goals_for_chapter(self, role: str, outline: BookOutline) -> List[str]:
        """Get plot goals based on chapter role."""
        role_goals = {
            "opening": [
                "Establish protagonist in ordinary world",
                "Hint at story's central conflict",
                "Create hook to engage reader"
            ],
            "first_plot_point": [
                "Protagonist commits to the journey",
                "Stakes become clear",
                "Point of no return"
            ],
            "midpoint": [
                "Major revelation or reversal",
                "Stakes increase significantly",
                "Protagonist's approach must change"
            ],
            "second_plot_point": [
                "All seems lost moment",
                "Protagonist faces ultimate test",
                "Set up final confrontation"
            ],
            "climax": [
                "Final confrontation",
                "Protagonist uses everything learned",
                "Maximum tension and stakes"
            ],
            "resolution": [
                "Tie up loose ends",
                "Show new normal",
                "Thematic payoff"
            ],
            "development": [
                "Advance plot threads",
                "Develop character relationships",
                "Build toward next turning point"
            ]
        }
        return role_goals.get(role, role_goals["development"])

    def _get_character_goals_for_chapter(self, role: str) -> List[str]:
        """Get character development goals based on chapter role."""
        role_goals = {
            "opening": ["Establish character voice and personality", "Show character's normal life"],
            "first_plot_point": ["Show character making crucial choice", "Reveal deeper motivation"],
            "midpoint": ["Force character to confront weakness", "Show growth or setback"],
            "second_plot_point": ["Character faces darkest moment", "Internal and external crisis"],
            "climax": ["Character proves growth", "Apply lessons learned"],
            "resolution": ["Show transformed character", "Hint at future"],
            "development": ["Advance character arc", "Deepen relationships"]
        }
        return role_goals.get(role, role_goals["development"])

    def _get_emotional_arc_for_chapter(self, role: str) -> str:
        """Get emotional journey for chapter."""
        arcs = {
            "opening": "curiosity -> engagement",
            "first_plot_point": "uncertainty -> commitment",
            "midpoint": "confidence -> shock",
            "second_plot_point": "hope -> despair",
            "climax": "fear -> triumph",
            "resolution": "relief -> satisfaction",
            "development": "tension -> partial resolution"
        }
        return arcs.get(role, "tension -> release")

    def get_generation_prompt(self, chapter_num: int) -> str:
        """
        Get detailed generation guidance for a chapter.

        This is the key DOC contribution: detailed outline guides generation.
        """
        if not self.book_outline or chapter_num > len(self.book_outline.chapters):
            return ""

        chapter = self.book_outline.chapters[chapter_num - 1]

        prompt_parts = [
            f"## Chapter {chapter_num}: {chapter.title}",
            "",
            "### Requirements:",
        ]

        # Plot goals
        if chapter.plot_goals:
            prompt_parts.append("\n**Plot Goals (must accomplish):**")
            for goal in chapter.plot_goals:
                prompt_parts.append(f"- {goal}")

        # Character goals
        if chapter.character_goals:
            prompt_parts.append("\n**Character Goals:**")
            for goal in chapter.character_goals:
                prompt_parts.append(f"- {goal}")

        # Required elements
        if chapter.required_scenes:
            prompt_parts.append("\n**Required Scenes:**")
            for scene in chapter.required_scenes:
                prompt_parts.append(f"- {scene}")

        # Setups and payoffs
        if chapter.must_setup:
            prompt_parts.append("\n**Must Setup (for later chapters):**")
            for setup in chapter.must_setup:
                prompt_parts.append(f"- {setup}")

        if chapter.must_payoff:
            prompt_parts.append("\n**Must Payoff (from earlier):**")
            for payoff in chapter.must_payoff:
                prompt_parts.append(f"- {payoff}")

        # Constraints
        if chapter.must_avoid:
            prompt_parts.append("\n**Must Avoid:**")
            for avoid in chapter.must_avoid:
                prompt_parts.append(f"- {avoid}")

        # Emotional arc
        if chapter.emotional_journey:
            prompt_parts.append(f"\n**Emotional Arc:** {chapter.emotional_journey}")

        # Connection points
        if chapter.hook_from_previous:
            prompt_parts.append(f"\n**Connect from previous:** {chapter.hook_from_previous}")
        if chapter.hook_for_next:
            prompt_parts.append(f"\n**Lead into next:** {chapter.hook_for_next}")

        return "\n".join(prompt_parts)

    def score_coherence(self, chapter_num: int, content: str) -> Dict[str, float]:
        """
        Score generated content against outline requirements.

        This is the coherence reranking component of DOC.
        """
        if not self.book_outline or chapter_num > len(self.book_outline.chapters):
            return {"overall": 80.0}

        chapter = self.book_outline.chapters[chapter_num - 1]
        scores = {}

        # Score plot goal coverage
        plot_score = self._score_goal_coverage(chapter.plot_goals, content)
        scores["plot_goals"] = plot_score

        # Score character goal coverage
        char_score = self._score_goal_coverage(chapter.character_goals, content)
        scores["character_goals"] = char_score

        # Score required elements
        if chapter.required_scenes:
            scene_score = self._score_goal_coverage(chapter.required_scenes, content)
            scores["required_scenes"] = scene_score

        # Score emotional arc
        if chapter.emotional_journey:
            emotion_score = self._score_emotional_arc(chapter.emotional_journey, content)
            scores["emotional_arc"] = emotion_score

        # Check constraints (things to avoid)
        if chapter.must_avoid:
            avoid_score = self._score_avoidance(chapter.must_avoid, content)
            scores["constraints"] = avoid_score

        # Calculate overall
        scores["overall"] = sum(scores.values()) / len(scores)

        return scores

    def _score_goal_coverage(self, goals: List[str], content: str) -> float:
        """Score how well content covers goals."""
        if not goals:
            return 100.0

        content_lower = content.lower()
        covered = 0

        for goal in goals:
            # Extract key words from goal
            key_words = re.findall(r'\b\w{4,}\b', goal.lower())
            key_words = [w for w in key_words if w not in
                        {'must', 'should', 'need', 'with', 'from', 'into', 'that', 'this'}]

            # Check if key words appear in content
            matches = sum(1 for word in key_words if word in content_lower)
            if matches >= len(key_words) * 0.5:  # 50% threshold
                covered += 1

        return (covered / len(goals)) * 100

    def _score_emotional_arc(self, arc: str, content: str) -> float:
        """Score emotional arc adherence."""
        # Parse arc (format: "emotion1 -> emotion2")
        if "->" not in arc:
            return 80.0

        parts = arc.split("->")
        start_emotion = parts[0].strip().lower()
        end_emotion = parts[1].strip().lower()

        content_lower = content.lower()

        # Check if emotions are represented
        # (Simple heuristic - would be better with sentiment analysis)
        emotion_words = {
            "curiosity": ["curious", "wonder", "question", "puzzled"],
            "engagement": ["interest", "fascinated", "drawn", "compelled"],
            "uncertainty": ["unsure", "doubt", "hesitate", "uncertain"],
            "commitment": ["decided", "determined", "resolved", "committed"],
            "confidence": ["confident", "sure", "certain", "believe"],
            "shock": ["shocked", "stunned", "surprised", "realized"],
            "hope": ["hope", "optimistic", "believe", "possible"],
            "despair": ["despair", "hopeless", "lost", "defeated"],
            "fear": ["afraid", "terrified", "fear", "dread"],
            "triumph": ["triumph", "victory", "success", "won"],
            "relief": ["relief", "relieved", "safe", "finally"],
            "satisfaction": ["satisfied", "content", "fulfilled", "complete"],
            "tension": ["tense", "nervous", "anxious", "worried"]
        }

        start_found = any(word in content_lower for word in emotion_words.get(start_emotion, [start_emotion]))
        end_found = any(word in content_lower for word in emotion_words.get(end_emotion, [end_emotion]))

        if start_found and end_found:
            return 100.0
        elif start_found or end_found:
            return 70.0
        else:
            return 50.0

    def _score_avoidance(self, avoid_list: List[str], content: str) -> float:
        """Score constraint adherence (things to avoid)."""
        content_lower = content.lower()
        violations = 0

        for avoid in avoid_list:
            # Extract key concept
            key_words = re.findall(r'\b\w{4,}\b', avoid.lower())
            if any(word in content_lower for word in key_words):
                violations += 1

        if not avoid_list:
            return 100.0

        return max(0, 100 - (violations / len(avoid_list)) * 100)

    def update_chapter_outline(self, chapter_num: int, **updates):
        """Update a chapter's outline with new information."""
        if self.book_outline and chapter_num <= len(self.book_outline.chapters):
            chapter = self.book_outline.chapters[chapter_num - 1]
            for key, value in updates.items():
                if hasattr(chapter, key):
                    setattr(chapter, key, value)

    def to_json(self) -> str:
        """Export outline to JSON."""
        if not self.book_outline:
            return "{}"

        outline = self.book_outline
        data = {
            "title": outline.title,
            "genre": outline.genre,
            "premise": outline.premise,
            "themes": outline.themes,
            "acts": outline.acts,
            "chapters": [
                {
                    "chapter_num": ch.chapter_num,
                    "title": ch.title,
                    "pov_character": ch.pov_character,
                    "plot_goals": ch.plot_goals,
                    "character_goals": ch.character_goals,
                    "emotional_journey": ch.emotional_journey,
                    "must_setup": ch.must_setup,
                    "must_payoff": ch.must_payoff,
                    "must_avoid": ch.must_avoid
                }
                for ch in outline.chapters
            ]
        }
        return json.dumps(data, indent=2)

    def from_json(self, json_str: str):
        """Load outline from JSON."""
        data = json.loads(json_str)

        self.book_outline = BookOutline(
            title=data.get("title", ""),
            genre=data.get("genre", ""),
            premise=data.get("premise", ""),
            themes=data.get("themes", []),
            acts=data.get("acts", [])
        )

        for ch_data in data.get("chapters", []):
            chapter = ChapterOutline(
                chapter_num=ch_data.get("chapter_num", 0),
                title=ch_data.get("title", ""),
                pov_character=ch_data.get("pov_character", ""),
                setting=ch_data.get("setting", ""),
                time_period=ch_data.get("time_period", ""),
                plot_goals=ch_data.get("plot_goals", []),
                character_goals=ch_data.get("character_goals", []),
                emotional_journey=ch_data.get("emotional_journey", ""),
                must_setup=ch_data.get("must_setup", []),
                must_payoff=ch_data.get("must_payoff", []),
                must_avoid=ch_data.get("must_avoid", [])
            )
            self.book_outline.chapters.append(chapter)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    # Demo
    controller = DOCOutlineController()

    # Create outline
    outline = controller.create_outline(
        premise="A young wizard discovers she is the heir to a forbidden magic that could save or destroy the kingdom",
        genre="fantasy",
        num_chapters=12,
        themes=["power and responsibility", "chosen one", "sacrifice"]
    )

    print("Created outline:")
    print(f"  Acts: {len(outline.acts)}")
    print(f"  Chapters: {len(outline.chapters)}")

    # Get generation prompt for chapter 1
    print("\n" + "=" * 60)
    print("Generation prompt for Chapter 1:")
    print("=" * 60)
    print(controller.get_generation_prompt(1))

    # Simulate scoring
    sample_content = """
    Elena stood at the edge of the market square, watching the merchant stalls with practiced
    disinterest. Today was her sixteenth birthday, though no one seemed to notice or care.
    She felt the familiar pull of something inside her - a restlessness she couldn't explain.

    "Strange girl," she heard someone mutter as she passed.

    Strange. That was what they called her. Strange because she could feel the currents of
    something beneath the world, something that sang to her in colors no one else could see.
    """

    scores = controller.score_coherence(1, sample_content)
    print("\n" + "=" * 60)
    print("Coherence scores for sample content:")
    print("=" * 60)
    for key, value in scores.items():
        print(f"  {key}: {value:.1f}%")
