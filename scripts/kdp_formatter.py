#!/usr/bin/env python3
"""
KDP Formatter - Convert manuscript to KDP-ready formats
Outputs: DOCX, EPUB, and formatted HTML
"""

import re
import sys
from pathlib import Path
from datetime import datetime
import subprocess


class KDPFormatter:
    def __init__(self, manuscript_file: Path, output_dir: Path):
        self.manuscript_file = Path(manuscript_file)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.book_title = ""
        self.author = "AI Generated"  # Customize as needed
        self.chapters = []

    def parse_manuscript(self):
        """Parse manuscript into structured chapters"""
        content = self.manuscript_file.read_text(encoding='utf-8')

        # Extract title (first h1)
        title_match = re.search(r'^#\s+(.+)$', content, re.MULTILINE)
        if title_match:
            self.book_title = title_match.group(1).strip()
        else:
            self.book_title = "Untitled"

        # Split into chapters
        # Assumes chapters are marked with ## Chapter or # Chapter
        chapter_pattern = r'(?:^|\n)(#{1,2}\s+Chapter\s+\d+.*?)(?=\n#{1,2}\s+Chapter\s+\d+|\Z)'
        chapter_matches = re.finditer(chapter_pattern, content, re.MULTILINE | re.DOTALL)

        for match in chapter_matches:
            chapter_text = match.group(1).strip()

            # Extract chapter number and title
            header_match = re.match(r'#{1,2}\s+(Chapter\s+\d+)(?:\s*[:-]\s*(.+?))?$',
                                    chapter_text.split('\n')[0])

            if header_match:
                chapter_num = header_match.group(1)
                chapter_title = header_match.group(2) if header_match.group(2) else ""

                # Get chapter body (everything after first line)
                chapter_body = '\n'.join(chapter_text.split('\n')[1:]).strip()

                self.chapters.append({
                    'number': chapter_num,
                    'title': chapter_title,
                    'body': chapter_body
                })

        print(f"Parsed {len(self.chapters)} chapters")
        return len(self.chapters) > 0

    def format_for_docx(self):
        """Create DOCX using pandoc"""
        docx_file = self.output_dir / f"{self.manuscript_file.stem}.docx"

        # Create a cleaned version for DOCX
        formatted_content = self._create_formatted_content()
        temp_file = self.output_dir / "temp_formatted.md"
        temp_file.write_text(formatted_content)

        # Use pandoc if available
        try:
            result = subprocess.run(
                ["pandoc", str(temp_file), "-o", str(docx_file),
                 "--metadata", f"title={self.book_title}",
                 "--metadata", f"author={self.author}"],
                capture_output=True, text=True, timeout=60
            )

            if result.returncode == 0:
                print(f"✓ DOCX created: {docx_file}")
                temp_file.unlink()
                return True
            else:
                print(f"Pandoc error: {result.stderr}")
        except FileNotFoundError:
            print("Pandoc not found, skipping DOCX generation")
            print("Install: apt-get install pandoc or brew install pandoc")
        except Exception as e:
            print(f"Error creating DOCX: {e}")

        return False

    def format_for_epub(self):
        """Create EPUB using pandoc"""
        epub_file = self.output_dir / f"{self.manuscript_file.stem}.epub"

        formatted_content = self._create_formatted_content()
        temp_file = self.output_dir / "temp_formatted.md"
        temp_file.write_text(formatted_content)

        # Use pandoc if available
        try:
            result = subprocess.run(
                ["pandoc", str(temp_file), "-o", str(epub_file),
                 "--metadata", f"title={self.book_title}",
                 "--metadata", f"author={self.author}",
                 "--epub-chapter-level=2",
                 "--toc"],
                capture_output=True, text=True, timeout=60
            )

            if result.returncode == 0:
                print(f"✓ EPUB created: {epub_file}")
                temp_file.unlink()
                return True
            else:
                print(f"Pandoc error: {result.stderr}")
        except FileNotFoundError:
            print("Pandoc not found, skipping EPUB generation")
        except Exception as e:
            print(f"Error creating EPUB: {e}")

        return False

    def create_kdp_html(self):
        """Create KDP-formatted HTML"""
        html_file = self.output_dir / f"{self.manuscript_file.stem}_kdp.html"

        html = self._generate_kdp_html()
        html_file.write_text(html)

        print(f"✓ KDP HTML created: {html_file}")
        return True

    def _create_formatted_content(self):
        """Create cleaned, formatted content"""
        lines = [f"# {self.book_title}\n\n"]

        for chapter in self.chapters:
            # Chapter heading
            lines.append(f"## {chapter['number']}")
            if chapter['title']:
                lines.append(f": {chapter['title']}")
            lines.append("\n\n")

            # Chapter body
            body = chapter['body']

            # Clean up formatting
            # Remove extra blank lines
            body = re.sub(r'\n{3,}', '\n\n', body)

            # Convert scene breaks
            body = re.sub(r'\n\s*\*\s*\*\s*\*\s*\n', '\n\n* * *\n\n', body)

            lines.append(body)
            lines.append("\n\n")

        return "".join(lines)

    def _generate_kdp_html(self):
        """Generate KDP-compliant HTML"""
        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>{self.book_title}</title>
    <style>
        body {{
            font-family: Georgia, serif;
            line-height: 1.6;
            max-width: 40em;
            margin: 0 auto;
            padding: 2em;
        }}
        h1 {{
            text-align: center;
            font-size: 2em;
            margin: 2em 0;
        }}
        h2 {{
            text-align: center;
            font-size: 1.5em;
            margin: 2em 0 1em 0;
            page-break-before: always;
        }}
        p {{
            text-indent: 1.5em;
            margin: 0;
        }}
        p:first-of-type,
        h2 + p {{
            text-indent: 0;
        }}
        .scene-break {{
            text-align: center;
            margin: 2em 0;
        }}
    </style>
</head>
<body>
    <h1>{self.book_title}</h1>
"""

        for chapter in self.chapters:
            html += f"\n    <h2>{chapter['number']}"
            if chapter['title']:
                html += f": {chapter['title']}"
            html += "</h2>\n\n"

            # Convert body to HTML paragraphs
            body = chapter['body']

            # Convert scene breaks
            body = re.sub(r'\n\s*\*\s*\*\s*\*\s*\n',
                          '\n<div class="scene-break">* * *</div>\n', body)

            # Split into paragraphs
            paragraphs = [p.strip() for p in body.split('\n\n') if p.strip()]

            for para in paragraphs:
                if '<div class="scene-break">' in para:
                    html += f"    {para}\n"
                else:
                    # Handle dialogue formatting
                    para_html = self._format_paragraph(para)
                    html += f"    <p>{para_html}</p>\n"

            html += "\n"

        html += """</body>
</html>"""

        return html

    def _format_paragraph(self, text):
        """Format paragraph text for HTML"""
        # Escape HTML entities
        text = text.replace('&', '&amp;')
        text = text.replace('<', '&lt;')
        text = text.replace('>', '&gt;')

        # Convert emphasis (if any)
        text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)
        text = re.sub(r'\*(.+?)\*', r'<em>\1</em>', text)

        # Convert em-dashes
        text = text.replace('—', '&mdash;')
        text = text.replace('--', '&mdash;')

        return text

    def create_print_format(self):
        """Create print-ready PDF via pandoc"""
        pdf_file = self.output_dir / f"{self.manuscript_file.stem}_print.pdf"

        formatted_content = self._create_formatted_content()
        temp_file = self.output_dir / "temp_formatted.md"
        temp_file.write_text(formatted_content)

        # Create PDF with print settings
        try:
            result = subprocess.run(
                ["pandoc", str(temp_file), "-o", str(pdf_file),
                 "--metadata", f"title={self.book_title}",
                 "--metadata", f"author={self.author}",
                 "--pdf-engine=xelatex",
                 "-V", "geometry:paperwidth=6in",
                 "-V", "geometry:paperheight=9in",
                 "-V", "geometry:margin=0.75in",
                 "--toc"],
                capture_output=True, text=True, timeout=120
            )

            if result.returncode == 0:
                print(f"✓ Print PDF created: {pdf_file}")
                temp_file.unlink()
                return True
            else:
                print(f"PDF generation error: {result.stderr}")
        except FileNotFoundError:
            print("Pandoc/XeLaTeX not found, skipping PDF")
        except Exception as e:
            print(f"Error creating PDF: {e}")

        return False

    def generate_all_formats(self):
        """Generate all KDP formats"""
        print(f"\nFormatting manuscript: {self.book_title}")
        print(f"Output directory: {self.output_dir}\n")

        if not self.parse_manuscript():
            print("Error: Could not parse manuscript")
            return False

        success = True

        # Always generate HTML (doesn't require external tools)
        if not self.create_kdp_html():
            success = False

        # Optional: DOCX (requires pandoc)
        self.format_for_docx()

        # Optional: EPUB (requires pandoc)
        self.format_for_epub()

        # Optional: Print PDF (requires pandoc + xelatex)
        self.create_print_format()

        return success


def main():
    if len(sys.argv) < 3:
        print("Usage: kdp_formatter.py <manuscript.md> <output_dir>")
        sys.exit(1)

    manuscript_file = Path(sys.argv[1])
    output_dir = Path(sys.argv[2])

    if not manuscript_file.exists():
        print(f"Error: Manuscript not found: {manuscript_file}")
        sys.exit(1)

    formatter = KDPFormatter(manuscript_file, output_dir)
    success = formatter.generate_all_formats()

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
