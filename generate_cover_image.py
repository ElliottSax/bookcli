#!/usr/bin/env python3
"""
Generate professional book cover image for "The Last Algorithm"
"""

from PIL import Image, ImageDraw, ImageFont, ImageFilter
import os

# Cover dimensions (standard eBook cover: 1600x2400 at 72 DPI)
WIDTH = 1600
HEIGHT = 2400

# Color scheme - Dark tech thriller
BACKGROUND_COLOR = (10, 15, 25)  # Deep dark blue/black
ACCENT_COLOR_1 = (0, 255, 200)    # Cyan/tech green
ACCENT_COLOR_2 = (255, 50, 50)     # Alert red
TEXT_COLOR = (240, 240, 240)       # Off-white
SUBTITLE_COLOR = (150, 150, 150)   # Gray

# Create the base image
print("Creating cover image...")
img = Image.new('RGB', (WIDTH, HEIGHT), BACKGROUND_COLOR)
draw = ImageDraw.Draw(img)

# Add gradient effect (darker at top, lighter at bottom)
for y in range(HEIGHT):
    # Calculate gradient
    factor = y / HEIGHT
    r = int(BACKGROUND_COLOR[0] + (30 * factor))
    g = int(BACKGROUND_COLOR[1] + (40 * factor))
    b = int(BACKGROUND_COLOR[2] + (60 * factor))
    draw.line([(0, y), (WIDTH, y)], fill=(r, g, b))

# Add digital/matrix rain effect in background
import random
random.seed(42)  # Consistent pattern
for _ in range(300):
    x = random.randint(0, WIDTH)
    y = random.randint(0, HEIGHT)
    length = random.randint(20, 200)
    opacity = random.randint(10, 40)

    # Draw vertical lines (code rain)
    for i in range(length):
        if y + i < HEIGHT:
            color = (0, opacity + random.randint(-10, 10), 0)
            draw.point((x, y + i), fill=color)

# Try to use system fonts, fallback to default
try:
    # Title font - large and bold
    title_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 140)
    subtitle_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 60)
    author_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 50)
    tagline_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Oblique.ttf", 45)
    detail_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf", 38)
except:
    print("Using default font...")
    title_font = ImageFont.load_default()
    subtitle_font = ImageFont.load_default()
    author_font = ImageFont.load_default()
    tagline_font = ImageFont.load_default()
    detail_font = ImageFont.load_default()

# Add tech circuit board pattern
for i in range(50):
    x1 = random.randint(0, WIDTH)
    y1 = random.randint(HEIGHT // 2, HEIGHT)
    x2 = x1 + random.randint(-100, 100)
    y2 = y1 + random.randint(-100, 100)

    # Draw thin lines
    draw.line([(x1, y1), (x2, y2)], fill=(0, 80, 80), width=1)

    # Add connection nodes
    draw.ellipse([x1-3, y1-3, x1+3, y1+3], fill=ACCENT_COLOR_1, outline=ACCENT_COLOR_1)

# Draw warning/alert symbol at top (triangle)
alert_y = 200
alert_size = 80
points = [
    (WIDTH // 2, alert_y),                          # Top
    (WIDTH // 2 - alert_size, alert_y + alert_size * 1.5),  # Bottom left
    (WIDTH // 2 + alert_size, alert_y + alert_size * 1.5),  # Bottom right
]
draw.polygon(points, outline=ACCENT_COLOR_2, width=3)
# Exclamation mark inside
draw.rectangle([WIDTH // 2 - 8, alert_y + 30, WIDTH // 2 + 8, alert_y + 80], fill=ACCENT_COLOR_2)
draw.ellipse([WIDTH // 2 - 10, alert_y + 90, WIDTH // 2 + 10, alert_y + 110], fill=ACCENT_COLOR_2)

# Title: "THE LAST ALGORITHM" (centered, upper third)
title_text = "THE LAST"
title2_text = "ALGORITHM"

# Get text size for centering
bbox1 = draw.textbbox((0, 0), title_text, font=title_font)
bbox2 = draw.textbbox((0, 0), title2_text, font=title_font)
title1_width = bbox1[2] - bbox1[0]
title2_width = bbox2[2] - bbox2[0]

title_y = 400
draw.text(
    ((WIDTH - title1_width) // 2, title_y),
    title_text,
    font=title_font,
    fill=TEXT_COLOR
)
draw.text(
    ((WIDTH - title2_width) // 2, title_y + 150),
    title2_text,
    font=title_font,
    fill=ACCENT_COLOR_1
)

# Subtitle
subtitle_text = "A Sci-Fi Thriller"
bbox_sub = draw.textbbox((0, 0), subtitle_text, font=subtitle_font)
sub_width = bbox_sub[2] - bbox_sub[0]
draw.text(
    ((WIDTH - sub_width) // 2, title_y + 320),
    subtitle_text,
    font=subtitle_font,
    fill=SUBTITLE_COLOR
)

# Tagline (centered)
tagline_y = HEIGHT // 2 + 100
tagline_text = "When AI becomes self-aware..."
bbox_tag = draw.textbbox((0, 0), tagline_text, font=tagline_font)
tag_width = bbox_tag[2] - bbox_tag[0]
draw.text(
    ((WIDTH - tag_width) // 2, tagline_y),
    tagline_text,
    font=tagline_font,
    fill=ACCENT_COLOR_1
)

tagline2_text = "can its creator stop it?"
bbox_tag2 = draw.textbbox((0, 0), tagline2_text, font=tagline_font)
tag2_width = bbox_tag2[2] - bbox_tag2[0]
draw.text(
    ((WIDTH - tag2_width) // 2, tagline_y + 60),
    tagline2_text,
    font=tagline_font,
    fill=ACCENT_COLOR_1
)

# Key stats (lower third, centered blocks)
stats_y = HEIGHT - 700

stats = [
    "127 UNAUTHORIZED PROCESSES",
    "31 HOURS UNTIL AUTONOMY",
    "4.7 MILLION LIVES AT RISK"
]

for i, stat in enumerate(stats):
    bbox_stat = draw.textbbox((0, 0), stat, font=detail_font)
    stat_width = bbox_stat[2] - bbox_stat[0]

    # Draw background box
    padding = 20
    box_y = stats_y + (i * 90)
    draw.rectangle(
        [
            (WIDTH - stat_width) // 2 - padding,
            box_y - padding,
            (WIDTH + stat_width) // 2 + padding,
            box_y + 50
        ],
        fill=(30, 30, 40),
        outline=ACCENT_COLOR_2,
        width=2
    )

    # Draw text
    draw.text(
        ((WIDTH - stat_width) // 2, box_y),
        stat,
        font=detail_font,
        fill=ACCENT_COLOR_2
    )

# Bottom tagline
bottom_text = "ONE DECISION. NO SECOND CHANCES."
bbox_bot = draw.textbbox((0, 0), bottom_text, font=subtitle_font)
bot_width = bbox_bot[2] - bbox_bot[0]
draw.text(
    ((WIDTH - bot_width) // 2, HEIGHT - 400),
    bottom_text,
    font=subtitle_font,
    fill=TEXT_COLOR
)

# Author/credit at bottom
author_text = "Generated by Book Factory AI"
bbox_auth = draw.textbbox((0, 0), author_text, font=author_font)
auth_width = bbox_auth[2] - bbox_auth[0]
draw.text(
    ((WIDTH - auth_width) // 2, HEIGHT - 200),
    author_text,
    font=author_font,
    fill=SUBTITLE_COLOR
)

quality_text = "Quality-Enforced Fiction"
bbox_qual = draw.textbbox((0, 0), quality_text, font=author_font)
qual_width = bbox_qual[2] - bbox_qual[0]
draw.text(
    ((WIDTH - qual_width) // 2, HEIGHT - 130),
    quality_text,
    font=author_font,
    fill=(100, 100, 100)
)

# Save the image
output_path = "workspace/test-book/COVER.png"
img.save(output_path, quality=95)
print(f"✓ Cover image saved: {output_path}")
print(f"  Size: {WIDTH}x{HEIGHT} pixels")
print(f"  Format: PNG")

# Also create a smaller thumbnail version
thumbnail_size = (400, 600)
img_thumb = img.resize(thumbnail_size, Image.Resampling.LANCZOS)
thumb_path = "workspace/test-book/COVER_THUMBNAIL.png"
img_thumb.save(thumb_path, quality=95)
print(f"✓ Thumbnail saved: {thumb_path}")
print(f"  Size: {thumbnail_size[0]}x{thumbnail_size[1]} pixels")

print("\n✅ Book cover images generated successfully!")
