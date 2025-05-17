"""
Onboarding Schemas Module

This module contains Pydantic models for the onboarding process, centralizing
schema definitions to avoid code duplication across router files.
"""

from typing import Any, Optional

from pydantic import BaseModel, Field


class SetGoalRequest(BaseModel):
    """Request model for setting a user's goal during onboarding."""

    goal_description: Any = Field(
        ..., description="The user's goal description to be processed"
    )


class AddContextRequest(BaseModel):
    """Request model for adding context during onboarding."""

    context_reflection: Any = Field(
        ..., description="The user's contextual information for the goal"
    )


class OnboardingResponse(BaseModel):
    """Response model for onboarding endpoints."""

    onboarding_status: str
    message: str
    refined_goal: Optional[str] = None
    first_task: Optional[dict] = None
