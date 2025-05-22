"""
Feature Flags Management

This module provides a centralized way to manage feature flags across the application.
"""

import logging
from typing import Any, Callable, Dict, Optional
from forest_app.utils.import_fallbacks import import_with_fallback

logger = logging.getLogger(__name__)

check_flag = import_with_fallback(
    lambda: __import__('forest_app.core.feature_flags', fromlist=['is_enabled']).is_enabled,
    lambda: (lambda feature: False),
    logger,
    "check_flag"
)

# Default feature flags when the real module is not available
DEFAULT_FEATURE_FLAGS = {
    # Add default feature flags here
    "advanced_analytics": False,
    "experimental_ui": False,
}


def is_enabled(flag_name: str, feature_flags: Optional[Dict[str, Any]] = None) -> bool:
    """
    Checks if a feature flag is enabled.

    Args:
        flag_name: The name of the feature flag
        feature_flags: Optional dictionary of feature flags

    Returns:
        bool: True if the flag is enabled, False otherwise
    """
    if feature_flags is None:
        return False
    return bool(feature_flags.get(flag_name, False))


def with_feature_flag(feature: str, _default: bool = False) -> callable:
    """
    Decorator to conditionally enable/disable functions based on feature flags.

    Args:
        feature: The name of the feature flag to check
        default: Default value if the feature flag check fails

    Returns:
        callable: The decorated function or a no-op function
    """

    def decorator(func):
        if is_enabled(feature):
            return func

        def noop(_args, **_kwargs):
            logger.debug(
                "Feature '%s' is disabled. Skipping %s", feature, func.__name__
            )
            return None

        return noop

    return decorator
