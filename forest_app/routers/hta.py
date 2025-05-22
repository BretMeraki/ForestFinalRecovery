"""
HTA router for Forest OS API.

Handles retrieval of the current HTA (Hierarchical Task Analysis) state for the user. Implements robust error handling, logging, and dependency injection for HTA management.
"""

import json
import logging
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException

# --- Pydantic Imports ---
from pydantic import BaseModel  # Import base pydantic needs
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from forest_app.core.discovery_journey.integration_utils import (
    infuse_recommendations_into_snapshot,
    track_task_completion_for_discovery,
)
from forest_app.core.integrations.discovery_integration import (
    get_discovery_journey_service,
)
from forest_app.core.orchestrator import ForestOrchestrator
from forest_app.core.security import get_current_active_user
from forest_app.core.snapshot import MemorySnapshot
from forest_app.dependencies import get_orchestrator

# --- Dependencies & Models ---
from forest_app.persistence.database import get_db
from forest_app.persistence.models import UserModel
from forest_app.persistence.repository import MemorySnapshotRepository

# <<< --- END ADDED IMPORT --- >>>

from forest_app.utils.import_fallbacks import import_with_fallback

logger = logging.getLogger(__name__)
router = APIRouter()

constants = import_with_fallback(
    lambda: __import__('forest_app.config', fromlist=['constants']).constants,
    lambda: {},
    logger,
    "constants"
)

# --- Pydantic Models DEFINED LOCALLY ---
class HTAStateResponse(BaseModel):
    """Response model for HTA state retrieval."""

    hta_tree: Optional[Dict[str, Any]] = None
    message: Optional[str] = None

    class Config:
        # Suppress 'too few public methods' warning for Pydantic models
        arbitrary_types_allowed = True  # type: ignore
        # pylint: disable=too-few-public-methods


# --- End Pydantic Models ---


# Helper functions for snapshot_data and id

def get_snapshot_data(model):
    if hasattr(model, 'snapshot_data'):
        return model.snapshot_data
    return None

def get_snapshot_id(model):
    if hasattr(model, 'id'):
        return model.id
    return None


@router.get(
    "/state", response_model=HTAStateResponse, tags=["HTA"]
)  # Prefix is in main.py
async def get_hta_state(
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_active_user),
    orchestrator_i: ForestOrchestrator = Depends(get_orchestrator),
):
    """Retrieves the current HTA state for the user."""
    user_id = current_user.id
    logger.info("Request HTA state user %d", user_id)
    try:
        repo = MemorySnapshotRepository(db)
        stored_model = repo.get_latest_snapshot(user_id)
        if not stored_model:
            return HTAStateResponse(hta_tree=None, message="No active session found.")
        if not get_snapshot_data(stored_model):
            return HTAStateResponse(hta_tree=None, message="Session data missing.")

        try:
            snapshot = MemorySnapshot.from_dict(get_snapshot_data(stored_model))
        except Exception as load_err:  # noqa: W0718
            # Broad catch is intentional to ensure FastAPI endpoint robustness and to log unexpected errors.
            raise HTTPException(
                status_code=500, detail=f"Failed load session: {load_err}"
            ) from load_err

        if not snapshot.activated_state.get("activated", False):
            status_msg = (
                constants.ONBOARDING_STATUS_NEEDS_CONTEXT
                if snapshot.activated_state.get("goal_set")
                else constants.ONBOARDING_STATUS_NEEDS_GOAL
            )
            message = (
                "Onboarding incomplete. Provide context."
                if status_msg == constants.ONBOARDING_STATUS_NEEDS_CONTEXT
                else "Onboarding incomplete. Set goal."
            )
            return HTAStateResponse(hta_tree=None, message=message)

        # Use injected orchestrator instance
        result = await orchestrator_i.process_task_completion(
            user_id=str(current_user.id), task_footprint=None
        )

        # Invisibly leverage Discovery Journey without creating a separate experience
        discovery_service = get_discovery_journey_service(None)
        if discovery_service:
            try:
                # Silently track task completion to inform the discovery journey
                await track_task_completion_for_discovery(
                    discovery_service=discovery_service,
                    user_id=str(current_user.id),
                    task_id=None,
                    feedback={
                        "emotion": None,
                        "reflection": None,
                        "difficulty": None,
                        "completion_context": {"time": None, "node_data": None},
                    },
                )

                # If we have a snapshot, invisibly enrich it with discovery insights
                if result and "snapshot" in result and result["snapshot"]:
                    result["snapshot"] = await infuse_recommendations_into_snapshot(
                        discovery_service=discovery_service,
                        snapshot=result["snapshot"],
                        user_id=str(current_user.id),
                    )
            except Exception as e:  # noqa: W0718
                # Broad catch is intentional to ensure FastAPI endpoint robustness and to log unexpected errors.
                logger.warning(
                    "Non-critical: Could not enhance task completion with discovery insights: %s",
                    e,
                )

        hta_tree_data = snapshot.core_state.get("hta_tree")

        # <<< --- ADDED LOGGING --- >>>
        try:
            if hta_tree_data:
                log_data_str = json.dumps(hta_tree_data, indent=2, default=str)
                if len(log_data_str) > 1000:
                    log_data_str = log_data_str[:1000] + "... (truncated)"
                logger.debug(
                    "[ROUTER HTA LOAD] HTA data loaded from core_state to be returned:\n%s",
                    log_data_str,
                )
            else:
                logger.debug(
                    "[ROUTER HTA LOAD] HTA data loaded from core_state is None or empty."
                )
        except Exception as log_ex:  # noqa: W0718
            # Broad catch is intentional to ensure FastAPI endpoint robustness and to log unexpected errors.
            logger.error("[ROUTER HTA LOAD] Error logging loaded HTA state: %s", log_ex)
        # <<< --- END ADDED LOGGING --- >>>

        if (
            not hta_tree_data
            or not isinstance(hta_tree_data, dict)
            or not hta_tree_data.get("root")
        ):
            # Log this specific condition too
            logger.warning(
                "[ROUTER HTA LOAD] HTA data is invalid/missing root just before returning 404-like response. "
                "Type: %s",
                type(hta_tree_data),
            )
            return HTAStateResponse(
                hta_tree=None, message="HTA data not found or invalid."
            )

        return HTAStateResponse(
            hta_tree=hta_tree_data, message="HTA structure retrieved."
        )

    except HTTPException:
        raise
    except SQLAlchemyError as db_err:
        logger.error(
            "DB error getting HTA state user %d: %s", user_id, db_err, exc_info=True
        )
        raise HTTPException(status_code=503, detail="DB error.") from db_err
    except Exception as e:  # noqa: W0718
        # Broad catch is intentional to ensure FastAPI endpoint robustness and to log unexpected errors.
        logger.error("Error getting HTA state user %d: %s", user_id, e, exc_info=True)
        raise HTTPException(status_code=500, detail="Internal error.") from e
