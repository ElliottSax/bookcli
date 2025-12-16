"""
Publishing module for Book Factory
Handles automated publishing to multiple platforms
"""

from .publishing_orchestrator import (
    PublishingOrchestrator,
    PublishingPlatform,
    BookMetadata
)

__all__ = [
    'PublishingOrchestrator',
    'PublishingPlatform',
    'BookMetadata'
]