"""
Simple verification script for the LLM service implementation.
This script avoids test framework complexities and just verifies imports and basic instantiation.
"""

import os
import sys
from unittest.mock import patch
from forest_app.utils.import_fallbacks import import_with_fallback
import logging

# Add the project root to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

print("Attempting to import LLM service modules...")

logger = logging.getLogger(__name__)

llm_service_import = import_with_fallback(
    lambda: __import__('forest_app.integrations.llm_service', fromlist=['LLMService', 'LLMError', 'LLMValidationError', 'LLMConfigurationError', 'LLMConnectionError']),
    lambda: type('DummyLLMService', (), {}),
    logger,
    "llm_service_import"
)

try:
    from forest_app.integrations.llm_service import (
        BaseLLMService,
        GoogleGeminiService,
        create_llm_service,
        get_llm_service,
    )

    print("✅ Successfully imported llm_service module")

    from forest_app.integrations.context_trimmer import ContextTrimmer

    print("✅ Successfully imported context_trimmer module")

    from forest_app.integrations.prompt_augmentation import PromptAugmentationService

    print("✅ Successfully imported prompt_augmentation module")

except ImportError as e:
    print(f"❌ Import error: {e}")
    sys.exit(1)

print("\nVerifying class instantiation...")
try:
    # Mock the necessary Google API calls
    with patch("google.generativeai.configure") as mock_configure:
        with patch("google.generativeai.GenerativeModel") as mock_generative_model:
            # Create the service
            service = create_llm_service(provider="gemini", api_key="test_key")

            print(f"✅ Successfully created LLM service: {service.__class__.__name__}")
            print(f"   - Service name: {service.service_name}")
            print(f"   - Default model: {service.default_model}")
            print(f"   - Advanced model: {service.advanced_model_name}")
            print(f"   - Max retries: {service.max_retries}")
            print(f"   - Cache enabled: {service._cache_enabled}")

            # Create auxiliary services
            trimmer = ContextTrimmer()
            print("✅ Successfully created ContextTrimmer")
            print(f"   - Max tokens: {trimmer.config.max_tokens}")

            augmentation = PromptAugmentationService()
            print("✅ Successfully created PromptAugmentationService")
            print(
                f"   - Available templates: {', '.join(augmentation.templates.keys())}"
            )

except Exception as e:
    print(f"❌ Error during verification: {e}")
    raise

print(
    "\n✅ All verifications passed! The LLM service implementation appears to be working correctly."
)
print(
    "Note: This is a basic verification and does not test the actual functionality with real API calls."
)
