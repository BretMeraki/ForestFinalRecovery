"""
Core router for Forest OS API.

Handles core command and task completion endpoints, including reflection processing, snapshot management, and dependency injection for orchestrator and related services.
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from forest_app.containers import Container
from forest_app.core.discovery_journey.integration_utils import (
    infuse_recommendations_into_snapshot, track_task_completion_for_discovery)
from forest_app.core.integrations.discovery_integration import \
    get_discovery_journey_service
from forest_app.core.orchestrator import ForestOrchestrator
from forest_app.core.auth.security_utils import get_current_active_user
from forest_app.core.memory.memory_snapshot import MemorySnapshot
from forest_app.routers.onboarding_helpers import save_snapshot_with_codename
from forest_app.modules.logging_tracking import TaskFootprintLogger
from forest_app.modules.trigger_phrase import TriggerPhraseHandler
from forest_app.database.session import get_db
from forest_app.models import UserModel
from forest_app.persistence.repository import MemorySnapshotRepository

try:
    from forest_app.config import constants
except ImportError:

    class ConstantsPlaceholder:
        MAX_CODENAME_LENGTH = 60
        MIN_PASSWORD_LENGTH = 8
        ONBOARDING_STATUS_NEEDS_GOAL = "needs_goal"
        ONBOARDING_STATUS_NEEDS_CONTEXT = "needs_context"
        ONBOARDING_STATUS_COMPLETED = "completed"
        SEED_STATUS_ACTIVE = "active"
        SEED_STATUS_COMPLETED = "completed"
        DEFAULT_RESONANCE_THEME = "neutral"

    constants = ConstantsPlaceholder()

logger = logging.getLogger(__name__)
router = APIRouter()


class CommandRequest(BaseModel):
    """Request model for core command endpoint."""

    command: str


class RichCommandResponse(BaseModel):
    """Response model for core command endpoint."""

    tasks: List[Dict[str, Any]] = Field(default_factory=list)
    offering: Optional[dict] = None
    mastery_challenge: Optional[dict] = None
    magnitude_description: str
    arbiter_response: str
    resonance_theme: str
    routing_score: float
    onboarding_status: Optional[str] = None
    action_required: Optional[str] = None
    confirmation_details: Optional[Dict[str, Any]] = None

    class Config:
        arbitrary_types_allowed = True  # type: ignore
        # pylint: disable=too-few-public-methods


class CompleteTaskRequest(BaseModel):
    """Request model for task completion endpoint."""

    task_id: str
    success: bool
    reflection: Optional[str] = None


class MessageResponse(BaseModel):
    """Response model for simple message responses."""

    message: str

    class Config:
        arbitrary_types_allowed = True  # type: ignore
        # pylint: disable=too-few-public-methods


@router.post("/command", response_model=RichCommandResponse, tags=["Core"])
@inject
async def command_endpoint(
    request_data: CommandRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_active_user),
    trigger_h: TriggerPhraseHandler = Depends(
        Provide[Container.trigger_phrase_handler]
    ),
    orchestrator_i: ForestOrchestrator = Depends(Provide[Container.orchestrator]),
):
    """Processes a core command, handling triggers, onboarding, and reflection."""
    user_id = current_user.id
    command_text = request_data.command
    logger.info("Received command user %d: '%.50s...'", user_id, command_text)
    try:
        repo = MemorySnapshotRepository(db)
        stored_model = get_latest_snapshot_model(user_id, db)
        snapshot = None
        if stored_model and stored_model.snapshot_data:
            try:
                snapshot = MemorySnapshot.from_dict(stored_model.snapshot_data)
            except Exception as load_err:
                logger.error(
                    "Err load snapshot user %d: %s", user_id, load_err, exc_info=True
                )
                stored_model = None
        elif stored_model:
            logger.warning("Snapshot user %d has no data.", user_id)
            stored_model = None
        trigger_result = trigger_h.handle_trigger_phrase(command_text, snapshot)
        action = trigger_result.get("action")
        if trigger_result.get("triggered"):
            logger.info("Command trigger user %d. Action: %s", user_id, action)
            if action == "save_snapshot":
                if not snapshot or not stored_model:
                    raise HTTPException(
                        status_code=404, detail="No active session to save."
                    )
                if not orchestrator_i or not orchestrator_i.llm_client:
                    raise HTTPException(
                        status_code=500, detail="LLM service needed for save."
                    )
                saved_model = await save_snapshot_with_codename(
                    db=db,
                    repo=repo,
                    user_id=user_id,
                    snapshot=snapshot,
                    llm_client=orchestrator_i.llm_client,
                    stored_model=stored_model,
                )
                if not saved_model:
                    raise HTTPException(status_code=500, detail="Save failed")
                try:
                    db.commit()
                    db.refresh(saved_model)
                except SQLAlchemyError as commit_err:
                    db.rollback()
                    logger.exception("Failed commit: %s", commit_err)
                    raise HTTPException(
                        status_code=500, detail="Failed finalize save."
                    ) from commit_err
                codename = saved_model.codename or f"ID {saved_model.id}"
                return RichCommandResponse(
                    tasks=[],
                    arbiter_response=f"Snapshot saved ('{codename}')",
                    magnitude_description="N/A",
                    resonance_theme="N/A",
                    routing_score=0.0,
                )
            else:
                return RichCommandResponse(
                    tasks=[],
                    arbiter_response=trigger_result.get(
                        "message", "Acknowledged trigger."
                    ),
                    magnitude_description="N/A",
                    resonance_theme="N/A",
                    routing_score=0.0,
                )
        if not snapshot or not stored_model:
            onboarding_status = constants.ONBOARDING_STATUS_NEEDS_GOAL
            temp_stored_model = get_latest_snapshot_model(user_id, db)
            if temp_stored_model and temp_stored_model.snapshot_data:
                try:
                    temp_snap_data = temp_stored_model.snapshot_data
                    if isinstance(temp_snap_data, dict) and temp_snap_data.get(
                        "activated_state", {}
                    ).get("goal_set"):
                        onboarding_status = constants.ONBOARDING_STATUS_NEEDS_CONTEXT
                except Exception as snap_peek_err:
                    logger.error(
                        "Error peeking snapshot: %s", snap_peek_err, exc_info=True
                    )
            detail = (
                "Onboarding: Please provide context."
                if onboarding_status == constants.ONBOARDING_STATUS_NEEDS_CONTEXT
                else "Onboarding: Please set a goal."
            )
            raise HTTPException(status_code=403, detail=detail)
        if not snapshot.activated_state.get("activated", False):
            raise HTTPException(status_code=403, detail="Onboarding incomplete.")
        logger.info("Processing command user %d as reflection.", user_id)
        result_dict = await orchestrator_i.process_reflection(
            user_input=command_text, snap=snapshot
        )
        if not orchestrator_i.llm_client:
            raise HTTPException(status_code=500, detail="LLM service needed for save.")
        saved_model = await save_snapshot_with_codename(
            db=db,
            repo=repo,
            user_id=user_id,
            snapshot=snapshot,
            llm_client=orchestrator_i.llm_client,
            stored_model=stored_model,
        )
        if not saved_model:
            raise HTTPException(
                status_code=500, detail="Failed save state after reflection."
            )
        try:
            db.commit()
            db.refresh(saved_model)
        except SQLAlchemyError as commit_err:
            db.rollback()
            logger.exception("Failed commit: %s", commit_err)
            raise HTTPException(
                status_code=500, detail="Failed finalize reflection save."
            ) from commit_err
        response_payload = {
            "tasks": result_dict.get("tasks", []),
            "arbiter_response": result_dict.get("arbiter_response", ""),
            "offering": result_dict.get("offering"),
            "mastery_challenge": result_dict.get("mastery_challenge"),
            "magnitude_description": result_dict.get("magnitude_description", "N/A"),
            "resonance_theme": result_dict.get(
                "resonance_theme", constants.DEFAULT_RESONANCE_THEME
            ),
            "routing_score": result_dict.get("routing_score", 0.0),
            "onboarding_status": result_dict.get("onboarding_status"),
            "action_required": result_dict.get("action_required"),
            "confirmation_details": result_dict.get("confirmation_details"),
        }
        return RichCommandResponse(**response_payload)
    except HTTPException:
        raise
    except (SQLAlchemyError, ValueError, TypeError) as db_val_err:
        logger.exception(
            "DB/Data error /command user %d: %s", user_id, db_val_err, exc_info=True
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
    except Exception as e:
        logger.exception("Error /command user %d: %s", user_id, e, exc_info=True)
        raise HTTPException(status_code=500, detail="Internal error.") from e


# --- ADDED: Task Completion Endpoint ---
@router.post("/complete_task", response_model=Dict[str, Any], tags=["Core"])
@inject  # <<< ADDED DECORATOR
async def complete_task_endpoint(
    request_data: CompleteTaskRequest,  # Use the renamed request model
    request: Request,  # Inject FastAPI Request object if needed for context
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(
        get_current_active_user
    ),  # Use the specific active user function
    # --- MODIFIED: Inject Dependencies using Provide ---
    orchestrator: ForestOrchestrator = Depends(Provide[Container.orchestrator]),
    task_logger: TaskFootprintLogger = Depends(
        Provide[Container.task_footprint_logger]
    ),
):
    """
    Endpoint to mark a task as completed (or failed) and trigger
    subsequent processing like HTA updates and potential evolution.
    """
    user_id = current_user.id
    task_id = request_data.task_id
    success = request_data.success
    logger.info(
        "Received /complete_task request user %d, Task: %s, Success: %s",
        user_id,
        task_id,
        success,
    )

    try:
        # 1. Load the latest snapshot
        repo = MemorySnapshotRepository(db)
        # REMINDER: Ensure get_latest_snapshot_model is sync if not using await
        stored_model = get_latest_snapshot_model(user_id, db)
        if not stored_model:
            logger.error("Snapshot not found for user %d during task completion.")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="No active session found."
            )
        if not stored_model.snapshot_data:
            logger.error(
                "Snapshot data empty for user %d (ID: %s).", user_id, stored_model.id
            )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Active session data is empty.",
            )

        try:
            snap = MemorySnapshot.from_dict(stored_model.snapshot_data)
        except Exception as load_err:
            logger.error(
                "Err load snapshot user %d: %s", user_id, load_err, exc_info=True
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed load session state: {load_err}",
            ) from load_err

        # 2. Check Onboarding Status
        if not snap.activated_state.get("activated"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot complete task: Onboarding incomplete.",
            )

        # 3. Call Orchestrator Logic with reflection support (Task 1.5 enhancement)
        completion_result = await orchestrator.process_task_completion(
            task_id=task_id,
            success=success,
            snap=snap,  # Pass the MemorySnapshot object
            db=db,  # Pass db session if logger needs it
            task_logger=task_logger,  # Pass the injected logger
            reflection=request_data.reflection,  # Pass optional user reflection
        )

        # 3.5 Invisibly enhance with Discovery Journey capabilities
        # This happens behind the scenes without creating a separate feature
        discovery_service = get_discovery_journey_service(request)
        if discovery_service:
            try:
                # Silently track task completion for discovery journey insights
                await track_task_completion_for_discovery(
                    discovery_service=discovery_service,
                    user_id=str(current_user.id),
                    task_id=task_id,
                    feedback={
                        "success": success,
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "task_metadata": completion_result.get("task_metadata", {}),
                    },
                )

                # Invisibly infuse recommendations into the snapshot
                snap = await infuse_recommendations_into_snapshot(
                    discovery_service=discovery_service,
                    snapshot=snap,
                    user_id=str(current_user.id),
                )
                logger.debug(
                    "Enhanced snapshot with Discovery Journey insights invisibly"
                )
            except Exception as e:
                # Non-critical enhancement - log but don't disrupt normal flow
                logger.warning(
                    "Non-critical: Could not enhance with discovery journey: %s", e
                )

        # 4. Save Updated Snapshot
        if (
            not orchestrator.llm_client
        ):  # Check if LLM client is available on orchestrator
            logger.error(
                "LLMClient not available via orchestrator for saving snapshot post-completion."
            )
            raise HTTPException(
                status_code=500,
                detail="Internal configuration error: LLM service needed for save.",
            )

        # Pass the potentially modified 'snap' object to the save helper
        # REMINDER: Ensure save_snapshot_with_codename is async if using await
        saved_model = await save_snapshot_with_codename(
            db=db,
            repo=repo,
            user_id=user_id,
            snapshot=snap,  # Pass the updated snapshot object
            llm_client=orchestrator.llm_client,
            stored_model=stored_model,  # Pass the original DB model for update context
        )
        if not saved_model:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed save state after task completion.",
            )

        # 5. Commit Transaction
        try:
            db.commit()
            db.refresh(saved_model)  # Refresh to get updated data if needed
            logger.info(
                "Successfully processed completion for task %s and saved snapshot.",
                task_id,
            )
        except SQLAlchemyError as commit_err:
            db.rollback()
            logger.exception("Failed commit after task completion: %s", commit_err)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed finalize task completion state save.",
            ) from commit_err

        # 6. Return Result
        return {"detail": f"Task '{task_id}' processed.", "result": completion_result}

    except HTTPException:
        raise
    except (SQLAlchemyError, ValueError, TypeError) as db_val_err:
        logger.exception(
            "DB/Data error /complete_task user %d: %s",
            user_id,
            db_val_err,
            exc_info=True,
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
    except Exception as e:
        logger.exception("Error /complete_task user %d: %s", user_id, e, exc_info=True)
        raise HTTPException(status_code=500, detail="Internal error.") from e


# --- END ADDED ---
