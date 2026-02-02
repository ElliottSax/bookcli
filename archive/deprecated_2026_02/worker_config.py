#!/usr/bin/env python3
"""
⚠️  DEPRECATION NOTICE (2026-02-01) ⚠️
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
This file has been DEPRECATED. Use instead:

    lib/config.py

Worker configuration is now managed in the centralized config module.

New Usage:
    from lib.config import get_config

    config = get_config()
    # Worker configuration can be accessed via config object

Migration Guide: See REFACTORING_COMPLETE_2026_02.md
Quick Start: See REFACTORING_QUICK_START.md
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Worker Configuration for bookcli - Book Generation Workers

These are the available OCI compute workers for distributed book generation.
"""

# Available workers (Ubuntu workers with our SSH key)
WORKERS = [
    {"ip": "147.224.209.15", "user": "ubuntu", "name": "book-worker-1"},
    {"ip": "64.181.220.95", "user": "ubuntu", "name": "book-worker-2"},
]

# SSH key path
SSH_KEY = "~/.ssh/oci_worker_key"

# API Keys - loaded from environment (no hardcoded keys)
from api_config import DEEPSEEK_API_KEY, GROQ_API_KEY

# Worker capabilities
WORKER_CAPABILITIES = {
    "book-worker-1": ["book_generation", "non_fiction", "fiction"],
    "book-worker-2": ["book_generation", "non_fiction", "fiction"],
}


def get_workers():
    """Get all available workers."""
    return WORKERS


def get_worker_by_name(name: str):
    """Get a specific worker by name."""
    for w in WORKERS:
        if w["name"] == name:
            return w
    return None


def get_ssh_command(worker: dict, command: str) -> str:
    """Generate SSH command for a worker."""
    from pathlib import Path
    key = Path(SSH_KEY).expanduser()
    return f'ssh -o StrictHostKeyChecking=no -i {key} {worker["user"]}@{worker["ip"]} "{command}"'
