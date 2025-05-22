"""Dependency Injection Container for Forest Application.

This module provides a dependency injection container that manages all the application's
components and their dependencies. It uses dependency_injector for managing the
injection of dependencies throughout the application.
"""

import logging
from typing import Any, Dict, List, Optional, Protocol, TypeVar

try:
    from dependency_injector import containers, providers
except ImportError as e:
    logging.error(f"Failed to import dependency_injector: {e}")
    class containers:
        class DeclarativeContainer:
            pass
        class WiringConfiguration:
            def __init__(self, modules=None):
                pass
    class providers:
        @staticmethod
        def Singleton(*args, **kwargs):
            return lambda *a, **k: None
        @staticmethod
        def Configuration(strict=False):
            return None
        @staticmethod
        def Dict(d):
            return d

try:
    from forest_app.modules.types import SemanticMemoryProtocol
except ImportError as e:
    logging.error(f"Failed to import SemanticMemoryProtocol: {e}")
    class SemanticMemoryProtocol:
        pass

# Import centralized error handling
try:
    from forest_app.utils.error_handling import log_import_error
except ImportError as e:
    def log_import_error(error, module_name=None):
        logging.error(f"Import error in {module_name or 'unknown module'}: {error}")


# Protocol for semantic memory
class SemanticMemoryProtocol(Protocol):
    """Protocol defining the interface for semantic memory operations."""

    def store_memory(
        self,
        event_type: str,
        content: str,
        metadata: Dict[str, Any],
        importance: float = 0.5,
    ) -> None: ...

    def query_memories(
        self,
        query: str,
        k: int = 5,
        event_types: Optional[List[str]] = None,
        time_window_days: Optional[int] = None,
    ) -> List[Dict[str, Any]]: ...
    def update_memory_stats(self, memory_id: str, access_count: int = 1) -> None: ...

    def get_recent_memories(self, limit: int = 5) -> List[Dict[str, Any]]: ...
    def extract_themes(self, memories: List[Dict[str, Any]]) -> List[str]: ...
    def get_memory_stats(self) -> Dict[str, Any]: ...


# Type variable for generic container types
T = TypeVar("T")

# --- Feature Flags ---
try:
    from forest_app.core.feature_flags import Feature, is_enabled

    FEATURE_FLAGS_IMPORT_OK = True
    logger = logging.getLogger("containers")
    logger.info("Successfully imported feature flags.")
except ImportError as import_err:
    logging.basicConfig(level=logging.ERROR)
    logger = logging.getLogger("containers_init_error")
    logger.error(
        "CRITICAL: containers.py failed to import Feature Flags: %s. Check path.",
        import_err,
    )
    logger.warning("WARNING: ALL features will be treated as DISABLED.")

    class Feature:
        """Feature flags for enabling/disabling application features."""

        SENTIMENT_ANALYSIS = "FEATURE_ENABLE_SENTIMENT_ANALYSIS"
        PATTERN_ID = "FEATURE_ENABLE_PATTERN_ID"
        RELATIONAL = "FEATURE_ENABLE_RELATIONAL"
        NARRATIVE_MODES = "FEATURE_ENABLE_NARRATIVE_MODES"
        XP_MASTERY = "FEATURE_ENABLE_XP_MASTERY"
        EMOTIONAL_INTEGRITY = "FEATURE_ENABLE_EMOTIONAL_INTEGRITY"
        DESIRE_ENGINE = "FEATURE_ENABLE_DESIRE_ENGINE"
        FINANCIAL_READINESS = "FEATURE_ENABLE_FINANCIAL_READINESS"
        REWARDS = "FEATURE_ENABLE_REWARDS"
        TRIGGER_PHRASES = "FEATURE_ENABLE_TRIGGER_PHRASES"
        PRACTICAL_CONSEQUENCE = "FEATURE_ENABLE_PRACTICAL_CONSEQUENCE"
        CORE_HTA = "FEATURE_ENABLE_CORE_HTA"

    def is_enabled(feature: Feature) -> bool:  # pylint: disable=unused-argument
        """Check if a feature is enabled (dummy implementation).

        Args:
            feature: The feature to check (unused in dummy implementation)

        Returns:
            bool: Always returns False in dummy implementation
        """
        return False


# --- Configuration ---
try:
    from forest_app.config.settings import settings

    SETTINGS_IMPORT_OK = True
    logger.info("Successfully imported settings.")
except ImportError as import_error:
    logger.warning("Settings import failed: %s", import_error)

    class DummySettings:
        """Dummy settings for fallback configuration.

        This class provides default configuration values when the real settings
        module cannot be imported. All settings are initialized with safe defaults.
        """

        def __init__(self) -> None:
            """Initialize dummy settings with default values."""
            # API and connection settings
            self.google_api_key = "DUMMY_KEY_REQUIRED"
            self.db_connection_string = "sqlite:///./dummy_db_required.db"

            # Model configuration
            self.gemini_model_name = "gemini-1.5-flash-latest"
            self.gemini_advanced_model_name = "gemini-1.5-pro-latest"
            self.llm_temperature = 0.7

            # Engine configuration
            self.metrics_engine_alpha = 0.3
            self.metrics_engine_thresholds = {}
            self.narrative_engine_config = {}

            # Flow control
            self.snapshot_flow_frequency = 5
            self.snapshot_flow_max_snapshots = 100
            self.task_engine_templates = {}

    settings = DummySettings()
    SETTINGS_IMPORT_OK = False


class DummyService:
    """Base dummy class for fallback implementations.

    This class provides a base implementation that logs all method calls and returns None.
    It's used as a fallback when real service implementations cannot be imported.
    """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Initialize dummy service with debug logging.

        Args:
            *args: Positional arguments (ignored).
            **kwargs: Keyword arguments (ignored).
        """
        logger.debug(
            "Initialized DummyService for %s with args: %s, kwargs: %s",
            self.__class__.__name__,
            args,
            kwargs,
        )

    def __call__(self, *args: Any, **kwargs: Any) -> None:
        """Handle call to dummy service with debug logging.

        Args:
            *args: Positional arguments (ignored).
            **kwargs: Keyword arguments (ignored).

        Returns:
            None: Always returns None.
        """
        logger.debug(
            "Called DummyService %s with args: %s, kwargs: %s",
            self.__class__.__name__,
            args,
            kwargs,
        )
        return None

    def __getattr__(self, name: str) -> Any:
        """Dynamically handle attribute access with debug logging.

        Args:
            name: Name of the attribute being accessed.

        Returns:
            A dummy method that logs its calls and returns None.
        """

        def _dummy_method(*args: Any, **kwargs: Any) -> None:
            """Dummy method that logs its calls and returns None."""
            logger.debug(
                "Called dummy method '%s' on DummyService %s with args: %s, kwargs: %s",
                name,
                self.__class__.__name__,
                args,
                kwargs,
            )
            return None

        return _dummy_method


try:
    # First try to import from the real implementation
    from forest_app.integrations.llm import LLMClient

    LLM_IMPORT_OK = True
except ImportError as e:
    logger.warning("containers.py: Using fallback LLM implementation: %s", e)

    # Import centralized fallback implementation
    from forest_app.integrations.llm_fallbacks import LLMClient

    LLM_IMPORT_OK = False

try:
    from forest_app.core.harmonic_framework import HarmonicRouting, SilentScoring
    from forest_app.core.orchestrator import ForestOrchestrator
    from forest_app.core.processors import CompletionProcessor, ReflectionProcessor
    from forest_app.core.services import (
        ComponentStateManager,
        HTAService,
        SemanticMemoryManager,
    )
    from forest_app.modules.desire_engine import DesireEngine
    from forest_app.modules.emotional_integrity import EmotionalIntegrityIndex
    from forest_app.modules.financial_readiness import FinancialReadinessEngine
    from forest_app.modules.logging_tracking import TaskFootprintLogger
    from forest_app.modules.metrics_specific import MetricsSpecificEngine
    from forest_app.modules.narrative_modes import NarrativeModesEngine
    from forest_app.modules.offering_reward import OfferingRouter
    from forest_app.modules.pattern_id import PatternIdentificationEngine
    from forest_app.modules.practical_consequence import PracticalConsequenceEngine
    from forest_app.modules.relational import (
        Profile,
        RelationalManager,
        RelationalRepairEngine,
    )
    from forest_app.modules.seed import SeedManager
    from forest_app.modules.sentiment import SecretSauceSentimentEngineHybrid
    from forest_app.modules.snapshot_flow import SnapshotFlowController
    from forest_app.modules.task_engine import TaskEngine
    from forest_app.modules.trigger_phrase import TriggerPhraseHandler
    from forest_app.modules.xp_mastery import XPMastery

    try:
        from forest_app.core.discovery_journey import DiscoveryJourneyService

        DISCOVERY_JOURNEY_IMPORT_OK = True
        logger.info("Successfully imported Discovery Journey service.")
    except ImportError as e:
        logger.error("Failed to import Discovery Journey service: %s", e)

        class DiscoveryJourneyService(DummyService):
            """Dummy implementation of DiscoveryJourneyService."""

            pass

        DISCOVERY_JOURNEY_IMPORT_OK = False
    MODULES_CORE_IMPORT_OK = True
    logger.info("Successfully imported application modules and core components.")
except ImportError as e:
    # Use centralized error handler for consistency
    log_import_error(e, "containers.py")
    # Additional critical log for this specific case
    logger.critical(
        "Container initialization failed - application may not function correctly"
    )

    # Dummy service implementations
    class TaskFootprintLogger(DummyService):
        """Dummy implementation of TaskFootprintLogger for logging task footprints."""

    class TriggerPhraseHandler(DummyService):
        """Dummy implementation of TriggerPhraseHandler for handling trigger phrases."""

    class SecretSauceSentimentEngineHybrid(DummyService):
        """Dummy implementation of sentiment analysis engine."""

    class PatternIdentificationEngine(DummyService):
        """Dummy implementation of pattern identification engine."""

    class PracticalConsequenceEngine(DummyService):
        """Dummy implementation of practical consequence engine."""

    class MetricsSpecificEngine(DummyService):
        """Dummy implementation of metrics engine."""

    class SeedManager(DummyService):
        """Dummy implementation of seed manager."""

    class RelationalManager(DummyService):
        """Dummy implementation of relational manager."""

    class NarrativeModesEngine(DummyService):
        """Dummy implementation of narrative modes engine."""

    class OfferingRouter(DummyService):
        """Dummy implementation of offering router."""

    class XPMastery(DummyService):
        """Dummy implementation of XP mastery system."""

    class EmotionalIntegrityIndex(DummyService):
        """Dummy implementation of emotional integrity index."""

    class TaskEngine(DummyService):
        """Dummy implementation of task engine."""

    class SnapshotFlowController(DummyService):
        """Dummy implementation of snapshot flow controller."""

    class DesireEngine(DummyService):
        """Dummy implementation of desire engine."""

    class FinancialReadinessEngine(DummyService):
        """Dummy implementation of financial readiness engine."""

    class SilentScoring(DummyService):
        """Dummy implementation of silent scoring system."""

    class HarmonicRouting(DummyService):
        """Dummy implementation of harmonic routing."""

    class ForestOrchestrator(DummyService):
        """Dummy implementation of forest orchestrator."""

    class ReflectionProcessor(DummyService):
        """Dummy implementation of reflection processor."""

    class CompletionProcessor(DummyService):
        """Dummy implementation of completion processor."""

    # Import the HTAService protocol to ensure type safety and compliance

    class HTAService(DummyService):
        """Dummy implementation of HTA service conforming to HTAServiceProtocol."""

        # This class is meant to be a placeholder when the actual implementation
        # cannot be loaded. The actual implementation is in core/services/hta_service.py

    class ComponentStateManager(DummyService):
        """Dummy implementation of component state manager."""

    class SemanticMemoryManager(DummyService):
        """Dummy implementation of SemanticMemoryManager."""

    class DiscoveryJourneyService(DummyService):
        """Dummy implementation of DiscoveryJourneyService."""

    MODULES_CORE_IMPORT_OK = False

try:
    from forest_app.core.processors import CompletionProcessor, ReflectionProcessor

    PROCESSORS_IMPORT_OK = True
except ImportError as e:
    logger.error("CRITICAL: containers.py failed to import processors: %s", e)
    PROCESSORS_IMPORT_OK = False


class DummySemanticMemoryManager(DummyService, SemanticMemoryProtocol):
    """Dummy implementation of SemanticMemoryProtocol for fallback.

    This class provides a dummy implementation of the semantic memory interface
    that logs all calls and returns empty/default values. It's used when the real
    semantic memory implementation cannot be imported.
    """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Initialize the dummy semantic memory manager.

        Args:
            *args: Positional arguments (ignored).
            **kwargs: Keyword arguments (ignored).
        """
        super().__init__(*args, **kwargs)
        self._memories: List[Dict[str, Any]] = []

    async def store_memory(
        self,
        event_type: str,
        content: str,
        metadata: Dict[str, Any],
        importance: float = 0.5,
    ) -> Dict[str, Any]:
        """Store a memory with the given type, content, and metadata.

        Args:
            event_type: Type of the event being stored.
            content: Content of the memory.
            metadata: Additional metadata for the memory.
            importance: Importance score of the memory (0.0 to 1.0).

        Returns:
            Dictionary containing status and memory ID.
        """
        logger.debug(
            "DummySemanticMemoryManager.store_memory called with event_type=%s, "
            "content_length=%d, metadata_keys=%s, importance=%.2f",
            event_type,
            len(content),
            list(metadata.keys()),
            importance,
        )
        memory_id = f"dummy_mem_{len(self._memories)}"
        self._memories.append(
            {
                "id": memory_id,
                "event_type": event_type,
                "content": content,
                "metadata": metadata,
                "importance": importance,
                "timestamp": "2023-01-01T00:00:00Z",
            }
        )
        return {"status": "success", "memory_id": memory_id}

    async def query_memories(
        self,
        query: str,
        k: int = 5,
        event_types: Optional[List[str]] = None,
        time_window_days: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """Query memories based on the given parameters.

        Args:
            query: Search query string.
            k: Maximum number of results to return.
            event_types: Optional list of event types to filter by.
            time_window_days: Optional time window in days to limit the search.

        Returns:
            List of matching memory dictionaries.
        """
        logger.debug(
            "DummySemanticMemoryManager.query_memories called with query='%s', k=%d, "
            "event_types=%s, time_window_days=%s",
            query,
            k,
            event_types,
            time_window_days,
        )
        return self._memories[:k]

    async def update_memory_stats(self, memory_id: str, access_count: int = 1) -> bool:
        """Update access statistics for a memory.

        Args:
            memory_id: ID of the memory to update.
            access_count: Number of times the memory was accessed.

        Returns:
            Boolean indicating if the update was successful.
        """
        logger.debug(
            "DummySemanticMemoryManager.update_memory_stats called with "
            "memory_id=%s, access_count=%d",
            memory_id,
            access_count,
        )
        return True

    async def get_recent_memories(self, limit: int = 5) -> List[Dict[str, Any]]:
        """Get the most recent memories.

        Args:
            limit: Maximum number of recent memories to return.

        Returns:
            List of recent memory dictionaries.
        """
        logger.debug(
            "DummySemanticMemoryManager.get_recent_memories called with limit=%d", limit
        )
        return self._memories[-limit:]

    async def extract_themes(self, memories: List[Dict[str, Any]]) -> List[str]:
        """Extract common themes from a list of memories.

        Args:
            memories: List of memory dictionaries to analyze.

        Returns:
            List of extracted themes.
        """
        logger.debug(
            "DummySemanticMemoryManager.extract_themes called with %d memories",
            len(memories),
        )
        return ["theme1", "theme2", "theme3"][: min(3, len(memories))]

    async def get_memory_stats(self) -> Dict[str, Any]:
        """Get statistics about stored memories.

        Returns:
            Dictionary containing memory statistics.
        """
        logger.debug("DummySemanticMemoryManager.get_memory_stats called")
        return {
            "total_memories": len(self._memories),
            "memory_types": {},
            "avg_importance": 0.0,
            "avg_access_count": 0.0,
            "last_updated": "2023-01-01T00:00:00Z" if self._memories else None,
        }


class Container(containers.DeclarativeContainer):
    """Dependency injection container for the Forest application.

    This container manages the creation and wiring of all application components,
    providing a centralized way to manage dependencies and configurations.
    """

    # Wiring configuration for dependency injection
    wiring_config = containers.WiringConfiguration(
        modules=[
            "forest_app.main",
            "forest_app.dependencies",
            "forest_app.routers.core",
            "forest_app.routers.auth",
            "forest_app.routers.onboarding",
            "forest_app.routers.users",
            "forest_app.routers.hta",
            "forest_app.routers.snapshots",
            "forest_app.routers.goals",
            "forest_app.core",
            "forest_app.core.processors",
            "forest_app.core.services",
            "forest_app.core.integrations",
            "forest_app.api.routers.discovery_journey",
            "forest_app.core.discovery_journey",
            "forest_app.modules.snapshot_flow",
            "forest_app.helpers",
        ]
    )
    config = providers.Configuration(strict=False)

    # LLM Client - Provides language model functionality
    llm_client = (
        providers.Singleton(LLMClient, config=config)
        if LLM_IMPORT_OK
        else providers.Singleton(DummyService)
    )
    # Sentiment analysis engine
    sentiment_engine = (
        providers.Singleton(SecretSauceSentimentEngineHybrid, llm_client=llm_client)
        if MODULES_CORE_IMPORT_OK
        and LLM_IMPORT_OK
        and is_enabled(Feature.SENTIMENT_ANALYSIS)
        else providers.Singleton(DummyService)
    )

    # Pattern identification engine
    pattern_engine = (
        providers.Singleton(PatternIdentificationEngine, config=config.provided)
        if MODULES_CORE_IMPORT_OK and is_enabled(Feature.PATTERN_ID)
        else providers.Singleton(DummyService)
    )

    # Practical consequence engine
    practical_consequence_engine = (
        providers.Singleton(PracticalConsequenceEngine)
        if MODULES_CORE_IMPORT_OK and is_enabled(Feature.PRACTICAL_CONSEQUENCE)
        else providers.Singleton(DummyService)
    )

    # Metrics engine
    metrics_engine = (
        providers.Singleton(
            MetricsSpecificEngine,
            alpha=config.metrics_engine_alpha,
            thresholds=config.metrics_engine_thresholds,
        )
        if MODULES_CORE_IMPORT_OK
        else providers.Singleton(DummyService)
    )

    # Seed manager
    seed_manager = (
        providers.Singleton(SeedManager)
        if MODULES_CORE_IMPORT_OK
        else providers.Singleton(DummyService)
    )

    # Relational manager
    relational_manager = (
        providers.Singleton(RelationalManager, llm_client=llm_client)
        if MODULES_CORE_IMPORT_OK and LLM_IMPORT_OK and is_enabled(Feature.RELATIONAL)
        else providers.Singleton(DummyService)
    )

    # Narrative engine
    narrative_engine = (
        providers.Singleton(NarrativeModesEngine, config=config.narrative_engine_config)
        if MODULES_CORE_IMPORT_OK and is_enabled(Feature.NARRATIVE_MODES)
        else providers.Singleton(DummyService)
    )

    # XP Mastery system
    xp_mastery = (
        providers.Singleton(XPMastery)
        if MODULES_CORE_IMPORT_OK and is_enabled(Feature.XP_MASTERY)
        else providers.Singleton(DummyService)
    )

    # Emotional integrity engine
    emotional_integrity_engine = (
        providers.Singleton(EmotionalIntegrityIndex, llm_client=llm_client)
        if MODULES_CORE_IMPORT_OK
        and LLM_IMPORT_OK
        and is_enabled(Feature.EMOTIONAL_INTEGRITY)
        else providers.Singleton(DummyService)
    )

    # Semantic memory manager
    semantic_memory_manager: providers.Provider[SemanticMemoryProtocol] = (
        providers.Singleton(SemanticMemoryManager, llm_client=llm_client)
        if MODULES_CORE_IMPORT_OK
        else providers.Singleton(DummySemanticMemoryManager)
    )

    # Snapshot flow controller
    snapshot_flow_controller = (
        providers.Singleton(
            SnapshotFlowController,
            frequency=config.snapshot_flow_frequency,
            max_snapshots=config.snapshot_flow_max_snapshots,
            semantic_memory_manager=semantic_memory_manager,
        )
        if MODULES_CORE_IMPORT_OK
        else providers.Singleton(DummyService)
    )

    # Desire engine
    desire_engine = (
        providers.Singleton(DesireEngine, llm_client=llm_client)
        if MODULES_CORE_IMPORT_OK
        and LLM_IMPORT_OK
        and is_enabled(Feature.DESIRE_ENGINE)
        else providers.Singleton(DummyService)
    )

    # Financial engine
    financial_engine = (
        providers.Singleton(FinancialReadinessEngine, llm_client=llm_client)
        if MODULES_CORE_IMPORT_OK
        and LLM_IMPORT_OK
        and is_enabled(Feature.FINANCIAL_READINESS)
        else providers.Singleton(DummyService)
    )

    # Offering router
    offering_router = (
        providers.Singleton(
            OfferingRouter,
            llm_client=llm_client,
            desire_engine=desire_engine,
            financial_engine=financial_engine,
        )
        if MODULES_CORE_IMPORT_OK and LLM_IMPORT_OK and is_enabled(Feature.REWARDS)
        else providers.Singleton(DummyService)
    )

    # Task engine
    task_engine = (
        providers.Singleton(
            TaskEngine,
            pattern_engine=pattern_engine,
            task_templates=config.task_engine_templates,
        )
        if MODULES_CORE_IMPORT_OK and is_enabled(Feature.CORE_HTA)
        else providers.Singleton(DummyService)
    )

    # Trigger phrase handler
    trigger_phrase_handler = (
        providers.Singleton(TriggerPhraseHandler)
        if MODULES_CORE_IMPORT_OK and is_enabled(Feature.TRIGGER_PHRASES)
        else providers.Singleton(DummyService)
    )

    # Silent scorer
    silent_scorer = (
        providers.Singleton(SilentScoring)
        if MODULES_CORE_IMPORT_OK
        else providers.Singleton(DummyService)
    )

    # Harmonic router
    harmonic_router = (
        providers.Singleton(HarmonicRouting)
        if MODULES_CORE_IMPORT_OK
        else providers.Singleton(DummyService)
    )

    # Task footprint logger
    task_footprint_logger = (
        providers.Singleton(TaskFootprintLogger)
        if MODULES_CORE_IMPORT_OK
        else providers.Singleton(DummyService)
    )
    # Dictionary of managed engines for component state management
    managed_engines_dict = providers.Dict(
        {
            "metrics_engine": metrics_engine,
            "seed_manager": seed_manager,
            "relational_manager": relational_manager,
            "sentiment_engine_calibration": sentiment_engine,
            "practical_consequence": practical_consequence_engine,
            "xp_mastery": xp_mastery,
            "pattern_engine_config": pattern_engine,
            "narrative_engine_config": narrative_engine,
            "emotional_integrity_index": emotional_integrity_engine,
            "desire_engine": desire_engine,
            "financial_readiness_engine": financial_engine,
            "semantic_memory": semantic_memory_manager,
        }
    )

    # Component state manager
    component_state_manager = (
        providers.Singleton(ComponentStateManager, managed_engines=managed_engines_dict)
        if MODULES_CORE_IMPORT_OK
        else providers.Singleton(DummyService)
    )

    # HTA Service
    hta_service = (
        providers.Singleton(
            HTAService,
            llm_client=llm_client,
            seed_manager=seed_manager,
            semantic_memory_manager=semantic_memory_manager,
        )
        if MODULES_CORE_IMPORT_OK
        else providers.Singleton(DummyService)
    )

    # Reflection processor
    reflection_processor = (
        providers.Singleton(
            ReflectionProcessor,
            llm_client=llm_client,
            task_engine=task_engine,
            sentiment_engine=sentiment_engine,
            practical_consequence_engine=practical_consequence_engine,
            narrative_engine=narrative_engine,
            silent_scorer=silent_scorer,
            harmonic_router=harmonic_router,
            semantic_memory_manager=semantic_memory_manager,
        )
        if MODULES_CORE_IMPORT_OK
        else providers.Singleton(DummyService)
    )

    # Completion processor
    completion_processor = (
        providers.Singleton(
            CompletionProcessor,
            hta_service=hta_service,
            task_engine=task_engine,
            xp_mastery=xp_mastery,
            llm_client=llm_client,
            semantic_memory_manager=semantic_memory_manager,
        )
        if MODULES_CORE_IMPORT_OK
        else providers.Singleton(DummyService)
    )

    # Discovery journey service
    discovery_journey_service = (
        providers.Singleton(
            DiscoveryJourneyService,
            hta_service=hta_service,
            llm_client=llm_client,
            semantic_memory_manager=semantic_memory_manager,
        )
        if MODULES_CORE_IMPORT_OK and DISCOVERY_JOURNEY_IMPORT_OK
        else providers.Singleton(DummyService)
    )

    # Main orchestrator
    orchestrator = (
        providers.Singleton(
            ForestOrchestrator,
            reflection_processor=reflection_processor,
            completion_processor=completion_processor,
            state_manager=component_state_manager,
            hta_service=hta_service,
            seed_manager=seed_manager,
            semantic_memory_manager=semantic_memory_manager,
        )
        if MODULES_CORE_IMPORT_OK
        else providers.Singleton(DummyService)
    )


class ContainerManager:
    """Manages the dependency injection container instance."""

    _instance = None
    _initialized = False

    @classmethod
    def get_instance(cls) -> Container:
        """Get or create the container instance.

        Returns:
            Container: The initialized dependency injection container
        """
        if cls._instance is None:
            cls._instance = Container()
            cls._instance.config.from_dict({"test": "test"})
            cls._initialized = True
        return cls._instance

    @classmethod
    def initialize_wiring(cls) -> None:
        """Initialize container wiring."""
        if cls._initialized and cls._instance is not None:
            try:
                cls._instance.wire(modules=Container.wiring_config.modules)
                logger.info("DI Container wiring applied successfully.")
            except (AttributeError, ImportError, ValueError) as wire_err:
                logger.critical("DI Container wiring failed: %s", wire_err)
                raise


# Initialize the container when module is imported
if __name__ == "__main__":
    CONTAINER = ContainerManager.get_instance()
    ContainerManager.initialize_wiring()
else:
    # Initialize wiring when imported as a module
    CONTAINER = ContainerManager.get_instance()
    ContainerManager.initialize_wiring()
