# forest_app/routers/trees.py

"""
HTA Trees Router for Forest OS API.

Handles creation and retrieval of HTA trees, including idempotency, manifest validation,
and integration with EnhancedHTAService.
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional
from uuid import UUID, uuid4

from fastapi import (APIRouter, Body, Depends, HTTPException, Path, Request,
                     status)
from pydantic import BaseModel, Field
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from forest_app.core.roadmap_models import RoadmapManifest
from forest_app.core.auth.security_utils import get_current_active_user
from forest_app.core.services.enhanced_hta import EnhancedHTAService
# --- Service Access ---
from forest_app.dependencies import get_hta_service
# --- Dependencies & Models ---
from forest_app.database.session import get_db
from forest_app.models import UserModel
from forest_app.persistence.repository import HTATreeRepository

logger = logging.getLogger(__name__)
router = APIRouter()


# --- Pydantic Models ---
class TreeCreateRequest(BaseModel):
    """Request to create a new HTA tree."""

    manifest: Dict[str, Any] = Field(..., description="RoadmapManifest in JSON format")
    idempotency_key: Optional[str] = Field(
        None, description="Optional idempotency key to prevent duplicate trees"
    )
    metadata: Optional[Dict[str, Any]] = Field(
        None, description="Optional metadata about the tree"
    )


class TreeResponse(BaseModel):
    """Response from tree creation or retrieval."""

    tree_id: UUID
    user_id: UUID
    created_at: datetime
    updated_at: datetime
    step_count: int
    message: str


# --- Endpoints ---
@router.post("/", response_model=TreeResponse, tags=["HTA"])
async def create_tree(
    request: Request,
    tree_data: TreeCreateRequest = Body(...),
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_active_user),
    hta_service: EnhancedHTAService = Depends(get_hta_service),
):
    """
    Create a new HTA tree from a RoadmapManifest.

    This endpoint is idempotent when an idempotency_key is provided,
    ensuring the same tree is not created multiple times.
    """
    user_id = current_user.id

    # Create a request context for auditing
    request_context = {
        "ip": (
            request.client.host
            if hasattr(request, "client") and hasattr(request.client, "host")
            else None
        ),
        "user_agent": request.headers.get("user-agent"),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    try:
        # Check for idempotency if key provided
        if tree_data.idempotency_key:
            repo = HTATreeRepository(db)
            existing_tree = repo.find_by_metadata(
                user_id=user_id,
                metadata_key="idempotency_key",
                metadata_value=tree_data.idempotency_key,
            )

            if existing_tree:
                step_count = (
                    len(existing_tree.manifest.get("steps", []))
                    if existing_tree.manifest
                    else 0
                )
                logger.info(
                    "Using existing tree for idempotency key %s: %s",
                    tree_data.idempotency_key,
                    existing_tree.id,
                )
                return TreeResponse(
                    tree_id=existing_tree.id,
                    user_id=existing_tree.user_id,
                    created_at=existing_tree.created_at,
                    updated_at=existing_tree.updated_at,
                    step_count=step_count,
                    message="Retrieved existing tree with matching idempotency key",
                )

        # Parse manifest
        try:
            manifest = RoadmapManifest.model_validate(tree_data.manifest)
            if not manifest.tree_id:
                manifest.tree_id = uuid4()
        except (ValidationError, TypeError, ValueError) as e:
            logger.error("Invalid manifest: %s", e)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid manifest format: {str(e)}",
            ) from e

        # Create the tree
        try:
            tree_model = await hta_service.generate_initial_hta_from_manifest(
                manifest=manifest, user_id=user_id, request_context=request_context
            )

            # If idempotency key provided, store in tree manifest
            if tree_data.idempotency_key:
                # Update tree manifest with idempotency key
                repo = HTATreeRepository(db)
                manifest = tree_model.manifest or {}
                manifest["idempotency_key"] = tree_data.idempotency_key
                if tree_data.metadata:
                    manifest.update(tree_data.metadata)
                repo.update_metadata(tree_model.id, manifest)
                # Reload tree_model to get updated manifest from DB
                tree_model_reloaded = repo.get_tree(tree_model.id, user_id)
                if tree_model_reloaded is not None:
                    tree_model = tree_model_reloaded
                # Parse manifest as RoadmapManifest if needed
                if isinstance(tree_model.manifest, dict):
                    try:
                        manifest_obj = RoadmapManifest.model_validate(
                            tree_model.manifest
                        )
                    except Exception:
                        manifest_obj = tree_model.manifest
                else:
                    manifest_obj = tree_model.manifest
            else:
                manifest_obj = manifest

            # Count steps from manifest
            step_count = len(
                getattr(manifest_obj, "steps", manifest_obj.get("steps", []))
            )

            return TreeResponse(
                tree_id=tree_model.id,
                user_id=tree_model.user_id,
                created_at=tree_model.created_at,
                updated_at=tree_model.updated_at,
                step_count=step_count,
                message="Tree created successfully",
            )

        except ValueError as val_err:
            logger.error("Validation error: %s", val_err)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Validation error: {str(val_err)}",
            ) from val_err

        except SQLAlchemyError as db_err:
            logger.error("Database error creating tree: %s", db_err)
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Database error creating tree",
            ) from db_err

        except Exception as e:  # noqa: W0718
            # Broad catch is intentional for FastAPI endpoint robustness and to log unexpected errors.
            logger.error("Unexpected error creating tree: %s", e)
            if isinstance(e, HTTPException):
                raise e
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create tree",
            ) from e

    except IntegrityError as int_err:
        # This would happen if trying to create a tree with duplicate ID
        logger.error("Integrity error: %s", int_err)
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Tree with this ID already exists",
        ) from int_err


@router.get("/{tree_id}", response_model=TreeResponse, tags=["HTA"])
async def get_tree(
    tree_id: UUID = Path(..., description="ID of the tree to retrieve"),
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_active_user),
):
    """
    Get a tree by ID.

    Retrieves an existing HTA tree by its ID.
    """
    user_id = current_user.id

    try:
        repo = HTATreeRepository(db)
        tree = repo.get_tree(tree_id, user_id)

        if not tree:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Tree not found"
            )

        step_count = len(tree.manifest.get("steps", [])) if tree.manifest else 0

        return TreeResponse(
            tree_id=tree.id,
            user_id=tree.user_id,
            created_at=tree.created_at,
            updated_at=tree.updated_at,
            step_count=step_count,
            message="Tree retrieved successfully",
        )

    except HTTPException:
        raise

    except Exception as e:  # noqa: W0718
        # Broad catch is intentional for FastAPI endpoint robustness and to log unexpected errors.
        logger.error("Error retrieving tree %s: %s", tree_id, e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve tree",
        ) from e
