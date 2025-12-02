#!/usr/bin/env python3
"""
Real-Time Quality Dashboard for Book Generation
Phase 4, Priority 2.1: Live monitoring of generation quality metrics

Provides web-based dashboard for monitoring:
- Real-time quality scores
- Generation progress
- Provider performance
- Cost tracking
- Issue detection
"""

import json
import time
import threading
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from collections import deque
import statistics

# For web interface
from http.server import HTTPServer, BaseHTTPRequestHandler
import urllib.parse

# Import quality components
from multi_dimensional_scorer import MultiDimensionalScorer
from detail_density_analyzer import DetailDensityAnalyzer
from word_count_enforcer import WordCountEnforcer
from quality_predictor import QualityPredictor


@dataclass
class ChapterMetrics:
    """Metrics for a single chapter"""
    chapter_num: int
    status: str  # 'pending', 'generating', 'analyzing', 'complete', 'failed'
    start_time: Optional[float] = None
    end_time: Optional[float] = None

    # Quality scores
    overall_quality: Optional[float] = None
    emotional_impact: Optional[float] = None
    prose_beauty: Optional[float] = None
    obsession_depth: Optional[float] = None
    voice_distinctiveness: Optional[float] = None
    thematic_subtlety: Optional[float] = None

    # Analysis metrics
    detail_density: Optional[float] = None
    word_count: Optional[int] = None
    word_count_target: Optional[int] = None
    word_count_variance: Optional[float] = None

    # Generation details
    provider: Optional[str] = None
    generation_time: Optional[float] = None
    cost: Optional[float] = None
    tokens_used: Optional[int] = None
    retry_count: int = 0
    errors: List[str] = None

    # Enhancement tracking
    enhancement_count: int = 0
    enhancement_time: Optional[float] = None

    def to_dict(self) -> Dict:
        return asdict(self)


class QualityDashboard:
    """
    Real-time dashboard for monitoring book generation quality

    Features:
    - Live quality metrics per chapter
    - Provider performance tracking
    - Cost accumulation
    - Issue detection and alerts
    - Historical trends
    """

    def __init__(self, book_name: str, total_chapters: int = 20,
                 target_quality: float = 8.0):
        """
        Initialize quality dashboard

        Args:
            book_name: Name of book being generated
            total_chapters: Total chapters to generate
            target_quality: Target quality score
        """
        self.book_name = book_name
        self.total_chapters = total_chapters
        self.target_quality = target_quality

        # Chapter metrics
        self.chapters: Dict[int, ChapterMetrics] = {}
        for i in range(1, total_chapters + 1):
            self.chapters[i] = ChapterMetrics(chapter_num=i, status='pending')

        # Quality analyzers
        self.scorer = MultiDimensionalScorer()
        self.detail_analyzer = DetailDensityAnalyzer()
        self.word_count_enforcer = WordCountEnforcer()
        self.quality_predictor = QualityPredictor()

        # Aggregate metrics
        self.start_time = time.time()
        self.total_cost = 0.0
        self.total_tokens = 0
        self.provider_stats: Dict[str, Dict] = {}

        # Historical data (for trends)
        self.quality_history = deque(maxlen=50)  # Last 50 quality scores
        self.cost_history = deque(maxlen=50)
        self.time_history = deque(maxlen=50)

        # Alerts
        self.alerts: List[Dict] = []
        self.alert_thresholds = {
            'quality_min': 7.0,
            'quality_target': target_quality,
            'cost_per_chapter_max': 0.05,
            'time_per_chapter_max': 120,  # seconds
            'retry_max': 3,
            'word_count_variance_max': 0.2  # 20%
        }

        # Thread safety
        self.lock = threading.Lock()

        # Dashboard server
        self.server = None
        self.server_thread = None

    def update_chapter_start(self, chapter_num: int, provider: str):
        """Mark chapter generation started"""
        with self.lock:
            chapter = self.chapters[chapter_num]
            chapter.status = 'generating'
            chapter.start_time = time.time()
            chapter.provider = provider

    def update_chapter_generated(self, chapter_num: int, text: str,
                                cost: float, tokens: int):
        """Update after text generation"""
        with self.lock:
            chapter = self.chapters[chapter_num]
            chapter.status = 'analyzing'
            chapter.cost = cost
            chapter.tokens_used = tokens
            chapter.word_count = len(text.split())

            # Update totals
            self.total_cost += cost
            self.total_tokens += tokens

            # Analyze quality
            self._analyze_chapter_quality(chapter_num, text)

    def _analyze_chapter_quality(self, chapter_num: int, text: str):
        """Run quality analysis on chapter"""
        chapter = self.chapters[chapter_num]

        try:
            # Multi-dimensional scoring
            score_result = self.scorer.score(text)
            chapter.overall_quality = score_result.total
            chapter.emotional_impact = score_result.scores.get('emotional_impact', 0)
            chapter.prose_beauty = score_result.scores.get('prose_beauty', 0)
            chapter.obsession_depth = score_result.scores.get('obsession_depth', 0)
            chapter.voice_distinctiveness = score_result.scores.get('voice_distinctiveness', 0)
            chapter.thematic_subtlety = score_result.scores.get('thematic_subtlety', 0)

            # Detail density
            density_result = self.detail_analyzer.analyze(text, target_density=3.0)
            chapter.detail_density = density_result.get('density', 0)

            # Word count validation
            if chapter.word_count_target:
                variance = abs(chapter.word_count - chapter.word_count_target) / chapter.word_count_target
                chapter.word_count_variance = variance

            # Update history
            self.quality_history.append(chapter.overall_quality)
            self.cost_history.append(chapter.cost)

            # Check for alerts
            self._check_alerts(chapter)

        except Exception as e:
            chapter.errors = chapter.errors or []
            chapter.errors.append(f"Analysis failed: {str(e)}")

    def update_chapter_complete(self, chapter_num: int):
        """Mark chapter as complete"""
        with self.lock:
            chapter = self.chapters[chapter_num]
            chapter.status = 'complete'
            chapter.end_time = time.time()

            if chapter.start_time:
                chapter.generation_time = chapter.end_time - chapter.start_time
                self.time_history.append(chapter.generation_time)

            # Update provider stats
            if chapter.provider:
                self._update_provider_stats(chapter)

    def update_chapter_failed(self, chapter_num: int, error: str):
        """Mark chapter as failed"""
        with self.lock:
            chapter = self.chapters[chapter_num]
            chapter.status = 'failed'
            chapter.errors = chapter.errors or []
            chapter.errors.append(error)
            chapter.retry_count += 1

            # Create alert
            self._add_alert('error', f"Chapter {chapter_num} failed: {error}")

    def _update_provider_stats(self, chapter: ChapterMetrics):
        """Update provider performance statistics"""
        if not chapter.provider:
            return

        if chapter.provider not in self.provider_stats:
            self.provider_stats[chapter.provider] = {
                'chapters': 0,
                'total_cost': 0,
                'total_tokens': 0,
                'total_time': 0,
                'avg_quality': 0,
                'failures': 0
            }

        stats = self.provider_stats[chapter.provider]
        stats['chapters'] += 1
        stats['total_cost'] += chapter.cost or 0
        stats['total_tokens'] += chapter.tokens_used or 0
        stats['total_time'] += chapter.generation_time or 0

        if chapter.overall_quality:
            # Update average quality
            prev_avg = stats['avg_quality']
            stats['avg_quality'] = (
                (prev_avg * (stats['chapters'] - 1) + chapter.overall_quality) /
                stats['chapters']
            )

        if chapter.status == 'failed':
            stats['failures'] += 1

    def _check_alerts(self, chapter: ChapterMetrics):
        """Check if chapter metrics trigger any alerts"""
        # Quality alerts
        if chapter.overall_quality and chapter.overall_quality < self.alert_thresholds['quality_min']:
            self._add_alert('critical',
                f"Chapter {chapter.chapter_num}: Quality {chapter.overall_quality:.1f} below minimum {self.alert_thresholds['quality_min']}")
        elif chapter.overall_quality and chapter.overall_quality < self.alert_thresholds['quality_target']:
            self._add_alert('warning',
                f"Chapter {chapter.chapter_num}: Quality {chapter.overall_quality:.1f} below target {self.alert_thresholds['quality_target']}")

        # Cost alert
        if chapter.cost and chapter.cost > self.alert_thresholds['cost_per_chapter_max']:
            self._add_alert('warning',
                f"Chapter {chapter.chapter_num}: Cost ${chapter.cost:.4f} exceeds max ${self.alert_thresholds['cost_per_chapter_max']}")

        # Time alert
        if chapter.generation_time and chapter.generation_time > self.alert_thresholds['time_per_chapter_max']:
            self._add_alert('warning',
                f"Chapter {chapter.chapter_num}: Generation time {chapter.generation_time:.1f}s exceeds max {self.alert_thresholds['time_per_chapter_max']}s")

        # Retry alert
        if chapter.retry_count > self.alert_thresholds['retry_max']:
            self._add_alert('critical',
                f"Chapter {chapter.chapter_num}: Excessive retries ({chapter.retry_count})")

        # Word count alert
        if chapter.word_count_variance and chapter.word_count_variance > self.alert_thresholds['word_count_variance_max']:
            self._add_alert('warning',
                f"Chapter {chapter.chapter_num}: Word count variance {chapter.word_count_variance:.1%} exceeds {self.alert_thresholds['word_count_variance_max']:.0%}")

    def _add_alert(self, level: str, message: str):
        """Add an alert to the dashboard"""
        alert = {
            'timestamp': datetime.now().isoformat(),
            'level': level,  # 'info', 'warning', 'critical', 'error'
            'message': message
        }
        self.alerts.append(alert)

        # Keep only last 100 alerts
        if len(self.alerts) > 100:
            self.alerts.pop(0)

    def get_dashboard_data(self) -> Dict:
        """Get all dashboard data for display"""
        with self.lock:
            # Calculate aggregates
            completed = sum(1 for c in self.chapters.values() if c.status == 'complete')
            in_progress = sum(1 for c in self.chapters.values() if c.status in ['generating', 'analyzing'])
            failed = sum(1 for c in self.chapters.values() if c.status == 'failed')
            pending = sum(1 for c in self.chapters.values() if c.status == 'pending')

            # Average quality
            qualities = [c.overall_quality for c in self.chapters.values() if c.overall_quality]
            avg_quality = statistics.mean(qualities) if qualities else 0

            # Progress percentage
            progress = (completed / self.total_chapters * 100) if self.total_chapters > 0 else 0

            # ETA calculation
            elapsed = time.time() - self.start_time
            if completed > 0:
                avg_time_per_chapter = elapsed / completed
                remaining = self.total_chapters - completed
                eta_seconds = avg_time_per_chapter * remaining
                eta = datetime.now() + timedelta(seconds=eta_seconds)
            else:
                eta = None

            return {
                'book_name': self.book_name,
                'timestamp': datetime.now().isoformat(),
                'progress': {
                    'completed': completed,
                    'in_progress': in_progress,
                    'failed': failed,
                    'pending': pending,
                    'total': self.total_chapters,
                    'percentage': progress
                },
                'quality': {
                    'average': avg_quality,
                    'target': self.target_quality,
                    'min': min(qualities) if qualities else 0,
                    'max': max(qualities) if qualities else 0,
                    'history': list(self.quality_history)
                },
                'cost': {
                    'total': self.total_cost,
                    'per_chapter': self.total_cost / max(completed, 1),
                    'history': list(self.cost_history)
                },
                'time': {
                    'elapsed': elapsed,
                    'eta': eta.isoformat() if eta else None,
                    'avg_per_chapter': elapsed / max(completed, 1),
                    'history': list(self.time_history)
                },
                'providers': self.provider_stats,
                'chapters': {k: v.to_dict() for k, v in self.chapters.items()},
                'alerts': self.alerts[-10:],  # Last 10 alerts
                'tokens_used': self.total_tokens
            }

    def get_ascii_dashboard(self) -> str:
        """Get ASCII representation of dashboard for terminal"""
        data = self.get_dashboard_data()

        lines = []
        lines.append("="*80)
        lines.append(f"QUALITY DASHBOARD: {self.book_name}")
        lines.append("="*80)

        # Progress bar
        progress = data['progress']['percentage']
        bar_length = 40
        filled = int(bar_length * progress / 100)
        bar = '█' * filled + '░' * (bar_length - filled)
        lines.append(f"Progress: [{bar}] {progress:.1f}%")
        lines.append(f"Chapters: ✓ {data['progress']['completed']} | "
                    f"⟳ {data['progress']['in_progress']} | "
                    f"✗ {data['progress']['failed']} | "
                    f"◯ {data['progress']['pending']}")

        lines.append("")

        # Quality metrics
        lines.append("QUALITY METRICS")
        lines.append("-" * 40)
        avg_quality = data['quality']['average']
        quality_bar = self._quality_to_bar(avg_quality)
        lines.append(f"Average Quality: {quality_bar} {avg_quality:.1f}/10")
        lines.append(f"Target Quality:  {'─' * int(data['quality']['target'])}┃ {data['quality']['target']:.1f}/10")
        lines.append(f"Range: {data['quality']['min']:.1f} - {data['quality']['max']:.1f}")

        lines.append("")

        # Cost & Time
        lines.append("COST & TIME")
        lines.append("-" * 40)
        lines.append(f"Total Cost: ${data['cost']['total']:.4f}")
        lines.append(f"Per Chapter: ${data['cost']['per_chapter']:.4f}")
        elapsed_str = time.strftime('%H:%M:%S', time.gmtime(data['time']['elapsed']))
        lines.append(f"Elapsed: {elapsed_str}")
        if data['time']['eta']:
            eta_dt = datetime.fromisoformat(data['time']['eta'])
            eta_str = eta_dt.strftime('%H:%M')
            lines.append(f"ETA: {eta_str}")

        lines.append("")

        # Provider performance
        if data['providers']:
            lines.append("PROVIDER PERFORMANCE")
            lines.append("-" * 40)
            for provider, stats in data['providers'].items():
                lines.append(f"{provider}: {stats['chapters']} chapters, "
                           f"${stats['total_cost']:.4f}, "
                           f"Q: {stats['avg_quality']:.1f}")

        lines.append("")

        # Recent alerts
        if data['alerts']:
            lines.append("RECENT ALERTS")
            lines.append("-" * 40)
            for alert in data['alerts'][-5:]:  # Last 5 alerts
                icon = {'info': 'ℹ', 'warning': '⚠', 'critical': '⚡', 'error': '✗'}.get(alert['level'], '•')
                lines.append(f"{icon} {alert['message']}")

        lines.append("="*80)
        return "\n".join(lines)

    def _quality_to_bar(self, quality: float) -> str:
        """Convert quality score to visual bar"""
        if quality >= 8.5:
            return '█' * 10 + ' ★★★★★'
        elif quality >= 8.0:
            return '█' * 9 + '▒' + ' ★★★★☆'
        elif quality >= 7.5:
            return '█' * 8 + '▒' * 2 + ' ★★★☆☆'
        elif quality >= 7.0:
            return '█' * 7 + '▒' * 3 + ' ★★☆☆☆'
        else:
            filled = int(quality)
            return '█' * filled + '▒' * (10 - filled) + ' ★☆☆☆☆'

    def start_web_server(self, port: int = 8080):
        """Start web server for dashboard"""

        class DashboardHandler(BaseHTTPRequestHandler):
            dashboard = self

            def do_GET(self):
                if self.path == '/':
                    self.send_response(200)
                    self.send_header('Content-type', 'text/html')
                    self.end_headers()
                    self.wfile.write(self._get_html_dashboard().encode())
                elif self.path == '/data':
                    self.send_response(200)
                    self.send_header('Content-type', 'application/json')
                    self.end_headers()
                    data = DashboardHandler.dashboard.get_dashboard_data()
                    self.wfile.write(json.dumps(data).encode())
                else:
                    self.send_response(404)
                    self.end_headers()

            def _get_html_dashboard(self) -> str:
                return f'''
<!DOCTYPE html>
<html>
<head>
    <title>BookCLI Quality Dashboard</title>
    <meta http-equiv="refresh" content="5">
    <style>
        body {{ font-family: monospace; background: #1e1e1e; color: #e0e0e0; padding: 20px; }}
        h1 {{ color: #4CAF50; }}
        .progress {{ background: #333; height: 30px; border-radius: 5px; overflow: hidden; }}
        .progress-bar {{ background: linear-gradient(90deg, #4CAF50, #8BC34A); height: 100%; transition: width 0.5s; }}
        .metric {{ display: inline-block; margin: 10px 20px; padding: 10px; background: #2a2a2a; border-radius: 5px; }}
        .alert {{ padding: 5px; margin: 5px 0; border-radius: 3px; }}
        .alert.warning {{ background: #ff9800; color: #000; }}
        .alert.critical {{ background: #f44336; color: #fff; }}
        .alert.error {{ background: #d32f2f; color: #fff; }}
        .quality-bar {{ display: inline-block; width: 200px; height: 20px; background: #333; position: relative; }}
        .quality-fill {{ height: 100%; background: linear-gradient(90deg, #f44336, #ff9800, #4CAF50); }}
        table {{ width: 100%; border-collapse: collapse; }}
        th, td {{ padding: 8px; text-align: left; border-bottom: 1px solid #333; }}
        th {{ background: #2a2a2a; }}
    </style>
    <script>
        setTimeout(function(){{location.reload();}}, 5000);
    </script>
</head>
<body>
    <h1>📚 BookCLI Quality Dashboard</h1>
    <div id="dashboard">Loading...</div>
    <script>
        fetch('/data')
            .then(response => response.json())
            .then(data => {{
                document.getElementById('dashboard').innerHTML = formatDashboard(data);
            }});

        function formatDashboard(data) {{
            let html = '<h2>' + data.book_name + '</h2>';

            // Progress
            let progress = data.progress.percentage;
            html += '<div class="progress"><div class="progress-bar" style="width:' + progress + '%"></div></div>';
            html += '<p>Progress: ' + progress.toFixed(1) + '% | ';
            html += '✓ ' + data.progress.completed + ' | ';
            html += '⟳ ' + data.progress.in_progress + ' | ';
            html += '✗ ' + data.progress.failed + '</p>';

            // Quality
            html += '<div class="metric">';
            html += '<strong>Quality</strong><br>';
            html += 'Average: ' + data.quality.average.toFixed(1) + '/10<br>';
            html += 'Target: ' + data.quality.target.toFixed(1) + '/10';
            html += '</div>';

            // Cost
            html += '<div class="metric">';
            html += '<strong>Cost</strong><br>';
            html += 'Total: $' + data.cost.total.toFixed(4) + '<br>';
            html += 'Per Chapter: $' + data.cost.per_chapter.toFixed(4);
            html += '</div>';

            // Alerts
            if (data.alerts.length > 0) {{
                html += '<h3>Recent Alerts</h3>';
                data.alerts.forEach(alert => {{
                    html += '<div class="alert ' + alert.level + '">' + alert.message + '</div>';
                }});
            }}

            return html;
        }}
    </script>
</body>
</html>
                '''

            def log_message(self, format, *args):
                pass  # Suppress request logging

        self.server = HTTPServer(('', port), DashboardHandler)
        DashboardHandler.dashboard = self

        self.server_thread = threading.Thread(target=self.server.serve_forever)
        self.server_thread.daemon = True
        self.server_thread.start()

        print(f"[Dashboard] Web interface started at http://localhost:{port}")

    def stop_web_server(self):
        """Stop the web server"""
        if self.server:
            self.server.shutdown()
            self.server_thread.join()


def demo_dashboard():
    """Demonstrate dashboard functionality"""
    print("="*60)
    print("QUALITY DASHBOARD DEMO")
    print("="*60)

    # Create dashboard
    dashboard = QualityDashboard(
        book_name="Test Book",
        total_chapters=20,
        target_quality=8.0
    )

    # Start web server
    dashboard.start_web_server(port=8080)
    print("\nWeb dashboard: http://localhost:8080")
    print("(Will auto-refresh every 5 seconds)")

    # Simulate chapter generation
    import random

    for chapter_num in range(1, 6):
        print(f"\n--- Simulating Chapter {chapter_num} ---")

        # Start generation
        provider = random.choice(['groq', 'deepseek', 'openrouter'])
        dashboard.update_chapter_start(chapter_num, provider)

        # Simulate generation time
        time.sleep(0.5)

        # Generate fake text
        text = f"Chapter {chapter_num} content. " * 500
        cost = random.uniform(0.001, 0.05)
        tokens = random.randint(1000, 5000)

        # Update generated
        dashboard.update_chapter_generated(chapter_num, text, cost, tokens)

        # Simulate analysis time
        time.sleep(0.2)

        # Complete or fail randomly
        if random.random() > 0.1:  # 90% success
            dashboard.update_chapter_complete(chapter_num)
        else:
            dashboard.update_chapter_failed(chapter_num, "Simulated error")

        # Print ASCII dashboard
        print("\n" + dashboard.get_ascii_dashboard())

    print("\n" + "="*60)
    print("Dashboard demo running. Press Ctrl+C to stop.")
    print("View web dashboard at: http://localhost:8080")
    print("="*60)

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        dashboard.stop_web_server()
        print("\nDashboard stopped.")


if __name__ == "__main__":
    demo_dashboard()