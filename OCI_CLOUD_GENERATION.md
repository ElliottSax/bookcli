# Oracle Cloud Integration for Mass Book Generation

**Maximize your Oracle Free Tier ($300 credits + always-free resources) to generate thousands of books**

## Overview

This integration enables distributed book generation across Oracle Cloud Infrastructure (OCI) compute instances. Generate books in parallel at massive scale while optimizing costs.

## What You Get

### Oracle Free Tier Benefits
- **$300 in free trial credits** (valid for 30 days)
- **Always Free services** (available forever):
  - 4 Arm-based Ampere A1 cores (up to 24GB RAM)
  - 2 AMD compute instances (1/8 OCPU + 1GB RAM each)
  - 200 GB block storage
  - 10 GB object storage

### Combined with Cheap LLM APIs
- **Groq**: ~$0.05 per 30k word book
- **DeepSeek**: ~$0.03 per 30k word book
- **OpenRouter**: Various models, competitive pricing

### Result: Generate ~6,000+ Books with $300

Using free tier instances + cheap LLMs, you can generate approximately:
- **Unlimited books** on free tier (compute cost: $0)
- **6,000 books** with $300 in LLM costs (~$0.05/book)
- **Parallel generation** across 4 instances = 4x faster

## Quick Start

### 1. Install Prerequisites

```bash
# Install OCI SDK
pip install oci

# Or run our setup script
bash scripts/setup_oci.sh
```

### 2. Configure Oracle Cloud

1. **Sign up for Oracle Cloud Free Tier**:
   - Visit: https://cloud.oracle.com/free
   - Get $300 in credits + always-free services
   - No credit card required in some regions

2. **Generate API Key**:
   ```bash
   # Install OCI CLI
   pip install oci-cli

   # Run setup wizard
   oci setup config
   ```

   Follow the prompts to create `~/.oci/config`

3. **Set LLM API Keys**:
   ```bash
   export GROQ_API_KEY='your-groq-key'
   export DEEPSEEK_API_KEY='your-deepseek-key'
   ```

### 3. Generate Books at Scale

```bash
# Generate 10 books using free tier only
python3 scripts/oci_book_generation.py --num-books 10 --free-tier-only

# Generate 50 books using up to 4 instances
python3 scripts/oci_book_generation.py --num-books 50 --max-instances 4

# Dry run to see costs first
python3 scripts/oci_book_generation.py --num-books 100 --dry-run
```

## Architecture

```
┌─────────────────────┐
│   Control Node      │
│  (Your Computer)    │
│                     │
│  • Job Queue        │
│  • Cost Tracker     │
│  • Orchestrator     │
└──────────┬──────────┘
           │
           │ Manages & Monitors
           │
    ┌──────┴──────────────────────┐
    │                             │
┌───▼────────┐    ┌──────────┐  ┌──────────┐
│ OCI        │    │ OCI      │  │ OCI      │
│ Instance 1 │    │ Instance │  │ Instance │
│            │    │ 2        │  │ 3        │
│ Generating │    │ Generat- │  │ Generat- │
│ Book 1     │    │ ing      │  │ ing      │
│            │    │ Book 2   │  │ Book 3   │
└────────────┘    └──────────┘  └──────────┘
     │                  │              │
     └──────────┬───────┴──────────────┘
                │
                │ Results
                ▼
        ┌───────────────┐
        │ Object Storage│
        │  (Generated   │
        │   Books)      │
        └───────────────┘
```

## Components

### 1. OCI Instance Manager (`oci_instance_manager.py`)

Manages OCI compute instances:
- Creates/starts/stops instances
- Prioritizes free tier resources
- Deploys book generation system
- Tracks costs against $300 budget

```python
from oci_instance_manager import OCIInstanceManager, InstanceConfig

# Initialize manager
manager = OCIInstanceManager(max_spend=300.0)

# Create free tier instance
config = InstanceConfig(
    shape="VM.Standard.A1.Flex",
    ocpus=2,
    memory_gb=12,
    use_free_tier=True
)

instance_id = manager.create_instance("bookgen-1", config)
```

### 2. Cloud Batch Orchestrator (`cloud_batch_orchestrator.py`)

Manages distributed book generation:
- SQLite job queue
- Auto-scaling based on queue depth
- Job assignment to instances
- Progress monitoring

```python
from cloud_batch_orchestrator import CloudBatchOrchestrator

orchestrator = CloudBatchOrchestrator(
    oci_manager=manager,
    max_instances=4,
    auto_scale=True
)

# Submit batch jobs
jobs = [
    {
        'source_file': 'outline1.txt',
        'book_name': 'fantasy-epic-1',
        'genre': 'fantasy',
        'target_words': 30000,
        'provider': 'groq'
    },
    # ... more jobs
]

job_ids = orchestrator.submit_batch(jobs)
orchestrator.wait_for_completion()
```

### 3. OCI Cost Tracker (`oci_cost_tracker.py`)

Comprehensive cost tracking:
- Cloud infrastructure costs (OCI)
- LLM API costs (all providers)
- Cost per book metrics
- Budget burn rate analysis

```python
from oci_cost_tracker import OCICostTracker

tracker = OCICostTracker(max_budget=300.0)

# Costs are tracked automatically
# View report
tracker.print_cost_report(detailed=True)
```

## Cost Optimization Strategies

### Strategy 1: Free Tier Only (Unlimited Books)
- Use 4 Ampere A1 cores (always free)
- Use cheap LLM providers (Groq/DeepSeek)
- Cloud cost: $0
- LLM cost: ~$0.03-0.05 per book
- **Books with $300: ~6,000-10,000**

### Strategy 2: Free Tier + Paid (Maximum Speed)
- Start with free tier instances
- Scale to paid instances for queue bursts
- Cloud cost: ~$0.01-0.02 per book
- Total cost: ~$0.04-0.07 per book
- **Books with $300: ~4,000-7,500**

### Strategy 3: Cost Minimization
- Sequential generation on single free instance
- DeepSeek API only (~$0.03/book)
- Cloud cost: $0
- **Books with $300: ~10,000**

## Usage Examples

### Example 1: Generate 100 Fantasy Books

```bash
# Create 100 fantasy book outlines
mkdir -p source/fantasy_batch
# ... create outlines

# Generate all books in parallel
python3 scripts/oci_book_generation.py \
  --num-books 100 \
  --max-instances 4 \
  --free-tier-only
```

### Example 2: Mixed Genre Batch

```python
from cloud_batch_orchestrator import CloudBatchOrchestrator
from oci_instance_manager import OCIInstanceManager

# Initialize
manager = OCIInstanceManager(max_spend=300.0)
orchestrator = CloudBatchOrchestrator(manager, max_instances=4)

# Submit diverse jobs
jobs = []
genres = ['fantasy', 'science_fiction', 'mystery', 'romance', 'thriller']

for i in range(50):
    jobs.append({
        'source_file': f'source/outline_{i}.txt',
        'book_name': f'book-{i}-{genres[i % 5]}',
        'genre': genres[i % 5],
        'target_words': 30000,
        'provider': 'groq'  # or 'deepseek'
    })

# Generate all
orchestrator.submit_batch(jobs)
orchestrator.wait_for_completion()
orchestrator.print_status()
```

### Example 3: Cost-Optimized Generation

```python
# Use DeepSeek (cheapest) with free tier only
orchestrator = CloudBatchOrchestrator(
    oci_manager=manager,
    max_instances=4,  # All free tier
    auto_scale=False  # Don't create paid instances
)

# Force DeepSeek provider
jobs = [
    {
        'source_file': outline,
        'book_name': f'budget-book-{i}',
        'genre': 'fantasy',
        'target_words': 30000,
        'provider': 'deepseek'  # Cheapest option
    }
    for i, outline in enumerate(outlines)
]

orchestrator.submit_batch(jobs)
```

## Monitoring and Reporting

### Real-time Monitoring

The orchestrator provides real-time progress updates:

```
==================================================================
CLOUD BATCH ORCHESTRATOR STATUS
==================================================================

Jobs:
  Queued:    45
  Assigned:  3
  Running:   4
  Completed: 12
  Failed:    1

Instances:
  Active: 4/4

Costs:
  LLM API:   $0.52
  Cloud:     $0.00
  Total:     $0.52

Budget:
  Spent:     $0.52
  Remaining: $299.48 (99.8%)
==================================================================
```

### Cost Reports

Detailed cost breakdown:

```bash
# Get comprehensive cost report
python3 -c "
from oci_cost_tracker import OCICostTracker
tracker = OCICostTracker()
tracker.print_cost_report(detailed=True)
"
```

Output:
```
==================================================================
COST TRACKING REPORT
==================================================================

Budget:
  Total Budget:    $300.00
  Spent:           $5.23 (1.7%)
  Remaining:       $294.77

Burn Rate:
  Daily:           $1.05/day
  Days Remaining:  280.7 days

Production:
  Books Generated: 100
  Cost per Book:   $0.05
  Books Possible:  ~5,895 with remaining budget

Cost Breakdown:
  Cloud (OCI):     $0.00 (0.0%)
  LLM APIs:        $5.23 (100.0%)
    Groq:          $3.15
    DeepSeek:      $2.08

  Total:           $5.23

Recommendations:
  ✓ Excellent: Low spending, lots of runway
  💡 Most cost-effective provider: DeepSeek
==================================================================
```

## Advanced Features

### Custom Instance Configuration

```python
from oci_instance_manager import InstanceConfig, InstanceShape

# High-performance instance (uses paid credits)
config = InstanceConfig(
    shape=InstanceShape.AMPERE_MEDIUM.value,
    ocpus=4,
    memory_gb=24,
    boot_volume_gb=100,
    use_free_tier=False
)

instance_id = manager.create_instance("high-perf-1", config)
```

### Job Priority and Scheduling

```python
# Priority queuing (implement custom logic)
high_priority_jobs = [...]
normal_priority_jobs = [...]

# Submit high priority first
orchestrator.submit_batch(high_priority_jobs)

# Wait for some completion
time.sleep(600)  # 10 minutes

# Then submit normal priority
orchestrator.submit_batch(normal_priority_jobs)
```

### Result Aggregation

```python
# Get all completed books
stats = orchestrator.job_queue.get_queue_stats()
completed_count = stats['completed']

# Export job history
import sqlite3
conn = sqlite3.connect("workspace/book_jobs.db")
cursor = conn.cursor()
cursor.execute("SELECT * FROM jobs WHERE status = 'completed'")
completed_jobs = cursor.fetchall()

# Process results
for job in completed_jobs:
    print(f"Book: {job['book_name']}")
    print(f"  Path: {job['result_path']}")
    print(f"  Cost: ${job['cost_llm'] + job['cost_cloud']:.2f}")
```

## Troubleshooting

### Issue: OCI Config Not Found

```bash
# Solution: Run OCI setup
pip install oci-cli
oci setup config

# Follow prompts to configure
```

### Issue: No API Keys Set

```bash
# Solution: Set environment variables
export GROQ_API_KEY='your-key-here'
export DEEPSEEK_API_KEY='your-key-here'

# Or add to ~/.bashrc for persistence
echo "export GROQ_API_KEY='your-key'" >> ~/.bashrc
source ~/.bashrc
```

### Issue: Instance Creation Fails

Check:
1. OCI credentials are valid: `oci iam user get --user-id YOUR_USER_ID`
2. Compartment ID is correct
3. Subnet and availability domain exist
4. Free tier quota not exhausted

### Issue: Jobs Stuck in Queue

```python
# Check instance status
orchestrator.oci_manager.list_instances()

# Check for failed instances
orchestrator.oci_manager.print_status_report()

# Manually assign jobs
orchestrator.assign_jobs_to_instances()
```

## Best Practices

### 1. Start Small
- Test with 5-10 books first
- Verify costs are as expected
- Scale up gradually

### 2. Monitor Costs
- Check cost reports frequently
- Set alerts at 50%, 75%, 90% budget
- Use `--dry-run` for large batches

### 3. Optimize Provider Selection
- Use DeepSeek for lowest cost
- Use Groq for best speed/cost balance
- Avoid expensive providers (OpenAI, Claude) for mass generation

### 4. Leverage Free Tier
- Always use free tier instances first
- Only scale to paid if needed
- Shutdown instances when done

### 5. Batch Strategically
- Submit 50-100 jobs at a time
- Don't overload queue (memory usage)
- Stagger submissions for very large batches (1000+)

## ROI Calculator

**Scenario**: Romance author generating series

- **Free Tier Setup**:
  - Initial setup: 30 minutes
  - OCI free tier: 4 Ampere cores
  - LLM: DeepSeek (~$0.03/book)

- **Generation Rate**:
  - 4 parallel instances
  - ~30 minutes per book
  - ~8 books/hour
  - ~192 books/day (24 hours)

- **Cost**:
  - Cloud: $0 (free tier)
  - LLM: $0.03/book
  - **Total: $5.76/day for 192 books**
  - **Or: $0.03 per 30,000-word novel**

- **With $300 Budget**:
  - Can generate: 10,000 books
  - Time: ~52 days running 24/7
  - Or: 1,250 days generating 8 books/day

**Compare to Manual**:
- Manual writing: $0.10-0.50 per word = $3,000-15,000 per 30k book
- AI cloud generation: $0.03 per 30k book
- **Savings: 99.9%+**

## Conclusion

The OCI integration enables:
- ✅ **Massive parallel generation** (4+ instances)
- ✅ **Near-zero cloud costs** (free tier)
- ✅ **Minimal LLM costs** ($0.03-0.05/book)
- ✅ **Automated scaling** (based on queue)
- ✅ **Comprehensive monitoring** (costs, progress, quality)

**Get started today and generate thousands of books with your $300 OCI credits!**

## Support

- **OCI Documentation**: https://docs.oracle.com/iaas/
- **Free Tier Info**: https://cloud.oracle.com/free
- **API Setup Guide**: https://docs.oracle.com/iaas/Content/API/Concepts/apisigningkey.htm
- **Book Generation System**: See `README.md`

---

**Generated with the Book Factory System**
For more information, see project documentation.
