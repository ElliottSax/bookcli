# Next Steps - You Have Oracle Account ✅

Great! Now let's get your credentials and generate books.

## Step 1: Get Your OCIDs (2 minutes)

You're in the Oracle Cloud Console. Get these 3 values:

### 1a. User OCID

1. Click your **profile icon** (top right corner)
2. Click **User Settings**
3. You'll see your User OCID (looks like: `ocid1.user.oc1..aaaa...`)
4. Click **Copy** next to it
5. **Paste it here to save**: _______________________________________________

### 1b. Tenancy OCID

1. Click your **profile icon** again
2. Click **Tenancy: [your-tenancy-name]**
3. You'll see Tenancy OCID (looks like: `ocid1.tenancy.oc1..aaaa...`)
4. Click **Copy**
5. **Paste it here to save**: _______________________________________________

### 1c. Region

1. Look at the top of the page - there's a region selector
2. It shows something like "US East (Ashburn)"
3. The region code is: **us-ashburn-1** (or similar)
4. **Write it here**: _______________________________________________

## Step 2: Generate API Key (2 minutes)

Still in Oracle Cloud Console:

1. Go back to **User Settings** (Profile icon → User Settings)
2. Scroll down on the left sidebar
3. Click **API Keys** (under Resources)
4. Click **Add API Key** button
5. Select **Generate API Key Pair**
6. Click **Download Private Key** button
   - This downloads a file called `oci_api_key.pem`
   - **Important**: Remember where it saves (usually ~/Downloads/)
7. **DO NOT close the dialog yet!**
8. You'll see a **Configuration File Preview** - it looks like:
   ```
   [DEFAULT]
   user=ocid1.user.oc1..aaaa...
   fingerprint=xx:xx:xx:xx:...
   tenancy=ocid1.tenancy.oc1..aaaa...
   region=us-ashburn-1
   key_file=~/.oci/oci_api_key.pem
   ```
9. **Copy this entire text** (you'll use it in Step 3)
10. Click **Close**

## Step 3: Configure OCI Locally (2 minutes)

Now run these commands on your computer:

```bash
# Go to your project
cd /mnt/e/projects/bookcli

# Create OCI directory
mkdir -p ~/.oci

# Move the downloaded key (adjust path if your Downloads folder is different)
mv ~/Downloads/oci_api_key.pem ~/.oci/

# If that doesn't work, find it:
# find ~ -name "oci_api_key.pem" 2>/dev/null
# Then move it: mv /path/to/oci_api_key.pem ~/.oci/

# Set correct permissions (IMPORTANT!)
chmod 600 ~/.oci/oci_api_key.pem

# Create config file
nano ~/.oci/config
```

**In the nano editor**:
1. Paste the configuration you copied from Step 2
2. Press `Ctrl+O` (to save)
3. Press `Enter` (to confirm)
4. Press `Ctrl+X` (to exit)

**Verify it worked**:
```bash
cat ~/.oci/config
# Should show your configuration

ls -l ~/.oci/oci_api_key.pem
# Should show: -rw------- (600 permissions)
```

## Step 4: Test OCI Connection (1 minute)

```bash
python3 -c "
import oci
config = oci.config.from_file()
identity = oci.identity.IdentityClient(config)
user = identity.get_user(config['user']).data
print(f'✓ Connected to OCI as: {user.name}')
print(f'  Region: {config[\"region\"]}')
"
```

If you see "✓ Connected to OCI", you're good! ✅

If you get an error, check:
- File exists: `ls ~/.oci/oci_api_key.pem`
- Permissions: `chmod 600 ~/.oci/oci_api_key.pem`
- Config is valid: `cat ~/.oci/config`

## Step 5: Get LLM API Key (2 minutes)

You need at least ONE of these:

### Option A: Groq (Recommended - FREE)

1. Go to: https://console.groq.com
2. Sign in with Google or GitHub
3. Click **API Keys** in left menu
4. Click **Create API Key**
5. Give it a name (e.g., "book-generation")
6. Click **Submit**
7. **Copy the key** (starts with `gsk_...`)
8. **Paste it here**: _______________________________________________

### Option B: DeepSeek (Cheapest - ~$0.03/book)

1. Go to: https://platform.deepseek.com
2. Sign up with email
3. Go to **API Keys** section
4. Click **Create API Key**
5. **Copy the key** (starts with `sk-...`)
6. **Paste it here**: _______________________________________________

### Set the API Key

```bash
# For Groq:
export GROQ_API_KEY='paste-your-actual-key-here'

# For DeepSeek:
export DEEPSEEK_API_KEY='paste-your-actual-key-here'

# Make it permanent (optional):
echo 'export GROQ_API_KEY="your-actual-key"' >> ~/.bashrc
source ~/.bashrc
```

## Step 6: Verify Everything (1 minute)

```bash
python3 scripts/verify_oci_integration.py
```

This should show:
- ✓ OCI SDK installed
- ✓ OCI config found
- ✓ OCI connection successful
- ✓ API keys set

## Step 7: Generate Your First Cloud Books! 🚀

### Dry Run First (see what would happen, no cost)

```bash
python3 scripts/oci_book_generation.py --num-books 5 --dry-run
```

This shows:
- What instances would be created
- Estimated costs
- Expected time

### Real Generation (5 books, ~15 minutes, ~$0.25)

```bash
python3 scripts/oci_book_generation.py --num-books 5 --free-tier-only
```

**What happens**:
1. Creates 5 sample book outlines
2. Creates OCI instances (free tier)
3. Deploys book generation system
4. Generates 5 books in parallel
5. Shows real-time progress
6. Saves books to workspace
7. Shuts down instances
8. Shows cost report

### Scale Up (100 books)

Once you've verified it works:

```bash
# Check costs first
python3 scripts/oci_book_generation.py --num-books 100 --dry-run

# Generate
python3 scripts/oci_book_generation.py --num-books 100 --max-instances 4
```

## Troubleshooting

### "No module named 'oci'"

```bash
pip install oci --break-system-packages
# or
pip install --user oci
```

### "Could not load config"

Check your config file:
```bash
cat ~/.oci/config

# Make sure it has:
# [DEFAULT]
# user=ocid1.user...
# fingerprint=...
# tenancy=ocid1.tenancy...
# region=us-ashburn-1
# key_file=~/.oci/oci_api_key.pem
```

### "Permission denied" on key file

```bash
chmod 600 ~/.oci/oci_api_key.pem
```

### "Invalid key format"

You might have copied the public key instead of private. Re-download from Oracle Console.

### "No API keys set"

```bash
echo $GROQ_API_KEY
# If empty, set it:
export GROQ_API_KEY='your-key'
```

## Quick Reference

**After setup, to generate books**:

```bash
# Small test
python3 scripts/oci_book_generation.py --num-books 5 --free-tier-only

# Medium batch
python3 scripts/oci_book_generation.py --num-books 50

# Large batch
python3 scripts/oci_book_generation.py --num-books 100

# Check status
python3 scripts/verify_oci_integration.py
```

## Summary

You've completed: ✅ Oracle Cloud account

Still need:
- [ ] Get OCIDs (Step 1)
- [ ] Generate API key (Step 2)
- [ ] Configure locally (Step 3)
- [ ] Test connection (Step 4)
- [ ] Get LLM API key (Step 5)
- [ ] Verify setup (Step 6)
- [ ] Generate books (Step 7)

**Current step**: Go to Step 1 above ☝️

---

**Expected time**: 8 more minutes, then you're generating books!
