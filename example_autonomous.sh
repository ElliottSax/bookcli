#!/bin/bash
# Example: Autonomous Book Generation with Claude API
# This demonstrates fully autonomous generation of a complete book

set -e

echo "======================================================================="
echo "   AUTONOMOUS BOOK GENERATION EXAMPLE"
echo "======================================================================="
echo ""

# Check for API key
if [ -z "$ANTHROPIC_API_KEY" ]; then
    echo "❌ ERROR: ANTHROPIC_API_KEY not set"
    echo ""
    echo "To run this example, you need a Claude API key:"
    echo ""
    echo "1. Get API key from: https://console.anthropic.com/"
    echo "2. Set environment variable:"
    echo "   export ANTHROPIC_API_KEY=sk-ant-your-key-here"
    echo ""
    echo "Or run without --use-api for manual generation:"
    echo "   bash example_run.sh"
    echo ""
    exit 1
fi

echo "✓ API key found"
echo ""

# Check for anthropic package
if ! python3 -c "import anthropic" 2>/dev/null; then
    echo "❌ ERROR: anthropic package not installed"
    echo ""
    echo "Install with:"
    echo "   pip install anthropic"
    echo ""
    exit 1
fi

echo "✓ anthropic package installed"
echo ""

# Create minimal test source
echo "Creating test source material..."
mkdir -p source

cat > source/autonomous_test.txt << 'EOF'
The Shadow Protocol

Dr. Sarah Chen, a quantum computing researcher at MIT, discovers a mysterious
algorithm that can predict financial markets with 97% accuracy. When she tries
to investigate further, she's targeted by a shadowy organization that will stop
at nothing to protect their secret.

Katherine Walsh, a federal agent with Task Force Quantum, recruits Sarah to
help stop the conspiracy. Together they must race against time to prevent the
algorithm from being used to crash the global economy.

A high-tech thriller about technology, conspiracy, and the power of quantum computing.

Key elements:
- Fast-paced action
- Tech thriller with realistic science
- Strong female protagonist
- Government conspiracy
- Race against time
- 80,000 word target
EOF

echo "✓ Source material created ($(wc -w < source/autonomous_test.txt) words)"
echo ""

# Show what we're about to do
echo "======================================================================="
echo "CONFIGURATION"
echo "======================================================================="
echo "Source: source/autonomous_test.txt"
echo "Book Name: autonomous-thriller"
echo "Genre: thriller"
echo "Target Words: 7,000 (creates ~2 chapters for demo)"
echo "Max Budget: \$5.00 (safety limit for demo)"
echo "Mode: AUTONOMOUS (API)"
echo ""
echo "NOTE: This will generate approximately 2 chapters to demonstrate"
echo "      autonomous generation while keeping costs minimal (~\$0.16)"
echo ""
echo "      For a full book (80k words, 22 chapters), use:"
echo "      --target-words 80000 --max-budget 50.0"
echo ""
read -p "Press ENTER to continue (Ctrl+C to cancel)..."
echo ""

# Run autonomous generation
echo "======================================================================="
echo "STARTING AUTONOMOUS GENERATION"
echo "======================================================================="
echo ""

python3 scripts/orchestrator.py \
  --source source/autonomous_test.txt \
  --book-name autonomous-thriller \
  --genre thriller \
  --target-words 7000 \
  --use-api \
  --max-budget 5.0

# Check results
echo ""
echo "======================================================================="
echo "GENERATION COMPLETE"
echo "======================================================================="
echo ""

if [ -f "output/autonomous-thriller/autonomous-thriller_manuscript.md" ]; then
    WORD_COUNT=$(wc -w < "output/autonomous-thriller/autonomous-thriller_manuscript.md")
    echo "✓ Manuscript created: $WORD_COUNT words"
    echo ""

    if [ -f "workspace/autonomous-thriller/status.json" ]; then
        CHAPTERS=$(grep -o '"chapters_completed": [0-9]*' workspace/autonomous-thriller/status.json | grep -o '[0-9]*')
        COST=$(grep -o '"total_cost": [0-9.]*' workspace/autonomous-thriller/status.json | grep -o '[0-9.]*')
        echo "✓ Chapters generated: $CHAPTERS"
        echo "✓ Total cost: \$$COST"
    fi

    echo ""
    echo "Output files:"
    echo "  📄 Manuscript: output/autonomous-thriller/autonomous-thriller_manuscript.md"
    echo "  🌐 KDP HTML: output/autonomous-thriller/autonomous-thriller_kdp.html"
    echo "  📊 Status: workspace/autonomous-thriller/status.json"
    echo "  📝 Logs: workspace/autonomous-thriller/production.log"
    echo ""

    echo "View the generated chapter:"
    echo "  cat workspace/autonomous-thriller/chapters/chapter_001.md"
    echo ""

    echo "View the complete manuscript:"
    echo "  cat output/autonomous-thriller/autonomous-thriller_manuscript.md"
    echo ""

    echo "✅ AUTONOMOUS GENERATION SUCCESSFUL!"
    echo ""
    echo "This demonstrates the system can:"
    echo "  ✓ Call Claude API automatically"
    echo "  ✓ Generate chapters without human intervention"
    echo "  ✓ Apply quality checks and auto-fixes"
    echo "  ✓ Track continuity across chapters"
    echo "  ✓ Monitor costs and enforce budget limits"
    echo "  ✓ Assemble final manuscript"
    echo "  ✓ Format for KDP upload"
    echo ""
    echo "For a complete 80k-word book, run:"
    echo "  python3 scripts/orchestrator.py \\"
    echo "    --source source/your-book.txt \\"
    echo "    --book-name your-book \\"
    echo "    --genre thriller \\"
    echo "    --target-words 80000 \\"
    echo "    --use-api \\"
    echo "    --max-budget 50.0"
    echo ""
    echo "See DEPLOYMENT.md for complete production guide."

else
    echo "❌ Manuscript not created - check logs:"
    echo "   cat workspace/autonomous-thriller/production.log"
    exit 1
fi

echo ""
echo "======================================================================="
