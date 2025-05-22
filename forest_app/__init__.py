"""
Forest App - A personal growth and task management application.
"""

__version__ = "1.0.0"

# Import core components
from forest_app.utils.import_fallbacks import import_with_fallback
import logging

logger = logging.getLogger(__name__)

# Core components
from forest_app.core.session_management import run_forest_session
from forest_app.modules.hta_tree import HTATree
from forest_app.modules.task_engine import TaskEngine
from forest_app.models.session import SessionState

# Processors
CompletionProcessor = import_with_fallback(
    lambda: __import__('forest_app.core.processors', fromlist=['CompletionProcessor']).CompletionProcessor,
    lambda: type('CompletionProcessor', (), {}),
    logger,
    "CompletionProcessor"
)
ReflectionProcessor = import_with_fallback(
    lambda: __import__('forest_app.core.processors', fromlist=['ReflectionProcessor']).ReflectionProcessor,
    lambda: type('ReflectionProcessor', (), {}),
    logger,
    "ReflectionProcessor"
)

__all__ = [
    "run_forest_session",
    "HTATree",
    "TaskEngine",
    "SessionState",
    "ReflectionProcessor",
    "CompletionProcessor",
]
