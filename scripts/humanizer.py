#!/usr/bin/env python3
"""
Humanizer Module - Transforms competent AI prose into human-voiced fiction

Applies authorial voice, emotional depth, thematic subtlety, and controlled variance
to make AI-generated fiction indistinguishable from human writing.
"""

import re
import yaml
import random
from pathlib import Path
from dataclasses import dataclass
from typing import List, Dict, Tuple

@dataclass
class VoiceProfile:
    """Authorial voice configuration"""
    author_name: str
    personality: str
    primary_obsessions: Dict
    verbal_patterns: Dict
    prose_craft: Dict
    quality_targets: Dict

class Humanizer:
    """Transforms competent AI prose into human-voiced fiction"""

    def __init__(self, config_dir="config"):
        """Initialize with configuration files"""
        self.config_dir = Path(config_dir)

        # Load configurations
        self.voice_config = self._load_yaml('authorial_voice.yaml')
        self.emotion_config = self._load_yaml('emotional_depth.yaml')
        self.theme_config = self._load_yaml('thematic_subtlety.yaml')

        # Create voice profile
        self.voice = VoiceProfile(
            author_name=self.voice_config['voice_profile']['author_name'],
            personality=self.voice_config['voice_profile']['personality'],
            primary_obsessions=self.voice_config['primary_obsessions'],
            verbal_patterns=self.voice_config['verbal_patterns'],
            prose_craft=self.voice_config['prose_craft'],
            quality_targets=self.voice_config['quality_targets']
        )

    def _load_yaml(self, filename):
        """Load YAML configuration file"""
        path = self.config_dir / filename
        with open(path, 'r') as f:
            return yaml.safe_load(f)

    def apply_to_chapter(self, chapter_text: str, chapter_num: int) -> str:
        """
        Main transformation pipeline

        Args:
            chapter_text: Raw generated chapter text
            chapter_num: Chapter number (affects obsession selection)

        Returns:
            Humanized chapter text
        """
        print(f"Humanizing Chapter {chapter_num}...")

        # 1. Apply authorial obsessions
        chapter_text = self._inject_obsessions(chapter_text, chapter_num)

        # 2. Deepen emotional specificity
        chapter_text = self._deepen_emotions(chapter_text)

        # 3. Reduce thematic explicitness
        chapter_text = self._soften_themes(chapter_text)

        # 4. Apply voice patterns
        chapter_text = self._apply_voice_patterns(chapter_text)

        # 5. Introduce minor imperfections (rarely)
        if random.random() < 0.15:  # 15% of chapters
            chapter_text = self._add_subtle_inconsistency(chapter_text, chapter_num)

        return chapter_text

    def _inject_obsessions(self, text: str, chapter_num: int) -> str:
        """Add recurring authorial obsessions"""

        # Select 1-2 obsessions to emphasize this chapter
        obsessions = self.voice.primary_obsessions
        active_obsessions = []

        # Hands obsession (35% frequency)
        if random.random() < 0.35:
            active_obsessions.append('hands_as_identity')

        # Magic sensation (40% frequency)
        if random.random() < 0.40:
            active_obsessions.append('magic_as_physical_sensation')

        # Philosophical paradox (25% frequency)
        if random.random() < 0.25:
            active_obsessions.append('philosophical_paradox')

        # Apply each active obsession
        for obsession_name in active_obsessions:
            if obsession_name == 'hands_as_identity':
                text = self._add_hand_imagery(text)
            elif obsession_name == 'magic_as_physical_sensation':
                text = self._enhance_magic_sensation(text)
            elif obsession_name == 'philosophical_paradox':
                text = self._embed_paradox(text)

        return text

    def _add_hand_imagery(self, text: str) -> str:
        """Add hand descriptions and imagery"""

        # Find opportunities to add hand descriptions
        # Look for character action sentences

        # Pattern: Character looked/turned/moved
        pattern = r'(Marcus|Lily|Dmitri|Kira|Evan) (looked|turned|moved|stopped|walked)'

        def add_hand_detail(match):
            character = match.group(1)
            action = match.group(2)

            # 30% chance to add hand detail
            if random.random() < 0.30:
                hand_details = [
                    f"{character} {action}, hands clenched.",
                    f"{character}'s hands trembled. {character.split()[0]} {action}.",
                    f"{character} looked at {('his' if character == 'Marcus' or character == 'Dmitri' or character == 'Evan' else 'her')} hands, then {action}.",
                ]
                return random.choice(hand_details)

            return match.group(0)

        text = re.sub(pattern, add_hand_detail, text)

        # Add hand examination during stress
        # Pattern: Character + emotion word nearby
        stress_pattern = r'(Marcus|Lily) (.{0,50})(scared|afraid|worried|uncertain|nervous)'

        def add_hand_examination(match):
            character = match.group(1)
            middle = match.group(2)
            emotion = match.group(3)

            # Add hand check
            insertion = f"\n\n{character} looked at {('his' if character == 'Marcus' else 'her')} hands. "

            # Add detail based on character
            if character == "Marcus":
                details = [
                    "The binding mark pulsed faintly. ",
                    "Marked and scarred. ",
                    "Kid hands doing impossible things. "
                ]
            else:  # Lily
                details = [
                    "Silver scars caught the light. ",
                    "Pianist fingers, now marked. ",
                    "They'd stopped shaking. "
                ]

            insertion += random.choice(details)

            return insertion + character + middle + emotion

        # Only apply to some instances
        if text.count('Marcus') > 3 or text.count('Lily') > 3:
            text = re.sub(stress_pattern, add_hand_examination, text, count=1)

        return text

    def _enhance_magic_sensation(self, text: str) -> str:
        """Enhance magic descriptions with physical sensation"""

        # Find magic-related sentences
        magic_patterns = [
            r'(Marcus|Lily|Dmitri|Kira|Evan) channeled',
            r'(magic|energy|power) flowed',
            r'(manifested|created|summoned)',
        ]

        sensory_vocab = self.voice.primary_obsessions['magic_as_physical_sensation']['sensory_vocabulary']

        for pattern in magic_patterns:
            matches = list(re.finditer(pattern, text, re.IGNORECASE))

            for match in matches:
                # Find sentence containing this match
                start = text.rfind('.', 0, match.start()) + 1
                end = text.find('.', match.end()) + 1
                sentence = text[start:end].strip()

                # Check if already enhanced (contains temperature/texture words)
                already_enhanced = any(
                    word in sentence.lower()
                    for word_list in sensory_vocab.values()
                    for word in word_list
                )

                if not already_enhanced and random.random() < 0.50:
                    # Add sensory detail
                    enhancement = self._create_magic_sensation_detail()
                    # Insert after the sentence
                    text = text.replace(sentence, sentence + " " + enhancement)

        return text

    def _create_magic_sensation_detail(self) -> str:
        """Generate magic sensation description"""

        sensory_vocab = self.voice.primary_obsessions['magic_as_physical_sensation']['sensory_vocabulary']

        templates = [
            f"His channels {random.choice(sensory_vocab['pain'])}.",
            f"The energy felt {random.choice(sensory_vocab['texture'])}.",
            f"{random.choice(sensory_vocab['temperature'].copy()).capitalize()} spread through his marked palm.",
            f"Magic wanted to {random.choice(['open', 'split', 'tear'])} him apart from inside.",
        ]

        return random.choice(templates)

    def _embed_paradox(self, text: str) -> str:
        """Embed philosophical paradoxes"""

        paradoxes = self.voice.primary_obsessions['philosophical_paradox']['core_paradoxes']

        # Look for decision points or resolutions
        decision_patterns = [
            r'(Marcus|Lily|Dmitri) (chose|decided|selected)',
            r'(victory|success|win)',
            r'(solved|fixed|healed)',
        ]

        for pattern in decision_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                # 20% chance to add paradox
                if random.random() < 0.20:
                    # Add paradoxical element
                    paradox_insertion = self._create_paradox_statement()

                    # Find good insertion point (after paragraph)
                    paragraphs = text.split('\n\n')
                    if len(paragraphs) > 3:
                        insert_pos = random.randint(len(paragraphs)//2, len(paragraphs)-1)
                        paragraphs.insert(insert_pos, paradox_insertion)
                        text = '\n\n'.join(paragraphs)

                break  # Only one paradox per chapter

        return text

    def _create_paradox_statement(self) -> str:
        """Generate paradoxical statement"""

        templates = [
            "Saving them. Destroying who they'd been.\n\nBoth true.",
            "The right choice. The wrong outcome.\n\nYes.",
            "Freedom felt like loss. Loss felt like freedom.\n\nMarcus couldn't tell which he'd given them.",
            "He'd won. He'd failed.\n\nSomehow both.",
        ]

        return random.choice(templates)

    def _deepen_emotions(self, text: str) -> str:
        """Replace generic emotions with specific sensory memories"""

        # Detect generic emotion statements
        generic_patterns = self.emotion_config['generic_emotion_patterns']

        for pattern in generic_patterns:
            matches = list(re.finditer(pattern, text, re.IGNORECASE))

            # Process matches in reverse order to preserve positions
            for match in reversed(matches):
                # Extract emotion type
                emotion_word = match.group(1) if match.lastindex >= 1 else 'afraid'

                # Map to emotion category
                emotion_category = self._map_to_emotion_category(emotion_word)

                if emotion_category and emotion_category in self.emotion_config['emotions']:
                    # Generate specific version
                    specific_version = self._create_specific_emotion(
                        emotion_category,
                        text,
                        match
                    )

                    # Replace only this specific match by position
                    text = text[:match.start()] + specific_version + text[match.end():]

        return text

    def _map_to_emotion_category(self, emotion_word: str) -> str:
        """Map emotion word to category"""

        mapping = {
            'sad': 'grief',
            'afraid': 'fear',
            'scared': 'fear',
            'nervous': 'fear',
            'worried': 'fear',
            'angry': 'anger',
            'happy': 'hope',
            'excited': 'hope',
        }

        return mapping.get(emotion_word.lower())

    def _create_specific_emotion(self, category: str, full_text: str, match) -> str:
        """Create specific emotion description"""

        emotion_data = self.emotion_config['emotions'][category]

        # Get character name from context
        character = 'Marcus'  # Default
        for name in ['Marcus', 'Lily', 'Dmitri', 'Kira', 'Evan']:
            if name in full_text[max(0, match.start()-100):match.start()+100]:
                character = name
                break

        # Build specific version using template
        physical = random.choice(emotion_data['physical_sensations'])
        action = random.choice(emotion_data['character_actions'])

        # Use memory anchor if available
        if emotion_data.get('memory_anchors') and random.random() < 0.60:
            memory = random.choice(emotion_data['memory_anchors'])
            specific = f"{character}'s {physical} {memory}. {character.split()[0]} {action}."
        else:
            specific = f"{character}'s {physical}. {character.split()[0]} {action}."

        return specific

    def _soften_themes(self, text: str) -> str:
        """Remove explicit theme statements, replace with implications"""

        # Detect heavy-handed theme statements
        heavy_patterns = self.theme_config['heavy_handed_patterns']

        for pattern in heavy_patterns:
            matches = list(re.finditer(pattern, text, re.IGNORECASE))

            for match in matches:
                # Find full sentence
                start = text.rfind('.', 0, match.start()) + 1
                end = text.find('.', match.end()) + 1
                sentence = text[start:end].strip()

                # Replace with subtle version
                subtle_version = self._create_subtle_theme_moment()

                # Replace sentence
                text = text.replace(sentence + '.', subtle_version)

        return text

    def _create_subtle_theme_moment(self) -> str:
        """Create subtle thematic moment"""

        templates = [
            "Lily looked at her scars. They'd stopped hurting.",
            "Marcus didn't answer.\n\nSome questions didn't have answers.",
            "He'd chosen. That would have to be enough.",
            "Both right. Both wrong.\n\nBoth paid a price.",
        ]

        return random.choice(templates)

    def _apply_voice_patterns(self, text: str) -> str:
        """Apply sentence-level voice patterns"""

        # Add fragment sentences (2-3 per chapter)
        text = self._add_fragments(text, count=random.randint(2, 3))

        # Add "Not X. Y." constructions (2-3 per chapter)
        text = self._add_not_x_y_pattern(text, count=random.randint(2, 3))

        # Add single-word paragraphs (0-1 per chapter)
        if random.random() < 0.50:
            text = self._add_single_word_paragraph(text)

        return text

    def _add_fragments(self, text: str, count: int) -> str:
        """Add fragment sentences for rhythm"""

        # Find sentences with conjunctions that can be split
        # Pattern: text + " and " + short phrase + punctuation
        pattern = r'([^.!?]+)\s+and\s+([^.!?]{1,30})([.!?])'

        matches = list(re.finditer(pattern, text))

        # Limit to count replacements
        replacements_made = 0
        for match in matches:
            if replacements_made >= count:
                break

            first_part = match.group(1)
            second_part = match.group(2)
            punct = match.group(3)

            # Only create fragment if second part is short (4 words or less)
            if len(second_part.split()) <= 4:
                # Create fragment: "first. Second."
                replacement = f"{first_part}. {second_part.strip().capitalize()}{punct}"
                text = text.replace(match.group(0), replacement, 1)
                replacements_made += 1

        return text

    def _add_not_x_y_pattern(self, text: str, count: int) -> str:
        """Add 'Not X. Y.' constructions"""

        # Find adjectives to negate
        # Pattern: "He felt X" → "Not X. Y."
        pattern = r'(Marcus|Lily|Dmitri) (felt|was|seemed) (\w+)'

        matches = list(re.finditer(pattern, text))

        if matches and count > 0:
            match = random.choice(matches)
            adjective = match.group(3)
            character = match.group(1)

            # Create not-X-Y version
            alternatives = {
                'afraid': 'Not fear. Recognition.',
                'tired': 'Not tired. Exhausted. Bone-deep.',
                'angry': 'Not anger. Frustration. The kind that had nowhere to go.',
                'happy': 'Not happy. Relief. The kind that made you want to cry.',
            }

            if adjective.lower() in alternatives:
                replacement = alternatives[adjective.lower()]
                text = text.replace(match.group(0), replacement, 1)

        return text

    def _add_single_word_paragraph(self, text: str) -> str:
        """Add single-word paragraph for emphasis"""

        emphasis_words = ['Silence.', 'Nothing.', 'Pain.', 'Yes.', 'No.', 'Failed.', 'Succeeded.']

        # Find dramatic moment
        dramatic_patterns = [
            'screamed',
            'collapsed',
            'died',
            'won',
            'lost',
        ]

        for pattern in dramatic_patterns:
            if pattern in text.lower():
                # Find sentence with pattern
                match = re.search(r'[^.!?]*' + pattern + r'[^.!?]*[.!?]', text, re.IGNORECASE)
                if match:
                    # Add emphasis word after
                    insertion = '\n\n' + random.choice(emphasis_words) + '\n\n'
                    pos = match.end()
                    text = text[:pos] + insertion + text[pos:]
                    break

        return text

    def _add_subtle_inconsistency(self, text: str, chapter_num: int) -> str:
        """Introduce minor human-like errors (rarely)"""

        inconsistency_types = [
            'measurement_drift',
            'detail_simplification',
        ]

        chosen_type = random.choice(inconsistency_types)

        if chosen_type == 'measurement_drift':
            # "twenty keys" → "maybe eighteen"
            # "three days" → "nearly a week"
            number_pattern = r'\b(twenty|thirty|fifteen|ten|three|four|five)\b'
            match = re.search(number_pattern, text, re.IGNORECASE)
            if match:
                original = match.group(1)
                alternatives = {
                    'twenty': 'maybe eighteen',
                    'three': 'nearly a week',
                    'fifteen': 'dozen or so',
                }
                if original.lower() in alternatives:
                    text = text.replace(match.group(0), alternatives[original.lower()], 1)

        elif chosen_type == 'detail_simplification':
            # "seventeen windows" → "dozens of windows"
            specific_pattern = r'\b(seventeen|eighteen|nineteen|twenty-three)\s+(\w+)'
            match = re.search(specific_pattern, text, re.IGNORECASE)
            if match:
                item = match.group(2)
                text = text.replace(match.group(0), f'dozens of {item}', 1)

        return text

def main():
    """Humanize a chapter file or test on sample text"""
    import sys

    if len(sys.argv) >= 3:
        # File mode: humanizer.py <file_path> <chapter_num>
        file_path = sys.argv[1]
        chapter_num = int(sys.argv[2])

        with open(file_path, 'r') as f:
            original_text = f.read()

        print(f"Humanizing Chapter {chapter_num}...")

        humanizer = Humanizer()
        humanized = humanizer.apply_to_chapter(original_text, chapter_num)

        # Write back to file
        with open(file_path, 'w') as f:
            f.write(humanized)

        print(f"✓ Chapter {chapter_num} humanized successfully")
        print(f"  File: {file_path}")

    else:
        # Sample mode
        sample_text = """
        Marcus walked to the Mender wing. He needed to see Evan about his channels.
        They still hurt from the mission. Lily was there too, recovering. He felt sad
        about what happened to her.

        Evan checked his channels and said they were healing. Marcus would be able to
        channel again soon. That was good news.

        Marcus learned that sometimes healing isn't possible and you have to make hard choices.
        """

        humanizer = Humanizer()

        print("BEFORE HUMANIZATION:")
        print("="*60)
        print(sample_text)

        print("\n\nAFTER HUMANIZATION:")
        print("="*60)
        humanized = humanizer.apply_to_chapter(sample_text, chapter_num=1)
        print(humanized)

if __name__ == '__main__':
    main()
