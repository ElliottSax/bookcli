#!/usr/bin/env python3
"""
Generate metadata.json for fiction books using Groq API
"""
import json
import os
import sys
from pathlib import Path
import requests
import time

# API Keys - loaded from environment (no hardcoded keys)
from api_config import GROQ_API_KEY
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"

BOOKS = [
    "A_Room_of_Her_Own_The_Founders_Manifesto",
    "A_View_from_Abroad_A_Semester_to_Remember",
    "Alice_in_the_Metaverse",
    "All_Quiet_on_the_Digital_Front",
    "Anti-Nephi-Lehis_The_Pacifists",
    "Brother_of_Jared_Submarine_Startup",
    "Descent_A_Deep_Sea_Thriller",
    "Dracula_Inc_Blood_Money",
    "Gadianton_Organized_Crime",
    "Ghosts_of_Gentrification"
]

def count_words_in_chapter(chapter_path):
    """Count words in a chapter file."""
    try:
        with open(chapter_path, 'r', encoding='utf-8') as f:
            content = f.read()
            return len(content.split())
    except (OSError, UnicodeDecodeError):
        return 0

def estimate_book_metrics(book_dir):
    """Estimate total word count and page count based on available chapters."""
    total_words = 0
    chapter_count = 0

    # Count words in all chapters
    for i in range(1, 51):  # Check up to 50 chapters
        chapter_file = book_dir / f"chapter_{i:02d}.md"
        if chapter_file.exists():
            words = count_words_in_chapter(chapter_file)
            if words > 0:
                total_words += words
                chapter_count += 1

    # If no chapters found, estimate based on typical book
    if total_words == 0:
        total_words = 75000  # Average novel length

    # Estimate pages (assuming 250 words per page)
    page_count = max(200, total_words // 250)

    return total_words, page_count

def call_groq_api(outline_content, chapter_content, word_count, page_count):
    """Call Groq API to generate metadata."""

    prompt = f"""Based on the following book outline and first chapter, generate comprehensive metadata for this fiction book.

OUTLINE:
{outline_content}

FIRST CHAPTER:
{chapter_content[:4000]}

BOOK METRICS:
- Estimated word count: {word_count}
- Estimated page count: {page_count}

Please generate a JSON object with the following fields:
1. title: The full book title (string)
2. subtitle: A compelling subtitle that captures the book's essence (string)
3. author: Author name (use "AI Generated Fiction" as placeholder) (string)
4. description_short: A 1-2 sentence hook that would appear on the back cover (string, max 150 characters)
5. description_long: A comprehensive 3-4 paragraph description suitable for online retailers (string, 300-500 words)
6. keywords: 7 relevant keywords/phrases for discoverability (array of strings)
7. categories: 3 primary genre/category classifications (array of strings)
8. age_rating: Appropriate age rating (string: "General", "Teen", "Young Adult", "Adult", "Mature")
9. page_count: The estimated page count I provided ({page_count})
10. word_count: The estimated word count I provided ({word_count})
11. comparable_titles: 3 similar published books readers might enjoy (array of strings in format "Title by Author")

Return ONLY the JSON object, no additional text or markdown formatting. Make sure it's valid JSON."""

    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }

    data = {
        "model": "llama-3.3-70b-versatile",
        "messages": [
            {
                "role": "user",
                "content": prompt
            }
        ],
        "temperature": 0.7,
        "max_tokens": 2000
    }

    try:
        response = requests.post(GROQ_API_URL, headers=headers, json=data, timeout=60)
        response.raise_for_status()

        result = response.json()
        content = result['choices'][0]['message']['content']

        # Try to parse the JSON response
        # Sometimes the API wraps it in markdown code blocks
        content = content.strip()
        if content.startswith('```json'):
            content = content[7:]
        if content.startswith('```'):
            content = content[3:]
        if content.endswith('```'):
            content = content[:-3]
        content = content.strip()

        metadata = json.loads(content)
        return metadata

    except Exception as e:
        print(f"Error calling Groq API: {e}")
        return None

def process_book(book_name, base_dir):
    """Process a single book and generate its metadata."""
    book_dir = base_dir / book_name
    outline_path = book_dir / "outline.json"
    chapter_path = book_dir / "chapter_01.md"
    metadata_path = book_dir / "metadata.json"

    # Check if metadata already exists
    if metadata_path.exists():
        print(f"✓ {book_name}: metadata.json already exists, skipping")
        return True

    # Check if required files exist
    if not outline_path.exists():
        print(f"✗ {book_name}: outline.json not found")
        return False

    if not chapter_path.exists():
        print(f"✗ {book_name}: chapter_01.md not found")
        return False

    print(f"Processing {book_name}...")

    # Read outline
    try:
        with open(outline_path, 'r', encoding='utf-8') as f:
            outline_content = f.read()
    except Exception as e:
        print(f"✗ {book_name}: Error reading outline.json: {e}")
        return False

    # Read first chapter
    try:
        with open(chapter_path, 'r', encoding='utf-8') as f:
            chapter_content = f.read()
    except Exception as e:
        print(f"✗ {book_name}: Error reading chapter_01.md: {e}")
        return False

    # Estimate book metrics
    word_count, page_count = estimate_book_metrics(book_dir)

    # Generate metadata via Groq API
    print(f"  Calling Groq API...")
    metadata = call_groq_api(outline_content, chapter_content, word_count, page_count)

    if metadata is None:
        print(f"✗ {book_name}: Failed to generate metadata")
        return False

    # Save metadata
    try:
        with open(metadata_path, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)
        print(f"✓ {book_name}: metadata.json created successfully")
        return True
    except Exception as e:
        print(f"✗ {book_name}: Error saving metadata.json: {e}")
        return False

def main():
    """Main function to process all books."""
    base_dir = Path("/mnt/e/projects/bookcli/output/fiction")

    if not base_dir.exists():
        print(f"Error: Directory {base_dir} does not exist")
        sys.exit(1)

    print(f"Starting metadata generation for {len(BOOKS)} books...")
    print(f"Using Groq API with llama-3.3-70b-versatile model\n")

    success_count = 0
    fail_count = 0

    for i, book in enumerate(BOOKS):
        if process_book(book, base_dir):
            success_count += 1
        else:
            fail_count += 1
        print()  # Blank line between books

        # Add delay between API calls to avoid rate limits
        if i < len(BOOKS) - 1:  # Don't wait after the last book
            time.sleep(3)

    print("=" * 60)
    print(f"Summary: {success_count} successful, {fail_count} failed")
    print("=" * 60)

if __name__ == "__main__":
    main()
