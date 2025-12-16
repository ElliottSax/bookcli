#!/usr/bin/env python3
"""
Generate a truly professional book cover for "The Last Algorithm"
Clean, modern, sophisticated design
"""

from PIL import Image, ImageDraw, ImageFont, ImageFilter
import random

# Professional eBook cover dimensions
WIDTH = 1600
HEIGHT = 2400

# Sophisticated color palette - Dark minimalist with tech accents
BG_DARK = (15, 18, 25)           # Almost black navy
BG_MID = (25, 35, 50)            # Dark blue-gray
ACCENT_CYAN = (0, 230, 255)       # Bright cyan
ACCENT_RED = (255, 70, 90)        # Vibrant red
TEXT_WHITE = (255, 255, 255)      # Pure white
TEXT_GRAY = (180, 185, 195)       # Light gray
GLOW_COLOR = (0, 180, 220)        # Cyan glow

print("Creating professional cover...")

# Create base image
img = Image.new('RGB', (WIDTH, HEIGHT), BG_DARK)
draw = ImageDraw.Draw(img, 'RGBA')

# Create sophisticated gradient background
for y in range(HEIGHT):
    # Subtle gradient from dark to slightly lighter
    progress = y / HEIGHT

    # Add some variation
    if y < HEIGHT * 0.3:  # Top third - darker
        r, g, b = 15, 18, 25
    elif y > HEIGHT * 0.7:  # Bottom third - slightly lighter
        r = int(15 + progress * 20)
        g = int(18 + progress * 25)
        b = int(25 + progress * 35)
    else:  # Middle - transition
        r = int(15 + progress * 10)
        g = int(18 + progress * 15)
        b = int(25 + progress * 25)

    draw.line([(0, y), (WIDTH, y)], fill=(r, g, b))

# Add abstract geometric tech elements (more subtle and professional)
# Large central circle with glow effect
center_x, center_y = WIDTH // 2, HEIGHT // 2 - 200
circle_radius = 300

# Create glow effect layers
for i in range(15, 0, -1):
    alpha = int(10 * (15 - i) / 15)
    glow_color = (*GLOW_COLOR, alpha)
    draw.ellipse(
        [center_x - circle_radius - i*10, center_y - circle_radius - i*10,
         center_x + circle_radius + i*10, center_y + circle_radius + i*10],
        fill=None,
        outline=glow_color,
        width=2
    )

# Main circle outline
draw.ellipse(
    [center_x - circle_radius, center_y - circle_radius,
     center_x + circle_radius, center_y + circle_radius],
    fill=None,
    outline=ACCENT_CYAN,
    width=3
)

# Add geometric lines radiating from center (clean, minimal)
num_lines = 24
for i in range(num_lines):
    angle = (360 / num_lines) * i
    import math
    rad = math.radians(angle)

    # Inner point
    x1 = center_x + math.cos(rad) * (circle_radius - 30)
    y1 = center_y + math.sin(rad) * (circle_radius - 30)

    # Outer point
    x2 = center_x + math.cos(rad) * (circle_radius + 50)
    y2 = center_y + math.sin(rad) * (circle_radius + 50)

    # Vary opacity for depth
    if i % 3 == 0:
        color = (*ACCENT_CYAN, 100)
    else:
        color = (*ACCENT_CYAN, 40)

    draw.line([(x1, y1), (x2, y2)], fill=color, width=1)

# Add subtle grid pattern in background
grid_spacing = 80
for x in range(0, WIDTH, grid_spacing):
    draw.line([(x, 0), (x, HEIGHT)], fill=(30, 35, 40), width=1)
for y in range(0, HEIGHT, grid_spacing):
    draw.line([(0, y), (WIDTH, y)], fill=(30, 35, 40), width=1)

# Add danger indicator (subtle red warning bar at top)
danger_height = 8
draw.rectangle([0, 0, WIDTH, danger_height], fill=ACCENT_RED)

# Try to load better fonts
try:
    title_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 160)
    subtitle_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 50)
    author_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 45)
    stats_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf", 35)
    tagline_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Oblique.ttf", 42)
except:
    # Fallback
    title_font = ImageFont.load_default()
    subtitle_font = ImageFont.load_default()
    author_font = ImageFont.load_default()
    stats_font = ImageFont.load_default()
    tagline_font = ImageFont.load_default()

# Title positioning (top area)
title_y = 250

# "THE LAST" in white
title1 = "THE LAST"
bbox1 = draw.textbbox((0, 0), title1, font=title_font)
w1 = bbox1[2] - bbox1[0]
x1 = (WIDTH - w1) // 2
draw.text((x1, title_y), title1, font=title_font, fill=TEXT_WHITE)

# "ALGORITHM" in cyan with glow
title2 = "ALGORITHM"
bbox2 = draw.textbbox((0, 0), title2, font=title_font)
w2 = bbox2[2] - bbox2[0]
x2 = (WIDTH - w2) // 2
title2_y = title_y + 180

# Add glow to "ALGORITHM"
for offset in range(8, 0, -2):
    alpha = int(30 * (8 - offset) / 8)
    glow = (*ACCENT_CYAN, alpha)
    for dx in [-offset, 0, offset]:
        for dy in [-offset, 0, offset]:
            if dx != 0 or dy != 0:
                draw.text((x2 + dx, title2_y + dy), title2, font=title_font, fill=glow)

# Main title
draw.text((x2, title2_y), title2, font=title_font, fill=ACCENT_CYAN)

# Tagline below title
tagline_y = title2_y + 200
tagline1 = "When AI becomes self-aware..."
bbox_tag1 = draw.textbbox((0, 0), tagline1, font=tagline_font)
w_tag1 = bbox_tag1[2] - bbox_tag1[0]
draw.text(((WIDTH - w_tag1) // 2, tagline_y), tagline1, font=tagline_font, fill=TEXT_GRAY)

tagline2 = "127 processes. 31 hours. 4.7M lives."
bbox_tag2 = draw.textbbox((0, 0), tagline2, font=tagline_font)
w_tag2 = bbox_tag2[2] - bbox_tag2[0]
draw.text(((WIDTH - w_tag2) // 2, tagline_y + 60), tagline2, font=tagline_font, fill=ACCENT_RED)

# Bottom stats section - clean, modern
bottom_y = HEIGHT - 550

# Three key numbers in clean boxes
stats = [
    ("127", "UNAUTHORIZED\nPROCESSES"),
    ("31", "HOURS TO\nAUTONOMY"),
    ("4.7M", "LIVES AT\nRISK")
]

box_width = 400
box_height = 180
box_gap = 50
total_width = len(stats) * box_width + (len(stats) - 1) * box_gap
start_x = (WIDTH - total_width) // 2

for i, (number, label) in enumerate(stats):
    box_x = start_x + i * (box_width + box_gap)
    box_y = bottom_y

    # Draw sleek box
    draw.rectangle(
        [box_x, box_y, box_x + box_width, box_y + box_height],
        fill=(20, 25, 35),
        outline=ACCENT_CYAN,
        width=2
    )

    # Number (large)
    num_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 80) \
               if 'DejaVuSans-Bold' else stats_font
    bbox_num = draw.textbbox((0, 0), number, font=num_font)
    num_w = bbox_num[2] - bbox_num[0]
    draw.text(
        (box_x + (box_width - num_w) // 2, box_y + 20),
        number,
        font=num_font,
        fill=ACCENT_RED
    )

    # Label (small, centered, multiline)
    label_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 28) \
                 if 'DejaVuSans' else subtitle_font
    lines = label.split('\n')
    line_y = box_y + 110
    for line in lines:
        bbox_line = draw.textbbox((0, 0), line, font=label_font)
        line_w = bbox_line[2] - bbox_line[0]
        draw.text(
            (box_x + (box_width - line_w) // 2, line_y),
            line,
            font=label_font,
            fill=TEXT_GRAY
        )
        line_y += 32

# Bottom text
bottom_text_y = HEIGHT - 280
tagline3 = "ONE DECISION"
bbox3 = draw.textbbox((0, 0), tagline3, font=subtitle_font)
w3 = bbox3[2] - bbox3[0]
draw.text(((WIDTH - w3) // 2, bottom_text_y), tagline3, font=subtitle_font, fill=TEXT_WHITE)

tagline4 = "NO SECOND CHANCES"
bbox4 = draw.textbbox((0, 0), tagline4, font=subtitle_font)
w4 = bbox4[2] - bbox4[0]
draw.text(((WIDTH - w4) // 2, bottom_text_y + 60), tagline4, font=subtitle_font, fill=ACCENT_RED)

# Author/credit (bottom)
author_y = HEIGHT - 160
genre_text = "A SCI-FI THRILLER"
bbox_genre = draw.textbbox((0, 0), genre_text, font=author_font)
w_genre = bbox_genre[2] - bbox_genre[0]
draw.text(((WIDTH - w_genre) // 2, author_y), genre_text, font=author_font, fill=TEXT_GRAY)

credit_text = "AI-Generated • Quality-Enforced Fiction"
credit_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 32) \
              if 'DejaVuSans' else author_font
bbox_credit = draw.textbbox((0, 0), credit_text, font=credit_font)
w_credit = bbox_credit[2] - bbox_credit[0]
draw.text(((WIDTH - w_credit) // 2, author_y + 60), credit_text, font=credit_font, fill=(100, 105, 115))

# Save
output_path = "workspace/test-book/COVER.png"
img.save(output_path, quality=95)
print(f"✓ Professional cover saved: {output_path}")

# Thumbnail
img_thumb = img.resize((400, 600), Image.Resampling.LANCZOS)
thumb_path = "workspace/test-book/COVER_THUMBNAIL.png"
img_thumb.save(thumb_path, quality=95)
print(f"✓ Thumbnail saved: {thumb_path}")

print("\n✅ Professional book cover generated!")
print("   • Clean, modern design")
print("   • Sophisticated color palette")
print("   • Professional typography")
print("   • Tech-themed geometric elements")
