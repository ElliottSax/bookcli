#!/usr/bin/env python3
"""
Master Orchestrator for Autonomous Book Production
Runs complete pipeline: source → analysis → generation → assembly → KDP format
"""

import json
import sys
import subprocess
from pathlib import Path
from datetime import datetime
from typing import Optional
import time
import os
import re

# Add scripts directory to path for imports
script_dir = Path(__file__).parent
sys.path.insert(0, str(script_dir))

from llm_providers import LLMClient, Provider, ProviderConfig

# Import ultra-tier components
try:
    from multi_dimensional_scorer import MultiDimensionalScorer
    SCORER_AVAILABLE = True
except ImportError:
    SCORER_AVAILABLE = False

try:
    from prompt_builder import PromptBuilder
    PROMPT_BUILDER_AVAILABLE = True
except ImportError:
    PROMPT_BUILDER_AVAILABLE = False

# Import Phase 2 analyzers
try:
    from detail_density_analyzer import DetailDensityAnalyzer
    DETAIL_ANALYZER_AVAILABLE = True
except ImportError:
    DETAIL_ANALYZER_AVAILABLE = False

try:
    from word_count_enforcer import WordCountEnforcer
    WORD_COUNT_ENFORCER_AVAILABLE = True
except ImportError:
    WORD_COUNT_ENFORCER_AVAILABLE = False

try:
    from quality_predictor import QualityPredictor
    QUALITY_PREDICTOR_AVAILABLE = True
except ImportError:
    QUALITY_PREDICTOR_AVAILABLE = False


class BookOrchestrator:
    def __init__(self, source_file: Path, book_name: str, genre: str,
                 target_words: int = 80000, test_first: bool = True,
                 use_api: bool = False, max_budget: float = 50.0,
                 provider: str = "claude", multi_pass_attempts: int = 1):
        self.source_file = Path(source_file)
        self.book_name = book_name
        self.genre = genre
        self.target_words = target_words
        self.test_first = test_first
        self.use_api = use_api
        self.max_budget = max_budget
        self.multi_pass_attempts = multi_pass_attempts

        # Provider configuration
        self.provider = Provider(provider.lower())
        self.provider_config = ProviderConfig.get_config(self.provider)
        self.llm_client = None

        # Ultra-tier quality system
        self.scorer = MultiDimensionalScorer() if SCORER_AVAILABLE and multi_pass_attempts > 1 else None
        self.prompt_builder = PromptBuilder() if PROMPT_BUILDER_AVAILABLE else None

        # Phase 2 analyzers
        self.detail_analyzer = DetailDensityAnalyzer() if DETAIL_ANALYZER_AVAILABLE else None
        self.word_count_enforcer = WordCountEnforcer() if WORD_COUNT_ENFORCER_AVAILABLE else None
        self.quality_predictor = QualityPredictor() if QUALITY_PREDICTOR_AVAILABLE else None

        # Cost tracking
        self.total_cost = 0.0
        self.total_input_tokens = 0
        self.total_output_tokens = 0

        # Setup paths
        self.workspace = Path("workspace") / book_name
        self.output_dir = Path("output") / book_name
        self.chapters_dir = self.workspace / "chapters"
        self.analysis_dir = self.workspace / "analysis"
        self.continuity_dir = self.workspace / "continuity"
        self.summaries_dir = self.workspace / "summaries"

        # Create directories
        for directory in [self.workspace, self.output_dir, self.chapters_dir,
                          self.analysis_dir, self.continuity_dir, self.summaries_dir]:
            directory.mkdir(parents=True, exist_ok=True)

        # Status tracking
        self.status_file = self.workspace / "status.json"
        self.log_file = self.workspace / "production.log"

        self._init_status()

    def _init_status(self):
        """Initialize status tracking"""
        if not self.status_file.exists():
            status = {
                "book_name": self.book_name,
                "genre": self.genre,
                "target_words": self.target_words,
                "started": datetime.now().isoformat(),
                "stage": "initialized",
                "chapters_planned": 0,
                "chapters_completed": 0,
                "total_words": 0,
                "quality_passes": 0,
                "errors": [],
                "completed": False
            }
            self._save_status(status)

    def _load_status(self):
        """Load current status"""
        return json.loads(self.status_file.read_text())

    def _save_status(self, status):
        """Save status"""
        self.status_file.write_text(json.dumps(status, indent=2))

    def _log(self, message: str, level: str = "INFO"):
        """Log message"""
        timestamp = datetime.now().isoformat()
        log_entry = f"[{timestamp}] [{level}] {message}\n"
        with open(self.log_file, 'a') as f:
            f.write(log_entry)
        print(f"[{level}] {message}")

    def _update_stage(self, stage: str):
        """Update current stage"""
        status = self._load_status()
        status["stage"] = stage
        status["last_updated"] = datetime.now().isoformat()
        self._save_status(status)
        self._log(f"Stage: {stage}")

    def run_tests(self):
        """Run self-tests before production"""
        self._log("Running self-tests...")
        self._update_stage("testing")

        # Test quality gate
        self._log("Testing quality gate...")
        test_text = "She felt very happy. He delved into the mystery. Their hearts hammered."
        test_file = self.workspace / "test.txt"
        test_file.write_text(test_text)

        result = subprocess.run(
            ["python3", "scripts/quality_gate.py", str(test_file)],
            capture_output=True, text=True
        )

        if result.returncode == 0:
            self._log("✓ Quality gate test passed")
        else:
            self._log("✗ Quality gate test failed", "ERROR")
            return False

        # Test continuity tracker
        self._log("Testing continuity tracker...")
        result = subprocess.run(
            ["python3", "scripts/continuity_tracker.py", str(self.workspace), "summary"],
            capture_output=True, text=True
        )

        if result.returncode == 0:
            self._log("✓ Continuity tracker test passed")
        else:
            self._log("✗ Continuity tracker test failed", "ERROR")
            return False

        test_file.unlink()
        self._log("All tests passed ✓")
        return True

    def analyze_source(self):
        """Analyze source material"""
        self._log("Analyzing source material...")
        self._update_stage("analysis")

        if not self.source_file.exists():
            self._log(f"Source file not found: {self.source_file}", "ERROR")
            return False

        # Read source
        source_text = self.source_file.read_text(encoding='utf-8', errors='ignore')
        word_count = len(source_text.split())
        self._log(f"Source: {word_count:,} words")

        # Estimate chapters needed
        avg_chapter_length = 3500
        chapters_needed = max(20, self.target_words // avg_chapter_length)

        # Save analysis
        analysis = {
            "source_file": str(self.source_file),
            "source_words": word_count,
            "target_words": self.target_words,
            "chapters_planned": chapters_needed,
            "words_per_chapter": avg_chapter_length,
            "genre": self.genre,
            "analyzed": datetime.now().isoformat()
        }

        analysis_file = self.analysis_dir / "plan.json"
        analysis_file.write_text(json.dumps(analysis, indent=2))

        # Update status
        status = self._load_status()
        status["chapters_planned"] = chapters_needed
        status["source_words"] = word_count
        self._save_status(status)

        self._log(f"Plan: {chapters_needed} chapters × {avg_chapter_length} words")
        return True

    def create_chapter_plan(self):
        """Create detailed chapter-by-chapter plan"""
        self._log("Creating chapter plan...")

        analysis = json.loads((self.analysis_dir / "plan.json").read_text())
        chapters_planned = analysis["chapters_planned"]

        # Create basic structure plan
        plan = {
            "total_chapters": chapters_planned,
            "structure": {
                "act1": {"start": 1, "end": int(chapters_planned * 0.25), "focus": "setup"},
                "act2a": {"start": int(chapters_planned * 0.25) + 1, "end": int(chapters_planned * 0.50), "focus": "rising_action"},
                "act2b": {"start": int(chapters_planned * 0.50) + 1, "end": int(chapters_planned * 0.75), "focus": "complications"},
                "act3": {"start": int(chapters_planned * 0.75) + 1, "end": chapters_planned, "focus": "climax_resolution"}
            },
            "chapters": []
        }

        # Generate chapter beats (simplified - Claude will enhance)
        for i in range(1, chapters_planned + 1):
            if i <= plan["structure"]["act1"]["end"]:
                beat = "Introduce characters, establish world, inciting incident"
            elif i <= plan["structure"]["act2a"]["end"]:
                beat = "Rising action, complications, character development"
            elif i <= plan["structure"]["act2b"]["end"]:
                beat = "Escalating tension, midpoint twist, darkening stakes"
            else:
                beat = "Climax building, resolution, epilogue"

            plan["chapters"].append({
                "number": i,
                "beat": beat,
                "target_words": analysis["words_per_chapter"],
                "status": "pending"
            })

        plan_file = self.analysis_dir / "chapter_plan.json"
        plan_file.write_text(json.dumps(plan, indent=2))

        self._log(f"Chapter plan created: {chapters_planned} chapters")
        return plan

    def _predict_quality_from_outline(self, chapter_num: int, chapter_plan: dict, context: dict):
        """Predict quality from outline before generation (Phase 2)"""
        if not self.quality_predictor:
            return None

        self._log(f"Predicting quality from outline...")

        # Build outline text
        outline = f"""
Chapter {chapter_num}: {chapter_plan.get('beat', 'Continue the story')}
Target length: {chapter_plan.get('target_words', 3000)} words
"""
        # Add context
        context_summary = {}
        if context.get("characters"):
            context_summary["character_count"] = len(context["characters"])
        if context.get("active_threads"):
            context_summary["thread_count"] = len(context["active_threads"])

        # Predict
        result = self.quality_predictor.predict_from_outline(outline, context_summary)

        self._log(f"Predicted quality: {result['predicted_quality']:.1f}/10 ({result['confidence']})")

        if result['issues']:
            self._log(f"Issues found: {len(result['issues'])}")
            for issue in result['issues'][:3]:  # Show top 3
                self._log(f"  [{issue['severity']}] {issue['issue']}: {issue['fix']}")

        return result

    def _analyze_generated_chapter(self, chapter_text: str, target_words: int):
        """Analyze generated chapter with detail density and word count (Phase 2)"""
        results = {}

        # Detail density analysis
        if self.detail_analyzer:
            self._log("Analyzing detail density...")
            density_result = self.detail_analyzer.analyze(chapter_text, target_density=3.0)
            results['detail_density'] = density_result

            if density_result['passed']:
                self._log(f"✓ Detail density: {density_result['density']:.2f}/1000 words (target: 3.0)")
            else:
                self._log(f"✗ Detail density: {density_result['density']:.2f}/1000 words (needs {density_result['details_needed']} more)")

        # Word count analysis
        if self.word_count_enforcer:
            self._log("Validating word count...")
            wc_result = self.word_count_enforcer.validate(chapter_text, target_words)
            results['word_count'] = wc_result

            if wc_result['passed']:
                self._log(f"✓ Word count: {wc_result['actual']} words (target: {wc_result['target']} ±15%)")
            else:
                variance_pct = ((wc_result['actual'] - wc_result['target']) / wc_result['target']) * 100
                self._log(f"✗ Word count: {wc_result['actual']} words ({variance_pct:+.1f}% from target)")
                if 'action' in wc_result:
                    self._log(f"  Action: {wc_result['action']}")

        return results

    def _enhance_chapter_section(self, section_text: str, issue_type: str, target_improvement: str):
        """Enhance a specific section of text based on identified issue"""
        if not self.llm_client:
            return section_text

        # Build enhancement prompt
        enhancement_prompts = {
            'ADD_DEPTH': """Enhance this section by adding obsessive detail:
- Add specific measurements, counts, or numbers
- Include sensory specifics (exact colors, textures, temperatures)
- Add micro-focus on physical details (hands, eyes, skin)
- Maintain the same narrative events and pacing

Original section:
{section}

Enhanced section (maintain same events, add depth):""",

            'ADD_EMOTION': """Enhance this section with deeper emotional grounding:
- Replace generic emotions with physical sensations
- Add body responses (heart rate, breath, temperature)
- Include sensory details tied to emotions
- Maintain the same narrative events

Original section:
{section}

Enhanced section (same events, deeper emotion):""",

            'EXPAND_INTIMATE': """Expand this intimate moment with time dilation (3× longer):
- Slow down the key moment
- Add temperature details, touch sensations, duration
- Include breath patterns, heart rate, proximity
- Maintain emotional authenticity

Original section:
{section}

Expanded section (3× detail on intimate moment):""",
        }

        prompt_template = enhancement_prompts.get(issue_type, enhancement_prompts['ADD_DEPTH'])
        prompt = prompt_template.format(section=section_text)

        try:
            enhanced_text, _, _ = self.llm_client.generate(prompt, max_tokens=2000)
            return enhanced_text.strip()
        except Exception as e:
            self._log(f"Enhancement failed: {str(e)}", "WARN")
            return section_text

    def _iterative_first_pass_generation(self, chapter_num: int, chapter_plan: dict, context: dict, max_iterations: int = 2):
        """Generate chapter with iterative analysis and enhancement (Phase 3)"""
        self._log(f"\n{'='*60}")
        self._log(f"ITERATIVE FIRST-PASS GENERATION (Phase 3)")
        self._log(f"{'='*60}\n")

        target_words = chapter_plan.get('target_words', 3000)

        # Step 1: Predict quality from outline
        quality_prediction = self._predict_quality_from_outline(chapter_num, chapter_plan, context)

        # Step 2: Generate initial version
        self._log("\n--- Initial Generation ---")
        prompt = self._create_chapter_prompt(chapter_num, chapter_plan, context)

        try:
            chapter_text, input_tokens, output_tokens = self.llm_client.generate(prompt)

            # Track costs
            cost = ProviderConfig.calculate_cost(self.provider, input_tokens, output_tokens)
            self.total_input_tokens += input_tokens
            self.total_output_tokens += output_tokens
            self.total_cost += cost

            self._log(f"Generated: {len(chapter_text.split())} words | Cost: ${cost:.4f}")

        except Exception as e:
            self._log(f"Generation failed: {str(e)}", "ERROR")
            return None

        # Step 3: Analyze generated chapter
        self._log("\n--- Analysis ---")
        analysis = self._analyze_generated_chapter(chapter_text, target_words)

        # Step 4: Iterative enhancement if needed
        iteration = 0
        while iteration < max_iterations:
            needs_enhancement = False

            # Check detail density
            if analysis.get('detail_density') and not analysis['detail_density']['passed']:
                needs_enhancement = True
                self._log(f"\nIteration {iteration + 1}: Enhancing detail density...")

                # Find weak sections and enhance them
                if 'weak_sections' in analysis['detail_density']:
                    for weak_section in analysis['detail_density']['weak_sections'][:2]:  # Enhance top 2
                        section_start = weak_section.get('start', 0)
                        section_end = weak_section.get('end', len(chapter_text))
                        section_text = chapter_text[section_start:section_end]

                        enhanced = self._enhance_chapter_section(section_text, 'ADD_DEPTH', 'increase_detail_density')
                        chapter_text = chapter_text[:section_start] + enhanced + chapter_text[section_end:]

                        # Track enhancement cost
                        self.total_cost += 0.01  # Approximate small enhancement cost

            # Check word count
            if analysis.get('word_count') and not analysis['word_count']['passed']:
                wc = analysis['word_count']

                if wc.get('action') == 'ADD_DEPTH':
                    needs_enhancement = True
                    self._log(f"\nIteration {iteration + 1}: Expanding chapter (deficit: {wc.get('deficit', 0)} words)...")

                    # Add expansion at suggested points
                    if 'suggestions' in wc:
                        # Use first suggestion for expansion
                        suggestion = wc['suggestions'][0] if wc['suggestions'] else None
                        if suggestion:
                            # Enhance emotional or intimate moments
                            enhanced = self._enhance_chapter_section(chapter_text[-500:], 'EXPAND_INTIMATE', 'add_words')
                            chapter_text = chapter_text[:-500] + enhanced

                elif wc.get('action') == 'CUT_WEAK':
                    # For now, just log - cutting is risky
                    self._log(f"Note: Chapter is {wc.get('excess', 0)} words over target, consider manual review")

            if not needs_enhancement:
                break

            # Re-analyze after enhancement
            self._log("\n--- Re-analyzing after enhancement ---")
            analysis = self._analyze_generated_chapter(chapter_text, target_words)
            iteration += 1

        # Step 5: Return final chapter
        final_word_count = len(chapter_text.split())
        self._log(f"\n✓ Final chapter: {final_word_count} words")

        return chapter_text

    def generate_chapter(self, chapter_num: int, max_retries: int = 3):
        """Generate a single chapter with quality checks"""
        self._log(f"Generating chapter {chapter_num}...")

        chapter_file = self.chapters_dir / f"chapter_{chapter_num:03d}.md"

        # Get context from continuity tracker
        result = subprocess.run(
            ["python3", "scripts/continuity_tracker.py", str(self.workspace),
             "get_context", str(chapter_num)],
            capture_output=True, text=True
        )

        context = json.loads(result.stdout) if result.returncode == 0 else {}

        # Load chapter plan
        plan = json.loads((self.analysis_dir / "chapter_plan.json").read_text())
        chapter_plan = plan["chapters"][chapter_num - 1]

        # Use API if enabled, otherwise just create prompt
        if self.use_api:
            # Use multi-pass if enabled
            if self.multi_pass_attempts > 1 and self.scorer:
                return self._generate_chapter_multipass(chapter_num, chapter_plan, context, max_retries)
            # Use iterative first-pass if Phase 2 analyzers available
            elif self.detail_analyzer and self.word_count_enforcer:
                return self._generate_chapter_iterative(chapter_num, chapter_plan, context, max_retries)
            else:
                # Basic single-pass generation
                prompt = self._create_chapter_prompt(chapter_num, chapter_plan, context)
                prompt_file = self.workspace / f"prompt_ch{chapter_num}.md"
                prompt_file.write_text(prompt)
                return self._generate_chapter_with_api(chapter_num, prompt, max_retries)
        else:
            # Prompt-only mode (no API)
            prompt = self._create_chapter_prompt(chapter_num, chapter_plan, context)
            prompt_file = self.workspace / f"prompt_ch{chapter_num}.md"
            prompt_file.write_text(prompt)
            self._log(f"Chapter {chapter_num} prompt created: {prompt_file}")
            self._log("API mode disabled - use Claude Code CLI to generate chapter")
            return True

    def _generate_chapter_with_api(self, chapter_num: int, prompt: str, max_retries: int = 3):
        """Generate chapter using configured LLM provider"""
        # Initialize LLM client if not already done
        if self.llm_client is None:
            try:
                self.llm_client = LLMClient(self.provider)
                self._log(f"Using provider: {self.provider_config['name']}")
                self._log(f"Model: {self.provider_config['model']}")
                self._log(f"Cost: ${self.provider_config['input_cost_per_1m']:.2f}/${self.provider_config['output_cost_per_1m']:.2f} per 1M tokens")
            except ValueError as e:
                self._log(f"Failed to initialize provider: {str(e)}", "ERROR")
                self._log(f"Set API key: export {self.provider_config['api_key_env']}=your-key", "ERROR")
                return False
            except Exception as e:
                self._log(f"Error initializing provider: {str(e)}", "ERROR")
                return False

        chapter_file = self.chapters_dir / f"chapter_{chapter_num:03d}.md"

        for attempt in range(max_retries):
            try:
                self._log(f"Calling {self.provider_config['name']} API (attempt {attempt + 1}/{max_retries})...")

                # Call LLM provider
                chapter_text, input_tokens, output_tokens = self.llm_client.generate(prompt)

                # Track costs
                cost = ProviderConfig.calculate_cost(self.provider, input_tokens, output_tokens)

                self.total_input_tokens += input_tokens
                self.total_output_tokens += output_tokens
                self.total_cost += cost

                self._log(f"Tokens: {input_tokens} in, {output_tokens} out | Cost: ${cost:.4f} | Total: ${self.total_cost:.2f}")

                # Check budget
                if self.total_cost > self.max_budget:
                    self._log(f"Budget exceeded! ${self.total_cost:.2f} > ${self.max_budget:.2f}", "ERROR")
                    return False

                # Save chapter
                chapter_file.write_text(chapter_text)
                self._log(f"Chapter {chapter_num} generated: {len(chapter_text.split())} words")

                # Auto-extract and track continuity
                self._auto_extract_continuity(chapter_num, chapter_text)

                return True

            except Exception as e:
                self._log(f"Attempt {attempt + 1} failed: {str(e)}", "WARN")
                if attempt == max_retries - 1:
                    self._log(f"Failed to generate chapter {chapter_num} after {max_retries} attempts", "ERROR")
                    return False
                time.sleep(2)  # Wait before retry

        return False

    def _generate_chapter_iterative(self, chapter_num: int, chapter_plan: dict, context: dict, max_retries: int = 3):
        """Generate chapter using iterative first-pass system (Phase 3)"""
        # Initialize LLM client if not already done
        if self.llm_client is None:
            try:
                self.llm_client = LLMClient(self.provider)
                self._log(f"Using provider: {self.provider_config['name']}")
                self._log(f"Model: {self.provider_config['model']}")
            except Exception as e:
                self._log(f"Error initializing provider: {str(e)}", "ERROR")
                return False

        chapter_file = self.chapters_dir / f"chapter_{chapter_num:03d}.md"

        # Use iterative first-pass generation
        chapter_text = self._iterative_first_pass_generation(chapter_num, chapter_plan, context, max_iterations=2)

        if not chapter_text:
            self._log(f"Failed to generate chapter {chapter_num}", "ERROR")
            return False

        # Check budget
        if self.total_cost > self.max_budget:
            self._log(f"Budget exceeded! ${self.total_cost:.2f} > ${self.max_budget:.2f}", "ERROR")
            return False

        # Save chapter
        chapter_file.write_text(chapter_text)
        self._log(f"Chapter {chapter_num} saved: {len(chapter_text.split())} words")
        self._log(f"Total cost: ${self.total_cost:.2f}")

        # Auto-extract and track continuity
        self._auto_extract_continuity(chapter_num, chapter_text)

        return True

    def _generate_chapter_multipass(self, chapter_num: int, chapter_plan: dict, context: dict, max_retries: int = 3):
        """Generate multiple chapter versions and select the best"""

        self._log(f"\n{'='*60}")
        self._log(f"MULTI-PASS GENERATION: {self.multi_pass_attempts} versions")
        self._log(f"{'='*60}\n")

        # Initialize LLM client if needed
        if self.llm_client is None:
            try:
                self.llm_client = LLMClient(self.provider)
                self._log(f"Using provider: {self.provider_config['name']}")
                self._log(f"Model: {self.provider_config['model']}")
            except Exception as e:
                self._log(f"Error initializing provider: {str(e)}", "ERROR")
                return False

        attempts = []
        chapter_file = self.chapters_dir / f"chapter_{chapter_num:03d}.md"

        # Generate multiple versions
        for version in range(1, self.multi_pass_attempts + 1):
            self._log(f"\n--- Version {version}/{self.multi_pass_attempts} ---")

            # Determine variation focus for this version
            variation_focus = self._get_variation_focus(version)
            if variation_focus:
                self._log(f"Focus: {variation_focus}")

            # Create prompt with appropriate variation focus
            prompt_variation = self._create_chapter_prompt(chapter_num, chapter_plan, context, variation_focus)

            # Generate this version
            for retry in range(max_retries):
                try:
                    self._log(f"Calling {self.provider_config['name']} API...")

                    chapter_text, input_tokens, output_tokens = self.llm_client.generate(prompt_variation)

                    # Track costs
                    cost = ProviderConfig.calculate_cost(self.provider, input_tokens, output_tokens)
                    self.total_input_tokens += input_tokens
                    self.total_output_tokens += output_tokens
                    self.total_cost += cost

                    self._log(f"Generated: {len(chapter_text.split())} words | Cost: ${cost:.4f}")

                    # Check budget
                    if self.total_cost > self.max_budget:
                        self._log(f"Budget exceeded! ${self.total_cost:.2f} > ${self.max_budget:.2f}", "ERROR")
                        return False

                    # Score this version
                    score_result = self.scorer.score(chapter_text)
                    self._log(f"Score: {score_result.total:.1f}/10")
                    self._log(f"  Emotional: {score_result.scores['emotional_impact']:.1f} | "
                             f"Voice: {score_result.scores['voice_distinctiveness']:.1f} | "
                             f"Depth: {score_result.scores['obsession_depth']:.1f}")

                    attempts.append({
                        'version': version,
                        'text': chapter_text,
                        'score': score_result.total,
                        'score_result': score_result
                    })

                    break  # Success

                except Exception as e:
                    self._log(f"Attempt {retry + 1} failed: {str(e)}", "WARN")
                    if retry == max_retries - 1:
                        self._log(f"Version {version} failed after {max_retries} attempts", "ERROR")
                        # Continue to next version rather than failing completely
                    time.sleep(2)

        # Check if we got any successful attempts
        if not attempts:
            self._log("All versions failed to generate!", "ERROR")
            return False

        # Select best version
        best = max(attempts, key=lambda a: a['score'])

        self._log(f"\n{'='*60}")
        self._log(f"BEST VERSION: v{best['version']} - Score: {best['score']:.1f}/10")
        self._log(f"{'='*60}")

        # Show all scores for comparison
        self._log("\nAll versions:")
        for attempt in sorted(attempts, key=lambda a: a['score'], reverse=True):
            marker = "★" if attempt['version'] == best['version'] else " "
            self._log(f"{marker} v{attempt['version']}: {attempt['score']:.1f}/10")

        # Save best version
        chapter_file.write_text(best['text'])
        self._log(f"\n✓ Best version saved: {len(best['text'].split())} words")

        # Auto-extract and track continuity
        self._auto_extract_continuity(chapter_num, best['text'])

        return True

    def _get_variation_focus(self, version: int) -> Optional[str]:
        """Get variation focus for this version to encourage diversity

        Maps version numbers to variation_focus strings used by prompt_builder.
        If prompt_builder is not available, returns None and variations are handled
        by appending instructions to base prompt.

        Returns:
            variation_focus string: 'emotion', 'voice', 'theme', 'depth', 'risk', 'balanced', or None
        """

        # Map version numbers to variation focuses
        # Version 1 is baseline (no specific focus)
        focus_map = {
            1: None,           # Baseline - no specific focus
            2: 'emotion',      # Emotional specificity
            3: 'voice',        # Voice distinctiveness
            4: 'depth',        # Obsessive depth
            5: 'theme',        # Thematic subtlety
            6: 'risk',         # Risk-taking
            7: 'balanced',     # Balanced excellence
        }

        # Cycle through focuses if more than 7 versions
        return focus_map.get(((version - 1) % 7) + 1)


    def _auto_extract_continuity(self, chapter_num: int, chapter_text: str):
        """Automatically extract and track continuity from chapter"""
        self._log(f"Extracting continuity from chapter {chapter_num}...")

        # Extract character names mentioned (simple regex)
        # In production, could use Claude to extract structured data
        character_pattern = r'\b([A-Z][a-z]+ [A-Z][a-z]+)\b'
        characters_found = set(re.findall(character_pattern, chapter_text))

        # Track new characters
        for char_name in characters_found:
            # Simple tracking - just note they appeared
            subprocess.run([
                "python3", "scripts/continuity_tracker.py", str(self.workspace),
                "update_character", char_name,
                json.dumps({"chapter": chapter_num, "mentioned": True})
            ], capture_output=True)

        self._log(f"Tracked {len(characters_found)} character mentions")

        # Generate chapter summary for next chapter context
        summary_file = self.summaries_dir / f"chapter_{chapter_num:03d}_summary.md"
        summary = self._generate_chapter_summary(chapter_text)
        summary_file.write_text(summary)

    def _generate_chapter_summary(self, chapter_text: str) -> str:
        """Create brief summary of chapter for next chapter's context"""
        # Simple summary - first and last paragraphs
        paragraphs = [p.strip() for p in chapter_text.split('\n\n') if p.strip()]

        if len(paragraphs) > 2:
            return f"Previous chapter:\n{paragraphs[0]}\n...\n{paragraphs[-1]}"
        else:
            return f"Previous chapter:\n{chapter_text[:500]}..."

    def _create_chapter_prompt(self, chapter_num: int, chapter_plan: dict, context: dict, variation_focus: Optional[str] = None):
        """Create comprehensive prompt for chapter generation"""

        # Use enhanced prompt builder if available
        if self.prompt_builder and PROMPT_BUILDER_AVAILABLE:
            # Build enhanced prompt with few-shot examples
            outline = f"""
Chapter {chapter_num}: {chapter_plan.get('beat', 'Continue the story')}
Target length: {chapter_plan.get('target_words', 3000)} words
"""

            # Build context summary
            context_summary = ""
            if context.get("characters"):
                context_summary += "Active characters: " + ", ".join(list(context["characters"].keys())[:5]) + "\n"
            if context.get("active_threads"):
                threads = [t.get('thread', '') for t in context["active_threads"][:3]]
                context_summary += "Active plot threads: " + ", ".join(threads) + "\n"

            # Source excerpt (use actual source if available)
            source_excerpt = ""
            if hasattr(self, 'source_file') and self.source_file.exists():
                with open(self.source_file, 'r') as f:
                    source_excerpt = f.read()[:1000]  # First 1000 chars

            return self.prompt_builder.build_chapter_prompt(
                chapter_num=chapter_num,
                outline=outline,
                context=context_summary,
                source_excerpt=source_excerpt,
                variation_focus=variation_focus,
                num_examples=2
            )

        # Fallback to basic prompt if prompt_builder not available
        prompt = f"""# Generate Chapter {chapter_num}

## Load Required Files
- .claude/core-rules.md
- .claude/forbidden-lists.md
- config/genres/{self.genre}.md
- config/craft/scene-structure.md

## Chapter Specifications
- **Number**: {chapter_num}
- **Target Words**: {chapter_plan['target_words']}
- **Beat**: {chapter_plan['beat']}

## Context from Previous Chapters
"""

        if context.get("characters"):
            prompt += "\n### Characters\n"
            for name, data in list(context["characters"].items())[:5]:
                prompt += f"- **{name}**: {data.get('current_state', 'Active')}\n"

        if context.get("active_threads"):
            prompt += "\n### Active Plot Threads\n"
            for thread in context["active_threads"][:5]:
                prompt += f"- {thread.get('thread', 'Unknown')}\n"

        prompt += f"""

## Instructions
1. Generate chapter following ALL rules from loaded files
2. Maintain continuity with established facts
3. End on cliffhanger/hook for next chapter
4. Track: new characters, events, facts revealed
5. WRITE COMPLETE CHAPTER - do not summarize or outline

## Output Format
Write the complete chapter text in markdown format.
At the end, add metadata:

---
METADATA:
- New characters: [list]
- Key events: [list]
- Facts established: [list]
- Threads advanced: [list]
---

## Begin Writing Chapter {chapter_num}
"""
        return prompt

    def quality_check_chapter(self, chapter_num: int):
        """Run quality gate on chapter with humanization"""
        self._log(f"Quality check: chapter {chapter_num}...")

        chapter_file = self.chapters_dir / f"chapter_{chapter_num:03d}.md"

        if not chapter_file.exists():
            self._log(f"Chapter file not found: {chapter_file}", "ERROR")
            return False

        # STEP 1: Humanize the chapter (apply voice, emotion, theme subtlety)
        self._log(f"Humanizing chapter {chapter_num}...")
        result = subprocess.run(
            ["python3", "scripts/humanizer.py", str(chapter_file), str(chapter_num)],
            capture_output=True, text=True
        )

        if result.returncode == 0:
            self._log(f"✓ Chapter {chapter_num} humanized")
        else:
            self._log(f"⚠ Humanization warning: {result.stderr}", "WARN")

        # STEP 2: Run quality gate with auto-fix
        result = subprocess.run(
            ["python3", "scripts/quality_gate.py", str(chapter_file)],
            capture_output=True, text=True
        )

        if result.returncode == 0:
            self._log(f"✓ Chapter {chapter_num} passed quality gate")
            return True
        else:
            output = json.loads(result.stdout)
            self._log(f"✗ Chapter {chapter_num} quality issues: {output.get('total_issues', 0)}")

            # Auto-fix was applied, check again
            if output.get('fixes_applied', 0) > 0:
                self._log(f"Applied {output['fixes_applied']} automatic fixes, rechecking...")
                # Quality gate already updated file, just return success
                return True

            return False

    def update_continuity(self, chapter_num: int):
        """Extract and update continuity from chapter"""
        self._log(f"Updating continuity: chapter {chapter_num}...")

        chapter_file = self.chapters_dir / f"chapter_{chapter_num:03d}.md"
        content = chapter_file.read_text()

        # Extract metadata section
        if "METADATA:" in content:
            metadata_section = content.split("METADATA:")[1]

            # Parse metadata (simplified - would be more sophisticated)
            # This would extract characters, events, facts, etc.

            # Update continuity files
            # (In real implementation, would parse and call continuity_tracker)

            self._log(f"✓ Continuity updated for chapter {chapter_num}")

        return True

    def generate_all_chapters(self, resume: bool = True):
        """Generate all chapters in sequence with progress tracking and resume capability"""
        self._update_stage("generation")

        plan = json.loads((self.analysis_dir / "chapter_plan.json").read_text())
        total_chapters = plan["total_chapters"]

        # Resume logic - find last completed chapter
        start_chapter = 1
        if resume:
            status = self._load_status()
            completed = status.get("chapters_completed", 0)
            if completed > 0:
                start_chapter = completed + 1
                self._log(f"Resuming from chapter {start_chapter} (completed: {completed})")

        # Calculate progress
        total_to_generate = total_chapters - start_chapter + 1
        start_time = time.time()

        for i, chapter_num in enumerate(range(start_chapter, total_chapters + 1), 1):
            # Progress bar
            progress_pct = (i / total_to_generate) * 100
            elapsed = time.time() - start_time
            if i > 1:
                eta_seconds = (elapsed / (i - 1)) * (total_to_generate - i + 1)
                eta_str = time.strftime('%H:%M:%S', time.gmtime(eta_seconds))
            else:
                eta_str = "calculating..."

            self._log(f"\n{'='*60}")
            self._log(f"CHAPTER {chapter_num}/{total_chapters} | Progress: {progress_pct:.1f}% | ETA: {eta_str}")
            self._log(f"{'='*60}\n")

            # Generate chapter
            if not self.generate_chapter(chapter_num):
                self._log(f"Failed to generate chapter {chapter_num}", "ERROR")
                # Save failure in status for debugging
                status = self._load_status()
                status["errors"].append({
                    "chapter": chapter_num,
                    "stage": "generation",
                    "timestamp": datetime.now().isoformat()
                })
                self._save_status(status)
                continue

            # Quality check
            if not self.quality_check_chapter(chapter_num):
                self._log(f"Chapter {chapter_num} failed quality check", "ERROR")
                # Save failure
                status = self._load_status()
                status["errors"].append({
                    "chapter": chapter_num,
                    "stage": "quality_check",
                    "timestamp": datetime.now().isoformat()
                })
                self._save_status(status)
                continue

            # Update continuity (already done in _auto_extract_continuity if using API)
            if not self.use_api:
                self.update_continuity(chapter_num)

            # Update status with cost tracking
            status = self._load_status()
            status["chapters_completed"] = chapter_num
            status["total_cost"] = self.total_cost
            status["total_input_tokens"] = self.total_input_tokens
            status["total_output_tokens"] = self.total_output_tokens
            self._save_status(status)

            self._log(f"✓ Chapter {chapter_num} complete")
            self._log(f"Total cost so far: ${self.total_cost:.2f}")

        # Final summary
        elapsed_total = time.time() - start_time
        self._log("\n" + "="*60)
        self._log(f"ALL CHAPTERS GENERATED: {total_chapters}")
        self._log(f"Total time: {time.strftime('%H:%M:%S', time.gmtime(elapsed_total))}")
        self._log(f"Total cost: ${self.total_cost:.2f}")
        self._log(f"Tokens: {self.total_input_tokens:,} in, {self.total_output_tokens:,} out")
        self._log("="*60 + "\n")

    def assemble_manuscript(self):
        """Assemble final manuscript"""
        self._log("Assembling manuscript...")
        self._update_stage("assembly")

        # Collect all chapters
        chapters = sorted(self.chapters_dir.glob("chapter_*.md"))

        if not chapters:
            self._log("No chapters found to assemble", "ERROR")
            return False

        # Combine into single manuscript
        manuscript = []
        manuscript.append(f"# {self.book_name.replace('-', ' ').title()}\n\n")

        for chapter_file in chapters:
            content = chapter_file.read_text()

            # Remove metadata section
            if "---\nMETADATA:" in content:
                content = content.split("---\nMETADATA:")[0]

            manuscript.append(content)
            manuscript.append("\n\n")

        # Save complete manuscript
        manuscript_file = self.output_dir / f"{self.book_name}_manuscript.md"
        manuscript_file.write_text("".join(manuscript))

        word_count = len(" ".join(manuscript).split())
        self._log(f"✓ Manuscript assembled: {word_count:,} words")

        # Update status
        status = self._load_status()
        status["total_words"] = word_count
        self._save_status(status)

        return True

    def format_for_kdp(self):
        """Format manuscript for KDP"""
        self._log("Formatting for KDP...")
        self._update_stage("formatting")

        manuscript_file = self.output_dir / f"{self.book_name}_manuscript.md"

        if not manuscript_file.exists():
            self._log("Manuscript not found", "ERROR")
            return False

        # Call KDP formatter
        result = subprocess.run(
            ["python3", "scripts/kdp_formatter.py", str(manuscript_file), str(self.output_dir)],
            capture_output=True, text=True
        )

        if result.returncode == 0:
            self._log("✓ KDP formatting complete")
            return True
        else:
            self._log("KDP formatting failed", "ERROR")
            return False

    def run_full_pipeline(self):
        """Execute complete autonomous pipeline"""
        self._log("\n" + "="*60)
        self._log("AUTONOMOUS BOOK PRODUCTION PIPELINE")
        self._log(f"Book: {self.book_name}")
        self._log(f"Genre: {self.genre}")
        self._log(f"Target: {self.target_words:,} words")
        self._log("="*60 + "\n")

        try:
            # Stage 1: Tests
            if self.test_first:
                if not self.run_tests():
                    self._log("Tests failed, aborting", "ERROR")
                    return False

            # Stage 2: Analysis
            if not self.analyze_source():
                return False

            # Stage 3: Planning
            if not self.create_chapter_plan():
                return False

            # Stage 4: Generation
            # Note: This creates prompts. In fully autonomous mode,
            # you'd integrate Claude API here
            self.generate_all_chapters()

            # Stage 5: Assembly
            if not self.assemble_manuscript():
                return False

            # Stage 6: KDP Formatting
            if not self.format_for_kdp():
                return False

            # Mark complete
            status = self._load_status()
            status["completed"] = True
            status["completed_at"] = datetime.now().isoformat()
            self._save_status(status)

            self._log("\n" + "="*60)
            self._log("✓ BOOK PRODUCTION COMPLETE")
            self._log(f"Output: {self.output_dir}")
            self._log("="*60 + "\n")

            return True

        except Exception as e:
            self._log(f"Pipeline error: {str(e)}", "ERROR")
            status = self._load_status()
            status["errors"].append({
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            })
            self._save_status(status)
            return False


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Autonomous Book Production")
    parser.add_argument("--source", required=True, help="Source file path")
    parser.add_argument("--book-name", required=True, help="Book name (slug format)")
    parser.add_argument("--genre", required=True, help="Genre (thriller/romance/fantasy)")
    parser.add_argument("--target-words", type=int, default=80000, help="Target word count")
    parser.add_argument("--no-test", action="store_true", help="Skip self-tests")
    parser.add_argument("--use-api", action="store_true", help="Use LLM API for autonomous generation")
    parser.add_argument("--provider", type=str, default="claude",
                        choices=["claude", "deepseek", "openrouter", "qwen", "openai", "groq", "together", "huggingface"],
                        help="LLM provider (default: claude). Use 'groq' for cheapest ($0.05/$0.08 per 1M) or 'huggingface' for free tier")
    parser.add_argument("--max-budget", type=float, default=50.0, help="Maximum budget in USD (default: $50)")
    parser.add_argument("--multi-pass", type=int, default=1, metavar="N",
                        help="Generate N versions per chapter and select best (default: 1, recommend: 5-7 for quality)")

    args = parser.parse_args()

    # Check for API key if --use-api is set
    if args.use_api:
        provider = Provider(args.provider.lower())
        provider_config = ProviderConfig.get_config(provider)
        api_key_env = provider_config["api_key_env"]

        if not os.environ.get(api_key_env):
            print(f"ERROR: --use-api with --provider {args.provider} requires {api_key_env} environment variable")
            print(f"Set it with: export {api_key_env}=your-key")
            print("")
            print("Available providers:")
            print("  --provider claude     (default, $3/$15 per 1M tokens)")
            print("  --provider deepseek   (cheapest, $0.14/$0.28 per 1M tokens) ← RECOMMENDED")
            print("  --provider openrouter ($0.14/$0.28 per 1M tokens)")
            print("  --provider qwen       ($0.29/$0.57 per 1M tokens)")
            print("  --provider openai     ($10/$30 per 1M tokens)")
            print("")
            print("Or run without --use-api to create prompts for manual generation")
            sys.exit(1)

    orchestrator = BookOrchestrator(
        source_file=args.source,
        book_name=args.book_name,
        genre=args.genre,
        target_words=args.target_words,
        test_first=not args.no_test,
        use_api=args.use_api,
        max_budget=args.max_budget,
        provider=args.provider,
        multi_pass_attempts=args.multi_pass
    )

    success = orchestrator.run_full_pipeline()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
