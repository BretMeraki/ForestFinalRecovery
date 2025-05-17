"""
Onboarding Helper Functions

This module contains helper functions for the Forest OS onboarding process.
These functions support the onboarding router by handling various aspects of
the onboarding flow, such as HTA generation, parsing, and database operations.
"""

# Standard library imports
import json
import logging
from datetime import datetime, timezone
from typing import Any, Optional, Tuple

# Third-party imports
from fastapi import HTTPException, status
from pydantic import ValidationError
from sqlalchemy.orm import Session

# Application imports
from forest_app.core.memory.memory_snapshot import MemorySnapshot
from forest_app.core.services.forest_orchestrator import ForestOrchestrator
from forest_app.helpers import save_snapshot_with_codename
from forest_app.modules.seed import Seed
from forest_app.persistence.repository import MemorySnapshotRepository
from forest_app.schemas.onboarding_schemas import AddContextRequest
from forest_app.utils import commit_and_refresh_db, get_constants_module

# Constants
constants = get_constants_module()
logger = logging.getLogger(__name__)


def handle_already_active_session(
    snapshot: MemorySnapshot, orchestrator_i: ForestOrchestrator
) -> Tuple[str, dict]:
    """
    Handles the case where the session is already active during onboarding context addition.
    Returns (refined_goal_desc, first_task) tuple for the response.

    Args:
        snapshot: The current MemorySnapshot instance
        orchestrator_i: ForestOrchestrator instance for task recommendations

    Returns:
        tuple: A tuple containing (refined_goal_desc, first_task)
    """
    refined_goal_desc = snapshot.component_state.get("processed_goal", "")
    if not refined_goal_desc:
        refined_goal_desc = snapshot.component_state.get("raw_goal_description", "")

    # Try to get first task - might not be available if snapshot structure changed
    first_task = {}
    try:
        rec_service = orchestrator_i.recommendation_service
        if rec_service:
            first_task = rec_service.get_next_task_recommendation(snapshot)
    except Exception as e:  # noqa: W0718
        # Broad catch is intentional for robustness and to handle any recommendation service issue
        logger.warning("Error getting first task recommendation: %s", e, exc_info=True)

    return refined_goal_desc, first_task


def load_snapshot_with_error_handling(
    stored_model: Any, user_id: str
) -> MemorySnapshot:
    """
    Loads a MemorySnapshot from stored_model, handling errors and raising HTTPException if needed.

    Args:
        stored_model: The database model containing the snapshot data
        user_id: ID of the user for logging purposes

    Returns:
        MemorySnapshot: The loaded MemorySnapshot instance

    Raises:
        HTTPException: If there's an error loading the snapshot data
    """
    try:
        snapshot = MemorySnapshot.from_dict(stored_model.snapshot_data)
        return snapshot
    except Exception as e:  # noqa: W0718
        # Broad catch is intentional for robustness in handling corrupted snapshot data
        logger.exception("Error loading snapshot for user %s: %s", user_id, e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error loading snapshot data.",
        ) from e


def build_hta_prompt(
    processed_goal: str, processed_context: str, root_node_id: str
) -> str:
    """
    Constructs the HTA prompt string for the LLM based on the user's goal and context.

    Args:
        processed_goal: The processed user goal
        processed_context: The processed user context
        root_node_id: The unique ID for the root node

    Returns:
        str: A formatted prompt string ready to be sent to the LLM
    """
    current_time = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    # Build the prompt
    prompt = f"""Generate a Hierarchical Task Analysis tree for the following goal: 
    
Goal: {processed_goal}

Context: {processed_context}

Current time: {current_time}

Provide a detailed, step-by-step breakdown of tasks to complete this goal.
The root task ID must be "{root_node_id}".
Format your response as a valid JSON structure matching the following schema:
{{
    "root_id": "string (required: must be '{root_node_id}')",
    "nodes": {{
        "node_id1": {{
            "id": "string (required: must match key)",
            "parent_id": "string (required: parent node id or null for root)",
            "title": "string (required: concise task name)",
            "description": "string (required: detailed explanation)",
            "status": "string (required: one of 'pending', 'in-progress', 'completed', 'blocked')",
            "order": "number (required: order among siblings, starting from 0)",
            "depth": "number (required: 0 for root, incrementing for each level)"
        }},
        "node_id2": {{ ... }}
    }}
}}
"""
    return prompt


def enrich_hta_with_discovery(
    discovery_service: Any,
    hta_response: dict,
    orchestrator_i: ForestOrchestrator,
    context: dict,
) -> Optional[dict]:
    """
    Optionally enriches the HTA with discovery insights if a discovery service and HTA response are available.
    Returns the enriched HTA result or None if not enriched.

    Args:
        discovery_service: The discovery service instance
        hta_response: The HTA response from the LLM
        orchestrator_i: ForestOrchestrator instance
        context: Context dictionary for the discovery service

    Returns:
        Optional[dict]: The enriched HTA response, or None if no enrichment occurred
    """
    if not discovery_service or not hta_response:
        return None

    try:
        if hasattr(discovery_service, "enhance_hta_with_journey_info"):
            enriched_result = discovery_service.enhance_hta_with_journey_info(
                hta_response, orchestrator_i, context
            )
            return enriched_result
    except (AttributeError, ValueError, TypeError) as e:
        # Catch specific exceptions that might be raised during discovery enhancement
        logger.warning(
            "Error enriching HTA with discovery: %s", e, exc_info=True
        )
    except Exception as e:  # noqa: W0718
        # Keep broad catch as a last resort for robustness
        logger.warning(
            "Unexpected error enriching HTA with discovery: %s", e, exc_info=True
        )
    return None


def activate_hta_and_create_seed(
    hta_model_dict: dict,
    processed_goal: str,
    snapshot: MemorySnapshot,
    repo: MemorySnapshotRepository,
    db: Session,
    user_id: str,
    orchestrator_i: ForestOrchestrator,
    llm_client_instance: Any,
    stored_model: Any,
) -> Tuple[Seed, Any, dict, str]:
    """
    Handles HTA activation, seed creation, and snapshot saving.
    
    Args:
        hta_model_dict: Dictionary representation of the HTA model
        processed_goal: The processed user goal
        snapshot: Current MemorySnapshot instance
        repo: MemorySnapshotRepository instance
        db: Database session
        user_id: User identifier
        orchestrator_i: ForestOrchestrator instance
        llm_client_instance: LLM client instance
        stored_model: Stored model from database
        
    Returns:
        Tuple containing (new_seed, saved_model, first_task, refined_goal_desc)
    """
    # Create new Seed from HTA
    logger.info("Creating seed with hta_model_dict for user %s", user_id)
    hta_tree = HTATreeModel.from_dict(hta_model_dict)
    new_seed = Seed.from_hta_model(hta_tree, processed_goal)
    logger.debug("Created seed for user %s", user_id)

    # Update snapshot with seed and set activation status
    update_snapshot_with_seed(snapshot, new_seed, user_id)

    # Save snapshot - using the helper function that handles LLM calls for codename
    if stored_model and stored_model.id:
        # Update existing
        snapshot.id = stored_model.id
        logger.debug(
            "Updating existing snapshot id=%s for user %s", snapshot.id, user_id
        )
        saved_model = save_snapshot_with_codename(
            snapshot, repo, llm_client_instance, update=True
        )
    else:
        # Create new
        logger.debug("Creating new snapshot for user %s", user_id)
        saved_model = save_snapshot_with_codename(
            snapshot, repo, llm_client_instance, update=False
        )

    # Commit changes
    saved_model = commit_snapshot_changes(db, repo, snapshot, saved_model, user_id)
    logger.info("Activated and saved HTA for user %s", user_id)

    # Retrieve first task recommendation
    first_task = determine_first_task(snapshot, orchestrator_i, user_id)

    return new_seed, saved_model, first_task, processed_goal


def process_onboarding_inputs(
    request: AddContextRequest, snapshot: MemorySnapshot, user_id: str
) -> Tuple[str, str]:
    """
    Process and validate onboarding inputs.
    
    Args:
        request: The AddContextRequest containing user input
        snapshot: Current MemorySnapshot instance
        user_id: User identifier for logging
        
    Returns:
        Tuple of (processed_goal, processed_context)
        
    Raises:
        HTTPException: If input validation fails
    """
    # Get goal from previous step
    raw_goal = snapshot.component_state.get("raw_goal_description", "")
    if not raw_goal:
        logger.error("No goal found in snapshot for user %s in add_context.", user_id)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Goal not found in session. Please set goal first.",
        )

    # Get context from request
    context_input = request.context_description
    if not context_input or not context_input.strip():
        context_input = "No additional context provided."

    # Process inputs (simple processing for now, could be enhanced)
    processed_goal = str(raw_goal).strip()
    processed_context = str(context_input).strip()

    # Update snapshot with processed data
    snapshot.component_state["processed_goal"] = processed_goal
    snapshot.component_state["processed_context"] = processed_context

    # Log the context addition
    snapshot.log_event(
        event_type=constants.EVENT_TYPE_CONTEXT_ADDED,
        metadata={"user_id": user_id, "context_length": len(processed_context)},
    )

    return processed_goal, processed_context


async def generate_hta_from_llm(
    processed_goal: str,
    processed_context: str,
    llm_client_instance: Any,
    root_node_id: str,
    user_id: str,
) -> str:
    """
    Generate HTA structure using LLM.
    
    Args:
        processed_goal: The processed user goal
        processed_context: The processed user context
        llm_client_instance: LLM client instance
        root_node_id: Unique ID for the root node
        user_id: User identifier for logging
        
    Returns:
        str: JSON string containing the HTA structure
        
    Raises:
        HTTPException: If there's an error during generation
    """
    prompt = build_hta_prompt(processed_goal, processed_context, root_node_id)
    logger.info("Generating HTA from LLM for user %s", user_id)

    try:
        # Call LLM with error handling
        hta_response_json_str = await llm_client_instance.make_llm_call(
            endpoint=constants.LLM_ENDPOINT_HTA_GENERATION,
            prompt=prompt,
            prompt_version=constants.PROMPT_VERSION_HTA_GENERATION,
            user_id=user_id,
        )
        logger.debug("Successfully received HTA from LLM for user %s", user_id)
        return hta_response_json_str
    except LLMResponseError as llm_err:
        logger.error(
            "LLM response error during HTA generation for user %s: %s",
            user_id,
            llm_err,
        )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Error during HTA generation: {llm_err}",
        ) from llm_err
    except Exception as e:  # noqa: W0718
        # Broad catch is intentional to ensure robust error handling for LLM calls
        logger.exception(
            "Unexpected error during HTA generation for user %s: %s",
            user_id,
            e,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unexpected error during HTA generation: {e}",
        ) from e


def determine_first_task(
    snapshot: MemorySnapshot, orchestrator_i: ForestOrchestrator, user_id: str
) -> dict:
    """
    Determine the first task for the user's onboarding journey.
    
    Args:
        snapshot: Current MemorySnapshot instance
        orchestrator_i: ForestOrchestrator instance
        user_id: User identifier for logging
        
    Returns:
        dict: First task recommendation
    """
    first_task = {}
    try:
        # Get recommendation service from orchestrator
        if orchestrator_i and orchestrator_i.recommendation_service:
            rec_service = orchestrator_i.recommendation_service
            first_task = rec_service.get_next_task_recommendation(snapshot)
            logger.info(
                "Got first task recommendation for user %s: %s",
                user_id,
                first_task.get("title", "unknown"),
            )
    except Exception as e:  # noqa: W0718
        # Broad catch is intentional to handle any recommendation service issues gracefully
        logger.warning(
            "Error getting first task recommendation for user %s: %s",
            user_id,
            e,
            exc_info=True,
        )
        first_task = {
            "id": "unknown",
            "title": "Start your journey",
            "description": "Begin working on your goal.",
        }

    return first_task


def update_snapshot_with_seed(
    snapshot: MemorySnapshot, new_seed: Seed, user_id: str
) -> None:
    """
    Update snapshot with the new seed information.
    
    Args:
        snapshot: Current MemorySnapshot instance
        new_seed: Newly created Seed
        user_id: User identifier for logging
    """
    # Set seed in snapshot
    snapshot.seed = new_seed.to_dict()

    # Mark as activated
    snapshot.activated_state["activated"] = True
    logger.info("Marked snapshot as activated for user %s", user_id)


def commit_snapshot_changes(
    db: Session, 
    repo: MemorySnapshotRepository, 
    snapshot: MemorySnapshot, 
    saved_model: Any, 
    user_id: str
) -> Any:
    """
    Commit changes to the snapshot in the database.
    
    Args:
        db: Database session
        repo: MemorySnapshotRepository instance
        snapshot: Current MemorySnapshot
        saved_model: Model to refresh
        user_id: User identifier for logging
        
    Returns:
        Any: The refreshed model
        
    Raises:
        HTTPException: If there's a database error
    """
    try:
        return commit_and_refresh_db(
            db, saved_model, user_id, "snapshot activation during onboarding"
        )
    except HTTPException:
        # Pass through HTTP exceptions from commit_and_refresh_db
        raise
    except Exception as e:  # noqa: W0718
        # This should not normally be reached as commit_and_refresh_db handles errors,
        # but it's here as a safety net
        logger.exception(
            "Unexpected error committing snapshot changes for user %s: %s",
            user_id,
            e,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error saving changes: {e}",
        ) from e


def activate_hta_and_finalize(
    hta_model_dict: dict,
    processed_goal: str,
    snapshot: MemorySnapshot,
    repo: MemorySnapshotRepository,
    db: Session,
    user_id: str,
    orchestrator_i: ForestOrchestrator,
    llm_client_instance: Any,
    stored_model: Any,
) -> Tuple[Seed, Any, dict, str]:
    """
    Activate HTA and finalize the onboarding process.
    
    Args:
        hta_model_dict: Dictionary representation of the HTA model
        processed_goal: The processed user goal
        snapshot: Current MemorySnapshot instance
        repo: MemorySnapshotRepository instance
        db: Database session
        user_id: User identifier
        orchestrator_i: ForestOrchestrator instance
        llm_client_instance: LLM client instance
        stored_model: Stored model from database
        
    Returns:
        Tuple containing (new_seed, saved_model, first_task, refined_goal_desc)
    """
    logger.info("Activating HTA and finalizing for user %s", user_id)

    # Delegate to the more detailed helper function
    return activate_hta_and_create_seed(
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


def complete_onboarding(user_id: str, refined_goal_desc: str, first_task: dict) -> dict:
    """
    Complete the onboarding process and prepare the response.
    
    Args:
        user_id: User identifier for logging
        refined_goal_desc: The refined goal description
        first_task: First task recommendation
        

    Returns:
        dict: OnboardingResponse data
    """
    logger.info("Onboarding completed successfully for user %s", user_id)
    return {
        "onboarding_status": constants.ONBOARDING_STATUS_COMPLETED,
        "message": "Onboarding completed successfully.",
        "refined_goal": refined_goal_desc,
        "first_task": first_task,
    }


async def parse_and_enrich_hta_response(
    hta_response_json_str: str,
    orchestrator_i: ForestOrchestrator,
    discovery_service: Any,
    user_id: str,
    processed_goal: str,
    processed_context: str,
    snapshot: MemorySnapshot,
) -> dict:
    """
    Parses LLM HTA response, enriches it, validates, and converts to HTATreeModel dict.

    Args:
        hta_response_json_str: JSON string response from the LLM
        orchestrator_i: ForestOrchestrator instance
        discovery_service: Discovery service if available
        user_id: User identifier
        processed_goal: Processed user goal
        processed_context: Processed user context
        snapshot: Current MemorySnapshot

    Returns:
        dict: HTATreeModel as dictionary

    Raises:
        HTTPException: If there's an error parsing or validating the HTA response
    """
    try:
        # Parse JSON response
        parsed_response = json.loads(hta_response_json_str)

        # Basic validation
        if not isinstance(parsed_response, dict):
            raise ValueError(f"Expected JSON object, got {type(parsed_response)}")

        # Convert to HTAResponseModel for structural validation
        try:
            # This validates the structure
            hta_response_model = HTAResponseModel(**parsed_response)
            hta_response = hta_response_model.dict()
        except ValidationError as ve:
            logger.error(
                "LLM HTA response validation error user %s: %s",
                user_id,
                str(ve),
            )
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Invalid HTA structure from LLM: {ve}",
            ) from ve

        # Optionally enrich HTA with discovery insights
        if discovery_service is not None:
            enriched_hta = enrich_hta_with_discovery(
                discovery_service,
                hta_response,
                orchestrator_i,
                {
                    "goal": processed_goal,
                    "context": processed_context,
                    "user_id": user_id,
                },
            )
            if enriched_hta:
                logger.info(
                    "Enriched HTA with discovery insights for user %s",
                    user_id,
                )
                hta_response = enriched_hta

        # Convert to HTATreeModel
        hta_tree = HTATreeModel.from_hta_response(hta_response)

        # Add manifest field to HTA tree (if generated by LLM)
        if orchestrator_i and orchestrator_i.roadmap_service:
            try:
                roadmap_service = orchestrator_i.roadmap_service
                manifest_json = await roadmap_service.generate_manifest_from_hta(
                    hta_tree, processed_goal, user_id
                )
                if manifest_json:
                    hta_tree.manifest = manifest_json
                    logger.info(
                        "Generated manifest from HTA for user %s",
                        user_id,
                    )
                    snapshot.log_event(
                        event_type=constants.EVENT_TYPE_MANIFEST_GENERATED,
                        metadata={"user_id": user_id},
                    )
            except Exception as manifest_err:  # noqa: W0718
                # Don't fail the whole operation if manifest generation fails
                logger.error(
                    "Error generating manifest from HTA for user %s: %s",
                    user_id,
                    str(manifest_err),
                    exc_info=True,
                )

        # Get final model as dict for processing
        hta_model_dict = hta_tree.dict()
        return hta_model_dict

    except json.JSONDecodeError as json_err:
        logger.error(
            "Failed to parse LLM HTA response for user %s: %s",
            user_id,
            json_err,
        )
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid JSON in LLM response: {json_err}",
        ) from json_err
    except (ValueError, TypeError, AttributeError) as err:
        logger.error(
            "Error processing HTA data for user %s: %s",
            user_id,
            err,
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Error processing HTA data: {err}",
        ) from err
    except Exception as e:  # noqa: W0718
        # Broad catch is intentional to ensure robust error handling
        logger.exception(
            "Unexpected error parsing HTA response for user %s: %s",
            user_id,
            e,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unexpected error parsing HTA: {e}",
        ) from e
