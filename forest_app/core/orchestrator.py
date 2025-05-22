# forest_app/core/orchestrator.py (REFACTORED)

import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Callable
import threading

try:
    from sqlalchemy.orm import Session
except ImportError as e:
    logging.error(f"Failed to import Session: {e}")
    class Session:
        pass

try:
    from forest_app.utils.error_handling import log_import_error
except ImportError as e:
    def log_import_error(error, module_name=None):
        logging.error(f"Import error in {module_name or 'unknown module'}: {error}")

# Core imports with error handling
try:
    from uuid import UUID
    from forest_app.core.processors import CompletionProcessor, ReflectionProcessor
    from forest_app.core.services import (
        ComponentStateManager,
        HTAService,
        SemanticMemoryManager,
    )
    from forest_app.core.services.enhanced_hta.memory import HTAMemoryManager
    from forest_app.core.snapshot import MemorySnapshot
    from forest_app.core.utils import clamp01
    from forest_app.models import HTANodeModel
    from forest_app.modules.logging_tracking import (
        ReflectionLogLogger,
        TaskFootprintLogger,
    )
    from forest_app.modules.seed import Seed, SeedManager
    from forest_app.modules.soft_deadline_manager import hours_until_deadline
    from forest_app.persistence.repository import HTATreeRepository
except ImportError as e:
    log_import_error(e, "orchestrator.py")
    class MemorySnapshot:
        pass
    class ReflectionProcessor:
        pass
    class CompletionProcessor:
        pass
    class ComponentStateManager:
        pass
    class SemanticMemoryManager:
        pass
    class HTAMemoryManager:
        pass
    class SeedManager:
        pass
    class Seed:
        pass
    class TaskFootprintLogger:
        pass
    class ReflectionLogLogger:
        pass
    class HTATreeRepository:
        pass
    class HTANodeModel:
        pass
    class UUID:
        pass
    def clamp01(x):
        return x
    def hours_until_deadline(x):
        return 0

try:
    from forest_app.core.feature_flags import Feature, is_enabled
except ImportError:
    def is_enabled(feature):
        return False
    class Feature:
        SOFT_DEADLINES = "FEATURE_ENABLE_SOFT_DEADLINES"

try:
    from forest_app.config.constants import (
        MAGNITUDE_THRESHOLDS,
        WITHERING_COMPLETION_RELIEF,
        WITHERING_DECAY_FACTOR,
        WITHERING_IDLE_COEFF,
        WITHERING_OVERDUE_COEFF,
    )
except ImportError:
    MAGNITUDE_THRESHOLDS = {"HIGH": 8.0, "MEDIUM": 5.0, "LOW": 2.0}
    WITHERING_COMPLETION_RELIEF = 0.1
    WITHERING_IDLE_COEFF = {"structured": 0.1}
    WITHERING_OVERDUE_COEFF = 0.1
    WITHERING_DECAY_FACTOR = 0.9

try:
    from forest_app.modules.types import SemanticMemoryProtocol
except ImportError as e:
    logging.error(f"Failed to import SemanticMemoryProtocol: {e}")
    class SemanticMemoryProtocol:
        pass

try:
    from forest_app.core.session_management import run_forest_session, run_forest_session_async
except ImportError as e:
    logging.error(f"Failed to import session management functions: {e}")
    def run_forest_session(*args, **kwargs):
        pass
    def run_forest_session_async(*args, **kwargs):
        pass

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# ═════════════════════════════ ForestOrchestrator (Refactored) ══════════════


class ForestOrchestrator:
    """
    Orchestrates the Forest OS session lifecycle and state management.
    """

    # ───────────────────────── 1. INITIALISATION (DI Based) ─────────────────
    def __init__(
        self,
        reflection_processor: ReflectionProcessor,
        completion_processor: CompletionProcessor,
        state_manager: ComponentStateManager,
        hta_service: HTAService,
        seed_manager: SeedManager,
        semantic_memory_manager: SemanticMemoryProtocol,
        memory_manager: Optional[HTAMemoryManager] = None,
        tree_repository: Optional[HTATreeRepository] = None,
        task_logger: Optional[TaskFootprintLogger] = None,
        reflection_logger: Optional[ReflectionLogLogger] = None,
        llm_client=None,
        saver: Callable[[Dict[str, Any]], None] = None,
    ):
        """Initializes the orchestrator with injected processors and services."""
        self.reflection_processor = reflection_processor
        self.completion_processor = completion_processor
        self.state_manager = state_manager
        self.hta_service = hta_service
        self.seed_manager = seed_manager
        self.semantic_memory_manager = semantic_memory_manager
        self.memory_manager = memory_manager
        self.tree_repository = tree_repository
        self.task_logger = task_logger
        self.reflection_logger = reflection_logger
        self.llm_client = llm_client
        self.logger = logging.getLogger(__name__)
        self._saver = saver

        # Check critical dependencies
        if not isinstance(self.reflection_processor, ReflectionProcessor):
            raise TypeError("Invalid ReflectionProcessor provided.")
        if not isinstance(self.completion_processor, CompletionProcessor):
            raise TypeError("Invalid CompletionProcessor provided.")
        if not isinstance(self.state_manager, ComponentStateManager):
            raise TypeError("Invalid ComponentStateManager provided.")
        if not isinstance(self.seed_manager, SeedManager):
            raise TypeError("Invalid SeedManager provided.")
        # Add checks for other injected components like hta_service if kept

        logger.info("ForestOrchestrator (Refactored) initialized.")

    # ───────────────────────── 2. CORE WORKFLOWS ────────────────────────────

    async def process_reflection(
        self, reflection_text: str, snapshot: Any = None
    ) -> Dict[str, Any]:
        """Process a reflection with semantic memory integration."""
        try:
            # Store reflection as semantic memory
            await self.semantic_memory_manager.store_memory(
                event_type="reflection",
                content=reflection_text,
                metadata={"timestamp": datetime.now(timezone.utc).isoformat()},
                importance=0.7,  # Reflections are generally important
            )

            # Query relevant memories for context
            relevant_memories = await self.semantic_memory_manager.query_memories(
                query=reflection_text, k=3, event_types=["reflection"]
            )

            # Process reflection with context from semantic memory
            result = await self.reflection_processor.process_reflection(
                reflection_text=reflection_text,
                context={"relevant_memories": relevant_memories},
                snapshot=snapshot,
            )

            return {
                "processed_reflection": result,
                "relevant_memories": relevant_memories,
            }

        except Exception as e:
            self.logger.error("Error in process_reflection: %s", e)
            raise

    async def process_task_completion(
        self,
        task_id: str,
        success: bool,
        snap: Optional[MemorySnapshot] = None,
        db: Optional[Session] = None,
        task_logger: Optional[TaskFootprintLogger] = None,
        reflection: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Process a task completion with full transactional integrity.

        This method implements Task 1.5 requirements, ensuring atomic updates,
        memory snapshot updates, audit logging, and positive reinforcement.
        It handles both task node updates and roadmap manifest synchronization.

        Args:
            task_id: UUID or string ID of the task/node to complete
            success: Whether the task was completed successfully
            snap: Optional MemorySnapshot for context and update
            db: Optional database session for transaction context
            task_logger: Optional logger for task footprints (overrides instance logger)
            reflection: Optional user reflection on the completion

        Returns:
            Dictionary with completion results, including supportive message
        """
        try:
            self.logger.info(
                "Processing task completion for task %s, success=%s", task_id, success
            )

            # Convert string UUID to UUID if needed
            node_id = UUID(task_id) if isinstance(task_id, str) else task_id

            # Extract user_id from snapshot if available
            user_id = None
            if snap and hasattr(snap, "user_id"):
                user_id = snap.user_id
            elif snap and hasattr(snap, "user") and hasattr(snap.user, "id"):
                user_id = snap.user.id

            if not user_id:
                self.logger.warning(
                    "No user ID available in snapshot for task completion"
                )
                # Attempt to retrieve user_id from the node if possible
                if self.tree_repository:
                    try:
                        node = await self.tree_repository.get_node_by_id(node_id)
                        if node:
                            user_id = node.user_id
                    except Exception as node_err:
                        self.logger.warning(
                            "Error getting node for user ID: %s", node_err
                        )

            if not user_id:
                self.logger.error("Cannot complete task: No user ID available")
                raise ValueError("No user ID available for task completion")

            # Use enhanced implementation if all required components are available
            if all(
                [self.completion_processor, self.tree_repository, self.memory_manager]
            ):
                # Use the enhanced CompletionProcessor implementation for Task 1.5
                result = await self.completion_processor.process_node_completion(
                    node_id=node_id,
                    user_id=user_id,
                    success=success,
                    reflection=reflection,
                    db_session=db,
                )

                # Update snapshot with reinforcement message if available
                if snap and result.get("reinforcement_message"):
                    # Add the message to the snapshot if it has a messages array
                    if hasattr(snap, "messages") and isinstance(snap.messages, list):
                        snap.messages.append(
                            {
                                "type": "system",
                                "content": result.get("reinforcement_message"),
                                "timestamp": datetime.now(timezone.utc).isoformat(),
                                "is_reinforcement": True,
                            }
                        )
                    # Update last activity timestamp
                    if hasattr(snap, "component_state") and isinstance(
                        snap.component_state, dict
                    ):
                        snap.component_state["last_activity_ts"] = datetime.now(
                            timezone.utc
                        ).isoformat()

                    # Reduce withering level on task completion
                    if hasattr(snap, "withering_level"):
                        current_level = getattr(snap, "withering_level", 0.0)
                        if isinstance(current_level, (int, float)):
                            snap.withering_level = max(
                                0.0, current_level - WITHERING_COMPLETION_RELIEF
                            )
                return result

            # Fall back to legacy implementation if components are missing
            self.logger.warning(
                "Using legacy completion flow - some Task 1.5 features unavailable"
            )
            completion_data = {
                "success": success,
                "reflection": reflection or "",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

            return await self.complete_task(task_id, completion_data)

        except Exception as e:
            self.logger.error("Error processing task completion: %s", e)
            raise

    async def complete_task(
        self, task_id: str, completion_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Complete a task with semantic memory integration (legacy method).

        Note: This is maintained for backward compatibility. For new code,
        prefer using process_task_completion which implements Task 1.5 requirements.
        """
        try:
            # Store task completion as semantic memory
            await self.semantic_memory_manager.store_memory(
                event_type="task_completion",
                content=f"Completed task {task_id}: {completion_data.get('summary', '')}",
                metadata={
                    "task_id": task_id,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    **completion_data,
                },
                importance=0.6,
            )

            # Process task completion
            result = await self.completion_processor.process_completion(
                task_id, completion_data
            )

            return result

        except Exception as e:
            self.logger.error("Error in complete_task: %s", e)
            raise

    async def get_memory_context(self, query: str = None) -> Dict[str, Any]:
        """Get relevant memory context for the current state."""
        try:
            memories = await self.semantic_memory_manager.query_memories(
                query=query or "Get recent important memories", k=5
            )

            stats = self.semantic_memory_manager.get_memory_stats()

            return {"relevant_memories": memories, "memory_stats": stats}

        except Exception as e:
            self.logger.error("Error in get_memory_context: %s", e)
            raise

    # ───────────────────────── 3. UTILITY & DELEGATION ──────────────────────

    def _update_withering(self, snapshot: Dict[str, Any]) -> None:
        """
        Update withering scores for tasks and goals based on time elapsed.

        Args:
            snapshot: Current session snapshot
        """
        try:
            # Update task withering
            tasks = snapshot.get("tasks", [])
            for task in tasks:
                if "withering" not in task:
                    task["withering"] = 0.0
                task["withering"] = min(1.0, task["withering"] + 0.1)

            # Update goal withering
            goals = snapshot.get("goals", [])
            for goal in goals:
                if "withering" not in goal:
                    goal["withering"] = 0.0
                goal["withering"] = min(1.0, goal["withering"] + 0.05)

        except Exception as e:
            logger.error("Error updating withering: %s", e, exc_info=True)
            raise

    def _save_component_states(self, snapshot: Dict[str, Any]) -> None:
        """
        Save the current state of all components.

        Args:
            snapshot: Current session snapshot
        """
        try:
            self._saver(snapshot)
        except Exception as e:
            logger.error("Error saving component states: %s", e, exc_info=True)
            raise

    def start_session(
        self,
        snapshot: Dict[str, Any],
        lock: Optional[threading.Lock] = None,
        async_mode: bool = False
    ) -> None:
        """
        Start a new Forest OS session with heartbeat management.

        Args:
            snapshot: Session snapshot to manage
            lock: Optional thread lock for thread-safe operations
            async_mode: Whether to run in async mode
        """
        if async_mode:
            run_forest_session_async(snapshot, self._saver, lock)
        else:
            run_forest_session(snapshot, self._saver, lock)

    # Example: Keeping get_primary_active_seed here, but could be moved to SeedManager
    async def get_primary_active_seed(self) -> Optional[Seed]:
        """Retrieves the first active seed using the injected SeedManager."""
        if not self.seed_manager or not hasattr(
            self.seed_manager, "get_primary_active_seed"
        ):
            logger.error(
                "Injected SeedManager missing or invalid for get_primary_active_seed."
            )
            return None
        try:
            # Assuming get_primary_active_seed is now async in SeedManager
            return await self.seed_manager.get_primary_active_seed()
        except Exception as e:
            logger.exception(
                "Error getting primary active seed via orchestrator: %s", e
            )
            return None

    # Convenience APIs delegating to SeedManager
    async def plant_seed(
        self, intention: str, domain: str, addl_ctx: Optional[Dict[str, Any]] = None
    ) -> Optional[Seed]:
        logger.info("Orchestrator: Delegating plant_seed to SeedManager...")
        if not self.seed_manager or not hasattr(self.seed_manager, "plant_seed"):
            logger.error("Injected SeedManager missing or invalid for plant_seed.")
            return None
        try:
            # Assuming plant_seed is now async in SeedManager
            return await self.seed_manager.plant_seed(intention, domain, addl_ctx)
        except Exception as exc:
            logger.exception("Orchestrator plant_seed delegation error: %s", exc)
            return None

    async def trigger_seed_evolution(
        self, seed_id: str, evolution: str, new_intention: Optional[str] = None
    ) -> bool:
        logger.info("Orchestrator: Delegating trigger_seed_evolution to SeedManager...")
        if not self.seed_manager or not hasattr(self.seed_manager, "evolve_seed"):
            logger.error("Injected SeedManager missing or invalid for evolve_seed.")
            return False
        try:
            # Assuming evolve_seed is now async in SeedManager
            return await self.seed_manager.evolve_seed(
                seed_id, evolution, new_intention
            )
        except Exception as exc:
            logger.exception(
                "Orchestrator trigger_seed_evolution delegation error: %s", exc
            )
            return False
