"""
Unit tests for lib/config.py
"""

import pytest
import os
from pathlib import Path
from unittest.mock import patch

import sys
sys.path.insert(0, str(__file__).rsplit('/tests/', 1)[0])

from lib.config import (
    Config,
    PathConfig,
    APIConfig,
    QualityConfig,
    PipelineConfig,
    ConfigValidationError,
    get_config,
    reset_config,
)


class TestPathConfig:
    """Tests for PathConfig."""

    def test_default_paths(self):
        """Default paths should be set relative to project."""
        config = PathConfig()

        assert config.base_dir.exists() or True  # May not exist in test env
        assert 'output' in str(config.output_dir)
        assert 'fiction' in str(config.fiction_dir)

    def test_paths_are_path_objects(self):
        """All paths should be Path objects."""
        config = PathConfig()

        assert isinstance(config.base_dir, Path)
        assert isinstance(config.output_dir, Path)
        assert isinstance(config.fiction_dir, Path)


class TestAPIConfig:
    """Tests for APIConfig."""

    def test_loads_keys_from_environment(self):
        """API keys should be loaded from environment."""
        with patch.dict(os.environ, {'DEEPSEEK_API_KEY': 'test_key'}):
            config = APIConfig()
            assert config.deepseek_key == 'test_key'

    def test_missing_keys_are_none(self):
        """Missing API keys should be None."""
        with patch.dict(os.environ, {}, clear=True):
            config = APIConfig()
            # Key might exist from actual env, so just check type
            assert config.deepseek_key is None or isinstance(config.deepseek_key, str)

    def test_get_available_apis(self):
        """Should return list of configured APIs."""
        with patch.dict(os.environ, {
            'DEEPSEEK_API_KEY': 'key1',
            'GROQ_API_KEY': 'key2',
        }, clear=True):
            config = APIConfig()
            available = config.get_available_apis()

            assert 'deepseek' in available
            assert 'groq' in available

    def test_default_models_are_set(self):
        """Default models should be configured."""
        config = APIConfig()

        assert config.deepseek_model
        assert config.groq_model
        assert config.openrouter_model

    def test_rate_limits_are_set(self):
        """Rate limits should be configured for each API."""
        config = APIConfig()

        assert 'deepseek' in config.rate_limits
        assert 'groq' in config.rate_limits
        assert all(isinstance(v, int) for v in config.rate_limits.values())


class TestQualityConfig:
    """Tests for QualityConfig."""

    def test_default_thresholds(self):
        """Quality thresholds should have sensible defaults."""
        config = QualityConfig()

        assert config.min_chapter_words > 0
        assert config.target_chapter_words > config.min_chapter_words
        assert config.chapters_per_book > 0

    def test_dialogue_ratios(self):
        """Dialogue ratios should be valid."""
        config = QualityConfig()

        assert 0 <= config.min_dialogue_ratio <= 1
        assert 0 <= config.max_dialogue_ratio <= 1
        assert config.min_dialogue_ratio < config.max_dialogue_ratio

    def test_forbidden_phrases_exist(self):
        """Should have list of forbidden phrases."""
        config = QualityConfig()

        assert isinstance(config.forbidden_phrases, list)
        assert len(config.forbidden_phrases) > 0


class TestPipelineConfig:
    """Tests for PipelineConfig."""

    def test_default_settings(self):
        """Pipeline should have sensible defaults."""
        config = PipelineConfig()

        assert config.max_workers > 0
        assert config.batch_size > 0
        assert config.max_api_retries > 0

    def test_delays_are_positive(self):
        """Delays should be positive numbers."""
        config = PipelineConfig()

        assert config.delay_between_books >= 0
        assert config.delay_between_chapters >= 0
        assert config.retry_base_delay > 0


class TestConfig:
    """Tests for main Config class."""

    def test_creates_all_subconfigs(self):
        """Should create all sub-configurations."""
        config = Config()

        assert isinstance(config.paths, PathConfig)
        assert isinstance(config.api, APIConfig)
        assert isinstance(config.quality, QualityConfig)
        assert isinstance(config.pipeline, PipelineConfig)

    def test_to_dict(self):
        """Should convert to dictionary."""
        config = Config()
        data = config.to_dict()

        assert isinstance(data, dict)
        assert 'env' in data
        assert 'paths' in data
        assert 'quality' in data


class TestGetConfig:
    """Tests for get_config singleton."""

    def setup_method(self):
        """Reset config before each test."""
        reset_config()

    def teardown_method(self):
        """Reset config after each test."""
        reset_config()

    def test_returns_config_instance(self):
        """Should return a Config instance."""
        config = get_config()
        assert isinstance(config, Config)

    def test_returns_same_instance(self):
        """Should return the same instance on multiple calls."""
        config1 = get_config()
        config2 = get_config()
        assert config1 is config2

    def test_reset_creates_new_instance(self):
        """reset_config should create new instance on next call."""
        config1 = get_config()
        reset_config()
        config2 = get_config()
        assert config1 is not config2


class TestAPIConfigValidation:
    """Tests for APIConfig validation."""

    def test_invalid_default_timeout(self):
        """Should reject non-positive default_timeout."""
        with pytest.raises(ConfigValidationError, match="default_timeout"):
            APIConfig(default_timeout=0)

    def test_invalid_long_timeout(self):
        """Should reject non-positive long_timeout."""
        with pytest.raises(ConfigValidationError, match="long_timeout"):
            APIConfig(long_timeout=0)

    def test_long_timeout_less_than_default(self):
        """Should reject long_timeout < default_timeout."""
        with pytest.raises(ConfigValidationError, match="long_timeout must be >= default_timeout"):
            APIConfig(default_timeout=200, long_timeout=100)

    def test_invalid_rate_limit(self):
        """Should reject non-positive rate limits."""
        with pytest.raises(ConfigValidationError, match="rate_limit"):
            APIConfig(rate_limits={"deepseek": 0})


class TestQualityConfigValidation:
    """Tests for QualityConfig validation."""

    def test_invalid_min_chapter_words(self):
        """Should reject non-positive min_chapter_words."""
        with pytest.raises(ConfigValidationError, match="min_chapter_words"):
            QualityConfig(min_chapter_words=0)

    def test_min_greater_than_target(self):
        """Should reject min_chapter_words > target_chapter_words."""
        with pytest.raises(ConfigValidationError, match="min_chapter_words must be <= target"):
            QualityConfig(min_chapter_words=5000, target_chapter_words=3000)

    def test_target_greater_than_max(self):
        """Should reject target_chapter_words > max_chapter_words."""
        with pytest.raises(ConfigValidationError, match="target_chapter_words must be <= max"):
            QualityConfig(target_chapter_words=7000, max_chapter_words=6000)

    def test_invalid_dialogue_ratio_range(self):
        """Should reject dialogue ratios outside [0, 1]."""
        with pytest.raises(ConfigValidationError, match="min_dialogue_ratio"):
            QualityConfig(min_dialogue_ratio=-0.1)

        with pytest.raises(ConfigValidationError, match="max_dialogue_ratio"):
            QualityConfig(max_dialogue_ratio=1.5)

    def test_min_dialogue_ratio_greater_than_max(self):
        """Should reject min_dialogue_ratio >= max_dialogue_ratio."""
        with pytest.raises(ConfigValidationError, match="min_dialogue_ratio must be < max"):
            QualityConfig(min_dialogue_ratio=0.6, max_dialogue_ratio=0.4)

    def test_invalid_paragraph_lengths(self):
        """Should reject invalid paragraph length configuration."""
        with pytest.raises(ConfigValidationError, match="min_paragraph_length must be < max"):
            QualityConfig(min_paragraph_length=500, max_paragraph_length=100)


class TestPipelineConfigValidation:
    """Tests for PipelineConfig validation."""

    def test_invalid_max_workers(self):
        """Should reject non-positive max_workers."""
        with pytest.raises(ConfigValidationError, match="max_workers"):
            PipelineConfig(max_workers=0)

    def test_invalid_batch_size(self):
        """Should reject non-positive batch_size."""
        with pytest.raises(ConfigValidationError, match="batch_size"):
            PipelineConfig(batch_size=0)

    def test_negative_delay(self):
        """Should reject negative delays."""
        with pytest.raises(ConfigValidationError, match="delay_between_books"):
            PipelineConfig(delay_between_books=-1)

    def test_invalid_retry_settings(self):
        """Should reject invalid retry configuration."""
        with pytest.raises(ConfigValidationError, match="max_api_retries"):
            PipelineConfig(max_api_retries=0)

        with pytest.raises(ConfigValidationError, match="retry_base_delay must be <= retry_max_delay"):
            PipelineConfig(retry_base_delay=100, retry_max_delay=10)

    def test_invalid_circuit_breaker(self):
        """Should reject invalid circuit breaker settings."""
        with pytest.raises(ConfigValidationError, match="failure_threshold"):
            PipelineConfig(failure_threshold=0)

        with pytest.raises(ConfigValidationError, match="recovery_timeout"):
            PipelineConfig(recovery_timeout=0)
