# OCI Cloud Generation - 5 Minute Quickstart

Generate thousands of books using Oracle's $300 free credits + always-free cloud resources.

## Prerequisites (1 minute)

```bash
# 1. Python 3.8+
python3 --version

# 2. Install OCI requirements
pip install -r requirements-oci.txt

# Or just OCI SDK
pip install oci
```

## Setup (3 minutes)

### Step 1: Oracle Cloud Account

1. Visit: https://cloud.oracle.com/free
2. Sign up (free, no credit card in some regions)
3. Get: **$300 credits + 4 always-free Ampere cores**

### Step 2: Configure OCI

```bash
# Install OCI CLI
pip install oci-cli

# Run setup wizard
oci setup config

# Follow prompts:
# - Enter your User OCID
# - Enter your Tenancy OCID
# - Enter your region
# - Generate API key pair (Y)
```

This creates `~/.oci/config`

### Step 3: Set LLM API Keys

```bash
# Get free/cheap API keys:
# - Groq: https://console.groq.com (free tier)
# - DeepSeek: https://platform.deepseek.com (ultra cheap)

export GROQ_API_KEY='your-groq-key-here'
export DEEPSEEK_API_KEY='your-deepseek-key-here'
```

## Generate Books (1 minute to start)

### Quick Test (5 books)

```bash
python3 scripts/oci_book_generation.py --num-books 5 --free-tier-only
```

This will:
1. Create 5 sample book outlines
2. Spin up OCI instances (free tier)
3. Generate books in parallel
4. Show real-time progress
5. Display cost report

**Expected cost: $0.15-0.25 (LLM only, cloud is free)**

### Scale Up (100 books)

```bash
python3 scripts/oci_book_generation.py --num-books 100 --max-instances 4
```

**Expected cost: $3-5 for 100 books (~$0.03-0.05 per book)**

### Maximum Scale (1000+ books)

```bash
# Dry run first to see costs
python3 scripts/oci_book_generation.py --num-books 1000 --dry-run

# Then run for real
python3 scripts/oci_book_generation.py --num-books 1000 --max-instances 4
```

**Expected cost: $30-50 for 1000 books**

## What Happens

```
1. Creates OCI compute instances (free tier priority)
2. Installs book generation system on each
3. Distributes jobs across instances
4. Generates books in parallel
5. Monitors progress & costs
6. Collects results
7. Shuts down instances
```

## Monitoring

The script shows real-time updates:

```
CLOUD BATCH ORCHESTRATOR STATUS
================================================================

Jobs:
  Queued:    85
  Running:   4
  Completed: 11
  Failed:    0

Instances:
  Active: 4/4 (all free tier)

Costs:
  LLM API:   $0.33
  Cloud:     $0.00 (free tier)
  Total:     $0.33

Books Possible with $300: ~9,090
================================================================
```

## Cost Optimization

### Free Tier Only (Recommended)
```bash
python3 scripts/oci_book_generation.py \
  --num-books 100 \
  --max-instances 4 \
  --free-tier-only
```
- **Cloud cost**: $0 (using always-free instances)
- **LLM cost**: ~$3-5 (using Groq/DeepSeek)
- **Total**: ~$3-5 for 100 books

### Maximum Speed (Uses Paid Instances)
```bash
python3 scripts/oci_book_generation.py \
  --num-books 100 \
  --max-instances 10
```
- **Cloud cost**: ~$2-5 (paid instances)
- **LLM cost**: ~$3-5
- **Total**: ~$5-10 for 100 books
- **Benefit**: 2.5x faster

## ROI: What Can You Generate?

### With $300 Budget

| Strategy | Books | Cost/Book | Cloud Cost | LLM Cost |
|----------|-------|-----------|------------|----------|
| **Free Tier + DeepSeek** | ~10,000 | $0.03 | $0 | $300 |
| **Free Tier + Groq** | ~6,000 | $0.05 | $0 | $300 |
| **Paid + DeepSeek** | ~7,500 | $0.04 | $75 | $225 |
| **Paid + Groq** | ~5,000 | $0.06 | $75 | $225 |

**Recommendation**: Free Tier + DeepSeek for maximum books

### Time Estimates

With 4 parallel instances (free tier):
- ~8 books/hour
- ~192 books/day
- ~1,440 books/week

With $300 budget:
- **10,000 books in ~52 days** (free tier + DeepSeek)
- Or generate **192 books/day** indefinitely on free tier

## Advanced Usage

### Custom Batch Generation

```python
from cloud_batch_orchestrator import CloudBatchOrchestrator
from oci_instance_manager import OCIInstanceManager

# Initialize
manager = OCIInstanceManager(max_spend=300.0)
orchestrator = CloudBatchOrchestrator(manager, max_instances=4)

# Define your books
jobs = [
    {
        'source_file': 'outlines/fantasy-series-1.txt',
        'book_name': 'dragon-wars-book-1',
        'genre': 'fantasy',
        'target_words': 50000,
        'provider': 'groq'
    },
    # ... add more
]

# Generate
orchestrator.submit_batch(jobs)
orchestrator.wait_for_completion()
```

### Cost Tracking

```python
from oci_cost_tracker import OCICostTracker

tracker = OCICostTracker(max_budget=300.0)
tracker.print_cost_report(detailed=True)

# Export to CSV for analysis
tracker.export_costs_csv(Path("costs.csv"))
```

## Troubleshooting

### "No OCI config found"
```bash
# Run OCI setup
oci setup config
```

### "No API keys set"
```bash
export GROQ_API_KEY='your-key'
export DEEPSEEK_API_KEY='your-key'
```

### "Instance creation failed"
- Check your OCI compartment ID
- Verify API key permissions
- Ensure free tier quota available

### Books not generating
```bash
# Check instance status
python3 -c "
from oci_instance_manager import OCIInstanceManager
mgr = OCIInstanceManager()
mgr.print_status_report()
"
```

## Next Steps

1. **Read full documentation**: See `OCI_CLOUD_GENERATION.md`
2. **Customize generation**: Modify scripts in `scripts/`
3. **Scale production**: Use job queue for large batches
4. **Monitor costs**: Set up alerts at 50%, 75%, 90% budget

## Support

- **Full docs**: `OCI_CLOUD_GENERATION.md`
- **OCI docs**: https://docs.oracle.com/iaas/
- **Free tier info**: https://cloud.oracle.com/free

---

**Ready to generate thousands of books? Run the quickstart command:**

```bash
python3 scripts/oci_book_generation.py --num-books 10 --free-tier-only
```

**Estimated time**: 15 minutes to generate 10 books
**Estimated cost**: $0.30-0.50 (all LLM, cloud is free)
