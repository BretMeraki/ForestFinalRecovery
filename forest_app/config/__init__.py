"""
Forest App Configuration Package

This package contains configuration constants and settings.
"""

import logging

try:
    from forest_app.config.constants import (
        ORCHESTRATOR_HEARTBEAT_SEC,
    )
except ImportError as e:
    logging.error(f"Failed to import ORCHESTRATOR_HEARTBEAT_SEC: {e}")
    ORCHESTRATOR_HEARTBEAT_SEC = 30

__all__ = [
    "ORCHESTRATOR_HEARTBEAT_SEC",
    # Add other constants that should be publicly available
]
