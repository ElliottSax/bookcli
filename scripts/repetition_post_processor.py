#!/usr/bin/env python3
"""
Repetition Post-Processor for Fiction

Detects and removes repetitive patterns, AI-isms, and quality issues
from LLM-generated fiction content.

Ported from book system and enhanced for fiction/novel generation.
Based on research from:
- https://arxiv.org/abs/2512.04419 (Solving LLM Repetition Problem in Production)
"""

import re
import logging
from typing import List, Tuple, Dict, Optional
from collections import Counter


class RepetitionPostProcessor:
    """
    Post-processor to clean up LLM-generated fiction by removing:
    1. AI-isms and overused phrases common in LLM output
    2. Repeated phrases and sentences
    3. Purple prose and melodramatic language
    4. Weak/passive writing patterns
    5. Telling instead of showing markers
    """

    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger(__name__)

        # AI-ism replacements optimized for fiction (regex pattern -> replacement)
        self.ai_ism_replacements = [
            # === FICTION-SPECIFIC AI-ISMS ===
            # Purple prose and melodrama
            (r"\ba (?:deep|profound) (?:sense|feeling) of\b", ""),
            (r"\bwash(?:ed)? over (?:him|her|them)\b", "hit"),
            (r"\bcrash(?:ed)? (?:over|through) (?:him|her|them)\b", "struck"),
            (r"\bthreaten(?:ed|ing)? to (?:consume|overwhelm)\b", "nearly overwhelming"),
            (r"\bevery fiber of (?:his|her|their) being\b", "completely"),
            (r"\bin that (?:single )?moment\b", "then"),
            (r"\btime (?:seemed to )?(?:stand|stood) still\b", "everything paused"),
            (r"\bthe world (?:seemed to )?(?:fade|fall) away\b", "nothing else mattered"),
            (r"\bheart (?:pounded|hammered|raced) (?:in|against) (?:his|her|their) chest\b", "pulse quickened"),
            (r"\bblood (?:ran|went) cold\b", "froze"),
            (r"\bbreath (?:caught|hitched) in (?:his|her|their) throat\b", "breath caught"),
            (r"\beyes (?:widened|went wide) (?:in|with) (?:shock|surprise|horror)\b", "stared"),
            (r"\bstomach (?:dropped|sank|churned)\b", "felt sick"),
            (r"\bweight of the world\b", "heavy burden"),
            (r"\bdeafening silence\b", "silence"),
            (r"\bpalpable tension\b", "tension"),
            (r"\bunspoken words hung in the air\b", "neither spoke"),
            (r"\btime (?:stretched|crawled)\b", "seconds passed slowly"),

            # Overused emotional tells
            (r"\bcouldn't help but (?:feel|think|wonder)\b", "felt"),
            (r"\bfound (?:himself|herself|themselves) (?:thinking|wondering|feeling)\b", "thought"),
            (r"\bdidn't know (?:what|how) to (?:feel|think)\b", "was confused"),
            (r"\ba mix(?:ture)? of (?:emotions?|feelings?)\b", "conflicting feelings"),
            (r"\bcomplex (?:emotions?|feelings?)\b", "mixed feelings"),
            (r"\bswirl(?:ing)? (?:emotions?|feelings?|thoughts?)\b", "racing thoughts"),
            (r"\bwhirlwind of (?:emotions?|feelings?)\b", "overwhelming feelings"),

            # Weak action verbs - strengthen
            (r"\bseemed to\b", ""),
            (r"\bappeared to\b", ""),
            (r"\bbegan to\b", ""),
            (r"\bstarted to\b", ""),
            (r"\bproceeded to\b", ""),
            (r"\bcontinued to\b", "kept"),
            (r"\bmanaged to\b", ""),
            (r"\battempted to\b", "tried to"),

            # Adverb overuse
            (r"\bsuddenly,?\s*", ""),
            (r"\b(?:very|really|quite|rather|extremely|incredibly|absolutely) ", ""),
            (r"\bslowly\b", ""),  # Often unnecessary
            (r"\bquickly\b", "fast"),
            (r"\bimmediately\b", "at once"),

            # === GENERAL AI-ISMS ===
            # Opening cliches
            (r"[Ii]n today'?s fast-paced world,?\s*", ""),
            (r"[Ll]et'?s dive in\.?\s*", ""),
            (r"[Ww]ithout further ado,?\s*", ""),

            # Overused verbs
            (r"\b[Ll]everage[sd]?\b", "use"),
            (r"\b[Ll]everaging\b", "using"),
            (r"\b[Uu]tilize[sd]?\b", "use"),
            (r"\b[Uu]tilizing\b", "using"),
            (r"\b[Dd]elve[sd]?\b", "look"),
            (r"\b[Dd]elving\b", "looking"),
            (r"\b[Ee]mbark(?:ed|ing)? on\b", "start"),
            (r"\b[Uu]nlock(?:ed|ing)?\b", "find"),
            (r"\b[Hh]arness(?:ed|ing)?\b", "use"),
            (r"\b[Ff]oster(?:ed|ing|s)?\b", "encourage"),
            (r"\b[Nn]urture[sd]?\b", "support"),
            (r"\b[Nn]urturing\b", "supporting"),
            (r"\b[Cc]ultivate[sd]?\b", "grow"),
            (r"\b[Cc]ultivating\b", "growing"),
            (r"\b[Ee]mpower(?:ed|ing|s)?\b", "enable"),
            (r"\b[Oo]ptimize[sd]?\b", "improve"),
            (r"\b[Oo]ptimizing\b", "improving"),
            (r"\b[Ss]treamline[sd]?\b", "simplify"),
            (r"\b[Rr]evolutionize[sd]?\b", "change"),
            (r"\b[Tt]ransform(?:ed|ing|s)?\b", "change"),
            (r"\b[Ee]levate[sd]?\b", "raise"),
            (r"\b[Aa]mplif(?:y|ied|ies|ying)\b", "increase"),

            # Overused nouns
            (r"\b[Jj]ourney\b", "path"),
            (r"\b[Tt]apestry\b", "pattern"),
            (r"\b[Bb]eacon\b", "light"),
            (r"\b[Cc]atalyst\b", "spark"),
            (r"\b[Cc]ornerstone\b", "foundation"),
            (r"\b[Nn]exus\b", "link"),
            (r"\b[Pp]aradigm\b", "model"),
            (r"\b[Rr]ealm\b", "world"),
            (r"\b[Ll]andscape\b", "scene"),
            (r"\b[Tt]estament to\b", "proof of"),
            (r"\b[Ee]pitome\b", "example"),

            # Filler phrases
            (r"[Ii]t'?s important to note that\s*", ""),
            (r"[Ii]t should be noted that\s*", ""),
            (r"[Aa]s we all know,?\s*", ""),
            (r"[Nn]eedless to say,?\s*", ""),
            (r"[Aa]t the end of the day,?\s*", ""),
            (r"[Ii]n a nutshell,?\s*", ""),
            (r"[Tt]he fact of the matter is,?\s*", ""),
            (r"[Ii]t goes without saying,?\s*", ""),

            # === WIKIPEDIA AI TELLS (2024-2025) ===
            # "Not X, but Y" pattern - THE BIGGEST AI TELL
            (r"\bnot as ([^,]+), but as ([^.]+)", r"like \2"),
            (r"\bnot just ([^,]+), but ([^.]+)", r"\2"),
            (r"\bnot merely ([^,]+), but ([^.]+)", r"\2"),
            (r"\bnot simply ([^,]+), but ([^.]+)", r"\2"),
            (r"\bnot only ([^,]+), but (?:also )?([^.]+)", r"both \1 and \2"),

            # "It wasn't X—it was Y" contrast pattern
            (r"[Ii]t wasn'?t ([^—–-]+)[—–-]+it was ([^.]+)", r"It was \2"),
            (r"[Ii]t wasn'?t ([^,]+), it was ([^.]+)", r"It was \2"),
            (r"[Ss]he wasn'?t ([^—–-]+)[—–-]+she was ([^.]+)", r"She was \2"),
            (r"[Hh]e wasn'?t ([^—–-]+)[—–-]+he was ([^.]+)", r"He was \2"),
            (r"[Tt]his wasn'?t ([^—–-]+)[—–-]+(?:it|this) was ([^.]+)", r"This was \2"),

            # "Not X. Y." sentence fragment pairs (dramatic false emphasis)
            # These need careful handling - flag for manual review or combine
            (r"Not (\w+)\. (\w+)\.", r"\2."),  # "Not random. Insistent." -> "Insistent."
            (r"Not (\w+)\. ([A-Z])", r"\2"),  # "Not fear. Focus." -> "Focus."

            # False biology/impossible descriptions
            (r"\b(?:watched|stared|gazed),? unblinking\b", "stared"),
            (r"\beyes[,]? unblinking\b", "fixed stare"),
            (r"\bunblinking (?:eyes|gaze|stare)\b", "steady gaze"),
            (r"\bwithout blinking\b", "steadily"),
            (r"\bheld (?:his|her|their) breath\b", "tensed"),  # Often overused

            # Inflated symbolism (Wikipedia top offenders)
            (r"\bstands? as a testament\b", "shows"),
            (r"\bserves? as a testament\b", "proves"),
            (r"\bis a testament to\b", "shows"),
            (r"\bplays? a (?:vital|significant|crucial|important) role\b", "matters"),
            (r"\bunderscores? (?:its|the) importance\b", "shows its value"),
            (r"\bcontinues? to captivate\b", "still interests"),
            (r"\bleaves? a lasting (?:impact|impression)\b", "affects"),
            (r"\bwatershed moment\b", "turning point"),
            (r"\bkey turning point\b", "turning point"),
            (r"\bdeeply rooted\b", "rooted"),
            (r"\bprofound (?:heritage|impact|effect)\b", "deep \1"),
            (r"\bsteadfast (?:dedication|commitment)\b", "firm \1"),
            (r"\bsolidifies\b", "confirms"),

            # Promotional/breathless language
            (r"\brich cultural (?:heritage|tapestry)\b", "culture"),
            (r"\brich history\b", "history"),
            (r"\bbreathtaking\b", "impressive"),
            (r"\bstunning (?:natural )?beauty\b", "beauty"),
            (r"\benduring legacy\b", "legacy"),
            (r"\blasting legacy\b", "legacy"),
            (r"\bmust-(?:visit|see)\b", "notable"),
            (r"\biconic\b", "famous"),

            # Editorializing phrases
            (r"[Ii]t'?s (?:important|worth|interesting) to (?:note|remember|consider) that\s*", ""),
            (r"[Nn]o (?:discussion|account) would be complete without\s*", ""),
            (r"[Ii]n this article,?\s*", ""),

            # Overused transitions (Wikipedia flagged) - only at sentence start
            (r"(?:^|\. )[Mm]oreover,?\s+", ". "),
            (r"(?:^|\. )[Ff]urthermore,?\s+", ". "),
            (r"(?:^|\. )[Aa]dditionally,?\s+", ". Also, "),
            (r"(?:^|\. )[Ii]n addition,?\s+", ". Also, "),
            (r"(?:^|\. )[Oo]n the other hand,?\s+", ". But "),
            (r"(?:^|\. )[Ii]n contrast,?\s+", ". But "),
            (r"(?:^|\. )[Hh]owever,?\s+", ". But "),
            (r"(?:^|\. )[Nn]evertheless,?\s+", ". Still, "),
            (r"(?:^|\. )[Nn]onetheless,?\s+", ". Still, "),
            # Mid-sentence however - just remove
            (r",\s*however,\s*", ", "),

            # Superficial -ing analysis words
            (r"\b(?:thereby |thus )?ensuring\b", "to ensure"),
            (r"\bhighlighting\b", "showing"),
            (r"\bemphasizing\b", "stressing"),
            (r"\breflecting\b", "showing"),
            (r"\bunderscoring\b", "showing"),
            (r"\bexemplifying\b", "showing"),
            (r"\bdemonstrating\b", "showing"),
            (r"\bshowcasing\b", "showing"),

            # Vague attribution (lazy AI hedging)
            (r"\b[Ii]ndustry (?:reports?|experts?) (?:suggest|indicate)\b", "some say"),
            (r"\b[Oo]bservers have (?:cited|noted)\b", "some note"),
            (r"\b[Ss]ome critics argue\b", "critics say"),
            (r"\b[Mm]any (?:believe|argue|say)\b", "some think"),

            # Em-dash overuse (convert to commas or remove)
            (r"\s*—\s*", ", "),
            (r"\s*–\s*", ", "),

            # Curly quotes to straight (AI formatting tell)
            (r'[\u201c\u201d]', '"'),
            (r'[\u2018\u2019]', "'"),
        ]

        # Sentence variety patterns (avoid consecutive sentences starting same way)
        self.sentence_starters_to_vary = {
            'he': ['Marcus', 'The man', 'Without hesitation,'],
            'she': ['Elena', 'The woman', 'Turning,'],
            'the': ['A', 'That', 'This'],
            'it': ['This', 'That', 'The thing'],
            'they': ['The group', 'Both of them', 'Together,'],
            'there': ['Ahead', 'Before them', 'In the distance'],
            'this': ['That', 'It', 'The'],
        }

        # Compile patterns for efficiency
        self.compiled_ai_isms = [
            (re.compile(pattern, re.IGNORECASE), replacement)
            for pattern, replacement in self.ai_ism_replacements
        ]

    def process(self, text: str) -> Tuple[str, Dict]:
        """
        Process text to remove repetition and AI artifacts.

        Args:
            text: Input text to process

        Returns:
            Tuple of (cleaned_text, stats_dict)
        """
        stats = {
            "ai_isms_replaced": 0,
            "duplicate_sentences_removed": 0,
            "repeated_phrases_removed": 0,
            "sentence_starts_varied": 0,
            "original_length": len(text),
            "final_length": 0,
        }

        # Step 1: Replace AI-isms with natural alternatives
        text, count = self._replace_ai_isms(text)
        stats["ai_isms_replaced"] = count

        # Step 2: Remove duplicate sentences
        text, count = self._remove_duplicate_sentences(text)
        stats["duplicate_sentences_removed"] = count

        # Step 3: Remove repeated phrases
        text, count = self._remove_repeated_phrases(text)
        stats["repeated_phrases_removed"] = count

        # Step 4: Vary consecutive sentence starts
        text, count = self._vary_sentence_starts(text)
        stats["sentence_starts_varied"] = count

        # Step 5: Clean up whitespace
        text = self._clean_whitespace(text)

        stats["final_length"] = len(text)
        stats["reduction_percent"] = round(
            (1 - stats["final_length"] / max(stats["original_length"], 1)) * 100, 1
        )

        self.logger.info(
            f"Post-processing: {stats['ai_isms_replaced']} AI-isms replaced, "
            f"{stats['duplicate_sentences_removed']} duplicates removed, "
            f"{stats['sentence_starts_varied']} sentence starts varied. "
            f"Size change: {stats['reduction_percent']}%"
        )

        return text, stats

    def _replace_ai_isms(self, text: str) -> Tuple[str, int]:
        """Replace AI-isms and overused phrases with natural alternatives."""
        count = 0

        for pattern, replacement in self.compiled_ai_isms:
            matches = pattern.findall(text)
            if matches:
                count += len(matches)
                text = pattern.sub(replacement, text)

        # Fix any double spaces from removals
        text = re.sub(r'  +', ' ', text)
        text = re.sub(r' ,', ',', text)
        text = re.sub(r' \.', '.', text)

        return text, count

    def _remove_duplicate_sentences(self, text: str) -> Tuple[str, int]:
        """Remove duplicate sentences while preserving paragraph structure."""
        paragraphs = text.split('\n\n')
        seen = set()
        duplicates = 0
        cleaned_paragraphs = []

        for para in paragraphs:
            if not para.strip():
                continue

            # Split into sentences
            sentences = re.split(r'(?<=[.!?])\s+', para)
            unique_sentences = []

            for sent in sentences:
                # Normalize for comparison
                normalized = re.sub(r'\s+', ' ', sent.lower().strip())

                # Only check substantial sentences
                if len(normalized) > 30:
                    if normalized in seen:
                        duplicates += 1
                        continue
                    seen.add(normalized)

                if sent.strip():
                    unique_sentences.append(sent.strip())

            if unique_sentences:
                cleaned_paragraphs.append(' '.join(unique_sentences))

        return '\n\n'.join(cleaned_paragraphs), duplicates

    def _remove_repeated_phrases(self, text: str, min_len: int = 25, max_reps: int = 2) -> Tuple[str, int]:
        """Remove phrases that appear more than max_reps times."""
        words = text.split()
        phrase_counts = Counter()
        removed = 0

        # Count n-gram phrases (5-10 words)
        for n in range(5, 11):
            for i in range(len(words) - n + 1):
                phrase = ' '.join(words[i:i+n])
                if len(phrase) >= min_len:
                    phrase_counts[phrase] += 1

        # Find excessive phrases
        excessive = {p for p, c in phrase_counts.items() if c > max_reps}

        if not excessive:
            return text, 0

        # Remove all but first occurrence
        first_seen = set()
        for phrase in sorted(excessive, key=len, reverse=True):
            if phrase not in first_seen:
                # Keep first, remove subsequent
                parts = text.split(phrase)
                if len(parts) > 2:
                    # Keep first occurrence, remove others
                    text = parts[0] + phrase + phrase.join(parts[1:2]) + ''.join(parts[2:])
                    removed += len(parts) - 2
                first_seen.add(phrase)

        return text, removed

    def _vary_sentence_starts(self, text: str) -> Tuple[str, int]:
        """Vary consecutive sentences that start the same way."""
        count = 0
        paragraphs = text.split('\n\n')
        fixed_paragraphs = []

        for para in paragraphs:
            sentences = re.split(r'(?<=[.!?])\s+', para)
            if len(sentences) < 3:
                fixed_paragraphs.append(para)
                continue

            fixed_sentences = [sentences[0]]
            prev_start = sentences[0].split()[0].lower() if sentences[0].split() else ''

            for i, sent in enumerate(sentences[1:], 1):
                words = sent.split()
                if not words:
                    fixed_sentences.append(sent)
                    continue

                curr_start = words[0].lower()

                # Check if 3+ consecutive sentences start the same
                if curr_start == prev_start:
                    next_start = ''
                    if i + 1 < len(sentences):
                        next_words = sentences[i + 1].split()
                        if next_words:
                            next_start = next_words[0].lower()

                    if next_start == curr_start and curr_start in self.sentence_starters_to_vary:
                        # Replace with alternative
                        alts = self.sentence_starters_to_vary[curr_start]
                        new_start = alts[count % len(alts)]
                        new_sent = new_start + sent[len(words[0]):]
                        fixed_sentences.append(new_sent)
                        count += 1
                        prev_start = new_start.split()[0].lower()
                        continue

                fixed_sentences.append(sent)
                prev_start = curr_start

            fixed_paragraphs.append(' '.join(fixed_sentences))

        return '\n\n'.join(fixed_paragraphs), count

    def _clean_whitespace(self, text: str) -> str:
        """Clean up whitespace issues."""
        # Multiple blank lines -> double
        text = re.sub(r'\n{3,}', '\n\n', text)
        # Trailing whitespace
        text = re.sub(r'[ \t]+$', '', text, flags=re.MULTILINE)
        # Multiple spaces
        text = re.sub(r'  +', ' ', text)
        return text.strip()

    def quick_clean(self, text: str) -> str:
        """Quick clean for real-time use - only removes obvious AI-isms."""
        for pattern, replacement in self.compiled_ai_isms[:20]:  # Top 20 patterns
            text = pattern.sub(replacement, text)
        return text


def clean_fiction_content(text: str, logger: Optional[logging.Logger] = None) -> str:
    """Convenience function to clean generated fiction content."""
    processor = RepetitionPostProcessor(logger)
    cleaned, _ = processor.process(text)
    return cleaned


# Testing
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    test_text = """
    In that single moment, time seemed to stand still. A deep sense of dread washed over him,
    threatening to consume his very being. His heart pounded against his chest as he leveraged
    all his strength to foster a sense of calm.

    She couldn't help but feel that something was wrong. She found herself thinking about
    the journey ahead. She knew this was just the beginning.

    The weight of the world pressed down on them. The deafening silence was palpable.
    Unspoken words hung in the air between them.

    He began to walk forward. He seemed to hesitate. He continued to move slowly.
    """

    processor = RepetitionPostProcessor()
    cleaned, stats = processor.process(test_text)

    print("=" * 60)
    print("ORIGINAL:")
    print(test_text)
    print("\n" + "=" * 60)
    print("CLEANED:")
    print(cleaned)
    print("\n" + "=" * 60)
    print("STATS:", stats)
