#!/usr/bin/env python3
"""
Web Dashboard for Book Pipeline
Simple Flask-based dashboard to monitor books and workers.
"""

import os
import sys
import json
import sqlite3
import subprocess
from pathlib import Path
from datetime import datetime
from typing import Dict, List

# Try Flask, fall back to basic HTTP server
try:
    from flask import Flask, render_template_string, jsonify, request
    FLASK_AVAILABLE = True
except ImportError:
    FLASK_AVAILABLE = False
    from http.server import HTTPServer, SimpleHTTPRequestHandler

sys.path.insert(0, str(Path(__file__).parent))
from book_database import BookDatabase

# Configuration
OUTPUT_DIR = Path("/mnt/e/projects/bookcli/output")
WORKERS = [
    {"ip": "147.224.209.15", "name": "worker-1"},
    {"ip": "64.181.220.95", "name": "worker-2"},
]

# HTML Template
DASHBOARD_HTML = '''
<!DOCTYPE html>
<html>
<head>
    <title>Book Pipeline Dashboard</title>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #1a1a2e; color: #eee; padding: 20px; }
        .container { max-width: 1400px; margin: 0 auto; }
        h1 { text-align: center; margin-bottom: 30px; color: #00d4ff; }
        .stats-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; margin-bottom: 30px; }
        .stat-card { background: #16213e; padding: 20px; border-radius: 10px; text-align: center; }
        .stat-value { font-size: 2.5em; font-weight: bold; color: #00d4ff; }
        .stat-label { color: #888; margin-top: 5px; }
        .section { background: #16213e; padding: 20px; border-radius: 10px; margin-bottom: 20px; }
        .section h2 { color: #00d4ff; margin-bottom: 15px; border-bottom: 1px solid #333; padding-bottom: 10px; }
        table { width: 100%; border-collapse: collapse; }
        th, td { padding: 12px; text-align: left; border-bottom: 1px solid #333; }
        th { background: #0f3460; color: #00d4ff; }
        tr:hover { background: #1f4068; }
        .status-badge { padding: 4px 12px; border-radius: 20px; font-size: 0.85em; }
        .status-ready { background: #00c853; color: #000; }
        .status-review { background: #ffc107; color: #000; }
        .status-draft { background: #ff5722; color: #fff; }
        .status-incomplete { background: #9c27b0; color: #fff; }
        .worker-status { display: flex; gap: 20px; }
        .worker-card { flex: 1; background: #0f3460; padding: 15px; border-radius: 8px; }
        .worker-online { border-left: 4px solid #00c853; }
        .worker-offline { border-left: 4px solid #f44336; }
        .progress-bar { background: #333; border-radius: 10px; height: 20px; overflow: hidden; }
        .progress-fill { background: linear-gradient(90deg, #00d4ff, #00ff88); height: 100%; transition: width 0.3s; }
        .refresh-btn { background: #00d4ff; color: #000; border: none; padding: 10px 20px; border-radius: 5px; cursor: pointer; float: right; }
        .refresh-btn:hover { background: #00b8d4; }
        .icon { margin-right: 8px; }
        .books-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 15px; }
        .book-card { background: #0f3460; padding: 15px; border-radius: 8px; }
        .book-title { font-weight: bold; color: #00d4ff; margin-bottom: 8px; }
        .book-meta { font-size: 0.9em; color: #888; }
        .book-assets { margin-top: 10px; display: flex; gap: 8px; }
        .asset-badge { padding: 2px 8px; border-radius: 4px; font-size: 0.8em; background: #333; }
        .asset-badge.has { background: #00c853; color: #000; }
    </style>
</head>
<body>
    <div class="container">
        <h1>📚 Book Pipeline Dashboard</h1>
        <button class="refresh-btn" onclick="location.reload()">🔄 Refresh</button>

        <div class="stats-grid">
            <div class="stat-card">
                <div class="stat-value">{{ stats.total_books }}</div>
                <div class="stat-label">Total Books</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{{ "{:,}".format(stats.total_words) }}</div>
                <div class="stat-label">Total Words</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{{ stats.avg_quality }}/100</div>
                <div class="stat-label">Avg Quality</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{{ stats.with_covers }}</div>
                <div class="stat-label">With Covers</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{{ stats.with_epubs }}</div>
                <div class="stat-label">EPUBs Ready</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{{ stats.with_audiobooks }}</div>
                <div class="stat-label">Audiobooks</div>
            </div>
        </div>

        <div class="section">
            <h2>👷 Workers</h2>
            <div class="worker-status">
                {% for worker in workers %}
                <div class="worker-card {{ 'worker-online' if worker.status == 'online' else 'worker-offline' }}">
                    <strong>{{ worker.name }}</strong> ({{ worker.ip }})<br>
                    <span style="color: {{ '#00c853' if worker.status == 'online' else '#f44336' }}">
                        ● {{ worker.status }}
                    </span>
                    {% if worker.processes %}
                    <br><small>{{ worker.processes | join(', ') }}</small>
                    {% endif %}
                </div>
                {% endfor %}
            </div>
        </div>

        <div class="section">
            <h2>📖 Fiction Books ({{ fiction_books | length }})</h2>
            <div class="books-grid">
                {% for book in fiction_books %}
                <div class="book-card">
                    <div class="book-title">{{ book.title }}</div>
                    <div class="book-meta">
                        {{ book.genre }} • {{ book.chapters }}/{{ book.expected_chapters }} chapters • {{ "{:,}".format(book.word_count) }} words
                    </div>
                    <div class="progress-bar">
                        <div class="progress-fill" style="width: {{ (book.chapters / book.expected_chapters * 100) | int }}%"></div>
                    </div>
                    <div class="book-assets">
                        <span class="asset-badge {{ 'has' if book.has_cover else '' }}">Cover</span>
                        <span class="asset-badge {{ 'has' if book.has_epub else '' }}">EPUB</span>
                        <span class="asset-badge {{ 'has' if book.has_audiobook else '' }}">Audio</span>
                        <span class="status-badge status-{{ book.status }}">{{ book.status }}</span>
                    </div>
                </div>
                {% endfor %}
            </div>
        </div>

        <div class="section">
            <h2>📗 Non-Fiction Books ({{ nonfiction_books | length }})</h2>
            <table>
                <tr>
                    <th>Title</th>
                    <th>Chapters</th>
                    <th>Words</th>
                    <th>Quality</th>
                    <th>Assets</th>
                    <th>Status</th>
                </tr>
                {% for book in nonfiction_books %}
                <tr>
                    <td>{{ book.title }}</td>
                    <td>{{ book.chapters }}/{{ book.expected_chapters }}</td>
                    <td>{{ "{:,}".format(book.word_count) }}</td>
                    <td>{{ book.quality_score }}/100</td>
                    <td>
                        {% if book.has_cover %}📷{% endif %}
                        {% if book.has_epub %}📱{% endif %}
                        {% if book.has_pdf %}📄{% endif %}
                        {% if book.has_audiobook %}🎧{% endif %}
                    </td>
                    <td><span class="status-badge status-{{ book.status }}">{{ book.status }}</span></td>
                </tr>
                {% endfor %}
            </table>
        </div>

        <div class="section">
            <h2>📊 Status Distribution</h2>
            <div class="stats-grid">
                {% for status, count in stats.by_status.items() %}
                <div class="stat-card">
                    <div class="stat-value">{{ count }}</div>
                    <div class="stat-label">{{ status }}</div>
                </div>
                {% endfor %}
            </div>
        </div>

        <p style="text-align: center; color: #666; margin-top: 30px;">
            Last updated: {{ last_updated }}
        </p>
    </div>
</body>
</html>
'''

def check_worker_status(ip: str) -> Dict:
    """Check if a worker is online and what's running."""
    try:
        result = subprocess.run(
            ['ssh', '-o', 'StrictHostKeyChecking=no', '-o', 'ConnectTimeout=3',
             '-i', os.path.expanduser('~/.ssh/oci_worker_key'),
             f'ubuntu@{ip}', 'ps aux | grep python3 | grep -v grep | awk \'{print $NF}\''],
            capture_output=True, text=True, timeout=5
        )

        if result.returncode == 0:
            processes = [p.split('/')[-1] for p in result.stdout.strip().split('\n') if p]
            return {'status': 'online', 'processes': processes}
    except (subprocess.TimeoutExpired, subprocess.SubprocessError, OSError) as e:
        logger.debug(f"Worker check failed for {worker['ip']}: {e}")

    return {'status': 'offline', 'processes': []}


def get_dashboard_data() -> Dict:
    """Get all data for the dashboard."""
    db = BookDatabase()

    # Get stats
    stats = db.get_stats()

    # Get all books
    all_books = db.get_all_books()
    fiction_books = [b for b in all_books if b['book_type'] == 'fiction']
    nonfiction_books = [b for b in all_books if b['book_type'] == 'nonfiction']

    # Check workers
    workers = []
    for w in WORKERS:
        status = check_worker_status(w['ip'])
        workers.append({
            'ip': w['ip'],
            'name': w['name'],
            **status
        })

    return {
        'stats': stats,
        'fiction_books': fiction_books,
        'nonfiction_books': nonfiction_books,
        'workers': workers,
        'last_updated': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }


if FLASK_AVAILABLE:
    app = Flask(__name__)

    @app.route('/')
    def dashboard():
        data = get_dashboard_data()
        return render_template_string(DASHBOARD_HTML, **data)

    @app.route('/api/stats')
    def api_stats():
        db = BookDatabase()
        return jsonify(db.get_stats())

    @app.route('/api/books')
    def api_books():
        db = BookDatabase()
        return jsonify(db.get_all_books())

    def run_flask(host='0.0.0.0', port=8080):
        """Run Flask server."""
        print(f"Starting dashboard at http://{host}:{port}")
        app.run(host=host, port=port, debug=False)

else:
    # Fallback: Generate static HTML
    def generate_static_html():
        """Generate static HTML file."""
        from string import Template

        data = get_dashboard_data()

        # Simple template replacement (no Jinja)
        html = f'''
<!DOCTYPE html>
<html>
<head>
    <title>Book Pipeline Dashboard</title>
    <meta charset="utf-8">
    <style>
        body {{ font-family: sans-serif; background: #1a1a2e; color: #eee; padding: 20px; }}
        .stat {{ display: inline-block; background: #16213e; padding: 20px; margin: 10px; border-radius: 10px; }}
        .stat-value {{ font-size: 2em; color: #00d4ff; }}
        table {{ width: 100%; border-collapse: collapse; }}
        th, td {{ padding: 10px; border-bottom: 1px solid #333; text-align: left; }}
    </style>
</head>
<body>
    <h1>📚 Book Pipeline Dashboard</h1>
    <div>
        <div class="stat"><div class="stat-value">{data['stats']['total_books']}</div>Total Books</div>
        <div class="stat"><div class="stat-value">{data['stats']['total_words']:,}</div>Total Words</div>
        <div class="stat"><div class="stat-value">{data['stats']['avg_quality']}/100</div>Avg Quality</div>
        <div class="stat"><div class="stat-value">{data['stats']['with_epubs']}</div>EPUBs Ready</div>
    </div>
    <h2>Fiction ({len(data['fiction_books'])})</h2>
    <ul>
        {''.join(f"<li>{b['title']} - {b['chapters']}/{b['expected_chapters']} chapters</li>" for b in data['fiction_books'])}
    </ul>
    <h2>Non-Fiction ({len(data['nonfiction_books'])})</h2>
    <ul>
        {''.join(f"<li>{b['title']} - {b['word_count']:,} words</li>" for b in data['nonfiction_books'])}
    </ul>
    <p>Last updated: {data['last_updated']}</p>
</body>
</html>
'''
        output_file = OUTPUT_DIR / "dashboard.html"
        output_file.write_text(html)
        print(f"Dashboard saved to: {output_file}")


if __name__ == "__main__":
    # First, update database
    from book_database import scan_and_update_database
    fiction_dir = Path("/mnt/e/projects/bookcli/output/fiction")
    books_dir = Path("/mnt/e/projects/bookcli/output/books")
    scan_and_update_database(fiction_dir, books_dir)

    if FLASK_AVAILABLE:
        import argparse
        parser = argparse.ArgumentParser()
        parser.add_argument('--port', type=int, default=8080)
        parser.add_argument('--host', default='0.0.0.0')
        args = parser.parse_args()
        run_flask(host=args.host, port=args.port)
    else:
        generate_static_html()
