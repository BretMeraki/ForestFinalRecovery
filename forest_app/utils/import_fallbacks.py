"""
import_fallbacks.py

Shared utility for robust import fallbacks in Forest App.
Provides a generic function to handle try/except imports and return dummy fallbacks.
"""

import logging
from typing import Any, Callable

def import_with_fallback(import_func: Callable[[], Any], fallback_factory: Callable[[], Any], logger: logging.Logger, name: str = "") -> Any:
    """
    Attempts to execute import_func. If ImportError occurs, logs the error and returns the fallback from fallback_factory.

    Args:
        import_func: Callable that performs the import and returns the imported object.
        fallback_factory: Callable that returns a fallback object if import fails.
        logger: Logger instance for error logging.
        name: Optional name of the import for logging clarity.

    Returns:
        The imported object, or the fallback if import fails.
    """
    try:
        return import_func()
    except ImportError as e:
        logger.error(f"Failed to import {name or import_func.__name__}: {e}")
        return fallback_factory()

def get_feature_flag_tools(logger):
    """
    Returns (Feature, is_enabled) using import_with_fallback for feature flag robustness.
    Usage:
        Feature, is_enabled = get_feature_flag_tools(logger)
    """
    Feature = import_with_fallback(
        lambda: __import__('forest_app.core.feature_flags', fromlist=['Feature']).Feature,
        lambda: type('Feature', (), {}),
        logger,
        "Feature"
    )
    is_enabled = import_with_fallback(
        lambda: __import__('forest_app.core.feature_flags', fromlist=['is_enabled']).is_enabled,
        lambda: (lambda *a, **k: False),
        logger,
        "is_enabled"
    )
    return Feature, is_enabled

# Example usage:
# from forest_app.utils.import_fallbacks import import_with_fallback
# get_db = import_with_fallback(lambda: from forest_app.persistence.database import get_db or get_db, lambda: lambda *a, **k: raise Exception("DB missing"), logger, "get_db") 