#!/usr/bin/env python3
"""
Reader Feedback Collection System - Phase 5 Priority 1.1
Collects and stores reader feedback for learning and adaptation
"""

import json
import time
import hashlib
import sqlite3
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from enum import Enum
import numpy as np
from collections import defaultdict


class FeedbackType(Enum):
    """Types of reader feedback"""
    RATING = "rating"              # 1-10 scale overall book rating
    CHAPTER_RATING = "chapter_rating"  # Per-chapter ratings
    HIGHLIGHT = "highlight"         # Text highlighted by reader
    COMMENT = "comment"             # Reader comment on section
    COMPLETION = "completion"       # How much was read (percentage)
    READING_TIME = "reading_time"   # Time spent per chapter
    ABANDONMENT = "abandonment"     # Where reader stopped
    PURCHASE = "purchase"           # Book was purchased
    RECOMMENDATION = "recommendation"  # Reader recommended to others


@dataclass
class ReaderProfile:
    """Profile of a reader for personalization"""
    reader_id: str
    preferred_genres: List[str]
    reading_speed: float  # words per minute
    quality_threshold: float  # minimum acceptable quality
    favorite_themes: List[str]
    disliked_elements: List[str]
    reading_history: List[str]  # book IDs
    avg_session_time: float  # minutes
    completion_rate: float  # 0-1

    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class FeedbackEntry:
    """Single feedback data point"""
    feedback_id: str
    book_id: str
    reader_id: str
    feedback_type: FeedbackType
    chapter_num: Optional[int]
    timestamp: float
    data: Dict[str, Any]

    def to_dict(self) -> Dict:
        return {
            'feedback_id': self.feedback_id,
            'book_id': self.book_id,
            'reader_id': self.reader_id,
            'feedback_type': self.feedback_type.value,
            'chapter_num': self.chapter_num,
            'timestamp': self.timestamp,
            'data': self.data
        }


class FeedbackCollector:
    """Collects and manages reader feedback for learning"""

    def __init__(self, db_path: str = "feedback.db"):
        """Initialize feedback collection system"""
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_database()
        self.feedback_cache = []
        self.batch_size = 100

    def _init_database(self):
        """Initialize SQLite database for feedback storage"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        # Feedback table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS feedback (
                feedback_id TEXT PRIMARY KEY,
                book_id TEXT NOT NULL,
                reader_id TEXT NOT NULL,
                feedback_type TEXT NOT NULL,
                chapter_num INTEGER,
                timestamp REAL NOT NULL,
                data TEXT NOT NULL,
                processed BOOLEAN DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Reader profiles table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS reader_profiles (
                reader_id TEXT PRIMARY KEY,
                profile_data TEXT NOT NULL,
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Book performance table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS book_performance (
                book_id TEXT PRIMARY KEY,
                genre TEXT,
                avg_rating REAL,
                completion_rate REAL,
                total_readers INTEGER DEFAULT 0,
                total_purchases INTEGER DEFAULT 0,
                quality_scores TEXT,
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Create indexes
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_book_id ON feedback(book_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_reader_id ON feedback(reader_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_feedback_type ON feedback(feedback_type)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_processed ON feedback(processed)")

        conn.commit()
        conn.close()

    def collect_rating(self, book_id: str, reader_id: str, rating: float,
                      chapter_num: Optional[int] = None) -> str:
        """Collect rating feedback"""
        feedback_type = FeedbackType.CHAPTER_RATING if chapter_num else FeedbackType.RATING

        feedback = FeedbackEntry(
            feedback_id=self._generate_feedback_id(book_id, reader_id, feedback_type),
            book_id=book_id,
            reader_id=reader_id,
            feedback_type=feedback_type,
            chapter_num=chapter_num,
            timestamp=time.time(),
            data={'rating': rating}
        )

        self._store_feedback(feedback)
        return feedback.feedback_id

    def collect_highlight(self, book_id: str, reader_id: str, chapter_num: int,
                         highlighted_text: str, start_pos: int, end_pos: int) -> str:
        """Collect text highlight feedback"""
        feedback = FeedbackEntry(
            feedback_id=self._generate_feedback_id(book_id, reader_id, FeedbackType.HIGHLIGHT),
            book_id=book_id,
            reader_id=reader_id,
            feedback_type=FeedbackType.HIGHLIGHT,
            chapter_num=chapter_num,
            timestamp=time.time(),
            data={
                'text': highlighted_text,
                'start_position': start_pos,
                'end_position': end_pos,
                'length': len(highlighted_text)
            }
        )

        self._store_feedback(feedback)
        return feedback.feedback_id

    def collect_reading_session(self, book_id: str, reader_id: str,
                               chapters_read: List[int], session_time: float,
                               completion_percentage: float) -> str:
        """Collect reading session data"""
        # Reading time feedback
        time_feedback = FeedbackEntry(
            feedback_id=self._generate_feedback_id(book_id, reader_id, FeedbackType.READING_TIME),
            book_id=book_id,
            reader_id=reader_id,
            feedback_type=FeedbackType.READING_TIME,
            chapter_num=None,
            timestamp=time.time(),
            data={
                'chapters_read': chapters_read,
                'session_time_minutes': session_time,
                'avg_time_per_chapter': session_time / len(chapters_read) if chapters_read else 0
            }
        )

        # Completion feedback
        completion_feedback = FeedbackEntry(
            feedback_id=self._generate_feedback_id(book_id, reader_id, FeedbackType.COMPLETION),
            book_id=book_id,
            reader_id=reader_id,
            feedback_type=FeedbackType.COMPLETION,
            chapter_num=None,
            timestamp=time.time(),
            data={'completion_percentage': completion_percentage}
        )

        self._store_feedback(time_feedback)
        self._store_feedback(completion_feedback)

        return time_feedback.feedback_id

    def collect_abandonment(self, book_id: str, reader_id: str,
                           last_chapter: int, abandonment_reason: Optional[str] = None) -> str:
        """Collect abandonment data when reader stops reading"""
        feedback = FeedbackEntry(
            feedback_id=self._generate_feedback_id(book_id, reader_id, FeedbackType.ABANDONMENT),
            book_id=book_id,
            reader_id=reader_id,
            feedback_type=FeedbackType.ABANDONMENT,
            chapter_num=last_chapter,
            timestamp=time.time(),
            data={
                'last_chapter_read': last_chapter,
                'reason': abandonment_reason or 'unknown'
            }
        )

        self._store_feedback(feedback)
        return feedback.feedback_id

    def _generate_feedback_id(self, book_id: str, reader_id: str,
                             feedback_type: FeedbackType) -> str:
        """Generate unique feedback ID"""
        content = f"{book_id}_{reader_id}_{feedback_type.value}_{time.time()}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]

    def _store_feedback(self, feedback: FeedbackEntry):
        """Store feedback in database"""
        self.feedback_cache.append(feedback)

        # Batch write to database
        if len(self.feedback_cache) >= self.batch_size:
            self._flush_cache()

    def _flush_cache(self):
        """Write cached feedback to database"""
        if not self.feedback_cache:
            return

        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        for feedback in self.feedback_cache:
            cursor.execute("""
                INSERT OR REPLACE INTO feedback
                (feedback_id, book_id, reader_id, feedback_type, chapter_num,
                 timestamp, data, processed)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                feedback.feedback_id,
                feedback.book_id,
                feedback.reader_id,
                feedback.feedback_type.value,
                feedback.chapter_num,
                feedback.timestamp,
                json.dumps(feedback.data),
                False
            ))

        conn.commit()
        conn.close()

        self.feedback_cache.clear()

    def get_book_metrics(self, book_id: str) -> Dict:
        """Get aggregated metrics for a book"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        # Get ratings
        cursor.execute("""
            SELECT AVG(CAST(json_extract(data, '$.rating') AS REAL)) as avg_rating,
                   COUNT(DISTINCT reader_id) as total_readers
            FROM feedback
            WHERE book_id = ? AND feedback_type = ?
        """, (book_id, FeedbackType.RATING.value))

        rating_data = cursor.fetchone()
        avg_rating = rating_data[0] or 0
        total_readers = rating_data[1] or 0

        # Get completion rate
        cursor.execute("""
            SELECT AVG(CAST(json_extract(data, '$.completion_percentage') AS REAL)) as avg_completion
            FROM feedback
            WHERE book_id = ? AND feedback_type = ?
        """, (book_id, FeedbackType.COMPLETION.value))

        completion_data = cursor.fetchone()
        avg_completion = completion_data[0] or 0

        # Get chapter ratings
        cursor.execute("""
            SELECT chapter_num,
                   AVG(CAST(json_extract(data, '$.rating') AS REAL)) as chapter_rating
            FROM feedback
            WHERE book_id = ? AND feedback_type = ? AND chapter_num IS NOT NULL
            GROUP BY chapter_num
            ORDER BY chapter_num
        """, (book_id, FeedbackType.CHAPTER_RATING.value))

        chapter_ratings = {row[0]: row[1] for row in cursor.fetchall()}

        # Get abandonment points
        cursor.execute("""
            SELECT chapter_num, COUNT(*) as abandonment_count
            FROM feedback
            WHERE book_id = ? AND feedback_type = ?
            GROUP BY chapter_num
            ORDER BY abandonment_count DESC
        """, (book_id, FeedbackType.ABANDONMENT.value))

        abandonment_points = cursor.fetchall()

        # Get popular highlights
        cursor.execute("""
            SELECT json_extract(data, '$.text') as highlight_text,
                   COUNT(*) as highlight_count
            FROM feedback
            WHERE book_id = ? AND feedback_type = ?
            GROUP BY highlight_text
            ORDER BY highlight_count DESC
            LIMIT 10
        """, (book_id, FeedbackType.HIGHLIGHT.value))

        popular_highlights = cursor.fetchall()

        conn.close()

        return {
            'book_id': book_id,
            'avg_rating': round(avg_rating, 2),
            'total_readers': total_readers,
            'completion_rate': round(avg_completion, 2),
            'chapter_ratings': chapter_ratings,
            'abandonment_points': abandonment_points[:5],
            'popular_highlights': popular_highlights,
            'quality_indicators': {
                'engagement': avg_completion * 10,  # 0-10 scale
                'satisfaction': avg_rating,
                'retention': 10 * (1 - len(abandonment_points) / max(total_readers, 1))
            }
        }

    def update_reader_profile(self, reader_id: str, profile: ReaderProfile):
        """Update reader profile for personalization"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        cursor.execute("""
            INSERT OR REPLACE INTO reader_profiles (reader_id, profile_data)
            VALUES (?, ?)
        """, (reader_id, json.dumps(profile.to_dict())))

        conn.commit()
        conn.close()

    def get_reader_profile(self, reader_id: str) -> Optional[ReaderProfile]:
        """Get reader profile"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        cursor.execute("""
            SELECT profile_data FROM reader_profiles WHERE reader_id = ?
        """, (reader_id,))

        result = cursor.fetchone()
        conn.close()

        if result:
            data = json.loads(result[0])
            return ReaderProfile(**data)
        return None

    def get_unprocessed_feedback(self, limit: int = 1000) -> List[FeedbackEntry]:
        """Get unprocessed feedback for analysis"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        cursor.execute("""
            SELECT feedback_id, book_id, reader_id, feedback_type,
                   chapter_num, timestamp, data
            FROM feedback
            WHERE processed = 0
            ORDER BY timestamp
            LIMIT ?
        """, (limit,))

        feedback_list = []
        for row in cursor.fetchall():
            feedback_list.append(FeedbackEntry(
                feedback_id=row[0],
                book_id=row[1],
                reader_id=row[2],
                feedback_type=FeedbackType(row[3]),
                chapter_num=row[4],
                timestamp=row[5],
                data=json.loads(row[6])
            ))

        conn.close()
        return feedback_list

    def mark_feedback_processed(self, feedback_ids: List[str]):
        """Mark feedback as processed"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        cursor.executemany("""
            UPDATE feedback SET processed = 1 WHERE feedback_id = ?
        """, [(fid,) for fid in feedback_ids])

        conn.commit()
        conn.close()


def demonstrate_feedback_collection():
    """Demonstrate feedback collection system"""
    print("="*60)
    print("READER FEEDBACK COLLECTION SYSTEM")
    print("="*60)

    # Initialize collector
    collector = FeedbackCollector("test_feedback.db")

    # Simulate reader feedback for a book
    book_id = "threads-of-fire"

    # Simulate multiple readers
    readers = [f"reader_{i:03d}" for i in range(1, 11)]

    print("\n📚 Collecting feedback for: Threads of Fire")
    print("-"*40)

    for reader_id in readers:
        # Overall rating (7-9 range for good book)
        rating = np.random.uniform(7.0, 9.0)
        collector.collect_rating(book_id, reader_id, rating)
        print(f"✓ {reader_id}: Overall rating {rating:.1f}/10")

        # Chapter ratings (some variation)
        for chapter in range(1, 6):
            chapter_rating = rating + np.random.uniform(-0.5, 0.5)
            chapter_rating = max(1, min(10, chapter_rating))
            collector.collect_rating(book_id, reader_id, chapter_rating, chapter)

        # Reading session
        chapters_read = list(range(1, np.random.randint(5, 21)))
        session_time = len(chapters_read) * np.random.uniform(3, 7)  # 3-7 min per chapter
        completion = len(chapters_read) / 20 * 100
        collector.collect_reading_session(book_id, reader_id, chapters_read,
                                         session_time, completion)

        # Some readers abandon
        if np.random.random() < 0.2:  # 20% abandonment
            last_chapter = np.random.randint(3, 15)
            collector.collect_abandonment(book_id, reader_id, last_chapter,
                                        "Lost interest")

        # Some highlight favorite passages
        if np.random.random() < 0.5:  # 50% highlight
            collector.collect_highlight(
                book_id, reader_id, 1,
                "The threads of magic wove through the air like living light",
                100, 200
            )

    # Flush remaining feedback
    collector._flush_cache()

    # Get book metrics
    print("\n📊 AGGREGATED METRICS")
    print("-"*40)

    metrics = collector.get_book_metrics(book_id)

    print(f"Average Rating: {'█' * int(metrics['avg_rating'])}{'░' * (10 - int(metrics['avg_rating']))} {metrics['avg_rating']}/10")
    print(f"Total Readers: {metrics['total_readers']}")
    print(f"Completion Rate: {metrics['completion_rate']:.1f}%")

    print("\n📈 Quality Indicators:")
    for indicator, value in metrics['quality_indicators'].items():
        print(f"  {indicator.capitalize()}: {value:.1f}/10")

    if metrics['chapter_ratings']:
        print("\n📖 Chapter Ratings:")
        for chapter, rating in list(metrics['chapter_ratings'].items())[:5]:
            print(f"  Chapter {chapter}: {rating:.1f}/10")

    if metrics['abandonment_points']:
        print("\n⚠️ Common Abandonment Points:")
        for chapter, count in metrics['abandonment_points']:
            print(f"  Chapter {chapter}: {count} readers stopped")

    print("\n✅ Feedback collection system operational!")
    print(f"📁 Database: test_feedback.db")

    # Clean up test database
    Path("test_feedback.db").unlink(missing_ok=True)

    return metrics


if __name__ == "__main__":
    demonstrate_feedback_collection()