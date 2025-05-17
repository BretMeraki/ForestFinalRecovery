"""
Application Constants Module

This module centralizes all constant definitions used throughout the Forest application
to prevent duplication and ensure consistency. This includes API keys, status codes,
feature flags, and other application-wide values.

Usage:
    from forest_app.config.app_constants import API_KEYS, STATUS_CODES, etc.
"""

# ------------ API Response Keys ------------
# These keys are used in API responses for consistent structure
KEY_STATUS_CODE = "status_code"
KEY_ERROR = "error"
KEY_DETAIL = "detail"
KEY_DATA = "data"
KEY_ACCESS_TOKEN = "access_token"
KEY_ONBOARDING_STATUS = "onboarding_status"
KEY_USER_INFO_EMAIL = "email"
KEY_USER_INFO_ID = "id"
KEY_ERROR_MESSAGE = "error_message"
KEY_MESSAGES = "messages"
KEY_CURRENT_TASK = "current_task"
KEY_HTA_STATE = "hta_state"
KEY_PENDING_CONFIRMATION = "pending_confirmation"
KEY_MILESTONES = "milestones_achieved"

# ------------ Onboarding Status Values ------------
ONBOARDING_STATUS_NEEDS_GOAL = "needs_goal"
ONBOARDING_STATUS_NEEDS_CONTEXT = "needs_context"
ONBOARDING_STATUS_COMPLETED = "completed"

# ------------ User Settings ------------
MAX_CODENAME_LENGTH = 60
MIN_PASSWORD_LENGTH = 8

# ------------ Seed Status Values ------------
SEED_STATUS_ACTIVE = "active"
SEED_STATUS_COMPLETED = "completed"

# ------------ Theme Constants ------------
DEFAULT_RESONANCE_THEME = "neutral"

# ------------ Service Settings ------------
DEFAULT_TIMEOUT_SECONDS = 30
MAX_RETRIES = 3

# ------------ Feature Flags ------------
# Define feature flags here to keep them centralized
FEATURE_DISCOVERY_JOURNEY = "discovery_journey"
FEATURE_HTA_DYNAMIC_EXPANSION = "hta_dynamic_expansion"
FEATURE_EMOTIONAL_INTEGRITY = "emotional_integrity"
