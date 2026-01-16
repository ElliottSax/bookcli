"""
Unit tests for lib/api_client.py
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import json

import sys
sys.path.insert(0, str(__file__).rsplit('/tests/', 1)[0])

from lib.api_client import (
    APIClient,
    APIResponse,
    get_api_client,
    reset_api_client,
    call_llm,
    extract_json_from_response,
)


class TestAPIResponse:
    """Tests for APIResponse dataclass."""

    def test_success_response_is_truthy(self):
        """Successful response with content should be truthy."""
        response = APIResponse(content="Hello", success=True, api_name="test")
        assert bool(response) is True

    def test_failed_response_is_falsy(self):
        """Failed response should be falsy."""
        response = APIResponse(success=False, api_name="test", error="Failed")
        assert bool(response) is False

    def test_success_without_content_is_falsy(self):
        """Success without content should be falsy."""
        response = APIResponse(success=True, api_name="test", content=None)
        assert bool(response) is False


class TestAPIClient:
    """Tests for APIClient class."""

    def setup_method(self):
        """Reset client before each test."""
        reset_api_client()

    @patch('lib.api_client.get_config')
    def test_get_available_apis_with_keys(self, mock_config):
        """Should return APIs with configured keys."""
        mock_api_config = Mock()
        mock_api_config.get_available_apis.return_value = ['deepseek', 'groq']
        mock_api_config.rate_limits = {'deepseek': 60, 'groq': 30}

        mock_pipeline_config = Mock()
        mock_pipeline_config.failure_threshold = 5
        mock_pipeline_config.recovery_timeout = 30.0

        mock_config.return_value.api = mock_api_config
        mock_config.return_value.pipeline = mock_pipeline_config

        client = APIClient(mock_api_config)
        available = client.get_available_apis()

        assert 'deepseek' in available
        assert 'groq' in available

    @patch('lib.api_client.requests.post')
    @patch('lib.api_client.get_config')
    def test_call_api_success(self, mock_config, mock_post):
        """Should return successful response on API success."""
        # Setup mocks
        mock_api_config = Mock()
        mock_api_config.deepseek_key = 'test_key'
        mock_api_config.deepseek_url = 'https://api.test.com'
        mock_api_config.deepseek_model = 'test-model'
        mock_api_config.default_timeout = 60
        mock_api_config.rate_limits = {'deepseek': 60}
        mock_api_config.get_available_apis.return_value = ['deepseek']

        mock_pipeline_config = Mock()
        mock_pipeline_config.failure_threshold = 5
        mock_pipeline_config.recovery_timeout = 30.0

        mock_config.return_value.api = mock_api_config
        mock_config.return_value.pipeline = mock_pipeline_config

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'choices': [{'message': {'content': 'Hello world'}}],
            'usage': {'total_tokens': 10}
        }
        mock_post.return_value = mock_response

        client = APIClient(mock_api_config)
        response = client.call_api('deepseek', 'Test prompt')

        assert response.success
        assert response.content == 'Hello world'
        assert response.api_name == 'deepseek'

    @patch('lib.api_client.requests.post')
    @patch('lib.api_client.get_config')
    def test_call_api_rate_limited(self, mock_config, mock_post):
        """Should handle rate limiting."""
        mock_api_config = Mock()
        mock_api_config.deepseek_key = 'test_key'
        mock_api_config.deepseek_url = 'https://api.test.com'
        mock_api_config.deepseek_model = 'test-model'
        mock_api_config.default_timeout = 60
        mock_api_config.rate_limits = {'deepseek': 60}
        mock_api_config.get_available_apis.return_value = ['deepseek']

        mock_pipeline_config = Mock()
        mock_pipeline_config.failure_threshold = 5
        mock_pipeline_config.recovery_timeout = 30.0

        mock_config.return_value.api = mock_api_config
        mock_config.return_value.pipeline = mock_pipeline_config

        mock_response = Mock()
        mock_response.status_code = 429
        mock_post.return_value = mock_response

        client = APIClient(mock_api_config)
        response = client.call_api('deepseek', 'Test prompt')

        assert not response.success
        assert 'Rate limited' in response.error

    def test_call_api_unknown_api(self):
        """Should return error for unknown API."""
        client = APIClient()
        response = client.call_api('unknown_api', 'Test prompt')

        assert not response.success
        assert 'Unknown API' in response.error


class TestExtractJsonFromResponse:
    """Tests for extract_json_from_response helper."""

    def test_extracts_from_code_block(self):
        """Should extract JSON from markdown code block."""
        response = '''Here is the result:
```json
{"name": "test", "value": 123}
```
'''
        result = extract_json_from_response(response)

        assert result == {"name": "test", "value": 123}

    def test_extracts_from_plain_code_block(self):
        """Should extract JSON from plain code block."""
        response = '''```
{"key": "value"}
```'''
        result = extract_json_from_response(response)

        assert result == {"key": "value"}

    def test_extracts_raw_json(self):
        """Should extract raw JSON without code block."""
        response = '{"direct": true}'
        result = extract_json_from_response(response)

        assert result == {"direct": True}

    def test_extracts_embedded_json(self):
        """Should extract JSON embedded in text."""
        response = 'Some text before {"embedded": 1} and after'
        result = extract_json_from_response(response)

        assert result == {"embedded": 1}

    def test_returns_none_for_invalid(self):
        """Should return None for non-JSON content."""
        response = 'This is not JSON at all'
        result = extract_json_from_response(response)

        assert result is None

    def test_returns_none_for_empty(self):
        """Should return None for empty content."""
        assert extract_json_from_response('') is None
        assert extract_json_from_response(None) is None


class TestCallLlm:
    """Tests for call_llm convenience function."""

    @patch('lib.api_client.get_api_client')
    def test_returns_content_on_success(self, mock_get_client):
        """Should return content string on success."""
        mock_client = Mock()
        mock_client.call.return_value = APIResponse(
            content="Response text",
            success=True,
            api_name="test"
        )
        mock_get_client.return_value = mock_client

        result = call_llm("Test prompt")

        assert result == "Response text"

    @patch('lib.api_client.get_api_client')
    def test_returns_none_on_failure(self, mock_get_client):
        """Should return None on failure."""
        mock_client = Mock()
        mock_client.call.return_value = APIResponse(
            success=False,
            api_name="test",
            error="Failed"
        )
        mock_get_client.return_value = mock_client

        result = call_llm("Test prompt")

        assert result is None
