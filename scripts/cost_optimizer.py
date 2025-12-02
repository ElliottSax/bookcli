#!/usr/bin/env python3
"""
Cost Optimization Engine for Task-Based Provider Selection
Phase 4, Priority 1.4: Intelligent provider selection based on task complexity

Optimizes costs by using appropriate providers for different tasks:
- Premium providers for complex generation
- Cheap providers for simple enhancements
- Local models for analysis (when possible)
"""

from enum import Enum
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple, Any
import json
from pathlib import Path
import time

from llm_providers import Provider, ProviderConfig


class TaskType(Enum):
    """Types of tasks with different quality requirements"""
    # High quality required
    CHAPTER_GENERATION = "chapter_generation"
    CREATIVE_WRITING = "creative_writing"
    COMPLEX_REASONING = "complex_reasoning"

    # Medium quality required
    ENHANCEMENT = "enhancement"
    REWRITING = "rewriting"
    EXPANSION = "expansion"

    # Low quality acceptable
    ANALYSIS = "analysis"
    SUMMARIZATION = "summarization"
    EXTRACTION = "extraction"
    FORMATTING = "formatting"

    # Can use local models
    WORD_COUNT = "word_count"
    QUALITY_CHECK = "quality_check"
    SYNTAX_CHECK = "syntax_check"


@dataclass
class TaskProfile:
    """Profile for a specific task type"""
    task_type: TaskType
    min_quality_score: float  # Minimum acceptable quality (0-10)
    max_acceptable_cost: float  # Maximum cost per 1M tokens
    preferred_providers: List[Provider]
    fallback_providers: List[Provider]
    can_use_local: bool = False
    typical_tokens: int = 4000  # Typical token usage

    def get_cost_for_provider(self, provider: Provider, tokens: int = None) -> float:
        """Calculate estimated cost for this task with given provider"""
        tokens = tokens or self.typical_tokens
        config = ProviderConfig.get_config(provider)

        # Assume 20% input, 80% output for generation tasks
        if self.task_type in [TaskType.CHAPTER_GENERATION, TaskType.CREATIVE_WRITING]:
            input_tokens = int(tokens * 0.2)
            output_tokens = int(tokens * 0.8)
        # Assume 80% input, 20% output for analysis tasks
        elif self.task_type in [TaskType.ANALYSIS, TaskType.SUMMARIZATION]:
            input_tokens = int(tokens * 0.8)
            output_tokens = int(tokens * 0.2)
        # Default 50/50
        else:
            input_tokens = output_tokens = tokens // 2

        cost = (
            (input_tokens / 1_000_000) * config['input_cost_per_1m'] +
            (output_tokens / 1_000_000) * config['output_cost_per_1m']
        )
        return cost


class CostOptimizer:
    """
    Optimizes provider selection based on task requirements and costs

    Key strategies:
    1. Use cheapest provider that meets quality requirements
    2. Reserve premium providers for high-quality tasks
    3. Use local models when possible (zero cost)
    4. Track actual costs vs estimates for optimization
    """

    def __init__(self, available_providers: List[str] = None):
        """
        Initialize cost optimizer

        Args:
            available_providers: List of available provider names
        """
        # Default providers in order of preference (quality)
        self.all_providers = [
            Provider.CLAUDE,      # Highest quality, most expensive
            Provider.OPENAI,      # High quality, expensive
            Provider.DEEPSEEK,    # Good quality, cheap
            Provider.OPENROUTER,  # Good quality, cheap
            Provider.QWEN,        # Decent quality, cheap
            Provider.GROQ,        # Fast, very cheap
            Provider.TOGETHER,    # Decent, cheap
            Provider.HUGGINGFACE  # Variable quality, free tier
        ]

        # Filter to available providers
        if available_providers:
            self.available_providers = [
                p for p in self.all_providers
                if p.value in [ap.lower() for ap in available_providers]
            ]
        else:
            self.available_providers = self._detect_available_providers()

        # Initialize task profiles
        self.task_profiles = self._create_task_profiles()

        # Cost tracking
        self.cost_history = {}
        self.provider_performance = {}

    def _detect_available_providers(self) -> List[Provider]:
        """Detect which providers have API keys configured"""
        import os
        available = []

        for provider in self.all_providers:
            try:
                config = ProviderConfig.get_config(provider)
                if os.environ.get(config['api_key_env']):
                    available.append(provider)
                    print(f"[CostOptimizer] ✓ Provider available: {config['name']}")
            except:
                pass

        return available

    def _create_task_profiles(self) -> Dict[TaskType, TaskProfile]:
        """Create task profiles with provider preferences"""
        profiles = {}

        # High-quality generation tasks
        profiles[TaskType.CHAPTER_GENERATION] = TaskProfile(
            task_type=TaskType.CHAPTER_GENERATION,
            min_quality_score=8.0,
            max_acceptable_cost=15.0,  # $15 per 1M tokens max
            preferred_providers=[Provider.CLAUDE, Provider.OPENAI],
            fallback_providers=[Provider.DEEPSEEK, Provider.OPENROUTER],
            typical_tokens=5000
        )

        profiles[TaskType.CREATIVE_WRITING] = TaskProfile(
            task_type=TaskType.CREATIVE_WRITING,
            min_quality_score=7.5,
            max_acceptable_cost=10.0,
            preferred_providers=[Provider.CLAUDE, Provider.OPENAI],
            fallback_providers=[Provider.DEEPSEEK, Provider.QWEN],
            typical_tokens=3000
        )

        profiles[TaskType.COMPLEX_REASONING] = TaskProfile(
            task_type=TaskType.COMPLEX_REASONING,
            min_quality_score=8.5,
            max_acceptable_cost=20.0,
            preferred_providers=[Provider.CLAUDE, Provider.OPENAI],
            fallback_providers=[Provider.DEEPSEEK],
            typical_tokens=2000
        )

        # Medium-quality enhancement tasks
        profiles[TaskType.ENHANCEMENT] = TaskProfile(
            task_type=TaskType.ENHANCEMENT,
            min_quality_score=6.5,
            max_acceptable_cost=1.0,
            preferred_providers=[Provider.GROQ, Provider.DEEPSEEK],
            fallback_providers=[Provider.QWEN, Provider.TOGETHER],
            typical_tokens=1500
        )

        profiles[TaskType.REWRITING] = TaskProfile(
            task_type=TaskType.REWRITING,
            min_quality_score=7.0,
            max_acceptable_cost=2.0,
            preferred_providers=[Provider.DEEPSEEK, Provider.OPENROUTER],
            fallback_providers=[Provider.GROQ, Provider.QWEN],
            typical_tokens=2000
        )

        profiles[TaskType.EXPANSION] = TaskProfile(
            task_type=TaskType.EXPANSION,
            min_quality_score=6.0,
            max_acceptable_cost=0.5,
            preferred_providers=[Provider.GROQ, Provider.TOGETHER],
            fallback_providers=[Provider.HUGGINGFACE],
            typical_tokens=1000
        )

        # Low-quality acceptable tasks
        profiles[TaskType.ANALYSIS] = TaskProfile(
            task_type=TaskType.ANALYSIS,
            min_quality_score=5.0,
            max_acceptable_cost=0.2,
            preferred_providers=[Provider.GROQ, Provider.HUGGINGFACE],
            fallback_providers=[Provider.TOGETHER],
            can_use_local=True,
            typical_tokens=1000
        )

        profiles[TaskType.SUMMARIZATION] = TaskProfile(
            task_type=TaskType.SUMMARIZATION,
            min_quality_score=5.5,
            max_acceptable_cost=0.3,
            preferred_providers=[Provider.GROQ, Provider.TOGETHER],
            fallback_providers=[Provider.HUGGINGFACE],
            typical_tokens=800
        )

        profiles[TaskType.EXTRACTION] = TaskProfile(
            task_type=TaskType.EXTRACTION,
            min_quality_score=4.0,
            max_acceptable_cost=0.1,
            preferred_providers=[Provider.GROQ, Provider.HUGGINGFACE],
            fallback_providers=[Provider.TOGETHER],
            can_use_local=True,
            typical_tokens=500
        )

        profiles[TaskType.FORMATTING] = TaskProfile(
            task_type=TaskType.FORMATTING,
            min_quality_score=3.0,
            max_acceptable_cost=0.05,
            preferred_providers=[Provider.GROQ, Provider.HUGGINGFACE],
            fallback_providers=[],
            can_use_local=True,
            typical_tokens=300
        )

        # Local model tasks (zero cost)
        profiles[TaskType.WORD_COUNT] = TaskProfile(
            task_type=TaskType.WORD_COUNT,
            min_quality_score=1.0,
            max_acceptable_cost=0.0,
            preferred_providers=[],
            fallback_providers=[Provider.GROQ],
            can_use_local=True,
            typical_tokens=100
        )

        profiles[TaskType.QUALITY_CHECK] = TaskProfile(
            task_type=TaskType.QUALITY_CHECK,
            min_quality_score=2.0,
            max_acceptable_cost=0.01,
            preferred_providers=[],
            fallback_providers=[Provider.GROQ],
            can_use_local=True,
            typical_tokens=200
        )

        profiles[TaskType.SYNTAX_CHECK] = TaskProfile(
            task_type=TaskType.SYNTAX_CHECK,
            min_quality_score=1.0,
            max_acceptable_cost=0.0,
            preferred_providers=[],
            fallback_providers=[Provider.GROQ],
            can_use_local=True,
            typical_tokens=100
        )

        return profiles

    def select_provider(self, task_type: TaskType,
                        estimated_tokens: Optional[int] = None,
                        quality_override: Optional[float] = None) -> Tuple[Provider, float]:
        """
        Select optimal provider for a task

        Args:
            task_type: Type of task to perform
            estimated_tokens: Estimated token usage (uses typical if not provided)
            quality_override: Override minimum quality requirement

        Returns:
            Tuple of (selected_provider, estimated_cost)
        """
        profile = self.task_profiles.get(task_type)
        if not profile:
            # Default to cheapest available
            return self._get_cheapest_provider(), 0.0

        tokens = estimated_tokens or profile.typical_tokens
        min_quality = quality_override or profile.min_quality_score

        # Check if local model is acceptable
        if profile.can_use_local and min_quality <= 3.0:
            return None, 0.0  # Use local model

        # Find cheapest provider that meets requirements
        candidates = []

        # Check preferred providers first
        for provider in profile.preferred_providers:
            if provider in self.available_providers:
                cost = profile.get_cost_for_provider(provider, tokens)
                if cost <= profile.max_acceptable_cost:
                    candidates.append((provider, cost))

        # Check fallback providers if needed
        if not candidates:
            for provider in profile.fallback_providers:
                if provider in self.available_providers:
                    cost = profile.get_cost_for_provider(provider, tokens)
                    if cost <= profile.max_acceptable_cost * 1.5:  # Allow 50% over for fallbacks
                        candidates.append((provider, cost))

        # If still no candidates, use any available provider
        if not candidates:
            for provider in self.available_providers:
                cost = profile.get_cost_for_provider(provider, tokens)
                candidates.append((provider, cost))

        if not candidates:
            raise ValueError(f"No providers available for task {task_type.value}")

        # Sort by cost and return cheapest
        candidates.sort(key=lambda x: x[1])
        selected_provider, estimated_cost = candidates[0]

        # Track selection
        self._track_selection(task_type, selected_provider, estimated_cost)

        return selected_provider, estimated_cost

    def _get_cheapest_provider(self) -> Provider:
        """Get the absolute cheapest available provider"""
        if not self.available_providers:
            raise ValueError("No providers available")

        costs = []
        for provider in self.available_providers:
            config = ProviderConfig.get_config(provider)
            avg_cost = (config['input_cost_per_1m'] + config['output_cost_per_1m']) / 2
            costs.append((provider, avg_cost))

        costs.sort(key=lambda x: x[1])
        return costs[0][0]

    def _track_selection(self, task_type: TaskType, provider: Provider, cost: float):
        """Track provider selection for optimization"""
        key = f"{task_type.value}_{provider.value}"
        if key not in self.cost_history:
            self.cost_history[key] = []
        self.cost_history[key].append({
            'timestamp': time.time(),
            'estimated_cost': cost
        })

    def optimize_for_book(self, total_chapters: int = 20,
                          words_per_chapter: int = 3500) -> Dict:
        """
        Calculate optimal provider strategy for entire book

        Returns cost breakdown and recommendations
        """
        # Estimate tokens (roughly 1.3 tokens per word)
        tokens_per_chapter = int(words_per_chapter * 1.3)

        recommendations = {
            'total_estimated_cost': 0.0,
            'cost_breakdown': {},
            'provider_assignments': {},
            'potential_savings': 0.0
        }

        # Calculate costs for each task type
        tasks = [
            (TaskType.CHAPTER_GENERATION, total_chapters, tokens_per_chapter),
            (TaskType.ANALYSIS, total_chapters * 2, 500),  # Analysis twice per chapter
            (TaskType.ENHANCEMENT, total_chapters * 0.3, 1000),  # 30% need enhancement
            (TaskType.QUALITY_CHECK, total_chapters * 3, 200),  # Multiple quality checks
        ]

        for task_type, count, tokens in tasks:
            provider, cost_per = self.select_provider(task_type, tokens)
            total_cost = cost_per * count

            recommendations['cost_breakdown'][task_type.value] = {
                'provider': provider.value if provider else 'local',
                'count': count,
                'cost_per': cost_per,
                'total_cost': total_cost
            }
            recommendations['provider_assignments'][task_type.value] = provider.value if provider else 'local'
            recommendations['total_estimated_cost'] += total_cost

        # Calculate potential savings vs using premium for everything
        premium_cost = self._calculate_all_premium_cost(total_chapters, tokens_per_chapter)
        recommendations['potential_savings'] = premium_cost - recommendations['total_estimated_cost']
        recommendations['savings_percentage'] = (
            (recommendations['potential_savings'] / premium_cost * 100)
            if premium_cost > 0 else 0
        )

        return recommendations

    def _calculate_all_premium_cost(self, chapters: int, tokens_per_chapter: int) -> float:
        """Calculate cost if using premium provider for everything"""
        # Assume Claude for everything
        if Provider.CLAUDE in self.available_providers:
            config = ProviderConfig.get_config(Provider.CLAUDE)
        elif Provider.OPENAI in self.available_providers:
            config = ProviderConfig.get_config(Provider.OPENAI)
        else:
            return 0.0

        # Estimate total tokens
        total_tokens = chapters * tokens_per_chapter * 2  # Factor in all operations
        cost = (total_tokens / 1_000_000) * ((config['input_cost_per_1m'] + config['output_cost_per_1m']) / 2)
        return cost

    def get_cost_comparison(self) -> str:
        """Generate cost comparison report"""
        report = ["", "="*60, "PROVIDER COST COMPARISON", "="*60, ""]

        # Create cost table
        report.append("Provider               | Input $/1M | Output $/1M | Avg $/1M | Quality")
        report.append("-" * 70)

        for provider in self.all_providers:
            try:
                config = ProviderConfig.get_config(provider)
                avg_cost = (config['input_cost_per_1m'] + config['output_cost_per_1m']) / 2
                available = "✓" if provider in self.available_providers else "✗"

                # Assign quality tier
                if provider in [Provider.CLAUDE, Provider.OPENAI]:
                    quality = "★★★★★"
                elif provider in [Provider.DEEPSEEK, Provider.OPENROUTER]:
                    quality = "★★★★☆"
                elif provider in [Provider.QWEN, Provider.TOGETHER]:
                    quality = "★★★☆☆"
                elif provider == Provider.GROQ:
                    quality = "★★★☆☆"
                else:
                    quality = "★★☆☆☆"

                report.append(
                    f"{available} {config['name']:<18} | ${config['input_cost_per_1m']:>8.2f} | "
                    f"${config['output_cost_per_1m']:>9.2f} | ${avg_cost:>7.2f} | {quality}"
                )
            except:
                pass

        report.append("")
        report.append("TASK-BASED RECOMMENDATIONS")
        report.append("-" * 70)

        for task_type, profile in self.task_profiles.items():
            try:
                provider, cost = self.select_provider(task_type)
                provider_name = ProviderConfig.get_config(provider)['name'] if provider else "Local Model"
                report.append(f"{task_type.value:<25} → {provider_name:<20} (${cost:.4f}/task)")
            except:
                report.append(f"{task_type.value:<25} → No provider available")

        report.append("")
        report.append("="*60)
        return "\n".join(report)


class OptimizedOrchestrator:
    """
    Orchestrator with cost optimization integrated

    Uses CostOptimizer to select appropriate providers for each task
    """

    def __init__(self, base_orchestrator, cost_optimizer: CostOptimizer):
        """
        Wrap an orchestrator with cost optimization

        Args:
            base_orchestrator: Base orchestrator to wrap
            cost_optimizer: CostOptimizer instance
        """
        self.orchestrator = base_orchestrator
        self.optimizer = cost_optimizer
        self.task_costs = {}

    def generate_chapter_optimized(self, chapter_num: int) -> Tuple[bool, float]:
        """
        Generate chapter with optimized provider selection

        Returns:
            Tuple of (success, total_cost)
        """
        total_cost = 0.0

        # Step 1: Generation (high quality needed)
        gen_provider, gen_cost = self.optimizer.select_provider(
            TaskType.CHAPTER_GENERATION,
            estimated_tokens=5000
        )
        print(f"[Optimized] Generation: {gen_provider.value if gen_provider else 'local'} (${gen_cost:.4f})")
        total_cost += gen_cost

        # Step 2: Analysis (can use cheaper provider)
        analysis_provider, analysis_cost = self.optimizer.select_provider(
            TaskType.ANALYSIS,
            estimated_tokens=500
        )
        print(f"[Optimized] Analysis: {analysis_provider.value if analysis_provider else 'local'} (${analysis_cost:.4f})")
        total_cost += analysis_cost

        # Step 3: Enhancement if needed (cheap provider)
        if True:  # Would check if enhancement needed
            enhance_provider, enhance_cost = self.optimizer.select_provider(
                TaskType.ENHANCEMENT,
                estimated_tokens=1000
            )
            print(f"[Optimized] Enhancement: {enhance_provider.value if enhance_provider else 'local'} (${enhance_cost:.4f})")
            total_cost += enhance_cost

        # Step 4: Quality check (local or cheapest)
        check_provider, check_cost = self.optimizer.select_provider(
            TaskType.QUALITY_CHECK,
            estimated_tokens=200
        )
        print(f"[Optimized] Quality Check: {check_provider.value if check_provider else 'local'} (${check_cost:.4f})")
        total_cost += check_cost

        self.task_costs[chapter_num] = total_cost
        print(f"[Optimized] Total chapter cost: ${total_cost:.4f}")

        # Would actually generate here with selected providers
        return True, total_cost


def demo_cost_optimizer():
    """Demonstrate cost optimization functionality"""
    print("="*60)
    print("COST OPTIMIZER DEMO")
    print("="*60)

    # Create optimizer
    optimizer = CostOptimizer()

    # Show cost comparison
    print(optimizer.get_cost_comparison())

    # Test task-based selection
    print("\n" + "="*60)
    print("TASK-BASED PROVIDER SELECTION")
    print("="*60)

    tasks = [
        (TaskType.CHAPTER_GENERATION, 5000),
        (TaskType.ENHANCEMENT, 1000),
        (TaskType.ANALYSIS, 500),
        (TaskType.QUALITY_CHECK, 200),
    ]

    total_cost = 0.0
    for task_type, tokens in tasks:
        provider, cost = optimizer.select_provider(task_type, tokens)
        provider_name = ProviderConfig.get_config(provider)['name'] if provider else "Local Model"
        print(f"{task_type.value:<25} → {provider_name:<20} ${cost:.4f}")
        total_cost += cost

    print(f"\nTotal estimated cost: ${total_cost:.4f}")

    # Book cost optimization
    print("\n" + "="*60)
    print("FULL BOOK COST OPTIMIZATION")
    print("="*60)

    book_strategy = optimizer.optimize_for_book(
        total_chapters=20,
        words_per_chapter=3500
    )

    print(f"Total estimated cost: ${book_strategy['total_estimated_cost']:.2f}")
    print(f"Potential savings: ${book_strategy['potential_savings']:.2f} ({book_strategy['savings_percentage']:.1f}%)")
    print("\nCost breakdown:")
    for task, details in book_strategy['cost_breakdown'].items():
        print(f"  {task}: ${details['total_cost']:.2f} ({details['count']} × ${details['cost_per']:.4f})")

    print("\nProvider assignments:")
    for task, provider in book_strategy['provider_assignments'].items():
        print(f"  {task}: {provider}")


if __name__ == "__main__":
    import os
    # Set example API keys for demo
    os.environ.setdefault('GROQ_API_KEY', 'demo-key')
    os.environ.setdefault('DEEPSEEK_API_KEY', 'demo-key')

    demo_cost_optimizer()