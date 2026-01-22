#!/usr/bin/env python3
"""
Audiobook Generator
Converts book chapters to audio using TTS (Text-to-Speech).
Uses edge-tts (free Microsoft voices) with fallback options.
"""

import os
import sys
import json
import asyncio
import re
import subprocess
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass

from lib.logging_config import setup_logging, get_logger

setup_logging()
logger = get_logger(__name__)

# Try to import edge-tts
try:
    import edge_tts
    EDGE_TTS_AVAILABLE = True
except ImportError:
    EDGE_TTS_AVAILABLE = False
    logger.warning("edge-tts not installed. Run: pip install edge-tts")


# Voice configurations by genre/mood
VOICE_PROFILES = {
    "fiction_male": {
        "voice": "en-US-GuyNeural",
        "rate": "-5%",
        "pitch": "-5Hz"
    },
    "fiction_female": {
        "voice": "en-US-JennyNeural",
        "rate": "-5%",
        "pitch": "+0Hz"
    },
    "nonfiction": {
        "voice": "en-US-AriaNeural",
        "rate": "+0%",
        "pitch": "+0Hz"
    },
    "thriller": {
        "voice": "en-US-DavisNeural",
        "rate": "-10%",
        "pitch": "-10Hz"
    },
    "romance": {
        "voice": "en-US-SaraNeural",
        "rate": "-5%",
        "pitch": "+5Hz"
    },
    "fantasy": {
        "voice": "en-GB-RyanNeural",
        "rate": "-5%",
        "pitch": "-5Hz"
    },
    "horror": {
        "voice": "en-US-DavisNeural",
        "rate": "-15%",
        "pitch": "-15Hz"
    },
    "scifi": {
        "voice": "en-US-TonyNeural",
        "rate": "+0%",
        "pitch": "+0Hz"
    }
}

# Genre to voice profile mapping
GENRE_VOICE_MAP = {
    "romantasy": "romance",
    "dark_romance": "thriller",
    "fantasy": "fantasy",
    "thriller": "thriller",
    "mystery": "thriller",
    "horror": "horror",
    "scifi": "scifi",
    "science_fiction": "scifi",
    "romance": "romance",
    "literary": "fiction_female",
    "historical": "fiction_male"
}


@dataclass
class AudioChapter:
    """Represents an audio chapter."""
    chapter_num: int
    title: str
    audio_path: Path
    duration_seconds: float
    word_count: int


@dataclass
class AudiobookResult:
    """Result of audiobook generation."""
    title: str
    chapters: List[AudioChapter]
    total_duration: float
    output_dir: Path
    combined_file: Optional[Path] = None


class AudiobookGenerator:
    """Generates audiobooks from text using TTS."""

    def __init__(self, output_base: Path = None):
        self.output_base = output_base or Path("/mnt/e/projects/bookcli/output")
        self.ffmpeg_path = self._find_ffmpeg()

    def _find_ffmpeg(self) -> Optional[str]:
        """Find ffmpeg binary."""
        paths = [
            "/home/elliott/.local/bin/ffmpeg",
            "/usr/bin/ffmpeg",
            "/usr/local/bin/ffmpeg",
            "ffmpeg"
        ]
        for p in paths:
            try:
                result = subprocess.run([p, "-version"], capture_output=True)
                if result.returncode == 0:
                    return p
            except (OSError, subprocess.SubprocessError):
                continue
        return None

    def _clean_text_for_speech(self, text: str) -> str:
        """Clean markdown text for natural speech."""
        # Remove markdown headers
        text = re.sub(r'^#+\s+', '', text, flags=re.MULTILINE)

        # Remove emphasis markers but keep the text
        text = re.sub(r'\*\*([^*]+)\*\*', r'\1', text)
        text = re.sub(r'\*([^*]+)\*', r'\1', text)
        text = re.sub(r'_([^_]+)_', r'\1', text)

        # Remove horizontal rules
        text = re.sub(r'^\s*[-*_]{3,}\s*$', '', text, flags=re.MULTILINE)

        # Remove image/link markdown
        text = re.sub(r'!\[([^\]]*)\]\([^)]+\)', r'\1', text)
        text = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', text)

        # Clean up multiple newlines
        text = re.sub(r'\n{3,}', '\n\n', text)

        # Add pauses for scene breaks
        text = text.replace('***', '... ... ...')
        text = text.replace('* * *', '... ... ...')

        # Handle dialogue attribution for better flow
        # "Hello," she said. -> natural pause
        text = re.sub(r'([.!?])"(\s+)(she|he|they|I)\s+said', r'\1" \3 said', text)

        return text.strip()

    def _get_voice_profile(self, book_type: str, genre: str) -> Dict:
        """Get appropriate voice profile for book."""
        if book_type == "nonfiction":
            return VOICE_PROFILES["nonfiction"]

        # Map genre to voice
        genre_lower = genre.lower().replace(" ", "_") if genre else ""
        profile_key = GENRE_VOICE_MAP.get(genre_lower, "fiction_female")
        return VOICE_PROFILES.get(profile_key, VOICE_PROFILES["fiction_female"])

    async def _generate_audio_edge_tts(
        self,
        text: str,
        output_path: Path,
        voice_profile: Dict
    ) -> bool:
        """Generate audio using edge-tts."""
        if not EDGE_TTS_AVAILABLE:
            return False

        try:
            communicate = edge_tts.Communicate(
                text,
                voice=voice_profile["voice"],
                rate=voice_profile.get("rate", "+0%"),
                pitch=voice_profile.get("pitch", "+0Hz")
            )
            await communicate.save(str(output_path))
            return True
        except Exception as e:
            logger.error(f"edge-tts error: {e}")
            return False

    def _get_audio_duration(self, audio_path: Path) -> float:
        """Get duration of audio file in seconds."""
        if not self.ffmpeg_path:
            return 0.0

        try:
            ffprobe = self.ffmpeg_path.replace("ffmpeg", "ffprobe")
            result = subprocess.run(
                [ffprobe, "-v", "quiet", "-show_entries",
                 "format=duration", "-of", "csv=p=0", str(audio_path)],
                capture_output=True, text=True
            )
            return float(result.stdout.strip())
        except (ValueError, OSError, subprocess.SubprocessError):
            return 0.0

    def _combine_audio_files(
        self,
        audio_files: List[Path],
        output_path: Path
    ) -> bool:
        """Combine multiple audio files into one."""
        if not self.ffmpeg_path or not audio_files:
            return False

        try:
            # Create file list
            list_file = output_path.parent / "audio_list.txt"
            with open(list_file, 'w') as f:
                for audio in audio_files:
                    f.write(f"file '{audio}'\n")

            # Combine with ffmpeg
            result = subprocess.run(
                [self.ffmpeg_path, "-f", "concat", "-safe", "0",
                 "-i", str(list_file), "-c", "copy", str(output_path), "-y"],
                capture_output=True
            )

            list_file.unlink()  # Clean up
            return result.returncode == 0
        except Exception as e:
            logger.error(f"Combine error: {e}")
            return False

    async def generate_chapter_audio(
        self,
        chapter_file: Path,
        output_dir: Path,
        voice_profile: Dict,
        chapter_num: int
    ) -> Optional[AudioChapter]:
        """Generate audio for a single chapter."""
        if not chapter_file.exists():
            return None

        text = chapter_file.read_text()
        cleaned_text = self._clean_text_for_speech(text)
        word_count = len(cleaned_text.split())

        # Extract chapter title
        title_match = re.search(r'^#\s+(.+)$', text, re.MULTILINE)
        title = title_match.group(1) if title_match else f"Chapter {chapter_num}"

        # Add chapter announcement
        full_text = f"Chapter {chapter_num}. {title}. ... {cleaned_text}"

        output_path = output_dir / f"chapter_{chapter_num:02d}.mp3"

        success = await self._generate_audio_edge_tts(
            full_text, output_path, voice_profile
        )

        if not success:
            return None

        duration = self._get_audio_duration(output_path)

        return AudioChapter(
            chapter_num=chapter_num,
            title=title,
            audio_path=output_path,
            duration_seconds=duration,
            word_count=word_count
        )

    async def generate_audiobook(
        self,
        book_dir: Path,
        book_type: str = "fiction",
        genre: str = None,
        combine: bool = True
    ) -> Optional[AudiobookResult]:
        """Generate complete audiobook from book directory."""
        outline_file = book_dir / "outline.json"
        if not outline_file.exists():
            logger.warning(f"No outline.json in {book_dir}")
            return None

        book_info = json.loads(outline_file.read_text())
        title = book_info.get('title', book_dir.name)
        genre = genre or book_info.get('genre', '')

        logger.info(f"Generating audiobook: {title}")

        # Create audio output directory
        audio_dir = book_dir / "audiobook"
        audio_dir.mkdir(exist_ok=True)

        # Get voice profile
        voice_profile = self._get_voice_profile(book_type, genre)
        logger.info(f"Using voice: {voice_profile['voice']}")

        # Find chapter files
        chapter_files = sorted(book_dir.glob("chapter_*.md"))
        if not chapter_files:
            logger.warning(f"No chapters found in {book_dir}")
            return None

        # Generate audio for each chapter
        chapters = []
        for i, chapter_file in enumerate(chapter_files, 1):
            logger.info(f"  Processing chapter {i}/{len(chapter_files)}")

            chapter = await self.generate_chapter_audio(
                chapter_file, audio_dir, voice_profile, i
            )

            if chapter:
                chapters.append(chapter)
                logger.info(f"    Duration: {chapter.duration_seconds/60:.1f} min")
            else:
                logger.warning(f"    Failed to generate audio for chapter {i}")

        if not chapters:
            return None

        total_duration = sum(c.duration_seconds for c in chapters)

        result = AudiobookResult(
            title=title,
            chapters=chapters,
            total_duration=total_duration,
            output_dir=audio_dir
        )

        # Combine all chapters into single file
        if combine and len(chapters) > 1:
            combined_path = audio_dir / f"{self._sanitize_filename(title)}_complete.mp3"
            audio_files = [c.audio_path for c in chapters]

            if self._combine_audio_files(audio_files, combined_path):
                result.combined_file = combined_path
                logger.info(f"Combined audiobook: {combined_path}")

        # Save metadata
        meta = {
            "title": title,
            "genre": genre,
            "voice": voice_profile["voice"],
            "total_duration_seconds": total_duration,
            "total_duration_hours": total_duration / 3600,
            "chapter_count": len(chapters),
            "chapters": [
                {
                    "num": c.chapter_num,
                    "title": c.title,
                    "file": c.audio_path.name,
                    "duration_seconds": c.duration_seconds,
                    "word_count": c.word_count
                }
                for c in chapters
            ]
        }

        meta_file = audio_dir / "audiobook_meta.json"
        meta_file.write_text(json.dumps(meta, indent=2))

        logger.info(f"Audiobook complete: {total_duration/3600:.1f} hours, {len(chapters)} chapters")

        return result

    def _sanitize_filename(self, name: str) -> str:
        """Sanitize string for use as filename."""
        return re.sub(r'[^\w\s-]', '', name).strip().replace(' ', '_')


async def generate_all_audiobooks(
    fiction_dir: Path,
    books_dir: Path,
    max_books: int = 5
) -> int:
    """Generate audiobooks for books that don't have them yet."""
    generator = AudiobookGenerator()
    generated = 0

    # Process fiction
    if fiction_dir.exists():
        for book_dir in sorted(fiction_dir.iterdir()):
            if generated >= max_books:
                break

            if not book_dir.is_dir():
                continue

            audio_dir = book_dir / "audiobook"
            if audio_dir.exists() and list(audio_dir.glob("*.mp3")):
                continue  # Already has audio

            chapters = len(list(book_dir.glob("chapter_*.md")))
            if chapters < 3:
                continue  # Not enough content

            result = await generator.generate_audiobook(
                book_dir, book_type="fiction"
            )

            if result:
                generated += 1

    # Process non-fiction
    if books_dir.exists():
        for book_dir in sorted(books_dir.iterdir()):
            if generated >= max_books:
                break

            if not book_dir.is_dir():
                continue

            audio_dir = book_dir / "audiobook"
            if audio_dir.exists() and list(audio_dir.glob("*.mp3")):
                continue

            chapters = len(list(book_dir.glob("chapter_*.md")))
            if chapters < 3:
                continue

            result = await generator.generate_audiobook(
                book_dir, book_type="nonfiction"
            )

            if result:
                generated += 1

    return generated


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Generate audiobooks from text")
    parser.add_argument("--book", type=str, help="Specific book directory to process")
    parser.add_argument("--type", choices=["fiction", "nonfiction"], default="fiction")
    parser.add_argument("--max", type=int, default=3, help="Max books to generate")
    parser.add_argument("--no-combine", action="store_true", help="Don't combine chapters")
    args = parser.parse_args()

    if not EDGE_TTS_AVAILABLE:
        print("edge-tts not installed. Installing...")
        os.system("pip install edge-tts")
        print("Please run the script again.")
        sys.exit(1)

    if args.book:
        book_dir = Path(args.book)
        generator = AudiobookGenerator()
        result = asyncio.run(generator.generate_audiobook(
            book_dir,
            book_type=args.type,
            combine=not args.no_combine
        ))
        if result:
            print(f"\nGenerated: {result.title}")
            print(f"Duration: {result.total_duration/3600:.1f} hours")
            print(f"Chapters: {len(result.chapters)}")
            if result.combined_file:
                print(f"Combined: {result.combined_file}")
    else:
        fiction_dir = Path("/mnt/e/projects/bookcli/output/fiction")
        books_dir = Path("/mnt/e/projects/bookcli/output/books")

        count = asyncio.run(generate_all_audiobooks(
            fiction_dir, books_dir, max_books=args.max
        ))
        print(f"\nGenerated {count} audiobooks")
