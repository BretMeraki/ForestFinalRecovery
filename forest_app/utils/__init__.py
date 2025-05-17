"""
Forest App Utilities Package

This package contains utility functions and helpers for use throughout the Forest App.
It includes utilities for loading baselines, LLM handling, error handling, data validation,
feature flags, and shared code patterns to reduce duplication across the codebase.
"""

# Standard library imports
import logging

# Import LLM fallbacks directly from centralized location
from forest_app.integrations.llm_fallbacks import (LLMClient,
                                                   LLMConfigurationError,
                                                   LLMConnectionError,
                                                   LLMError,
                                                   LLMValidationError)
# Local application imports
from forest_app.utils.baseline_loader import load_user_baselines
from forest_app.utils.constants_utils import (ConstantsPlaceholder,
                                              get_constants_module)
from forest_app.utils.data_validation import (clamp01,
                                              get_category_from_thresholds,
                                              validate_dict_timestamp,
                                              validate_timestamp)
from forest_app.utils.error_handling import \
    handle_db_errors as handle_db_errors_decorator
from forest_app.utils.error_handling import (handle_http_errors,
                                             validate_and_parse_timestamp)
from forest_app.utils.exception_handlers import (handle_db_errors,
                                                 handle_db_exceptions)
from forest_app.utils.feature_flags import is_enabled, with_feature_flag
# Keep util functions from llm_utils.py
from forest_app.utils.llm_utils import (create_llm_dummy_classes,
                                        handle_llm_import_error)
from forest_app.utils.router_helpers import (commit_and_refresh_db,
                                             handle_router_exceptions)
from forest_app.utils.validation import (get_threshold_label,
                                         is_valid_thresholds)

__all__ = [
    # Baseline utilities
    "load_user_baselines",
    # LLM utilities
    "LLMClient",
    "LLMError",
    "LLMValidationError",
    "LLMConfigurationError",
    "LLMConnectionError",
    "create_llm_dummy_classes",
    "handle_llm_import_error",
    # Exception handling utilities
    "handle_db_exceptions",
    "handle_db_errors",
    "handle_db_errors_decorator",
    "handle_http_errors",
    "validate_and_parse_timestamp",
    # Router utilities
    "handle_router_exceptions",
    "commit_and_refresh_db",
    # Constants utilities
    "ConstantsPlaceholder",
    "get_constants_module",
    # Data validation utilities
    "clamp01",
    "validate_timestamp",
    "validate_dict_timestamp",
    "get_category_from_thresholds",
    "is_valid_thresholds",
    "get_threshold_label",
    # Feature flags
    "is_enabled",
    "with_feature_flag",
]
