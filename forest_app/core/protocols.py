from datetime import datetime
from typing import Any, Dict, List, Optional, Protocol, Union
from uuid import UUID


class HTANodeProtocol(Protocol):
    node_id: UUID
    parent_id: Optional[UUID]
    title: str
    description: str
    children: List["HTANodeProtocol"]
    completion_status: float  # 0.0 to 1.0
    created_at: datetime
    updated_at: datetime
    metadata: Dict[str, Any]

    def add_child(self, node: "HTANodeProtocol") -> None: ...
    def remove_child(self, node_id: UUID) -> None: ...
    def update_completion(self) -> None: ...
    def get_frontier_tasks(self) -> List["HTANodeProtocol"]: ...


class HTATreeProtocol(Protocol):
    root: HTANodeProtocol

    def get_node(self, node_id: UUID) -> Optional[HTANodeProtocol]: ...
    def update_node(self, node_id: UUID, updates: Dict[str, Any]) -> None: ...
    def propagate_completion(self, node_id: UUID) -> None: ...
    def get_all_frontier_tasks(self) -> List[HTANodeProtocol]: ...


class TaskEngineProtocol(Protocol):
    def generate_task_batch(self, context: Dict[str, Any]) -> List[HTANodeProtocol]: ...
    def recommend_next_tasks(self, count: int = 3) -> List[HTANodeProtocol]: ...

    def update_task_status(self, task_id: UUID, completion: float) -> None: ...


class SemanticMemoryProtocol(Protocol):
    def store_milestone(
        self, node_id: UUID, description: str, impact: float
    ) -> None: ...

    def store_reflection(
        self, reflection_type: str, content: str, emotion: Optional[str] = None
    ) -> None: ...

    def get_relevant_memories(
        self, context: str, limit: int = 5
    ) -> List[Dict[str, Any]]: ...
    def update_context(self, new_context: Dict[str, Any]) -> None: ...


class HTAServiceProtocol(Protocol):
    """Protocol defining the interface for HTA (Hierarchical Task Analysis) services.

    This protocol ensures consistent implementation across different HTA service classes,
    enforcing a standard API for managing task hierarchies, tree operations, and status updates.
    """

    def initialize_task_hierarchy(
        self, task_id: str, hierarchy_data: Dict[str, Any]
    ) -> None: ...

    def update_task_state(self, task_id: str, state_data: Dict[str, Any]) -> None: ...

    def get_task_hierarchy(self, task_id: str) -> Optional[Dict[str, Any]]: ...

    def load_tree(self, snapshot: Any) -> Optional[Any]: ...

    def save_tree(self, snapshot: Any, tree: Any) -> bool: ...

    def update_node_status(
        self, tree: Any, node_id: Union[str, UUID], new_status: str
    ) -> bool: ...

    def evolve_tree(
        self, tree: Any, reflections: List[str], user_mood: Optional[str] = None
    ) -> Optional[Any]: ...
