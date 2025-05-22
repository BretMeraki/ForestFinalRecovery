"""
Forest App Utilities Package

This package contains utility functions and helpers for use throughout the Forest App.
It includes utilities for loading baselines, LLM handling, error handling, data validation,
feature flags, and shared code patterns to reduce duplication across the codebase.
"""

# Standard library imports
import logging

# LLM fallbacks
from forest_app.utils.import_fallbacks import import_with_fallback

logger = logging.getLogger(__name__)

LLMClient = import_with_fallback(
    lambda: __import__('forest_app.integrations.llm_fallbacks', fromlist=['LLMClient']).LLMClient,
    lambda: type('LLMClient', (), {}),
    logger,
    "LLMClient"
)
LLMConfigurationError = import_with_fallback(
    lambda: __import__('forest_app.integrations.llm_fallbacks', fromlist=['LLMConfigurationError']).LLMConfigurationError,
    lambda: type('LLMConfigurationError', (Exception,), {}),
    logger,
    "LLMConfigurationError"
)
LLMConnectionError = import_with_fallback(
    lambda: __import__('forest_app.integrations.llm_fallbacks', fromlist=['LLMConnectionError']).LLMConnectionError,
    lambda: type('LLMConnectionError', (Exception,), {}),
    logger,
    "LLMConnectionError"
)
LLMError = import_with_fallback(
    lambda: __import__('forest_app.integrations.llm_fallbacks', fromlist=['LLMError']).LLMError,
    lambda: type('LLMError', (Exception,), {}),
    logger,
    "LLMError"
)
LLMValidationError = import_with_fallback(
    lambda: __import__('forest_app.integrations.llm_fallbacks', fromlist=['LLMValidationError']).LLMValidationError,
    lambda: type('LLMValidationError', (Exception,), {}),
    logger,
    "LLMValidationError"
)

# Local application imports
load_user_baselines = import_with_fallback(
    lambda: __import__('forest_app.utils.baseline_loader', fromlist=['load_user_baselines']).load_user_baselines,
    lambda: (lambda *a, **k: []),
    logger,
    "load_user_baselines"
)
ConstantsPlaceholder = import_with_fallback(
    lambda: __import__('forest_app.utils.constants_utils', fromlist=['ConstantsPlaceholder']).ConstantsPlaceholder,
    lambda: type('ConstantsPlaceholder', (), {}),
    logger,
    "ConstantsPlaceholder"
)
get_constants_module = import_with_fallback(
    lambda: __import__('forest_app.utils.constants_utils', fromlist=['get_constants_module']).get_constants_module,
    lambda: (lambda: ConstantsPlaceholder()),
    logger,
    "get_constants_module"
)
clamp01 = import_with_fallback(
    lambda: __import__('forest_app.utils.data_validation', fromlist=['clamp01']).clamp01,
    lambda: (lambda x, default=0.5: default),
    logger,
    "clamp01"
)
get_category_from_thresholds = import_with_fallback(
    lambda: __import__('forest_app.utils.data_validation', fromlist=['get_category_from_thresholds']).get_category_from_thresholds,
    lambda: (lambda *a, **k: "Unknown"),
    logger,
    "get_category_from_thresholds"
)
validate_dict_timestamp = import_with_fallback(
    lambda: __import__('forest_app.utils.data_validation', fromlist=['validate_dict_timestamp']).validate_dict_timestamp,
    lambda: (lambda *a, **k: False),
    logger,
    "validate_dict_timestamp"
)
validate_timestamp = import_with_fallback(
    lambda: __import__('forest_app.utils.data_validation', fromlist=['validate_timestamp']).validate_timestamp,
    lambda: (lambda *a, **k: False),
    logger,
    "validate_timestamp"
)
handle_db_errors_decorator = import_with_fallback(
    lambda: __import__('forest_app.utils.error_handling', fromlist=['handle_db_errors']).handle_db_errors,
    lambda: (lambda *a, **k: None),
    logger,
    "handle_db_errors_decorator"
)
handle_http_errors = import_with_fallback(
    lambda: __import__('forest_app.utils.error_handling', fromlist=['handle_http_errors']).handle_http_errors,
    lambda: (lambda *a, **k: None),
    logger,
    "handle_http_errors"
)
validate_and_parse_timestamp = import_with_fallback(
    lambda: __import__('forest_app.utils.error_handling', fromlist=['validate_and_parse_timestamp']).validate_and_parse_timestamp,
    lambda: (lambda *a, **k: None),
    logger,
    "validate_and_parse_timestamp"
)
handle_db_errors = import_with_fallback(
    lambda: __import__('forest_app.utils.exception_handlers', fromlist=['handle_db_errors']).handle_db_errors,
    lambda: (lambda *a, **k: None),
    logger,
    "handle_db_errors"
)
handle_db_exceptions = import_with_fallback(
    lambda: __import__('forest_app.utils.exception_handlers', fromlist=['handle_db_exceptions']).handle_db_exceptions,
    lambda: (lambda *a, **k: None),
    logger,
    "handle_db_exceptions"
)
is_enabled = import_with_fallback(
    lambda: __import__('forest_app.utils.feature_flags', fromlist=['is_enabled']).is_enabled,
    lambda: (lambda *a, **k: False),
    logger,
    "is_enabled"
)
with_feature_flag = import_with_fallback(
    lambda: __import__('forest_app.utils.feature_flags', fromlist=['with_feature_flag']).with_feature_flag,
    lambda: (lambda *a, **k: (lambda func: func)),
    logger,
    "with_feature_flag"
)
create_llm_dummy_classes = import_with_fallback(
    lambda: __import__('forest_app.utils.llm_utils', fromlist=['create_llm_dummy_classes']).create_llm_dummy_classes,
    lambda: (lambda: (LLMClient, LLMError, LLMValidationError, LLMConfigurationError, LLMConnectionError)),
    logger,
    "create_llm_dummy_classes"
)
handle_llm_import_error = import_with_fallback(
    lambda: __import__('forest_app.utils.llm_utils', fromlist=['handle_llm_import_error']).handle_llm_import_error,
    lambda: (lambda error: (False,) + create_llm_dummy_classes()),
    logger,
    "handle_llm_import_error"
)
commit_and_refresh_db = import_with_fallback(
    lambda: __import__('forest_app.utils.router_helpers', fromlist=['commit_and_refresh_db']).commit_and_refresh_db,
    lambda: (lambda *a, **k: None),
    logger,
    "commit_and_refresh_db"
)
handle_router_exceptions = import_with_fallback(
    lambda: __import__('forest_app.utils.router_helpers', fromlist=['handle_router_exceptions']).handle_router_exceptions,
    lambda: (lambda *a, **k: (lambda func: func)),
    logger,
    "handle_router_exceptions"
)
get_threshold_label = import_with_fallback(
    lambda: __import__('forest_app.utils.validation', fromlist=['get_threshold_label']).get_threshold_label,
    lambda: (lambda *a, **k: "Unknown"),
    logger,
    "get_threshold_label"
)
is_valid_thresholds = import_with_fallback(
    lambda: __import__('forest_app.utils.validation', fromlist=['is_valid_thresholds']).is_valid_thresholds,
    lambda: (lambda *a, **k: False),
    logger,
    "is_valid_thresholds"
)

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
