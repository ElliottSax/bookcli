#!/usr/bin/env python3
"""
Simple test for the quality dashboard without web server
"""

import sys
import time
import random
from pathlib import Path

# Add scripts directory to path
sys.path.insert(0, str(Path(__file__).parent / "scripts"))

# Import dashboard (simplified - skip missing dependencies)
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict
from collections import deque
import statistics
import threading


@dataclass
class ChapterMetrics:
    """Metrics for a single chapter"""
    chapter_num: int
    status: str  # 'pending', 'generating', 'analyzing', 'complete', 'failed'
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    overall_quality: Optional[float] = None
    detail_density: Optional[float] = None
    word_count: Optional[int] = None
    provider: Optional[str] = None
    generation_time: Optional[float] = None
    cost: Optional[float] = None
    tokens_used: Optional[int] = None
    retry_count: int = 0
    errors: List[str] = None

    def to_dict(self) -> Dict:
        return asdict(self)


class SimpleQualityDashboard:
    """Simplified dashboard for testing"""

    def __init__(self, book_name: str, total_chapters: int = 20):
        self.book_name = book_name
        self.total_chapters = total_chapters
        self.chapters: Dict[int, ChapterMetrics] = {}

        for i in range(1, total_chapters + 1):
            self.chapters[i] = ChapterMetrics(chapter_num=i, status='pending')

        self.start_time = time.time()
        self.total_cost = 0.0
        self.total_tokens = 0
        self.quality_history = deque(maxlen=50)
        self.alerts = []
        self.lock = threading.Lock()

    def update_chapter(self, chapter_num: int, **kwargs):
        """Update chapter metrics"""
        with self.lock:
            chapter = self.chapters[chapter_num]
            for key, value in kwargs.items():
                setattr(chapter, key, value)

            if 'cost' in kwargs:
                self.total_cost += kwargs['cost']
            if 'overall_quality' in kwargs:
                self.quality_history.append(kwargs['overall_quality'])

    def get_ascii_dashboard(self) -> str:
        """Get ASCII representation of dashboard"""
        with self.lock:
            lines = []
            lines.append("="*60)
            lines.append(f"QUALITY DASHBOARD: {self.book_name}")
            lines.append("="*60)

            # Count statuses
            completed = sum(1 for c in self.chapters.values() if c.status == 'complete')
            in_progress = sum(1 for c in self.chapters.values() if c.status in ['generating', 'analyzing'])
            failed = sum(1 for c in self.chapters.values() if c.status == 'failed')
            pending = sum(1 for c in self.chapters.values() if c.status == 'pending')

            # Progress bar
            progress = (completed / self.total_chapters * 100) if self.total_chapters > 0 else 0
            bar_length = 40
            filled = int(bar_length * progress / 100)
            bar = '█' * filled + '░' * (bar_length - filled)

            lines.append(f"Progress: [{bar}] {progress:.1f}%")
            lines.append(f"Chapters: ✓ {completed} | ⟳ {in_progress} | ✗ {failed} | ◯ {pending}")
            lines.append("")

            # Quality metrics
            qualities = [c.overall_quality for c in self.chapters.values() if c.overall_quality]
            if qualities:
                avg_quality = statistics.mean(qualities)
                lines.append("QUALITY METRICS")
                lines.append("-" * 40)
                lines.append(f"Average Quality: {'█' * int(avg_quality)}{'░' * (10 - int(avg_quality))} {avg_quality:.1f}/10")
                lines.append(f"Range: {min(qualities):.1f} - {max(qualities):.1f}")
                lines.append("")

            # Cost & Time
            lines.append("COST & TIME")
            lines.append("-" * 40)
            lines.append(f"Total Cost: ${self.total_cost:.4f}")
            lines.append(f"Per Chapter: ${self.total_cost / max(completed, 1):.4f}")
            elapsed = time.time() - self.start_time
            elapsed_str = time.strftime('%M:%S', time.gmtime(elapsed))
            lines.append(f"Elapsed: {elapsed_str}")

            # Chapter details
            lines.append("")
            lines.append("CHAPTER STATUS")
            lines.append("-" * 40)
            for i in range(1, min(6, self.total_chapters + 1)):  # Show first 5
                chapter = self.chapters[i]
                status_icon = {
                    'pending': '◯',
                    'generating': '⟳',
                    'analyzing': '🔍',
                    'complete': '✓',
                    'failed': '✗'
                }.get(chapter.status, '?')

                quality_str = f"Q:{chapter.overall_quality:.1f}" if chapter.overall_quality else ""
                cost_str = f"${chapter.cost:.4f}" if chapter.cost else ""

                lines.append(f"Ch {i:2d}: {status_icon} {chapter.status:10s} {quality_str:6s} {cost_str:8s}")

            lines.append("="*60)
            return "\n".join(lines)


def test_dashboard():
    """Test the dashboard with simulated data"""
    print("TESTING SIMPLE QUALITY DASHBOARD")
    print("="*60)

    # Create dashboard
    dashboard = SimpleQualityDashboard(
        book_name="Test Book",
        total_chapters=10
    )

    # Initial state
    print("\nInitial State:")
    print(dashboard.get_ascii_dashboard())

    # Simulate some chapter generation
    for chapter_num in range(1, 6):
        print(f"\n--- Simulating Chapter {chapter_num} ---")

        # Start generation
        dashboard.update_chapter(chapter_num,
            status='generating',
            start_time=time.time(),
            provider=random.choice(['groq', 'deepseek', 'openrouter'])
        )

        # Update to analyzing
        time.sleep(0.1)
        dashboard.update_chapter(chapter_num,
            status='analyzing',
            word_count=random.randint(3000, 4000),
            cost=random.uniform(0.001, 0.05),
            tokens_used=random.randint(1000, 5000)
        )

        # Complete with quality score
        time.sleep(0.1)
        dashboard.update_chapter(chapter_num,
            status='complete',
            end_time=time.time(),
            overall_quality=random.uniform(7.5, 8.5),
            detail_density=random.uniform(2.5, 4.5)
        )

        # Show updated dashboard
        print(dashboard.get_ascii_dashboard())

    # Simulate some failures
    print("\n--- Simulating Some Failures ---")
    dashboard.update_chapter(6, status='failed', errors=['API timeout'])
    dashboard.update_chapter(7, status='generating')

    print(dashboard.get_ascii_dashboard())

    print("\n✓ Dashboard test complete!")


if __name__ == "__main__":
    test_dashboard()