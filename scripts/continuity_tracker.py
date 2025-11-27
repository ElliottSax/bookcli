#!/usr/bin/env python3
"""
Continuity Tracking System
Maintains story consistency across chapters
"""

import json
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any


class ContinuityTracker:
    def __init__(self, workspace_dir: Path):
        self.workspace = Path(workspace_dir)
        self.continuity_dir = self.workspace / "continuity"
        self.continuity_dir.mkdir(parents=True, exist_ok=True)

        # Initialize tracking files
        self.characters_file = self.continuity_dir / "characters.json"
        self.timeline_file = self.continuity_dir / "timeline.json"
        self.facts_file = self.continuity_dir / "facts.json"
        self.threads_file = self.continuity_dir / "threads.json"
        self.knowledge_file = self.continuity_dir / "knowledge.json"

        self._ensure_files()

    def _ensure_files(self):
        """Create empty tracking files if they don't exist"""
        if not self.characters_file.exists():
            self.characters_file.write_text(json.dumps({}, indent=2))
        if not self.timeline_file.exists():
            self.timeline_file.write_text(json.dumps({"events": []}, indent=2))
        if not self.facts_file.exists():
            self.facts_file.write_text(json.dumps({"facts": []}, indent=2))
        if not self.threads_file.exists():
            self.threads_file.write_text(json.dumps({"active": [], "resolved": []}, indent=2))
        if not self.knowledge_file.exists():
            self.knowledge_file.write_text(json.dumps({}, indent=2))

    def load_characters(self) -> Dict:
        """Load character data"""
        return json.loads(self.characters_file.read_text())

    def save_characters(self, data: Dict):
        """Save character data"""
        self.characters_file.write_text(json.dumps(data, indent=2))

    def update_character(self, name: str, updates: Dict):
        """Update or create character entry"""
        characters = self.load_characters()

        if name not in characters:
            characters[name] = {
                "name": name,
                "introduced_chapter": updates.get("chapter", 1),
                "physical_description": {},
                "personality": [],
                "relationships": {},
                "goals": [],
                "current_state": {},
                "arc_notes": []
            }

        # Merge updates
        for key, value in updates.items():
            if isinstance(value, dict):
                characters[name][key].update(value)
            elif isinstance(value, list):
                characters[name][key].extend(value)
            else:
                characters[name][key] = value

        self.save_characters(characters)
        return characters[name]

    def load_timeline(self) -> List[Dict]:
        """Load timeline events"""
        data = json.loads(self.timeline_file.read_text())
        return data.get("events", [])

    def add_timeline_event(self, chapter: int, event: str, time_marker: str = None):
        """Add event to timeline"""
        data = json.loads(self.timeline_file.read_text())
        data["events"].append({
            "chapter": chapter,
            "event": event,
            "time_marker": time_marker,
            "added": datetime.now().isoformat()
        })
        self.timeline_file.write_text(json.dumps(data, indent=2))

    def load_facts(self) -> List[str]:
        """Load established facts"""
        data = json.loads(self.facts_file.read_text())
        return data.get("facts", [])

    def add_fact(self, fact: str, chapter: int):
        """Add established fact"""
        data = json.loads(self.facts_file.read_text())
        data["facts"].append({
            "fact": fact,
            "established_chapter": chapter,
            "added": datetime.now().isoformat()
        })
        self.facts_file.write_text(json.dumps(data, indent=2))

    def load_threads(self) -> Dict:
        """Load plot threads"""
        return json.loads(self.threads_file.read_text())

    def add_thread(self, thread: str, chapter: int):
        """Add active plot thread"""
        data = self.load_threads()
        data["active"].append({
            "thread": thread,
            "introduced": chapter,
            "status": "active"
        })
        self.threads_file.write_text(json.dumps(data, indent=2))

    def resolve_thread(self, thread_text: str, chapter: int):
        """Mark thread as resolved"""
        data = self.load_threads()

        # Find and move to resolved
        for i, thread in enumerate(data["active"]):
            if thread_text in thread["thread"]:
                resolved = data["active"].pop(i)
                resolved["resolved_chapter"] = chapter
                resolved["status"] = "resolved"
                data["resolved"].append(resolved)
                break

        self.threads_file.write_text(json.dumps(data, indent=2))

    def update_character_knowledge(self, character: str, knowledge: str, chapter: int):
        """Track what characters know (prevent impossible knowledge)"""
        data = json.loads(self.knowledge_file.read_text())

        if character not in data:
            data[character] = []

        data[character].append({
            "knowledge": knowledge,
            "learned_chapter": chapter,
            "added": datetime.now().isoformat()
        })

        self.knowledge_file.write_text(json.dumps(data, indent=2))

    def verify_character_knowledge(self, character: str, knowledge_check: str, current_chapter: int) -> bool:
        """Verify if character could know something"""
        data = json.loads(self.knowledge_file.read_text())

        if character not in data:
            return False

        # Check if character has learned this or something related
        for entry in data[character]:
            if entry["learned_chapter"] <= current_chapter:
                if knowledge_check.lower() in entry["knowledge"].lower():
                    return True

        return False

    def get_context_for_chapter(self, chapter: int) -> Dict:
        """Get all relevant context for writing a chapter"""
        return {
            "characters": self.load_characters(),
            "recent_events": [e for e in self.load_timeline() if e["chapter"] >= chapter - 2],
            "active_threads": self.load_threads()["active"],
            "established_facts": self.load_facts()[-20:],  # Last 20 facts
            "character_knowledge": json.loads(self.knowledge_file.read_text())
        }

    def check_consistency(self, chapter_text: str, chapter_num: int) -> List[Dict]:
        """Check chapter for continuity issues"""
        issues = []
        characters = self.load_characters()

        # Check for character name consistency
        for char_name in characters.keys():
            # Simple check - could be more sophisticated
            if char_name.lower() in chapter_text.lower():
                # Character appears - verify against their last known state
                pass

        # Check for contradicting established facts
        facts = self.load_facts()
        # This would need NLP for real checking, simplified here

        return issues

    def generate_summary(self) -> Dict:
        """Generate summary of current story state"""
        characters = self.load_characters()
        threads = self.load_threads()
        timeline = self.load_timeline()

        return {
            "total_characters": len(characters),
            "main_characters": [c for c in characters.values() if c.get("importance") == "main"],
            "active_threads": len(threads["active"]),
            "resolved_threads": len(threads["resolved"]),
            "total_events": len(timeline),
            "last_event": timeline[-1] if timeline else None
        }


def main():
    if len(sys.argv) < 3:
        print(json.dumps({"error": "Usage: continuity_tracker.py <workspace> <command> [args...]"}))
        sys.exit(1)

    workspace = Path(sys.argv[1])
    command = sys.argv[2]

    tracker = ContinuityTracker(workspace)

    if command == "update_character":
        # continuity_tracker.py workspace update_character "Name" '{"physical_description": {...}}'
        name = sys.argv[3]
        updates = json.loads(sys.argv[4])
        result = tracker.update_character(name, updates)
        print(json.dumps(result, indent=2))

    elif command == "add_event":
        # continuity_tracker.py workspace add_event 5 "Event description"
        chapter = int(sys.argv[3])
        event = sys.argv[4]
        tracker.add_timeline_event(chapter, event)
        print(json.dumps({"success": True, "event": event}))

    elif command == "add_fact":
        chapter = int(sys.argv[3])
        fact = sys.argv[4]
        tracker.add_fact(fact, chapter)
        print(json.dumps({"success": True}))

    elif command == "add_thread":
        chapter = int(sys.argv[3])
        thread = sys.argv[4]
        tracker.add_thread(thread, chapter)
        print(json.dumps({"success": True}))

    elif command == "resolve_thread":
        chapter = int(sys.argv[3])
        thread = sys.argv[4]
        tracker.resolve_thread(thread, chapter)
        print(json.dumps({"success": True}))

    elif command == "get_context":
        chapter = int(sys.argv[3])
        context = tracker.get_context_for_chapter(chapter)
        print(json.dumps(context, indent=2))

    elif command == "summary":
        summary = tracker.generate_summary()
        print(json.dumps(summary, indent=2))

    else:
        print(json.dumps({"error": f"Unknown command: {command}"}))
        sys.exit(1)


if __name__ == "__main__":
    main()
