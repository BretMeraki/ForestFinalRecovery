"""Financial Readiness Analysis Engine Module.

This module provides functionality for assessing and tracking a user's financial readiness level
through initial baseline assessment and ongoing reflection analysis using LLM integration.
It includes robust error handling, feature flag support, and serialization capabilities.
"""

# Standard library imports
import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional

# Third-party imports
from pydantic import BaseModel, Field, ValidationError

# Local application imports
from forest_app.utils import (
    LLMClient,
    LLMError,
    clamp01,
    handle_http_errors,
    is_enabled,
    validate_and_parse_timestamp,
)

# Constants
DEFAULT_READINESS = 0.5
FEATURE_FLAG = "FEATURE_ENABLE_FINANCIAL_READINESS"

# Initialize module logger
logger = logging.getLogger(__name__)


# --- Define Response Models ---
class BaselineReadinessResponse(BaseModel):
    """Response model for baseline financial readiness assessment."""

    readiness: float = Field(..., ge=0.0, le=1.0)


class ReflectionDeltaResponse(BaseModel):
    """Response model for financial readiness delta calculation from reflections."""

    delta: float


class FinancialReadinessEngine:
    """
    Assesses and tracks the user's financial readiness level (0.0–1.0).

    This engine uses an LLM for assessment based on reflections or context updates.
    It respects the FINANCIAL_READINESS feature flag and provides methods for:
    - Initial baseline assessment
    - Reflection-based adjustments
    - Serialization and deserialization of state
    """

    def __init__(self, llm_client: LLMClient):
        """
        Initialize the financial readiness engine.

        Args:
            llm_client: An instance of the LLMClient for making calls.

        Raises:
            TypeError: If the provided llm_client is not a valid LLMClient instance.
        """
        self.llm_client = llm_client
        self.readiness = DEFAULT_READINESS
        self.last_update = None

        if not isinstance(llm_client, LLMClient):
            raise TypeError(
                "FinancialReadinessEngine requires a valid LLMClient instance."
            )

        logger.info("FinancialReadinessEngine initialized.")

    def _reset_state(self) -> None:
        """Reset readiness to default and clear timestamp."""
        self.readiness = DEFAULT_READINESS
        self.last_update = None
        logger.info("Financial readiness state has been reset to default")
        logger.debug("Financial Readiness state reset to default.")

    def update_from_dict(self, data: Dict[str, Any]) -> None:
        """
        Rehydrate engine state from a dictionary.

        Resets state if FINANCIAL_READINESS feature is disabled or if the provided
        data is invalid.

        Args:
            data: Dictionary containing readiness state information.
        """
        if not is_enabled(FEATURE_FLAG):
            logger.debug("Financial readiness feature is disabled. Resetting state.")
            self._reset_state()
            return

        try:
            # Safely update state from dict
            self.readiness = clamp01(float(data.get("readiness", DEFAULT_READINESS)))

            # Handle timestamp safely using the utility function
            self.last_update = validate_and_parse_timestamp(data.get("last_update"))

            logger.debug("Updated financial readiness state from dict")

        except (ValueError, TypeError) as e:
            logger.warning("Invalid data in update_from_dict: %s. Resetting state.", e)
            self._reset_state()

    def to_dict(self) -> Dict[str, Any]:
        """
        Serialize engine state to a dictionary.

        Returns an empty dict if FINANCIAL_READINESS feature is disabled.

        Returns:
            Dictionary containing the current readiness state.
        """
        if not is_enabled(FEATURE_FLAG):
            logger.debug(
                "Financial readiness feature is disabled. Returning empty dict."
            )
            return {}

        return {
            "readiness": self.readiness,
            "last_update": self.last_update.isoformat() if self.last_update else None,
        }

    @handle_http_errors("Error assessing baseline financial readiness")
    async def assess_baseline(self, description: str) -> float:
        """
        Perform initial baseline assessment using LLM.

        Returns current readiness without LLM call or state update if
        FINANCIAL_READINESS feature is disabled.

        Args:
            description: User description to analyze for financial readiness assessment.

        Returns:
            The readiness score (0.0-1.0) - either newly assessed or current state.

        Raises:
            HTTPException: If there's an error during the assessment process.
        """
        if not is_enabled(FEATURE_FLAG):
            logger.debug(
                "Financial readiness feature is disabled. Returning current readiness."
            )
            return self.readiness

        if not description or not description.strip():
            logger.warning(
                "Empty or invalid description provided for baseline assessment."
            )
            return self.readiness

        logger.info("Assessing baseline financial readiness...")

        try:
            # Call LLM for assessment
            response = await self.llm_client.generate(
                prompt=f"""
                Analyze the following financial situation and provide a readiness score between 0.0 and 1.0:
                {description}
                
                Return a JSON object with a single 'readiness' field.
                """,
                response_model=BaselineReadinessResponse,
            )

            # Update state with new assessment
            self.readiness = clamp01(response.readiness)
            self.last_update = datetime.now(timezone.utc)

            logger.info("Baseline financial readiness assessed: %.2f", self.readiness)
            return self.readiness

        except (LLMError, ValidationError) as e:
            logger.error("Error in baseline assessment: %s", str(e), exc_info=True)
            # Return current state on error
            return self.readiness

    @handle_http_errors("Error analyzing financial reflection")
    async def analyze_reflection(
        self, reflection: str, context: Optional[Dict[str, Any]] = None
    ) -> float:
        """
        Adjust readiness based on reflection using LLM delta.

        Returns current readiness without LLM call or state update if
        FINANCIAL_READINESS feature is disabled.

        Args:
            reflection: User reflection to analyze for readiness adjustment
            context: Optional context information to enhance the analysis

        Returns:
            The readiness score (0.0-1.0) - either updated or current state.

        Raises:
            HTTPException: If there's an error during the analysis process.
        """
        if not is_enabled(FEATURE_FLAG):
            logger.debug(
                "Financial readiness feature is disabled. Returning current readiness."
            )
            return self.readiness

        if not reflection or not reflection.strip():
            logger.warning("Empty or invalid reflection provided for analysis.")
            return self.readiness

        logger.info("Analyzing reflection for financial readiness adjustment...")

        try:
            # Prepare prompt with context if available
            context_str = (
                json.dumps(context, indent=2) if context else "No additional context"
            )

            # Call LLM for reflection analysis
            response = await self.llm_client.generate(
                prompt=f"""
                Analyze the following reflection and provide a delta (-1.0 to 1.0) 
                to adjust the user's financial readiness score:
                
                Current Readiness: {self.readiness:.2f}
                
                Reflection:
                {reflection}
                
                Context:
                {context_str}
                
                Return a JSON object with a single 'delta' field.
                """,
                response_model=ReflectionDeltaResponse,
            )

            # Calculate and clamp new readiness
            new_readiness = self.readiness + response.delta
            self.readiness = clamp01(new_readiness)
            self.last_update = datetime.now(timezone.utc)

            logger.info(
                "Financial readiness updated by %.2f to %.2f",
                response.delta,
                self.readiness,
            )
            return self.readiness

        except (LLMError, ValidationError) as e:
            logger.error("Error in reflection analysis: %s", str(e), exc_info=True)
            logger.info(
                "Reflection analysis failed or returned no delta. "
                "Readiness remains %.3f",
                self.readiness,
            )
            return self.readiness
