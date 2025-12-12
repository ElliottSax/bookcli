# Set Up Oracle Cloud - Step by Step Guide

**Goal**: Get cloud book generation working in the next 10 minutes

## Current Situation

The OCI SDK installation timed out. This is common in WSL environments. Here are your options:

## Option A: Quick Setup (Recommended - 10 minutes)

### Step 1: Install OCI SDK (try in background)

Open a **new terminal** and run:
```bash
cd /mnt/e/projects/bookcli

# Try installing in background
pip install oci --break-system-packages &

# Or use a virtual environment (safer)
python3 -m venv oci_env
source oci_env/bin/activate
pip install oci
```

**While that installs**, continue with Steps 2-4 below.

### Step 2: Create Oracle Cloud Account (5 minutes)

1. **Go to**: https://cloud.oracle.com/free

2. **Sign up** (Free - no credit card required in most regions):
   - Enter email
   - Choose region (e.g., US East)
   - Verify email
   - Set password

3. **You get**:
   - $300 in free trial credits (30 days)
   - 4 Ampere A1 CPU cores (FREE FOREVER)
   - 2 AMD instances (FREE FOREVER)

4. **Write down** these values (you'll need them):
   - Tenancy OCID (looks like: ocid1.tenancy.oc1..aaa...)
   - User OCID (looks like: ocid1.user.oc1..aaa...)
   - Region (e.g., us-ashburn-1)

### Step 3: Generate API Key (2 minutes)

**In Oracle Cloud Console**:

1. Click **Profile icon** (top right) → **User Settings**

2. Click **API Keys** (left menu)

3. Click **Add API Key**

4. Select **Generate API Key Pair**

5. **Download** both:
   - Private key (file: `oci_api_key.pem`)
   - Public key (optional)

6. **Copy** the configuration snippet shown (you'll use this)

### Step 4: Configure OCI Locally (2 minutes)

**On your computer**:

```bash
# Create OCI config directory
mkdir -p ~/.oci

# Move your downloaded private key
mv ~/Downloads/oci_api_key.pem ~/.oci/

# Set correct permissions
chmod 600 ~/.oci/oci_api_key.pem

# Create config file
cat > ~/.oci/config << 'EOF'
[DEFAULT]
user=<your_user_ocid>
fingerprint=<your_key_fingerprint>
key_file=~/.oci/oci_api_key.pem
tenancy=<your_tenancy_ocid>
region=<your_region>
EOF
```

**Replace** the values:
- `<your_user_ocid>`: User OCID from Oracle console
- `<your_key_fingerprint>`: Shown when you created API key
- `<your_tenancy_ocid>`: Tenancy OCID from Oracle console
- `<your_region>`: Your region (e.g., us-ashburn-1)

### Step 5: Get LLM API Keys (2 minutes)

You need at least one of these:

**Groq (FREE, recommended)**:
1. Go to: https://console.groq.com
2. Sign in with Google/GitHub
3. Create API key
4. Copy key

**DeepSeek (ULTRA CHEAP, $0.03/book)**:
1. Go to: https://platform.deepseek.com
2. Sign up
3. Create API key
4. Copy key

**Set the keys**:
```bash
# Add to your environment
echo 'export GROQ_API_KEY="your-groq-key-here"' >> ~/.bashrc
echo 'export DEEPSEEK_API_KEY="your-deepseek-key-here"' >> ~/.bashrc

# Load now
source ~/.bashrc

# Or just set for this session
export GROQ_API_KEY='your-groq-key-here'
export DEEPSEEK_API_KEY='your-deepseek-key-here'
```

### Step 6: Test Setup

```bash
# Check if OCI SDK installed (from Step 1)
python3 -c "import oci; print('✓ OCI SDK ready')"

# Verify integration
python3 scripts/verify_oci_integration.py
```

### Step 7: Generate Your First Cloud Book!

```bash
# Dry run first (see costs without spending)
python3 scripts/oci_book_generation.py --num-books 5 --dry-run

# Generate for real (5 books)
python3 scripts/oci_book_generation.py --num-books 5 --free-tier-only

# Scale up (100 books)
python3 scripts/oci_book_generation.py --num-books 100 --max-instances 4
```

## Option B: Manual OCI CLI Setup

If automatic setup doesn't work:

```bash
# Install OCI CLI
curl -L https://raw.githubusercontent.com/oracle/oci-cli/master/scripts/install/install.sh -o install.sh
bash install.sh --accept-all-defaults

# Run interactive setup
oci setup config

# Follow prompts to enter:
# - User OCID
# - Tenancy OCID
# - Region
# - Generate new API key
```

## Option C: Alternative - Continue with Local System

If cloud setup is taking too long, you can continue with local:

```bash
# Set API key
export GROQ_API_KEY='your-key'

# Generate books locally
python3 scripts/resilient_orchestrator.py
```

Then set up cloud later when you need scale.

## Troubleshooting

### OCI SDK won't install

Try:
```bash
# Option 1: Virtual environment
python3 -m venv venv
source venv/bin/activate
pip install oci

# Option 2: System package
sudo apt install python3-oci

# Option 3: pipx
pipx install oci-cli
```

### Can't find OCID values

**User OCID**:
1. Oracle Cloud Console
2. Click profile icon → User Settings
3. Copy OCID

**Tenancy OCID**:
1. Oracle Cloud Console
2. Click profile icon → Tenancy
3. Copy OCID

**Region**:
- Look at URL: https://cloud.oracle.com/?region=**us-ashburn-1**
- Or: Menu → Governance → Region Management

### API key not working

```bash
# Check permissions
ls -l ~/.oci/oci_api_key.pem
# Should show: -rw------- (600)

# Fix if needed
chmod 600 ~/.oci/oci_api_key.pem

# Verify config
cat ~/.oci/config
```

### "No LLM API keys"

Get free keys:
- **Groq**: https://console.groq.com (instant, free)
- **DeepSeek**: https://platform.deepseek.com (cheap)

```bash
export GROQ_API_KEY='gsk_...'
export DEEPSEEK_API_KEY='sk-...'
```

## Quick Reference

### Check Status
```bash
python3 scripts/verify_oci_integration.py
```

### Test OCI Connection
```bash
python3 -c "
import oci
config = oci.config.from_file()
identity = oci.identity.IdentityClient(config)
user = identity.get_user(config['user']).data
print(f'Connected as: {user.name}')
"
```

### Generate Books
```bash
# Dry run (no cost)
python3 scripts/oci_book_generation.py --num-books 10 --dry-run

# Real generation
python3 scripts/oci_book_generation.py --num-books 10 --free-tier-only
```

## What Happens When You Generate

1. **Script starts** and creates sample book outlines
2. **OCI instances created** (free tier Ampere cores)
3. **Books distributed** across 4 parallel instances
4. **Generation begins** using your LLM provider
5. **Progress updates** shown in real-time
6. **Books completed** and saved to workspace
7. **Instances shut down** automatically
8. **Cost report** displayed

## Expected Costs

**For 10 books** (30k words each):
- Cloud: $0 (free tier)
- LLM (Groq): ~$0.50 total
- LLM (DeepSeek): ~$0.30 total
- **Total**: $0.30-0.50

**For 100 books**:
- Cloud: $0 (free tier)
- LLM: ~$3-5 total
- **Total**: $3-5

**With $300 credits**:
- ~6,000-10,000 books possible

## Next Steps After Setup

Once cloud is working:

1. **Test with 5 books**
   ```bash
   python3 scripts/oci_book_generation.py --num-books 5 --free-tier-only
   ```

2. **Scale to 50 books**
   ```bash
   python3 scripts/oci_book_generation.py --num-books 50 --max-instances 4
   ```

3. **Production run (100+ books)**
   ```bash
   python3 scripts/oci_book_generation.py --num-books 100 --dry-run
   python3 scripts/oci_book_generation.py --num-books 100
   ```

4. **Monitor costs**
   ```python
   from oci_cost_tracker import OCICostTracker
   tracker = OCICostTracker()
   tracker.print_cost_report(detailed=True)
   ```

## Summary

**Time to set up**: ~10 minutes
**Cost to set up**: $0 (all free)
**Cost per book**: $0.03-0.05 (same as local)
**Speed improvement**: 4× faster
**Scale**: Thousands of books possible

**You get**:
- ✅ $300 in Oracle credits
- ✅ 4 CPU cores free forever
- ✅ 4× faster generation
- ✅ Unlimited scale

---

**Ready to start? Begin with Step 1 above!**

For detailed info: See `OCI_QUICKSTART.md` or `OCI_CLOUD_GENERATION.md`
