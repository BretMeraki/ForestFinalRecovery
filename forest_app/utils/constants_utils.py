"""
Constants Utilities

This module provides centralized handling for constants management
throughout the application. It's primarily responsible for:

1. Providing a consistent interface for accessing constants
2. Falling back to default values when the main constants module is unavailable
3. Allowing dynamic override of constants for testing or configuration

For most cases, you should directly import from forest_app.config.app_constants
rather than using these utilities, which are mainly for legacy support and
special use cases.
"""

from forest_app.utils.import_fallbacks import import_with_fallback
import logging
from forest_app.config.app_constants import (
    MAX_CODENAME_LENGTH,
    MIN_PASSWORD_LENGTH,
    ONBOARDING_STATUS_NEEDS_GOAL,
    ONBOARDING_STATUS_NEEDS_CONTEXT,
    ONBOARDING_STATUS_COMPLETED,
    SEED_STATUS_ACTIVE,
    SEED_STATUS_COMPLETED,
    DEFAULT_RESONANCE_THEME,
    DEFAULT_TIMEOUT_SECONDS,
    MAX_RETRIES
)

logger = logging.getLogger(__name__)

class ConstantsPlaceholder:
    """
    Placeholder for constants when the actual constants module fails to import.

    This class is maintained for backward compatibility. New code should
    import directly from forest_app.config.app_constants.

    This provides safe default values for essential constants used throughout
    the application, ensuring that the application can still function even
    when the constants module is not available.
    """

    # Onboarding related constants
    MAX_CODENAME_LENGTH = MAX_CODENAME_LENGTH
    MIN_PASSWORD_LENGTH = MIN_PASSWORD_LENGTH
    ONBOARDING_STATUS_NEEDS_GOAL = ONBOARDING_STATUS_NEEDS_GOAL
    ONBOARDING_STATUS_NEEDS_CONTEXT = ONBOARDING_STATUS_NEEDS_CONTEXT
    ONBOARDING_STATUS_COMPLETED = ONBOARDING_STATUS_COMPLETED

    # Seed related constants
    SEED_STATUS_ACTIVE = SEED_STATUS_ACTIVE
    SEED_STATUS_COMPLETED = SEED_STATUS_COMPLETED

    # Theme related constants
    DEFAULT_RESONANCE_THEME = DEFAULT_RESONANCE_THEME

    # Service related constants
    DEFAULT_TIMEOUT_SECONDS = DEFAULT_TIMEOUT_SECONDS
    MAX_RETRIES = MAX_RETRIES

    def __init__(self, **kwargs):
        """
        Initialize with optional custom values.

        Args:
            **kwargs: Override default values for any constants
        """
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)


def get_constants_module():
    """
    Safely imports the constants module with a fallback to default values.

    Returns:
        module or ConstantsPlaceholder: Either the actual constants module or a placeholder
    """
    try:
        logger.info("Successfully imported constants module.")
        return ConstantsPlaceholder()
    except ImportError as e:
        logger.warning("Failed to import constants module: %s. Using defaults.", e)
        return ConstantsPlaceholder()
