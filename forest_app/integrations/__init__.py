"""
Forest App Integrations Package

This package contains external service integrations and clients.
It also provides centralized fallback implementations for when
external dependencies are unavailable, ensuring consistent behavior
throughout the application.

Import strategy:
1. Try to import actual implementations first
2. Fall back to centralized fallback implementations if needed
3. Expose a consistent interface regardless of which is used
"""

# Import all centralized fallbacks first, so they're available if needed
from forest_app.integrations.llm_fallbacks import \
    LLMClient as FallbackLLMClient
from forest_app.integrations.llm_fallbacks import LLMError as FallbackLLMError
from forest_app.integrations.llm_fallbacks import \
    LLMValidationError as FallbackLLMValidationError
from forest_app.integrations.llm_fallbacks import get_llm_fallbacks
from forest_app.integrations.pydantic_fallbacks import \
    BaseModel as FallbackBaseModel
from forest_app.integrations.pydantic_fallbacks import Field as FallbackField
from forest_app.integrations.pydantic_fallbacks import \
    ValidationError as FallbackValidationError
from forest_app.integrations.pydantic_fallbacks import get_pydantic_fallbacks

# Try to import actual implementations
try:
    from forest_app.integrations.llm import (DistilledReflectionResponse,
                                             HTAEvolveResponse, LLMClient,
                                             LLMError, LLMResponseModel,
                                             LLMValidationError,
                                             generate_response)
    from forest_app.integrations.llm_service import (BaseLLMService,
                                                     GoogleGeminiService,
                                                     LLMConfigError,
                                                     LLMRequestError,
                                                     LLMResponseError,
                                                     LLMServiceError,
                                                     create_llm_service)
except ImportError:
    # Fall back to using dummy implementations when real ones aren't available
    LLMClient = FallbackLLMClient
    LLMError = FallbackLLMError
    LLMValidationError = FallbackLLMValidationError
    # These would need more implementation if used extensively
    DistilledReflectionResponse = None
    HTAEvolveResponse = None
    LLMResponseModel = None
    BaseLLMService = None
    GoogleGeminiService = None
    LLMConfigError = None
    LLMRequestError = None
    LLMResponseError = None
    LLMServiceError = None

    def generate_response(*args, **kwargs):
        """Fallback implementation for generate_response when actual implementation is unavailable."""
        import logging

        logger = logging.getLogger(__name__)
        logger.warning(
            "Called dummy generate_response with args=%s, kwargs=%s", args, kwargs
        )
        return None

    def create_llm_service(*args, **kwargs):
        """Fallback implementation for create_llm_service when actual implementation is unavailable."""
        import logging

        logger = logging.getLogger(__name__)
        logger.warning(
            "Called dummy create_llm_service with args=%s, kwargs=%s", args, kwargs
        )
        return None


__all__ = [
    # LLMClient and related
    "LLMClient",
    "LLMError",
    "LLMValidationError",
    "HTAEvolveResponse",
    "DistilledReflectionResponse",
    "generate_response",
    "LLMResponseModel",
    # LLM Service Abstraction Layer
    "BaseLLMService",
    "GoogleGeminiService",
    "create_llm_service",
    "LLMServiceError",
    "LLMConfigError",
    "LLMRequestError",
    "LLMResponseError",
    # Fallback utilities
    "get_llm_fallbacks",
    "get_pydantic_fallbacks",
    "FallbackLLMClient",
    "FallbackLLMError",
    "FallbackBaseModel",
    "FallbackField",
    "FallbackValidationError",
]
