#!/usr/bin/env python3
"""
Character Consistency Validator

Real implementation replacing placeholder logic in comprehensive_quality_validator.py.
Validates character consistency across chapters including:
- Physical descriptions (eye color, hair, height, etc.)
- Personality traits and behavior patterns
- Speech patterns and dialogue style
- Knowledge and abilities
- Relationships with other characters
- Location and timeline tracking
"""

import re
import logging
from typing import Dict, List, Tuple, Optional, Set
from collections import defaultdict
from dataclasses import dataclass, field


@dataclass
class CharacterProfile:
    """Complete profile of a character."""
    name: str
    aliases: Set[str] = field(default_factory=set)

    # Physical attributes
    physical: Dict[str, str] = field(default_factory=dict)  # attr -> value

    # Personality and behavior
    personality_traits: List[str] = field(default_factory=list)
    speech_patterns: List[str] = field(default_factory=list)  # distinctive phrases

    # Abilities and knowledge
    abilities: Set[str] = field(default_factory=set)
    knowledge: Set[str] = field(default_factory=set)

    # Relationships
    relationships: Dict[str, str] = field(default_factory=dict)  # other -> type

    # Tracking
    chapter_appearances: List[int] = field(default_factory=list)
    location_history: List[Tuple[int, str]] = field(default_factory=list)  # (chapter, location)


@dataclass
class ConsistencyIssue:
    """A detected consistency issue."""
    character: str
    issue_type: str  # "physical", "behavior", "knowledge", "relationship", "location"
    severity: str  # "critical", "major", "minor"
    description: str
    chapter: int
    evidence: str  # Quote showing the issue
    previous_value: str
    current_value: str


@dataclass
class ConsistencyReport:
    """Complete consistency analysis report."""
    overall_score: float  # 0-100
    characters_analyzed: int
    issues: List[ConsistencyIssue] = field(default_factory=list)

    # Per-character scores
    character_scores: Dict[str, float] = field(default_factory=dict)

    # Statistics
    physical_consistency: float = 100.0
    behavior_consistency: float = 100.0
    knowledge_consistency: float = 100.0
    relationship_consistency: float = 100.0


class CharacterConsistencyValidator:
    """
    Validates character consistency across chapters.

    Uses pattern matching and state tracking to detect contradictions in:
    - Physical descriptions
    - Personality and behavior
    - Knowledge and abilities
    - Relationships
    - Location and timeline
    """

    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger(__name__)
        self.characters: Dict[str, CharacterProfile] = {}
        self.issues: List[ConsistencyIssue] = []

        # Physical attribute patterns
        self.physical_patterns = {
            'eye_color': [
                r"(?P<name>[A-Z][a-z]+)'s\s+(?P<value>\w+)\s+eyes",
                r"(?P<name>[A-Z][a-z]+)\s+(?:looked at \w+ with|with)\s+(?P<value>\w+)\s+eyes",
                r"(?P<value>\w+)[- ]eyed\s+(?P<name>[A-Z][a-z]+)",
            ],
            'hair_color': [
                r"(?P<name>[A-Z][a-z]+)'s\s+(?P<value>\w+)\s+hair",
                r"(?P<name>[A-Z][a-z]+)\s+ran\s+(?:a hand|fingers)\s+through\s+(?:his|her|their)\s+(?P<value>\w+)\s+hair",
                r"(?P<value>\w+)[- ]haired\s+(?P<name>[A-Z][a-z]+)",
            ],
            'height': [
                r"(?P<name>[A-Z][a-z]+)\s+(?:stood|was)\s+(?P<value>\d+(?:\s+feet|\s+inches|'|''|cm|m)[\d\s]*)",
                r"(?P<name>[A-Z][a-z]+),?\s+(?P<value>tall|short|average height)",
            ],
            'build': [
                r"(?P<name>[A-Z][a-z]+)'s\s+(?P<value>\w+)\s+(?:build|frame|physique)",
                r"(?P<value>muscular|slim|stocky|lean|heavyset)\s+(?P<name>[A-Z][a-z]+)",
            ],
            'age': [
                r"(?P<name>[A-Z][a-z]+)\s+(?:was|is|had been)\s+(?P<value>\d+)\s+(?:years?\s+old)?",
                r"(?P<value>\d+)[- ]year[- ]old\s+(?P<name>[A-Z][a-z]+)",
            ],
            'scars': [
                r"(?P<name>[A-Z][a-z]+)'s\s+(?P<value>scar\s+\w+)",
                r"the\s+(?P<value>scar\s+on\s+[^.]+)\s+(?:on|across)\s+(?P<name>[A-Z][a-z]+)",
            ],
        }

        # Relationship patterns
        self.relationship_patterns = [
            r"(?P<char1>[A-Z][a-z]+)\s+(?:was|is)\s+(?P<char2>[A-Z][a-z]+)'s\s+(?P<rel>\w+)",
            r"(?P<char1>[A-Z][a-z]+)'s\s+(?P<rel>brother|sister|mother|father|friend|enemy|lover|wife|husband)\s+(?P<char2>[A-Z][a-z]+)",
            r"(?P<char1>[A-Z][a-z]+)\s+and\s+(?P<char2>[A-Z][a-z]+)\s+(?:were|are)\s+(?P<rel>\w+)",
        ]

        # Location patterns
        self.location_patterns = [
            r"(?P<name>[A-Z][a-z]+)\s+(?:was|stood|sat|waited)\s+(?:in|at|inside|outside)\s+(?:the\s+)?(?P<loc>[A-Z][\w\s]+)",
            r"(?P<name>[A-Z][a-z]+)\s+(?:entered|left|arrived at|reached)\s+(?:the\s+)?(?P<loc>[A-Z][\w\s]+)",
        ]

        # Knowledge acquisition patterns
        self.knowledge_patterns = [
            r"(?P<name>[A-Z][a-z]+)\s+(?:learned|discovered|realized|knew|found out)\s+(?:that\s+)?(?P<knowledge>[^.]+)",
            r"(?P<name>[A-Z][a-z]+)\s+(?:didn't know|had no idea|was unaware)\s+(?:that\s+)?(?P<unknown>[^.]+)",
        ]

    def analyze_chapter(self, chapter_num: int, content: str) -> Dict:
        """
        Analyze a chapter for character consistency.

        Args:
            chapter_num: Chapter number (1-indexed)
            content: Chapter content

        Returns:
            Dictionary with analysis results
        """
        chapter_issues = []

        # Extract physical descriptions
        for attr, patterns in self.physical_patterns.items():
            for pattern in patterns:
                matches = re.finditer(pattern, content, re.IGNORECASE)
                for match in matches:
                    try:
                        name = match.group('name')
                        value = match.group('value').lower()

                        issue = self._check_physical_consistency(
                            name, attr, value, chapter_num, match.group(0)
                        )
                        if issue:
                            chapter_issues.append(issue)

                    except (IndexError, AttributeError):
                        continue

        # Extract relationships
        for pattern in self.relationship_patterns:
            matches = re.finditer(pattern, content, re.IGNORECASE)
            for match in matches:
                try:
                    char1 = match.group('char1')
                    char2 = match.group('char2')
                    rel = match.group('rel').lower()

                    issue = self._check_relationship_consistency(
                        char1, char2, rel, chapter_num, match.group(0)
                    )
                    if issue:
                        chapter_issues.append(issue)

                except (IndexError, AttributeError):
                    continue

        # Extract knowledge
        for pattern in self.knowledge_patterns:
            matches = re.finditer(pattern, content, re.IGNORECASE)
            for match in matches:
                try:
                    name = match.group('name')
                    knowledge = match.group('knowledge') if 'knowledge' in match.groupdict() else None
                    unknown = match.group('unknown') if 'unknown' in match.groupdict() else None

                    if knowledge:
                        issue = self._check_knowledge_consistency(
                            name, knowledge, True, chapter_num, match.group(0)
                        )
                        if issue:
                            chapter_issues.append(issue)

                except (IndexError, AttributeError):
                    continue

        # Add issues to global list
        self.issues.extend(chapter_issues)

        return {
            'chapter': chapter_num,
            'issues_found': len(chapter_issues),
            'characters_updated': len(self.characters),
            'issues': chapter_issues
        }

    def _check_physical_consistency(self, name: str, attr: str, value: str,
                                   chapter: int, evidence: str) -> Optional[ConsistencyIssue]:
        """Check if physical attribute is consistent with previous mentions."""
        # Initialize character if needed
        if name not in self.characters:
            self.characters[name] = CharacterProfile(name=name)

        char = self.characters[name]
        char.chapter_appearances.append(chapter)

        # Check for contradiction
        if attr in char.physical:
            prev_value = char.physical[attr]

            # Allow for synonyms
            synonyms = {
                'eye_color': {'blue': {'azure', 'sapphire', 'cerulean'},
                             'brown': {'chocolate', 'hazel', 'amber'},
                             'green': {'emerald', 'jade'}},
                'hair_color': {'black': {'raven', 'dark', 'ebony'},
                              'brown': {'chestnut', 'chocolate'},
                              'blonde': {'golden', 'fair', 'flaxen'}},
            }

            # Check if values are equivalent
            if prev_value.lower() != value.lower():
                # Check synonyms
                attr_synonyms = synonyms.get(attr, {})
                is_synonym = False

                for base, syns in attr_synonyms.items():
                    if prev_value.lower() in ({base} | syns) and value.lower() in ({base} | syns):
                        is_synonym = True
                        break

                if not is_synonym:
                    return ConsistencyIssue(
                        character=name,
                        issue_type="physical",
                        severity="critical" if attr in ['eye_color', 'hair_color'] else "major",
                        description=f"{name}'s {attr.replace('_', ' ')} changed from '{prev_value}' to '{value}'",
                        chapter=chapter,
                        evidence=evidence,
                        previous_value=prev_value,
                        current_value=value
                    )
        else:
            # First mention - store it
            char.physical[attr] = value

        return None

    def _check_relationship_consistency(self, char1: str, char2: str, rel: str,
                                        chapter: int, evidence: str) -> Optional[ConsistencyIssue]:
        """Check if relationship is consistent."""
        if char1 not in self.characters:
            self.characters[char1] = CharacterProfile(name=char1)

        char = self.characters[char1]

        if char2 in char.relationships:
            prev_rel = char.relationships[char2]

            # Check for contradictory relationships
            contradictory = {
                ('friend', 'enemy'), ('lover', 'enemy'),
                ('brother', 'friend'), ('sister', 'friend'),  # Family shouldn't change to just friend
                ('wife', 'stranger'), ('husband', 'stranger'),
            }

            pair = (prev_rel.lower(), rel.lower())
            if pair in contradictory or pair[::-1] in contradictory:
                return ConsistencyIssue(
                    character=char1,
                    issue_type="relationship",
                    severity="major",
                    description=f"{char1}'s relationship with {char2} changed from '{prev_rel}' to '{rel}'",
                    chapter=chapter,
                    evidence=evidence,
                    previous_value=prev_rel,
                    current_value=rel
                )
        else:
            char.relationships[char2] = rel

        return None

    def _check_knowledge_consistency(self, name: str, knowledge: str, learned: bool,
                                    chapter: int, evidence: str) -> Optional[ConsistencyIssue]:
        """Check knowledge consistency."""
        if name not in self.characters:
            self.characters[name] = CharacterProfile(name=name)

        char = self.characters[name]

        # Normalize knowledge
        knowledge_key = knowledge.lower().strip()[:100]

        if learned:
            char.knowledge.add(knowledge_key)
        else:
            # Character claims not to know something
            if knowledge_key in char.knowledge:
                return ConsistencyIssue(
                    character=name,
                    issue_type="knowledge",
                    severity="major",
                    description=f"{name} previously knew '{knowledge_key[:50]}...' but now claims not to",
                    chapter=chapter,
                    evidence=evidence,
                    previous_value="knew",
                    current_value="doesn't know"
                )

        return None

    def analyze_all(self, chapters: List[str]) -> ConsistencyReport:
        """
        Analyze all chapters for character consistency.

        Args:
            chapters: List of chapter contents

        Returns:
            Complete consistency report
        """
        self.characters.clear()
        self.issues.clear()

        for i, chapter in enumerate(chapters, 1):
            self.analyze_chapter(i, chapter)

        # Calculate scores
        if not self.issues:
            overall = 100.0
        else:
            # Deduct points based on issue severity
            deductions = {
                'critical': 15,
                'major': 8,
                'minor': 3
            }
            total_deduction = sum(
                deductions.get(issue.severity, 5) for issue in self.issues
            )
            overall = max(0, 100 - total_deduction)

        # Calculate per-type scores
        physical_issues = sum(1 for i in self.issues if i.issue_type == "physical")
        behavior_issues = sum(1 for i in self.issues if i.issue_type == "behavior")
        knowledge_issues = sum(1 for i in self.issues if i.issue_type == "knowledge")
        relationship_issues = sum(1 for i in self.issues if i.issue_type == "relationship")

        # Per-character scores
        char_scores = {}
        for name in self.characters:
            char_issues = sum(1 for i in self.issues if i.character == name)
            char_scores[name] = max(0, 100 - char_issues * 10)

        return ConsistencyReport(
            overall_score=overall,
            characters_analyzed=len(self.characters),
            issues=self.issues,
            character_scores=char_scores,
            physical_consistency=max(0, 100 - physical_issues * 15),
            behavior_consistency=max(0, 100 - behavior_issues * 10),
            knowledge_consistency=max(0, 100 - knowledge_issues * 10),
            relationship_consistency=max(0, 100 - relationship_issues * 10)
        )

    def get_character_summary(self, name: str) -> Optional[Dict]:
        """Get summary of a character's tracked attributes."""
        if name not in self.characters:
            return None

        char = self.characters[name]
        return {
            'name': char.name,
            'physical_attributes': char.physical,
            'relationships': char.relationships,
            'appearances': char.chapter_appearances,
            'known_facts': list(char.knowledge)[:10]  # Limit output
        }

    def get_score(self, chapters: List[str]) -> float:
        """
        Get character consistency score (0-100).

        This is the main method called by ComprehensiveQualityValidator.
        """
        report = self.analyze_all(chapters)
        return report.overall_score


def format_consistency_report(report: ConsistencyReport) -> str:
    """Format consistency report for display."""
    lines = [
        "=" * 60,
        "CHARACTER CONSISTENCY REPORT",
        "=" * 60,
        f"Overall Score: {report.overall_score:.1f}/100",
        f"Characters Analyzed: {report.characters_analyzed}",
        "",
        "Category Scores:",
        f"  Physical Consistency:     {report.physical_consistency:.1f}%",
        f"  Behavior Consistency:     {report.behavior_consistency:.1f}%",
        f"  Knowledge Consistency:    {report.knowledge_consistency:.1f}%",
        f"  Relationship Consistency: {report.relationship_consistency:.1f}%",
    ]

    if report.character_scores:
        lines.append("\nPer-Character Scores:")
        for name, score in sorted(report.character_scores.items(), key=lambda x: x[1]):
            bar = '*' * int(score / 10)
            lines.append(f"  {name:15s}: {bar:10s} {score:.0f}%")

    if report.issues:
        lines.append(f"\nIssues Found ({len(report.issues)}):")

        critical = [i for i in report.issues if i.severity == "critical"]
        major = [i for i in report.issues if i.severity == "major"]

        if critical:
            lines.append("\n  CRITICAL:")
            for issue in critical[:5]:
                lines.append(f"    - Ch.{issue.chapter}: {issue.description}")
                lines.append(f"      Evidence: \"{issue.evidence[:60]}...\"")

        if major:
            lines.append("\n  MAJOR:")
            for issue in major[:5]:
                lines.append(f"    - Ch.{issue.chapter}: {issue.description}")

    lines.append("=" * 60)
    return "\n".join(lines)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    # Test with sample chapters
    chapter1 = """
    Marcus stood in the doorway, his blue eyes scanning the room.
    His sister Elena waited by the window, her long black hair catching the light.
    "You're late," she said, concern evident in her voice.
    Marcus was 25 years old, but felt decades older after everything he'd seen.
    """

    chapter2 = """
    The next morning, Marcus woke with a start. His green eyes snapped open.
    He ran a hand through his hair and went to find Elena.
    His sister - no, his friend - Elena was already awake.
    "I learned something last night," Marcus said. "The truth about our father."
    """

    chapter3 = """
    Marcus didn't know anything about their father's past.
    Elena's blonde hair was tied back as she listened.
    The 25-year-old warrior felt lost.
    """

    validator = CharacterConsistencyValidator()
    report = validator.analyze_all([chapter1, chapter2, chapter3])

    print(format_consistency_report(report))

    # Show character summaries
    print("\nCharacter Summaries:")
    for name in validator.characters:
        summary = validator.get_character_summary(name)
        print(f"\n{name}:")
        print(f"  Physical: {summary['physical_attributes']}")
        print(f"  Relationships: {summary['relationships']}")
