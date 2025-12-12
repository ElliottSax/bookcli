#!/usr/bin/env python3
"""
Complete example: Mass book generation using Oracle Cloud Infrastructure

This script demonstrates:
1. Setting up OCI for distributed book generation
2. Submitting batch jobs for multiple books
3. Monitoring progress and costs
4. Collecting results

Maximizes Oracle Free Tier ($300 credits + always-free resources)
"""

import os
import sys
import time
import argparse
from pathlib import Path
from typing import List, Dict

# Import our OCI components
try:
    from oci_instance_manager import OCIInstanceManager, InstanceConfig, InstanceShape
    from cloud_batch_orchestrator import CloudBatchOrchestrator, BookJob
    from oci_cost_tracker import OCICostTracker
    OCI_AVAILABLE = True
except ImportError as e:
    OCI_AVAILABLE = False
    print(f"❌ OCI components not available: {e}")
    print("\nPlease ensure OCI SDK is installed:")
    print("  pip install oci")
    sys.exit(1)


def check_prerequisites() -> bool:
    """Check if all prerequisites are met"""
    issues = []

    # Check OCI config
    oci_config = Path.home() / ".oci" / "config"
    if not oci_config.exists():
        issues.append("No OCI config found. Run: oci setup config")

    # Check API keys
    if not os.environ.get('GROQ_API_KEY') and not os.environ.get('DEEPSEEK_API_KEY'):
        issues.append("No LLM API keys set (GROQ_API_KEY or DEEPSEEK_API_KEY)")

    if issues:
        print("❌ Prerequisites not met:\n")
        for issue in issues:
            print(f"  • {issue}")
        print("\nRun setup script: bash scripts/setup_oci.sh")
        return False

    return True


def create_sample_outlines(count: int = 5) -> List[Path]:
    """Create sample book outlines for demonstration"""
    outlines = []
    outline_dir = Path("source/oci_batch")
    outline_dir.mkdir(parents=True, exist_ok=True)

    genres = ["fantasy", "science_fiction", "mystery", "romance", "thriller"]

    for i in range(count):
        genre = genres[i % len(genres)]
        outline_file = outline_dir / f"book_{i+1}_{genre}.txt"

        outline_content = f"""
Book Outline {i+1} - {genre.replace('_', ' ').title()}

Chapter 1: Introduction
- Establish main character and setting
- Present the initial situation
- Hint at the larger conflict

Chapter 2: Rising Action
- Introduce supporting characters
- Develop the main conflict
- First major challenge

Chapter 3: Complications
- Stakes are raised
- Character faces difficult choices
- Build tension

Chapter 4: Climax
- Main conflict reaches peak
- Character must make crucial decision
- Action-packed resolution

Chapter 5: Resolution
- Tie up loose ends
- Show character growth
- Satisfying conclusion

Target: 30,000 words
Genre: {genre}
Tone: Engaging and immersive
"""

        outline_file.write_text(outline_content)
        outlines.append(outline_file)

    print(f"✓ Created {count} sample outlines in {outline_dir}")
    return outlines


def run_batch_generation(num_books: int = 5, max_instances: int = 4,
                         use_free_tier_only: bool = True,
                         dry_run: bool = False):
    """
    Run batch book generation on OCI

    Args:
        num_books: Number of books to generate
        max_instances: Maximum concurrent instances
        use_free_tier_only: Only use free tier resources
        dry_run: Show plan without creating instances
    """
    print("="*70)
    print("ORACLE CLOUD BOOK GENERATION")
    print("="*70)
    print()

    # Initialize components
    print("Initializing OCI manager...")
    oci_manager = OCIInstanceManager(max_spend=300.0)

    print("Initializing cost tracker...")
    cost_tracker = OCICostTracker(max_budget=300.0)

    print("Initializing batch orchestrator...")
    orchestrator = CloudBatchOrchestrator(
        oci_manager=oci_manager,
        max_instances=max_instances,
        auto_scale=True
    )

    # Create sample outlines
    print(f"\nPreparing {num_books} book generation jobs...")
    outlines = create_sample_outlines(num_books)

    # Submit batch jobs
    jobs = []
    for i, outline in enumerate(outlines):
        # Determine genre from filename
        filename = outline.name
        if "fantasy" in filename:
            genre = "fantasy"
        elif "science_fiction" in filename:
            genre = "science_fiction"
        elif "mystery" in filename:
            genre = "mystery"
        elif "romance" in filename:
            genre = "sapphic_romance"
        else:
            genre = "thriller"

        # Prefer cheap providers
        provider = "groq" if os.environ.get('GROQ_API_KEY') else "deepseek"

        job_config = {
            'source_file': str(outline),
            'book_name': f"cloud-book-{i+1}-{genre}",
            'genre': genre,
            'target_words': 30000,
            'provider': provider
        }
        jobs.append(job_config)

    print(f"✓ Prepared {len(jobs)} jobs")

    # Show cost estimate
    print("\n" + "="*70)
    print("COST ESTIMATE")
    print("="*70)

    if use_free_tier_only:
        print("Strategy: FREE TIER ONLY")
        print("  • Using Ampere A1 instances (always free)")
        print("  • Up to 4 OCPUs available")
        print("  • Cloud cost: $0.00")
    else:
        print("Strategy: FREE TIER + PAID")
        print("  • Using free tier when available")
        print("  • Paid instances if needed")
        print("  • Cloud cost: ~$0.05-0.10 per instance/hour")

    # Estimate LLM costs
    avg_cost_per_book = 0.05  # Groq/DeepSeek average
    estimated_llm_cost = num_books * avg_cost_per_book

    print(f"\nLLM API costs (estimated):")
    print(f"  • Books: {num_books}")
    print(f"  • Cost per book: ~${avg_cost_per_book:.2f}")
    print(f"  • Total LLM cost: ~${estimated_llm_cost:.2f}")

    estimated_cloud_cost = 0.0 if use_free_tier_only else num_books * 0.02
    total_estimated = estimated_llm_cost + estimated_cloud_cost

    print(f"\nTotal estimated cost: ${total_estimated:.2f}")
    print(f"Books possible with $300: ~{int(300 / avg_cost_per_book)}")

    if dry_run:
        print("\n[DRY RUN MODE - No instances will be created]")
        print("\nTo run for real, remove --dry-run flag")
        return

    # Confirm before proceeding
    print("\n" + "="*70)
    response = input("Proceed with book generation? (y/n): ")
    if response.lower() != 'y':
        print("Cancelled")
        return

    # Submit jobs
    print("\nSubmitting batch jobs...")
    job_ids = orchestrator.submit_batch(jobs)
    print(f"✓ Submitted {len(job_ids)} jobs")

    # Monitor progress
    print("\nMonitoring progress...")
    print("(Press Ctrl+C to stop monitoring, jobs will continue)\n")

    try:
        while True:
            orchestrator.print_status()

            # Check if all jobs complete
            stats = orchestrator.job_queue.get_queue_stats()
            pending = stats['queued'] + stats['assigned'] + stats['running']

            if pending == 0:
                print("✓ All jobs completed!")
                break

            time.sleep(30)

    except KeyboardInterrupt:
        print("\n\nStopping monitoring (jobs continue in background)")

    # Final status
    print("\n" + "="*70)
    print("FINAL STATUS")
    print("="*70)
    orchestrator.print_status()
    cost_tracker.print_cost_report(detailed=True)

    # Cleanup
    print("\nCleaning up instances...")
    orchestrator.cleanup()
    print("✓ Cleanup complete")

    print("\n" + "="*70)
    print("GENERATION COMPLETE")
    print("="*70)
    print(f"\nBooks generated: {stats['completed']}")
    print(f"Failed: {stats['failed']}")
    print(f"\nResults available in: workspace/")


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Generate books at scale using Oracle Cloud Infrastructure",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Generate 5 books using free tier only
  python3 oci_book_generation.py --num-books 5 --free-tier-only

  # Generate 20 books using up to 10 instances
  python3 oci_book_generation.py --num-books 20 --max-instances 10

  # Dry run to see costs without generating
  python3 oci_book_generation.py --num-books 10 --dry-run

Maximize your $300 OCI credits:
  • Use free tier instances (4 Ampere cores forever free)
  • Use cheap LLM providers (Groq: ~$0.05/book, DeepSeek: ~$0.03/book)
  • Generate in parallel for maximum throughput
  • With $300, you can generate ~6,000 books using free tier + cheap LLMs!
        """
    )

    parser.add_argument(
        '--num-books', type=int, default=5,
        help='Number of books to generate (default: 5)'
    )
    parser.add_argument(
        '--max-instances', type=int, default=4,
        help='Maximum concurrent instances (default: 4)'
    )
    parser.add_argument(
        '--free-tier-only', action='store_true',
        help='Use only free tier resources'
    )
    parser.add_argument(
        '--dry-run', action='store_true',
        help='Show plan without actually generating'
    )

    args = parser.parse_args()

    # Check prerequisites
    if not check_prerequisites():
        sys.exit(1)

    # Run batch generation
    run_batch_generation(
        num_books=args.num_books,
        max_instances=args.max_instances,
        use_free_tier_only=args.free_tier_only,
        dry_run=args.dry_run
    )


if __name__ == "__main__":
    main()
