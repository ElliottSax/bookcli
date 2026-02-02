#!/usr/bin/env python3
"""
Simple Book Server for Cloud Workers
Serves books from output/fiction/ and output/non-fiction/
"""

from flask import Flask, jsonify, request
from flask_cors import CORS
import os
import json
from pathlib import Path
from datetime import datetime

app = Flask(__name__)
CORS(app)

BASE_DIR = Path(__file__).parent
FICTION_DIR = BASE_DIR / "output" / "fiction"
NON_FICTION_DIR = BASE_DIR / "output" / "non-fiction"

# Track processing status
processing_status = {}

def load_book(book_path):
    """Load a book's chapters."""
    chapters = []

    # Try reading chapters (.md first, then .txt for backwards compatibility)
    md_files = sorted(book_path.glob("chapter_*.md"))
    txt_files = sorted(book_path.glob("chapter_*.txt"))
    chapter_files = md_files if md_files else txt_files

    for chapter_file in chapter_files:
        try:
            with open(chapter_file, 'r', encoding='utf-8') as f:
                chapters.append(f.read())
        except Exception as e:
            print(f"Error reading {chapter_file}: {e}")

    return chapters

def get_all_books():
    """Get list of all books with their status."""
    books = []

    # Fiction books
    if FICTION_DIR.exists():
        for book_dir in FICTION_DIR.iterdir():
            if book_dir.is_dir():
                status_file = book_dir / ".quality_status.json"
                quality_improved = False

                if status_file.exists():
                    try:
                        with open(status_file, 'r') as f:
                            status_data = json.load(f)
                            quality_improved = status_data.get("quality_improved", False)
                    except:
                        pass

                books.append({
                    "name": book_dir.name,
                    "type": "fiction",
                    "status": "complete",
                    "quality_improved": quality_improved,
                    "path": str(book_dir)
                })

    # Non-fiction books
    if NON_FICTION_DIR.exists():
        for book_dir in NON_FICTION_DIR.iterdir():
            if book_dir.is_dir():
                status_file = book_dir / ".quality_status.json"
                quality_improved = False

                if status_file.exists():
                    try:
                        with open(status_file, 'r') as f:
                            status_data = json.load(f)
                            quality_improved = status_data.get("quality_improved", False)
                    except:
                        pass

                books.append({
                    "name": book_dir.name,
                    "type": "non-fiction",
                    "status": "complete",
                    "quality_improved": quality_improved,
                    "path": str(book_dir)
                })

    return books

@app.route('/')
def index():
    """Server info."""
    books = get_all_books()
    needs_quality = [b for b in books if not b.get("quality_improved", False)]

    return jsonify({
        "server": "Book Quality Server",
        "status": "running",
        "total_books": len(books),
        "needs_quality": len(needs_quality),
        "timestamp": datetime.now().isoformat()
    })

@app.route('/api/books/status')
def books_status():
    """Get status of all books."""
    books = get_all_books()
    return jsonify({
        "books": books,
        "total": len(books),
        "timestamp": datetime.now().isoformat()
    })

@app.route('/api/books/<book_name>')
def get_book(book_name):
    """Get a specific book's content."""
    # Try fiction first
    book_path = FICTION_DIR / book_name
    if not book_path.exists():
        # Try non-fiction
        book_path = NON_FICTION_DIR / book_name

    if not book_path.exists():
        return jsonify({"error": "Book not found"}), 404

    chapters = load_book(book_path)

    return jsonify({
        "name": book_name,
        "chapters": chapters,
        "chapter_count": len(chapters),
        "timestamp": datetime.now().isoformat()
    })

@app.route('/api/books/<book_name>/update', methods=['POST'])
def update_book(book_name):
    """Update a book with improved chapters."""
    data = request.json

    if not data or 'chapters' not in data:
        return jsonify({"error": "No chapters provided"}), 400

    # Find book path
    book_path = FICTION_DIR / book_name
    if not book_path.exists():
        book_path = NON_FICTION_DIR / book_name

    if not book_path.exists():
        return jsonify({"error": "Book not found"}), 404

    # Create backup directory
    backup_dir = book_path / "backups"
    backup_dir.mkdir(exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # Save improved chapters
    chapters = data['chapters']
    for i, chapter_text in enumerate(chapters, 1):
        chapter_file = book_path / f"chapter_{i:03d}.txt"

        # Backup original if it exists
        if chapter_file.exists():
            backup_file = backup_dir / f"chapter_{i:03d}_backup_{timestamp}.txt"
            with open(chapter_file, 'r', encoding='utf-8') as f:
                original = f.read()
            with open(backup_file, 'w', encoding='utf-8') as f:
                f.write(original)

        # Write improved version
        with open(chapter_file, 'w', encoding='utf-8') as f:
            f.write(chapter_text)

    # Update status
    status_file = book_path / ".quality_status.json"
    status_data = {
        "quality_improved": True,
        "improved_at": datetime.now().isoformat(),
        "worker_id": data.get("worker_id", "unknown"),
        "chapter_count": len(chapters)
    }

    with open(status_file, 'w') as f:
        json.dump(status_data, f, indent=2)

    print(f"✓ Updated: {book_name} ({len(chapters)} chapters) by {data.get('worker_id', 'unknown')}")

    return jsonify({
        "success": True,
        "book": book_name,
        "chapters_updated": len(chapters),
        "timestamp": datetime.now().isoformat()
    })

@app.route('/api/stats')
def stats():
    """Get server statistics."""
    books = get_all_books()
    needs_quality = [b for b in books if not b.get("quality_improved", False)]
    completed = [b for b in books if b.get("quality_improved", False)]

    return jsonify({
        "total_books": len(books),
        "needs_quality": len(needs_quality),
        "completed": len(completed),
        "fiction": len([b for b in books if b["type"] == "fiction"]),
        "non_fiction": len([b for b in books if b["type"] == "non-fiction"]),
        "timestamp": datetime.now().isoformat()
    })

if __name__ == '__main__':
    print("=" * 60)
    print("📚 BOOK QUALITY SERVER")
    print("=" * 60)

    books = get_all_books()
    needs_quality = [b for b in books if not b.get("quality_improved", False)]

    print(f"Total books: {len(books)}")
    print(f"Needs quality: {len(needs_quality)}")
    print(f"Already improved: {len(books) - len(needs_quality)}")
    print("=" * 60)
    print("\nStarting server on http://0.0.0.0:8765")
    print("Workers can connect and process books!")
    print("=" * 60 + "\n")

    app.run(host='0.0.0.0', port=8765, debug=False)
