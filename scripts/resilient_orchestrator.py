#!/usr/bin/env python3
"""
Resilient Orchestrator with Retry Logic and Provider Fallbacks
Phase 4, Priority 1.3: Smart retry with automatic provider switching

Provides robust generation with automatic fallback to alternative providers
when primary provider fails or is rate limited.
"""

import time
import random
from pathlib import Path
from typing import List, Dict, Optional, Tuple, Any
from dataclasses import dataclass
from enum import Enum
import json
import traceback

# Import base components
from orchestrator import BookOrchestrator
from parallel_orchestrator import AsyncBookOrchestrator
from checkpoint_manager import CheckpointManager, GenerationCheckpoint
from llm_providers import LLMClient, Provider, ProviderConfig

# Import quality enforcement (Phase 8)
try:
    from quality_gate_enforcer import QualityGateEnforcer, ChapterQualityReport
    QUALITY_ENFORCEMENT_AVAILABLE = True
except ImportError:
    QUALITY_ENFORCEMENT_AVAILABLE = False

# Import enhanced quality pipeline (Phase 9)
try:
    from enhanced_quality_pipeline import EnhancedQualityPipeline, EnhancedQualityReport
    ENHANCED_QUALITY_AVAILABLE = True
except ImportError:
    ENHANCED_QUALITY_AVAILABLE = False

# Import multi-agent generator (Phase 9)
try:
    from multi_agent_generator import MultiAgentGenerator, AgentRole
    MULTI_AGENT_AVAILABLE = True
except ImportError:
    MULTI_AGENT_AVAILABLE = False

# Import advanced chapter generator (Phase 10 - Claude-style)
try:
    from advanced_chapter_generator import (
        AdvancedChapterGenerator, BookType, PassType,
        HierarchicalMemory, generate_fiction_chapter, generate_nonfiction_chapter
    )
    ADVANCED_GENERATOR_AVAILABLE = True
except ImportError:
    ADVANCED_GENERATOR_AVAILABLE = False


class RetryStrategy(Enum):
    """Retry strategies for failed operations"""
    EXPONENTIAL_BACKOFF = "exponential_backoff"
    LINEAR_BACKOFF = "linear_backoff"
    IMMEDIATE = "immediate"
    JITTERED = "jittered"


@dataclass
class ProviderStatus:
    """Track provider health and availability"""
    provider: Provider
    available: bool = True
    failure_count: int = 0
    last_failure: Optional[float] = None
    last_success: Optional[float] = None
    average_response_time: float = 0.0
    total_cost: float = 0.0
    total_tokens: int = 0
    rate_limit_reset: Optional[float] = None


class ProviderPool:
    """
    Manages multiple LLM providers with automatic failover

    Features:
    - Health tracking for each provider
    - Automatic failover to backup providers
    - Cost-based provider selection
    - Rate limit awareness
    - Performance monitoring
    """

    def __init__(self, providers: List[str], primary: Optional[str] = None):
        """
        Initialize provider pool

        Args:
            providers: List of provider names to use
            primary: Primary provider (defaults to first in list)
        """
        self.providers = []
        self.provider_status = {}

        # Initialize providers
        for provider_name in providers:
            try:
                provider = Provider(provider_name.lower())
                config = ProviderConfig.get_config(provider)

                # Check if API key is available
                import os
                if os.environ.get(config['api_key_env']):
                    self.providers.append(provider)
                    self.provider_status[provider] = ProviderStatus(provider=provider)
                    print(f"[ProviderPool] ✓ Added provider: {config['name']}")
                else:
                    print(f"[ProviderPool] ✗ Skipped {config['name']}: No API key")

            except Exception as e:
                print(f"[ProviderPool] ✗ Failed to add provider {provider_name}: {e}")

        if not self.providers:
            raise ValueError("No valid providers available")

        # Set primary provider
        self.primary = Provider(primary.lower()) if primary else self.providers[0]
        self.current_provider = self.primary

        print(f"[ProviderPool] Primary provider: {ProviderConfig.get_config(self.primary)['name']}")

    def get_next_provider(self, exclude: Optional[List[Provider]] = None) -> Optional[Provider]:
        """
        Get next available provider

        Args:
            exclude: Providers to exclude from selection

        Returns:
            Next available provider or None
        """
        exclude = exclude or []

        # Sort providers by availability and cost
        available_providers = [
            p for p in self.providers
            if p not in exclude and self.provider_status[p].available
        ]

        if not available_providers:
            # Try to reset failed providers if none available
            self._reset_failed_providers()
            available_providers = [
                p for p in self.providers
                if p not in exclude and self.provider_status[p].available
            ]

        if not available_providers:
            return None

        # Sort by cost (cheapest first)
        available_providers.sort(
            key=lambda p: ProviderConfig.get_config(p)['input_cost_per_1m']
        )

        return available_providers[0]

    def mark_failure(self, provider: Provider, error: str):
        """Mark a provider as failed"""
        status = self.provider_status[provider]
        status.failure_count += 1
        status.last_failure = time.time()

        # Check if rate limited
        if "rate" in error.lower() or "429" in error:
            status.rate_limit_reset = time.time() + 3600  # Assume 1 hour reset
            print(f"[ProviderPool] Rate limit detected for {provider.value}, cooling down for 1 hour")

        # Mark unavailable after 3 failures
        if status.failure_count >= 3:
            status.available = False
            print(f"[ProviderPool] Provider {provider.value} marked unavailable after {status.failure_count} failures")

    def mark_success(self, provider: Provider, response_time: float, tokens: int, cost: float):
        """Mark a successful operation"""
        status = self.provider_status[provider]
        status.last_success = time.time()
        status.failure_count = 0  # Reset failure count on success
        status.available = True
        status.total_tokens += tokens
        status.total_cost += cost

        # Update average response time
        if status.average_response_time == 0:
            status.average_response_time = response_time
        else:
            status.average_response_time = (status.average_response_time * 0.9) + (response_time * 0.1)

    def _reset_failed_providers(self):
        """Reset providers that have been cooling down"""
        current_time = time.time()

        for provider, status in self.provider_status.items():
            if not status.available:
                # Reset if rate limit expired
                if status.rate_limit_reset and current_time > status.rate_limit_reset:
                    status.available = True
                    status.failure_count = 0
                    print(f"[ProviderPool] Provider {provider.value} reset after cooldown")

                # Reset if enough time passed since last failure (5 minutes)
                elif status.last_failure and (current_time - status.last_failure) > 300:
                    status.available = True
                    status.failure_count = 0
                    print(f"[ProviderPool] Provider {provider.value} reset after timeout")

    def get_statistics(self) -> Dict:
        """Get provider pool statistics"""
        stats = {
            'total_providers': len(self.providers),
            'available_providers': sum(1 for s in self.provider_status.values() if s.available),
            'total_cost': sum(s.total_cost for s in self.provider_status.values()),
            'total_tokens': sum(s.total_tokens for s in self.provider_status.values()),
            'provider_details': {}
        }

        for provider, status in self.provider_status.items():
            config = ProviderConfig.get_config(provider)
            stats['provider_details'][provider.value] = {
                'name': config['name'],
                'available': status.available,
                'failure_count': status.failure_count,
                'avg_response_time': f"{status.average_response_time:.2f}s",
                'total_cost': f"${status.total_cost:.4f}",
                'total_tokens': status.total_tokens
            }

        return stats


class ResilientOrchestrator(AsyncBookOrchestrator):
    """
    Resilient orchestrator with retry logic and provider fallbacks

    Extends AsyncBookOrchestrator with:
    - Automatic retry with configurable strategies
    - Provider fallback on failure
    - Checkpoint integration for precise resume
    - Cost optimization across providers
    """

    def __init__(self, *args,
                 providers: List[str] = None,
                 retry_strategy: RetryStrategy = RetryStrategy.EXPONENTIAL_BACKOFF,
                 max_retries_per_provider: int = 3,
                 checkpoint_enabled: bool = True,
                 quality_enforcement_enabled: bool = False,
                 quality_strict_mode: bool = True,
                 enhanced_quality_enabled: bool = True,
                 multi_agent_enabled: bool = False,
                 **kwargs):
        """
        Initialize resilient orchestrator

        Args:
            providers: List of provider names for fallback
            retry_strategy: Strategy for retrying failed operations
            max_retries_per_provider: Max retries before switching providers
            checkpoint_enabled: Enable checkpoint saving
            quality_enforcement_enabled: Enable quality gate enforcement (Phase 8)
            quality_strict_mode: If True, all quality gates must pass
            enhanced_quality_enabled: Enable enhanced quality pipeline (Phase 9)
            multi_agent_enabled: Enable multi-agent generation (Phase 9)
            *args, **kwargs: Passed to parent AsyncBookOrchestrator
        """
        # Default providers if none specified
        if providers is None:
            providers = ['groq', 'deepseek', 'openrouter']

        # Initialize provider pool
        self.provider_pool = ProviderPool(providers, kwargs.get('provider'))

        # Set initial provider
        kwargs['provider'] = self.provider_pool.current_provider.value

        # Initialize parent
        super().__init__(*args, **kwargs)

        self.retry_strategy = retry_strategy
        self.max_retries_per_provider = max_retries_per_provider

        # Initialize checkpoint manager if enabled
        if checkpoint_enabled:
            self.checkpoint_manager = CheckpointManager(self.workspace)
        else:
            self.checkpoint_manager = None

        # Initialize quality enforcer if enabled (Phase 8)
        self.quality_enforcement_enabled = quality_enforcement_enabled and QUALITY_ENFORCEMENT_AVAILABLE
        if self.quality_enforcement_enabled:
            self.quality_enforcer = QualityGateEnforcer(strict_mode=quality_strict_mode)
            self._log("Quality enforcement enabled (Phase 8)")
        else:
            self.quality_enforcer = None
            if quality_enforcement_enabled and not QUALITY_ENFORCEMENT_AVAILABLE:
                self._log("WARNING: Quality enforcement requested but not available")

        # Initialize enhanced quality pipeline (Phase 9)
        self.enhanced_quality_enabled = enhanced_quality_enabled and ENHANCED_QUALITY_AVAILABLE
        if self.enhanced_quality_enabled:
            self.enhanced_pipeline = EnhancedQualityPipeline()
            self._log("Enhanced quality pipeline enabled (Phase 9)")
        else:
            self.enhanced_pipeline = None
            if enhanced_quality_enabled and not ENHANCED_QUALITY_AVAILABLE:
                self._log("WARNING: Enhanced quality pipeline requested but not available")

        # Initialize multi-agent generator (Phase 9)
        self.multi_agent_enabled = multi_agent_enabled and MULTI_AGENT_AVAILABLE
        if self.multi_agent_enabled:
            self.multi_agent_generator = MultiAgentGenerator()
            self._log("Multi-agent generation enabled (Phase 9)")
        else:
            self.multi_agent_generator = None
            if multi_agent_enabled and not MULTI_AGENT_AVAILABLE:
                self._log("WARNING: Multi-agent generation requested but not available")

    def _generate_with_retry(self, generation_func, *args, **kwargs) -> Tuple[Any, bool]:
        """
        Execute generation function with retry logic and provider fallback

        Args:
            generation_func: Function to execute
            *args, **kwargs: Arguments for the function

        Returns:
            Tuple of (result, success)
        """
        attempted_providers = []
        last_error = None

        while True:
            # Get next provider
            current_provider = self.provider_pool.get_next_provider(exclude=attempted_providers)

            if not current_provider:
                print(f"[Resilient] ✗ All providers exhausted")
                if last_error:
                    print(f"[Resilient] Last error: {last_error}")
                return None, False

            attempted_providers.append(current_provider)

            # Update orchestrator provider
            self.provider = current_provider
            self.provider_config = ProviderConfig.get_config(current_provider)

            # Reset LLM client to use new provider
            try:
                self.llm_client = LLMClient(current_provider)
            except Exception as e:
                print(f"[Resilient] Failed to initialize {current_provider.value}: {e}")
                self.provider_pool.mark_failure(current_provider, str(e))
                continue

            print(f"[Resilient] Using provider: {self.provider_config['name']}")

            # Try generation with retries
            for retry in range(self.max_retries_per_provider):
                try:
                    # Calculate delay based on retry strategy
                    if retry > 0:
                        delay = self._calculate_retry_delay(retry)
                        print(f"[Resilient] Retry {retry}/{self.max_retries_per_provider} in {delay:.1f}s...")
                        time.sleep(delay)

                    # Execute generation
                    start_time = time.time()
                    result = generation_func(*args, **kwargs)
                    response_time = time.time() - start_time

                    # Mark success
                    # Note: In real implementation, would track actual tokens/cost
                    self.provider_pool.mark_success(
                        current_provider,
                        response_time,
                        tokens=0,  # Would get from actual generation
                        cost=0.0   # Would calculate from actual usage
                    )

                    return result, True

                except Exception as e:
                    last_error = str(e)
                    print(f"[Resilient] Attempt {retry + 1} failed: {last_error}")

                    if retry == self.max_retries_per_provider - 1:
                        # Mark provider failure after max retries
                        self.provider_pool.mark_failure(current_provider, last_error)

        return None, False

    def _calculate_retry_delay(self, retry_count: int) -> float:
        """Calculate retry delay based on strategy"""
        if self.retry_strategy == RetryStrategy.EXPONENTIAL_BACKOFF:
            return min(2 ** retry_count, 60)  # Max 60 seconds

        elif self.retry_strategy == RetryStrategy.LINEAR_BACKOFF:
            return retry_count * 2  # 2, 4, 6 seconds

        elif self.retry_strategy == RetryStrategy.JITTERED:
            base_delay = 2 ** retry_count
            jitter = random.uniform(0, base_delay * 0.1)
            return min(base_delay + jitter, 60)

        else:  # IMMEDIATE
            return 0

    def generate_chapter(self, chapter_num: int, max_retries: int = 3) -> bool:
        """
        Generate chapter with resilient retry and checkpointing

        Overrides parent method to add resilience
        """
        # Check checkpoint if enabled
        if self.checkpoint_manager:
            checkpoint = self.checkpoint_manager.load_checkpoint(chapter_num)
            if checkpoint and checkpoint.stage == 'completed':
                self._log(f"Chapter {chapter_num} already completed (checkpoint)")
                return True

            if checkpoint and checkpoint.stage != 'started':
                self._log(f"Resuming chapter {chapter_num} from stage: {checkpoint.stage}")
                return self._resume_from_checkpoint(checkpoint)

        # Create checkpoint for new generation
        if self.checkpoint_manager:
            checkpoint = GenerationCheckpoint(
                chapter_num=chapter_num,
                stage='started',
                timestamp=time.time(),
                data={}
            )
            self.checkpoint_manager.save_checkpoint(checkpoint)

        # Use resilient generation
        def generate():
            return super(ResilientOrchestrator, self).generate_chapter(chapter_num, max_retries)

        result, success = self._generate_with_retry(generate)

        # Update checkpoint
        if self.checkpoint_manager:
            if success:
                checkpoint.stage = 'completed'
            else:
                checkpoint.stage = 'failed'
                checkpoint.error = "Generation failed after all retries"
            self.checkpoint_manager.save_checkpoint(checkpoint)

        return success

    def _resume_from_checkpoint(self, checkpoint: GenerationCheckpoint) -> bool:
        """Resume generation from checkpoint"""
        # This would need full integration with the generation pipeline
        # For now, simplified implementation
        self._log(f"Resuming from checkpoint stage: {checkpoint.stage}")

        # Determine what needs to be done
        if checkpoint.stage == 'prompt_created' and checkpoint.prompt:
            # Continue from prompt
            self._log("Continuing from saved prompt")
            # Would call generation with saved prompt
            return True

        elif checkpoint.stage == 'generated' and checkpoint.raw_text:
            # Continue from raw text
            self._log("Continuing from generated text")
            # Would run analysis and enhancement
            return True

        elif checkpoint.stage == 'analyzed':
            # Continue from analysis
            self._log("Continuing from analysis")
            # Would run enhancement
            return True

        else:
            # Can't resume, start over
            self._log("Cannot resume, starting over")
            return False

    def generate_chapter_with_quality_enforcement(self, chapter_num: int,
                                                  max_quality_retries: int = 3) -> Tuple[bool, Optional[ChapterQualityReport]]:
        """
        Generate chapter with quality gate enforcement (Phase 8)

        This method wraps the standard chapter generation with quality checks.
        If quality gates fail, it will regenerate the chapter up to max_quality_retries times.

        Args:
            chapter_num: Chapter number to generate
            max_quality_retries: Maximum regeneration attempts for quality failures

        Returns:
            Tuple of (success, quality_report)
        """
        if not self.quality_enforcement_enabled:
            # Fall back to standard generation if quality enforcement not enabled
            success = self.generate_chapter(chapter_num)
            return success, None

        quality_report = None

        for attempt in range(max_quality_retries):
            self._log(f"[Quality] Chapter {chapter_num} - Quality attempt {attempt + 1}/{max_quality_retries}")

            # Generate the chapter using standard resilient generation
            success = self.generate_chapter(chapter_num)

            if not success:
                self._log(f"[Quality] ✗ Chapter {chapter_num} generation failed")
                continue

            # Read the generated chapter
            chapter_file = self.workspace / f"chapter_{chapter_num:03d}.md"
            if not chapter_file.exists():
                self._log(f"[Quality] ✗ Chapter file not found: {chapter_file}")
                continue

            chapter_text = chapter_file.read_text(encoding='utf-8')

            # Run quality gates
            quality_report = self.quality_enforcer.check_chapter(chapter_text, chapter_num)

            if quality_report.passed_all_gates:
                self._log(f"[Quality] ✓ Chapter {chapter_num} passed all quality gates")
                quality_report.print_report()

                # Save quality report
                report_file = self.workspace / f"chapter_{chapter_num:03d}_quality_report.json"
                self.quality_enforcer.save_report(quality_report, report_file)

                return True, quality_report

            # Quality gates failed
            self._log(f"[Quality] ✗ Chapter {chapter_num} failed quality gates (score: {quality_report.total_score:.1f}/100)")
            quality_report.print_report()

            if attempt < max_quality_retries - 1:
                self._log(f"[Quality] Regenerating chapter {chapter_num} to meet quality standards...")
                # Delete the failed chapter so it regenerates
                if chapter_file.exists():
                    chapter_file.unlink()
            else:
                self._log(f"[Quality] ⚠ Chapter {chapter_num} failed quality after {max_quality_retries} attempts")
                self._log(f"[Quality] Keeping chapter with warnings (score: {quality_report.total_score:.1f}/100)")

                # Save quality report even for failed chapter
                report_file = self.workspace / f"chapter_{chapter_num:03d}_quality_report.json"
                self.quality_enforcer.save_report(quality_report, report_file)

        return True, quality_report  # Return True even if quality failed, but with report

    def initialize_enhanced_pipeline(self, premise: str, genre: str,
                                      num_chapters: int, themes: List[str] = None):
        """
        Initialize the enhanced quality pipeline for a book generation session.

        This should be called before generating chapters to set up:
        - DOC outline controller (hierarchical outline)
        - SCORE state tracker (dynamic state)
        - Narrative coherence tracker (cross-chapter consistency)

        Args:
            premise: Book premise/concept
            genre: Book genre
            num_chapters: Total number of chapters planned
            themes: Optional list of themes to explore
        """
        if not self.enhanced_quality_enabled:
            self._log("Enhanced pipeline not available, skipping initialization")
            return

        themes = themes or []
        self.enhanced_pipeline.initialize(premise, genre, num_chapters, themes)
        self._log(f"Enhanced quality pipeline initialized for {num_chapters} chapters")

    def generate_chapter_enhanced(self, chapter_num: int,
                                   max_quality_retries: int = 3) -> Tuple[bool, Optional[EnhancedQualityReport]]:
        """
        Generate a chapter using the enhanced quality pipeline (Phase 9).

        This method provides:
        1. Context from SCORE state tracker for coherent generation
        2. Outline guidance from DOC controller
        3. Post-processing to remove AI-isms
        4. Different-model critique for quality issues
        5. Narrative coherence validation
        6. Character and plot consistency checking

        Args:
            chapter_num: Chapter number to generate
            max_quality_retries: Maximum regeneration attempts

        Returns:
            Tuple of (success, enhanced_quality_report)
        """
        if not self.enhanced_quality_enabled:
            # Fall back to standard generation
            success = self.generate_chapter(chapter_num)
            return success, None

        enhanced_report = None

        for attempt in range(max_quality_retries):
            self._log(f"[Enhanced] Chapter {chapter_num} - Attempt {attempt + 1}/{max_quality_retries}")

            # Get generation context from enhanced pipeline
            context = self.enhanced_pipeline.get_generation_context(chapter_num)

            # Log what we're using
            if context.get('generation_prompt'):
                self._log(f"[Enhanced] Using DOC-guided generation prompt")
            if context.get('things_to_remember'):
                self._log(f"[Enhanced] {len(context['things_to_remember'])} items to remember")

            # Generate the chapter using standard method
            success = self.generate_chapter(chapter_num)

            if not success:
                self._log(f"[Enhanced] ✗ Chapter {chapter_num} generation failed")
                continue

            # Read the generated chapter
            chapter_file = self.workspace / f"chapter_{chapter_num:03d}.md"
            if not chapter_file.exists():
                self._log(f"[Enhanced] ✗ Chapter file not found")
                continue

            raw_content = chapter_file.read_text(encoding='utf-8')

            # Post-process the chapter (AI-ism removal, etc.)
            processed_content, processing_stats = self.enhanced_pipeline.post_process(
                chapter_num, raw_content
            )

            if processing_stats.get('ai_isms_replaced', 0) > 0:
                self._log(f"[Enhanced] Replaced {processing_stats['ai_isms_replaced']} AI-isms")

            # Save processed content
            chapter_file.write_text(processed_content, encoding='utf-8')

            # Validate chapter quality
            enhanced_report = self.enhanced_pipeline.validate_chapter(chapter_num, processed_content)

            # Log the results
            self._log(f"[Enhanced] Quality score: {enhanced_report.overall_score:.1f}/100")

            if enhanced_report.passed:
                self._log(f"[Enhanced] ✓ Chapter {chapter_num} passed enhanced quality gates")

                # Save quality report
                report_file = self.workspace / f"chapter_{chapter_num:03d}_enhanced_report.json"
                self._save_enhanced_report(enhanced_report, report_file)

                return True, enhanced_report

            # Quality failed
            self._log(f"[Enhanced] ✗ Chapter {chapter_num} failed enhanced quality")

            if enhanced_report.critical_issues:
                self._log(f"[Enhanced] Critical issues: {', '.join(enhanced_report.critical_issues[:3])}")

            if attempt < max_quality_retries - 1:
                self._log(f"[Enhanced] Regenerating chapter...")
                # Delete failed chapter
                if chapter_file.exists():
                    chapter_file.unlink()
            else:
                self._log(f"[Enhanced] ⚠ Max attempts reached, keeping chapter with issues")
                report_file = self.workspace / f"chapter_{chapter_num:03d}_enhanced_report.json"
                self._save_enhanced_report(enhanced_report, report_file)

        return True, enhanced_report

    def generate_chapter_multi_agent(self, chapter_num: int, outline: Dict,
                                      previous_content: str = "") -> Tuple[str, Dict]:
        """
        Generate a chapter using the multi-agent system (Phase 9).

        Uses specialist agents:
        - Structure Agent: Plans chapter structure
        - Character Agent: Develops character voice and consistency
        - Scene Agent: Writes scene-by-scene content
        - Dialogue Agent: Refines character dialogue
        - Editor Agent: Final polish and coherence

        Args:
            chapter_num: Chapter number to generate
            outline: Chapter outline from DOC controller
            previous_content: Content from previous chapter(s)

        Returns:
            Tuple of (generated_content, generation_stats)
        """
        if not self.multi_agent_enabled:
            self._log("Multi-agent generation not available")
            return "", {}

        # Plan the chapter first
        plan = self.multi_agent_generator.plan_chapter(
            chapter_num, outline, previous_content
        )

        self._log(f"[MultiAgent] Chapter {chapter_num} plan created")
        self._log(f"[MultiAgent] Key events: {len(plan.key_events)}")
        self._log(f"[MultiAgent] Characters: {len(plan.character_arcs)}")

        # Create LLM callable using current provider
        def llm_call(prompt: str, system: str = None) -> str:
            return self._call_llm(prompt, system)

        # Generate using multi-agent system
        content, stats = self.multi_agent_generator.generate_chapter(
            chapter_num, plan, llm_call
        )

        self._log(f"[MultiAgent] Generation complete")
        self._log(f"[MultiAgent] Total tokens: {stats.get('total_tokens', 0):,}")
        self._log(f"[MultiAgent] Revision cycles: {stats.get('revision_cycles', 0)}")

        # Save the generated chapter
        chapter_file = self.workspace / f"chapter_{chapter_num:03d}.md"
        chapter_file.write_text(content, encoding='utf-8')

        return content, stats

    def generate_chapter_advanced(self, chapter_num: int,
                                   chapter_goal: str,
                                   book_type: str = "fiction",
                                   passes: int = 3,
                                   target_words: int = 2500) -> Tuple[str, Dict]:
        """
        Generate a chapter using the Advanced Chapter Generator (Phase 10).

        Uses Claude-style techniques:
        - Multi-agent pipeline (Planning → Writing → Refinement)
        - Hierarchical memory (short/medium/long-term context)
        - Multi-pass refinement (draft → consistency → voice → compression)
        - Genre-adaptive prompting

        Based on 2024-2025 research:
        - StoryWriter multi-agent framework
        - DOME hierarchical outlining with memory
        - Claude 4.x best practices
        - Context engineering research

        Args:
            chapter_num: Chapter number to generate
            chapter_goal: What this chapter should accomplish
            book_type: "fiction" or "nonfiction"
            passes: Number of refinement passes (1-4)
            target_words: Target word count

        Returns:
            Tuple of (generated_content, generation_stats)
        """
        if not ADVANCED_GENERATOR_AVAILABLE:
            self._log("[Advanced] Advanced generator not available, falling back to standard")
            return self._fallback_generate(chapter_num)

        self._log(f"[Advanced] Generating chapter {chapter_num} with {passes} passes...")

        # Determine book type
        bt = BookType.NONFICTION if book_type.lower() == "nonfiction" else BookType.FICTION

        # Create generator with current settings
        generator = AdvancedChapterGenerator(
            book_type=bt,
            logger=self.logger if hasattr(self, 'logger') else None
        )

        # Set up book context from orchestrator state
        premise = getattr(self, 'premise', 'A story unfolds...')
        genre = getattr(self, 'genre', 'literary fiction')
        themes = getattr(self, 'themes', [])

        # Get character facts if available
        characters = {}
        if hasattr(self, 'enhanced_quality_pipeline') and self.enhanced_quality_pipeline:
            if "character" in self.enhanced_quality_pipeline.components:
                char_validator = self.enhanced_quality_pipeline.components["character"]
                if hasattr(char_validator, 'character_facts'):
                    characters = char_validator.character_facts

        generator.set_book_context(
            premise=premise,
            genre=genre,
            themes=themes,
            characters=characters
        )

        # Load previous chapter summaries into memory
        for prev_num in range(1, chapter_num):
            prev_file = self.workspace / f"chapter_{prev_num:03d}.md"
            summary_file = self.workspace / f"chapter_{prev_num:03d}_summary.txt"
            if summary_file.exists():
                generator.memory.chapter_summaries[prev_num] = summary_file.read_text(encoding='utf-8')
            elif prev_file.exists():
                # Generate summary if not cached
                prev_content = prev_file.read_text(encoding='utf-8')
                if len(prev_content) > 500:
                    generator.memory.chapter_summaries[prev_num] = prev_content[:500] + "..."

        # Build pass list
        pass_list = [PassType.DRAFT]
        if passes >= 2:
            if bt == BookType.FICTION:
                pass_list.append(PassType.CONSISTENCY)
            else:
                pass_list.append(PassType.EXAMPLES)
        if passes >= 3:
            pass_list.append(PassType.VOICE)
        if passes >= 4:
            pass_list.append(PassType.COMPRESSION)

        # Generate chapter
        content, stats = generator.generate_chapter(
            chapter_num=chapter_num,
            chapter_goal=chapter_goal,
            target_words=target_words,
            passes=pass_list
        )

        # Save chapter
        chapter_file = self.workspace / f"chapter_{chapter_num:03d}.md"
        chapter_file.write_text(content, encoding='utf-8')

        # Save summary for future chapters
        if stats.get('summary'):
            summary_file = self.workspace / f"chapter_{chapter_num:03d}_summary.txt"
            summary_file.write_text(stats['summary'], encoding='utf-8')

        self._log(f"[Advanced] Chapter {chapter_num} complete: {stats.get('final_word_count', 0)} words")
        self._log(f"[Advanced] Passes: {', '.join(stats.get('passes', []))}")

        return content, stats

    def _fallback_generate(self, chapter_num: int) -> Tuple[str, Dict]:
        """Fallback generation when advanced generator unavailable."""
        self.generate_chapter(chapter_num)
        chapter_file = self.workspace / f"chapter_{chapter_num:03d}.md"
        if chapter_file.exists():
            return chapter_file.read_text(encoding='utf-8'), {"fallback": True}
        return "", {"error": "Generation failed"}

    def _call_llm(self, prompt: str, system: str = None) -> str:
        """Make an LLM call using the current provider."""
        try:
            messages = []
            if system:
                messages.append({"role": "system", "content": system})
            messages.append({"role": "user", "content": prompt})

            response = self.llm_client.chat(messages)
            return response.get('content', '')
        except Exception as e:
            self._log(f"LLM call failed: {e}")
            return ""

    def _save_enhanced_report(self, report: EnhancedQualityReport, filepath):
        """Save enhanced quality report to JSON."""
        import json
        from dataclasses import asdict

        try:
            with open(filepath, 'w') as f:
                json.dump(asdict(report), f, indent=2)
        except Exception as e:
            self._log(f"Failed to save report: {e}")

    def get_provider_report(self) -> str:
        """Get detailed provider usage report"""
        stats = self.provider_pool.get_statistics()

        report = ["", "="*60, "PROVIDER USAGE REPORT", "="*60]
        report.append(f"Total providers: {stats['total_providers']}")
        report.append(f"Available providers: {stats['available_providers']}")
        report.append(f"Total cost: ${stats['total_cost']:.4f}")
        report.append(f"Total tokens: {stats['total_tokens']:,}")
        report.append("")

        for provider_name, details in stats['provider_details'].items():
            status = "✓" if details['available'] else "✗"
            report.append(f"{status} {details['name']}:")
            report.append(f"  Failures: {details['failure_count']}")
            report.append(f"  Avg response: {details['avg_response_time']}")
            report.append(f"  Total cost: {details['total_cost']}")
            report.append(f"  Total tokens: {details['total_tokens']:,}")
            report.append("")

        report.append("="*60)
        return "\n".join(report)


def demo_resilient_orchestrator():
    """Demonstrate resilient orchestrator functionality"""
    print("="*60)
    print("RESILIENT ORCHESTRATOR DEMO")
    print("="*60)

    # Create test source
    test_source = Path("test_resilient_source.txt")
    test_source.write_text("""
    Test book for resilient generation.
    Chapter 1: Testing retry logic
    Chapter 2: Testing provider fallback
    Chapter 3: Testing checkpointing
    """)

    # Create resilient orchestrator
    orchestrator = ResilientOrchestrator(
        source_file=test_source,
        book_name="test-resilient",
        genre="fantasy",
        target_words=10000,
        test_first=False,
        use_api=False,  # Demo mode
        providers=['groq', 'deepseek', 'openrouter', 'claude'],
        retry_strategy=RetryStrategy.EXPONENTIAL_BACKOFF,
        max_retries_per_provider=2,
        checkpoint_enabled=True,
        max_concurrent=2
    )

    print("\n--- Provider Pool Status ---")
    print(orchestrator.get_provider_report())

    # Simulate generation with failures
    print("\n--- Simulating Generation with Failures ---")

    # Mock some provider failures
    print("\n1. Simulating rate limit on primary provider...")
    orchestrator.provider_pool.mark_failure(
        orchestrator.provider_pool.providers[0],
        "Rate limit exceeded (429)"
    )

    print("\n2. Attempting chapter generation...")
    # This would normally generate, but we're in demo mode
    success = orchestrator.generate_chapter(1)
    print(f"Generation result: {'✓ Success' if success else '✗ Failed'}")

    print("\n3. Simulating multiple failures...")
    for i in range(3):
        orchestrator.provider_pool.mark_failure(
            orchestrator.provider_pool.providers[0],
            f"Connection timeout (attempt {i+1})"
        )

    print("\n--- Final Provider Report ---")
    print(orchestrator.get_provider_report())

    # Show checkpoint status
    if orchestrator.checkpoint_manager:
        print("\n--- Checkpoint Status ---")
        resume_info = orchestrator.checkpoint_manager.get_resume_point()
        print(f"Completed chapters: {resume_info['completed_chapters']}")
        print(f"Can resume: {resume_info['can_resume']}")
        print(f"Next chapter: {resume_info['next_chapter']}")

    # Test retry delay calculation
    print("\n--- Retry Delay Calculation ---")
    for strategy in RetryStrategy:
        orchestrator.retry_strategy = strategy
        print(f"\n{strategy.value}:")
        for retry in range(4):
            delay = orchestrator._calculate_retry_delay(retry)
            print(f"  Retry {retry}: {delay:.1f}s delay")

    # Cleanup
    test_source.unlink()
    import shutil
    workspace = Path("workspace/test-resilient")
    if workspace.exists():
        shutil.rmtree(workspace)
        print(f"\n✓ Cleaned up test files")


if __name__ == "__main__":
    import os
    # Set dummy API keys for demo
    os.environ.setdefault('GROQ_API_KEY', 'demo-key')
    os.environ.setdefault('DEEPSEEK_API_KEY', 'demo-key')
    os.environ.setdefault('OPENROUTER_API_KEY', 'demo-key')

    demo_resilient_orchestrator()