#!/usr/bin/env python3
"""
Autonomous Quality Gate with Auto-Fix
Checks chapter quality and automatically fixes issues
"""

import re
import sys
import json
from pathlib import Path
from collections import Counter, defaultdict

# === FORBIDDEN PATTERNS ===
FORBIDDEN_WORDS = [
    "delve", "embark", "leverage", "harness", "unlock", "unveil",
    "illuminate", "elevate", "foster", "resonate", "endeavor", "unleash",
    "multifaceted", "intricate", "pivotal", "groundbreaking", "cutting-edge",
    "revolutionary", "transformative", "paramount", "seamless", "comprehensive",
    "holistic", "myriad", "plethora", "tapestry", "testament", "beacon",
    "robust", "nuanced", "underscore", "facilitates", "optimize", "synergy",
    "landscape", "realm", "journey", "navigate", "craft", "crafting"
]

FORBIDDEN_PHRASES = [
    r"shiver[s]?\s+(down|up|ran\s+down)\s+(the|her|his)\s+spine",
    r"breath\s+(caught|hitched)",
    r"heart\s+(skipped|hammered|pounded|raced)\s+(a\s+beat|in)",
    r"electricity\s+(crackled|sparked|shot)",
    r"(drowning|lost)\s+in\s+(her|his|their)\s+eyes",
    r"smoldering\s+gaze",
    r"piercing\s+(gaze|eyes)",
    r"set?\s+ablaze\s+with",
    r"heaving\s+bosom",
    r"alabaster\s+skin",
    r"\borbs\b",
    r"couldn'?t\s+help\s+but",
    r"found\s+(myself|himself|herself)",
    r"let\s+out\s+a\s+breath",
]

FILTER_PATTERNS = [
    (r"\b(she|he|they|I)\s+saw\s+", r"\1 watched as "),
    (r"\b(she|he|they|I)\s+heard\s+", r""),
    (r"\b(she|he|they|I)\s+felt\s+", r""),
    (r"\b(she|he|they|I)\s+noticed\s+", r""),
    (r"\b(she|he|they|I)\s+realized\s+", r""),
]

WEAK_MODIFIERS = ["very", "really", "quite", "rather", "somewhat", "slightly",
                  "a bit", "kind of", "sort of", "basically", "actually", "literally", "just"]


class QualityGate:
    def __init__(self, text, auto_fix=True):
        self.original_text = text
        self.text = text
        self.auto_fix = auto_fix
        self.fixes_applied = []
        self.issues = defaultdict(list)

    def check_forbidden_words(self):
        """Check and auto-fix forbidden words"""
        for word in FORBIDDEN_WORDS:
            # Match base form and common variations (s, ed, ing)
            # Handle -ing for words ending in 'e' (leverage -> leveraging)
            base = word.rstrip('e') if word.endswith('e') else word
            pattern = r'\b' + re.escape(word) + r'(?:[ds]|ed)?\b|\b' + re.escape(base) + r'ing\b'
            matches = list(re.finditer(pattern, self.text, re.IGNORECASE))

            if matches and self.auto_fix:
                # Replace with neutral alternative
                replacements = {
                    'delve': 'examine',
                    'embark': 'begin',
                    'leverage': 'use',
                    'unlock': 'reveal',
                    'unveil': 'reveal',
                    'illuminate': 'show',
                    'elevate': 'raise',
                    'foster': 'encourage',
                    'endeavor': 'attempt',
                    'robust': 'strong',
                    'nuanced': 'subtle',
                    'optimize': 'improve',
                }
                replacement = replacements.get(word.lower(), 'REMOVE')

                if replacement == 'REMOVE':
                    self.text = re.sub(pattern, '', self.text, flags=re.IGNORECASE)
                else:
                    self.text = re.sub(pattern, replacement, self.text, flags=re.IGNORECASE)

                self.fixes_applied.append(f"Replaced '{word}' with '{replacement}'")
            elif matches:
                for m in matches:
                    self.issues['forbidden_words'].append({
                        'word': word,
                        'position': m.start(),
                        'context': self.text[max(0, m.start()-30):m.end()+30]
                    })

    def check_forbidden_phrases(self):
        """Check and remove forbidden phrases"""
        for phrase_pattern in FORBIDDEN_PHRASES:
            matches = list(re.finditer(phrase_pattern, self.text, re.IGNORECASE))

            if matches and self.auto_fix:
                for match in reversed(matches):  # Reverse to maintain indices
                    # Replace with generic alternative
                    matched_text = match.group()

                    if 'breath' in matched_text.lower():
                        replacement = self._suggest_breath_alternative()
                    elif 'heart' in matched_text.lower():
                        replacement = self._suggest_heart_alternative()
                    elif 'shiver' in matched_text.lower():
                        replacement = "A chill ran through them"
                    elif 'eyes' in matched_text.lower():
                        replacement = "their gaze held"
                    else:
                        replacement = ""

                    self.text = self.text[:match.start()] + replacement + self.text[match.end():]
                    self.fixes_applied.append(f"Replaced purple prose: '{matched_text}' → '{replacement}'")
            elif matches:
                for m in matches:
                    self.issues['purple_prose'].append({
                        'phrase': m.group(),
                        'position': m.start()
                    })

    def check_filter_words(self):
        """Check and fix filter words (show don't tell)"""
        pronouns = r'\b(she|he|they|I)\s+'
        filters = ['saw', 'heard', 'felt', 'noticed', 'realized', 'knew',
                   'thought', 'wondered', 'watched', 'seemed', 'appeared']

        for word in filters:
            pattern = pronouns + word + r'\s+'
            matches = list(re.finditer(pattern, self.text, re.IGNORECASE))

            if matches and self.auto_fix:
                for match in reversed(matches):
                    # Remove the filter word and pronoun, leaving the object
                    pronoun = match.group(1)
                    # Just remove the filter construction
                    self.text = self.text[:match.start()] + self.text[match.end():]
                    self.fixes_applied.append(f"Removed filter word '{word}' from: {match.group()}")
            elif matches:
                for m in matches:
                    self.issues['filter_words'].append({
                        'word': word,
                        'match': m.group()
                    })

    def check_weak_modifiers(self):
        """Check and remove weak modifiers"""
        count = 0
        for modifier in WEAK_MODIFIERS:
            pattern = r'\b' + re.escape(modifier) + r'\b'
            matches = list(re.finditer(pattern, self.text, re.IGNORECASE))
            count += len(matches)

            if matches and self.auto_fix:
                for match in reversed(matches):
                    # Remove the modifier and extra space
                    self.text = self.text[:match.start()] + self.text[match.end():].lstrip()
                    self.fixes_applied.append(f"Removed weak modifier: '{modifier}'")

        word_count = len(self.text.split())
        ratio = count / max(word_count, 1)

        if ratio > 0.02 and not self.auto_fix:
            self.issues['weak_modifiers'].append({
                'count': count,
                'ratio': f"{ratio:.2%}"
            })

    def check_passive_voice(self):
        """Detect passive voice (reporting only, complex to auto-fix)"""
        passive_patterns = [
            r'\b(was|were)\s+\w+ed\b',
            r'\b(has|have|had)\s+been\s+\w+ed\b',
        ]

        passive_count = 0
        for pattern in passive_patterns:
            passive_count += len(re.findall(pattern, self.text, re.IGNORECASE))

        sentences = re.split(r'[.!?]+', self.text)
        sentence_count = len([s for s in sentences if s.strip()])

        ratio = passive_count / max(sentence_count, 1)

        if ratio > 0.15:
            self.issues['passive_voice'].append({
                'count': passive_count,
                'ratio': f"{ratio:.1%}",
                'threshold': '15%'
            })

    def check_repetitive_starts(self):
        """Check for sentences starting with same word"""
        sentences = re.split(r'[.!?]+', self.text)
        sentences = [s.strip() for s in sentences if s.strip()]

        streak_word = None
        streak_count = 0
        streak_start = 0

        for i, sentence in enumerate(sentences):
            words = sentence.split()
            if not words:
                continue
            first_word = words[0].lower()

            if first_word == streak_word:
                streak_count += 1
            else:
                if streak_count >= 3:
                    self.issues['repetitive_starts'].append({
                        'word': streak_word,
                        'count': streak_count,
                        'range': f"{streak_start+1}-{i}"
                    })
                streak_word = first_word
                streak_count = 1
                streak_start = i

        if streak_count >= 3:
            self.issues['repetitive_starts'].append({
                'word': streak_word,
                'count': streak_count,
                'range': f"{streak_start+1}-{len(sentences)}"
            })

    def check_sentence_variety(self):
        """Check sentence length variety"""
        sentences = re.split(r'[.!?]+', self.text)
        sentences = [s.strip() for s in sentences if s.strip()]

        if len(sentences) < 10:
            return

        lengths = [len(s.split()) for s in sentences]
        avg_length = sum(lengths) / len(lengths)
        variance = sum((l - avg_length) ** 2 for l in lengths) / len(lengths)
        std_dev = variance ** 0.5

        if avg_length < 8 or avg_length > 25:
            self.issues['sentence_length'].append({
                'average': f"{avg_length:.1f}",
                'target': '12-18 words'
            })

        if std_dev < 4:
            self.issues['sentence_variety'].append({
                'std_dev': f"{std_dev:.1f}",
                'message': 'Add sentence length variety'
            })

    def check_dialogue_ratio(self):
        """Check dialogue to prose ratio"""
        dialogue_matches = re.findall(r'"[^"]*"', self.text)
        dialogue_words = sum(len(d.split()) for d in dialogue_matches)
        total_words = len(self.text.split())

        ratio = dialogue_words / max(total_words, 1)

        if ratio < 0.15:
            self.issues['dialogue_ratio'].append({
                'ratio': f"{ratio:.1%}",
                'message': 'Consider adding more dialogue'
            })
        elif ratio > 0.60:
            self.issues['dialogue_ratio'].append({
                'ratio': f"{ratio:.1%}",
                'message': 'Consider adding more narrative'
            })

    def _suggest_breath_alternative(self):
        """Suggest alternative to breath caught/hitched"""
        alternatives = [
            "Their breath came short and fast",
            "Air caught in their lungs",
            "Breathing became difficult"
        ]
        return alternatives[0]

    def _suggest_heart_alternative(self):
        """Suggest alternative to heart hammered/pounded"""
        alternatives = [
            "Pulse thundered in their ears",
            "Their chest tightened",
            "Blood rushed through their veins"
        ]
        return alternatives[0]

    def run_all_checks(self):
        """Run all quality checks"""
        self.check_forbidden_words()
        self.check_forbidden_phrases()
        self.check_filter_words()
        self.check_weak_modifiers()
        self.check_passive_voice()
        self.check_repetitive_starts()
        self.check_sentence_variety()
        self.check_dialogue_ratio()

        # Determine pass/fail
        critical_issues = (
            len(self.issues['forbidden_words']) +
            len(self.issues['purple_prose'])
        )

        passed = critical_issues == 0

        return {
            'passed': passed,
            'fixed': self.auto_fix,
            'fixes_applied': len(self.fixes_applied),
            'fixes': self.fixes_applied,
            'remaining_issues': dict(self.issues),
            'total_issues': sum(len(v) for v in self.issues.values()),
            'word_count': len(self.text.split()),
            'fixed_text': self.text if self.auto_fix else None
        }


def main():
    if len(sys.argv) < 2:
        print(json.dumps({"error": "Usage: quality_gate.py <file> [--no-fix]"}))
        sys.exit(1)

    filepath = Path(sys.argv[1])
    auto_fix = '--no-fix' not in sys.argv

    if not filepath.exists():
        print(json.dumps({"error": f"File not found: {filepath}"}))
        sys.exit(1)

    text = filepath.read_text(encoding='utf-8')
    gate = QualityGate(text, auto_fix=auto_fix)
    results = gate.run_all_checks()

    # If auto-fix enabled and fixes were made, write back to file
    if auto_fix and results['fixes_applied'] > 0:
        filepath.write_text(results['fixed_text'], encoding='utf-8')
        results['file_updated'] = True

    print(json.dumps(results, indent=2))
    sys.exit(0 if results['passed'] else 1)


if __name__ == "__main__":
    main()
