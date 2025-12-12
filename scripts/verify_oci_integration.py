#!/usr/bin/env python3
"""
OCI Integration Verification Script
Checks if OCI integration is set up and ready to use
"""

import os
import sys
from pathlib import Path

# Add scripts to path
sys.path.insert(0, str(Path(__file__).parent))

def check_oci_sdk():
    """Check if OCI SDK is installed"""
    try:
        import oci
        print(f"✓ OCI SDK installed (version {oci.__version__})")
        return True
    except ImportError:
        print("✗ OCI SDK not installed")
        print("  Install with: pip install oci")
        return False

def check_oci_config():
    """Check if OCI config exists"""
    config_file = Path.home() / ".oci" / "config"
    if config_file.exists():
        print(f"✓ OCI config found at {config_file}")

        # Try to load config
        try:
            import oci
            config = oci.config.from_file()
            print(f"  User: {config.get('user', 'N/A')[:20]}...")
            print(f"  Region: {config.get('region', 'N/A')}")
            return True
        except Exception as e:
            print(f"  ⚠ Config exists but invalid: {e}")
            return False
    else:
        print(f"✗ OCI config not found")
        print("  Run: oci setup config")
        return False

def check_oci_connectivity():
    """Test OCI API connectivity"""
    try:
        import oci
        config = oci.config.from_file()
        identity = oci.identity.IdentityClient(config)
        user = identity.get_user(config['user']).data
        print(f"✓ OCI connection successful")
        print(f"  Connected as: {user.name}")
        return True
    except Exception as e:
        print(f"✗ Cannot connect to OCI: {e}")
        return False

def check_llm_keys():
    """Check if LLM API keys are set"""
    keys = {
        'GROQ_API_KEY': os.environ.get('GROQ_API_KEY'),
        'DEEPSEEK_API_KEY': os.environ.get('DEEPSEEK_API_KEY'),
        'OPENROUTER_API_KEY': os.environ.get('OPENROUTER_API_KEY'),
        'ANTHROPIC_API_KEY': os.environ.get('ANTHROPIC_API_KEY'),
    }

    found = []
    missing = []

    for key, value in keys.items():
        if value:
            found.append(key)
            print(f"✓ {key} is set")
        else:
            missing.append(key)
            print(f"✗ {key} not set")

    if not found:
        print("\n⚠ No LLM API keys set!")
        print("  At least one is required for book generation")
        return False

    return True

def check_oci_modules():
    """Check if our OCI modules can be imported"""
    modules = [
        'oci_instance_manager',
        'cloud_batch_orchestrator',
        'oci_cost_tracker'
    ]

    all_ok = True
    for module in modules:
        try:
            __import__(module)
            print(f"✓ {module} available")
        except ImportError as e:
            print(f"✗ {module} failed: {e}")
            all_ok = False

    return all_ok

def check_current_system():
    """Check what system is currently being used"""
    print("\nCurrent System Status:")
    print("-" * 60)

    # Check for existing workspace
    workspace = Path("workspace")
    if workspace.exists():
        books = list(workspace.glob("*/"))
        print(f"✓ Workspace exists: {len(books)} book directories")

        # Check for production DB
        prod_db = workspace / "production.db"
        if prod_db.exists():
            print(f"✓ Production database exists ({prod_db.stat().st_size} bytes)")

        # Check for OCI job database
        oci_db = workspace / "book_jobs.db"
        if oci_db.exists():
            print(f"✓ OCI job database exists ({oci_db.stat().st_size} bytes)")

            import sqlite3
            conn = sqlite3.connect(str(oci_db))
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM jobs")
            job_count = cursor.fetchone()[0]
            print(f"  {job_count} jobs in queue")
            conn.close()
        else:
            print("✗ No OCI job database (not using cloud generation yet)")
    else:
        print("✗ No workspace directory")

def show_integration_status():
    """Show how to integrate OCI with current system"""
    print("\n" + "="*60)
    print("INTEGRATION OPTIONS")
    print("="*60)

    print("\n1. LOCAL GENERATION (Current)")
    print("   Uses: resilient_orchestrator.py")
    print("   Runs: On your local machine")
    print("   Cost: LLM API only (~$0.03-0.05/book)")
    print("   Speed: 1 book at a time")
    print("   Command: python3 scripts/resilient_orchestrator.py")

    print("\n2. CLOUD GENERATION (OCI Integration)")
    print("   Uses: cloud_batch_orchestrator.py + OCI")
    print("   Runs: On Oracle Cloud instances")
    print("   Cost: LLM API (~$0.03-0.05/book) + Cloud ($0 with free tier)")
    print("   Speed: 4+ books in parallel")
    print("   Command: python3 scripts/oci_book_generation.py")

    print("\n3. HYBRID (Both)")
    print("   Uses: Both systems")
    print("   Local: For testing and small batches")
    print("   Cloud: For large-scale production runs")

def main():
    """Run all checks"""
    print("="*60)
    print("OCI INTEGRATION VERIFICATION")
    print("="*60)
    print()

    # Check OCI components
    print("OCI Components:")
    print("-" * 60)
    oci_sdk = check_oci_sdk()
    print()

    oci_modules = check_oci_modules()
    print()

    if oci_sdk:
        oci_config = check_oci_config()
        print()

        if oci_config:
            oci_connected = check_oci_connectivity()
            print()

    # Check LLM keys
    print("\nLLM API Keys:")
    print("-" * 60)
    llm_keys = check_llm_keys()
    print()

    # Check current system
    check_current_system()

    # Show integration status
    show_integration_status()

    # Summary
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)

    if not oci_sdk:
        print("\n❌ OCI SDK NOT INSTALLED")
        print("\nTo use cloud generation:")
        print("1. Install OCI SDK: pip install oci")
        print("2. Sign up for Oracle Cloud: https://cloud.oracle.com/free")
        print("3. Configure OCI: oci setup config")
        print("4. Run: python3 scripts/oci_book_generation.py")
        print("\nFor now, use local generation:")
        print("  python3 scripts/resilient_orchestrator.py")
    elif not check_oci_config():
        print("\n⚠ OCI SDK INSTALLED BUT NOT CONFIGURED")
        print("\nNext steps:")
        print("1. Sign up for Oracle Cloud: https://cloud.oracle.com/free")
        print("2. Configure OCI: oci setup config")
        print("3. Run: python3 scripts/oci_book_generation.py")
    else:
        print("\n✅ OCI INTEGRATION READY!")
        print("\nYou can now use cloud generation:")
        print("  python3 scripts/oci_book_generation.py --num-books 10 --dry-run")
        print("\nOr continue using local generation:")
        print("  python3 scripts/resilient_orchestrator.py")

    if not llm_keys:
        print("\n⚠ WARNING: No LLM API keys set")
        print("Set at least one:")
        print("  export GROQ_API_KEY='your-key'")
        print("  export DEEPSEEK_API_KEY='your-key'")

if __name__ == "__main__":
    main()
