"""
Forest App Core Components
"""

from forest_app.utils.import_fallbacks import import_with_fallback
import logging

logger = logging.getLogger(__name__)

HarmonicRouting = import_with_fallback(
    lambda: __import__('forest_app.core.harmonic_framework', fromlist=['HarmonicRouting']).HarmonicRouting,
    lambda: type('HarmonicRouting', (), {}),
    logger,
    "HarmonicRouting"
)
SilentScoring = import_with_fallback(
    lambda: __import__('forest_app.core.harmonic_framework', fromlist=['SilentScoring']).SilentScoring,
    lambda: type('SilentScoring', (), {}),
    logger,
    "SilentScoring"
)
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
ComponentStateManager = import_with_fallback(
    lambda: __import__('forest_app.core.services', fromlist=['ComponentStateManager']).ComponentStateManager,
    lambda: type('ComponentStateManager', (), {}),
    logger,
    "ComponentStateManager"
)
HTAService = import_with_fallback(
    lambda: __import__('forest_app.core.services', fromlist=['HTAService']).HTAService,
    lambda: type('HTAService', (), {}),
    logger,
    "HTAService"
)
SemanticMemoryManager = import_with_fallback(
    lambda: __import__('forest_app.core.services', fromlist=['SemanticMemoryManager']).SemanticMemoryManager,
    lambda: type('SemanticMemoryManager', (), {}),
    logger,
    "SemanticMemoryManager"
)
MemorySnapshot = import_with_fallback(
    lambda: __import__('forest_app.core.snapshot', fromlist=['MemorySnapshot']).MemorySnapshot,
    lambda: type('MemorySnapshot', (), {}),
    logger,
    "MemorySnapshot"
)
clamp01 = import_with_fallback(
    lambda: __import__('forest_app.core.utils', fromlist=['clamp01']).clamp01,
    lambda: (lambda x: x),
    logger,
    "clamp01"
)

__all__ = [
    "ReflectionProcessor",
    "CompletionProcessor",
    "HTAService",
    "ComponentStateManager",
    "SemanticMemoryManager",
    "MemorySnapshot",
    "clamp01",
    "SilentScoring",
    "HarmonicRouting",
]
