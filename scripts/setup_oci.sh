#!/bin/bash
# Setup script for Oracle Cloud Infrastructure integration
# This script helps configure OCI for distributed book generation

set -e

echo "================================================================"
echo "Oracle Cloud Infrastructure Setup for Book Generation"
echo "================================================================"
echo ""

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is required but not installed"
    exit 1
fi

echo "✓ Python 3 found"

# Check if pip is available
if ! command -v pip3 &> /dev/null; then
    echo "❌ pip3 is required but not installed"
    exit 1
fi

echo "✓ pip3 found"

# Install OCI SDK
echo ""
echo "Installing Oracle Cloud Infrastructure Python SDK..."
pip3 install --user oci --quiet

if [ $? -eq 0 ]; then
    echo "✓ OCI SDK installed"
else
    echo "❌ Failed to install OCI SDK"
    exit 1
fi

# Check for OCI config
OCI_CONFIG_DIR="$HOME/.oci"
OCI_CONFIG_FILE="$OCI_CONFIG_DIR/config"

echo ""
echo "Checking OCI configuration..."

if [ -f "$OCI_CONFIG_FILE" ]; then
    echo "✓ OCI config found at $OCI_CONFIG_FILE"
else
    echo "⚠ No OCI config found"
    echo ""
    echo "To set up Oracle Cloud Infrastructure:"
    echo ""
    echo "1. Sign up for Oracle Cloud Free Tier:"
    echo "   https://cloud.oracle.com/free"
    echo ""
    echo "2. Get your $300 in free trial credits + Always Free services:"
    echo "   - 4 Arm Ampere A1 cores (up to 24GB RAM) - FREE FOREVER"
    echo "   - 2 AMD compute instances - FREE FOREVER"
    echo "   - $300 in credits valid for 30 days"
    echo ""
    echo "3. Generate an API signing key:"
    echo "   https://docs.oracle.com/iaas/Content/API/Concepts/apisigningkey.htm"
    echo ""
    echo "4. Run the OCI CLI setup:"
    echo "   pip3 install oci-cli"
    echo "   oci setup config"
    echo ""
    echo "5. Follow the prompts to create your config file"
    echo ""

    read -p "Would you like to install OCI CLI now? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "Installing OCI CLI..."
        pip3 install --user oci-cli

        echo ""
        echo "Now run: oci setup config"
        echo "This will guide you through creating your OCI configuration"
    fi
fi

# Check required API keys for LLM providers
echo ""
echo "Checking LLM API keys..."

MISSING_KEYS=0

if [ -z "$GROQ_API_KEY" ]; then
    echo "⚠ GROQ_API_KEY not set (recommended - fastest & cheap)"
    MISSING_KEYS=$((MISSING_KEYS + 1))
else
    echo "✓ GROQ_API_KEY set"
fi

if [ -z "$DEEPSEEK_API_KEY" ]; then
    echo "⚠ DEEPSEEK_API_KEY not set (recommended - cheapest)"
    MISSING_KEYS=$((MISSING_KEYS + 1))
else
    echo "✓ DEEPSEEK_API_KEY set"
fi

if [ -z "$OPENROUTER_API_KEY" ]; then
    echo "⚠ OPENROUTER_API_KEY not set (optional - many models)"
    MISSING_KEYS=$((MISSING_KEYS + 1))
else
    echo "✓ OPENROUTER_API_KEY set"
fi

if [ $MISSING_KEYS -gt 0 ]; then
    echo ""
    echo "Add API keys to your environment:"
    echo "  export GROQ_API_KEY='your-key-here'"
    echo "  export DEEPSEEK_API_KEY='your-key-here'"
    echo ""
    echo "Or add to ~/.bashrc for persistence"
fi

# Create workspace directory
WORKSPACE_DIR="workspace"
if [ ! -d "$WORKSPACE_DIR" ]; then
    mkdir -p "$WORKSPACE_DIR"
    echo ""
    echo "✓ Created workspace directory"
fi

# Test OCI connection (if config exists)
if [ -f "$OCI_CONFIG_FILE" ]; then
    echo ""
    echo "Testing OCI connection..."

    python3 -c "
import oci
try:
    config = oci.config.from_file()
    identity = oci.identity.IdentityClient(config)
    user = identity.get_user(config['user']).data
    print(f'✓ Successfully connected to OCI as: {user.name}')
except Exception as e:
    print(f'❌ Failed to connect to OCI: {e}')
    print('Please check your OCI configuration')
"
fi

echo ""
echo "================================================================"
echo "Setup Complete!"
echo "================================================================"
echo ""
echo "Next steps:"
echo "1. Ensure OCI is configured (run: oci setup config)"
echo "2. Set your LLM API keys as environment variables"
echo "3. Run the cloud book generation example:"
echo "   python3 scripts/oci_book_generation.py"
echo ""
echo "Maximize your $300 OCI credits:"
echo "• Use free tier instances (4 Ampere cores forever free)"
echo "• Use cheap LLM providers (Groq, DeepSeek)"
echo "• Generate books in parallel across multiple instances"
echo "• Monitor costs with built-in cost tracker"
echo ""
