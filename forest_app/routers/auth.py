# forest_app/routers/auth.py

import logging
from datetime import timedelta
from typing import Optional  # Added Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm

# --- Pydantic Imports ---
from pydantic import BaseModel, EmailStr, Field  # Import base pydantic needs
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from forest_app.core.security import (
    ACCESS_TOKEN_EXPIRE_MINUTES,
    create_access_token,
    get_password_hash,
    verify_password,
)
from forest_app.persistence.database import get_db
from forest_app.persistence.repository import create_user, get_user_by_email
from forest_app.utils.import_fallbacks import import_with_fallback

# --- REMOVED INCORRECT IMPORT ---
# from forest_app.core.pydantic_models import Token, UserCreate, UserRead # Assuming models are moved/centralized
try:
    from forest_app.config import constants
except ImportError:

    class ConstantsPlaceholder:
        MIN_PASSWORD_LENGTH = 8
        ONBOARDING_STATUS_NEEDS_GOAL = "needs_goal"

    constants = ConstantsPlaceholder()


logger = logging.getLogger(__name__)
router = APIRouter()


# --- Pydantic Models DEFINED LOCALLY ---
# Define models needed specifically by this router
class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserBase(BaseModel):  # Base needed for others
    email: EmailStr
    full_name: Optional[str] = None


class UserCreate(UserBase):
    password: str = Field(..., min_length=constants.MIN_PASSWORD_LENGTH)


class UserRead(UserBase):
    id: UUID
    is_active: bool
    onboarding_status: Optional[str] = None

    class Config:
        from_attributes = True


# --- End Pydantic Models ---


@router.post("/token", response_model=Token, tags=["Authentication"])
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)
):
    # Function body remains the same...
    logger.debug("Login attempt for email: %s", form_data.username)
    try:
        user = get_user_by_email(db, email=form_data.username)
        if not user or not verify_password(form_data.password, get_user_hashed_password(user)):
            logger.warning(
                "Login failed for email %s: Incorrect email or password.",
                form_data.username,
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
        if get_user_is_active(user) is False:
            logger.warning("Login failed for email %s: User is inactive.", get_user_email(user))
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Inactive user"
            )

        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": get_user_email(user)}, expires_delta=access_token_expires
        )
        logger.info("User %s logged in successfully.", get_user_email(user))
        return Token(access_token=access_token, token_type="bearer")

    except HTTPException:
        raise
    except SQLAlchemyError as db_err:
        logger.exception(
            "Database error during login for %s: %s", form_data.username, db_err
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database error during login. Please try again later.",
        )
    except Exception as e:
        logger.exception(
            "Unexpected error during login for %s: %s", form_data.username, e
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during login.",
        )


@router.post(
    "/register",
    response_model=UserRead,
    status_code=status.HTTP_201_CREATED,
    tags=["Authentication"],
)
async def register_user(user_in: UserCreate, db: Session = Depends(get_db)):
    # Function body remains the same...
    logger.info("Registration attempt for email: %s", user_in.email)
    try:
        db_user = get_user_by_email(db, email=user_in.email)
        if db_user:
            logger.warning(
                "Registration failed for %s: Email already registered.", user_in.email
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered",
            )

        hashed_password = get_password_hash(user_in.password)
        user_data = {
            "email": user_in.email,
            "hashed_password": hashed_password,
            "full_name": user_in.full_name,
            "is_active": True,
        }
        created_user = create_user(db=db, user_data=user_data)

        if not created_user:
            logger.error(
                "create_user function returned None for email %s. Checking for race condition.",
                user_in.email,
            )
            if get_user_by_email(db, email=user_in.email):
                logger.warning(
                    "Registration failed for %s due to likely concurrent request.",
                    user_in.email,
                )
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Email already registered (concurrent request likely)",
                )
            else:
                logger.error(
                    "Failed to create user model for %s for unknown reason.",
                    user_in.email,
                )
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to create user model.",
                )

        logger.info(
            "User %s registered successfully (ID: %s). Preparing response.",
            get_user_email(created_user),
            getattr(created_user, "id", "Pending"),
        )
        response_data = UserRead.model_validate(
            created_user, from_attributes=True
        ).model_dump()
        response_data["onboarding_status"] = constants.ONBOARDING_STATUS_NEEDS_GOAL
        return UserRead.model_validate(response_data)

    except HTTPException:
        raise
    except SQLAlchemyError as db_err:
        logger.exception(
            "Database error during registration for %s: %s", user_in.email, db_err
        )
        if (
            "UNIQUE constraint failed" in str(db_err)
            or "duplicate key value violates unique constraint" in str(db_err).lower()
        ):
            logger.warning(
                "Registration failed for %s due to unique constraint (likely email).",
                user_in.email,
            )
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, detail="Email already registered."
            )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database error during registration.",
        )
    except Exception as e:
        logger.exception(
            "Unexpected error during registration for %s: %s", user_in.email, e
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during registration.",
        )


# --- Ensure UserModel attribute access is correct ---
# If current_user is a SQLAlchemy model, access attributes directly
# Add fallback for NoneType or missing attributes

def get_user_email(user):
    if hasattr(user, 'email'):
        return user.email
    return None

def get_user_hashed_password(user):
    if hasattr(user, 'hashed_password'):
        return user.hashed_password
    return None

def get_user_is_active(user):
    if hasattr(user, 'is_active'):
        return user.is_active
    return False

constants = import_with_fallback(
    lambda: __import__('forest_app.config', fromlist=['constants']).constants,
    lambda: {},
    logger,
    "constants"
)
