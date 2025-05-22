# forest_app/persistence/models.py

import uuid
from datetime import datetime
from enum import Enum as PyEnum
from typing import Any, Dict, List, Optional  # Ensure basic types are imported

# --- SQLAlchemy Imports ---
from sqlalchemy import Boolean, DateTime, ForeignKey, Index, String, Text, Column
from sqlalchemy import Enum as SqlAlchemyEnum

# --- ADDED/MODIFIED IMPORT for PostgreSQL types ---
from sqlalchemy.dialects.postgresql import (  # Import specifically for PostgreSQL
    JSONB,
    UUID,
)
from sqlalchemy.dialects.sqlite import JSON as SQLITE_JSON

# --- END ADDED/MODIFIED IMPORT ---
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func  # For server-side timestamp defaults
from sqlalchemy.types import TEXT, TypeDecorator


class JSONType(TypeDecorator):
    """Platform-independent JSON type: uses JSONB for Postgres, JSON for SQLite, TEXT fallback."""

    impl = TEXT
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            return dialect.type_descriptor(JSONB())
        elif dialect.name == "sqlite":
            try:
                return dialect.type_descriptor(SQLITE_JSON())
            except ImportError:
                return dialect.type_descriptor(TEXT())
        else:
            return dialect.type_descriptor(TEXT())

    def process_bind_param(self, value, dialect):
        import json

        if value is not None:
            return json.dumps(value)
        return None

    def process_result_value(self, value, dialect):
        import json

        if value is not None:
            return json.loads(value)
        return None


# --- Base Class ---
Base = declarative_base()


# --- Status Enum for HTA Nodes ---
class HTAStatus(str, PyEnum):
    """Status enum for HTA nodes, standardized across the application."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    DEFERRED = "deferred"
    CANCELLED = "cancelled"


# --- User Model with UUID ---
class UserModel(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # --- Relationships ---
    snapshots = relationship("MemorySnapshotModel", back_populates="user", cascade="all, delete-orphan")
    task_footprints = relationship("TaskFootprintModel", back_populates="user", cascade="all, delete-orphan")
    reflection_logs = relationship("ReflectionLogModel", back_populates="user", cascade="all, delete-orphan")
    hta_trees = relationship("HTATreeModel", back_populates="user", cascade="all, delete-orphan")
    hta_nodes = relationship("HTANodeModel", back_populates="user", cascade="all, delete-orphan")


# --- HTA Tree Model ---
class HTATreeModel(Base):
    __tablename__ = "hta_trees"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), index=True)
    goal_name = Column(String(255), nullable=False)
    initial_context = Column(Text, nullable=True)
    top_node_id = Column(UUID(as_uuid=True), ForeignKey("hta_nodes.id"), nullable=True)
    initial_roadmap_depth = Column(nullable=True)
    initial_task_count = Column(nullable=True)
    manifest = Column(JSONType, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # --- Relationships ---
    user = relationship("UserModel", back_populates="hta_trees")
    top_node = relationship("HTANodeModel", foreign_keys=[top_node_id])
    nodes = relationship(
        "HTANodeModel",
        primaryjoin="HTATreeModel.id == HTANodeModel.tree_id",
        back_populates="tree",
        cascade="all, delete-orphan",
    )

    # --- Create indexes for common query patterns ---
    __table_args__ = (
        Index("idx_hta_trees_user_id_created_at", user_id, created_at),
        # Add GIN index for manifest JSONB to support efficient queries
        Index("idx_hta_trees_manifest_gin", manifest, postgresql_using="gin"),
    )


# --- HTA Node Model ---
class HTANodeModel(Base):
    __tablename__ = "hta_nodes"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), index=True)
    parent_id = Column(UUID(as_uuid=True), ForeignKey("hta_nodes.id"), nullable=True, index=True)
    tree_id = Column(UUID(as_uuid=True), ForeignKey("hta_trees.id"), index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    is_leaf = Column(Boolean, default=True)
    status = Column(
        SqlAlchemyEnum("pending", "in_progress", "completed", name="hta_status_enum"),
        default="pending",
        index=True,
    )
    roadmap_step_id = Column(UUID(as_uuid=True), nullable=True, index=True)
    internal_task_details = Column(JSONType, nullable=True, default=lambda: {})
    journey_summary = Column(JSONType, nullable=True, default=lambda: {})
    branch_triggers = Column(
        JSONType,
        nullable=True,
        default=lambda: {
            "expand_now": False,
            "completion_count_for_expansion_trigger": 3,
            "current_completion_count": 0,
        },
    )
    is_major_phase = Column(Boolean, default=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # --- Relationships ---
    user = relationship("UserModel", back_populates="hta_nodes")
    tree = relationship("HTATreeModel", back_populates="nodes", foreign_keys=[tree_id])
    parent = relationship("HTANodeModel", remote_side=[id], back_populates="children")
    children = relationship("HTANodeModel", back_populates="parent", cascade="all, delete-orphan")

    # --- Create indexes for common query patterns ---
    __table_args__ = (
        # For finding nodes in a tree with a specific status
        Index("idx_hta_nodes_tree_id_status", tree_id, status),
        # For finding major phases with a specific status
        Index(
            "idx_hta_nodes_tree_id_is_major_phase_status",
            tree_id,
            is_major_phase,
            status,
        ),
        # For finding child nodes of a parent with a specific status
        Index("idx_hta_nodes_parent_id_status", parent_id, status),
    )


# --- Memory Snapshot Model ---
class MemorySnapshotModel(Base):
    __tablename__ = "memory_snapshots"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    snapshot_data = Column(JSONType, nullable=True)
    codename = Column(String, nullable=True)  # Added codename field
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # --- Relationships ---
    user = relationship("UserModel", back_populates="snapshots")


# --- Task Footprint Model ---
class TaskFootprintModel(Base):
    __tablename__ = "task_footprints"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    task_id = Column(String, index=True, nullable=False)
    event_type = Column(String, nullable=False)  # e.g., 'issued', 'completed', 'failed', 'skipped'
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    snapshot_ref = Column(JSONType, nullable=True)  # Optional snapshot context at time of event
    event_metadata = Column(JSONType, nullable=True)  # e.g., {"success": true/false, "reason": "..."}

    # --- Relationships ---
    user = relationship("UserModel", back_populates="task_footprints")


# --- Reflection Log Model ---
class ReflectionLogModel(Base):
    __tablename__ = "reflection_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    reflection_text = Column(Text, nullable=False)  # Use Text for potentially long reflections
    snapshot_ref = Column(JSONType, nullable=True)
    analysis_metadata = Column(JSONType, nullable=True)

    # --- Relationships ---
    user = relationship("UserModel", back_populates="reflection_logs")
