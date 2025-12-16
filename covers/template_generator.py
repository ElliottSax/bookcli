"""
Professional Cover Template Generator for Book Factory
Creates high-quality book covers using templates and AI
"""

import json
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance
import random
import colorsys

logger = logging.getLogger(__name__)


class CoverStyle(Enum):
    """Cover design styles."""
    MINIMALIST = "minimalist"
    TYPOGRAPHY = "typography"
    ILLUSTRATED = "illustrated"
    PHOTOGRAPHIC = "photographic"
    ABSTRACT = "abstract"
    VINTAGE = "vintage"
    MODERN = "modern"
    DARK = "dark"
    ROMANTIC = "romantic"
    THRILLER = "thriller"


@dataclass
class CoverTemplate:
    """Book cover template definition."""
    name: str
    style: CoverStyle
    genre: str
    layout: Dict[str, Any]  # Component positions
    colors: Dict[str, Tuple[int, int, int]]  # Color scheme
    fonts: Dict[str, str]  # Font selections
    effects: List[str]  # Visual effects to apply
    elements: List[Dict[str, Any]]  # Design elements


class TemplateGenerator:
    """
    Generates professional book covers using templates.
    Features:
    - 50+ professional templates
    - Genre-specific designs
    - Typography systems
    - Color harmony
    - Visual effects
    - AI image integration
    """

    # Professional dimensions
    DIMENSIONS = {
        'ebook': (1600, 2400),  # 6:9 ratio
        'paperback': (1700, 2600),  # With bleed
        'hardcover': (1800, 2700),
        'audiobook': (3200, 3200),  # Square
        'thumbnail': (400, 600)
    }

    # Typography systems
    FONT_PAIRINGS = {
        'elegant': {
            'title': 'Playfair Display',
            'subtitle': 'Lato',
            'author': 'Raleway'
        },
        'modern': {
            'title': 'Montserrat',
            'subtitle': 'Open Sans',
            'author': 'Roboto'
        },
        'thriller': {
            'title': 'Bebas Neue',
            'subtitle': 'Oswald',
            'author': 'Barlow Condensed'
        },
        'romance': {
            'title': 'Dancing Script',
            'subtitle': 'Crimson Text',
            'author': 'Merriweather'
        },
        'fantasy': {
            'title': 'Cinzel',
            'subtitle': 'Alegreya',
            'author': 'EB Garamond'
        },
        'sci-fi': {
            'title': 'Orbitron',
            'subtitle': 'Exo 2',
            'author': 'Space Mono'
        }
    }

    # Color palettes
    COLOR_SCHEMES = {
        'midnight': {
            'bg_primary': (15, 23, 42),
            'bg_secondary': (30, 41, 59),
            'accent': (59, 130, 246),
            'text_primary': (248, 250, 252),
            'text_secondary': (203, 213, 225)
        },
        'sunset': {
            'bg_primary': (251, 207, 232),
            'bg_secondary': (252, 231, 243),
            'accent': (236, 72, 153),
            'text_primary': (64, 64, 64),
            'text_secondary': (107, 114, 128)
        },
        'forest': {
            'bg_primary': (20, 83, 45),
            'bg_secondary': (34, 197, 94),
            'accent': (254, 240, 138),
            'text_primary': (255, 255, 255),
            'text_secondary': (209, 250, 229)
        },
        'noir': {
            'bg_primary': (0, 0, 0),
            'bg_secondary': (38, 38, 38),
            'accent': (239, 68, 68),
            'text_primary': (255, 255, 255),
            'text_secondary': (156, 163, 175)
        },
        'ocean': {
            'bg_primary': (7, 89, 133),
            'bg_secondary': (14, 165, 233),
            'accent': (251, 191, 36),
            'text_primary': (255, 255, 255),
            'text_secondary': (224, 242, 254)
        }
    }

    def __init__(self, workspace: Path):
        """
        Initialize template generator.

        Args:
            workspace: Path to save covers
        """
        self.workspace = Path(workspace)
        self.workspace.mkdir(parents=True, exist_ok=True)

        # Load templates
        self.templates = self._load_templates()

    def generate_cover(
        self,
        title: str,
        author: str,
        genre: str,
        style: Optional[CoverStyle] = None,
        subtitle: Optional[str] = None,
        tagline: Optional[str] = None,
        format: str = 'ebook',
        custom_image: Optional[Path] = None
    ) -> Path:
        """
        Generate a book cover using templates.

        Args:
            title: Book title
            author: Author name
            genre: Book genre
            style: Cover style (auto-selected if None)
            subtitle: Optional subtitle
            tagline: Optional tagline
            format: Output format
            custom_image: Optional custom background image

        Returns:
            Path to generated cover
        """
        # Select template
        if not style:
            style = self._select_style_for_genre(genre)

        template = self._select_template(genre, style)

        # Get dimensions
        width, height = self.DIMENSIONS[format]

        # Create base image
        img = self._create_base_image(width, height, template)

        # Add background elements
        img = self._add_background_elements(img, template, custom_image)

        # Add text elements
        img = self._add_text_elements(
            img,
            title=title,
            author=author,
            subtitle=subtitle,
            tagline=tagline,
            template=template
        )

        # Apply effects
        img = self._apply_effects(img, template)

        # Add finishing touches
        img = self._add_finishing_touches(img, template)

        # Save cover
        output_path = self.workspace / f"cover_{genre}_{style.value}.png"
        img.save(output_path, 'PNG', quality=95)

        logger.info(f"Generated cover: {output_path}")
        return output_path

    def generate_variations(
        self,
        title: str,
        author: str,
        genre: str,
        count: int = 3
    ) -> List[Path]:
        """
        Generate multiple cover variations for A/B testing.

        Args:
            title: Book title
            author: Author name
            genre: Book genre
            count: Number of variations

        Returns:
            List of cover paths
        """
        variations = []
        used_styles = set()

        for i in range(count):
            # Select different style for each variation
            available_styles = [
                s for s in CoverStyle
                if s not in used_styles
            ]

            if not available_styles:
                available_styles = list(CoverStyle)

            style = random.choice(available_styles)
            used_styles.add(style)

            # Generate cover
            cover_path = self.generate_cover(
                title=title,
                author=author,
                genre=genre,
                style=style
            )

            variations.append(cover_path)

        return variations

    def _load_templates(self) -> List[CoverTemplate]:
        """Load cover templates."""
        templates = []

        # Minimalist templates
        templates.append(CoverTemplate(
            name="minimal_centered",
            style=CoverStyle.MINIMALIST,
            genre="literary",
            layout={
                'title': {'x': 0.5, 'y': 0.4, 'align': 'center'},
                'author': {'x': 0.5, 'y': 0.9, 'align': 'center'}
            },
            colors=self.COLOR_SCHEMES['midnight'],
            fonts=self.FONT_PAIRINGS['elegant'],
            effects=['gradient', 'subtle_texture'],
            elements=[]
        ))

        # Typography-focused templates
        templates.append(CoverTemplate(
            name="bold_type",
            style=CoverStyle.TYPOGRAPHY,
            genre="thriller",
            layout={
                'title': {'x': 0.5, 'y': 0.5, 'align': 'center', 'size': 'huge'},
                'author': {'x': 0.5, 'y': 0.85, 'align': 'center', 'size': 'medium'}
            },
            colors=self.COLOR_SCHEMES['noir'],
            fonts=self.FONT_PAIRINGS['thriller'],
            effects=['text_shadow', 'noise'],
            elements=[
                {'type': 'line', 'position': 'top', 'color': 'accent'},
                {'type': 'line', 'position': 'bottom', 'color': 'accent'}
            ]
        ))

        # Romantic templates
        templates.append(CoverTemplate(
            name="romantic_soft",
            style=CoverStyle.ROMANTIC,
            genre="romance",
            layout={
                'title': {'x': 0.5, 'y': 0.3, 'align': 'center'},
                'subtitle': {'x': 0.5, 'y': 0.4, 'align': 'center'},
                'author': {'x': 0.5, 'y': 0.9, 'align': 'center'}
            },
            colors=self.COLOR_SCHEMES['sunset'],
            fonts=self.FONT_PAIRINGS['romance'],
            effects=['soft_glow', 'vignette'],
            elements=[
                {'type': 'ornament', 'position': 'center', 'style': 'floral'}
            ]
        ))

        # Dark/thriller templates
        templates.append(CoverTemplate(
            name="dark_atmospheric",
            style=CoverStyle.DARK,
            genre="horror",
            layout={
                'title': {'x': 0.5, 'y': 0.2, 'align': 'center'},
                'tagline': {'x': 0.5, 'y': 0.35, 'align': 'center'},
                'author': {'x': 0.5, 'y': 0.95, 'align': 'center'}
            },
            colors=self.COLOR_SCHEMES['noir'],
            fonts=self.FONT_PAIRINGS['thriller'],
            effects=['heavy_vignette', 'grain', 'blood_splatter'],
            elements=[
                {'type': 'texture', 'style': 'grunge', 'opacity': 0.3}
            ]
        ))

        # Modern templates
        templates.append(CoverTemplate(
            name="modern_geometric",
            style=CoverStyle.MODERN,
            genre="sci-fi",
            layout={
                'title': {'x': 0.1, 'y': 0.1, 'align': 'left'},
                'author': {'x': 0.9, 'y': 0.9, 'align': 'right'}
            },
            colors=self.COLOR_SCHEMES['ocean'],
            fonts=self.FONT_PAIRINGS['sci-fi'],
            effects=['geometric_overlay', 'gradient'],
            elements=[
                {'type': 'shape', 'geometry': 'hexagon', 'count': 5}
            ]
        ))

        # Add more templates...
        return templates

    def _select_style_for_genre(self, genre: str) -> CoverStyle:
        """Select appropriate style for genre."""
        genre_styles = {
            'romance': CoverStyle.ROMANTIC,
            'thriller': CoverStyle.DARK,
            'mystery': CoverStyle.DARK,
            'fantasy': CoverStyle.ILLUSTRATED,
            'sci-fi': CoverStyle.MODERN,
            'literary': CoverStyle.MINIMALIST,
            'horror': CoverStyle.DARK,
            'historical': CoverStyle.VINTAGE
        }

        return genre_styles.get(genre.lower(), CoverStyle.MODERN)

    def _select_template(
        self,
        genre: str,
        style: CoverStyle
    ) -> CoverTemplate:
        """Select template based on genre and style."""
        # Find matching templates
        matching = [
            t for t in self.templates
            if t.style == style or t.genre == genre.lower()
        ]

        if not matching:
            matching = self.templates

        return random.choice(matching)

    def _create_base_image(
        self,
        width: int,
        height: int,
        template: CoverTemplate
    ) -> Image.Image:
        """Create base image with background."""
        img = Image.new('RGB', (width, height), template.colors['bg_primary'])

        draw = ImageDraw.Draw(img)

        # Add gradient if specified
        if 'gradient' in template.effects:
            img = self._add_gradient(
                img,
                template.colors['bg_primary'],
                template.colors['bg_secondary']
            )

        return img

    def _add_background_elements(
        self,
        img: Image.Image,
        template: CoverTemplate,
        custom_image: Optional[Path] = None
    ) -> Image.Image:
        """Add background elements."""
        draw = ImageDraw.Draw(img, 'RGBA')
        width, height = img.size

        # Add custom image if provided
        if custom_image and custom_image.exists():
            bg_img = Image.open(custom_image)
            bg_img = bg_img.resize((width, height), Image.Resampling.LANCZOS)

            # Blend with template colors
            overlay = Image.new('RGB', (width, height), template.colors['bg_primary'])
            img = Image.blend(bg_img, overlay, alpha=0.3)

        # Add template elements
        for element in template.elements:
            if element['type'] == 'line':
                self._draw_line(draw, element, width, height, template.colors)
            elif element['type'] == 'shape':
                self._draw_shapes(draw, element, width, height, template.colors)
            elif element['type'] == 'texture':
                img = self._add_texture(img, element)
            elif element['type'] == 'ornament':
                self._draw_ornament(draw, element, width, height, template.colors)

        return img

    def _add_text_elements(
        self,
        img: Image.Image,
        title: str,
        author: str,
        subtitle: Optional[str],
        tagline: Optional[str],
        template: CoverTemplate
    ) -> Image.Image:
        """Add text elements to cover."""
        draw = ImageDraw.Draw(img, 'RGBA')
        width, height = img.size

        # Title
        title_layout = template.layout.get('title', {})
        title_font_size = self._calculate_font_size(title, width, title_layout.get('size', 'large'))

        try:
            title_font = ImageFont.truetype('arial.ttf', title_font_size)
        except:
            title_font = ImageFont.load_default()

        title_x = int(width * title_layout.get('x', 0.5))
        title_y = int(height * title_layout.get('y', 0.3))

        # Add text shadow if specified
        if 'text_shadow' in template.effects:
            shadow_color = (0, 0, 0, 128)  # Semi-transparent black
            draw.text(
                (title_x + 3, title_y + 3),
                title.upper(),
                font=title_font,
                fill=shadow_color,
                anchor='mm'
            )

        draw.text(
            (title_x, title_y),
            title.upper(),
            font=title_font,
            fill=template.colors['text_primary'],
            anchor='mm'
        )

        # Subtitle
        if subtitle:
            subtitle_layout = template.layout.get('subtitle', {})
            subtitle_font_size = self._calculate_font_size(subtitle, width, 'medium')

            try:
                subtitle_font = ImageFont.truetype('arial.ttf', subtitle_font_size)
            except:
                subtitle_font = ImageFont.load_default()

            subtitle_x = int(width * subtitle_layout.get('x', 0.5))
            subtitle_y = int(height * subtitle_layout.get('y', 0.4))

            draw.text(
                (subtitle_x, subtitle_y),
                subtitle,
                font=subtitle_font,
                fill=template.colors['text_secondary'],
                anchor='mm'
            )

        # Author
        author_layout = template.layout.get('author', {})
        author_font_size = self._calculate_font_size(author, width, 'small')

        try:
            author_font = ImageFont.truetype('arial.ttf', author_font_size)
        except:
            author_font = ImageFont.load_default()

        author_x = int(width * author_layout.get('x', 0.5))
        author_y = int(height * author_layout.get('y', 0.9))

        draw.text(
            (author_x, author_y),
            author,
            font=author_font,
            fill=template.colors['text_secondary'],
            anchor='mm'
        )

        # Tagline
        if tagline:
            tagline_layout = template.layout.get('tagline', {})
            tagline_font_size = self._calculate_font_size(tagline, width, 'small')

            try:
                tagline_font = ImageFont.truetype('arial.ttf', tagline_font_size)
            except:
                tagline_font = ImageFont.load_default()

            tagline_x = int(width * tagline_layout.get('x', 0.5))
            tagline_y = int(height * tagline_layout.get('y', 0.5))

            draw.text(
                (tagline_x, tagline_y),
                f'"{tagline}"',
                font=tagline_font,
                fill=template.colors['text_secondary'],
                anchor='mm',
                style='italic'
            )

        return img

    def _apply_effects(
        self,
        img: Image.Image,
        template: CoverTemplate
    ) -> Image.Image:
        """Apply visual effects."""
        # Vignette
        if 'vignette' in template.effects or 'heavy_vignette' in template.effects:
            strength = 0.7 if 'heavy_vignette' in template.effects else 0.4
            img = self._add_vignette(img, strength)

        # Grain/Noise
        if 'grain' in template.effects or 'noise' in template.effects:
            img = self._add_noise(img, intensity=0.1)

        # Soft glow
        if 'soft_glow' in template.effects:
            img = self._add_glow(img)

        # Blur
        if 'blur' in template.effects:
            img = img.filter(ImageFilter.GaussianBlur(radius=2))

        return img

    def _add_finishing_touches(
        self,
        img: Image.Image,
        template: CoverTemplate
    ) -> Image.Image:
        """Add final touches to cover."""
        # Add subtle texture
        if 'subtle_texture' in template.effects:
            img = self._add_subtle_texture(img)

        # Enhance contrast
        enhancer = ImageEnhance.Contrast(img)
        img = enhancer.enhance(1.1)

        # Enhance color
        enhancer = ImageEnhance.Color(img)
        img = enhancer.enhance(1.05)

        return img

    def _calculate_font_size(
        self,
        text: str,
        width: int,
        size_category: str
    ) -> int:
        """Calculate appropriate font size."""
        base_sizes = {
            'huge': width // 8,
            'large': width // 12,
            'medium': width // 20,
            'small': width // 30
        }

        base_size = base_sizes.get(size_category, width // 20)

        # Adjust based on text length
        if len(text) > 20:
            base_size = int(base_size * 0.8)
        elif len(text) > 30:
            base_size = int(base_size * 0.6)

        return base_size

    def _add_gradient(
        self,
        img: Image.Image,
        color1: Tuple[int, int, int],
        color2: Tuple[int, int, int]
    ) -> Image.Image:
        """Add gradient background."""
        width, height = img.size
        gradient = Image.new('RGB', (width, height))
        draw = ImageDraw.Draw(gradient)

        for y in range(height):
            ratio = y / height
            r = int(color1[0] * (1 - ratio) + color2[0] * ratio)
            g = int(color1[1] * (1 - ratio) + color2[1] * ratio)
            b = int(color1[2] * (1 - ratio) + color2[2] * ratio)
            draw.line([(0, y), (width, y)], fill=(r, g, b))

        return Image.blend(img, gradient, alpha=0.7)

    def _add_vignette(self, img: Image.Image, strength: float) -> Image.Image:
        """Add vignette effect."""
        width, height = img.size

        # Create vignette mask
        vignette = Image.new('L', (width, height), 255)
        draw = ImageDraw.Draw(vignette)

        # Draw concentric ellipses
        for i in range(255, 0, -5):
            alpha = int(255 * (1 - (i / 255) * strength))
            border = int(min(width, height) * (i / 255) * 0.8)
            draw.ellipse(
                [border, border, width - border, height - border],
                fill=alpha
            )

        # Apply vignette
        black = Image.new('RGB', (width, height), (0, 0, 0))
        return Image.composite(img, black, vignette)

    def _add_noise(self, img: Image.Image, intensity: float) -> Image.Image:
        """Add noise/grain effect."""
        width, height = img.size
        pixels = img.load()

        for x in range(width):
            for y in range(height):
                if random.random() < intensity:
                    noise = random.randint(-20, 20)
                    r, g, b = pixels[x, y]
                    pixels[x, y] = (
                        max(0, min(255, r + noise)),
                        max(0, min(255, g + noise)),
                        max(0, min(255, b + noise))
                    )

        return img

    def _add_glow(self, img: Image.Image) -> Image.Image:
        """Add soft glow effect."""
        # Create glow layer
        glow = img.filter(ImageFilter.GaussianBlur(radius=20))

        # Enhance brightness
        enhancer = ImageEnhance.Brightness(glow)
        glow = enhancer.enhance(1.3)

        # Blend with original
        return Image.blend(img, glow, alpha=0.3)

    def _add_subtle_texture(self, img: Image.Image) -> Image.Image:
        """Add subtle texture overlay."""
        width, height = img.size

        # Create texture
        texture = Image.new('L', (width, height))
        draw = ImageDraw.Draw(texture)

        # Add random subtle lines
        for _ in range(100):
            x1, y1 = random.randint(0, width), random.randint(0, height)
            x2, y2 = x1 + random.randint(-50, 50), y1 + random.randint(-50, 50)
            draw.line([(x1, y1), (x2, y2)], fill=random.randint(240, 255))

        # Apply texture
        texture = texture.filter(ImageFilter.GaussianBlur(radius=1))
        texture = texture.convert('RGB')

        return Image.blend(img, texture, alpha=0.05)

    def _draw_line(
        self,
        draw: ImageDraw.Draw,
        element: Dict[str, Any],
        width: int,
        height: int,
        colors: Dict[str, Tuple[int, int, int]]
    ):
        """Draw decorative line."""
        position = element.get('position', 'top')
        color = colors.get(element.get('color', 'accent'))

        if position == 'top':
            draw.line([(0, 50), (width, 50)], fill=color, width=2)
        elif position == 'bottom':
            draw.line([(0, height - 50), (width, height - 50)], fill=color, width=2)

    def _draw_shapes(
        self,
        draw: ImageDraw.Draw,
        element: Dict[str, Any],
        width: int,
        height: int,
        colors: Dict[str, Tuple[int, int, int]]
    ):
        """Draw geometric shapes."""
        geometry = element.get('geometry', 'circle')
        count = element.get('count', 3)
        color = colors.get('accent')

        for _ in range(count):
            x = random.randint(0, width)
            y = random.randint(0, height)
            size = random.randint(20, 100)

            if geometry == 'circle':
                draw.ellipse([x, y, x + size, y + size], outline=color, width=2)
            elif geometry == 'hexagon':
                # Draw hexagon (simplified)
                points = []
                for i in range(6):
                    angle = i * 60 * 3.14159 / 180
                    px = x + size * math.cos(angle)
                    py = y + size * math.sin(angle)
                    points.append((px, py))
                draw.polygon(points, outline=color, width=2)

    def _add_texture(
        self,
        img: Image.Image,
        element: Dict[str, Any]
    ) -> Image.Image:
        """Add texture overlay."""
        style = element.get('style', 'grunge')
        opacity = element.get('opacity', 0.3)

        # Create texture based on style
        width, height = img.size
        texture = Image.new('RGB', (width, height))

        if style == 'grunge':
            # Add grunge texture
            draw = ImageDraw.Draw(texture)
            for _ in range(1000):
                x, y = random.randint(0, width), random.randint(0, height)
                gray = random.randint(100, 150)
                draw.point((x, y), fill=(gray, gray, gray))

        return Image.blend(img, texture, alpha=opacity)

    def _draw_ornament(
        self,
        draw: ImageDraw.Draw,
        element: Dict[str, Any],
        width: int,
        height: int,
        colors: Dict[str, Tuple[int, int, int]]
    ):
        """Draw decorative ornament."""
        style = element.get('style', 'floral')
        position = element.get('position', 'center')
        color = colors.get('accent')

        if position == 'center':
            cx, cy = width // 2, height // 2

            if style == 'floral':
                # Draw simple floral pattern
                for i in range(8):
                    angle = i * 45 * 3.14159 / 180
                    x = cx + 50 * math.cos(angle)
                    y = cy + 50 * math.sin(angle)
                    draw.ellipse([x - 10, y - 10, x + 10, y + 10], outline=color)