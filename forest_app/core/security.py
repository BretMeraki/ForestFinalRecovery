# forest_app/core/security.py (Refactored - Updated Type Hint)

import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel, ValidationError
from sqlalchemy.orm import Session

from forest_app.persistence.database import get_db

logger = logging.getLogger(__name__)

UserModel = None
get_user_by_email: Optional[Callable[[Session, str], Optional[UserModel]]] = None


def initialize_security_dependencies(
    _get_user_by_email: Callable[[Session, str], Optional[UserModel]],
    _user_model: type,
):
    global get_user_by_email, UserModel
    if not all([_get_user_by_email, _user_model]):
        logger.critical("CRITICAL: Failed to initialize security dependencies.")
        return
    get_user_by_email = _get_user_by_email
    UserModel = _user_model
    logger.info("Security dependencies (get_user_by_email, UserModel) initialized.")


SECRET_KEY = os.getenv("SECRET_KEY", "dummy_insecure_secret_key_replace_in_env")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))
if SECRET_KEY == "dummy_insecure_secret_key_replace_in_env":
    logger.critical("FATAL SECURITY WARNING: SECRET_KEY environment variable not set.")

pwd_context = CryptContext(schemes=["argon2", "bcrypt"], deprecated=["bcrypt"])
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/token")


class TokenData(BaseModel):
    email: Optional[str] = None


def verify_password(plain_password: str, hashed_password: str) -> bool:
    if not plain_password or not hashed_password:
        return False
    try:
        return pwd_context.verify(plain_password, hashed_password)
    except Exception as exc:
        logger.error("Error verifying password: %s", exc, exc_info=True)
        return False


def get_password_hash(password: str) -> str:
    if not password:
        raise ValueError("Password cannot be empty")
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=ACCESS_TOKEN_EXPIRE_MINUTES
        )
    to_encode.update({"exp": expire})
    if "sub" not in to_encode and "email" in to_encode:
        to_encode["sub"] = to_encode.pop("email")
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


async def decode_access_token(token: str = Depends(oauth2_scheme)) -> TokenData:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: Optional[str] = payload.get("sub")
        if email is None:
            logger.warning("Token payload missing 'sub'.")
            raise credentials_exception
        token_data = TokenData(email=email)
    except JWTError as exc:
        logger.warning("JWTError decoding token: %s", exc)
        raise credentials_exception
    except ValidationError as exc:
        logger.warning("Token Data validation error: %s", exc)
        raise credentials_exception
    except Exception as exc:
        logger.exception("Unexpected error decoding token: %s", exc)
        raise credentials_exception
    return token_data


async def get_current_user(
    token_data: TokenData = Depends(decode_access_token),
    db: Session = Depends(get_db),
) -> Any:
    if not callable(get_user_by_email) or UserModel is None:
        logger.critical(
            "Security dependencies (get_user_by_email/UserModel) not initialized!"
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Server configuration error [Security Dep Init]",
        )
    if token_data.email is None:
        logger.error("Token data email is None in get_current_user.")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token data",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        logger.debug(
            "Fetching user in get_current_user for email: %s", token_data.email
        )
        user = get_user_by_email(db=db, email=token_data.email)
        if user is None:
            logger.warning(
                "User '%s' from token not found in database.", token_data.email
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User associated with token not found",
                headers={"WWW-Authenticate": "Bearer"},
            )
        logger.debug("User '%s' found in database.", token_data.email)
        return user
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception(
            "Error fetching user '%s' in get_current_user: %s", token_data.email, exc
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving user information.",
        )


async def get_current_active_user(
    current_user: Any = Depends(get_current_user),
) -> Any:
    if not getattr(current_user, "is_active", False):
        logger.warning(
            "Authentication attempt by inactive user: %s",
            getattr(current_user, "email", "N/A"),
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Inactive user"
        )
    return current_user
