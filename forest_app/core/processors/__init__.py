"""
Forest App Core Processors
"""

import logging

try:
    from forest_app.core.processors.completion_processor import CompletionProcessor
except ImportError as e:
    logging.error(f"Failed to import CompletionProcessor: {e}")
    class CompletionProcessor:
        pass
try:
    from forest_app.core.processors.reflection_processor import ReflectionProcessor
except ImportError as e:
    logging.error(f"Failed to import ReflectionProcessor: {e}")
    class ReflectionProcessor:
        pass

__all__ = ["ReflectionProcessor", "CompletionProcessor"]
