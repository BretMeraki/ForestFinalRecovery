# forest_app/core/snapshot.py (MODIFIED FOR BATCH TRACKING)
import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

try:
    from .feature_flags import Feature, is_enabled
except ImportError:
    logging.warning(
        "Feature flags module not found. Feature flag recording in snapshot will be disabled."
    )

    class Feature:
        pass

    def is_enabled(feature: Any) -> bool:
        return False


logger = logging.getLogger(__name__)


class MemorySnapshot:
    """Serializable container for user journey state with semantic memory integration."""

    def __init__(self) -> None:
        self.shadow_score: float = 0.50
        self.capacity: float = 0.50
        self.magnitude: float = 5.00
        self.resistance: float = 0.00
        self.relationship_index: float = 0.50
        self.story_beats: List[Dict[str, Any]] = []
        self.totems: List[Dict[str, Any]] = []
        self.wants_cache: Dict[str, float] = {}
        self.partner_profiles: Dict[str, Dict[str, Any]] = {}
        self.withering_level: float = 0.00
        self.activated_state: Dict[str, Any] = {
            "activated": False,
            "mode": None,
            "goal_set": False,
        }
        self.core_state: Dict[str, Any] = {}
        self.decor_state: Dict[str, Any] = {}
        self.current_path: str = "structured"
        self.estimated_completion_date: Optional[str] = None
        self.reflection_context: Dict[str, Any] = {
            "themes": [],
            "recent_insight": "",
            "current_priority": "",
        }
        self.reflection_log: List[Dict[str, Any]] = []
        self.task_backlog: List[Dict[str, Any]] = []
        self.task_footprints: List[Dict[str, Any]] = []
        self.conversation_history: List[Dict[str, str]] = []
        self.feature_flags: Dict[str, bool] = {}
        self.current_frontier_batch_ids: List[str] = []
        self.current_batch_reflections: List[str] = []
        self.component_state: Dict[str, Any] = {
            "sentiment_engine_calibration": {},
            "metrics_engine": {},
            "seed_manager": {},
            "archetype_manager": {},
            "dev_index": {},
            "memory_system": {},
            "xp_mastery": {},
            "pattern_engine_config": {},
            "emotional_integrity_index": {},
            "desire_engine": {},
            "resistance_engine": {},
            "reward_index": {},
            "last_issued_task_id": None,
            "last_activity_ts": None,
        }
        self.semantic_memories: Dict[str, Any] = {
            "memories": [],
            "stats": {
                "total_memories": 0,
                "memory_types": {},
                "avg_importance": 0.0,
                "avg_access_count": 0.0,
            },
        }
        self.memory_context: Dict[str, Any] = {
            "recent_memories": [],
            "relevant_memories": [],
            "memory_themes": [],
            "last_memory_query": None,
            "memory_stats": {
                "total_queries": 0,
                "avg_relevance_score": 0.0,
                "most_common_themes": [],
            },
        }
        self.template_metadata: Dict[str, Any] = {}
        self.last_ritual_mode: str = "Trail"
        self.timestamp: str = datetime.now(timezone.utc).isoformat()

    def record_feature_flags(self) -> None:
        self.feature_flags = {}
        if Feature is not None and hasattr(Feature, "__members__"):
            for feature_name, feature_enum in Feature.__members__.items():
                try:
                    self.feature_flags[feature_name] = is_enabled(feature_enum)
                except Exception as exc:
                    logger.error(
                        "Error checking feature flag %s: %s", feature_name, exc
                    )
                    self.feature_flags[feature_name] = False
        else:
            logger.warning("Feature enum not available, cannot record feature flags.")
        logger.debug("Recorded feature flags: %s", self.feature_flags)

    def to_dict(self) -> Dict[str, Any]:
        self.timestamp = datetime.now(timezone.utc).isoformat()
        data = {
            "shadow_score": self.shadow_score,
            "capacity": self.capacity,
            "magnitude": self.magnitude,
            "resistance": self.resistance,
            "relationship_index": self.relationship_index,
            "story_beats": self.story_beats,
            "totems": self.totems,
            "wants_cache": self.wants_cache,
            "partner_profiles": self.partner_profiles,
            "withering_level": self.withering_level,
            "activated_state": self.activated_state,
            "core_state": self.core_state,
            "decor_state": self.decor_state,
            "current_path": self.current_path,
            "estimated_completion_date": self.estimated_completion_date,
            "reflection_context": self.reflection_context,
            "reflection_log": self.reflection_log,
            "task_backlog": self.task_backlog,
            "task_footprints": self.task_footprints,
            "conversation_history": self.conversation_history,
            "feature_flags": self.feature_flags,
            "current_frontier_batch_ids": self.current_frontier_batch_ids,
            "current_batch_reflections": self.current_batch_reflections,
            "component_state": self.component_state,
            "semantic_memories": self.semantic_memories,
            "memory_context": self.memory_context,
            "template_metadata": self.template_metadata,
            "last_ritual_mode": self.last_ritual_mode,
            "timestamp": self.timestamp,
        }
        return data

    def update_from_dict(self, data: Dict[str, Any]) -> None:
        if not isinstance(data, dict):
            logger.error(
                "Invalid data passed to update_from_dict: expected dict, got %s",
                type(data),
            )
            return
        attributes_to_load = [
            "shadow_score",
            "capacity",
            "magnitude",
            "resistance",
            "relationship_index",
            "activated_state",
            "core_state",
            "decor_state",
            "reflection_context",
            "reflection_log",
            "task_backlog",
            "task_footprints",
            "story_beats",
            "totems",
            "wants_cache",
            "partner_profiles",
            "withering_level",
            "current_path",
            "estimated_completion_date",
            "template_metadata",
            "last_ritual_mode",
            "timestamp",
            "conversation_history",
            "feature_flags",
            "current_frontier_batch_ids",
            "current_batch_reflections",
            "semantic_memories",
            "memory_context",
        ]
        for attr in attributes_to_load:
            if attr in data:
                value = data[attr]
                expected_type = list
                default_value = []
                if attr in [
                    "core_state",
                    "feature_flags",
                    "component_state",
                    "activated_state",
                    "decor_state",
                    "reflection_context",
                    "wants_cache",
                    "partner_profiles",
                    "template_metadata",
                    "semantic_memories",
                    "memory_context",
                ]:
                    expected_type = dict
                    default_value = {}
                elif attr in [
                    "current_path",
                    "estimated_completion_date",
                    "last_ritual_mode",
                    "timestamp",
                ]:
                    expected_type = str
                    default_value = "" if attr != "current_path" else "structured"
                elif attr in [
                    "shadow_score",
                    "capacity",
                    "magnitude",
                    "resistance",
                    "relationship_index",
                    "withering_level",
                ]:
                    expected_type = float
                    default_value = 0.0
                elif attr in [
                    "current_batch_reflections",
                    "current_frontier_batch_ids",
                ]:
                    expected_type = list
                    default_value = []
                if isinstance(value, expected_type):
                    setattr(self, attr, value)
                elif value is None and expected_type in [str, list, dict]:
                    setattr(self, attr, None if expected_type is str else default_value)
                elif expected_type is float and isinstance(value, int):
                    logger.debug("Converting int value for '%s' to float.", attr)
                    setattr(self, attr, float(value))
                else:
                    logger.warning(
                        "Loaded '%s' has wrong type (%s, expected %s), resetting to default.",
                        attr,
                        type(value).__name__,
                        expected_type.__name__,
                    )
                    setattr(self, attr, default_value)
            elif attr in [
                "conversation_history",
                "feature_flags",
                "core_state",
                "component_state",
                "task_backlog",
                "reflection_log",
                "task_footprints",
                "story_beats",
                "totems",
                "current_frontier_batch_ids",
                "current_batch_reflections",
                "semantic_memories",
                "memory_context",
            ]:
                if getattr(self, attr, None) is None:
                    default_value = (
                        []
                        if "list" in str(self.__annotations__.get(attr, "")).lower()
                        or "List" in str(self.__annotations__.get(attr, ""))
                        else {}
                    )
                    logger.debug(
                        "Attribute '%s' missing in loaded data, setting default.", attr
                    )
                    setattr(self, attr, default_value)
        if not isinstance(getattr(self, "conversation_history", []), list):
            self.conversation_history = []
        if not isinstance(getattr(self, "core_state", {}), dict):
            self.core_state = {}
        if not isinstance(getattr(self, "feature_flags", {}), dict):
            self.feature_flags = {}
        if not isinstance(getattr(self, "component_state", {}), dict):
            self.component_state = {}
        if not isinstance(getattr(self, "current_frontier_batch_ids", []), list):
            logger.warning(
                "Post-load current_frontier_batch_ids is not a list (%s), resetting.",
                type(getattr(self, "current_frontier_batch_ids", None)),
            )
            self.current_frontier_batch_ids = []
        if not isinstance(getattr(self, "current_batch_reflections", []), list):
            logger.warning(
                "Post-load current_batch_reflections is not a list (%s), resetting.",
                type(getattr(self, "current_batch_reflections", None)),
            )
            self.current_batch_reflections = []
        loaded_cs = data.get("component_state")
        if isinstance(loaded_cs, dict):
            self.component_state = loaded_cs
        elif loaded_cs is not None:
            logger.warning(
                "Loaded component_state is not a dict (%s), ignoring.", type(loaded_cs)
            )
            if not hasattr(self, "component_state") or not isinstance(
                self.component_state, dict
            ):
                self.component_state = {}
        else:
            if not hasattr(self, "component_state") or not isinstance(
                self.component_state, dict
            ):
                self.component_state = {}
        if not isinstance(getattr(self, "semantic_memories", {}), dict):
            logger.warning("Post-load semantic_memories is not a dict, resetting.")
            self.semantic_memories = {
                "memories": [],
                "stats": {
                    "total_memories": 0,
                    "memory_types": {},
                    "avg_importance": 0.0,
                    "avg_access_count": 0.0,
                },
            }
        if not isinstance(getattr(self, "memory_context", {}), dict):
            logger.warning("Post-load memory_context is not a dict, resetting.")
            self.memory_context = {
                "recent_memories": [],
                "relevant_memories": [],
                "memory_themes": [],
                "last_memory_query": None,
                "memory_stats": {
                    "total_queries": 0,
                    "avg_relevance_score": 0.0,
                    "most_common_themes": [],
                },
            }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MemorySnapshot":
        snap = cls()
        if isinstance(data, dict):
            snap.update_from_dict(data)
            logger.debug(
                "FROM_DICT: Value of instance.core_state['hta_tree'] AFTER update: %s",
                snap.core_state.get("hta_tree", "MISSING_POST_ASSIGNMENT"),
            )
            logger.debug(
                "FROM_DICT: Loaded feature flags AFTER update: %s", snap.feature_flags
            )
            logger.debug(
                "FROM_DICT: Loaded batch IDs AFTER update: %s",
                snap.current_frontier_batch_ids,
            )
            logger.debug(
                "FROM_DICT: Loaded batch reflections count AFTER update: %s",
                len(snap.current_batch_reflections),
            )
        else:
            logger.error(
                "Invalid data passed to MemorySnapshot.from_dict: expected dict, got %s. Returning default snapshot.",
                type(data),
            )
        return snap

    def __str__(self) -> str:
        try:
            repr_dict = {
                "shadow_score": round(getattr(self, "shadow_score", 0.0), 2),
                "capacity": round(getattr(self, "capacity", 0.0), 2),
                "magnitude": round(getattr(self, "magnitude", 0.0), 1),
                "feature_flags_count": len(getattr(self, "feature_flags", {})),
                "batch_ids_count": len(getattr(self, "current_frontier_batch_ids", [])),
                "batch_refl_count": len(getattr(self, "current_batch_reflections", [])),
                "semantic_memories_count": len(
                    self.semantic_memories.get("memories", [])
                ),
                "memory_themes": len(self.memory_context.get("memory_themes", [])),
                "timestamp": getattr(self, "timestamp", "N/A"),
            }
            return f"<Snapshot {json.dumps(repr_dict, default=str)} ...>"
        except Exception as exc:
            logger.error("Snapshot __str__ error: %s", exc)
            return (
                f"<Snapshot ts={getattr(self, 'timestamp', 'N/A')} (error rendering)>"
            )

    def update_memory_context(
        self,
        recent_memories: Optional[List[Dict[str, Any]]] = None,
        relevant_memories: Optional[List[Dict[str, Any]]] = None,
        memory_themes: Optional[List[str]] = None,
        query_info: Optional[Dict[str, Any]] = None,
    ) -> None:
        if recent_memories is not None:
            self.memory_context["recent_memories"] = recent_memories
        if relevant_memories is not None:
            self.memory_context["relevant_memories"] = relevant_memories
        if memory_themes is not None:
            self.memory_context["memory_themes"] = memory_themes
        if query_info is not None:
            self.memory_context["last_memory_query"] = query_info
            stats = self.memory_context["memory_stats"]
            stats["total_queries"] += 1
            if "relevance_score" in query_info:
                current_avg = stats["avg_relevance_score"]
                stats["avg_relevance_score"] = (
                    current_avg * (stats["total_queries"] - 1)
                    + query_info["relevance_score"]
                ) / stats["total_queries"]
            if "themes" in query_info:
                current_themes = set(stats["most_common_themes"])
                new_themes = set(query_info["themes"])
                combined_themes = list(current_themes.union(new_themes))
                stats["most_common_themes"] = combined_themes[:10]

    def update_semantic_memories(
        self,
        new_memories: Optional[List[Dict[str, Any]]] = None,
        stats_update: Optional[Dict[str, Any]] = None,
    ) -> None:
        if new_memories is not None:
            self.semantic_memories["memories"].extend(new_memories)
        if stats_update is not None:
            self.semantic_memories["stats"].update(stats_update)

    def get_relevant_memories(
        self, context: str, limit: int = 5, memory_types: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        memories = self.memory_context["relevant_memories"]
        if memory_types:
            memories = [m for m in memories if m.get("type") in memory_types]
        memories.sort(key=lambda x: x.get("relevance", 0.0), reverse=True)
        return memories[:limit]
