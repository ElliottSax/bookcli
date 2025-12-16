"""
Secure Configuration Manager for Book Factory
Handles API keys and sensitive configuration securely
"""

import os
import json
import base64
from pathlib import Path
from typing import Dict, Any, Optional, List
from cryptography.fernet import Fernet
from dotenv import load_dotenv
import logging

logger = logging.getLogger(__name__)


class SecureConfigManager:
    """
    Manages secure configuration including API keys and credentials.
    Features:
    - Loads from .env file (never committed to git)
    - Validates required keys
    - Encrypts sensitive data in memory
    - Provides secure access to configuration
    - Supports key rotation
    """

    REQUIRED_KEYS = [
        # At least one LLM provider must be present
        ['GROQ_API_KEY', 'DEEPSEEK_API_KEY', 'OPENAI_API_KEY', 'ANTHROPIC_API_KEY']
    ]

    SENSITIVE_KEYS = [
        'API_KEY', 'SECRET', 'PASSWORD', 'TOKEN', 'CREDENTIAL',
        'PRIVATE', 'ENCRYPTION_KEY', 'JWT_SECRET'
    ]

    def __init__(self, env_file: Optional[Path] = None):
        """
        Initialize the secure config manager.

        Args:
            env_file: Path to .env file (defaults to .env in project root)
        """
        self.env_file = env_file or Path('.env')
        self.config: Dict[str, Any] = {}
        self.encrypted_values: Dict[str, bytes] = {}
        self.cipher = None

        # Initialize encryption
        self._init_encryption()

        # Load configuration
        self.load_config()

    def _init_encryption(self):
        """Initialize encryption for sensitive data."""
        # Get or generate encryption key
        encryption_key = os.environ.get('ENCRYPTION_KEY')

        if not encryption_key:
            # Generate a new key if not provided
            # In production, this should be stored securely
            encryption_key = Fernet.generate_key().decode()
            logger.warning("Generated new encryption key - store this securely!")

        # Create cipher
        if isinstance(encryption_key, str):
            encryption_key = encryption_key.encode()

        self.cipher = Fernet(encryption_key[:32].ljust(32, b'0'))

    def load_config(self) -> bool:
        """
        Load configuration from .env file.

        Returns:
            True if config loaded successfully
        """
        # Check if .env exists
        if not self.env_file.exists():
            # Try to create from template
            template_file = Path('.env.template')
            if template_file.exists():
                logger.warning(f"No .env file found. Please copy .env.template to .env and add your API keys.")
                return False
            else:
                logger.error("No .env or .env.template file found!")
                return False

        # Load environment variables
        load_dotenv(self.env_file)

        # Load all environment variables
        for key, value in os.environ.items():
            if value:  # Only store non-empty values
                # Check if this is a sensitive key
                if any(sensitive in key.upper() for sensitive in self.SENSITIVE_KEYS):
                    # Encrypt sensitive values
                    self.encrypted_values[key] = self._encrypt_value(value)
                    # Store placeholder in config
                    self.config[key] = "***ENCRYPTED***"
                else:
                    # Store non-sensitive values directly
                    self.config[key] = value

        # Validate required keys
        if not self._validate_required_keys():
            return False

        logger.info(f"Loaded {len(self.config)} configuration values")
        return True

    def _validate_required_keys(self) -> bool:
        """
        Validate that required keys are present.

        Returns:
            True if all required keys present
        """
        for key_group in self.REQUIRED_KEYS:
            if isinstance(key_group, list):
                # At least one key from the group must be present
                if not any(self.get(key) for key in key_group):
                    logger.error(f"At least one of these keys required: {key_group}")
                    return False
            else:
                # Single required key
                if not self.get(key_group):
                    logger.error(f"Required key missing: {key_group}")
                    return False

        return True

    def get(self, key: str, default: Any = None) -> Any:
        """
        Get a configuration value securely.

        Args:
            key: Configuration key
            default: Default value if key not found

        Returns:
            Configuration value (decrypted if sensitive)
        """
        # Check if this is an encrypted value
        if key in self.encrypted_values:
            return self._decrypt_value(self.encrypted_values[key])

        # Return regular value
        return self.config.get(key, default)

    def get_llm_provider_keys(self) -> Dict[str, Optional[str]]:
        """
        Get all available LLM provider API keys.

        Returns:
            Dictionary of provider names to API keys
        """
        providers = {
            'groq': self.get('GROQ_API_KEY'),
            'deepseek': self.get('DEEPSEEK_API_KEY'),
            'openai': self.get('OPENAI_API_KEY'),
            'anthropic': self.get('ANTHROPIC_API_KEY'),
            'openrouter': self.get('OPENROUTER_API_KEY'),
            'huggingface': self.get('HUGGINGFACE_API_KEY'),
            'qwen': self.get('QWEN_API_KEY'),
        }

        # Filter out None values
        return {k: v for k, v in providers.items() if v}

    def _encrypt_value(self, value: str) -> bytes:
        """
        Encrypt a sensitive value.

        Args:
            value: Value to encrypt

        Returns:
            Encrypted bytes
        """
        if self.cipher:
            return self.cipher.encrypt(value.encode())
        return value.encode()

    def _decrypt_value(self, encrypted: bytes) -> str:
        """
        Decrypt a sensitive value.

        Args:
            encrypted: Encrypted bytes

        Returns:
            Decrypted string
        """
        if self.cipher:
            return self.cipher.decrypt(encrypted).decode()
        return encrypted.decode()

    def set(self, key: str, value: Any):
        """
        Set a configuration value (runtime only, not persisted).

        Args:
            key: Configuration key
            value: Configuration value
        """
        # Check if this should be encrypted
        if any(sensitive in key.upper() for sensitive in self.SENSITIVE_KEYS):
            self.encrypted_values[key] = self._encrypt_value(str(value))
            self.config[key] = "***ENCRYPTED***"
        else:
            self.config[key] = value

    def get_safe_config(self) -> Dict[str, Any]:
        """
        Get configuration with sensitive values masked.

        Returns:
            Safe configuration dictionary
        """
        safe_config = {}

        for key, value in self.config.items():
            if key in self.encrypted_values:
                # Show only first 4 chars of API keys
                actual_value = self._decrypt_value(self.encrypted_values[key])
                if len(actual_value) > 4:
                    safe_config[key] = actual_value[:4] + "..." + "*" * 20
                else:
                    safe_config[key] = "***"
            else:
                safe_config[key] = value

        return safe_config

    def validate_providers(self) -> List[str]:
        """
        Validate which LLM providers are available.

        Returns:
            List of available provider names
        """
        available = []
        providers = self.get_llm_provider_keys()

        for provider, key in providers.items():
            if key and len(key) > 10:  # Basic validation
                available.append(provider)

        if not available:
            logger.error("No valid LLM provider API keys found!")
            logger.info("Please add at least one API key to your .env file")
            logger.info("Recommended: GROQ_API_KEY (free) or DEEPSEEK_API_KEY (cheap)")

        return available

    def rotate_key(self, key: str, new_value: str) -> bool:
        """
        Rotate an API key or credential.

        Args:
            key: Configuration key to rotate
            new_value: New value for the key

        Returns:
            True if rotation successful
        """
        old_value = self.get(key)

        # Update the value
        self.set(key, new_value)

        # Update in environment
        os.environ[key] = new_value

        logger.info(f"Rotated key: {key}")

        # Optionally update .env file (careful with this)
        # self._update_env_file(key, new_value)

        return True

    def export_template(self, output_file: Path = Path('.env.template')):
        """
        Export a template .env file with all keys but no values.

        Args:
            output_file: Path to output template file
        """
        template_lines = []
        template_lines.append("# Book Factory Environment Configuration")
        template_lines.append("# Copy this to .env and fill in your values")
        template_lines.append("")

        # Group keys by category
        categories = {
            'LLM Providers': ['GROQ_API_KEY', 'DEEPSEEK_API_KEY', 'OPENAI_API_KEY',
                             'ANTHROPIC_API_KEY', 'OPENROUTER_API_KEY'],
            'Cloud': ['OCI_CONFIG_PROFILE', 'OCI_COMPARTMENT_ID'],
            'Publishing': ['KDP_CLIENT_ID', 'KDP_CLIENT_SECRET'],
            'Security': ['ENCRYPTION_KEY', 'JWT_SECRET'],
            'Application': ['DATABASE_PATH', 'LOG_LEVEL', 'ENVIRONMENT']
        }

        for category, keys in categories.items():
            template_lines.append(f"# {category}")
            template_lines.append("#" + "=" * 40)
            for key in keys:
                template_lines.append(f"{key}=")
            template_lines.append("")

        # Write template
        output_file.write_text('\n'.join(template_lines))
        logger.info(f"Exported template to {output_file}")


# Singleton instance
_config_manager = None

def get_config() -> SecureConfigManager:
    """
    Get the singleton config manager instance.

    Returns:
        SecureConfigManager instance
    """
    global _config_manager
    if _config_manager is None:
        _config_manager = SecureConfigManager()
    return _config_manager


def get_api_key(provider: str) -> Optional[str]:
    """
    Convenience function to get an API key for a provider.

    Args:
        provider: Provider name (groq, openai, etc.)

    Returns:
        API key or None
    """
    config = get_config()
    key_name = f"{provider.upper()}_API_KEY"
    return config.get(key_name)