"""
Snapshots router for Forest OS API.

Handles listing, loading, and deleting user memory snapshots.
Implements robust error handling, logging, and dependency injection for snapshot management.
"""

import logging
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ValidationError
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from forest_app.core.memory.memory_snapshot import MemorySnapshot
from forest_app.core.auth.security_utils import get_current_active_user
from forest_app.database.session import get_db
from forest_app.models import UserModel
from forest_app.persistence.repository import MemorySnapshotRepository
from forest_app.routers.onboarding_helpers import save_snapshot_with_codename

logger = logging.getLogger(__name__)
router = APIRouter()


class SnapshotInfo(BaseModel):
    """Pydantic model for snapshot metadata."""

    id: int
    codename: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class LoadSessionRequest(BaseModel):
    """Request model for loading a session from a snapshot."""

    snapshot_id: int


class MessageResponse(BaseModel):
    """Response model for simple message responses."""

    message: str


@router.get("/list", response_model=List[SnapshotInfo], tags=["Snapshots"])
async def list_user_snapshots(
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_active_user),
):
    """Lists all saved snapshots for the current user."""
    user_id = current_user.id
    logger.info("Request list snapshots user %d", user_id)
    try:
        repo = MemorySnapshotRepository(db)
        models = repo.list_snapshots(user_id)
        if not models:
            return []
        return [SnapshotInfo.model_validate(m) for m in models]
    except SQLAlchemyError as db_err:
        logger.error(
            "DB error listing snapshots user %d: %s", user_id, db_err, exc_info=True
        )
        raise HTTPException(
            status_code=503, detail="DB error listing snapshots."
        ) from db_err
    except ValidationError as val_err:
        logger.error(
            "Validation error formatting snapshot list user %d: %s",
            user_id,
            val_err,
            exc_info=True,
        )
        raise HTTPException(
            status_code=500, detail="Internal error formatting snapshot list."
        ) from val_err
    except Exception as e:  # noqa: W0718
        # Broad catch is intentional to ensure FastAPI endpoint robustness and to log unexpected errors.
        logger.error("Error listing snapshots user %d: %s", user_id, e, exc_info=True)
        raise HTTPException(
            status_code=500, detail="Internal error listing snapshots."
        ) from e


@router.post("/session/load", response_model=MessageResponse, tags=["Snapshots"])
async def load_session_from_snapshot(
    request: LoadSessionRequest,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_active_user),
):
    """Loads a previous snapshot as the new active session."""
    user_id = current_user.id
    snapshot_id = request.snapshot_id
    logger.info("Request load session user %d from snapshot %d", user_id, snapshot_id)
    try:
        repo = MemorySnapshotRepository(db)
        model_to_load = repo.get_snapshot_by_id(snapshot_id, user_id)
        if not model_to_load:
            raise HTTPException(status_code=404, detail="Snapshot not found.")
        if not model_to_load.snapshot_data:
            raise HTTPException(status_code=404, detail="Snapshot empty.")
        try:
            loaded_snapshot = MemorySnapshot.from_dict(model_to_load.snapshot_data)
        except Exception as load_err:
            raise HTTPException(
                status_code=500, detail=f"Failed parse snapshot: {load_err}"
            ) from load_err
        if not isinstance(loaded_snapshot.activated_state, dict):
            loaded_snapshot.activated_state = {}
        loaded_snapshot.activated_state.update({"activated": True, "goal_set": True})
        new_model = await save_snapshot_with_codename(
            db=db,
            repo=repo,
            user_id=user_id,
            snapshot=loaded_snapshot,
            llm_client=None,
            stored_model=model_to_load,
            force_create_new=True,
        )
        if not new_model:
            raise HTTPException(status_code=500, detail="Failed save loaded session.")
        codename = new_model.codename or f"ID {new_model.id}"
        logger.info(
            "Loaded snap %d user %d. New ID: %d", snapshot_id, user_id, new_model.id
        )
        return MessageResponse(message=f"Session loaded from '{codename}'.")
    except HTTPException:
        raise
    except (SQLAlchemyError, ValueError, TypeError) as db_val_err:
        logger.exception(
            "DB/Data error load session user %d snap %d: %s",
            user_id,
            snapshot_id,
            db_val_err,
        )
        detail = (
            "DB error."
            if isinstance(db_val_err, SQLAlchemyError)
            else f"Invalid data: {db_val_err}"
        )
        status_code = (
            status.HTTP_503_SERVICE_UNAVAILABLE
            if isinstance(db_val_err, SQLAlchemyError)
            else status.HTTP_400_BAD_REQUEST
        )
        raise HTTPException(status_code=status_code, detail=detail) from db_val_err
    except Exception as e:  # noqa: W0718
        # Broad catch is intentional to ensure FastAPI endpoint robustness and to log unexpected errors.
        logger.exception(
            "Error load session user %d snap %d: %s", user_id, snapshot_id, e
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal error."
        ) from e


@router.delete(
    "/snapshots/{snapshot_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["Snapshots"],
)
async def delete_user_snapshot(
    snapshot_id: int,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_active_user),
):
    """Deletes a specific snapshot."""
    user_id = current_user.id
    logger.info("Request delete snap %d user %d", snapshot_id, user_id)
    try:
        repo = MemorySnapshotRepository(db)
        deleted = repo.delete_snapshot_by_id(snapshot_id, user_id)
        if not deleted:
            raise HTTPException(status_code=404, detail="Snapshot not found")
        logger.info("Deleted snap %d user %d", snapshot_id, user_id)
        return None
    except HTTPException:
        raise
    except SQLAlchemyError as db_err:
        logger.exception(
            "DB error delete snap %d user %d: %s", snapshot_id, user_id, db_err
        )
        raise HTTPException(status_code=503, detail="DB error.") from db_err
    except Exception as e:  # noqa: W0718
        # Broad catch is intentional to ensure FastAPI endpoint robustness and to log unexpected errors.
        logger.exception("Error delete snap %d user %d: %s", snapshot_id, user_id, e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal error."
        ) from e
