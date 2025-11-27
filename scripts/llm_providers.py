#!/usr/bin/env python3
"""
Multi-Provider LLM Support
Supports multiple API providers for cost optimization
"""

import os
import json
from typing import Dict, Optional, Tuple
from enum import Enum


class Provider(Enum):
    """Supported LLM providers"""
    CLAUDE = "claude"
    DEEPSEEK = "deepseek"
    OPENROUTER = "openrouter"
    QWEN = "qwen"
    OPENAI = "openai"


class ProviderConfig:
    """Configuration for each provider"""

    CONFIGS = {
        Provider.CLAUDE: {
            "name": "Anthropic Claude",
            "api_key_env": "ANTHROPIC_API_KEY",
            "model": "claude-sonnet-4-20250514",
            "max_tokens": 16000,
            "input_cost_per_1m": 3.00,
            "output_cost_per_1m": 15.00,
            "package": "anthropic",
            "endpoint": "https://api.anthropic.com/v1/messages"
        },
        Provider.DEEPSEEK: {
            "name": "DeepSeek",
            "api_key_env": "DEEPSEEK_API_KEY",
            "model": "deepseek-chat",
            "max_tokens": 16000,
            "input_cost_per_1m": 0.14,   # $0.14 per 1M tokens
            "output_cost_per_1m": 0.28,  # $0.28 per 1M tokens
            "package": "openai",  # Uses OpenAI-compatible API
            "endpoint": "https://api.deepseek.com/v1"
        },
        Provider.OPENROUTER: {
            "name": "OpenRouter",
            "api_key_env": "OPENROUTER_API_KEY",
            "model": "deepseek/deepseek-chat",  # Or any OpenRouter model
            "max_tokens": 16000,
            "input_cost_per_1m": 0.14,
            "output_cost_per_1m": 0.28,
            "package": "openai",  # OpenAI-compatible
            "endpoint": "https://openrouter.ai/api/v1"
        },
        Provider.QWEN: {
            "name": "Alibaba Qwen",
            "api_key_env": "QWEN_API_KEY",
            "model": "qwen-turbo",
            "max_tokens": 16000,
            "input_cost_per_1m": 0.29,   # Approximate pricing
            "output_cost_per_1m": 0.57,
            "package": "openai",  # Uses OpenAI-compatible API
            "endpoint": "https://dashscope.aliyuncs.com/compatible-mode/v1"
        },
        Provider.OPENAI: {
            "name": "OpenAI GPT-4",
            "api_key_env": "OPENAI_API_KEY",
            "model": "gpt-4-turbo-preview",
            "max_tokens": 16000,
            "input_cost_per_1m": 10.00,
            "output_cost_per_1m": 30.00,
            "package": "openai",
            "endpoint": "https://api.openai.com/v1"
        }
    }

    @classmethod
    def get_config(cls, provider: Provider) -> Dict:
        """Get configuration for a provider"""
        return cls.CONFIGS.get(provider, {})

    @classmethod
    def get_cheapest(cls) -> Provider:
        """Get cheapest provider"""
        return Provider.DEEPSEEK

    @classmethod
    def calculate_cost(cls, provider: Provider, input_tokens: int, output_tokens: int) -> float:
        """Calculate cost for a provider"""
        config = cls.get_config(provider)
        input_cost = (input_tokens / 1_000_000) * config["input_cost_per_1m"]
        output_cost = (output_tokens / 1_000_000) * config["output_cost_per_1m"]
        return input_cost + output_cost

    @classmethod
    def estimate_book_cost(cls, provider: Provider, chapters: int = 22, words_per_chapter: int = 3500) -> Tuple[float, float]:
        """Estimate cost for a complete book"""
        # Rough estimates based on typical usage
        input_tokens_per_chapter = 8000  # Prompt + context
        output_tokens_per_chapter = 4000  # Generated chapter

        total_input = input_tokens_per_chapter * chapters
        total_output = output_tokens_per_chapter * chapters

        min_cost = cls.calculate_cost(provider, total_input, total_output)
        max_cost = min_cost * 1.3  # +30% buffer

        return (min_cost, max_cost)


class LLMClient:
    """Unified client for multiple LLM providers"""

    def __init__(self, provider: Provider):
        self.provider = provider
        self.config = ProviderConfig.get_config(provider)
        self.client = None
        self._init_client()

    def _init_client(self):
        """Initialize the appropriate client"""
        api_key = os.environ.get(self.config["api_key_env"])
        if not api_key:
            raise ValueError(f"{self.config['api_key_env']} not set")

        package = self.config["package"]

        if package == "anthropic":
            import anthropic
            self.client = anthropic.Anthropic(api_key=api_key)
        elif package == "openai":
            from openai import OpenAI
            # Use custom base URL for non-OpenAI providers
            if self.provider == Provider.OPENAI:
                self.client = OpenAI(api_key=api_key)
            else:
                self.client = OpenAI(
                    api_key=api_key,
                    base_url=self.config["endpoint"]
                )
        else:
            raise ValueError(f"Unknown package: {package}")

    def generate(self, prompt: str) -> Tuple[str, int, int]:
        """
        Generate text using the provider

        Returns:
            (generated_text, input_tokens, output_tokens)
        """
        if self.config["package"] == "anthropic":
            return self._generate_claude(prompt)
        elif self.config["package"] == "openai":
            return self._generate_openai_compatible(prompt)
        else:
            raise ValueError(f"Unknown package: {self.config['package']}")

    def _generate_claude(self, prompt: str) -> Tuple[str, int, int]:
        """Generate using Claude API"""
        response = self.client.messages.create(
            model=self.config["model"],
            max_tokens=self.config["max_tokens"],
            messages=[{"role": "user", "content": prompt}]
        )

        text = response.content[0].text
        input_tokens = response.usage.input_tokens
        output_tokens = response.usage.output_tokens

        return (text, input_tokens, output_tokens)

    def _generate_openai_compatible(self, prompt: str) -> Tuple[str, int, int]:
        """Generate using OpenAI-compatible API"""
        response = self.client.chat.completions.create(
            model=self.config["model"],
            max_tokens=self.config["max_tokens"],
            messages=[{"role": "user", "content": prompt}]
        )

        text = response.choices[0].message.content
        input_tokens = response.usage.prompt_tokens
        output_tokens = response.usage.completion_tokens

        return (text, input_tokens, output_tokens)


def print_cost_comparison():
    """Print cost comparison for all providers"""
    print("\n" + "="*70)
    print("LLM PROVIDER COST COMPARISON")
    print("="*70)
    print("\nEstimated cost for 80k-word book (22 chapters):\n")

    print(f"{'Provider':<20} {'Cost per 1M':<15} {'Book Cost':<20} {'vs Claude':<10}")
    print("-" * 70)

    claude_cost = ProviderConfig.estimate_book_cost(Provider.CLAUDE, 22)

    for provider in Provider:
        config = ProviderConfig.get_config(provider)
        min_cost, max_cost = ProviderConfig.estimate_book_cost(provider, 22)

        # Calculate savings vs Claude
        savings_pct = ((claude_cost[0] - min_cost) / claude_cost[0]) * 100

        cost_str = f"${min_cost:.2f}-${max_cost:.2f}"

        if provider == Provider.CLAUDE:
            savings_str = "baseline"
        elif savings_pct > 0:
            savings_str = f"↓{savings_pct:.0f}%"
        else:
            savings_str = f"↑{abs(savings_pct):.0f}%"

        print(f"{config['name']:<20} ${config['input_cost_per_1m']:<14.2f} {cost_str:<20} {savings_str:<10}")

    print("\n" + "="*70)
    print("\nRECOMMENDATION:")
    print(f"  → Use DeepSeek for ~95% cost savings (${ProviderConfig.estimate_book_cost(Provider.DEEPSEEK, 22)[0]:.2f} vs ${claude_cost[0]:.2f})")
    print(f"  → Use Claude for highest quality (${claude_cost[0]:.2f}-${claude_cost[1]:.2f})")
    print("\n" + "="*70)


def main():
    """Test provider functionality"""
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "compare":
        print_cost_comparison()
        return

    print("\nAvailable providers:")
    for provider in Provider:
        config = ProviderConfig.get_config(provider)
        print(f"  - {provider.value}: {config['name']}")
        print(f"    API Key: {config['api_key_env']}")
        print(f"    Cost: ${config['input_cost_per_1m']:.2f}/${config['output_cost_per_1m']:.2f} per 1M tokens")

    print_cost_comparison()


if __name__ == "__main__":
    main()
