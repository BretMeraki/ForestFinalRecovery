import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional  # Added Optional, Any

import forest_app.utils
from forest_app.utils.import_fallbacks import import_with_fallback

# forest_app/modules/emotional_integrity.py

# Create logger first
logger = logging.getLogger(__name__)

# --- Import Feature Flags ---
Feature = import_with_fallback(
    lambda: __import__('forest_app.core.feature_flags', fromlist=['Feature']).Feature,
    lambda: type('Feature', (), {}),
    logger,
    "Feature"
)
is_enabled = import_with_fallback(
    lambda: __import__('forest_app.core.feature_flags', fromlist=['is_enabled']).is_enabled,
    lambda: (lambda *a, **k: False),
    logger,
    "is_enabled"
)

# --- Pydantic Import ---
try:
    from pydantic import BaseModel, Field, ValidationError

    pydantic_import_ok = True
except ImportError:
    logging.getLogger("ei_init").critical(
        "Pydantic not installed. EmotionalIntegrityIndex requires Pydantic for LLM responses."
    )
    pydantic_import_ok = False

    # Define dummy classes if Pydantic isn't installed
    class BaseModel:
        pass

    def Field(*args, **kwargs):
        return None  # Dummy Field function

    class ValidationError(Exception):
        pass


# --- LLM Integration Import ---
try:
    # First try to import from the real implementation
    from forest_app.integrations.llm import (
        LLMClient,
        LLMConfigurationError,
        LLMConnectionError,
        LLMError,
        LLMValidationError,
    )

    llm_import_ok = True
except ImportError as e:
    logging.getLogger("ei_init").warning(f"Using fallback LLM implementation: {e}")
    llm_import_ok = False

    # Import centralized fallback implementations
    from forest_app.integrations.llm_fallbacks import (
        LLMClient,
        LLMError,
        LLMValidationError,
    )


# --- Constants Import ---
try:
    from forest_app.config import constants
except ImportError:
    logger.warning("Failed to import constants, using defaults")
    # Create a dummy constants object with default values
    class DummyConstants:
        EMOTIONAL_INTEGRITY_BASELINE = 0.5
        MIN_EMOTIONAL_INTEGRITY_DELTA = -0.2
        MAX_EMOTIONAL_INTEGRITY_DELTA = 0.2
        DEFAULT_EMOTIONAL_INTEGRITY_DELTA = 0.0
        MIN_EMOTIONAL_INTEGRITY_SCORE = 0.0
        MAX_EMOTIONAL_INTEGRITY_SCORE = 1.0
        EMOTIONAL_INTEGRITY_SCALING_FACTOR = 1.0
        DEFAULT_SCORE_PRECISION = 2
    
    constants = DummyConstants()

# --- Define LLM Response Model ---
# Only define if Pydantic import was successful
if pydantic_import_ok:

    class EmotionalIntegrityResponse(BaseModel):
        # Use Field constraints for validation upon LLM response parsing
        kindness_delta: float = Field(..., ge=-0.2, le=0.2)
        respect_delta: float = Field(..., ge=-0.2, le=0.2)
        consideration_delta: float = Field(..., ge=-0.2, le=0.2)

else:
    # Dummy version if Pydantic failed
    class EmotionalIntegrityResponse:
        pass


# Define default output when feature is disabled or calculation fails
DEFAULT_EI_OUTPUT = {
    "kindness_score": 0.5,
    "respect_score": 0.5,
    "consideration_score": 0.5,
    "overall_index": 0.5,
    "last_update": None,
}


class EmotionalIntegrityIndex:
    """
    Tracks and assesses indicators of emotional integrity based on user input using LLM analysis.
    Requires an LLMClient to be injected. Respects the EMOTIONAL_INTEGRITY feature flag.
    """

    def __init__(self, llm_client: LLMClient):
        """
        Initializes the index.

        Args:
            llm_client: An instance of the LLMClient for making calls.
        """
        if (
            not isinstance(llm_client, LLMClient) and llm_import_ok
        ):  # Only raise if LLM was expected
            # This check might be better handled by the dependency injection framework
            raise TypeError(
                "EmotionalIntegrityIndex requires a valid LLMClient instance unless LLM imports failed."
            )
        self.llm_client = llm_client

        self._reset_state()  # Initialize using reset method
        logger.info("EmotionalIntegrityIndex initialized.")
        if not llm_import_ok:
            logger.error(
                "LLM Integration components failed import. Emotional integrity analysis will not function."
            )

    def _reset_state(self):
        """Resets scores to baseline and clears timestamp."""
        self.kindness_score: float = constants.EMOTIONAL_INTEGRITY_BASELINE
        self.respect_score: float = constants.EMOTIONAL_INTEGRITY_BASELINE
        self.consideration_score: float = constants.EMOTIONAL_INTEGRITY_BASELINE
        self.overall_index: float = constants.EMOTIONAL_INTEGRITY_BASELINE
        self.last_update: Optional[str] = None  # Reset to None
        logger.debug("Emotional Integrity Index state reset to defaults.")

    def _calculate_overall_index(self):
        """Calculates the overall index as a simple average of component scores."""
        scores = [self.kindness_score, self.respect_score, self.consideration_score]
        # Check if list is empty before dividing, though it shouldn't be with current structure
        avg_score = (
            sum(scores) / len(scores) if scores else constants.EMOTIONAL_INTEGRITY_BASELINE
        )
        # Ensure clamping after averaging
        clamped_avg = max(
            constants.MIN_EMOTIONAL_INTEGRITY_SCORE, min(constants.MAX_EMOTIONAL_INTEGRITY_SCORE, avg_score)
        )
        self.overall_index = round(clamped_avg, constants.DEFAULT_SCORE_PRECISION)

    async def analyze_reflection(
        self, reflection_text: str, context: Optional[Dict] = None
    ) -> Dict[str, float]:
        """
        Analyzes reflection text using LLM to assess emotional integrity deltas.
        Returns empty dict if feature is disabled or analysis fails.
        """
        # --- Feature Flag Check ---
        if not is_enabled(Feature.EMOTIONAL_INTEGRITY):
            logger.debug(
                "Skipping analyze_reflection: EMOTIONAL_INTEGRITY feature disabled."
            )
            return {}
        # --- End Check ---

        # Check for valid LLM client if feature is ON
        if (
            not llm_import_ok
            or not isinstance(self.llm_client, LLMClient)
            or not hasattr(self.llm_client, "generate")
        ):
            logger.error(
                "LLMClient not available for Emotional Integrity analysis. Cannot proceed."
            )
            return {}  # Cannot perform analysis

        if not isinstance(reflection_text, str) or not reflection_text.strip():
            logger.warning("Empty or invalid reflection text provided for EI analysis.")
            return {}

        logger.info("Analyzing reflection for emotional integrity via LLMClient...")
        context = context or {}
        context_summary = "{}"
        try:
            # Only include basic context for prompt brevity/focus
            context_data = {
                k: context.get(k) for k in ["shadow_score", "capacity"] if k in context
            }
            context_summary = json.dumps(context_data, default=str)
        except Exception as json_err:
            logger.error("Error serializing context for LLM prompt: %s", json_err)

        # Ensure response model is valid before using its schema
        response_model_schema = "{}"
        if pydantic_import_ok and issubclass(EmotionalIntegrityResponse, BaseModel):
            try:
                response_model_schema = EmotionalIntegrityResponse.model_json_schema(
                    indent=0
                )
            except Exception:  # Catch potential issues generating schema
                logger.error(
                    "Failed to generate Pydantic schema for EmotionalIntegrityResponse"
                )

        prompt = (
            f"You are an objective analyzer assessing emotional integrity indicators in text.\n"
            f"Analyze the following reflection text based on the user's general context:\n\n"
            f'REFLECTION:\n"""\n{reflection_text}\n"""\n\n'
            f"USER CONTEXT (Consider lightly):\n{context_summary}\n\n"
            f"INSTRUCTION:\n"
            f"Carefully evaluate the reflection for expressions of Kindness, Respect, and Consideration (towards self or others).\n"
            f"Assign a delta score between {constants.MIN_EMOTIONAL_INTEGRITY_DELTA} and {constants.MAX_EMOTIONAL_INTEGRITY_DELTA} for each dimension. {constants.DEFAULT_EMOTIONAL_INTEGRITY_DELTA} indicates neutrality.\n"
            f"Base the score PRIMARILY on the text's expressed content and tone.\n"
            f"Return ONLY a valid JSON object matching this schema:\n{response_model_schema}\n"
        )

        deltas = {}
        try:
            logger.debug(
                "Sending prompt to LLMClient for emotional integrity analysis."
            )
            llm_response: Optional[EmotionalIntegrityResponse] = (
                await self.llm_client.generate(
                    prompt_parts=[prompt],
                    response_model=EmotionalIntegrityResponse,
                    use_advanced_model=False,  # Adjust as needed
                )
            )

            if isinstance(llm_response, EmotionalIntegrityResponse):
                # Use model_dump() for Pydantic v2+ or .dict() for v1
                if hasattr(llm_response, "model_dump"):
                    deltas = llm_response.model_dump()
                else:
                    deltas = llm_response.dict()  # Fallback for Pydantic v1
                logger.info("Emotional integrity analysis complete. Deltas: %s", deltas)
            else:
                logger.warning(
                    "LLMClient did not return a valid EmotionalIntegrityResponse."
                )

        except (LLMError, LLMValidationError, ValidationError) as llm_e:
            logger.error("LLM/Validation Error during EI analysis: %s", llm_e)
        except Exception as e:
            logger.exception(
                "Unexpected error during emotional integrity analysis: %s", e
            )

        return deltas  # Return extracted deltas or empty dict on any failure

    def apply_updates(self, deltas: Dict[str, float]):
        """
        Applies calculated deltas to scores and updates the overall index.
        Does nothing if EMOTIONAL_INTEGRITY feature is disabled.
        """
        # --- Feature Flag Check ---
        if not is_enabled(Feature.EMOTIONAL_INTEGRITY):
            logger.debug(
                "Skipping apply_updates: EMOTIONAL_INTEGRITY feature disabled."
            )
            return
        # --- End Check ---

        if not isinstance(deltas, dict) or not deltas:
            logger.debug(
                "No valid deltas provided to apply_updates for EmotionalIntegrityIndex."
            )
            return

        scaling_factor = constants.EMOTIONAL_INTEGRITY_SCALING_FACTOR

        def _update_score(current_score, delta_key):
            delta = deltas.get(delta_key)  # Get delta, might be None
            try:
                # Apply default if delta is None or not convertible
                scaled_delta = (
                    float(
                        delta
                        if delta is not None
                        else constants.DEFAULT_EMOTIONAL_INTEGRITY_DELTA
                    )
                    * scaling_factor
                )
            except (ValueError, TypeError):
                scaled_delta = (
                    float(constants.DEFAULT_EMOTIONAL_INTEGRITY_DELTA) * scaling_factor
                )  # Use default delta on error
            new_score = current_score + scaled_delta
            # Clamp using constants
            return max(
                constants.MIN_EMOTIONAL_INTEGRITY_SCORE,
                min(constants.MAX_EMOTIONAL_INTEGRITY_SCORE, new_score),
            )

        self.kindness_score = _update_score(self.kindness_score, "kindness_delta")
        self.respect_score = _update_score(self.respect_score, "respect_delta")
        self.consideration_score = _update_score(
            self.consideration_score, "consideration_delta"
        )

        self._calculate_overall_index()
        self.last_update = datetime.now(timezone.utc).isoformat()
        logger.info(
            "Emotional Integrity Index updated: Overall=%.*f (K:%.*f, R:%.*f, C:%.*f)",
            constants.DEFAULT_SCORE_PRECISION,
            self.overall_index,
            constants.DEFAULT_SCORE_PRECISION,
            self.kindness_score,
            constants.DEFAULT_SCORE_PRECISION,
            self.respect_score,
            constants.DEFAULT_SCORE_PRECISION,
            self.consideration_score,
        )

    def get_index(self) -> dict:
        """
        Returns the current state of the index. Returns default state if
        EMOTIONAL_INTEGRITY feature is disabled.
        """
        # --- Feature Flag Check ---
        if not is_enabled(Feature.EMOTIONAL_INTEGRITY):
            logger.debug(
                "Returning default EI state: EMOTIONAL_INTEGRITY feature disabled."
            )
            # Return default values, timestamp None
            return DEFAULT_EI_OUTPUT.copy()
        # --- End Check ---

        # Feature enabled, return current state
        return {
            "kindness_score": round(self.kindness_score, constants.DEFAULT_SCORE_PRECISION),
            "respect_score": round(self.respect_score, constants.DEFAULT_SCORE_PRECISION),
            "consideration_score": round(
                self.consideration_score, constants.DEFAULT_SCORE_PRECISION
            ),
            "overall_index": round(self.overall_index, constants.DEFAULT_SCORE_PRECISION),
            "last_update": self.last_update,
        }

    def to_dict(self) -> dict:
        """
        Serializes the engine's state. Returns empty dict if
        EMOTIONAL_INTEGRITY feature is disabled.
        """
        # --- Feature Flag Check ---
        if not is_enabled(Feature.EMOTIONAL_INTEGRITY):
            logger.debug(
                "Skipping EmotionalIntegrityIndex serialization: EMOTIONAL_INTEGRITY feature disabled."
            )
            return {}
        # --- End Check ---

        # Call get_index which returns the current state (already rounded)
        logger.debug("Serializing EmotionalIntegrityIndex state.")
        return self.get_index()

    def update_from_dict(self, data: dict):
        """
        Updates the engine's state from a dictionary. Resets state if
        EMOTIONAL_INTEGRITY feature is disabled.
        """
        # --- Feature Flag Check ---
        if not is_enabled(Feature.EMOTIONAL_INTEGRITY):
            logger.debug(
                "Resetting state via update_from_dict: EMOTIONAL_INTEGRITY feature disabled."
            )
            self._reset_state()
            return
        # --- End Check ---

        # Feature enabled, proceed with loading
        if not isinstance(data, dict):
            logger.warning(
                "Invalid data type for EmotionalIntegrityIndex.update_from_dict: %s. Resetting state.",
                type(data),
            )
            self._reset_state()
            return

        # Helper to load/validate/clamp score
        def _load_score(key: str, default: float) -> float:
            value = data.get(key, default)
            try:
                score = float(value)
                # Clamp using constants
                return max(
                    constants.MIN_EMOTIONAL_INTEGRITY_SCORE,
                    min(constants.MAX_EMOTIONAL_INTEGRITY_SCORE, score),
                )
            except (ValueError, TypeError):
                logger.warning(
                    "Invalid value '%s' for '%s' during load. Using baseline %.2f.",
                    value,
                    key,
                    constants.EMOTIONAL_INTEGRITY_BASELINE,
                )
                return constants.EMOTIONAL_INTEGRITY_BASELINE  # Use baseline constant on error

        self.kindness_score = _load_score(
            "kindness_score", constants.EMOTIONAL_INTEGRITY_BASELINE
        )
        self.respect_score = _load_score("respect_score", constants.EMOTIONAL_INTEGRITY_BASELINE)
        self.consideration_score = _load_score(
            "consideration_score", constants.EMOTIONAL_INTEGRITY_BASELINE
        )

        # Recalculate overall index based on loaded scores
        self._calculate_overall_index()

        # Load last_update timestamp
        # Validate and set timestamp using utility function
        self.last_update = forest_app.utils.validate_dict_timestamp(data, "last_update")

        logger.debug("EmotionalIntegrityIndex state updated from dict.")
