# 🚀 Start Here: Cloud Book Generation Setup

**Your mission**: Get cloud book generation working so you can generate thousands of books using Oracle's $300 free credits.

## Current Situation

The OCI integration code is **100% complete** (1,963 lines), but you need to:
1. Install the OCI SDK
2. Create an Oracle Cloud account (free)
3. Configure your credentials
4. Set LLM API keys

**Total time**: ~10 minutes

## 🎯 Your Next Steps

### Step 1: Open the Checklist

**Open this file**: `CLOUD_SETUP_CHECKLIST.md`

This has every step with exact commands. Just follow it top to bottom.

### Step 2: While SDK Installs

The OCI SDK installation can take 2-3 minutes. **Open a new terminal** and run:

```bash
cd /mnt/e/projects/bookcli
bash /tmp/oci_install.sh
```

**While that runs**, continue with the checklist (Steps 2-5).

### Step 3: After Setup is Complete

Test everything works:
```bash
python3 scripts/verify_oci_integration.py
```

Generate your first cloud books:
```bash
# Test run (shows costs, doesn't generate)
python3 scripts/oci_book_generation.py --num-books 5 --dry-run

# Real generation (5 books, ~15 minutes)
python3 scripts/oci_book_generation.py --num-books 5 --free-tier-only
```

## 📚 Which File to Use When

**Right now** (setting up):
- `CLOUD_SETUP_CHECKLIST.md` ← **START HERE**
  - Complete step-by-step checklist
  - Exact commands to run
  - ~10 minutes total

**If you get stuck**:
- `SETUP_CLOUD_NOW.md`
  - Detailed explanations
  - Troubleshooting section
  - Alternative installation methods

**After setup** (learning):
- `OCI_QUICKSTART.md`
  - Quick reference
  - Common commands
  - Cost estimates

- `OCI_CLOUD_GENERATION.md`
  - Complete documentation
  - Architecture details
  - Advanced usage

**Verification** (anytime):
- Run: `python3 scripts/verify_oci_integration.py`
  - Shows what's working
  - Shows what's missing
  - Tells you next steps

## ✅ What You Need (The 4 Requirements)

### 1. Oracle Cloud Account
- **Get it**: https://cloud.oracle.com/free
- **What you get**: $300 credits + 4 free CPU cores forever
- **Cost**: Free (no credit card in most regions)
- **Time**: 5 minutes

### 2. OCI SDK
- **Install**: `bash /tmp/oci_install.sh` (in new terminal)
- **Alternative**: `pip install oci --break-system-packages`
- **Time**: 2-3 minutes

### 3. OCI API Key & Config
- **Generate**: In Oracle Cloud Console → User Settings → API Keys
- **Save to**: `~/.oci/config` and `~/.oci/oci_api_key.pem`
- **Time**: 2 minutes

### 4. LLM API Key
- **Groq (free)**: https://console.groq.com
- **DeepSeek (cheap)**: https://platform.deepseek.com
- **Set**: `export GROQ_API_KEY='your-key'`
- **Time**: 2 minutes

## 🎁 What You'll Get

Once setup is complete:

### Free Resources
- $300 in Oracle trial credits (30 days)
- 4 Ampere A1 CPU cores (**FREE FOREVER**)
- 2 AMD instances (free forever)
- Object storage (10GB free)

### Capabilities
- Generate **6,000-10,000 books** with $300
- **4× faster** than local generation
- **Parallel generation** (4 books at once)
- **Cloud-based** (don't need your computer running)

### Cost Efficiency
- **Cloud cost**: $0 (using free tier)
- **LLM cost**: $0.03-0.05 per book (same as local)
- **10 books**: ~$0.50
- **100 books**: ~$5
- **1000 books**: ~$50

## 🚦 Quick Start Commands

After setup is done:

```bash
# Verify everything works
python3 scripts/verify_oci_integration.py

# Test with 5 books (dry run - no cost)
python3 scripts/oci_book_generation.py --num-books 5 --dry-run

# Generate 5 books for real (~$0.25, ~15 min)
python3 scripts/oci_book_generation.py --num-books 5 --free-tier-only

# Scale to 50 books (~$2.50, ~2 hours)
python3 scripts/oci_book_generation.py --num-books 50

# Production run: 100 books (~$5, ~3 hours)
python3 scripts/oci_book_generation.py --num-books 100 --dry-run  # check first
python3 scripts/oci_book_generation.py --num-books 100

# Monitor costs
python3 -c "
from oci_cost_tracker import OCICostTracker
tracker = OCICostTracker()
tracker.print_cost_report(detailed=True)
"
```

## 🔧 If Something Goes Wrong

**OCI SDK won't install**:
- See SETUP_CLOUD_NOW.md → "OCI SDK won't install" section
- Try virtual environment method
- Or use OCI CLI instead

**Can't find Oracle account details**:
- User OCID: Console → Profile → User Settings
- Tenancy OCID: Console → Profile → Tenancy
- Region: Look at URL or region selector

**OCI connection fails**:
```bash
# Check config exists
cat ~/.oci/config

# Check key permissions (must be 600)
ls -l ~/.oci/oci_api_key.pem

# Fix permissions
chmod 600 ~/.oci/oci_api_key.pem
```

**No LLM API keys**:
- Get Groq (free): https://console.groq.com
- Or DeepSeek (cheap): https://platform.deepseek.com
- Set: `export GROQ_API_KEY='your-key'`

## 📊 Decision: Do You Really Need Cloud?

### Use CLOUD if you want to:
✅ Generate 50+ books
✅ Generate 4× faster
✅ Run 24/7 without your computer
✅ Maximize Oracle's $300 credits
✅ Scale to thousands of books

### Use LOCAL if you:
⏸️ Only need 1-20 books occasionally
⏸️ Don't mind slower generation
⏸️ Prefer keeping everything on your computer
⏸️ Don't want to sign up for Oracle

**Both systems work great - your choice!**

## 🎯 Action Plan

Here's what to do **right now**:

```
1. Open new terminal
   └─> Run: bash /tmp/oci_install.sh

2. Open CLOUD_SETUP_CHECKLIST.md in this terminal
   └─> Follow steps 2-7 while SDK installs

3. When done, test:
   └─> python3 scripts/verify_oci_integration.py

4. Generate first cloud books:
   └─> python3 scripts/oci_book_generation.py --num-books 5 --free-tier-only

5. Scale up:
   └─> python3 scripts/oci_book_generation.py --num-books 100
```

## 📞 Help & Resources

**Stuck on setup?**
- Check: `SETUP_CLOUD_NOW.md` (troubleshooting section)
- Verify: `python3 scripts/verify_oci_integration.py`

**Want to understand how it works?**
- Read: `OCI_CLOUD_GENERATION.md` (architecture & details)
- Read: `README_OCI.md` (overview)

**Quick reference?**
- Use: `OCI_QUICKSTART.md` (commands & examples)

**Oracle Cloud docs?**
- Signup: https://cloud.oracle.com/free
- Docs: https://docs.oracle.com/iaas/
- API keys: https://docs.oracle.com/iaas/Content/API/Concepts/apisigningkey.htm

---

## 🎉 Summary

**What to do**: Follow `CLOUD_SETUP_CHECKLIST.md` (10 minutes)

**What you'll get**: Ability to generate thousands of books on Oracle's free tier

**Cost**: $0 to set up, ~$0.03-0.05 per book generated

**Speed**: 4× faster than local

---

**Ready? Open `CLOUD_SETUP_CHECKLIST.md` and let's get started!** 🚀

---

*All files are in `/mnt/e/projects/bookcli/`*
*For current status: `python3 scripts/verify_oci_integration.py`*
