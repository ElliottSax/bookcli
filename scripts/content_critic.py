#!/usr/bin/env python3
"""
Content Critic - Uses a DIFFERENT model to review generated fiction.

This breaks the self-bias problem by having Model A generate and Model B critique.
Research shows this is more effective than self-critique.

Adapted for fiction/novel generation with fiction-specific quality criteria.
"""

import os
import re
import json
import logging
from typing import Dict, List, Optional
from dataclasses import dataclass, field
from enum import Enum

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


class CriticSeverity(Enum):
    """Severity of issues found by critic."""
    CRITICAL = "critical"   # Must fix before publishing
    MAJOR = "major"         # Should fix - significantly impacts quality
    MINOR = "minor"         # Nice to fix - small improvements
    SUGGESTION = "suggestion"  # Optional enhancement


@dataclass
class CriticIssue:
    """A single issue identified by the critic."""
    severity: CriticSeverity
    category: str           # e.g., "pacing", "dialogue", "character", "prose"
    description: str        # What's wrong
    location: str           # Quote or section reference
    suggestion: str         # How to fix it
    confidence: float       # 0.0-1.0


@dataclass
class CriticReport:
    """Complete critique report for fiction."""
    overall_quality: int    # 0-100 score
    publishable: bool       # Is this ready to publish?
    summary: str            # One paragraph assessment
    issues: List[CriticIssue] = field(default_factory=list)
    strengths: List[str] = field(default_factory=list)

    # Fiction-specific assessments
    pacing_assessment: str = ""
    dialogue_assessment: str = ""
    character_assessment: str = ""
    prose_assessment: str = ""
    tension_assessment: str = ""

    raw_response: str = ""


class ContentCritic:
    """
    Uses a different AI model to critique generated fiction.

    Key insight: Self-critique fails because models have blind spots.
    Using a different model breaks this cycle.
    """

    FICTION_CRITIQUE_PROMPT = '''You are a professional fiction editor reviewing a chapter. Be BRUTALLY HONEST.

Your job is to find EVERY problem. Do NOT be polite or encouraging. If something is wrong, say it clearly.

## Chapter to Review:
{content}

## Quality Requirements for Fiction:
- Word count: 1500-2500 words per chapter (CRITICAL)
- Show don't tell: Actions and sensory details, not emotional summaries
- No AI-isms: "journey", "leverage", "delve", "heart pounded against chest", etc.
- Physical grounding: Emotions shown through body sensations (pulse, breath, muscles)
- Obsessive details: Specific measurements, counts, precise observations
- Natural dialogue: Distinct character voices, subtext, no exposition dumps
- Pacing: Varied sentence length, tension building, proper scene structure
- Character consistency: Actions match established personality
- No purple prose: "time stood still", "every fiber of being", etc.

## Your Task:
Analyze this fiction and provide a critique in JSON format:

```json
{{
    "overall_quality": <0-100 score>,
    "publishable": <true/false>,
    "summary": "<one paragraph honest assessment>",
    "pacing_assessment": "<rhythm, tension, scene structure>",
    "dialogue_assessment": "<naturalness, subtext, character voice>",
    "character_assessment": "<consistency, depth, motivation>",
    "prose_assessment": "<style, AI-isms, purple prose>",
    "tension_assessment": "<stakes, conflict, reader engagement>",
    "strengths": ["<strength 1>", "<strength 2>"],
    "issues": [
        {{
            "severity": "<critical/major/minor/suggestion>",
            "category": "<pacing/dialogue/character/prose/tension/continuity>",
            "description": "<what is wrong>",
            "location": "<quote the problematic text>",
            "suggestion": "<specific fix>",
            "confidence": <0.0-1.0>
        }}
    ]
}}
```

BE SPECIFIC. Quote exact problematic text. Don't say "some dialogue" - say which line.

CRITICAL issues:
- Chapter too short (<1500 words)
- Excessive telling instead of showing
- Major character inconsistencies
- AI-ism saturation (>5 instances)

Respond ONLY with the JSON.'''

    def __init__(self, critic_model: str = "deepseek", logger: Optional[logging.Logger] = None):
        """
        Initialize the content critic.

        Args:
            critic_model: Model to use for criticism ("deepseek", "claude", "gemini", "groq")
                         Default is "deepseek" ($0.14/M tokens - very cheap)
            logger: Optional logger instance
        """
        self.critic_model = critic_model
        self.logger = logger or logging.getLogger(__name__)
        self._client = None

    def _get_client(self):
        """Get the appropriate API client."""
        if self._client is not None:
            return self._client

        if self.critic_model == "claude":
            self._client = self._init_claude()
        elif self.critic_model == "deepseek":
            self._client = self._init_deepseek()
        elif self.critic_model == "gemini":
            self._client = self._init_gemini()
        elif self.critic_model == "groq":
            self._client = self._init_groq()
        else:
            self._client = self._init_deepseek()

        return self._client

    def _init_claude(self):
        """Initialize Claude client."""
        try:
            import anthropic
            api_key = os.getenv('ANTHROPIC_API_KEY')
            if not api_key:
                raise ValueError("ANTHROPIC_API_KEY not set")
            return {"type": "claude", "client": anthropic.Anthropic(api_key=api_key)}
        except Exception as e:
            self.logger.warning(f"Claude init failed: {e}, falling back to DeepSeek")
            return self._init_deepseek()

    def _init_deepseek(self):
        """Initialize DeepSeek client (OpenAI-compatible, very cheap)."""
        try:
            api_key = os.getenv('DEEPSEEK_API_KEY')
            if not api_key:
                raise ValueError("DEEPSEEK_API_KEY not set")
            return {"type": "deepseek", "api_key": api_key}
        except Exception as e:
            self.logger.error(f"DeepSeek init failed: {e}")
            return None

    def _init_gemini(self):
        """Initialize Gemini client."""
        try:
            api_key = os.getenv('GEMINI_API_KEY') or os.getenv('GOOGLE_API_KEY')
            if not api_key:
                raise ValueError("GEMINI_API_KEY not set")
            return {"type": "gemini", "api_key": api_key}
        except Exception as e:
            self.logger.warning(f"Gemini init failed: {e}")
            return None

    def _init_groq(self):
        """Initialize Groq client (fast and free tier available)."""
        try:
            api_key = os.getenv('GROQ_API_KEY')
            if not api_key:
                raise ValueError("GROQ_API_KEY not set")
            return {"type": "groq", "api_key": api_key}
        except Exception as e:
            self.logger.warning(f"Groq init failed: {e}")
            return None

    def _call_claude(self, prompt: str) -> str:
        """Call Claude API."""
        client_info = self._get_client()
        response = client_info["client"].messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=4000,
            messages=[{"role": "user", "content": prompt}]
        )
        return response.content[0].text

    def _call_deepseek(self, prompt: str) -> str:
        """Call DeepSeek API."""
        import httpx
        client_info = self._get_client()

        response = httpx.post(
            "https://api.deepseek.com/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {client_info['api_key']}",
                "Content-Type": "application/json"
            },
            json={
                "model": "deepseek-chat",
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 4000,
                "temperature": 0.3
            },
            timeout=120.0
        )
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]

    def _call_gemini(self, prompt: str) -> str:
        """Call Gemini API."""
        import httpx
        client_info = self._get_client()

        response = httpx.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={client_info['api_key']}",
            headers={"Content-Type": "application/json"},
            json={
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {"maxOutputTokens": 4000, "temperature": 0.3}
            },
            timeout=120.0
        )
        response.raise_for_status()
        return response.json()["candidates"][0]["content"]["parts"][0]["text"]

    def _call_groq(self, prompt: str) -> str:
        """Call Groq API."""
        import httpx
        client_info = self._get_client()

        response = httpx.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {client_info['api_key']}",
                "Content-Type": "application/json"
            },
            json={
                "model": "llama-3.1-70b-versatile",
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 4000,
                "temperature": 0.3
            },
            timeout=120.0
        )
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]

    def _call_model(self, prompt: str) -> str:
        """Call the appropriate model."""
        client_info = self._get_client()
        if not client_info:
            raise ValueError("No critic model available")

        model_type = client_info.get("type", "deepseek")

        if model_type == "claude":
            return self._call_claude(prompt)
        elif model_type == "deepseek":
            return self._call_deepseek(prompt)
        elif model_type == "gemini":
            return self._call_gemini(prompt)
        elif model_type == "groq":
            return self._call_groq(prompt)
        else:
            return self._call_deepseek(prompt)

    def _parse_response(self, response: str) -> CriticReport:
        """Parse the JSON response from the critic model."""
        # Extract JSON from response
        json_match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', response)
        if json_match:
            json_str = json_match.group(1)
        else:
            json_match = re.search(r'\{[\s\S]*\}', response)
            if json_match:
                json_str = json_match.group(0)
            else:
                return CriticReport(
                    overall_quality=0,
                    publishable=False,
                    summary="Failed to parse critic response",
                    raw_response=response
                )

        try:
            data = json.loads(json_str)
        except json.JSONDecodeError as e:
            self.logger.error(f"JSON parse error: {e}")
            return CriticReport(
                overall_quality=0,
                publishable=False,
                summary=f"Failed to parse critic JSON: {e}",
                raw_response=response
            )

        # Convert issues
        issues = []
        for issue_data in data.get("issues", []):
            try:
                severity = CriticSeverity(issue_data.get("severity", "minor").lower())
            except ValueError:
                severity = CriticSeverity.MINOR

            issues.append(CriticIssue(
                severity=severity,
                category=issue_data.get("category", "unknown"),
                description=issue_data.get("description", ""),
                location=issue_data.get("location", ""),
                suggestion=issue_data.get("suggestion", ""),
                confidence=float(issue_data.get("confidence", 0.5))
            ))

        return CriticReport(
            overall_quality=int(data.get("overall_quality", 0)),
            publishable=bool(data.get("publishable", False)),
            summary=data.get("summary", ""),
            issues=issues,
            strengths=data.get("strengths", []),
            pacing_assessment=data.get("pacing_assessment", ""),
            dialogue_assessment=data.get("dialogue_assessment", ""),
            character_assessment=data.get("character_assessment", ""),
            prose_assessment=data.get("prose_assessment", ""),
            tension_assessment=data.get("tension_assessment", ""),
            raw_response=response
        )

    def critique(self, content: str, content_type: str = "chapter") -> CriticReport:
        """
        Critique the given fiction content using a different model.

        Args:
            content: The generated content to critique
            content_type: Type of content ("chapter", "scene", "dialogue")

        Returns:
            CriticReport with detailed feedback
        """
        self.logger.info(f"Critiquing {content_type} with {self.critic_model}...")

        prompt = self.FICTION_CRITIQUE_PROMPT.format(content=content)

        try:
            response = self._call_model(prompt)
            report = self._parse_response(response)

            critical_count = sum(1 for i in report.issues if i.severity == CriticSeverity.CRITICAL)
            major_count = sum(1 for i in report.issues if i.severity == CriticSeverity.MAJOR)

            self.logger.info(
                f"Critique complete: {report.overall_quality}/100, "
                f"{critical_count} critical, {major_count} major issues"
            )

            return report

        except Exception as e:
            self.logger.error(f"Critique failed: {e}")
            return CriticReport(
                overall_quality=0,
                publishable=False,
                summary=f"Critique failed: {e}",
                raw_response=""
            )

    def get_improvement_prompt(self, report: CriticReport, original_content: str) -> str:
        """
        Generate a prompt for improving content based on critique.
        """
        if not report.issues:
            return ""

        critical_issues = [i for i in report.issues if i.severity == CriticSeverity.CRITICAL]
        major_issues = [i for i in report.issues if i.severity == CriticSeverity.MAJOR]

        prompt_parts = ["Revise this chapter to address these issues:\n"]

        if critical_issues:
            prompt_parts.append("\n## CRITICAL (must fix):")
            for issue in critical_issues:
                prompt_parts.append(f"- {issue.description}")
                prompt_parts.append(f"  Problem: \"{issue.location[:100]}...\"")
                prompt_parts.append(f"  Fix: {issue.suggestion}")

        if major_issues:
            prompt_parts.append("\n## MAJOR (should fix):")
            for issue in major_issues[:5]:
                prompt_parts.append(f"- {issue.description}")
                prompt_parts.append(f"  Fix: {issue.suggestion}")

        prompt_parts.append(f"\n## Original:\n{original_content}")
        prompt_parts.append("\nRewrite fixing ALL critical issues. Keep same plot and characters.")

        return "\n".join(prompt_parts)

    def format_report(self, report: CriticReport) -> str:
        """Format the critique report for display."""
        lines = [
            "=" * 70,
            f"FICTION CRITIC REPORT ({self.critic_model.upper()})",
            "=" * 70,
            f"Overall Quality: {report.overall_quality}/100",
            f"Publishable: {'YES' if report.publishable else 'NO'}",
            "",
            "SUMMARY:",
            report.summary,
            "",
        ]

        if report.pacing_assessment:
            lines.append(f"Pacing: {report.pacing_assessment}")
        if report.dialogue_assessment:
            lines.append(f"Dialogue: {report.dialogue_assessment}")
        if report.character_assessment:
            lines.append(f"Characters: {report.character_assessment}")
        if report.prose_assessment:
            lines.append(f"Prose: {report.prose_assessment}")
        if report.tension_assessment:
            lines.append(f"Tension: {report.tension_assessment}")

        if report.strengths:
            lines.append("\nSTRENGTHS:")
            for strength in report.strengths:
                lines.append(f"  + {strength}")

        if report.issues:
            critical = [i for i in report.issues if i.severity == CriticSeverity.CRITICAL]
            major = [i for i in report.issues if i.severity == CriticSeverity.MAJOR]
            minor = [i for i in report.issues if i.severity == CriticSeverity.MINOR]

            if critical:
                lines.append(f"\nCRITICAL ISSUES ({len(critical)}):")
                for issue in critical:
                    lines.append(f"  X [{issue.category}] {issue.description}")
                    lines.append(f"     \"{issue.location[:60]}...\"")
                    lines.append(f"     Fix: {issue.suggestion}")

            if major:
                lines.append(f"\nMAJOR ISSUES ({len(major)}):")
                for issue in major:
                    lines.append(f"  ! [{issue.category}] {issue.description}")
                    lines.append(f"     Fix: {issue.suggestion}")

            if minor:
                lines.append(f"\nMINOR ISSUES ({len(minor)}):")
                for issue in minor[:5]:
                    lines.append(f"  - {issue.description}")

        lines.append("=" * 70)
        return "\n".join(lines)


def critique_fiction(content: str, model: str = "deepseek") -> CriticReport:
    """Quick function to critique fiction content."""
    critic = ContentCritic(critic_model=model)
    return critic.critique(content)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    test_content = """
    Chapter 5: The Revelation

    In that single moment, time seemed to stand still. Marcus felt a deep sense of dread
    wash over him, threatening to consume every fiber of his being. His heart pounded
    against his chest as he leveraged all his courage.

    "I can't believe this," he said, feeling shocked.

    Elena nodded. "I know. It's a lot to take in."

    He was very sad. She was also sad. They both felt sad together.

    Marcus walked. He then stopped. He turned around.
    """

    print("Testing Content Critic...")
    critic = ContentCritic(critic_model="deepseek")

    # Note: This will fail without API key, but shows structure
    try:
        report = critic.critique(test_content)
        print(critic.format_report(report))
    except Exception as e:
        print(f"Critique requires API key: {e}")
        print("Set DEEPSEEK_API_KEY environment variable")
