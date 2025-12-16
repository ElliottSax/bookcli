#!/bin/bash
# Quick script to generate test book once API key is set

echo "╔══════════════════════════════════════════════════════════════════╗"
echo "║           Test Book Generation Script                           ║"
echo "╚══════════════════════════════════════════════════════════════════╝"
echo ""

# Check for API keys
if [ -z "$GROQ_API_KEY" ] && [ -z "$DEEPSEEK_API_KEY" ] && [ -z "$OPENAI_API_KEY" ]; then
    echo "❌ No API key found!"
    echo ""
    echo "Please set one of these:"
    echo "  export GROQ_API_KEY='your-key'"
    echo "  export DEEPSEEK_API_KEY='your-key'"
    echo "  export OPENAI_API_KEY='your-key'"
    echo ""
    echo "See QUICK_API_SETUP.md for instructions."
    exit 1
fi

echo "✓ API key found"
echo ""

# Create workspace if needed
mkdir -p workspace/test-book
cd /mnt/e/projects/bookcli

echo "📖 Generating test book: 'The Last Algorithm'"
echo "   Genre: Sci-Fi Thriller"
echo "   Length: 3 chapters (~6,000 words)"
echo ""

# Generate the book
python3 << 'PYTHON_SCRIPT'
import sys
from pathlib import Path
sys.path.insert(0, str(Path.cwd() / 'scripts'))

from resilient_orchestrator import ResilientOrchestrator
from llm_providers import Provider

# Initialize orchestrator with quality enforcement
orchestrator = ResilientOrchestrator(
    workspace=Path("workspace/test-book"),
    source_file=Path("workspace/test-book-outline.txt"),
    book_name="the-last-algorithm",
    target_chapters=3,
    target_words=2000,  # Per chapter
    genre="sci-fi-thriller",
    providers=[
        Provider.GROQ,
        Provider.DEEPSEEK,
        Provider.OPENAI,
    ],
    quality_enforcement_enabled=True,  # Enable Phase 8 quality gates
    quality_strict_mode=False,  # Allow some flexibility for first run
    checkpoint_enabled=True
)

print("\n" + "="*70)
print("Starting book generation with quality enforcement...")
print("="*70 + "\n")

# Generate all chapters
for chapter_num in range(1, 4):
    print(f"\n{'='*70}")
    print(f"Generating Chapter {chapter_num}/3")
    print(f"{'='*70}\n")

    success, quality_report = orchestrator.generate_chapter_with_quality_enforcement(
        chapter_num=chapter_num,
        max_quality_retries=2
    )

    if success:
        print(f"\n✓ Chapter {chapter_num} complete!")
        if quality_report:
            print(f"   Quality score: {quality_report.total_score:.1f}/100")
    else:
        print(f"\n✗ Chapter {chapter_num} failed to generate")
        sys.exit(1)

print("\n" + "="*70)
print("✓ Book generation complete!")
print("="*70)

# Show file locations
workspace = Path("workspace/test-book")
print("\n📁 Generated files:")
for i in range(1, 4):
    chapter_file = workspace / f"chapter_{i:03d}.md"
    if chapter_file.exists():
        word_count = len(chapter_file.read_text().split())
        print(f"   ✓ {chapter_file} ({word_count:,} words)")

        # Check for quality report
        report_file = workspace / f"chapter_{i:03d}_quality_report.json"
        if report_file.exists():
            print(f"   ✓ {report_file}")

PYTHON_SCRIPT

echo ""
echo "╔══════════════════════════════════════════════════════════════════╗"
echo "║                 BOOK GENERATION COMPLETE!                        ║"
echo "╚══════════════════════════════════════════════════════════════════╝"
echo ""
echo "📚 Your test book is ready:"
echo "   Location: workspace/test-book/"
echo "   Chapters: chapter_001.md, chapter_002.md, chapter_003.md"
echo "   Quality Reports: chapter_*_quality_report.json"
echo ""
echo "Next: Generate cover with:"
echo "   python3 scripts/generate_cover.py --book workspace/test-book"
echo ""
