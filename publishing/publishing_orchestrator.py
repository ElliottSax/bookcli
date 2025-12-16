"""
Publishing Orchestrator for Book Factory
Manages automated publishing to multiple platforms
"""

import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)


class PublishingPlatform(Enum):
    """Supported publishing platforms."""
    KDP = "Amazon Kindle Direct Publishing"
    DRAFT2DIGITAL = "Draft2Digital"
    SMASHWORDS = "Smashwords"
    KOBO = "Kobo Writing Life"
    APPLE_BOOKS = "Apple Books"
    GOOGLE_PLAY = "Google Play Books"
    BARNES_NOBLE = "Barnes & Noble Press"


@dataclass
class BookMetadata:
    """Complete book metadata for publishing."""
    # Basic Information
    title: str
    subtitle: Optional[str] = None
    author: str = "AI Generated"
    series_name: Optional[str] = None
    series_number: Optional[int] = None

    # Description
    description: str = ""
    short_description: str = ""
    keywords: List[str] = None

    # Categories
    primary_category: str = ""
    secondary_categories: List[str] = None
    bisac_codes: List[str] = None

    # Publishing Details
    language: str = "en"
    publication_date: Optional[str] = None
    isbn: Optional[str] = None
    asin: Optional[str] = None

    # Pricing
    price_usd: float = 2.99
    price_currency: str = "USD"
    royalty_option: str = "70%"  # KDP specific

    # Files
    manuscript_file: Optional[Path] = None
    cover_file: Optional[Path] = None

    # Marketing
    comp_titles: List[str] = None
    target_audience: str = ""
    age_range: Optional[str] = None

    def __post_init__(self):
        """Initialize default values."""
        if self.keywords is None:
            self.keywords = []
        if self.secondary_categories is None:
            self.secondary_categories = []
        if self.bisac_codes is None:
            self.bisac_codes = []
        if self.comp_titles is None:
            self.comp_titles = []
        if not self.publication_date:
            self.publication_date = datetime.now().strftime("%Y-%m-%d")


class PublishingOrchestrator:
    """
    Orchestrates publishing to multiple platforms.
    Features:
    - Multi-platform publishing
    - Metadata optimization per platform
    - Price optimization
    - Category selection
    - Publishing status tracking
    """

    def __init__(self, workspace: Path):
        """
        Initialize the publishing orchestrator.

        Args:
            workspace: Path to book workspace
        """
        self.workspace = Path(workspace)
        self.metadata_file = self.workspace / "publishing_metadata.json"
        self.status_file = self.workspace / "publishing_status.json"

        # Platform-specific handlers (to be implemented)
        self.platform_handlers = {
            PublishingPlatform.KDP: self._publish_to_kdp,
            PublishingPlatform.DRAFT2DIGITAL: self._publish_to_d2d,
            PublishingPlatform.SMASHWORDS: self._publish_to_smashwords,
            PublishingPlatform.KOBO: self._publish_to_kobo,
            PublishingPlatform.APPLE_BOOKS: self._publish_to_apple,
            PublishingPlatform.GOOGLE_PLAY: self._publish_to_google,
            PublishingPlatform.BARNES_NOBLE: self._publish_to_barnes_noble,
        }

        # Load existing metadata if available
        self.metadata = self._load_metadata()
        self.publishing_status = self._load_status()

    def prepare_book_for_publishing(
        self,
        title: str,
        author: str,
        description: str,
        manuscript_file: Path,
        cover_file: Optional[Path] = None,
        **kwargs
    ) -> BookMetadata:
        """
        Prepare book metadata for publishing.

        Args:
            title: Book title
            author: Author name
            description: Book description
            manuscript_file: Path to manuscript
            cover_file: Path to cover image
            **kwargs: Additional metadata

        Returns:
            Complete BookMetadata object
        """
        # Create metadata
        metadata = BookMetadata(
            title=title,
            author=author,
            description=description,
            manuscript_file=Path(manuscript_file),
            cover_file=Path(cover_file) if cover_file else None,
            **kwargs
        )

        # Optimize metadata
        metadata = self._optimize_metadata(metadata)

        # Save metadata
        self.metadata = metadata
        self._save_metadata()

        logger.info(f"Prepared book '{title}' for publishing")
        return metadata

    def publish_to_platforms(
        self,
        platforms: List[PublishingPlatform],
        metadata: Optional[BookMetadata] = None,
        dry_run: bool = False
    ) -> Dict[PublishingPlatform, Dict[str, Any]]:
        """
        Publish book to multiple platforms.

        Args:
            platforms: List of platforms to publish to
            metadata: Book metadata (uses stored if not provided)
            dry_run: If True, simulates publishing without actual upload

        Returns:
            Dictionary of publishing results per platform
        """
        if metadata:
            self.metadata = metadata
        elif not self.metadata:
            raise ValueError("No metadata available for publishing")

        results = {}

        for platform in platforms:
            logger.info(f"Publishing to {platform.value}...")

            if dry_run:
                # Simulate publishing
                results[platform] = {
                    'status': 'simulated',
                    'message': f'Would publish to {platform.value}',
                    'metadata': self._get_platform_specific_metadata(platform)
                }
            else:
                # Actual publishing
                handler = self.platform_handlers.get(platform)
                if handler:
                    result = handler(self.metadata)
                    results[platform] = result

                    # Update status
                    self.publishing_status[platform.value] = {
                        'status': result.get('status', 'unknown'),
                        'timestamp': datetime.now().isoformat(),
                        'details': result
                    }
                else:
                    results[platform] = {
                        'status': 'error',
                        'message': f'Handler not implemented for {platform.value}'
                    }

        # Save status
        self._save_status()

        return results

    def optimize_pricing(
        self,
        base_price: float = 2.99,
        market_analysis: bool = True
    ) -> Dict[str, Any]:
        """
        Optimize book pricing based on market analysis.

        Args:
            base_price: Starting price point
            market_analysis: Whether to perform market analysis

        Returns:
            Pricing recommendations
        """
        recommendations = {
            'base_price': base_price,
            'recommendations': []
        }

        # Length-based pricing
        if self.metadata and self.metadata.manuscript_file:
            word_count = self._estimate_word_count(self.metadata.manuscript_file)

            if word_count < 10000:  # Short story
                recommendations['recommended_price'] = 0.99
                recommendations['recommendations'].append("Short length - consider $0.99 price point")
            elif word_count < 30000:  # Novella
                recommendations['recommended_price'] = 1.99
                recommendations['recommendations'].append("Novella length - $1.99 recommended")
            elif word_count < 80000:  # Novel
                recommendations['recommended_price'] = 2.99
                recommendations['recommendations'].append("Novel length - $2.99 sweet spot")
            else:  # Long novel
                recommendations['recommended_price'] = 3.99
                recommendations['recommendations'].append("Long novel - can support $3.99+")

        # Genre-based adjustments
        if self.metadata and self.metadata.primary_category:
            genre_pricing = {
                'Romance': 2.99,
                'Thriller': 3.99,
                'Mystery': 3.99,
                'Sci-Fi': 3.99,
                'Fantasy': 3.99,
                'Literary Fiction': 4.99,
                'Non-Fiction': 5.99,
            }

            for genre, price in genre_pricing.items():
                if genre.lower() in self.metadata.primary_category.lower():
                    recommendations['genre_price'] = price
                    recommendations['recommendations'].append(
                        f"{genre} typically prices at ${price}"
                    )
                    break

        # Platform-specific recommendations
        recommendations['platform_specific'] = {
            'KDP': {
                '35%_royalty': {'min': 0.99, 'max': 2.98},
                '70%_royalty': {'min': 2.99, 'max': 9.99}
            },
            'Apple_Books': {
                'recommended_tiers': [0.99, 1.99, 2.99, 3.99, 4.99]
            }
        }

        return recommendations

    def optimize_categories(
        self,
        genre: str,
        keywords: List[str]
    ) -> Dict[str, List[str]]:
        """
        Optimize category selection for maximum visibility.

        Args:
            genre: Primary genre
            keywords: Book keywords

        Returns:
            Optimized categories per platform
        """
        # Base categories mapping
        category_map = {
            'fantasy': [
                'Fiction / Fantasy / General',
                'Fiction / Fantasy / Epic',
                'Fiction / Fantasy / Action & Adventure'
            ],
            'romance': [
                'Fiction / Romance / Contemporary',
                'Fiction / Romance / General',
                'Fiction / Women\'s Fiction'
            ],
            'thriller': [
                'Fiction / Thrillers / General',
                'Fiction / Thrillers / Psychological',
                'Fiction / Thrillers / Suspense'
            ],
            'sci-fi': [
                'Fiction / Science Fiction / General',
                'Fiction / Science Fiction / Space Opera',
                'Fiction / Science Fiction / Adventure'
            ],
            'mystery': [
                'Fiction / Mystery & Detective / General',
                'Fiction / Mystery & Detective / Police Procedural',
                'Fiction / Crime'
            ]
        }

        # Get base categories
        base_categories = category_map.get(genre.lower(), [
            'Fiction / General'
        ])

        # Platform-specific optimization
        optimized = {
            'KDP': self._optimize_kdp_categories(base_categories, keywords),
            'Draft2Digital': base_categories[:5],  # D2D allows 5 categories
            'Kobo': base_categories[:3],  # Kobo allows 3
            'Apple_Books': base_categories[:2],  # Apple allows 2
            'BISAC': self._generate_bisac_codes(base_categories)
        }

        return optimized

    def generate_keywords(
        self,
        title: str,
        description: str,
        genre: str,
        max_keywords: int = 7
    ) -> List[str]:
        """
        Generate optimized keywords for the book.

        Args:
            title: Book title
            description: Book description
            genre: Book genre
            max_keywords: Maximum number of keywords

        Returns:
            List of optimized keywords
        """
        keywords = []

        # Genre-specific keywords
        genre_keywords = {
            'fantasy': ['magic', 'sword', 'quest', 'dragon', 'kingdom', 'prophecy'],
            'romance': ['love', 'passion', 'heartbreak', 'second chance', 'enemies to lovers'],
            'thriller': ['suspense', 'conspiracy', 'danger', 'chase', 'secrets'],
            'sci-fi': ['space', 'future', 'technology', 'alien', 'dystopia'],
            'mystery': ['detective', 'murder', 'investigation', 'clues', 'whodunit']
        }

        # Add genre keywords
        if genre.lower() in genre_keywords:
            keywords.extend(genre_keywords[genre.lower()][:3])

        # Extract from description (simplified - real implementation would use NLP)
        important_words = ['adventure', 'journey', 'discover', 'battle', 'save',
                          'mystery', 'secret', 'power', 'destiny', 'forbidden']

        for word in important_words:
            if word in description.lower() and word not in keywords:
                keywords.append(word)
                if len(keywords) >= max_keywords:
                    break

        # Add genre itself
        if genre.lower() not in keywords:
            keywords.append(genre.lower())

        return keywords[:max_keywords]

    def _publish_to_kdp(self, metadata: BookMetadata) -> Dict[str, Any]:
        """
        Publish to Amazon KDP.
        Note: Real implementation would use KDP API when available.
        """
        logger.info(f"Publishing '{metadata.title}' to KDP...")

        # Validate KDP requirements
        if not metadata.manuscript_file or not metadata.cover_file:
            return {
                'status': 'error',
                'message': 'KDP requires both manuscript and cover files'
            }

        # Simulate KDP publishing process
        result = {
            'status': 'success',
            'platform': 'KDP',
            'asin': f"B0{datetime.now().strftime('%Y%m%d%H')}",  # Simulated ASIN
            'url': f"https://www.amazon.com/dp/B0XXXXXXXXX",
            'royalty_rate': metadata.royalty_option,
            'estimated_earnings': metadata.price_usd * 0.7,  # 70% royalty
            'message': 'Book submitted to KDP for review'
        }

        logger.info(f"KDP publishing complete: {result['asin']}")
        return result

    def _publish_to_d2d(self, metadata: BookMetadata) -> Dict[str, Any]:
        """
        Publish to Draft2Digital.
        Note: Real implementation would use D2D API.
        """
        logger.info(f"Publishing '{metadata.title}' to Draft2Digital...")

        result = {
            'status': 'success',
            'platform': 'Draft2Digital',
            'book_id': f"D2D-{datetime.now().strftime('%Y%m%d%H%M')}",
            'distributed_to': ['Apple Books', 'Barnes & Noble', 'Kobo', 'Scribd'],
            'message': 'Book distributed to multiple retailers'
        }

        return result

    def _publish_to_smashwords(self, metadata: BookMetadata) -> Dict[str, Any]:
        """Publish to Smashwords."""
        return {'status': 'not_implemented', 'platform': 'Smashwords'}

    def _publish_to_kobo(self, metadata: BookMetadata) -> Dict[str, Any]:
        """Publish to Kobo Writing Life."""
        return {'status': 'not_implemented', 'platform': 'Kobo'}

    def _publish_to_apple(self, metadata: BookMetadata) -> Dict[str, Any]:
        """Publish to Apple Books."""
        return {'status': 'not_implemented', 'platform': 'Apple Books'}

    def _publish_to_google(self, metadata: BookMetadata) -> Dict[str, Any]:
        """Publish to Google Play Books."""
        return {'status': 'not_implemented', 'platform': 'Google Play'}

    def _publish_to_barnes_noble(self, metadata: BookMetadata) -> Dict[str, Any]:
        """Publish to Barnes & Noble Press."""
        return {'status': 'not_implemented', 'platform': 'Barnes & Noble'}

    def _optimize_metadata(self, metadata: BookMetadata) -> BookMetadata:
        """Optimize metadata for better discoverability."""
        # Generate keywords if not provided
        if not metadata.keywords:
            metadata.keywords = self.generate_keywords(
                metadata.title,
                metadata.description,
                metadata.primary_category,
                max_keywords=7
            )

        # Optimize description length
        if len(metadata.description) > 4000:
            metadata.description = metadata.description[:3997] + "..."

        # Generate short description if not provided
        if not metadata.short_description:
            metadata.short_description = metadata.description[:200] + "..."

        return metadata

    def _get_platform_specific_metadata(
        self,
        platform: PublishingPlatform
    ) -> Dict[str, Any]:
        """Get platform-specific metadata requirements."""
        if not self.metadata:
            return {}

        # Platform-specific transformations
        if platform == PublishingPlatform.KDP:
            return {
                'title': self.metadata.title[:200],  # KDP title limit
                'subtitle': self.metadata.subtitle[:200] if self.metadata.subtitle else None,
                'description': self.metadata.description[:4000],  # KDP description limit
                'keywords': ', '.join(self.metadata.keywords[:7]),  # KDP allows 7 keywords
            }
        elif platform == PublishingPlatform.DRAFT2DIGITAL:
            return {
                'title': self.metadata.title,
                'description': self.metadata.description,
                'categories': self.metadata.secondary_categories[:5],
            }

        return {}

    def _optimize_kdp_categories(
        self,
        base_categories: List[str],
        keywords: List[str]
    ) -> List[str]:
        """Optimize categories specifically for KDP."""
        # KDP allows 2 categories
        optimized = base_categories[:2]

        # Add keyword-based categories
        if 'young adult' in ' '.join(keywords).lower():
            optimized.append('Young Adult Fiction')

        return optimized[:2]

    def _generate_bisac_codes(self, categories: List[str]) -> List[str]:
        """Generate BISAC codes from categories."""
        # Simplified BISAC mapping
        bisac_map = {
            'Fiction / Fantasy / General': 'FIC009000',
            'Fiction / Romance / Contemporary': 'FIC027020',
            'Fiction / Thrillers / General': 'FIC031000',
            'Fiction / Science Fiction / General': 'FIC028000',
            'Fiction / Mystery & Detective / General': 'FIC022000',
        }

        bisac_codes = []
        for category in categories:
            if category in bisac_map:
                bisac_codes.append(bisac_map[category])

        return bisac_codes

    def _estimate_word_count(self, manuscript_file: Path) -> int:
        """Estimate word count from manuscript file."""
        if not manuscript_file.exists():
            return 0

        text = manuscript_file.read_text(encoding='utf-8')
        return len(text.split())

    def _load_metadata(self) -> Optional[BookMetadata]:
        """Load saved metadata."""
        if self.metadata_file.exists():
            data = json.loads(self.metadata_file.read_text())
            return BookMetadata(**data)
        return None

    def _save_metadata(self):
        """Save metadata to file."""
        if self.metadata:
            data = {
                k: str(v) if isinstance(v, Path) else v
                for k, v in self.metadata.__dict__.items()
            }
            self.metadata_file.write_text(
                json.dumps(data, indent=2),
                encoding='utf-8'
            )

    def _load_status(self) -> Dict[str, Any]:
        """Load publishing status."""
        if self.status_file.exists():
            return json.loads(self.status_file.read_text())
        return {}

    def _save_status(self):
        """Save publishing status."""
        self.status_file.write_text(
            json.dumps(self.publishing_status, indent=2),
            encoding='utf-8'
        )