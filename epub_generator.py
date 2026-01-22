#!/usr/bin/env python3
"""
EPUB and PDF Generator for Books
Converts markdown chapters into publishable ebook formats.
"""

import os
import sys
import json
import re
import uuid
import zipfile
import subprocess
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict
from dataclasses import dataclass

from lib.logging_config import setup_logging, get_logger

setup_logging()
logger = get_logger(__name__)


@dataclass
class BookMetadata:
    """Book metadata for EPUB."""
    title: str
    author: str
    genre: str
    description: str
    language: str = "en"
    publisher: str = "AI Publishing"
    isbn: str = ""
    cover_path: Optional[Path] = None


class EPUBGenerator:
    """Generates EPUB files from markdown chapters."""

    def __init__(self):
        self.mime_type = "application/epub+zip"

    def markdown_to_html(self, markdown: str, title: str = "") -> str:
        """Convert markdown to basic HTML."""
        html = markdown

        # Headers
        html = re.sub(r'^### (.+)$', r'<h3>\1</h3>', html, flags=re.MULTILINE)
        html = re.sub(r'^## (.+)$', r'<h2>\1</h2>', html, flags=re.MULTILINE)
        html = re.sub(r'^# (.+)$', r'<h1>\1</h1>', html, flags=re.MULTILINE)

        # Bold and italic
        html = re.sub(r'\*\*\*(.+?)\*\*\*', r'<strong><em>\1</em></strong>', html)
        html = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', html)
        html = re.sub(r'\*(.+?)\*', r'<em>\1</em>', html)

        # Paragraphs
        paragraphs = html.split('\n\n')
        formatted = []
        for p in paragraphs:
            p = p.strip()
            if p and not p.startswith('<h'):
                formatted.append(f'<p>{p}</p>')
            else:
                formatted.append(p)

        html = '\n'.join(formatted)

        # Clean up
        html = html.replace('\n', ' ')
        html = re.sub(r'\s+', ' ', html)
        html = html.replace('</p> <p>', '</p>\n<p>')
        html = html.replace('</h1> ', '</h1>\n')
        html = html.replace('</h2> ', '</h2>\n')
        html = html.replace('</h3> ', '</h3>\n')

        return html

    def create_chapter_xhtml(self, title: str, content: str, chapter_num: int) -> str:
        """Create XHTML for a chapter."""
        html_content = self.markdown_to_html(content, title)

        return f'''<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml" lang="en">
<head>
    <meta charset="UTF-8"/>
    <title>{title}</title>
    <link rel="stylesheet" type="text/css" href="style.css"/>
</head>
<body>
    <section class="chapter" id="chapter{chapter_num}">
        <h1 class="chapter-title">{title}</h1>
        {html_content}
    </section>
</body>
</html>'''

    def create_title_page(self, metadata: BookMetadata) -> str:
        """Create title page XHTML."""
        return f'''<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml" lang="en">
<head>
    <meta charset="UTF-8"/>
    <title>{metadata.title}</title>
    <link rel="stylesheet" type="text/css" href="style.css"/>
</head>
<body>
    <section class="title-page">
        <h1 class="book-title">{metadata.title}</h1>
        <p class="author">by {metadata.author}</p>
        <p class="genre">{metadata.genre.replace('_', ' ').title()}</p>
        <p class="publisher">{metadata.publisher}</p>
        <p class="year">{datetime.now().year}</p>
    </section>
</body>
</html>'''

    def create_toc_xhtml(self, metadata: BookMetadata, chapters: List[tuple]) -> str:
        """Create table of contents XHTML."""
        toc_items = '\n'.join([
            f'        <li><a href="chapter{i:02d}.xhtml">{title}</a></li>'
            for i, title in chapters
        ])

        return f'''<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops" lang="en">
<head>
    <meta charset="UTF-8"/>
    <title>Table of Contents</title>
    <link rel="stylesheet" type="text/css" href="style.css"/>
</head>
<body>
    <nav epub:type="toc" id="toc">
        <h1>Contents</h1>
        <ol>
{toc_items}
        </ol>
    </nav>
</body>
</html>'''

    def create_stylesheet(self) -> str:
        """Create CSS stylesheet."""
        return '''
body {
    font-family: Georgia, "Times New Roman", serif;
    font-size: 1em;
    line-height: 1.6;
    margin: 1em;
    text-align: justify;
}

h1 {
    font-size: 1.8em;
    text-align: center;
    margin-top: 2em;
    margin-bottom: 1em;
    page-break-before: always;
}

h2 {
    font-size: 1.4em;
    margin-top: 1.5em;
    margin-bottom: 0.5em;
}

h3 {
    font-size: 1.2em;
    margin-top: 1em;
    margin-bottom: 0.5em;
}

p {
    text-indent: 1.5em;
    margin-top: 0.3em;
    margin-bottom: 0.3em;
}

.title-page {
    text-align: center;
    padding-top: 30%;
}

.book-title {
    font-size: 2.5em;
    margin-bottom: 0.5em;
}

.author {
    font-size: 1.5em;
    font-style: italic;
    margin-bottom: 2em;
}

.genre, .publisher, .year {
    font-size: 1em;
    margin: 0.5em 0;
}

.chapter-title {
    page-break-before: always;
}

nav#toc ol {
    list-style-type: none;
    padding-left: 0;
}

nav#toc li {
    margin: 0.5em 0;
}

nav#toc a {
    text-decoration: none;
    color: #333;
}
'''

    def create_container_xml(self) -> str:
        """Create container.xml for EPUB."""
        return '''<?xml version="1.0" encoding="UTF-8"?>
<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
    <rootfiles>
        <rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/>
    </rootfiles>
</container>'''

    def create_content_opf(self, metadata: BookMetadata, chapters: List[tuple], has_cover: bool) -> str:
        """Create content.opf manifest."""
        book_id = str(uuid.uuid4())
        modified = datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")

        # Manifest items
        manifest_items = [
            '<item id="style" href="style.css" media-type="text/css"/>',
            '<item id="title" href="title.xhtml" media-type="application/xhtml+xml"/>',
            '<item id="toc" href="toc.xhtml" media-type="application/xhtml+xml" properties="nav"/>',
        ]

        if has_cover:
            manifest_items.append('<item id="cover-image" href="cover.png" media-type="image/png" properties="cover-image"/>')

        for i, _ in chapters:
            manifest_items.append(f'<item id="chapter{i:02d}" href="chapter{i:02d}.xhtml" media-type="application/xhtml+xml"/>')

        # Spine items
        spine_items = ['<itemref idref="title"/>']
        spine_items.append('<itemref idref="toc"/>')
        for i, _ in chapters:
            spine_items.append(f'<itemref idref="chapter{i:02d}"/>')

        return f'''<?xml version="1.0" encoding="UTF-8"?>
<package version="3.0" xmlns="http://www.idpf.org/2007/opf" unique-identifier="bookid">
    <metadata xmlns:dc="http://purl.org/dc/elements/1.1/">
        <dc:identifier id="bookid">urn:uuid:{book_id}</dc:identifier>
        <dc:title>{metadata.title}</dc:title>
        <dc:creator>{metadata.author}</dc:creator>
        <dc:language>{metadata.language}</dc:language>
        <dc:publisher>{metadata.publisher}</dc:publisher>
        <dc:description>{metadata.description}</dc:description>
        <dc:subject>{metadata.genre.replace('_', ' ').title()}</dc:subject>
        <meta property="dcterms:modified">{modified}</meta>
    </metadata>
    <manifest>
        {chr(10).join('        ' + item for item in manifest_items)}
    </manifest>
    <spine>
        {chr(10).join('        ' + item for item in spine_items)}
    </spine>
</package>'''

    def generate_epub(self, book_dir: Path, metadata: BookMetadata, output_path: Path) -> bool:
        """Generate EPUB file from book directory."""
        try:
            # Collect chapters
            chapters = []
            for chapter_file in sorted(book_dir.glob("chapter_*.md")):
                match = re.search(r'chapter_(\d+)', chapter_file.name)
                if match:
                    num = int(match.group(1))
                    content = chapter_file.read_text(encoding='utf-8')
                    lines = content.split('\n')
                    title = lines[0].replace('#', '').strip() if lines else f"Chapter {num}"
                    body = '\n'.join(lines[2:]) if len(lines) > 2 else content
                    chapters.append((num, title, body))

            if not chapters:
                logger.error(f"No chapters found in {book_dir}")
                return False

            chapters.sort(key=lambda x: x[0])

            # Check for cover
            cover_path = book_dir / "cover.png"
            has_cover = cover_path.exists()

            # Create EPUB as ZIP
            with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as epub:
                # Mimetype (must be first and uncompressed)
                epub.writestr('mimetype', self.mime_type, compress_type=zipfile.ZIP_STORED)

                # META-INF
                epub.writestr('META-INF/container.xml', self.create_container_xml())

                # OEBPS content
                epub.writestr('OEBPS/style.css', self.create_stylesheet())
                epub.writestr('OEBPS/title.xhtml', self.create_title_page(metadata))
                epub.writestr('OEBPS/toc.xhtml', self.create_toc_xhtml(metadata, [(c[0], c[1]) for c in chapters]))

                # Cover image
                if has_cover:
                    epub.write(cover_path, 'OEBPS/cover.png')

                # Chapters
                for num, title, body in chapters:
                    xhtml = self.create_chapter_xhtml(title, body, num)
                    epub.writestr(f'OEBPS/chapter{num:02d}.xhtml', xhtml)

                # Content.opf
                epub.writestr('OEBPS/content.opf',
                            self.create_content_opf(metadata, [(c[0], c[1]) for c in chapters], has_cover))

            logger.info(f"EPUB created: {output_path}")
            return True

        except Exception as e:
            logger.error(f"EPUB generation failed: {e}")
            return False


class PDFGenerator:
    """Generates PDF files from EPUB or markdown."""

    def __init__(self):
        self.pandoc_available = self._check_pandoc()

    def _check_pandoc(self) -> bool:
        """Check if pandoc is available."""
        try:
            result = subprocess.run(['pandoc', '--version'], capture_output=True, timeout=5)
            return result.returncode == 0
        except (OSError, subprocess.SubprocessError, subprocess.TimeoutExpired):
            # Try with full path
            try:
                result = subprocess.run([os.path.expanduser('~/.local/bin/pandoc'), '--version'],
                                       capture_output=True, timeout=5)
                return result.returncode == 0
            except (OSError, subprocess.SubprocessError, subprocess.TimeoutExpired):
                return False

    def generate_pdf(self, book_dir: Path, metadata: BookMetadata, output_path: Path) -> bool:
        """Generate PDF from markdown chapters."""
        if not self.pandoc_available:
            logger.warning("Pandoc not available, skipping PDF generation")
            return False

        try:
            # Collect all chapters into one markdown
            chapters = []
            for chapter_file in sorted(book_dir.glob("chapter_*.md")):
                content = chapter_file.read_text(encoding='utf-8')
                chapters.append(content)

            if not chapters:
                return False

            # Create combined markdown
            full_content = f"# {metadata.title}\n\n**{metadata.author}**\n\n---\n\n"
            full_content += "\n\n".join(chapters)

            # Write temp file
            temp_md = book_dir / "_temp_full.md"
            temp_md.write_text(full_content, encoding='utf-8')

            # Run pandoc
            pandoc_path = 'pandoc'
            if not self._check_pandoc():
                pandoc_path = os.path.expanduser('~/.local/bin/pandoc')

            cmd = [
                pandoc_path,
                str(temp_md),
                '-o', str(output_path),
                '--pdf-engine=xelatex',
                '-V', 'geometry:margin=1in',
                '-V', f'title={metadata.title}',
                '-V', f'author={metadata.author}',
                '--toc',
                '--toc-depth=2'
            ]

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)

            # Cleanup
            temp_md.unlink(missing_ok=True)

            if result.returncode == 0:
                logger.info(f"PDF created: {output_path}")
                return True
            else:
                logger.warning(f"PDF generation failed: {result.stderr[:200]}")
                return False

        except Exception as e:
            logger.error(f"PDF generation failed: {e}")
            return False


def generate_book_formats(book_dir: Path, is_fiction: bool = True) -> Dict[str, bool]:
    """Generate EPUB and PDF for a book."""
    results = {"epub": False, "pdf": False}

    outline_file = book_dir / "outline.json"
    if not outline_file.exists():
        return results

    book_info = json.loads(outline_file.read_text())
    title = book_info.get('title', book_dir.name)
    genre = book_info.get('genre', 'fiction' if is_fiction else 'nonfiction')
    premise = book_info.get('premise', '')

    metadata = BookMetadata(
        title=title,
        author="AI Publishing",
        genre=genre,
        description=premise[:500],
        cover_path=book_dir / "cover.png" if (book_dir / "cover.png").exists() else None
    )

    # Generate EPUB
    epub_path = book_dir / f"{book_dir.name}.epub"
    epub_gen = EPUBGenerator()
    results["epub"] = epub_gen.generate_epub(book_dir, metadata, epub_path)

    # Generate PDF
    pdf_path = book_dir / f"{book_dir.name}.pdf"
    pdf_gen = PDFGenerator()
    results["pdf"] = pdf_gen.generate_pdf(book_dir, metadata, pdf_path)

    return results


def generate_all_ebooks(fiction_dir: Path, books_dir: Path) -> Dict[str, int]:
    """Generate ebooks for all complete books."""
    stats = {"epub": 0, "pdf": 0, "skipped": 0}

    # Fiction
    if fiction_dir.exists():
        for book_dir in sorted(fiction_dir.iterdir()):
            if not book_dir.is_dir() or book_dir.name.startswith('.'):
                continue

            # Check if already has EPUB
            if (book_dir / f"{book_dir.name}.epub").exists():
                stats["skipped"] += 1
                continue

            # Check if complete enough
            chapters = len(list(book_dir.glob("chapter_*.md")))
            if chapters < 6:
                continue

            logger.info(f"Generating ebooks for: {book_dir.name}")
            results = generate_book_formats(book_dir, is_fiction=True)
            if results["epub"]:
                stats["epub"] += 1
            if results["pdf"]:
                stats["pdf"] += 1

    # Non-fiction
    if books_dir.exists():
        for book_dir in sorted(books_dir.iterdir()):
            if not book_dir.is_dir() or book_dir.name.startswith('.'):
                continue

            if (book_dir / f"{book_dir.name}.epub").exists():
                stats["skipped"] += 1
                continue

            chapters = len(list(book_dir.glob("chapter_*.md")))
            if chapters < 8:
                continue

            logger.info(f"Generating ebooks for: {book_dir.name}")
            results = generate_book_formats(book_dir, is_fiction=False)
            if results["epub"]:
                stats["epub"] += 1
            if results["pdf"]:
                stats["pdf"] += 1

    return stats


if __name__ == "__main__":
    fiction_dir = Path("/mnt/e/projects/bookcli/output/fiction")
    books_dir = Path("/mnt/e/projects/bookcli/output/books")

    logger.info("=" * 60)
    logger.info("EBOOK GENERATOR")
    logger.info("=" * 60)

    stats = generate_all_ebooks(fiction_dir, books_dir)
    logger.info(f"\nGenerated: {stats['epub']} EPUBs, {stats['pdf']} PDFs")
    logger.info(f"Skipped: {stats['skipped']} (already exist)")
