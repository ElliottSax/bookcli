Assemble complete manuscript and format for KDP.

Parameters:
- BOOK=$1 (book name or path to chapters directory)
- TITLE=$2 (book title, optional - inferred from folder)
- AUTHOR=$3 (author name, optional - defaults to "Anonymous")

Steps:

1. Locate and verify chapters:
```bash
# Find chapter files
if [ -d "workspace/$BOOK/chapters" ]; then
    CHAPTER_DIR="workspace/$BOOK/chapters"
elif [ -d "$BOOK" ]; then
    CHAPTER_DIR="$BOOK"
else
    echo "Error: Cannot find chapters directory"
    exit 1
fi

ls "$CHAPTER_DIR"/chapter*.md 2>/dev/null || ls "$CHAPTER_DIR"/*.md
```

2. Use the KDP Book Assembler to build the book:
```python
from scripts.kdp_book_assembler import KDPBookAssembler, BookMetadata, assemble_book
import glob

# Collect chapter files in order
chapter_files = sorted(glob.glob(f"{chapter_dir}/chapter*.md")) or sorted(glob.glob(f"{chapter_dir}/*.md"))

# Create metadata
metadata = BookMetadata(
    title=title or book_name.replace('_', ' ').title(),
    author=author or "Anonymous",
    subtitle="",
    dedication="",
    about_author=""
)

# Build the book
assembler = KDPBookAssembler(output_dir=f"output/{book_name}")
result = assembler.build_book(
    chapters=[open(f).read() for f in chapter_files],
    metadata=metadata,
    generate_epub=True,
    generate_pdf=True,
    kdp_format="6x9"
)
```

3. Generated files:
   - `output/{BOOK}/{BOOK}.md` - Combined manuscript
   - `output/{BOOK}/{BOOK}.epub` - Kindle ePub format
   - `output/{BOOK}/{BOOK}.pdf` - KDP print-ready PDF (6x9")

4. Validate KDP compliance:
   - ePub under 650MB limit
   - PDF under 650MB limit
   - Proper margins for print

5. Generate production report with:
   - Total word count
   - Chapter count
   - File sizes
   - Format validation results
   - Upload instructions for KDP

6. Provide KDP upload instructions:
   - For Kindle eBook: Upload the .epub file
   - For Paperback: Upload the .pdf file
   - Cover requirements: 2560x1600px for eBook, calculated based on page count for print

Requirements:
- Pandoc installed: `apt install pandoc`
- Optional: kdp-book-generator (`npm install -g kdp-book-generator`)
- Optional: XeLaTeX for PDF (`apt install texlive-xetex`)

No check-ins - complete entire assembly process autonomously.
