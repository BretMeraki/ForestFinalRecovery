"""
Data Validation Utilities

This module provides centralized validation functions for common data types
to reduce code duplication across the application.
"""

import logging
from typing import Any, Dict, Optional, TypeVar

T = TypeVar("T")
logger = logging.getLogger(__name__)


def clamp01(x: float) -> float:
    """
    Clamp a float to the 0.0-1.0 range.

    Args:
        x: The value to clamp

    Returns:
        float: The clamped value between 0.0 and 1.0
    """
    try:
        return max(0.0, min(float(x), 1.0))
    except (ValueError, TypeError) as e:
        logger.warning("Failed to clamp value %s: %s", x, e)
        return 0.0


def validate_timestamp(timestamp: Any, default: Optional[str] = None) -> Optional[str]:
    """
    Validate and process a timestamp value.

    Args:
        timestamp: The timestamp to validate (expected to be a string or None)
        default: Default value to return if timestamp is None

    Returns:
        Optional[str]: Validated timestamp string or None/default if invalid
    """
    if isinstance(timestamp, str):
        # Could add ISO format validation here
        return timestamp
    elif timestamp is not None:
        logger.warning(
            "Invalid timestamp type: %s. Expected string or None.",
            type(timestamp),
        )
    return default


def validate_dict_timestamp(
    data: Dict[str, Any], key: str = "last_update", default: Optional[str] = None
) -> Optional[str]:
    """
    Extract and validate a timestamp from a dictionary.

    Args:
        data: Dictionary containing the timestamp
        key: Key for the timestamp in the dictionary
        default: Default value to return if timestamp is missing or invalid

    Returns:
        Optional[str]: Validated timestamp string or None/default if invalid
    """
    loaded_ts = data.get(key)
    return validate_timestamp(loaded_ts, default)


def get_category_from_thresholds(
    float_value: float, thresholds: Dict[str, float], default: str = "Unknown"
) -> str:
    """
    Map a float value to a category based on thresholds.

    Args:
        float_value: The float value to categorize
        thresholds: Dictionary mapping category names to their minimum thresholds
        default: Default category to return if value doesn't meet any threshold

    Returns:
        str: The category name
    """
    try:
        # Filter out any invalid thresholds
        valid_thresholds = {
            k: v for k, v in thresholds.items() if isinstance(v, (int, float))
        }

        if not valid_thresholds:
            return default

        # Sort thresholds from highest to lowest
        sorted_thresholds = sorted(
            valid_thresholds.items(), key=lambda item: item[1], reverse=True
        )

        # Return the first category where the value meets or exceeds the threshold
        for label, thresh in sorted_thresholds:
            if float_value >= thresh:
                return str(label)

        # If no thresholds were met, return the lowest category or default
        return str(sorted_thresholds[-1][0]) if sorted_thresholds else "Dormant"

    except (ValueError, TypeError) as e:
        logger.warning("Error categorizing value %s: %s", float_value, e)
        return default
