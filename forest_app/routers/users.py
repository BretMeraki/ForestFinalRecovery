# forest_app/routers/users.py (Corrected Import and Type Hint)

import logging
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel, EmailStr, ValidationError
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from forest_app.utils.import_fallbacks import import_with_fallback
from forest_app.utils.shared_helpers import get_snapshot_data, get_snapshot_id

logger = logging.getLogger(__name__)

# --- Import dependencies with fallbacks ---
get_current_active_user = import_with_fallback(
    lambda: __import__('forest_app.core.security', fromlist=['get_current_active_user']).get_current_active_user,
    lambda: lambda x: None,
    logger,
    "get_current_active_user"
)
get_db = import_with_fallback(
    lambda: __import__('forest_app.persistence.database', fromlist=['get_db']).get_db,
    lambda: lambda: None,
    logger,
    "get_db"
)
UserModel = import_with_fallback(
    lambda: __import__('forest_app.persistence.models', fromlist=['UserModel']).UserModel,
    lambda: type('UserModel', (), {}),
    logger,
    "UserModel"
)
MemorySnapshotRepository = import_with_fallback(
    lambda: __import__('forest_app.persistence.repository', fromlist=['MemorySnapshotRepository']).MemorySnapshotRepository,
    lambda: type('MemorySnapshotRepository', (), {}),
    logger,
    "MemorySnapshotRepository"
)
MemorySnapshot = import_with_fallback(
    lambda: __import__('forest_app.core.snapshot', fromlist=['MemorySnapshot']).MemorySnapshot,
    lambda: type('MemorySnapshot', (), {}),
    logger,
    "MemorySnapshot"
)

# --- Constants placeholder ---
class ConstantsPlaceholder:
    ONBOARDING_STATUS_NEEDS_GOAL = "needs_goal"
    ONBOARDING_STATUS_NEEDS_CONTEXT = "needs_context"
    ONBOARDING_STATUS_COMPLETED = "completed"

constants = ConstantsPlaceholder()

router = APIRouter()


# --- Pydantic Models DEFINED LOCALLY ---
class UserBase(BaseModel):
    email: EmailStr
    full_name: Optional[str] = None


class UserRead(UserBase):
    id: UUID
    is_active: bool
    onboarding_status: Optional[str] = None

    class Config:
        from_attributes = True


# --- End Pydantic Models ---


@router.get("/me", response_model=UserRead, tags=["Users"])
async def read_users_me(
    # --- Use the correct UserModel for type hint ---
    current_user: UserModel = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Gets the current logged-in user's details, including onboarding status."""
    user_id: UUID = current_user.id
    logger.info(
        "Fetching details for current user ID: %s (%s)", user_id, current_user.email
    )
    onboarding_status = constants.ONBOARDING_STATUS_NEEDS_GOAL
    try:
        repo = MemorySnapshotRepository(db)
        stored_model = repo.get_latest_snapshot(user_id)
        if stored_model and get_snapshot_data(stored_model):
            try:
                snapshot = MemorySnapshot.from_dict(get_snapshot_data(stored_model))
                if snapshot.activated_state.get("activated", False):
                    onboarding_status = constants.ONBOARDING_STATUS_COMPLETED
                elif snapshot.activated_state.get("goal_set", False):
                    onboarding_status = constants.ONBOARDING_STATUS_NEEDS_CONTEXT
            except (ValidationError, TypeError, KeyError, Exception) as snap_load_err:
                logger.error(
                    "Error loading/parsing snapshot for user %s status: %s.",
                    user_id,
                    snap_load_err,
                    exc_info=True,
                )
        elif stored_model:
            logger.warning(
                "Latest snapshot (ID: %s) for user %s has no data.",
                get_snapshot_id(stored_model),
                user_id,
            )
        else:
            logger.info("No snapshot found for user %s.", user_id)
    except SQLAlchemyError as db_err:
        logger.error(
            "DB error fetching snapshot user %s status: %s",
            user_id,
            db_err,
            exc_info=True,
        )
    except Exception as e:
        # Broad catch is intentional for FastAPI endpoint robustness and to log unexpected errors.
        logger.error(
            "Unexpected error fetching snapshot user %s status: %s",
            user_id,
            e,
            exc_info=True,
        )

    try:
        user_data = UserRead.model_validate(
            current_user, from_attributes=True
        ).model_dump()
        user_data["onboarding_status"] = onboarding_status
        return UserRead.model_validate(user_data)
    except ValidationError as val_err:
        logger.error(
            "Validation failed creating final UserRead response user %s: %s",
            user_id,
            val_err,
        )
        # Fallback to returning basic user info without onboarding status if final validation fails
        return UserRead.model_validate(current_user, from_attributes=True)
