"""
Onboarding router for Forest OS API.

Handles user onboarding steps: setting goals, adding context, and generating the initial HTA tree.
Implements robust error handling, logging, and dependency injection for LLM-backed onboarding flows.
"""

# Standard library imports
import logging
import uuid

# Third-party imports
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

# Application imports
from forest_app.api.dependencies import (get_current_active_user, get_db,
                                         get_orchestrator)
from forest_app.core.memory.memory_snapshot import MemorySnapshot
from forest_app.core.services.forest_orchestrator import ForestOrchestrator
from forest_app.routers.onboarding_helpers import save_snapshot_with_codename
from forest_app.persistence.repository import MemorySnapshotRepository
from forest_app.schemas.onboarding_schemas import AddContextRequest
# Import helper functions from onboarding_helpers module
from forest_app.routers.onboarding_helpers import (
    activate_hta_and_finalize, complete_onboarding, determine_first_task,
    generate_hta_from_llm, handle_already_active_session,
    load_snapshot_with_error_handling, parse_and_enrich_hta_response,
    process_onboarding_inputs)
# Import centralized schemas
from forest_app.schemas.onboarding import (AddContextRequest,
                                           OnboardingResponse, SetGoalRequest)

# Constants
DISCOVERY_SERVICE_AVAILABLE = False

# Conditionally import discovery service
try:
    from forest_app.core.integrations.discovery_integration import \
        get_discovery_journey_service  # noqa: F401

    DISCOVERY_SERVICE_AVAILABLE = True
except (ImportError, AttributeError):
    pass

logger = logging.getLogger(__name__)
router = APIRouter()


# Pydantic models now imported from centralized schemas.onboarding module


@router.post("/start", response_model=OnboardingResponse, tags=["Onboarding"])
async def start_onboarding(
    onboarding_data: SetGoalRequest,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_active_user),
    orchestrator_i: ForestOrchestrator = Depends(get_orchestrator),
) -> OnboardingResponse:
    """
    Handle the first step of onboarding by setting the user's goal.

    This endpoint saves the user's goal description to their snapshot and updates
    the onboarding status. It ensures the LLM service is available and handles
    both new and existing user sessions appropriately.

    Args:
        onboarding_data: Contains the user's goal description
        db: Database session
        current_user: The currently authenticated user
        orchestrator_i: ForestOrchestrator instance for LLM operations

    Returns:
        OnboardingResponse with the current onboarding status

    Raises:
        HTTPException: If there's an error processing the request or LLM service is unavailable
    """
    user_id = current_user.id
    logger.info("Processing onboarding start for user %s", user_id)

    try:
        repo = MemorySnapshotRepository(db)
        stored_model = repo.get_latest_snapshot(user_id)
        snapshot = MemorySnapshot()

        # Load existing snapshot if available
        if stored_model and stored_model.snapshot_data:
            try:
                snapshot = MemorySnapshot.from_dict(stored_model.snapshot_data)
                logger.debug(
                    "Successfully loaded existing snapshot for user %s", user_id
                )
            except Exception as load_err:
                logger.error(
                    "Error loading snapshot for user %s: %s. Starting fresh.",
                    user_id,
                    str(load_err),
                    exc_info=True,
                )
                stored_model = None

        # Handle case where session was previously active
        if snapshot.activated_state.get("activated", False):
            logger.info(
                "Resetting previously active session for user %s",
                user_id,
            )

        # Update snapshot state with new goal
        if not isinstance(snapshot.component_state, dict):
            snapshot.component_state = {}

        snapshot.component_state["raw_goal_description"] = str(
            onboarding_data.goal_description
        )
        snapshot.activated_state["goal_set"] = True
        snapshot.activated_state["activated"] = False

        # Verify LLM client availability
        if not orchestrator_i or not orchestrator_i.llm_client:
            error_msg = "LLM service is currently unavailable"
            logger.error("%s for user %s", error_msg, user_id)
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=error_msg,
            )

        # Save snapshot with the new goal
        force_create = not stored_model
        saved_model = await save_snapshot_with_codename(
            db=db,
            repo=repo,
            user_id=user_id,
            snapshot=snapshot,
            llm_client=orchestrator_i.llm_client,
            stored_model=stored_model,
            force_create_new=force_create,
        )

        if not saved_model:
            error_msg = "Failed to save user's goal"
            logger.error("%s for user %s", error_msg, user_id)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=error_msg,
            )

        # Commit changes to the database
        try:
            db.commit()
            db.refresh(saved_model)
            logger.info(
                "Successfully committed snapshot for user %s in set_goal.", user_id
            )
        except SQLAlchemyError as commit_err:
            db.rollback()
            logger.exception(
                "Failed to commit snapshot for user %s in set_goal: %s",
                user_id,
                commit_err,
            )
            raise HTTPException(
                status_code=500, detail="Failed to finalize goal save."
            ) from commit_err

        logger.info("Onboarding Step 1 complete user %s.", user_id)
        return OnboardingResponse(
            onboarding_status=constants.ONBOARDING_STATUS_NEEDS_CONTEXT,
            message="Vision received. Now add context.",
        )
    except HTTPException:
        raise
    except (ValueError, TypeError, AttributeError) as data_err:
        logger.exception("Data/Type error /set_goal user %s: %s", user_id, data_err)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid data: {data_err}"
        ) from data_err
    except SQLAlchemyError as db_err:
        logger.exception("Database error /set_goal user %s: %s", user_id, db_err)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database error during goal setting.",
        ) from db_err
    except Exception as e:  # noqa: W0718
        # Broad catch is intentional for FastAPI endpoint robustness and to log all unexpected errors.
        logger.exception("Unexpected error /set_goal user %s: %s", user_id, e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process goal.",
        ) from e


# --- /add_context endpoint (Needs LLM call update) ---
@router.post("/add_context", response_model=OnboardingResponse, tags=["Onboarding"])
async def add_context_endpoint(
    request: AddContextRequest,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_active_user),
    orchestrator_i: ForestOrchestrator = Depends(
        get_orchestrator
    ),  # Inject orchestrator (provides LLMClient)
):
    """
    Handles the second step of onboarding: adding context and generating the initial HTA.
    Uses the injected orchestrator's LLMClient for HTA generation.
    """
    user_id = current_user.id
    try:
        logger.info(
            "[/onboarding/add_context] Received context request user %s.",
            user_id,
        )

        # --- Check Orchestrator and LLMClient availability ---
        if not orchestrator_i or not orchestrator_i.llm_client:
            logger.error(
                "LLMClient not available via orchestrator for user %s in add_context.",
                user_id,
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal configuration error: LLM service unavailable.",
            )
        llm_client_instance = orchestrator_i.llm_client  # Get client instance

        repo = MemorySnapshotRepository(db)
        stored_model = repo.get_latest_snapshot(user_id)
        if not stored_model or not stored_model.snapshot_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Snapshot not found. Run /set_goal first.",
            )

        snapshot = load_snapshot_with_error_handling(stored_model, user_id)

        if not snapshot.activated_state.get("goal_set", False):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Goal must be set before adding context.",
            )

        # --- Handle already active session (no LLM call needed here) ---
        if snapshot.activated_state.get("activated", False):
            logger.info(
                "User %s /add_context recalled, session already active.",
                user_id,
            )
            refined_goal_desc, first_task = handle_already_active_session(
                snapshot, orchestrator_i
            )
            return OnboardingResponse(
                onboarding_status=constants.ONBOARDING_STATUS_COMPLETED,
                message="Session already active. Context addition skipped.",
                refined_goal=refined_goal_desc,
                first_task=first_task,
            )

        # --- Step 1: Process Inputs ---
        processed_goal, processed_context = process_onboarding_inputs(
            request, snapshot, user_id
        )

        # --- Step 2: Generate HTA with LLM ---
        root_node_id = f"root_{str(uuid.uuid4())[:8]}"
        hta_response_json_str = await generate_hta_from_llm(
            processed_goal,
            processed_context,
            llm_client_instance,
            root_node_id,
            user_id,
        )
        snapshot.log_event(
            event_type=constants.EVENT_TYPE_LLM_RESPONSE_RECEIVED,
            metadata={"user_id": user_id, "component": "HTAGeneration"},
        )

        # --- Step 3: Parse, Enrich, and Validate HTA Response ---
        # Initialize discovery service if available
        discovery_service = None
        if DISCOVERY_SERVICE_AVAILABLE and fastapi_app is not None:
            try:
                discovery_service = get_discovery_journey_service(fastapi_app)
            except Exception as e:  # pylint: disable=broad-except
                logger.warning("Could not initialize discovery service: %s", str(e))

        hta_model_dict = await parse_and_enrich_hta_response(
            hta_response_json_str,
            orchestrator_i,
            discovery_service,
            user_id,
            processed_goal,
            processed_context,
            snapshot,
        )

        # Log successful HTA generation from LLM to snapshot
        snapshot.log_event(
            event_type=constants.EVENT_TYPE_HTA_GENERATED,
            metadata={
                "user_id": user_id,
                "root_node_id": hta_model_dict.get("root_id", "unknown"),
                "num_nodes": len(hta_model_dict.get("nodes", {})),
            },
        )
        snapshot.update_core_state("hta_generated_by_llm", True)

        # --- Step 4: Activate HTA, Create Seed, and Finalize Snapshot ---
        _, _, first_task, refined_goal_desc = activate_hta_and_finalize(
            hta_model_dict,
            processed_goal,
            snapshot,
            repo,
            db,
            user_id,
            orchestrator_i,
            llm_client_instance,
            stored_model,
        )

        # --- Determine First Task (Post-Activation) ---
        first_task = determine_first_task(snapshot, orchestrator_i, user_id)
        return OnboardingResponse(
            **complete_onboarding(user_id, refined_goal_desc, first_task)
        )
    except HTTPException:
        raise
    except (
        ValueError,
        TypeError,
        AttributeError,
        ValidationError,
    ) as data_err:  # Added ValidationError
        logger.exception(
            "Data/Validation error /add_context user %s: %s",
            user_id,
            data_err,
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid data/validation: {data_err}",
        ) from data_err
    except SQLAlchemyError as db_err:
        logger.exception("Database error /add_context user %s: %s", user_id, db_err)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database error during context processing.",
        ) from db_err
    except Exception as e:  # noqa: W0718
        # Broad catch is intentional to ensure FastAPI endpoint robustness and to log unexpected errors.
        logger.exception("Unexpected error /add_context user %s: %s", user_id, e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal error: {e}",
        ) from e
