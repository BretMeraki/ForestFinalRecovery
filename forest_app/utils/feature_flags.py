"""
Feature Flags Management

This module provides a centralized way to manage feature flags across the application.
"""

import logging

logger = logging.getLogger(__name__)

# Default feature flags when the real module is not available
DEFAULT_FEATURE_FLAGS = {
    # Add default feature flags here
    "advanced_analytics": False,
    "experimental_ui": False,
}


def is_enabled(feature: str) -> bool:
    """
    Check if a feature flag is enabled.

    Args:
        feature: The name of the feature flag to check

    Returns:
        bool: True if the feature is enabled, False otherwise
    """
    try:
        from forest_app.config.feature_flags import is_enabled as check_flag

        return check_flag(feature)
    except ImportError:
        logger.warning(
            "Feature flags module not available. Using default values. Feature: %s",
            feature,
        )
        return DEFAULT_FEATURE_FLAGS.get(feature, False)
    except Exception as e:
        # Broad catch is intentional for utility robustness and to log unexpected errors.
        logger.error("Error checking feature flag %s: %s", feature, str(e))
        return False


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
