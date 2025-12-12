#!/bin/bash
# OCI Activation Script
# Guides you through setting up Oracle Cloud for book generation

set -e

echo "================================================================"
echo "ORACLE CLOUD ACTIVATION WIZARD"
echo "================================================================"
echo ""
echo "This will set up Oracle Cloud Infrastructure for mass book"
echo "generation. You'll get:"
echo "  • $300 in free trial credits"
echo "  • 4 Ampere CPU cores (free forever)"
echo "  • Ability to generate thousands of books"
echo ""

# Step 1: Check current system
echo "Step 1: Checking current system..."
echo ""

if [ -f "workspace/production.db" ]; then
    echo "✓ Local system is working"
else
    echo "⚠ No local system detected"
fi

# Step 2: Install OCI SDK
echo ""
echo "Step 2: Installing OCI SDK..."
echo ""

read -p "Install OCI Python SDK? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    pip install --user oci
    if [ $? -eq 0 ]; then
        echo "✓ OCI SDK installed"
    else
        echo "✗ Installation failed"
        exit 1
    fi
else
    echo "Skipped SDK installation"
fi

# Step 3: Check for OCI config
echo ""
echo "Step 3: Checking OCI configuration..."
echo ""

if [ -f "$HOME/.oci/config" ]; then
    echo "✓ OCI config already exists"
else
    echo "✗ No OCI config found"
    echo ""
    echo "You need to:"
    echo "1. Sign up for Oracle Cloud (if you haven't):"
    echo "   https://cloud.oracle.com/free"
    echo ""
    echo "2. Get your credentials:"
    echo "   - User OCID"
    echo "   - Tenancy OCID"
    echo "   - Region"
    echo ""
    echo "3. Run OCI setup:"
    read -p "   Install OCI CLI and run setup? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        pip install --user oci-cli
        echo ""
        echo "Now running OCI setup wizard..."
        echo "Follow the prompts to configure your credentials"
        echo ""
        oci setup config
    else
        echo ""
        echo "Setup skipped. Run later with: oci setup config"
        exit 0
    fi
fi

# Step 4: Test connection
echo ""
echo "Step 4: Testing OCI connection..."
echo ""

python3 -c "
import oci
try:
    config = oci.config.from_file()
    identity = oci.identity.IdentityClient(config)
    user = identity.get_user(config['user']).data
    print(f'✓ Connected to OCI as: {user.name}')
    print(f'  Tenancy: {config[\"tenancy\"][:20]}...')
    print(f'  Region: {config[\"region\"]}')
except Exception as e:
    print(f'✗ Connection failed: {e}')
    exit(1)
"

if [ $? -ne 0 ]; then
    echo ""
    echo "⚠ OCI connection failed"
    echo "Please check your configuration and try again"
    exit 1
fi

# Step 5: Check API keys
echo ""
echo "Step 5: Checking LLM API keys..."
echo ""

has_keys=false

if [ -n "$GROQ_API_KEY" ]; then
    echo "✓ GROQ_API_KEY is set"
    has_keys=true
fi

if [ -n "$DEEPSEEK_API_KEY" ]; then
    echo "✓ DEEPSEEK_API_KEY is set"
    has_keys=true
fi

if [ -n "$OPENROUTER_API_KEY" ]; then
    echo "✓ OPENROUTER_API_KEY is set"
    has_keys=true
fi

if [ "$has_keys" = false ]; then
    echo "⚠ No LLM API keys set"
    echo ""
    echo "You need at least one API key to generate books."
    echo "Get free/cheap keys from:"
    echo "  • Groq (free tier): https://console.groq.com"
    echo "  • DeepSeek (ultra cheap): https://platform.deepseek.com"
    echo ""
    echo "Set them like:"
    echo "  export GROQ_API_KEY='your-key-here'"
    echo "  export DEEPSEEK_API_KEY='your-key-here'"
    echo ""
    echo "Add to ~/.bashrc to persist across sessions"
    echo ""
    read -p "Continue anyway? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 0
    fi
fi

# Step 6: Verify integration
echo ""
echo "Step 6: Verifying integration..."
echo ""

python3 scripts/verify_oci_integration.py

# Step 7: Ready to go
echo ""
echo "================================================================"
echo "ACTIVATION COMPLETE!"
echo "================================================================"
echo ""
echo "You're ready to generate books at scale with Oracle Cloud!"
echo ""
echo "Quick start:"
echo "  # Test with 5 books (dry run)"
echo "  python3 scripts/oci_book_generation.py --num-books 5 --dry-run"
echo ""
echo "  # Generate 5 books for real"
echo "  python3 scripts/oci_book_generation.py --num-books 5 --free-tier-only"
echo ""
echo "  # Scale up to 100 books"
echo "  python3 scripts/oci_book_generation.py --num-books 100 --max-instances 4"
echo ""
echo "Documentation:"
echo "  • Full guide: OCI_CLOUD_GENERATION.md"
echo "  • Quick start: OCI_QUICKSTART.md"
echo "  • Current status: CURRENT_STATUS.md"
echo ""
echo "With your $300 Oracle credits, you can generate:"
echo "  • ~10,000 books using DeepSeek ($0.03/book)"
echo "  • ~6,000 books using Groq ($0.05/book)"
echo "  • All using FREE TIER cloud instances!"
echo ""
