#!/bin/bash
# Example: Complete Book Production Run

set -e  # Exit on error

echo "=================================="
echo "Book Factory - Example Production"
echo "=================================="
echo ""

# Step 1: Run tests
echo "Step 1: Running self-tests..."
python3 tests/run_tests.py
if [ $? -ne 0 ]; then
    echo "Tests failed! Fix issues before proceeding."
    exit 1
fi
echo ""

# Step 2: Check for source file
SOURCE_FILE="source/sample_source.txt"
if [ ! -f "$SOURCE_FILE" ]; then
    echo "Creating sample source file..."
    cat > "$SOURCE_FILE" << 'EOF'
The Adventure Begins

Chapter One: The Discovery

Marcus had always known there was something different about the old house on Willow Street. Every time he walked past it on his way to school, he felt a strange pull, as if the house itself was calling to him.

One rainy Tuesday afternoon, curiosity finally got the better of him. The front door hung slightly ajar, creaking in the wind. Marcus pushed it open and stepped inside.

The interior was dusty and abandoned, but not quite empty. In the center of the main room sat a wooden chest, ornately carved with symbols he didn't recognize. Against all common sense, he approached it.

As his fingers touched the lid, the world shifted. Light exploded around him, and Marcus felt himself falling through space and time. When he opened his eyes, everything had changed.

He was no longer in the abandoned house. He stood in a vast forest, with trees that reached impossibly high into a purple sky. In the distance, he could hear the sound of drums.

This was just the beginning of Marcus's adventure—an adventure that would take him to worlds he never imagined existed, and reveal truths about himself he never knew.

[Continue story for ~5,000-10,000 words...]
EOF
    echo "Sample source created: $SOURCE_FILE"
    echo ""
fi

# Step 3: Run orchestrator (creates prompts for Claude)
echo "Step 3: Analyzing source and creating plan..."
python3 scripts/orchestrator.py \
    --source "$SOURCE_FILE" \
    --book-name example-adventure \
    --genre fantasy \
    --target-words 30000

echo ""
echo "=================================="
echo "Production Setup Complete!"
echo "=================================="
echo ""
echo "Next steps:"
echo "1. Check workspace/example-adventure/ for chapter prompts"
echo "2. Use Claude Code CLI to generate chapters:"
echo "   /write-chapter example-adventure 1"
echo "   /write-chapter example-adventure 2"
echo "   (etc.)"
echo "3. Assemble final book:"
echo "   /assemble-book example-adventure"
echo ""
echo "Output will be in: output/example-adventure/"
echo ""
