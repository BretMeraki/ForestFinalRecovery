"""
Forest App Core Services
"""

import logging

try:
    from forest_app.core.services.component_state_manager import ComponentStateManager
except ImportError as e:
    logging.error(f"Failed to import ComponentStateManager: {e}")
    class ComponentStateManager:
        pass
try:
    from forest_app.core.services.hta_service import HTAService
except ImportError as e:
    logging.error(f"Failed to import HTAService: {e}")
    class HTAService:
        pass
try:
    from forest_app.core.services.semantic_memory import SemanticMemoryManager
except ImportError as e:
    logging.error(f"Failed to import SemanticMemoryManager: {e}")
    class SemanticMemoryManager:
        pass

__all__ = ["HTAService", "ComponentStateManager", "SemanticMemoryManager"]
