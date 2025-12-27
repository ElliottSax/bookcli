#!/usr/bin/env python3
"""
Enhanced Quality Pipeline

Integrates all quality enhancement components:
1. Repetition Post-Processor (AI-ism removal)
2. Content Critic (different-model critique)
3. Narrative Coherence Tracker (cross-chapter consistency)
4. Character Consistency Validator (character tracking)
5. Semantic Plot Validator (plot coherence)
6. DOC Outline Controller (hierarchical outline control)
7. SCORE State Tracker (dynamic state tracking)

This provides a unified interface for quality validation and enhancement.
"""

import logging
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field

# Import all quality components
try:
    from repetition_post_processor import RepetitionPostProcessor, clean_fiction_content
except ImportError:
    RepetitionPostProcessor = None

try:
    from content_critic import ContentCritic, CriticReport
except ImportError:
    ContentCritic = None

try:
    from narrative_coherence_tracker import NarrativeCoherenceTracker, CoherenceReport
except ImportError:
    NarrativeCoherenceTracker = None

try:
    from character_consistency_validator import CharacterConsistencyValidator, ConsistencyReport
except ImportError:
    CharacterConsistencyValidator = None

try:
    from semantic_plot_validator import SemanticPlotValidator, PlotCoherenceReport
except ImportError:
    SemanticPlotValidator = None

try:
    from doc_outline_controller import DOCOutlineController, BookOutline
except ImportError:
    DOCOutlineController = None

try:
    from score_state_tracker import SCOREStateTracker, ContextSummary
except ImportError:
    SCOREStateTracker = None


@dataclass
class QualityGate:
    """Definition of a quality gate."""
    name: str
    threshold: float
    weight: float
    enabled: bool = True


@dataclass
class EnhancedQualityReport:
    """Comprehensive quality report from the enhanced pipeline."""
    overall_score: float
    passed: bool
    publication_ready: bool

    # Component scores
    repetition_score: float = 100.0
    critic_score: float = 100.0
    coherence_score: float = 100.0
    character_score: float = 100.0
    plot_score: float = 100.0
    outline_adherence: float = 100.0

    # Detailed reports
    repetition_stats: Dict[str, Any] = field(default_factory=dict)
    critic_issues: List[str] = field(default_factory=list)
    coherence_issues: List[str] = field(default_factory=list)
    character_issues: List[str] = field(default_factory=list)
    plot_issues: List[str] = field(default_factory=list)

    # Recommendations
    recommendations: List[str] = field(default_factory=list)
    critical_issues: List[str] = field(default_factory=list)

    # Processing info
    components_used: List[str] = field(default_factory=list)


class EnhancedQualityPipeline:
    """
    Unified quality pipeline integrating all enhancement components.

    Usage:
        pipeline = EnhancedQualityPipeline()
        pipeline.initialize(premise="...", genre="fantasy", num_chapters=12)

        # For each chapter during generation:
        context = pipeline.get_generation_context(chapter_num)
        # ... generate chapter using context ...
        cleaned = pipeline.post_process(chapter_num, content)
        report = pipeline.validate(chapter_num, cleaned)

        # After all chapters:
        final_report = pipeline.validate_complete(all_chapters)
    """

    # Quality gates with thresholds and weights
    DEFAULT_GATES = [
        QualityGate("repetition", 80.0, 0.10),
        QualityGate("character_consistency", 85.0, 0.20),
        QualityGate("plot_coherence", 80.0, 0.20),
        QualityGate("narrative_coherence", 80.0, 0.15),
        QualityGate("outline_adherence", 75.0, 0.15),
        QualityGate("critic_score", 70.0, 0.20),
    ]

    def __init__(self,
                 use_llm_critic: bool = True,
                 critic_model: str = "deepseek",
                 logger: Optional[logging.Logger] = None):
        """
        Initialize the enhanced quality pipeline.

        Args:
            use_llm_critic: Whether to use LLM-based critic (requires API)
            critic_model: Model to use for critic ("deepseek", "groq", "claude")
            logger: Optional logger
        """
        self.logger = logger or logging.getLogger(__name__)
        self.use_llm_critic = use_llm_critic
        self.critic_model = critic_model

        self.gates = self.DEFAULT_GATES.copy()
        self.initialized = False

        # Initialize components
        self._init_components()

    def _init_components(self):
        """Initialize all quality components."""
        self.components = {}

        # Repetition post-processor
        if RepetitionPostProcessor:
            self.components["repetition"] = RepetitionPostProcessor(self.logger)
            self.logger.info("Initialized: RepetitionPostProcessor")

        # Content critic
        if ContentCritic and self.use_llm_critic:
            self.components["critic"] = ContentCritic(
                critic_model=self.critic_model,
                logger=self.logger
            )
            self.logger.info(f"Initialized: ContentCritic ({self.critic_model})")

        # Narrative coherence tracker
        if NarrativeCoherenceTracker:
            self.components["coherence"] = NarrativeCoherenceTracker(self.logger)
            self.logger.info("Initialized: NarrativeCoherenceTracker")

        # Character consistency validator
        if CharacterConsistencyValidator:
            self.components["character"] = CharacterConsistencyValidator(self.logger)
            self.logger.info("Initialized: CharacterConsistencyValidator")

        # Semantic plot validator
        if SemanticPlotValidator:
            self.components["plot"] = SemanticPlotValidator(
                use_llm=self.use_llm_critic,
                model=self.critic_model,
                logger=self.logger
            )
            self.logger.info("Initialized: SemanticPlotValidator")

        # DOC outline controller
        if DOCOutlineController:
            self.components["outline"] = DOCOutlineController(self.logger)
            self.logger.info("Initialized: DOCOutlineController")

        # SCORE state tracker
        if SCOREStateTracker:
            self.components["state"] = SCOREStateTracker(self.logger)
            self.logger.info("Initialized: SCOREStateTracker")

    def initialize(self, premise: str, genre: str, num_chapters: int,
                  themes: List[str] = None) -> Dict[str, Any]:
        """
        Initialize the pipeline for a new book.

        Args:
            premise: Story premise
            genre: Genre (fantasy, thriller, romance, etc.)
            num_chapters: Target number of chapters
            themes: Key themes

        Returns:
            Initialization summary
        """
        self.logger.info(f"Initializing pipeline for {num_chapters}-chapter {genre}")

        results = {"components_initialized": []}

        # Create book outline
        if "outline" in self.components:
            outline = self.components["outline"].create_outline(
                premise=premise,
                genre=genre,
                num_chapters=num_chapters,
                themes=themes
            )
            results["outline_created"] = True
            results["components_initialized"].append("outline")

        # Initialize state tracker
        if "state" in self.components:
            # State tracker initializes as chapters are processed
            results["components_initialized"].append("state")

        # Initialize other trackers
        for name in ["coherence", "character", "plot"]:
            if name in self.components:
                results["components_initialized"].append(name)

        self.initialized = True
        return results

    def get_generation_context(self, chapter_num: int) -> Dict[str, Any]:
        """
        Get comprehensive context for generating a chapter.

        Combines DOC outline guidance with SCORE state tracking.
        """
        context = {
            "chapter": chapter_num,
            "outline_guidance": "",
            "state_context": "",
            "coherence_context": "",
        }

        # Get outline guidance
        if "outline" in self.components:
            context["outline_guidance"] = self.components["outline"].get_generation_prompt(chapter_num)

        # Get state context
        if "state" in self.components:
            state_context = self.components["state"].get_context_for_generation(chapter_num)
            context["state_context"] = self.components["state"].format_context_prompt(state_context)

        # Get coherence context
        if "coherence" in self.components:
            coh_context = self.components["coherence"].get_context_for_chapter(chapter_num)
            context["coherence_context"] = str(coh_context)

        return context

    def post_process(self, chapter_num: int, content: str) -> Tuple[str, Dict]:
        """
        Post-process generated content to clean up AI artifacts.

        Args:
            chapter_num: Chapter number
            content: Generated content

        Returns:
            Tuple of (cleaned_content, stats)
        """
        stats = {}

        # Apply repetition post-processor
        if "repetition" in self.components:
            content, rep_stats = self.components["repetition"].process(content)
            stats["repetition"] = rep_stats

        return content, stats

    def track_chapter(self, chapter_num: int, content: str) -> Dict[str, Any]:
        """
        Track a chapter through all tracking systems.

        Args:
            chapter_num: Chapter number
            content: Chapter content

        Returns:
            Tracking results from all systems
        """
        results = {}

        # Narrative coherence tracking
        if "coherence" in self.components:
            results["coherence"] = self.components["coherence"].track_chapter(
                f"Chapter {chapter_num}", content, chapter_num
            )

        # Character tracking
        if "character" in self.components:
            results["character"] = self.components["character"].analyze_chapter(
                chapter_num, content
            )

        # Plot tracking
        if "plot" in self.components:
            prev_summary = ""
            if "coherence" in self.components:
                prev_summary = self.components["coherence"].chapter_summaries.get(
                    chapter_num - 1, ""
                )
            results["plot"] = self.components["plot"].validate_chapter(
                chapter_num, content, prev_summary
            )

        # State tracking
        if "state" in self.components:
            results["state"] = self.components["state"].process_chapter(
                chapter_num, content
            )

        return results

    def validate_chapter(self, chapter_num: int, content: str) -> EnhancedQualityReport:
        """
        Validate a single chapter through all quality gates.

        Args:
            chapter_num: Chapter number
            content: Chapter content

        Returns:
            Comprehensive quality report
        """
        scores = {}
        issues = {}
        components_used = []

        # Track the chapter first
        tracking_results = self.track_chapter(chapter_num, content)

        # Check repetition
        if "repetition" in self.components:
            cleaned, stats = self.components["repetition"].process(content)
            ai_isms = stats.get("ai_isms_replaced", 0)
            duplicates = stats.get("duplicate_sentences_removed", 0)
            # Score: penalize for AI-isms found
            scores["repetition"] = max(0, 100 - ai_isms * 2 - duplicates * 5)
            issues["repetition"] = stats
            components_used.append("repetition")

        # Check character consistency
        if "character" in self.components:
            char_result = tracking_results.get("character", {})
            char_issues = char_result.get("issues", [])
            scores["character"] = max(0, 100 - len(char_issues) * 10)
            issues["character"] = [str(i) for i in char_issues[:5]]
            components_used.append("character")

        # Check plot coherence
        if "plot" in self.components:
            plot_result = tracking_results.get("plot", {})
            scores["plot"] = plot_result.get("score", 80)
            plot_issues = plot_result.get("issues", [])
            issues["plot"] = [str(i.description) for i in plot_issues[:5] if hasattr(i, 'description')]
            components_used.append("plot")

        # Check outline adherence
        if "outline" in self.components:
            outline_scores = self.components["outline"].score_coherence(chapter_num, content)
            scores["outline"] = outline_scores.get("overall", 80)
            components_used.append("outline")

        # LLM critic (expensive, run last)
        if "critic" in self.components and self.use_llm_critic:
            try:
                critic_report = self.components["critic"].critique(content)
                scores["critic"] = critic_report.overall_quality
                issues["critic"] = [
                    f"{i.severity}: {i.description}"
                    for i in critic_report.issues[:5]
                ]
                components_used.append("critic")
            except Exception as e:
                self.logger.warning(f"Critic failed: {e}")
                scores["critic"] = 80  # Default if fails

        # Calculate overall score
        overall = self._calculate_overall_score(scores)
        passed = self._check_gates(scores)

        # Generate recommendations
        recommendations = self._generate_recommendations(scores, issues)
        critical = [i for category in issues.values() for i in (category if isinstance(category, list) else [])]

        return EnhancedQualityReport(
            overall_score=overall,
            passed=passed,
            publication_ready=passed and overall >= 85,
            repetition_score=scores.get("repetition", 100),
            critic_score=scores.get("critic", 100),
            coherence_score=scores.get("coherence", 100),
            character_score=scores.get("character", 100),
            plot_score=scores.get("plot", 100),
            outline_adherence=scores.get("outline", 100),
            repetition_stats=issues.get("repetition", {}),
            critic_issues=issues.get("critic", []),
            coherence_issues=issues.get("coherence", []),
            character_issues=issues.get("character", []),
            plot_issues=issues.get("plot", []),
            recommendations=recommendations,
            critical_issues=critical[:10],
            components_used=components_used
        )

    def validate_complete(self, chapters: List[str]) -> EnhancedQualityReport:
        """
        Validate the complete book after all chapters are generated.

        Args:
            chapters: List of all chapter contents

        Returns:
            Comprehensive quality report for entire book
        """
        self.logger.info(f"Validating complete book ({len(chapters)} chapters)")

        all_scores = []
        all_issues = {
            "repetition": [],
            "character": [],
            "plot": [],
            "coherence": []
        }

        # Validate each chapter
        for i, chapter in enumerate(chapters, 1):
            report = self.validate_chapter(i, chapter)
            all_scores.append(report.overall_score)

            # Collect issues
            all_issues["character"].extend(report.character_issues)
            all_issues["plot"].extend(report.plot_issues)

        # Get full-book coherence analysis
        if "coherence" in self.components:
            coherence_report = self.components["coherence"].analyze_coherence()
            coherence_score = coherence_report.overall_score
        else:
            coherence_score = 85

        # Get full character consistency
        if "character" in self.components:
            char_report = self.components["character"].analyze_all(chapters)
            char_score = char_report.overall_score
        else:
            char_score = 85

        # Get full plot coherence
        if "plot" in self.components:
            plot_report = self.components["plot"].validate_all(chapters)
            plot_score = plot_report.overall_score
        else:
            plot_score = 85

        # Calculate overall
        avg_chapter_score = sum(all_scores) / len(all_scores) if all_scores else 80
        overall = (avg_chapter_score * 0.5 + coherence_score * 0.2 +
                  char_score * 0.15 + plot_score * 0.15)

        passed = overall >= 80
        publication_ready = overall >= 85 and not any(
            "critical" in str(i).lower() for issues in all_issues.values() for i in issues
        )

        recommendations = []
        if coherence_score < 80:
            recommendations.append("Review narrative coherence across chapters")
        if char_score < 85:
            recommendations.append("Check character consistency (physical descriptions, relationships)")
        if plot_score < 80:
            recommendations.append("Address plot coherence issues and unresolved threads")

        return EnhancedQualityReport(
            overall_score=overall,
            passed=passed,
            publication_ready=publication_ready,
            coherence_score=coherence_score,
            character_score=char_score,
            plot_score=plot_score,
            character_issues=all_issues["character"][:10],
            plot_issues=all_issues["plot"][:10],
            coherence_issues=all_issues["coherence"][:10],
            recommendations=recommendations,
            components_used=list(self.components.keys())
        )

    def _calculate_overall_score(self, scores: Dict[str, float]) -> float:
        """Calculate weighted overall score."""
        if not scores:
            return 80.0

        total_weight = 0
        weighted_sum = 0

        for gate in self.gates:
            if gate.name in scores and gate.enabled:
                weighted_sum += scores[gate.name] * gate.weight
                total_weight += gate.weight

        if total_weight == 0:
            return sum(scores.values()) / len(scores)

        return weighted_sum / total_weight

    def _check_gates(self, scores: Dict[str, float]) -> bool:
        """Check if all quality gates pass."""
        for gate in self.gates:
            if gate.enabled and gate.name in scores:
                if scores[gate.name] < gate.threshold:
                    return False
        return True

    def _generate_recommendations(self, scores: Dict[str, float],
                                  issues: Dict[str, Any]) -> List[str]:
        """Generate improvement recommendations."""
        recommendations = []

        for gate in self.gates:
            if gate.name in scores and scores[gate.name] < gate.threshold:
                if gate.name == "repetition":
                    recommendations.append("Reduce AI-isms and repetitive phrases")
                elif gate.name == "character":
                    recommendations.append("Fix character consistency issues")
                elif gate.name == "plot":
                    recommendations.append("Address plot coherence problems")
                elif gate.name == "outline":
                    recommendations.append("Better adhere to chapter outline requirements")
                elif gate.name == "critic":
                    recommendations.append("Address issues identified by critic")

        return recommendations

    def get_improvement_suggestions(self, report: EnhancedQualityReport) -> str:
        """Get formatted improvement suggestions from a report."""
        lines = [
            "## Quality Improvement Suggestions",
            "",
            f"Overall Score: {report.overall_score:.1f}/100",
            f"Status: {'PASSED' if report.passed else 'NEEDS WORK'}",
            ""
        ]

        if report.critical_issues:
            lines.append("### Critical Issues (fix first):")
            for issue in report.critical_issues[:5]:
                lines.append(f"- {issue}")
            lines.append("")

        if report.recommendations:
            lines.append("### Recommendations:")
            for rec in report.recommendations:
                lines.append(f"- {rec}")
            lines.append("")

        lines.append("### Score Breakdown:")
        lines.append(f"- Repetition: {report.repetition_score:.0f}%")
        lines.append(f"- Character Consistency: {report.character_score:.0f}%")
        lines.append(f"- Plot Coherence: {report.plot_score:.0f}%")
        lines.append(f"- Outline Adherence: {report.outline_adherence:.0f}%")
        if report.critic_score < 100:
            lines.append(f"- Critic Score: {report.critic_score:.0f}%")

        return "\n".join(lines)


def create_quality_pipeline(use_llm: bool = True,
                           critic_model: str = "deepseek") -> EnhancedQualityPipeline:
    """Factory function to create a quality pipeline."""
    return EnhancedQualityPipeline(
        use_llm_critic=use_llm,
        critic_model=critic_model
    )


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    # Demo usage
    pipeline = EnhancedQualityPipeline(use_llm_critic=False)

    # Initialize for a book
    pipeline.initialize(
        premise="A young wizard discovers forbidden magic",
        genre="fantasy",
        num_chapters=12,
        themes=["power", "sacrifice"]
    )

    # Get context for chapter 1
    context = pipeline.get_generation_context(1)
    print("Generation Context for Chapter 1:")
    print(context["outline_guidance"][:500])

    # Simulate validating a chapter
    sample_chapter = """
    In that single moment, time seemed to stand still. Elena felt a deep sense of dread wash
    over her, threatening to consume every fiber of her being. Her blue eyes scanned the room
    as she leveraged her training to remain calm.

    "We need to move," Marcus said, his green eyes - wait, they had been blue before - meeting hers.

    Elena nodded, embarking on what would be their most dangerous journey yet.
    """

    # Post-process
    cleaned, stats = pipeline.post_process(1, sample_chapter)
    print("\nPost-processing stats:", stats)

    # Validate
    report = pipeline.validate_chapter(1, cleaned)
    print("\n" + "=" * 60)
    print(pipeline.get_improvement_suggestions(report))
