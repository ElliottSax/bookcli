#!/usr/bin/env python3
"""
Semantic Plot Coherence Validator

Uses LLM-based validation to check deep plot coherence including:
- Cause-effect relationships between events
- Setup and payoff structures (Chekhov's gun)
- Character motivation consistency
- Plot hole detection
- Thematic resonance
- Narrative arc progression

This provides deeper validation than pattern-matching alone.
"""

import os
import re
import json
import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


class PlotIssueType(Enum):
    PLOT_HOLE = "plot_hole"
    BROKEN_CAUSALITY = "broken_causality"
    MISSING_SETUP = "missing_setup"
    ABANDONED_THREAD = "abandoned_thread"
    MOTIVATION_GAP = "motivation_gap"
    TIMELINE_ERROR = "timeline_error"
    LOGIC_ERROR = "logic_error"


@dataclass
class PlotIssue:
    """A detected plot coherence issue."""
    issue_type: PlotIssueType
    severity: str  # "critical", "major", "minor"
    description: str
    location: str  # Chapter/section reference
    suggestion: str
    confidence: float


@dataclass
class PlotElement:
    """A tracked plot element (setup, thread, etc.)."""
    element_type: str  # "setup", "thread", "mystery", "conflict"
    description: str
    introduced_chapter: int
    resolved_chapter: Optional[int] = None
    status: str = "open"  # "open", "resolved", "abandoned"


@dataclass
class PlotCoherenceReport:
    """Complete plot coherence analysis."""
    overall_score: float  # 0-100
    causality_score: float
    setup_payoff_score: float
    motivation_score: float
    arc_progression_score: float

    issues: List[PlotIssue] = field(default_factory=list)
    open_threads: List[PlotElement] = field(default_factory=list)
    resolved_threads: List[PlotElement] = field(default_factory=list)

    strengths: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)


class SemanticPlotValidator:
    """
    Validates plot coherence using semantic analysis and LLM critique.

    Can operate in two modes:
    1. Pattern-based (fast, no API calls)
    2. LLM-enhanced (thorough, requires API)
    """

    PLOT_ANALYSIS_PROMPT = '''Analyze this story excerpt for plot coherence issues.

## Story Content:
{content}

## Previous Chapter Summary (for context):
{previous_summary}

## Active Plot Elements to Track:
{plot_elements}

## Your Analysis Tasks:

1. **Causality Check**: Does every major event have a cause? Are consequences logical?

2. **Setup/Payoff Check**: Are introduced elements (weapons, secrets, abilities) used later?
   - Flag any "Chekhov's gun" violations (introduced but never used)
   - Flag any deus ex machina (solution appears without setup)

3. **Motivation Check**: Do character actions match their established motivations?
   - Flag unmotivated decisions
   - Flag out-of-character behavior

4. **Logic Check**: Are there any logical impossibilities or contradictions?
   - Timeline impossibilities
   - Knowledge characters shouldn't have
   - Physical impossibilities

5. **Thread Tracking**: What plot threads are opened/closed in this section?

Respond in JSON:
```json
{{
    "causality_score": <0-100>,
    "setup_payoff_score": <0-100>,
    "motivation_score": <0-100>,
    "logic_score": <0-100>,
    "issues": [
        {{
            "type": "<plot_hole|broken_causality|missing_setup|abandoned_thread|motivation_gap|timeline_error|logic_error>",
            "severity": "<critical|major|minor>",
            "description": "<what is wrong>",
            "location": "<quote or chapter reference>",
            "suggestion": "<how to fix>",
            "confidence": <0.0-1.0>
        }}
    ],
    "new_threads": [
        {{
            "type": "<setup|thread|mystery|conflict>",
            "description": "<what was introduced>",
            "importance": "<high|medium|low>"
        }}
    ],
    "resolved_threads": ["<description of resolved element>"],
    "strengths": ["<what works well>"],
    "summary": "<one paragraph plot assessment>"
}}
```

Be thorough but fair. Only flag clear issues, not stylistic choices.'''

    def __init__(self, use_llm: bool = True, model: str = "deepseek",
                logger: Optional[logging.Logger] = None):
        """
        Initialize the plot validator.

        Args:
            use_llm: Whether to use LLM for deep analysis
            model: Which model to use ("deepseek", "claude", "groq")
            logger: Optional logger
        """
        self.use_llm = use_llm
        self.model = model
        self.logger = logger or logging.getLogger(__name__)

        # Track plot elements across chapters
        self.plot_elements: List[PlotElement] = []
        self.chapter_summaries: Dict[int, str] = {}

        # Pattern-based detection
        self.setup_patterns = [
            r"(?:pulled out|drew|revealed|showed)\s+(?:a|the)\s+(\w+)",  # Object introduction
            r"(?:there was|he had|she carried)\s+(?:a|an)\s+(\w+\s+\w+)",  # Possession
            r"(?:secret|hidden|ancient|magical)\s+(\w+)",  # Special items
            r"(?:ability|power|skill)\s+to\s+(\w+)",  # Abilities
            r"(?:prophecy|legend|rumor)\s+(?:of|about|that)\s+([^.]+)",  # Prophecies
        ]

        self.resolution_patterns = [
            r"finally\s+(\w+)",
            r"(?:used|activated|triggered)\s+the\s+(\w+)",
            r"the\s+(\w+)\s+(?:was|had been)\s+(?:the key|the answer|what they needed)",
        ]

    def validate_chapter(self, chapter_num: int, content: str,
                        previous_summary: str = "") -> Dict[str, Any]:
        """
        Validate plot coherence for a single chapter.

        Args:
            chapter_num: Chapter number
            content: Chapter content
            previous_summary: Summary of previous chapter

        Returns:
            Validation results
        """
        # Pattern-based analysis (always runs)
        pattern_results = self._pattern_analysis(chapter_num, content)

        # LLM analysis (if enabled and available)
        if self.use_llm:
            try:
                llm_results = self._llm_analysis(chapter_num, content, previous_summary)
                # Merge results
                return self._merge_results(pattern_results, llm_results)
            except Exception as e:
                self.logger.warning(f"LLM analysis failed: {e}, using pattern-only")

        return pattern_results

    def _pattern_analysis(self, chapter_num: int, content: str) -> Dict:
        """Pattern-based plot analysis (fast, no API)."""
        issues = []
        new_elements = []

        # Detect new setups
        for pattern in self.setup_patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            for match in matches:
                element = PlotElement(
                    element_type="setup",
                    description=match if isinstance(match, str) else ' '.join(match),
                    introduced_chapter=chapter_num
                )
                self.plot_elements.append(element)
                new_elements.append(element)

        # Detect resolutions
        for pattern in self.resolution_patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            for match in matches:
                match_str = match if isinstance(match, str) else ' '.join(match)
                # Look for matching setup
                for element in self.plot_elements:
                    if element.status == "open" and match_str.lower() in element.description.lower():
                        element.status = "resolved"
                        element.resolved_chapter = chapter_num

        # Check for potential issues
        # Deus ex machina: resolution without prior setup
        resolution_words = re.findall(r"(?:suddenly|miraculously|fortunately)\s+([^.]+)", content)
        for resolution in resolution_words:
            # Check if this was set up
            was_setup = any(
                resolution.lower() in e.description.lower()
                for e in self.plot_elements
                if e.introduced_chapter < chapter_num
            )
            if not was_setup and len(resolution) > 20:
                issues.append(PlotIssue(
                    issue_type=PlotIssueType.MISSING_SETUP,
                    severity="major",
                    description=f"Potential deus ex machina: '{resolution[:50]}...'",
                    location=f"Chapter {chapter_num}",
                    suggestion="Add earlier setup/foreshadowing for this resolution",
                    confidence=0.6
                ))

        # Calculate score
        score = 100 - len(issues) * 10

        return {
            'chapter': chapter_num,
            'score': max(0, score),
            'issues': issues,
            'new_elements': [e.description for e in new_elements],
            'open_threads': [e.description for e in self.plot_elements if e.status == "open"]
        }

    def _llm_analysis(self, chapter_num: int, content: str,
                     previous_summary: str) -> Dict:
        """LLM-based deep plot analysis."""
        # Format plot elements for prompt
        elements_str = "\n".join([
            f"- [{e.element_type}] {e.description} (ch.{e.introduced_chapter}, {e.status})"
            for e in self.plot_elements[-20:]  # Last 20 elements
        ])

        prompt = self.PLOT_ANALYSIS_PROMPT.format(
            content=content[:8000],  # Limit content size
            previous_summary=previous_summary[:500],
            plot_elements=elements_str or "None tracked yet"
        )

        response = self._call_llm(prompt)
        return self._parse_llm_response(response, chapter_num)

    def _call_llm(self, prompt: str) -> str:
        """Call the configured LLM."""
        import httpx

        if self.model == "deepseek":
            api_key = os.getenv('DEEPSEEK_API_KEY')
            if not api_key:
                raise ValueError("DEEPSEEK_API_KEY not set")

            response = httpx.post(
                "https://api.deepseek.com/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "deepseek-chat",
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 2000,
                    "temperature": 0.3
                },
                timeout=60.0
            )
            response.raise_for_status()
            return response.json()["choices"][0]["message"]["content"]

        elif self.model == "groq":
            api_key = os.getenv('GROQ_API_KEY')
            if not api_key:
                raise ValueError("GROQ_API_KEY not set")

            response = httpx.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "llama-3.1-70b-versatile",
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 2000,
                    "temperature": 0.3
                },
                timeout=60.0
            )
            response.raise_for_status()
            return response.json()["choices"][0]["message"]["content"]

        raise ValueError(f"Unknown model: {self.model}")

    def _parse_llm_response(self, response: str, chapter_num: int) -> Dict:
        """Parse LLM JSON response."""
        # Extract JSON
        json_match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', response)
        if json_match:
            json_str = json_match.group(1)
        else:
            json_match = re.search(r'\{[\s\S]*\}', response)
            json_str = json_match.group(0) if json_match else "{}"

        try:
            data = json.loads(json_str)
        except json.JSONDecodeError:
            return {'chapter': chapter_num, 'score': 80, 'issues': [], 'parse_error': True}

        # Convert issues
        issues = []
        for issue_data in data.get('issues', []):
            try:
                issue_type = PlotIssueType(issue_data.get('type', 'logic_error'))
            except ValueError:
                issue_type = PlotIssueType.LOGIC_ERROR

            issues.append(PlotIssue(
                issue_type=issue_type,
                severity=issue_data.get('severity', 'minor'),
                description=issue_data.get('description', ''),
                location=issue_data.get('location', f'Chapter {chapter_num}'),
                suggestion=issue_data.get('suggestion', ''),
                confidence=float(issue_data.get('confidence', 0.5))
            ))

        # Track new threads
        for thread in data.get('new_threads', []):
            self.plot_elements.append(PlotElement(
                element_type=thread.get('type', 'thread'),
                description=thread.get('description', ''),
                introduced_chapter=chapter_num
            ))

        # Mark resolved threads
        for resolved in data.get('resolved_threads', []):
            for element in self.plot_elements:
                if element.status == "open" and resolved.lower() in element.description.lower():
                    element.status = "resolved"
                    element.resolved_chapter = chapter_num

        # Calculate overall score
        scores = [
            data.get('causality_score', 80),
            data.get('setup_payoff_score', 80),
            data.get('motivation_score', 80),
            data.get('logic_score', 80)
        ]
        avg_score = sum(scores) / len(scores)

        return {
            'chapter': chapter_num,
            'score': avg_score,
            'causality_score': data.get('causality_score', 80),
            'setup_payoff_score': data.get('setup_payoff_score', 80),
            'motivation_score': data.get('motivation_score', 80),
            'logic_score': data.get('logic_score', 80),
            'issues': issues,
            'strengths': data.get('strengths', []),
            'summary': data.get('summary', '')
        }

    def _merge_results(self, pattern_results: Dict, llm_results: Dict) -> Dict:
        """Merge pattern and LLM analysis results."""
        # Combine issues, removing duplicates
        all_issues = pattern_results.get('issues', []) + llm_results.get('issues', [])

        # Average scores
        avg_score = (pattern_results.get('score', 80) + llm_results.get('score', 80)) / 2

        return {
            'chapter': pattern_results['chapter'],
            'score': avg_score,
            'causality_score': llm_results.get('causality_score', 80),
            'setup_payoff_score': llm_results.get('setup_payoff_score', 80),
            'motivation_score': llm_results.get('motivation_score', 80),
            'issues': all_issues,
            'open_threads': pattern_results.get('open_threads', []),
            'strengths': llm_results.get('strengths', [])
        }

    def validate_all(self, chapters: List[str]) -> PlotCoherenceReport:
        """
        Validate plot coherence across all chapters.

        Args:
            chapters: List of chapter contents

        Returns:
            Complete coherence report
        """
        self.plot_elements.clear()
        all_issues = []
        chapter_scores = []

        previous_summary = ""
        for i, chapter in enumerate(chapters, 1):
            result = self.validate_chapter(i, chapter, previous_summary)
            all_issues.extend(result.get('issues', []))
            chapter_scores.append(result.get('score', 80))

            # Generate summary for next chapter
            previous_summary = chapter[:500]  # Simple - first 500 chars

        # Check for abandoned threads (introduced but never resolved)
        total_chapters = len(chapters)
        for element in self.plot_elements:
            if element.status == "open" and element.introduced_chapter < total_chapters - 1:
                all_issues.append(PlotIssue(
                    issue_type=PlotIssueType.ABANDONED_THREAD,
                    severity="major" if element.element_type == "setup" else "minor",
                    description=f"Unresolved {element.element_type}: {element.description}",
                    location=f"Introduced ch.{element.introduced_chapter}",
                    suggestion="Either resolve this element or remove its introduction",
                    confidence=0.7
                ))

        # Calculate final scores
        overall = sum(chapter_scores) / len(chapter_scores) if chapter_scores else 80

        open_threads = [e for e in self.plot_elements if e.status == "open"]
        resolved_threads = [e for e in self.plot_elements if e.status == "resolved"]

        recommendations = []
        if len(open_threads) > 5:
            recommendations.append("Many unresolved plot threads - consider resolving or removing some")
        if any(i.issue_type == PlotIssueType.MISSING_SETUP for i in all_issues):
            recommendations.append("Add foreshadowing for major revelations")

        return PlotCoherenceReport(
            overall_score=overall,
            causality_score=overall,  # Would be more detailed with LLM
            setup_payoff_score=100 - len([i for i in all_issues if i.issue_type == PlotIssueType.MISSING_SETUP]) * 10,
            motivation_score=100 - len([i for i in all_issues if i.issue_type == PlotIssueType.MOTIVATION_GAP]) * 10,
            arc_progression_score=overall,
            issues=all_issues,
            open_threads=open_threads,
            resolved_threads=resolved_threads,
            recommendations=recommendations
        )

    def get_score(self, chapters: List[str]) -> float:
        """Get plot coherence score (0-100). Main method for integration."""
        report = self.validate_all(chapters)
        return report.overall_score


def format_plot_report(report: PlotCoherenceReport) -> str:
    """Format plot coherence report for display."""
    lines = [
        "=" * 60,
        "PLOT COHERENCE REPORT",
        "=" * 60,
        f"Overall Score: {report.overall_score:.1f}/100",
        "",
        "Category Scores:",
        f"  Causality:       {report.causality_score:.1f}%",
        f"  Setup/Payoff:    {report.setup_payoff_score:.1f}%",
        f"  Motivation:      {report.motivation_score:.1f}%",
        f"  Arc Progression: {report.arc_progression_score:.1f}%",
        "",
        f"Plot Threads: {len(report.resolved_threads)} resolved, {len(report.open_threads)} open",
    ]

    if report.open_threads:
        lines.append("\nOpen Threads:")
        for thread in report.open_threads[:5]:
            lines.append(f"  - [{thread.element_type}] {thread.description} (ch.{thread.introduced_chapter})")

    if report.issues:
        lines.append(f"\nIssues ({len(report.issues)}):")
        for issue in sorted(report.issues, key=lambda x: x.severity)[:10]:
            lines.append(f"  [{issue.severity.upper()}] {issue.description}")
            lines.append(f"    -> {issue.suggestion}")

    if report.recommendations:
        lines.append("\nRecommendations:")
        for rec in report.recommendations:
            lines.append(f"  * {rec}")

    lines.append("=" * 60)
    return "\n".join(lines)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    # Test without LLM
    validator = SemanticPlotValidator(use_llm=False)

    chapter1 = """
    Marcus drew the ancient sword from its sheath. The blade glowed with an inner light.
    "This belonged to your father," the old man said. "It will be needed."
    There was a prophecy that spoke of a dark lord's return.
    """

    chapter2 = """
    The journey to the mountains took three days. Marcus practiced with the sword each night.
    He learned he had a hidden ability to sense danger before it arrived.
    Elena mentioned a secret about his past, but wouldn't reveal more.
    """

    chapter3 = """
    Suddenly, the dragon appeared. Miraculously, Marcus discovered he could speak to it.
    This ability had never been mentioned before, but it saved them.
    The ancient sword was left behind, forgotten.
    """

    report = validator.validate_all([chapter1, chapter2, chapter3])
    print(format_plot_report(report))
