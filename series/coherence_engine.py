"""
Series Coherence Engine for Book Factory
Maintains consistency across multi-book series
"""

import json
import sqlite3
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional, Set, Tuple
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
import hashlib

logger = logging.getLogger(__name__)


class ElementType(Enum):
    """Types of elements tracked across series."""
    CHARACTER = "character"
    LOCATION = "location"
    OBJECT = "object"
    EVENT = "event"
    RELATIONSHIP = "relationship"
    MAGIC_SYSTEM = "magic_system"
    TECHNOLOGY = "technology"
    ORGANIZATION = "organization"
    TIMELINE = "timeline"


@dataclass
class Character:
    """Character information tracked across books."""
    id: str
    name: str
    full_name: Optional[str] = None
    aliases: List[str] = field(default_factory=list)

    # Physical description
    age: Optional[int] = None
    gender: Optional[str] = None
    height: Optional[str] = None
    appearance: Dict[str, str] = field(default_factory=dict)
    distinguishing_features: List[str] = field(default_factory=list)

    # Personality
    personality_traits: List[str] = field(default_factory=list)
    motivations: List[str] = field(default_factory=list)
    fears: List[str] = field(default_factory=list)
    skills: List[str] = field(default_factory=list)

    # Background
    occupation: Optional[str] = None
    backstory: Optional[str] = None
    family: Dict[str, str] = field(default_factory=dict)

    # Tracking
    first_appearance: Optional[str] = None  # book_id:chapter
    last_appearance: Optional[str] = None
    status: str = "active"  # active, deceased, missing, etc.

    # Evolution tracking
    development: Dict[str, str] = field(default_factory=dict)  # book_id -> development notes

    def update_appearance(self, book_id: str, chapter: int):
        """Update character appearance tracking."""
        appearance_ref = f"{book_id}:chapter_{chapter:03d}"
        if not self.first_appearance:
            self.first_appearance = appearance_ref
        self.last_appearance = appearance_ref


@dataclass
class Location:
    """Location information tracked across books."""
    id: str
    name: str
    type: str  # city, building, room, landmark, etc.
    description: str

    # Physical details
    climate: Optional[str] = None
    geography: Optional[str] = None
    notable_features: List[str] = field(default_factory=list)

    # Relationships
    contained_in: Optional[str] = None  # parent location ID
    contains: List[str] = field(default_factory=list)  # child location IDs

    # History
    history: Optional[str] = None
    significance: Optional[str] = None

    # Tracking
    first_mentioned: Optional[str] = None
    last_mentioned: Optional[str] = None
    destroyed: bool = False


@dataclass
class Event:
    """Significant events tracked across series."""
    id: str
    name: str
    description: str
    timestamp: Optional[str] = None  # In-world time

    # Details
    location_id: Optional[str] = None
    participants: List[str] = field(default_factory=list)  # character IDs
    consequences: List[str] = field(default_factory=list)

    # References
    book_id: str
    chapter: int

    # Relationships
    caused_by: Optional[str] = None  # event ID
    leads_to: List[str] = field(default_factory=list)  # event IDs


@dataclass
class Relationship:
    """Relationships between characters."""
    id: str
    character1_id: str
    character2_id: str
    type: str  # family, romantic, friendship, enemy, etc.
    description: str

    # Evolution
    start_book: Optional[str] = None
    end_book: Optional[str] = None
    status: str = "active"
    evolution: Dict[str, str] = field(default_factory=dict)  # book_id -> status


class SeriesCoherenceEngine:
    """
    Manages consistency across book series.
    Features:
    - Character tracking and evolution
    - Location consistency
    - Timeline management
    - Relationship tracking
    - Plot thread continuity
    - World bible generation
    """

    def __init__(self, series_name: str, workspace: Path):
        """
        Initialize the coherence engine.

        Args:
            series_name: Name of the book series
            workspace: Path to series workspace
        """
        self.series_name = series_name
        self.workspace = Path(workspace)
        self.workspace.mkdir(parents=True, exist_ok=True)

        # Database for persistent storage
        self.db_path = self.workspace / f"{series_name}_coherence.db"
        self._init_database()

        # In-memory caches
        self.characters: Dict[str, Character] = {}
        self.locations: Dict[str, Location] = {}
        self.events: Dict[str, Event] = {}
        self.relationships: Dict[str, Relationship] = {}

        # Timeline
        self.timeline: List[Event] = []

        # Plot threads
        self.plot_threads: Dict[str, Dict[str, Any]] = {}

        # Load existing data
        self._load_from_database()

    def _init_database(self):
        """Initialize SQLite database for persistent storage."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Characters table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS characters (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                data JSON NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Locations table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS locations (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                type TEXT,
                data JSON NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Events table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS events (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                book_id TEXT NOT NULL,
                chapter INTEGER NOT NULL,
                timestamp TEXT,
                data JSON NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Relationships table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS relationships (
                id TEXT PRIMARY KEY,
                character1_id TEXT NOT NULL,
                character2_id TEXT NOT NULL,
                type TEXT NOT NULL,
                data JSON NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (character1_id) REFERENCES characters(id),
                FOREIGN KEY (character2_id) REFERENCES characters(id)
            )
        """)

        # Plot threads table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS plot_threads (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                status TEXT DEFAULT 'open',
                data JSON NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Consistency violations table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS violations (
                id TEXT PRIMARY KEY,
                type TEXT NOT NULL,
                severity TEXT NOT NULL,
                description TEXT NOT NULL,
                book_id TEXT,
                chapter INTEGER,
                element_id TEXT,
                detected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        conn.commit()
        conn.close()

    def add_character(
        self,
        name: str,
        book_id: str,
        chapter: int,
        **attributes
    ) -> Character:
        """
        Add a new character to the series.

        Args:
            name: Character name
            book_id: Book where character appears
            chapter: Chapter number
            **attributes: Additional character attributes

        Returns:
            Character object
        """
        # Generate ID
        char_id = self._generate_id('char', name)

        # Check if character already exists (by name similarity)
        existing = self._find_similar_character(name)
        if existing:
            logger.warning(f"Similar character found: {existing.name}. Creating as new character anyway.")

        # Create character
        character = Character(
            id=char_id,
            name=name,
            first_appearance=f"{book_id}:chapter_{chapter:03d}",
            **attributes
        )

        # Store in memory and database
        self.characters[char_id] = character
        self._save_character(character)

        logger.info(f"Added character: {name} (ID: {char_id})")
        return character

    def update_character(
        self,
        char_id: str,
        book_id: str,
        updates: Dict[str, Any]
    ) -> bool:
        """
        Update character information.

        Args:
            char_id: Character ID
            book_id: Book where update occurs
            updates: Dictionary of updates

        Returns:
            True if successful
        """
        if char_id not in self.characters:
            logger.error(f"Character {char_id} not found")
            return False

        character = self.characters[char_id]

        # Track development
        if 'development' in updates:
            character.development[book_id] = updates.pop('development')

        # Apply updates
        for key, value in updates.items():
            if hasattr(character, key):
                setattr(character, key, value)

        # Save to database
        self._save_character(character)

        logger.info(f"Updated character: {character.name}")
        return True

    def add_location(
        self,
        name: str,
        type: str,
        description: str,
        book_id: str,
        **attributes
    ) -> Location:
        """
        Add a new location to the series.

        Args:
            name: Location name
            type: Location type
            description: Location description
            book_id: Book where location appears
            **attributes: Additional attributes

        Returns:
            Location object
        """
        loc_id = self._generate_id('loc', name)

        location = Location(
            id=loc_id,
            name=name,
            type=type,
            description=description,
            first_mentioned=book_id,
            **attributes
        )

        self.locations[loc_id] = location
        self._save_location(location)

        logger.info(f"Added location: {name} (ID: {loc_id})")
        return location

    def add_event(
        self,
        name: str,
        description: str,
        book_id: str,
        chapter: int,
        participants: List[str] = None,
        **attributes
    ) -> Event:
        """
        Add a significant event.

        Args:
            name: Event name
            description: Event description
            book_id: Book ID
            chapter: Chapter number
            participants: List of character IDs
            **attributes: Additional attributes

        Returns:
            Event object
        """
        event_id = self._generate_id('event', f"{book_id}_{chapter}_{name}")

        event = Event(
            id=event_id,
            name=name,
            description=description,
            book_id=book_id,
            chapter=chapter,
            participants=participants or [],
            **attributes
        )

        self.events[event_id] = event
        self.timeline.append(event)
        self._save_event(event)

        logger.info(f"Added event: {name} (ID: {event_id})")
        return event

    def add_relationship(
        self,
        char1_id: str,
        char2_id: str,
        type: str,
        description: str,
        book_id: str
    ) -> Relationship:
        """
        Add a relationship between characters.

        Args:
            char1_id: First character ID
            char2_id: Second character ID
            type: Relationship type
            description: Relationship description
            book_id: Book where relationship established

        Returns:
            Relationship object
        """
        rel_id = self._generate_id('rel', f"{char1_id}_{char2_id}")

        relationship = Relationship(
            id=rel_id,
            character1_id=char1_id,
            character2_id=char2_id,
            type=type,
            description=description,
            start_book=book_id
        )

        self.relationships[rel_id] = relationship
        self._save_relationship(relationship)

        logger.info(f"Added relationship: {char1_id} <-> {char2_id} ({type})")
        return relationship

    def check_consistency(
        self,
        book_id: str,
        chapter_content: str
    ) -> List[Dict[str, Any]]:
        """
        Check chapter content for consistency violations.

        Args:
            book_id: Book ID
            chapter_content: Chapter text to check

        Returns:
            List of violations found
        """
        violations = []

        # Check character consistency
        for char_id, character in self.characters.items():
            if character.name in chapter_content:
                # Check if deceased character appears
                if character.status == "deceased":
                    violations.append({
                        'type': 'character_status',
                        'severity': 'high',
                        'description': f"Deceased character {character.name} appears in text",
                        'element_id': char_id
                    })

                # Check physical description consistency
                # (simplified - real implementation would use NLP)
                if character.appearance:
                    for feature, value in character.appearance.items():
                        # Check for contradictions
                        pass

        # Check location consistency
        for loc_id, location in self.locations.items():
            if location.name in chapter_content:
                if location.destroyed:
                    violations.append({
                        'type': 'location_status',
                        'severity': 'high',
                        'description': f"Destroyed location {location.name} appears in text",
                        'element_id': loc_id
                    })

        # Check timeline consistency
        # (would need more sophisticated date parsing)

        # Log violations
        for violation in violations:
            self._save_violation(violation, book_id)

        return violations

    def generate_world_bible(self) -> Dict[str, Any]:
        """
        Generate comprehensive world bible.

        Returns:
            Complete world bible as dictionary
        """
        world_bible = {
            'series_name': self.series_name,
            'generated_at': datetime.now().isoformat(),
            'statistics': {
                'total_characters': len(self.characters),
                'total_locations': len(self.locations),
                'total_events': len(self.events),
                'total_relationships': len(self.relationships),
            },
            'characters': {},
            'locations': {},
            'timeline': [],
            'relationships': {},
            'plot_threads': self.plot_threads
        }

        # Add characters (grouped by status)
        for status in ['active', 'deceased', 'missing']:
            chars = [c for c in self.characters.values() if c.status == status]
            if chars:
                world_bible['characters'][status] = [
                    asdict(char) for char in chars
                ]

        # Add locations (hierarchical)
        world_bible['locations'] = self._build_location_hierarchy()

        # Add timeline (chronological events)
        world_bible['timeline'] = [
            asdict(event) for event in sorted(
                self.timeline,
                key=lambda e: (e.book_id, e.chapter)
            )
        ]

        # Add relationships (grouped by type)
        for rel_type in ['family', 'romantic', 'friendship', 'enemy']:
            rels = [r for r in self.relationships.values() if r.type == rel_type]
            if rels:
                world_bible['relationships'][rel_type] = [
                    self._format_relationship(rel) for rel in rels
                ]

        # Save to file
        bible_path = self.workspace / f"{self.series_name}_world_bible.json"
        bible_path.write_text(json.dumps(world_bible, indent=2), encoding='utf-8')

        logger.info(f"Generated world bible: {bible_path}")
        return world_bible

    def get_character_arc(self, char_id: str) -> Dict[str, Any]:
        """
        Get complete character arc across series.

        Args:
            char_id: Character ID

        Returns:
            Character arc information
        """
        if char_id not in self.characters:
            return {}

        character = self.characters[char_id]

        arc = {
            'character': character.name,
            'first_appearance': character.first_appearance,
            'last_appearance': character.last_appearance,
            'status': character.status,
            'development': character.development,
            'relationships': [],
            'events': []
        }

        # Find relationships
        for rel in self.relationships.values():
            if rel.character1_id == char_id or rel.character2_id == char_id:
                arc['relationships'].append({
                    'type': rel.type,
                    'with': self.characters.get(
                        rel.character2_id if rel.character1_id == char_id else rel.character1_id,
                        {}
                    ).get('name', 'Unknown'),
                    'status': rel.status,
                    'evolution': rel.evolution
                })

        # Find events
        for event in self.events.values():
            if char_id in event.participants:
                arc['events'].append({
                    'name': event.name,
                    'book': event.book_id,
                    'chapter': event.chapter,
                    'description': event.description
                })

        return arc

    def _generate_id(self, prefix: str, value: str) -> str:
        """Generate unique ID."""
        hash_val = hashlib.md5(f"{prefix}_{value}".encode()).hexdigest()[:8]
        return f"{prefix}_{hash_val}"

    def _find_similar_character(self, name: str) -> Optional[Character]:
        """Find similar character by name."""
        name_lower = name.lower()
        for character in self.characters.values():
            if name_lower in character.name.lower() or character.name.lower() in name_lower:
                return character
            for alias in character.aliases:
                if name_lower == alias.lower():
                    return character
        return None

    def _build_location_hierarchy(self) -> Dict[str, Any]:
        """Build hierarchical location structure."""
        hierarchy = {}

        # Find root locations (no parent)
        roots = [loc for loc in self.locations.values() if not loc.contained_in]

        for root in roots:
            hierarchy[root.name] = {
                'id': root.id,
                'type': root.type,
                'description': root.description,
                'children': self._get_location_children(root.id)
            }

        return hierarchy

    def _get_location_children(self, parent_id: str) -> Dict[str, Any]:
        """Get child locations recursively."""
        children = {}
        for loc in self.locations.values():
            if loc.contained_in == parent_id:
                children[loc.name] = {
                    'id': loc.id,
                    'type': loc.type,
                    'description': loc.description,
                    'children': self._get_location_children(loc.id)
                }
        return children

    def _format_relationship(self, rel: Relationship) -> Dict[str, str]:
        """Format relationship for output."""
        char1 = self.characters.get(rel.character1_id, {})
        char2 = self.characters.get(rel.character2_id, {})

        return {
            'id': rel.id,
            'character1': getattr(char1, 'name', 'Unknown'),
            'character2': getattr(char2, 'name', 'Unknown'),
            'type': rel.type,
            'description': rel.description,
            'status': rel.status,
            'started': rel.start_book,
            'ended': rel.end_book
        }

    # Database operations
    def _save_character(self, character: Character):
        """Save character to database."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            INSERT OR REPLACE INTO characters (id, name, data, updated_at)
            VALUES (?, ?, ?, CURRENT_TIMESTAMP)
        """, (character.id, character.name, json.dumps(asdict(character))))

        conn.commit()
        conn.close()

    def _save_location(self, location: Location):
        """Save location to database."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            INSERT OR REPLACE INTO locations (id, name, type, data, updated_at)
            VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
        """, (location.id, location.name, location.type, json.dumps(asdict(location))))

        conn.commit()
        conn.close()

    def _save_event(self, event: Event):
        """Save event to database."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO events (id, name, book_id, chapter, timestamp, data)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (event.id, event.name, event.book_id, event.chapter,
              event.timestamp, json.dumps(asdict(event))))

        conn.commit()
        conn.close()

    def _save_relationship(self, relationship: Relationship):
        """Save relationship to database."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            INSERT OR REPLACE INTO relationships
            (id, character1_id, character2_id, type, data, updated_at)
            VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        """, (relationship.id, relationship.character1_id, relationship.character2_id,
              relationship.type, json.dumps(asdict(relationship))))

        conn.commit()
        conn.close()

    def _save_violation(self, violation: Dict[str, Any], book_id: str):
        """Save consistency violation to database."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        violation_id = self._generate_id('viol', str(violation))

        cursor.execute("""
            INSERT INTO violations (id, type, severity, description, book_id, element_id)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (violation_id, violation['type'], violation['severity'],
              violation['description'], book_id, violation.get('element_id')))

        conn.commit()
        conn.close()

    def _load_from_database(self):
        """Load existing data from database."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Load characters
        cursor.execute("SELECT data FROM characters")
        for row in cursor.fetchall():
            char_data = json.loads(row[0])
            character = Character(**char_data)
            self.characters[character.id] = character

        # Load locations
        cursor.execute("SELECT data FROM locations")
        for row in cursor.fetchall():
            loc_data = json.loads(row[0])
            location = Location(**loc_data)
            self.locations[location.id] = location

        # Load events
        cursor.execute("SELECT data FROM events ORDER BY book_id, chapter")
        for row in cursor.fetchall():
            event_data = json.loads(row[0])
            event = Event(**event_data)
            self.events[event.id] = event
            self.timeline.append(event)

        # Load relationships
        cursor.execute("SELECT data FROM relationships")
        for row in cursor.fetchall():
            rel_data = json.loads(row[0])
            relationship = Relationship(**rel_data)
            self.relationships[relationship.id] = relationship

        conn.close()

        logger.info(f"Loaded {len(self.characters)} characters, {len(self.locations)} locations, "
                   f"{len(self.events)} events, {len(self.relationships)} relationships")