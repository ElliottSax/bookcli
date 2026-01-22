#!/usr/bin/env python3
"""
Book Database
SQLite database for tracking all books, quality, and publishing status.
"""

import os
import sys
import json
import sqlite3
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass

from lib.logging_config import setup_logging, get_logger

setup_logging()
logger = get_logger(__name__)

DB_PATH = Path("/mnt/e/projects/bookcli/output/books.db")


@dataclass
class Book:
    """Book record."""
    id: int
    title: str
    genre: str
    book_type: str  # fiction/nonfiction
    chapters: int
    expected_chapters: int
    word_count: int
    quality_score: float
    status: str  # draft, review, ready, published
    has_cover: bool
    has_epub: bool
    has_pdf: bool
    has_audiobook: bool
    created_at: str
    updated_at: str
    published_at: Optional[str]
    amazon_asin: Optional[str]
    folder_path: str


class BookDatabase:
    """SQLite database for book tracking."""

    def __init__(self, db_path: Path = DB_PATH):
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _get_conn(self) -> sqlite3.Connection:
        """Get database connection."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        """Initialize database tables."""
        conn = self._get_conn()
        cursor = conn.cursor()

        # Books table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS books (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                genre TEXT,
                book_type TEXT NOT NULL,
                chapters INTEGER DEFAULT 0,
                expected_chapters INTEGER DEFAULT 10,
                word_count INTEGER DEFAULT 0,
                quality_score REAL DEFAULT 0,
                status TEXT DEFAULT 'draft',
                has_cover INTEGER DEFAULT 0,
                has_epub INTEGER DEFAULT 0,
                has_pdf INTEGER DEFAULT 0,
                has_audiobook INTEGER DEFAULT 0,
                created_at TEXT,
                updated_at TEXT,
                published_at TEXT,
                amazon_asin TEXT,
                folder_path TEXT UNIQUE
            )
        ''')

        # Quality metrics table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS quality_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                book_id INTEGER,
                metric_name TEXT,
                metric_value REAL,
                recorded_at TEXT,
                FOREIGN KEY (book_id) REFERENCES books(id)
            )
        ''')

        # Publishing history table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS publishing_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                book_id INTEGER,
                platform TEXT,
                action TEXT,
                status TEXT,
                details TEXT,
                timestamp TEXT,
                FOREIGN KEY (book_id) REFERENCES books(id)
            )
        ''')

        # Workers table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS workers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                worker_ip TEXT,
                worker_name TEXT,
                worker_type TEXT,
                status TEXT,
                last_seen TEXT,
                books_generated INTEGER DEFAULT 0,
                chapters_improved INTEGER DEFAULT 0
            )
        ''')

        # Pipeline runs table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS pipeline_runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_type TEXT,
                started_at TEXT,
                completed_at TEXT,
                books_processed INTEGER,
                covers_generated INTEGER,
                epubs_created INTEGER,
                errors TEXT
            )
        ''')

        conn.commit()
        conn.close()

    def upsert_book(self, folder_path: str, book_data: Dict) -> int:
        """Insert or update a book record."""
        conn = self._get_conn()
        cursor = conn.cursor()

        now = datetime.now().isoformat()

        # Check if exists
        cursor.execute('SELECT id FROM books WHERE folder_path = ?', (folder_path,))
        existing = cursor.fetchone()

        if existing:
            # Update
            cursor.execute('''
                UPDATE books SET
                    title = ?, genre = ?, book_type = ?,
                    chapters = ?, expected_chapters = ?, word_count = ?,
                    quality_score = ?, status = ?,
                    has_cover = ?, has_epub = ?, has_pdf = ?, has_audiobook = ?,
                    updated_at = ?
                WHERE folder_path = ?
            ''', (
                book_data.get('title'),
                book_data.get('genre'),
                book_data.get('book_type'),
                book_data.get('chapters', 0),
                book_data.get('expected_chapters', 10),
                book_data.get('word_count', 0),
                book_data.get('quality_score', 0),
                book_data.get('status', 'draft'),
                book_data.get('has_cover', False),
                book_data.get('has_epub', False),
                book_data.get('has_pdf', False),
                book_data.get('has_audiobook', False),
                now,
                folder_path
            ))
            book_id = existing['id']
        else:
            # Insert
            cursor.execute('''
                INSERT INTO books (
                    title, genre, book_type, chapters, expected_chapters,
                    word_count, quality_score, status,
                    has_cover, has_epub, has_pdf, has_audiobook,
                    created_at, updated_at, folder_path
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                book_data.get('title'),
                book_data.get('genre'),
                book_data.get('book_type'),
                book_data.get('chapters', 0),
                book_data.get('expected_chapters', 10),
                book_data.get('word_count', 0),
                book_data.get('quality_score', 0),
                book_data.get('status', 'draft'),
                book_data.get('has_cover', False),
                book_data.get('has_epub', False),
                book_data.get('has_pdf', False),
                book_data.get('has_audiobook', False),
                now, now,
                folder_path
            ))
            book_id = cursor.lastrowid

        conn.commit()
        conn.close()
        return book_id

    def get_all_books(self) -> List[Dict]:
        """Get all books."""
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM books ORDER BY updated_at DESC')
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]

    def get_books_by_status(self, status: str) -> List[Dict]:
        """Get books by status."""
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM books WHERE status = ?', (status,))
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]

    def get_stats(self) -> Dict:
        """Get overall statistics."""
        conn = self._get_conn()
        cursor = conn.cursor()

        stats = {}

        # Total books
        cursor.execute('SELECT COUNT(*) as count FROM books')
        stats['total_books'] = cursor.fetchone()['count']

        # By type
        cursor.execute('SELECT book_type, COUNT(*) as count FROM books GROUP BY book_type')
        stats['by_type'] = {row['book_type']: row['count'] for row in cursor.fetchall()}

        # By status
        cursor.execute('SELECT status, COUNT(*) as count FROM books GROUP BY status')
        stats['by_status'] = {row['status']: row['count'] for row in cursor.fetchall()}

        # Total words
        cursor.execute('SELECT SUM(word_count) as total FROM books')
        result = cursor.fetchone()
        stats['total_words'] = result['total'] or 0

        # Average quality
        cursor.execute('SELECT AVG(quality_score) as avg FROM books WHERE quality_score > 0')
        result = cursor.fetchone()
        stats['avg_quality'] = round(result['avg'] or 0, 1)

        # With assets
        cursor.execute('SELECT SUM(has_cover) as covers, SUM(has_epub) as epubs, SUM(has_pdf) as pdfs, SUM(has_audiobook) as audiobooks FROM books')
        result = cursor.fetchone()
        stats['with_covers'] = result['covers'] or 0
        stats['with_epubs'] = result['epubs'] or 0
        stats['with_pdfs'] = result['pdfs'] or 0
        stats['with_audiobooks'] = result['audiobooks'] or 0

        conn.close()
        return stats

    def record_quality_metric(self, book_id: int, metric_name: str, value: float):
        """Record a quality metric for a book."""
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO quality_metrics (book_id, metric_name, metric_value, recorded_at)
            VALUES (?, ?, ?, ?)
        ''', (book_id, metric_name, value, datetime.now().isoformat()))
        conn.commit()
        conn.close()

    def record_pipeline_run(self, run_type: str, books: int, covers: int, epubs: int, errors: str = ""):
        """Record a pipeline run."""
        conn = self._get_conn()
        cursor = conn.cursor()
        now = datetime.now().isoformat()
        cursor.execute('''
            INSERT INTO pipeline_runs (run_type, started_at, completed_at, books_processed, covers_generated, epubs_created, errors)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (run_type, now, now, books, covers, epubs, errors))
        conn.commit()
        conn.close()

    def update_worker(self, ip: str, name: str, worker_type: str, status: str):
        """Update worker status."""
        conn = self._get_conn()
        cursor = conn.cursor()
        now = datetime.now().isoformat()

        cursor.execute('SELECT id FROM workers WHERE worker_ip = ?', (ip,))
        existing = cursor.fetchone()

        if existing:
            cursor.execute('''
                UPDATE workers SET worker_name = ?, worker_type = ?, status = ?, last_seen = ?
                WHERE worker_ip = ?
            ''', (name, worker_type, status, now, ip))
        else:
            cursor.execute('''
                INSERT INTO workers (worker_ip, worker_name, worker_type, status, last_seen)
                VALUES (?, ?, ?, ?, ?)
            ''', (ip, name, worker_type, status, now))

        conn.commit()
        conn.close()


def scan_and_update_database(fiction_dir: Path, books_dir: Path) -> int:
    """Scan book directories and update database."""
    db = BookDatabase()
    updated = 0

    for base_dir, book_type in [(fiction_dir, 'fiction'), (books_dir, 'nonfiction')]:
        if not base_dir.exists():
            continue

        for book_dir in sorted(base_dir.iterdir()):
            if not book_dir.is_dir() or book_dir.name.startswith('.'):
                continue

            outline_file = book_dir / "outline.json"
            if not outline_file.exists():
                continue

            try:
                book_info = json.loads(outline_file.read_text())
            except (json.JSONDecodeError, OSError) as e:
                logger.debug(f"Could not read outline for {book_dir.name}: {e}")
                continue

            # Gather data
            chapters = len(list(book_dir.glob("chapter_*.md")))
            word_count = sum(len(f.read_text().split()) for f in book_dir.glob("chapter_*.md"))

            expected = len(book_info.get('chapters', [])) or (12 if book_type == 'fiction' else 10)

            # Determine status
            if chapters < expected * 0.5:
                status = 'draft'
            elif chapters < expected:
                status = 'incomplete'
            elif (book_dir / f"{book_dir.name}.epub").exists():
                status = 'ready'
            else:
                status = 'review'

            # Quality score (simple calculation)
            quality = min(100, (chapters / expected) * 50 + (word_count / (expected * 3000)) * 50)

            book_data = {
                'title': book_info.get('title', book_dir.name),
                'genre': book_info.get('genre', 'unknown'),
                'book_type': book_type,
                'chapters': chapters,
                'expected_chapters': expected,
                'word_count': word_count,
                'quality_score': round(quality, 1),
                'status': status,
                'has_cover': (book_dir / "cover.png").exists(),
                'has_epub': (book_dir / f"{book_dir.name}.epub").exists(),
                'has_pdf': (book_dir / f"{book_dir.name}.pdf").exists(),
                'has_audiobook': (book_dir / "audiobook.mp3").exists(),
            }

            db.upsert_book(str(book_dir), book_data)
            updated += 1

    return updated


if __name__ == "__main__":
    fiction_dir = Path("/mnt/e/projects/bookcli/output/fiction")
    books_dir = Path("/mnt/e/projects/bookcli/output/books")

    logger.info("=" * 60)
    logger.info("BOOK DATABASE")
    logger.info("=" * 60)

    count = scan_and_update_database(fiction_dir, books_dir)
    logger.info(f"Updated {count} books in database")

    # Print stats
    db = BookDatabase()
    stats = db.get_stats()
    logger.info(f"\nDatabase Stats:")
    logger.info(f"  Total Books: {stats['total_books']}")
    logger.info(f"  By Type: {stats['by_type']}")
    logger.info(f"  By Status: {stats['by_status']}")
    logger.info(f"  Total Words: {stats['total_words']:,}")
    logger.info(f"  Avg Quality: {stats['avg_quality']}/100")
    logger.info(f"  With Covers: {stats['with_covers']}")
    logger.info(f"  With EPUBs: {stats['with_epubs']}")
