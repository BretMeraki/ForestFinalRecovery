"""
Goals router for Forest OS API.

Handles goal completion confirmation and related endpoints.
Implements robust error handling, logging, and dependency injection for goal management.
"""

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from forest_app.config.app_constants import SEED_STATUS_COMPLETED
from forest_app.core.orchestrator import ForestOrchestrator
from forest_app.core.security import get_current_active_user
from forest_app.core.snapshot import MemorySnapshot
from forest_app.dependencies import get_orchestrator
from forest_app.persistence.database import get_db
from forest_app.persistence.models import UserModel
from forest_app.persistence.repository import MemorySnapshotRepository
from forest_app.routers.onboarding_helpers import save_snapshot_with_codename
from forest_app.utils.db_helpers import safe_db_operation

logger = logging.getLogger(__name__)
router = APIRouter()


class MessageResponse(BaseModel):
    """Response model for simple message responses."""

    message: str

    class Config:
        # Suppress 'too few public methods' warning for Pydantic models
        arbitrary_types_allowed = True  # type: ignore
        # pylint: disable=too-few-public-methods


async def _load_and_validate_seed_manager(orchestrator_i, snapshot, seed_id):
    """Helper to load and validate the seed manager and target seed."""
    # TODO: Refactor to avoid protected member access if possible
    orchestrator_i._load_component_states(snapshot)
    seed_manager = orchestrator_i.seed_manager
    if not seed_manager:
        raise HTTPException(status_code=500, detail="Failed goal state load.")
    seed_to_complete = seed_manager.get_seed_by_id(seed_id)
    if not seed_to_complete:
        raise HTTPException(status_code=404, detail=f"Goal ID '{seed_id}' not found.")
    if not hasattr(seed_to_complete, "status"):
        raise HTTPException(status_code=500, detail="Seed data invalid.")
    return seed_manager, seed_to_complete


@router.post(
    "/confirm_completion/{seed_id}", response_model=MessageResponse, tags=["Goals"]
)
async def confirm_goal_completion(
    seed_id: str,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_active_user),
    orchestrator_i: ForestOrchestrator = Depends(get_orchestrator),
):
    """Marks a specific Seed (goal) as completed."""
    user_id = current_user.id
    logger.info("Confirm goal complete user %d seed %s", user_id, seed_id)
    try:
        repo = MemorySnapshotRepository(db)
        stored_model = repo.get_latest_snapshot(user_id)
        if not stored_model or not stored_model.snapshot_data:
            raise HTTPException(status_code=404, detail="Active session not found.")
        try:
            snapshot = MemorySnapshot.from_dict(stored_model.snapshot_data)
        except Exception as load_err:  # noqa: W0718
            # Broad catch is intentional to ensure FastAPI endpoint robustness and to log unexpected errors.
            raise HTTPException(
                status_code=500, detail=f"Failed load session: {load_err}"
            ) from load_err
        if not snapshot.activated_state.get("activated"):
            raise HTTPException(status_code=403, detail="Session not active.")
        try:
            seed_manager, seed_to_complete = await _load_and_validate_seed_manager(
                orchestrator_i, snapshot, seed_id
            )
            if seed_to_complete.status == constants.SEED_STATUS_COMPLETED:
                return MessageResponse(
                    message=f"Goal (ID: {seed_id}) already completed."
                )
        except HTTPException:
            raise
        except Exception as state_err:  # noqa: W0718
            # Broad catch is intentional to ensure FastAPI endpoint robustness and to log unexpected errors.
            raise HTTPException(
                status_code=500,
                detail=f"Internal error accessing goal state: {state_err}",
            ) from state_err
        seed_to_complete.status = SEED_STATUS_COMPLETED
        seed_to_complete.updated_at = datetime.now(timezone.utc)
        snapshot.component_state["seed_manager"] = seed_manager.to_dict()

        # Use the safe_db_operation decorator internally for the snapshot save operation
        @safe_db_operation(
            operation_name="save_snapshot_for_goal_completion",
            session=db,
            default_error_message="Failed to save session after goal completion",
        )
        async def _save_snapshot():
            return await save_snapshot_with_codename(
                db=db,
                repo=repo,
                user_id=user_id,
                snapshot=snapshot,
                llm_client=None,
                stored_model=stored_model,
            )

        saved_model = await _save_snapshot()
        if not saved_model:
            raise HTTPException(status_code=500, detail="Failed to save session.")
        seed_name = getattr(seed_to_complete, "seed_name", f"ID: {seed_id}")
        return MessageResponse(message=f"Goal '{seed_name}' marked as completed.")
    except HTTPException:
        # Re-raise HTTP exceptions directly
        raise
    except Exception as e:  # noqa: W0718
        # Our safe_db_operation decorator already handles SQLAlchemyError, ValueError, and TypeError
        # This is just a fallback for any other unexpected exceptions
        logger.exception(
            "Unexpected error in /confirm_goal for user %s seed %s: %s",
            user_id,
            seed_id,
            e,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal error processing goal completion.",
        ) from e
