# Cloud Setup Checklist - Do This Now

**Estimated time**: 10 minutes total

## ☐ Step 1: Install OCI SDK (2-3 minutes)

The installation timed out in the main session. Run this in a **new terminal**:

```bash
# Open new terminal, navigate to project
cd /mnt/e/projects/bookcli

# Run installation script
bash /tmp/oci_install.sh
```

**Or** install manually:
```bash
pip install oci --break-system-packages
```

**While that runs**, continue with Steps 2-3 below.

---

## ☐ Step 2: Create Oracle Cloud Account (5 minutes)

### 2a. Sign Up

**Go to**: https://cloud.oracle.com/free

**What you get**:
- ✅ $300 free trial credits (30 days)
- ✅ 4 Ampere A1 cores (FREE FOREVER - no expiration)
- ✅ 2 AMD instances (FREE FOREVER)

**Sign up** (no credit card in most regions):
1. Enter email
2. Choose home region (e.g., us-ashburn-1)
3. Verify email
4. Complete registration

### 2b. Get Your OCIDs

After signing in, collect these values:

**User OCID**:
1. Click profile icon (top right) → **User Settings**
2. Copy the OCID (starts with `ocid1.user.oc1..`)
3. Save it: `_______________________________________________`

**Tenancy OCID**:
1. Click profile icon → **Tenancy: [name]**
2. Copy the OCID (starts with `ocid1.tenancy.oc1..`)
3. Save it: `_______________________________________________`

**Region**:
1. Look at your browser URL or click region selector
2. Example: `us-ashburn-1`
3. Save it: `_______________________________________________`

---

## ☐ Step 3: Generate API Key (2 minutes)

**In Oracle Cloud Console**:

1. Click **Profile icon** → **User Settings**
2. Scroll down, click **API Keys** in left menu
3. Click **Add API Key** button
4. Select **Generate API Key Pair**
5. Click **Download Private Key** (saves as `oci_api_key.pem`)
6. Click **Add** button

**Copy the configuration** shown in the dialog:
```
[DEFAULT]
user=ocid1.user.oc1..aaa...
fingerprint=xx:xx:xx:xx:...
tenancy=ocid1.tenancy.oc1..aaa...
region=us-ashburn-1
key_file=~/.oci/oci_api_key.pem
```

Save this configuration somewhere for Step 4.

---

## ☐ Step 4: Configure OCI on Your Computer (2 minutes)

**Run these commands**:

```bash
# Create OCI directory
mkdir -p ~/.oci

# Move downloaded key (adjust path if needed)
mv ~/Downloads/oci_api_key.pem ~/.oci/

# Set permissions (IMPORTANT!)
chmod 600 ~/.oci/oci_api_key.pem

# Create config file
nano ~/.oci/config
```

**Paste** the configuration from Step 3 (the one that starts with `[DEFAULT]`).

Make sure `key_file=~/.oci/oci_api_key.pem` points to the right location.

**Save** (Ctrl+O, Enter, Ctrl+X)

---

## ☐ Step 5: Get LLM API Keys (2 minutes)

You need at least ONE of these:

### Option A: Groq (Recommended - FREE)

1. Go to: https://console.groq.com
2. Sign in with Google/GitHub
3. Click **API Keys** → **Create API Key**
4. Copy the key (starts with `gsk_`)
5. Save: `_______________________________________________`

### Option B: DeepSeek (Cheapest - $0.03/book)

1. Go to: https://platform.deepseek.com
2. Sign up
3. Go to API Keys
4. Create new key
5. Copy key (starts with `sk-`)
6. Save: `_______________________________________________`

### Set the API keys:

```bash
# Add to .bashrc (permanent)
echo 'export GROQ_API_KEY="your-actual-key-here"' >> ~/.bashrc
echo 'export DEEPSEEK_API_KEY="your-actual-key-here"' >> ~/.bashrc

# Load now
source ~/.bashrc
```

**Or** just for this session:
```bash
export GROQ_API_KEY='your-actual-key-here'
export DEEPSEEK_API_KEY='your-actual-key-here'
```

---

## ☐ Step 6: Verify Everything Works (1 minute)

```bash
cd /mnt/e/projects/bookcli

# Check OCI SDK
python3 -c "import oci; print('✓ OCI SDK installed')"

# Check OCI config
python3 -c "
import oci
config = oci.config.from_file()
print('✓ OCI config loaded')
print(f'  Region: {config[\"region\"]}')
"

# Check OCI connection
python3 -c "
import oci
config = oci.config.from_file()
identity = oci.identity.IdentityClient(config)
user = identity.get_user(config['user']).data
print(f'✓ Connected to OCI as: {user.name}')
"

# Check API keys
python3 -c "
import os
if os.environ.get('GROQ_API_KEY'):
    print('✓ GROQ_API_KEY set')
if os.environ.get('DEEPSEEK_API_KEY'):
    print('✓ DEEPSEEK_API_KEY set')
"

# Full verification
python3 scripts/verify_oci_integration.py
```

---

## ☐ Step 7: Generate Your First Cloud Books! (15 minutes)

### 7a. Dry Run (see costs, no actual generation)

```bash
python3 scripts/oci_book_generation.py --num-books 5 --dry-run
```

This shows what would happen without actually creating instances or generating books.

### 7b. Real Generation (5 books)

```bash
python3 scripts/oci_book_generation.py --num-books 5 --free-tier-only
```

**What happens**:
1. Creates 5 sample book outlines
2. Spins up OCI instances (free tier)
3. Generates 5 books in parallel
4. Shows real-time progress
5. Displays cost report
6. Shuts down instances

**Expected**:
- Time: ~15 minutes
- Cost: ~$0.15-0.25 (LLM only)
- Cloud cost: $0 (free tier)

### 7c. Scale Up (100 books)

Once you've verified it works:

```bash
python3 scripts/oci_book_generation.py --num-books 100 --max-instances 4
```

---

## Troubleshooting

### ❌ OCI SDK not installing

Try:
```bash
# Method 1: Virtual environment (recommended)
python3 -m venv ~/oci_env
source ~/oci_env/bin/activate
pip install oci

# Then use this env for all OCI commands
```

### ❌ Can't find downloaded key

The key is probably in `~/Downloads/`. Find it:
```bash
ls -la ~/Downloads/oci*.pem
mv ~/Downloads/oci_api_key.pem ~/.oci/
```

### ❌ OCI connection fails

Check config:
```bash
cat ~/.oci/config
ls -l ~/.oci/oci_api_key.pem  # Should show -rw------- (600)
```

Fix permissions:
```bash
chmod 600 ~/.oci/oci_api_key.pem
```

### ❌ No API keys set

```bash
# Check
echo $GROQ_API_KEY
echo $DEEPSEEK_API_KEY

# Set
export GROQ_API_KEY='your-key'
export DEEPSEEK_API_KEY='your-key'
```

---

## Quick Reference Card

**After setup, generate books with**:
```bash
# Small test (5 books)
python3 scripts/oci_book_generation.py --num-books 5 --free-tier-only

# Medium batch (50 books)
python3 scripts/oci_book_generation.py --num-books 50

# Large batch (100+ books)
python3 scripts/oci_book_generation.py --num-books 100 --dry-run  # check first
python3 scripts/oci_book_generation.py --num-books 100

# Check status
python3 scripts/verify_oci_integration.py

# Monitor costs
python3 -c "
from oci_cost_tracker import OCICostTracker
tracker = OCICostTracker()
tracker.print_cost_report(detailed=True)
"
```

---

## Completion Checklist

Mark when done:

- [ ] OCI SDK installed (`python3 -c "import oci"` works)
- [ ] Oracle Cloud account created
- [ ] User OCID saved
- [ ] Tenancy OCID saved
- [ ] Region identified
- [ ] API key generated and downloaded
- [ ] Config file created at `~/.oci/config`
- [ ] Private key at `~/.oci/oci_api_key.pem` with 600 permissions
- [ ] At least one LLM API key set
- [ ] OCI connection test passed
- [ ] First cloud generation completed successfully

---

## What You'll Have When Done

✅ **Oracle Cloud account** with $300 credits
✅ **4 free CPU cores** (forever - no expiration)
✅ **Cloud book generation** working
✅ **4× faster** generation vs local
✅ **Ability to generate thousands** of books

**Start at Step 1 above!**

Need help? See: `SETUP_CLOUD_NOW.md` for detailed instructions.
