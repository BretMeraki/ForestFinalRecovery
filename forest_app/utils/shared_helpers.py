"""
shared_helpers.py

Shared utility helpers for Forest App, including common model attribute accessors.
"""
from typing import Any, Optional
import logging

def get_snapshot_data(model: Any) -> Optional[Any]:
    """
    Returns the 'snapshot_data' attribute from a model if it exists, else None.
    """
    return getattr(model, 'snapshot_data', None)

def get_snapshot_id(model: Any) -> Optional[Any]:
    """
    Returns the 'id' attribute from a model if it exists, else None.
    """
    return getattr(model, 'id', None)

def describe_magnitude(value: float, magnitude_thresholds: dict) -> str:
    """
    Describes magnitude based on thresholds. Accepts a value and a thresholds dict.
    Returns the label for the highest threshold not exceeding the value.
    """
    logger = logging.getLogger(__name__)
    try:
        float_value = float(value)
        valid_thresholds = {
            k: float(v)
            for k, v in magnitude_thresholds.items()
            if isinstance(v, (int, float))
        }
        if not valid_thresholds:
            return "Unknown"
        sorted_thresholds = sorted(
            valid_thresholds.items(), key=lambda item: item[1], reverse=True
        )
        for label, thresh in sorted_thresholds:
            if float_value >= thresh:
                return str(label)
        return str(sorted_thresholds[-1][0]) if sorted_thresholds else "Dormant"
    except (ValueError, TypeError) as e:
        logger.error(
            "Error converting value/threshold for magnitude: %s (Value: %s)", e, value
        )
        return "Unknown"
    except Exception as e:
        logger.exception("Error describing magnitude for value %s: %s", value, e)
        return "Unknown" 