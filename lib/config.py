"""
Centralized configuration for BookCLI.

Provides:
- All paths and directories
- API configuration
- Quality thresholds
- Pipeline settings
- Environment-aware configuration
"""

import os
from pathlib import Path
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
import yaml

# Detect environment
_ENV = os.environ.get("BOOKCLI_ENV", "development")


@dataclass
class PathConfig:
    """File system paths configuration."""
    # Base directories
    base_dir: Path = field(default_factory=lambda: Path(__file__).parent.parent)
    output_dir: Path = field(default_factory=lambda: Path(__file__).parent.parent / "output")
    fiction_dir: Path = field(default_factory=lambda: Path(__file__).parent.parent / "output" / "fiction")
    config_dir: Path = field(default_factory=lambda: Path(__file__).parent.parent / "config")
    logs_dir: Path = field(default_factory=lambda: Path(__file__).parent.parent / "logs")
    reports_dir: Path = field(default_factory=lambda: Path(__file__).parent.parent / "quality_reports")

    def __post_init__(self):
        """Ensure directories exist."""
        for attr_name in ['output_dir', 'fiction_dir', 'logs_dir', 'reports_dir']:
            path = getattr(self, attr_name)
            path.mkdir(parents=True, exist_ok=True)


@dataclass
class APIConfig:
    """API configuration with keys and endpoints."""
    # API Keys (loaded from environment)
    deepseek_key: Optional[str] = field(default_factory=lambda: os.environ.get("DEEPSEEK_API_KEY"))
    groq_key: Optional[str] = field(default_factory=lambda: os.environ.get("GROQ_API_KEY"))
    openrouter_key: Optional[str] = field(default_factory=lambda: os.environ.get("OPENROUTER_API_KEY"))
    together_key: Optional[str] = field(default_factory=lambda: os.environ.get("TOGETHER_API_KEY"))
    github_key: Optional[str] = field(default_factory=lambda: os.environ.get("GITHUB_TOKEN"))
    cerebras_key: Optional[str] = field(default_factory=lambda: os.environ.get("CEREBRAS_API_KEY"))
    cloudflare_key: Optional[str] = field(default_factory=lambda: os.environ.get("CLOUDFLARE_API_TOKEN"))
    cloudflare_account: Optional[str] = field(default_factory=lambda: os.environ.get("CLOUDFLARE_ACCOUNT_ID"))
    fireworks_key: Optional[str] = field(default_factory=lambda: os.environ.get("FIREWORKS_API_KEY"))
    anthropic_key: Optional[str] = field(default_factory=lambda: os.environ.get("ANTHROPIC_API_KEY"))
    openai_key: Optional[str] = field(default_factory=lambda: os.environ.get("OPENAI_API_KEY"))

    # API Endpoints
    deepseek_url: str = "https://api.deepseek.com/v1/chat/completions"
    groq_url: str = "https://api.groq.com/openai/v1/chat/completions"
    openrouter_url: str = "https://openrouter.ai/api/v1/chat/completions"
    together_url: str = "https://api.together.xyz/v1/chat/completions"
    github_url: str = "https://models.inference.ai.azure.com/chat/completions"
    cerebras_url: str = "https://api.cerebras.ai/v1/chat/completions"
    fireworks_url: str = "https://api.fireworks.ai/inference/v1/chat/completions"

    # Default models for each API
    deepseek_model: str = "deepseek-chat"
    groq_model: str = "llama-3.3-70b-versatile"
    openrouter_model: str = "meta-llama/llama-3.2-3b-instruct:free"
    together_model: str = "meta-llama/Llama-3.3-70B-Instruct-Turbo-Free"
    github_model: str = "gpt-4o-mini"
    cerebras_model: str = "llama-3.3-70b"
    fireworks_model: str = "accounts/fireworks/models/llama-v3p1-8b-instruct"

    # Timeouts (seconds)
    default_timeout: int = 120
    long_timeout: int = 300

    # Rate limits (calls per minute)
    rate_limits: Dict[str, int] = field(default_factory=lambda: {
        "deepseek": 60,
        "groq": 30,
        "openrouter": 60,
        "together": 60,
        "github": 15,
        "cerebras": 30,
        "cloudflare": 60,
        "fireworks": 60,
    })

    def get_available_apis(self) -> List[str]:
        """Get list of APIs with valid keys configured."""
        available = []
        key_mapping = {
            "deepseek": self.deepseek_key,
            "groq": self.groq_key,
            "openrouter": self.openrouter_key,
            "together": self.together_key,
            "github": self.github_key,
            "cerebras": self.cerebras_key,
            "cloudflare": self.cloudflare_key and self.cloudflare_account,
            "fireworks": self.fireworks_key,
        }
        for name, key in key_mapping.items():
            if key:
                available.append(name)
        return available


@dataclass
class QualityConfig:
    """Quality thresholds and settings."""
    # Chapter requirements
    min_chapter_words: int = 2500
    target_chapter_words: int = 3500
    max_chapter_words: int = 6000
    chapters_per_book: int = 12

    # Quality thresholds
    max_repeated_phrases: int = 3
    min_dialogue_ratio: float = 0.15
    max_dialogue_ratio: float = 0.60
    min_paragraph_length: int = 50
    max_paragraph_length: int = 500

    # Detection thresholds
    min_dialogue_quotes: int = 10  # Minimum quotes to consider chapter has dialogue
    duplicate_threshold: int = 200  # Characters to check for duplicates

    # AI-ism detection
    forbidden_phrases: List[str] = field(default_factory=lambda: [
        "I cannot", "I can't", "As an AI", "I don't have feelings",
        "I'm not able to", "I must clarify",
    ])

    overused_phrases: List[str] = field(default_factory=lambda: [
        "delved into", "moreover", "furthermore", "in conclusion",
        "it's important to note", "it's worth noting",
    ])


@dataclass
class PipelineConfig:
    """Pipeline execution settings."""
    # Parallel processing
    max_workers: int = 4
    batch_size: int = 10

    # Timing
    delay_between_books: float = 2.0
    delay_between_chapters: float = 0.5

    # Retry settings
    max_api_retries: int = 3
    retry_base_delay: float = 1.0
    retry_max_delay: float = 60.0

    # Circuit breaker
    failure_threshold: int = 5
    recovery_timeout: float = 30.0


@dataclass
class Config:
    """Main configuration class combining all settings."""
    paths: PathConfig = field(default_factory=PathConfig)
    api: APIConfig = field(default_factory=APIConfig)
    quality: QualityConfig = field(default_factory=QualityConfig)
    pipeline: PipelineConfig = field(default_factory=PipelineConfig)

    # Environment
    env: str = field(default_factory=lambda: _ENV)
    debug: bool = field(default_factory=lambda: _ENV == "development")

    @classmethod
    def from_yaml(cls, config_file: Path) -> 'Config':
        """Load configuration from YAML file with overrides."""
        config = cls()

        if config_file.exists():
            with open(config_file) as f:
                overrides = yaml.safe_load(f) or {}

            # Apply overrides
            if 'paths' in overrides:
                for key, value in overrides['paths'].items():
                    if hasattr(config.paths, key):
                        setattr(config.paths, key, Path(value))

            if 'quality' in overrides:
                for key, value in overrides['quality'].items():
                    if hasattr(config.quality, key):
                        setattr(config.quality, key, value)

            if 'pipeline' in overrides:
                for key, value in overrides['pipeline'].items():
                    if hasattr(config.pipeline, key):
                        setattr(config.pipeline, key, value)

        return config

    def to_dict(self) -> Dict[str, Any]:
        """Convert config to dictionary for serialization."""
        return {
            'env': self.env,
            'debug': self.debug,
            'paths': {
                'base_dir': str(self.paths.base_dir),
                'output_dir': str(self.paths.output_dir),
                'fiction_dir': str(self.paths.fiction_dir),
            },
            'quality': {
                'min_chapter_words': self.quality.min_chapter_words,
                'target_chapter_words': self.quality.target_chapter_words,
                'chapters_per_book': self.quality.chapters_per_book,
            },
            'api': {
                'available': self.api.get_available_apis(),
            }
        }


# Singleton instance
_config: Optional[Config] = None


def get_config(config_file: Optional[Path] = None) -> Config:
    """
    Get the global configuration instance.

    Creates config on first call, returns cached instance on subsequent calls.

    Args:
        config_file: Optional path to YAML config file for overrides

    Returns:
        Config instance

    Example:
        from lib.config import get_config
        config = get_config()
        print(config.paths.fiction_dir)
    """
    global _config

    if _config is None:
        if config_file:
            _config = Config.from_yaml(config_file)
        else:
            # Try to find default config file
            default_config = Path(__file__).parent.parent / "config" / "settings.yaml"
            if default_config.exists():
                _config = Config.from_yaml(default_config)
            else:
                _config = Config()

    return _config


def reset_config() -> None:
    """Reset the global config instance. Useful for testing."""
    global _config
    _config = None


# Convenience constants (for backwards compatibility during migration)
# These can be used directly: from lib.config import FICTION_DIR
def _get_paths() -> PathConfig:
    return get_config().paths

def _get_quality() -> QualityConfig:
    return get_config().quality

# Lazy path accessors
class _LazyPath:
    def __init__(self, attr: str):
        self.attr = attr

    def __fspath__(self) -> str:
        return str(getattr(_get_paths(), self.attr))

    def __str__(self) -> str:
        return str(getattr(_get_paths(), self.attr))

    def __truediv__(self, other) -> Path:
        return getattr(_get_paths(), self.attr) / other


# Export common paths for easy access
FICTION_DIR = _LazyPath('fiction_dir')
OUTPUT_DIR = _LazyPath('output_dir')
CONFIG_DIR = _LazyPath('config_dir')
LOGS_DIR = _LazyPath('logs_dir')

# Export common quality constants
MIN_CHAPTER_WORDS = property(lambda self: _get_quality().min_chapter_words)
TARGET_CHAPTER_WORDS = property(lambda self: _get_quality().target_chapter_words)
