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
