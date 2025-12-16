"""
Success Analytics Tracker for Book Factory
Tracks sales, quality scores, and reader engagement metrics
"""

import json
import sqlite3
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from enum import Enum
import statistics
import numpy as np
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import StandardScaler

logger = logging.getLogger(__name__)


class MetricType(Enum):
    """Types of metrics tracked."""
    SALES = "sales"
    REVIEWS = "reviews"
    RATING = "rating"
    QUALITY_SCORE = "quality_score"
    GENERATION_COST = "generation_cost"
    PAGE_READS = "page_reads"
    CONVERSION_RATE = "conversion_rate"
    RETURN_RATE = "return_rate"
    RANK = "rank"
    REVENUE = "revenue"


@dataclass
class BookPerformance:
    """Performance data for a single book."""
    book_id: str
    title: str
    author: str
    genre: str
    published_date: str

    # Quality metrics
    quality_score: float  # Internal quality score
    word_count: int
    chapters: int

    # Sales metrics
    total_sales: int = 0
    daily_sales: Dict[str, int] = None  # date -> sales
    revenue: float = 0.0
    price: float = 2.99

    # Engagement metrics
    reviews_count: int = 0
    average_rating: float = 0.0
    page_reads: int = 0
    read_through_rate: float = 0.0

    # Rankings
    best_rank: int = None
    current_rank: int = None
    category_ranks: Dict[str, int] = None

    # Cost metrics
    generation_cost: float = 0.0
    marketing_cost: float = 0.0
    profit: float = 0.0

    def __post_init__(self):
        """Initialize default values."""
        if self.daily_sales is None:
            self.daily_sales = {}
        if self.category_ranks is None:
            self.category_ranks = {}

        # Calculate profit
        self.profit = self.revenue - self.generation_cost - self.marketing_cost


@dataclass
class SuccessPredictor:
    """Model for predicting book success."""
    features: List[str]
    weights: Dict[str, float]
    accuracy: float
    r_squared: float
    predictions: Dict[str, float] = None

    def predict(self, book_features: Dict[str, float]) -> float:
        """Predict success score for given features."""
        score = 0.0
        for feature, value in book_features.items():
            if feature in self.weights:
                score += value * self.weights[feature]
        return max(0.0, min(100.0, score))


class SuccessAnalytics:
    """
    Analytics system for tracking and predicting book success.
    Features:
    - Sales tracking and analysis
    - Quality score correlation
    - Success prediction models
    - ROI calculation
    - Performance dashboards
    """

    def __init__(self, workspace: Path):
        """
        Initialize the analytics system.

        Args:
            workspace: Path to analytics workspace
        """
        self.workspace = Path(workspace)
        self.workspace.mkdir(parents=True, exist_ok=True)

        # Database for persistent storage
        self.db_path = self.workspace / "analytics.db"
        self._init_database()

        # In-memory caches
        self.books: Dict[str, BookPerformance] = {}
        self.predictors: Dict[str, SuccessPredictor] = {}

        # Load existing data
        self._load_from_database()

    def _init_database(self):
        """Initialize SQLite database."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Books performance table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS book_performance (
                book_id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                author TEXT,
                genre TEXT,
                published_date TEXT,
                quality_score REAL,
                word_count INTEGER,
                data JSON NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Daily metrics table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS daily_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                book_id TEXT NOT NULL,
                date TEXT NOT NULL,
                metric_type TEXT NOT NULL,
                value REAL NOT NULL,
                FOREIGN KEY (book_id) REFERENCES book_performance(book_id),
                UNIQUE(book_id, date, metric_type)
            )
        """)

        # Predictions table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS predictions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                book_id TEXT NOT NULL,
                predicted_sales REAL,
                predicted_rating REAL,
                predicted_roi REAL,
                confidence REAL,
                prediction_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (book_id) REFERENCES book_performance(book_id)
            )
        """)

        # Success patterns table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS success_patterns (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                pattern_name TEXT NOT NULL,
                genre TEXT,
                features JSON NOT NULL,
                success_rate REAL,
                sample_size INTEGER,
                discovered_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        conn.commit()
        conn.close()

    def track_book(
        self,
        book_id: str,
        title: str,
        genre: str,
        quality_score: float,
        word_count: int,
        generation_cost: float,
        **kwargs
    ) -> BookPerformance:
        """
        Start tracking a new book.

        Args:
            book_id: Unique book identifier
            title: Book title
            genre: Book genre
            quality_score: Internal quality score
            word_count: Total word count
            generation_cost: Cost to generate
            **kwargs: Additional metadata

        Returns:
            BookPerformance object
        """
        book = BookPerformance(
            book_id=book_id,
            title=title,
            author=kwargs.get('author', 'AI Generated'),
            genre=genre,
            published_date=datetime.now().isoformat(),
            quality_score=quality_score,
            word_count=word_count,
            chapters=kwargs.get('chapters', 20),
            generation_cost=generation_cost,
            price=kwargs.get('price', 2.99)
        )

        # Store in memory and database
        self.books[book_id] = book
        self._save_book_performance(book)

        logger.info(f"Started tracking book: {title} (ID: {book_id})")
        return book

    def update_metrics(
        self,
        book_id: str,
        date: str,
        metrics: Dict[MetricType, float]
    ) -> bool:
        """
        Update daily metrics for a book.

        Args:
            book_id: Book identifier
            date: Date (YYYY-MM-DD format)
            metrics: Dictionary of metric types and values

        Returns:
            True if successful
        """
        if book_id not in self.books:
            logger.error(f"Book {book_id} not found")
            return False

        book = self.books[book_id]

        # Process each metric
        for metric_type, value in metrics.items():
            # Update book object
            if metric_type == MetricType.SALES:
                book.daily_sales[date] = int(value)
                book.total_sales = sum(book.daily_sales.values())

            elif metric_type == MetricType.REVIEWS:
                book.reviews_count = int(value)

            elif metric_type == MetricType.RATING:
                book.average_rating = float(value)

            elif metric_type == MetricType.PAGE_READS:
                book.page_reads = int(value)

            elif metric_type == MetricType.RANK:
                book.current_rank = int(value)
                if book.best_rank is None or value < book.best_rank:
                    book.best_rank = int(value)

            elif metric_type == MetricType.REVENUE:
                book.revenue = float(value)

            # Save to database
            self._save_daily_metric(book_id, date, metric_type.value, value)

        # Update profit calculation
        book.profit = book.revenue - book.generation_cost - book.marketing_cost

        # Save updated book
        self._save_book_performance(book)

        logger.info(f"Updated metrics for book {book_id} on {date}")
        return True

    def calculate_roi(self, book_id: str) -> Dict[str, float]:
        """
        Calculate ROI for a book.

        Args:
            book_id: Book identifier

        Returns:
            ROI metrics
        """
        if book_id not in self.books:
            return {}

        book = self.books[book_id]

        total_cost = book.generation_cost + book.marketing_cost
        if total_cost == 0:
            roi_percentage = 0
        else:
            roi_percentage = (book.profit / total_cost) * 100

        return {
            'revenue': book.revenue,
            'total_cost': total_cost,
            'profit': book.profit,
            'roi_percentage': roi_percentage,
            'cost_per_sale': total_cost / max(1, book.total_sales),
            'revenue_per_sale': book.revenue / max(1, book.total_sales),
            'break_even_sales': int(total_cost / book.price) if book.price > 0 else 0,
            'days_to_break_even': self._calculate_days_to_break_even(book)
        }

    def analyze_success_factors(
        self,
        min_sales: int = 100
    ) -> Dict[str, Any]:
        """
        Analyze factors that correlate with success.

        Args:
            min_sales: Minimum sales to consider successful

        Returns:
            Analysis results
        """
        successful_books = []
        unsuccessful_books = []

        for book in self.books.values():
            if book.total_sales >= min_sales:
                successful_books.append(book)
            else:
                unsuccessful_books.append(book)

        if not successful_books:
            return {'error': 'Not enough successful books for analysis'}

        analysis = {
            'successful_count': len(successful_books),
            'unsuccessful_count': len(unsuccessful_books),
            'success_rate': len(successful_books) / len(self.books) * 100
        }

        # Analyze quality score correlation
        if successful_books:
            analysis['successful_avg_quality'] = statistics.mean(
                [b.quality_score for b in successful_books]
            )
            analysis['successful_avg_word_count'] = statistics.mean(
                [b.word_count for b in successful_books]
            )
            analysis['successful_avg_rating'] = statistics.mean(
                [b.average_rating for b in successful_books if b.average_rating > 0]
            )

        if unsuccessful_books:
            analysis['unsuccessful_avg_quality'] = statistics.mean(
                [b.quality_score for b in unsuccessful_books]
            )
            analysis['unsuccessful_avg_word_count'] = statistics.mean(
                [b.word_count for b in unsuccessful_books]
            )

        # Genre analysis
        genre_success = {}
        for book in self.books.values():
            if book.genre not in genre_success:
                genre_success[book.genre] = {'total': 0, 'successful': 0}

            genre_success[book.genre]['total'] += 1
            if book.total_sales >= min_sales:
                genre_success[book.genre]['successful'] += 1

        for genre, data in genre_success.items():
            data['success_rate'] = (
                data['successful'] / data['total'] * 100
                if data['total'] > 0 else 0
            )

        analysis['genre_success'] = genre_success

        # Price point analysis
        price_ranges = {
            '$0.99': (0, 1.0),
            '$1.99': (1.0, 2.0),
            '$2.99': (2.0, 3.0),
            '$3.99': (3.0, 4.0),
            '$4.99+': (4.0, float('inf'))
        }

        price_success = {}
        for range_name, (min_price, max_price) in price_ranges.items():
            books_in_range = [
                b for b in self.books.values()
                if min_price <= b.price < max_price
            ]
            if books_in_range:
                successful_in_range = [
                    b for b in books_in_range
                    if b.total_sales >= min_sales
                ]
                price_success[range_name] = {
                    'total': len(books_in_range),
                    'successful': len(successful_in_range),
                    'success_rate': len(successful_in_range) / len(books_in_range) * 100,
                    'avg_sales': statistics.mean([b.total_sales for b in books_in_range])
                }

        analysis['price_success'] = price_success

        return analysis

    def build_prediction_model(
        self,
        target: str = 'sales'
    ) -> SuccessPredictor:
        """
        Build a success prediction model.

        Args:
            target: Target to predict ('sales', 'rating', 'roi')

        Returns:
            SuccessPredictor model
        """
        if len(self.books) < 10:
            logger.warning("Not enough data for reliable prediction model")
            return None

        # Prepare features and targets
        features = []
        targets = []
        feature_names = [
            'quality_score', 'word_count', 'chapters',
            'price', 'genre_encoded'
        ]

        # Encode genres
        genres = list(set(b.genre for b in self.books.values()))
        genre_map = {g: i for i, g in enumerate(genres)}

        for book in self.books.values():
            # Skip books without enough data
            if target == 'sales' and book.total_sales == 0:
                continue
            elif target == 'rating' and book.average_rating == 0:
                continue

            # Build feature vector
            feature_vector = [
                book.quality_score,
                book.word_count / 1000,  # Normalize word count
                book.chapters,
                book.price,
                genre_map[book.genre]
            ]
            features.append(feature_vector)

            # Get target value
            if target == 'sales':
                targets.append(book.total_sales)
            elif target == 'rating':
                targets.append(book.average_rating)
            elif target == 'roi':
                roi = self.calculate_roi(book.book_id)
                targets.append(roi.get('roi_percentage', 0))

        if len(features) < 5:
            logger.warning("Insufficient data for model training")
            return None

        # Train model
        X = np.array(features)
        y = np.array(targets)

        # Normalize features
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)

        # Train linear regression
        model = LinearRegression()
        model.fit(X_scaled, y)

        # Calculate metrics
        predictions = model.predict(X_scaled)
        r_squared = model.score(X_scaled, y)

        # Build predictor
        weights = {
            feature_names[i]: model.coef_[i]
            for i in range(len(feature_names))
        }

        predictor = SuccessPredictor(
            features=feature_names,
            weights=weights,
            accuracy=r_squared * 100,
            r_squared=r_squared
        )

        # Cache predictor
        self.predictors[target] = predictor

        logger.info(f"Built prediction model for {target} with R²={r_squared:.3f}")
        return predictor

    def predict_success(
        self,
        quality_score: float,
        word_count: int,
        genre: str,
        price: float = 2.99
    ) -> Dict[str, float]:
        """
        Predict success for a new book.

        Args:
            quality_score: Book quality score
            word_count: Word count
            genre: Book genre
            price: Book price

        Returns:
            Success predictions
        """
        predictions = {}

        # Build predictors if not cached
        if 'sales' not in self.predictors:
            self.build_prediction_model('sales')
        if 'rating' not in self.predictors:
            self.build_prediction_model('rating')
        if 'roi' not in self.predictors:
            self.build_prediction_model('roi')

        # Get genre encoding
        genres = list(set(b.genre for b in self.books.values()))
        genre_encoded = genres.index(genre) if genre in genres else 0

        # Prepare features
        features = {
            'quality_score': quality_score,
            'word_count': word_count / 1000,
            'chapters': 20,  # Default
            'price': price,
            'genre_encoded': genre_encoded
        }

        # Make predictions
        for target, predictor in self.predictors.items():
            if predictor:
                predictions[f'predicted_{target}'] = predictor.predict(features)

        # Add confidence based on model accuracy
        avg_accuracy = statistics.mean([
            p.accuracy for p in self.predictors.values() if p
        ])
        predictions['confidence'] = avg_accuracy

        return predictions

    def generate_dashboard_data(self) -> Dict[str, Any]:
        """
        Generate data for analytics dashboard.

        Returns:
            Dashboard data
        """
        dashboard = {
            'summary': {
                'total_books': len(self.books),
                'total_sales': sum(b.total_sales for b in self.books.values()),
                'total_revenue': sum(b.revenue for b in self.books.values()),
                'total_profit': sum(b.profit for b in self.books.values()),
                'avg_rating': statistics.mean([
                    b.average_rating for b in self.books.values()
                    if b.average_rating > 0
                ]) if any(b.average_rating > 0 for b in self.books.values()) else 0
            },
            'top_performers': [],
            'recent_books': [],
            'genre_breakdown': {},
            'trends': {}
        }

        # Top performers by sales
        sorted_books = sorted(
            self.books.values(),
            key=lambda b: b.total_sales,
            reverse=True
        )

        dashboard['top_performers'] = [
            {
                'title': b.title,
                'genre': b.genre,
                'sales': b.total_sales,
                'revenue': b.revenue,
                'rating': b.average_rating,
                'roi': self.calculate_roi(b.book_id).get('roi_percentage', 0)
            }
            for b in sorted_books[:10]
        ]

        # Recent books
        recent_books = sorted(
            self.books.values(),
            key=lambda b: b.published_date,
            reverse=True
        )

        dashboard['recent_books'] = [
            {
                'title': b.title,
                'published': b.published_date,
                'quality_score': b.quality_score,
                'sales': b.total_sales
            }
            for b in recent_books[:10]
        ]

        # Genre breakdown
        for book in self.books.values():
            if book.genre not in dashboard['genre_breakdown']:
                dashboard['genre_breakdown'][book.genre] = {
                    'count': 0,
                    'total_sales': 0,
                    'total_revenue': 0,
                    'avg_rating': []
                }

            dashboard['genre_breakdown'][book.genre]['count'] += 1
            dashboard['genre_breakdown'][book.genre]['total_sales'] += book.total_sales
            dashboard['genre_breakdown'][book.genre]['total_revenue'] += book.revenue
            if book.average_rating > 0:
                dashboard['genre_breakdown'][book.genre]['avg_rating'].append(
                    book.average_rating
                )

        # Calculate genre averages
        for genre, data in dashboard['genre_breakdown'].items():
            if data['avg_rating']:
                data['avg_rating'] = statistics.mean(data['avg_rating'])
            else:
                data['avg_rating'] = 0

        # Sales trends (last 30 days)
        daily_totals = {}
        for book in self.books.values():
            for date, sales in book.daily_sales.items():
                if date not in daily_totals:
                    daily_totals[date] = 0
                daily_totals[date] += sales

        dashboard['trends']['daily_sales'] = [
            {'date': date, 'sales': sales}
            for date, sales in sorted(daily_totals.items())[-30:]
        ]

        return dashboard

    def export_report(self, output_path: Optional[Path] = None) -> Path:
        """
        Export analytics report.

        Args:
            output_path: Optional output path

        Returns:
            Path to report file
        """
        if output_path is None:
            output_path = self.workspace / f"analytics_report_{datetime.now().strftime('%Y%m%d')}.json"

        report = {
            'generated_at': datetime.now().isoformat(),
            'dashboard': self.generate_dashboard_data(),
            'success_factors': self.analyze_success_factors(),
            'roi_analysis': {
                book_id: self.calculate_roi(book_id)
                for book_id in self.books.keys()
            }
        }

        output_path.write_text(json.dumps(report, indent=2), encoding='utf-8')
        logger.info(f"Exported analytics report to {output_path}")

        return output_path

    def _calculate_days_to_break_even(self, book: BookPerformance) -> int:
        """Calculate days to break even."""
        if not book.daily_sales:
            return -1

        total_cost = book.generation_cost + book.marketing_cost
        cumulative_revenue = 0
        days = 0

        for date in sorted(book.daily_sales.keys()):
            days += 1
            cumulative_revenue += book.daily_sales[date] * book.price
            if cumulative_revenue >= total_cost:
                return days

        return -1  # Not yet broken even

    def _save_book_performance(self, book: BookPerformance):
        """Save book performance to database."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            INSERT OR REPLACE INTO book_performance
            (book_id, title, author, genre, published_date,
             quality_score, word_count, data, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        """, (book.book_id, book.title, book.author, book.genre,
              book.published_date, book.quality_score, book.word_count,
              json.dumps(asdict(book))))

        conn.commit()
        conn.close()

    def _save_daily_metric(
        self,
        book_id: str,
        date: str,
        metric_type: str,
        value: float
    ):
        """Save daily metric to database."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            INSERT OR REPLACE INTO daily_metrics
            (book_id, date, metric_type, value)
            VALUES (?, ?, ?, ?)
        """, (book_id, date, metric_type, value))

        conn.commit()
        conn.close()

    def _load_from_database(self):
        """Load existing data from database."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Load books
        cursor.execute("SELECT data FROM book_performance")
        for row in cursor.fetchall():
            book_data = json.loads(row[0])
            book = BookPerformance(**book_data)
            self.books[book.book_id] = book

        conn.close()

        logger.info(f"Loaded {len(self.books)} books from database")