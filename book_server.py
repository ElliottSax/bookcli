#!/usr/bin/env python3
"""
Book Server - Exposes books for cloud workers via HTTP
Run this locally, then use ngrok to expose it.
"""

from http.server import HTTPServer, BaseHTTPRequestHandler
import json
import os
from pathlib import Path
from urllib.parse import urlparse, parse_qs

FICTION_DIR = Path("/mnt/e/projects/bookcli/output/fiction")

class BookHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        print(f"[{self.address_string()}] {args[0]}")

    def send_json(self, data, status=200):
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path

        if path == "/books":
            # List books needing fixing
            books = []
            for d in sorted(FICTION_DIR.iterdir()):
                if not d.is_dir():
                    continue
                bible_path = d / "story_bible.json"
                if bible_path.exists():
                    try:
                        with open(bible_path) as f:
                            bible = json.load(f)
                        if not bible.get("quality_fixed"):
                            books.append(d.name)
                    except json.JSONDecodeError:
                        books.append(d.name)  # Include corrupted as needing fix
            self.send_json({"books": books, "count": len(books)})

        elif path.startswith("/book/"):
            # Get book data
            book_name = path[6:]
            book_dir = FICTION_DIR / book_name
            if not book_dir.exists():
                self.send_json({"error": "Book not found"}, 404)
                return

            # Load story bible
            bible_path = book_dir / "story_bible.json"
            bible = {}
            if bible_path.exists():
                with open(bible_path) as f:
                    bible = json.load(f)

            # Load chapters
            chapters = {}
            for ch in sorted(book_dir.glob("chapter_*.md")):
                chapters[ch.name] = ch.read_text()

            self.send_json({
                "name": book_name,
                "story_bible": bible,
                "chapters": chapters
            })

        elif path == "/status":
            total = len([d for d in FICTION_DIR.iterdir() if d.is_dir()])
            fixed = 0
            for d in FICTION_DIR.iterdir():
                if not d.is_dir():
                    continue
                bible_path = d / "story_bible.json"
                if bible_path.exists():
                    try:
                        with open(bible_path) as f:
                            bible = json.load(f)
                        if bible.get("quality_fixed"):
                            fixed += 1
                    except json.JSONDecodeError:
                        pass  # Skip corrupted files
            self.send_json({
                "total": total,
                "fixed": fixed,
                "remaining": total - fixed
            })

        else:
            self.send_json({"error": "Unknown endpoint"}, 404)

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path

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

            # Update chapters
            if "chapters" in data:
                for ch_name, content in data["chapters"].items():
                    ch_path = book_dir / ch_name
                    ch_path.write_text(content)
                    print(f"  Updated {ch_name}")

            # Update story bible
            if "quality_fixed" in data:
                bible_path = book_dir / "story_bible.json"
                with open(bible_path) as f:
                    bible = json.load(f)
                bible["quality_fixed"] = data["quality_fixed"]
                with open(bible_path, "w") as f:
                    json.dump(bible, f, indent=2)
                print(f"  Marked as quality_fixed")

            self.send_json({"success": True})

        else:
            self.send_json({"error": "Unknown endpoint"}, 404)

if __name__ == "__main__":
    port = 8765
    server = HTTPServer(("0.0.0.0", port), BookHandler)
    print(f"Book server running on http://localhost:{port}")
    print(f"Endpoints:")
    print(f"  GET  /status - Get fix status")
    print(f"  GET  /books - List unfixed books")
    print(f"  GET  /book/<name> - Get book data")
    print(f"  POST /book/<name>/update - Update book")
    print(f"\nRun: ngrok http {port}")
    server.serve_forever()
