"""
Data Validation Utilities

This module provides common data validation functions used across the application.
"""


def clamp01(value: float) -> float:
    """
    Clamp a float value to the range [0.0, 1.0].

    Args:
        value: The value to clamp

    Returns:
        float: The clamped value between 0.0 and 1.0
    """
    return max(0.0, min(1.0, float(value)))


def is_valid_thresholds(thresholds: dict) -> bool:
    """
    Validate that a thresholds dictionary contains valid numeric values.

    Args:
        thresholds: Dictionary of threshold values

    Returns:
        bool: True if all values are valid numbers, False otherwise
    """
    if not isinstance(thresholds, dict) or not thresholds:
        return False
    return all(isinstance(v, (int, float)) for v in thresholds.values())


def get_threshold_label(value: float, thresholds: dict) -> str:
    """
    Get the appropriate label for a value based on threshold ranges.

    Args:
        value: The value to classify
        thresholds: Dictionary mapping labels to threshold values

    Returns:
        str: The label corresponding to the value's threshold range
    """
    if not is_valid_thresholds(thresholds):
        return "Unknown"

    sorted_thresholds = sorted(
        thresholds.items(), key=lambda item: item[1], reverse=True
    )

    for label, threshold in sorted_thresholds:
        if value >= threshold:
            return str(label)

    return str(sorted_thresholds[-1][0]) if sorted_thresholds else "Unknown"
