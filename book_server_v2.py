#!/usr/bin/env python3
"""
Book Server v2 - Coordinated Distributed Book Fixer Server
==========================================================

Enhanced server with:
- Worker registration
- Book claiming (prevents duplicate work)
- Progress tracking
- Health monitoring

Run locally, then expose via ngrok:
  python book_server_v2.py
  ngrok http 8765
"""

from http.server import HTTPServer, BaseHTTPRequestHandler
import json
import os
import time
from pathlib import Path
from urllib.parse import urlparse
from datetime import datetime, timedelta
from threading import Lock
import hashlib

FICTION_DIR = Path("/mnt/e/projects/bookcli/output/fiction")
CLAIM_TIMEOUT = 600  # 10 minutes - release claim if worker goes silent

# Thread-safe state
_lock = Lock()
_claimed_books = {}  # book_name -> {"worker": id, "claimed_at": timestamp}
_workers = {}  # worker_id -> {"last_seen": timestamp, "books_fixed": int}
_stats = {"total_fixed": 0, "chapters_expanded": 0, "start_time": datetime.now().isoformat()}


def get_book_hash(book_dir):
    """Get hash of book content for change detection."""
    h = hashlib.md5()
    for ch in sorted(book_dir.glob("chapter_*.md")):
        h.update(ch.read_bytes())
    return h.hexdigest()[:8]


class BookHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        worker = self.headers.get("X-Worker-ID", "unknown")
        print(f"[{datetime.now().strftime('%H:%M:%S')}] [{worker}] {args[0]}")

    def send_json(self, data, status=200):
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, X-Worker-ID")
        self.end_headers()

    def do_GET(self):
        path = urlparse(self.path).path
        worker_id = self.headers.get("X-Worker-ID", "")

        # Update worker last seen
        if worker_id:
            with _lock:
                if worker_id not in _workers:
                    _workers[worker_id] = {"last_seen": time.time(), "books_fixed": 0}
                else:
                    _workers[worker_id]["last_seen"] = time.time()

        if path == "/":
            self.send_json({
                "service": "Book Fixer Server v2",
                "endpoints": ["/status", "/books", "/book/<name>", "/claim/<name>",
                              "/release/<name>", "/workers", "/health"]
            })

        elif path == "/health":
            self.send_json({"status": "ok", "time": datetime.now().isoformat()})

        elif path == "/status":
            total = 0
            fixed = 0
            for d in FICTION_DIR.iterdir():
                if not d.is_dir():
                    continue
                total += 1
                bible_path = d / "story_bible.json"
                if bible_path.exists():
                    try:
                        with open(bible_path) as f:
                            bible = json.load(f)
                        if bible.get("quality_fixed"):
                            fixed += 1
                    except:
                        pass

            with _lock:
                claimed = len(_claimed_books)
                active_workers = sum(1 for w in _workers.values()
                                    if time.time() - w["last_seen"] < 60)

            self.send_json({
                "total": total,
                "fixed": fixed,
                "remaining": total - fixed,
                "claimed": claimed,
                "active_workers": active_workers,
                "stats": _stats
            })

        elif path == "/books":
            # List unfixed, unclaimed books
            now = time.time()
            books = []

            # Clean up expired claims
            with _lock:
                expired = [k for k, v in _claimed_books.items()
                          if now - v["claimed_at"] > CLAIM_TIMEOUT]
                for k in expired:
                    print(f"  Releasing expired claim: {k}")
                    del _claimed_books[k]

            for d in sorted(FICTION_DIR.iterdir()):
                if not d.is_dir():
                    continue
                bible_path = d / "story_bible.json"
                if bible_path.exists():
                    try:
                        with open(bible_path) as f:
                            bible = json.load(f)
                        if not bible.get("quality_fixed"):
                            with _lock:
                                if d.name not in _claimed_books:
                                    books.append(d.name)
                    except:
                        with _lock:
                            if d.name not in _claimed_books:
                                books.append(d.name)

            self.send_json({"books": books, "count": len(books)})

        elif path.startswith("/claim/"):
            # Claim a book for processing
            book_name = path[7:]
            book_dir = FICTION_DIR / book_name
            if not book_dir.exists():
                self.send_json({"error": "Book not found"}, 404)
                return

            with _lock:
                if book_name in _claimed_books:
                    existing = _claimed_books[book_name]
                    if time.time() - existing["claimed_at"] > CLAIM_TIMEOUT:
                        # Expired, allow reclaim
                        _claimed_books[book_name] = {
                            "worker": worker_id,
                            "claimed_at": time.time()
                        }
                        self.send_json({"claimed": True, "book": book_name})
                    else:
                        self.send_json({
                            "claimed": False,
                            "reason": f"Already claimed by {existing['worker']}"
                        }, 409)
                else:
                    _claimed_books[book_name] = {
                        "worker": worker_id,
                        "claimed_at": time.time()
                    }
                    self.send_json({"claimed": True, "book": book_name})

        elif path.startswith("/release/"):
            # Release a claimed book
            book_name = path[9:]
            with _lock:
                if book_name in _claimed_books:
                    del _claimed_books[book_name]
            self.send_json({"released": True})

        elif path.startswith("/book/"):
            # Get book data
            book_name = path[6:]
            book_dir = FICTION_DIR / book_name
            if not book_dir.exists():
                self.send_json({"error": "Book not found"}, 404)
                return

            bible_path = book_dir / "story_bible.json"
            bible = {}
            if bible_path.exists():
                with open(bible_path) as f:
                    bible = json.load(f)

            chapters = {}
            for ch in sorted(book_dir.glob("chapter_*.md")):
                chapters[ch.name] = ch.read_text()

            self.send_json({
                "name": book_name,
                "story_bible": bible,
                "chapters": chapters,
                "hash": get_book_hash(book_dir)
            })

        elif path == "/workers":
            with _lock:
                now = time.time()
                workers_list = []
                for wid, info in _workers.items():
                    workers_list.append({
                        "id": wid,
                        "books_fixed": info["books_fixed"],
                        "last_seen": int(now - info["last_seen"]),
                        "active": now - info["last_seen"] < 60
                    })
            self.send_json({"workers": workers_list})

        else:
            self.send_json({"error": "Unknown endpoint"}, 404)

    def do_POST(self):
        path = urlparse(self.path).path
        worker_id = self.headers.get("X-Worker-ID", "unknown")

        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length).decode()
        data = json.loads(body) if body else {}

        if path.startswith("/book/") and path.endswith("/update"):
            # Update book
            book_name = path[6:-7]
            book_dir = FICTION_DIR / book_name
            if not book_dir.exists():
                self.send_json({"error": "Book not found"}, 404)
                return

            chapters_updated = 0

            # Update chapters
            if "chapters" in data:
                for ch_name, content in data["chapters"].items():
                    ch_path = book_dir / ch_name
                    ch_path.write_text(content)
                    chapters_updated += 1
                    print(f"  Updated {ch_name}")

            # Update story bible
            bible_path = book_dir / "story_bible.json"
            try:
                with open(bible_path) as f:
                    bible = json.load(f)
            except:
                bible = {}

            if "quality_fixed" in data:
                bible["quality_fixed"] = data["quality_fixed"]
            if "fixed_by" in data:
                bible["fixed_by"] = data["fixed_by"]
            bible["fixed_at"] = datetime.now().isoformat()

            with open(bible_path, "w") as f:
                json.dump(bible, f, indent=2)

            # Release claim
            with _lock:
                if book_name in _claimed_books:
                    del _claimed_books[book_name]

                # Update worker stats
                if worker_id in _workers:
                    _workers[worker_id]["books_fixed"] += 1

                _stats["total_fixed"] += 1
                _stats["chapters_expanded"] += chapters_updated

            print(f"  ✓ Fixed by {worker_id} ({chapters_updated} chapters)")
            self.send_json({"success": True, "chapters_updated": chapters_updated})

        else:
            self.send_json({"error": "Unknown endpoint"}, 404)


def main():
    port = int(os.environ.get("PORT", 8765))
    server = HTTPServer(("0.0.0.0", port), BookHandler)

    print("=" * 60)
    print("📚 Book Fixer Server v2")
    print("=" * 60)
    print(f"Running on: http://localhost:{port}")
    print()
    print("Endpoints:")
    print("  GET  /           - API info")
    print("  GET  /health     - Health check")
    print("  GET  /status     - Fix progress")
    print("  GET  /books      - List unfixed books")
    print("  GET  /book/<n>   - Get book data")
    print("  GET  /claim/<n>  - Claim book for processing")
    print("  GET  /release/<n>- Release claimed book")
    print("  POST /book/<n>/update - Update book")
    print("  GET  /workers    - List active workers")
    print()
    print("To expose to internet:")
    print(f"  ngrok http {port}")
    print()

    # Initial status
    total = len([d for d in FICTION_DIR.iterdir() if d.is_dir()])
    fixed = sum(1 for d in FICTION_DIR.iterdir()
                if d.is_dir() and (d / "story_bible.json").exists()
                and '"quality_fixed": true' in (d / "story_bible.json").read_text())
    print(f"Books: {fixed}/{total} fixed ({total - fixed} remaining)")
    print("=" * 60)

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down...")
        server.shutdown()


if __name__ == "__main__":
    main()
