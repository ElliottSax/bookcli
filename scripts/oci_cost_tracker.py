#!/usr/bin/env python3
"""
OCI Cost Tracker - Integrated with existing cost optimizer
Tracks both cloud infrastructure and LLM API costs

Integrates with:
- cost_optimizer.py: LLM API cost tracking
- oci_instance_manager.py: Cloud instance cost tracking
"""

import json
import time
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta

try:
    from cost_optimizer import CostOptimizer
    COST_OPTIMIZER_AVAILABLE = True
except ImportError:
    COST_OPTIMIZER_AVAILABLE = False


@dataclass
class CostBreakdown:
    """Detailed cost breakdown"""
    # Cloud costs (OCI)
    cloud_compute: float = 0.0
    cloud_storage: float = 0.0
    cloud_network: float = 0.0
    cloud_total: float = 0.0

    # LLM API costs
    llm_groq: float = 0.0
    llm_deepseek: float = 0.0
    llm_openrouter: float = 0.0
    llm_anthropic: float = 0.0
    llm_openai: float = 0.0
    llm_total: float = 0.0

    # Total
    total_cost: float = 0.0

    # Books generated
    books_generated: int = 0
    cost_per_book: float = 0.0


class OCICostTracker:
    """
    Comprehensive cost tracker for cloud book generation

    Tracks:
    - OCI compute instance costs (by shape and usage)
    - OCI storage costs
    - LLM API costs (all providers)
    - Cost per book metrics
    - Budget burn rate
    """

    def __init__(self, max_budget: float = 300.0):
        """
        Initialize cost tracker

        Args:
            max_budget: Maximum budget (OCI trial credits)
        """
        self.max_budget = max_budget

        # Cost tracking file
        self.cost_file = Path("workspace/oci_costs.json")
        self.cost_file.parent.mkdir(parents=True, exist_ok=True)

        # Load existing costs
        self.costs: List[Dict] = []
        self._load_costs()

        # Integrate with existing cost optimizer if available
        if COST_OPTIMIZER_AVAILABLE:
            self.llm_optimizer = CostOptimizer()
        else:
            self.llm_optimizer = None

    def _load_costs(self):
        """Load cost history from disk"""
        if self.cost_file.exists():
            with open(self.cost_file, 'r') as f:
                data = json.load(f)
                self.costs = data.get('costs', [])

    def _save_costs(self):
        """Save cost history to disk"""
        data = {
            'costs': self.costs,
            'last_updated': time.time()
        }

        with open(self.cost_file, 'w') as f:
            json.dump(data, f, indent=2)

    def record_cloud_cost(self, instance_id: str, instance_shape: str,
                         uptime_hours: float, cost: float,
                         operation: str = "compute"):
        """
        Record cloud infrastructure cost

        Args:
            instance_id: OCI instance ID
            instance_shape: Instance shape (e.g., VM.Standard.A1.Flex)
            uptime_hours: Hours the instance ran
            cost: Total cost for this operation
            operation: Type of operation (compute, storage, network)
        """
        cost_entry = {
            'timestamp': time.time(),
            'type': 'cloud',
            'operation': operation,
            'instance_id': instance_id,
            'instance_shape': instance_shape,
            'uptime_hours': uptime_hours,
            'cost': cost,
            'category': 'oci'
        }

        self.costs.append(cost_entry)
        self._save_costs()

    def record_llm_cost(self, provider: str, model: str, tokens: int, cost: float,
                       book_name: Optional[str] = None):
        """
        Record LLM API cost

        Args:
            provider: LLM provider (groq, deepseek, etc.)
            model: Model used
            tokens: Total tokens consumed
            cost: Total cost
            book_name: Book being generated (for attribution)
        """
        cost_entry = {
            'timestamp': time.time(),
            'type': 'llm',
            'provider': provider,
            'model': model,
            'tokens': tokens,
            'cost': cost,
            'book_name': book_name,
            'category': 'api'
        }

        self.costs.append(cost_entry)
        self._save_costs()

    def record_book_completion(self, book_name: str, total_cost: float):
        """
        Record completed book and its total cost

        Args:
            book_name: Name of completed book
            total_cost: Total cost to generate this book
        """
        cost_entry = {
            'timestamp': time.time(),
            'type': 'book_completed',
            'book_name': book_name,
            'cost': total_cost,
            'category': 'milestone'
        }

        self.costs.append(cost_entry)
        self._save_costs()

    def get_cost_breakdown(self, days: Optional[int] = None) -> CostBreakdown:
        """
        Get detailed cost breakdown

        Args:
            days: Only include costs from last N days (None = all time)

        Returns:
            CostBreakdown object
        """
        breakdown = CostBreakdown()

        # Filter by time if specified
        cutoff = time.time() - (days * 86400) if days else 0
        relevant_costs = [c for c in self.costs if c['timestamp'] >= cutoff]

        # Aggregate costs
        for entry in relevant_costs:
            cost = entry['cost']

            if entry['type'] == 'cloud':
                breakdown.cloud_total += cost

                operation = entry.get('operation', 'compute')
                if operation == 'compute':
                    breakdown.cloud_compute += cost
                elif operation == 'storage':
                    breakdown.cloud_storage += cost
                elif operation == 'network':
                    breakdown.cloud_network += cost

            elif entry['type'] == 'llm':
                breakdown.llm_total += cost

                provider = entry.get('provider', '').lower()
                if 'groq' in provider:
                    breakdown.llm_groq += cost
                elif 'deepseek' in provider:
                    breakdown.llm_deepseek += cost
                elif 'openrouter' in provider:
                    breakdown.llm_openrouter += cost
                elif 'anthropic' in provider or 'claude' in provider:
                    breakdown.llm_anthropic += cost
                elif 'openai' in provider:
                    breakdown.llm_openai += cost

            elif entry['type'] == 'book_completed':
                breakdown.books_generated += 1

        # Calculate totals
        breakdown.total_cost = breakdown.cloud_total + breakdown.llm_total

        if breakdown.books_generated > 0:
            breakdown.cost_per_book = breakdown.total_cost / breakdown.books_generated

        return breakdown

    def get_burn_rate(self) -> Dict:
        """
        Calculate budget burn rate

        Returns:
            Dict with burn rate metrics
        """
        breakdown = self.get_cost_breakdown()

        # Calculate daily burn rate (last 7 days)
        breakdown_7d = self.get_cost_breakdown(days=7)
        daily_burn = breakdown_7d.total_cost / 7

        # Project days remaining
        remaining = self.max_budget - breakdown.total_cost
        days_remaining = remaining / daily_burn if daily_burn > 0 else float('inf')

        return {
            'total_spent': breakdown.total_cost,
            'remaining_budget': remaining,
            'utilization_pct': (breakdown.total_cost / self.max_budget) * 100,
            'daily_burn_rate': daily_burn,
            'days_remaining': days_remaining,
            'books_generated': breakdown.books_generated,
            'cost_per_book': breakdown.cost_per_book
        }

    def print_cost_report(self, detailed: bool = True):
        """
        Print comprehensive cost report

        Args:
            detailed: Include detailed breakdown by provider
        """
        breakdown = self.get_cost_breakdown()
        burn_rate = self.get_burn_rate()

        print("\n" + "="*70)
        print("COST TRACKING REPORT")
        print("="*70)

        # Budget overview
        print(f"\nBudget:")
        print(f"  Total Budget:    ${self.max_budget:.2f}")
        print(f"  Spent:           ${burn_rate['total_spent']:.2f} "
              f"({burn_rate['utilization_pct']:.1f}%)")
        print(f"  Remaining:       ${burn_rate['remaining_budget']:.2f}")

        # Burn rate
        print(f"\nBurn Rate:")
        print(f"  Daily:           ${burn_rate['daily_burn_rate']:.2f}/day")
        if burn_rate['days_remaining'] != float('inf'):
            print(f"  Days Remaining:  {burn_rate['days_remaining']:.1f} days")
        else:
            print(f"  Days Remaining:  ∞ (no recent spending)")

        # Books generated
        print(f"\nProduction:")
        print(f"  Books Generated: {breakdown.books_generated}")
        if breakdown.books_generated > 0:
            print(f"  Cost per Book:   ${breakdown.cost_per_book:.2f}")
            print(f"  Books Possible:  ~{int(burn_rate['remaining_budget'] / breakdown.cost_per_book)} "
                  f"with remaining budget")

        # Cost breakdown
        print(f"\nCost Breakdown:")
        print(f"  Cloud (OCI):     ${breakdown.cloud_total:.2f} "
              f"({breakdown.cloud_total/breakdown.total_cost*100 if breakdown.total_cost > 0 else 0:.1f}%)")

        if detailed and breakdown.cloud_total > 0:
            print(f"    Compute:       ${breakdown.cloud_compute:.2f}")
            print(f"    Storage:       ${breakdown.cloud_storage:.2f}")
            print(f"    Network:       ${breakdown.cloud_network:.2f}")

        print(f"  LLM APIs:        ${breakdown.llm_total:.2f} "
              f"({breakdown.llm_total/breakdown.total_cost*100 if breakdown.total_cost > 0 else 0:.1f}%)")

        if detailed and breakdown.llm_total > 0:
            if breakdown.llm_groq > 0:
                print(f"    Groq:          ${breakdown.llm_groq:.2f}")
            if breakdown.llm_deepseek > 0:
                print(f"    DeepSeek:      ${breakdown.llm_deepseek:.2f}")
            if breakdown.llm_openrouter > 0:
                print(f"    OpenRouter:    ${breakdown.llm_openrouter:.2f}")
            if breakdown.llm_anthropic > 0:
                print(f"    Anthropic:     ${breakdown.llm_anthropic:.2f}")
            if breakdown.llm_openai > 0:
                print(f"    OpenAI:        ${breakdown.llm_openai:.2f}")

        print(f"\n  Total:           ${breakdown.total_cost:.2f}")

        # Recommendations
        print(f"\nRecommendations:")
        if burn_rate['utilization_pct'] < 10:
            print("  ✓ Excellent: Low spending, lots of runway")
        elif burn_rate['utilization_pct'] < 50:
            print("  ✓ Good: Healthy budget utilization")
        elif burn_rate['utilization_pct'] < 80:
            print("  ⚠ Warning: Over 50% budget used")
        else:
            print("  ⚠ Critical: Nearing budget limit")

        # Provider recommendations
        if breakdown.llm_total > 0:
            cheapest = min([
                ('Groq', breakdown.llm_groq),
                ('DeepSeek', breakdown.llm_deepseek),
                ('OpenRouter', breakdown.llm_openrouter)
            ], key=lambda x: x[1] if x[1] > 0 else float('inf'))

            if cheapest[1] > 0:
                print(f"  💡 Most cost-effective provider: {cheapest[0]}")

        print("="*70 + "\n")

    def export_costs_csv(self, output_file: Path):
        """Export costs to CSV for analysis"""
        import csv

        with open(output_file, 'w', newline='') as f:
            if not self.costs:
                return

            # Get all keys
            keys = set()
            for entry in self.costs:
                keys.update(entry.keys())

            writer = csv.DictWriter(f, fieldnames=sorted(keys))
            writer.writeheader()

            for entry in self.costs:
                writer.writerow(entry)

        print(f"[CostTracker] Exported {len(self.costs)} cost entries to {output_file}")


def demo_cost_tracker():
    """Demonstrate cost tracker"""
    print("="*70)
    print("OCI COST TRACKER DEMO")
    print("="*70)

    tracker = OCICostTracker(max_budget=300.0)

    # Simulate some costs
    print("\nSimulating book generation costs...")

    # Cloud instance running for 2 hours
    tracker.record_cloud_cost(
        instance_id="ocid1.instance.oc1...",
        instance_shape="VM.Standard.A1.Flex",
        uptime_hours=2.0,
        cost=0.0,  # Free tier
        operation="compute"
    )

    # LLM API costs for book generation
    tracker.record_llm_cost(
        provider="groq",
        model="llama-3.1-70b",
        tokens=150000,
        cost=0.05,
        book_name="fantasy-epic-1"
    )

    tracker.record_llm_cost(
        provider="deepseek",
        model="deepseek-chat",
        tokens=200000,
        cost=0.03,
        book_name="scifi-adventure-1"
    )

    # Complete books
    tracker.record_book_completion("fantasy-epic-1", 0.05)
    tracker.record_book_completion("scifi-adventure-1", 0.03)

    # Print report
    tracker.print_cost_report(detailed=True)

    # Export
    csv_file = Path("workspace/cost_export.csv")
    tracker.export_costs_csv(csv_file)

    print("✓ Cost tracking demo complete")


if __name__ == "__main__":
    demo_cost_tracker()
