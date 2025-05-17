"""
Pydantic Fallback Classes

This module provides centralized fallback implementations for Pydantic-related components
when the actual Pydantic implementation fails to import or is not available.

Usage:
    try:
        from pydantic import BaseModel, Field, ValidationError  # Real implementation
    except ImportError:
        from forest_app.integrations.pydantic_fallbacks import BaseModel, Field, ValidationError  # Fallbacks
"""

import logging
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


class ValidationError(Exception):
    """Fallback for Pydantic's ValidationError."""

    def __init__(self, errors: List[Dict[str, Any]], model: Any = None):
        self.errors = errors
        self.model = model
        message = f"Validation error: {errors}"
        super().__init__(message)


def Field(*args, **kwargs):
    """
    Fallback for Pydantic's Field function.

    Returns whatever is passed as default or None.
    """
    return kwargs.get("default", None)


class BaseModel:
    """
    Fallback for Pydantic's BaseModel class.

    Implements a basic dictionary-like interface with minimal validation.
    """

    def __init__(self, **data):
        logger.warning("Using fallback Pydantic BaseModel. Validation will be minimal.")
        for key, value in data.items():
            setattr(self, key, value)

    def dict(self) -> Dict[str, Any]:
        """Convert model to dictionary."""
        return {k: v for k, v in self.__dict__.items() if not k.startswith("_")}

    def json(self) -> str:
        """Convert model to JSON string."""
        import json

        return json.dumps(self.dict())

    @classmethod
    def parse_obj(cls, obj: Dict[str, Any]) -> "BaseModel":
        """Create a model instance from a dictionary."""
        return cls(**obj)

    @classmethod
    def parse_raw(cls, raw_data: str) -> "BaseModel":
        """Create a model instance from a JSON string."""
        import json

        try:
            data = json.loads(raw_data)
            return cls.parse_obj(data)
        except json.JSONDecodeError as e:
            raise ValidationError(
                [{"loc": ["__root__"], "msg": f"Invalid JSON: {str(e)}"}]
            )

    class Config:
        """Fallback Config class."""

        extra = "ignore"
        arbitrary_types_allowed = True


def get_pydantic_fallbacks():
    """
    Returns all Pydantic fallback classes as a tuple.

    Returns:
        tuple: (BaseModel, Field, ValidationError)
    """
    return (BaseModel, Field, ValidationError)
