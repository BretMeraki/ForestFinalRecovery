# front_end/onboarding_ui.py
import logging
from typing import Callable, Optional

import streamlit as st

# Import constants from the central app_constants module
from forest_app.config.app_constants import (
    KEY_CURRENT_TASK,
    KEY_DATA,
    KEY_ERROR,
    KEY_ERROR_MESSAGE,
    KEY_MESSAGES,
    KEY_ONBOARDING_STATUS,
    KEY_PENDING_CONFIRMATION,
    KEY_STATUS_CODE,
    MIN_PASSWORD_LENGTH,
    ONBOARDING_STATUS_COMPLETED,
    ONBOARDING_STATUS_NEEDS_CONTEXT,
    ONBOARDING_STATUS_NEEDS_GOAL,
)

# Update relative import to absolute
from forest_app.front_end.api_client import call_forest_api


# Create a constants class for backward compatibility with existing code
class constants:
    """Constants class for backward compatibility.

    Note: New code should import directly from forest_app.config.app_constants
    """

    ONBOARDING_STATUS_NEEDS_GOAL = ONBOARDING_STATUS_NEEDS_GOAL
    ONBOARDING_STATUS_NEEDS_CONTEXT = ONBOARDING_STATUS_NEEDS_CONTEXT
    ONBOARDING_STATUS_COMPLETED = ONBOARDING_STATUS_COMPLETED
    MIN_PASSWORD_LENGTH = MIN_PASSWORD_LENGTH


logger = logging.getLogger(__name__)

# --- Internal Handler Functions (modified from streamlit_app.py) ---


def _handle_set_goal(goal_text: str, backend_url: str) -> bool:
    """Handles goal submission during the 'needs_goal' onboarding phase. Returns True on success."""
    st.session_state[KEY_ERROR_MESSAGE] = None  # Clear previous errors
    logger.info("Submitting goal during onboarding...")

    if not isinstance(st.session_state.get(KEY_MESSAGES), list):
        st.session_state[KEY_MESSAGES] = []
    st.session_state.messages.append({"role": "user", "content": goal_text})
    # Display immediately in the main app's chat history area (caller handles this)

    with st.chat_message("assistant"):  # Show thinking message here
        message_placeholder = st.empty()
        message_placeholder.markdown("🎯 Setting your goal...")
        response = call_forest_api(
            "/onboarding/set_goal",
            method="POST",
            data={"goal_description": goal_text},
            backend_url=backend_url,
            api_token=st.session_state.get("token"),
        )

        if response.get(KEY_ERROR):
            error_msg = response.get(KEY_ERROR, "Unknown error")
            logger.error(f"API Fail set_goal: {error_msg}")
            message_placeholder.error(f"Error: {error_msg}")
            st.session_state[KEY_ERROR_MESSAGE] = f"API Error: {error_msg}"
            return False  # Indicate failure
        elif response.get(KEY_STATUS_CODE) == 200:
            logger.info("Goal set via API.")
            resp_data = response.get(KEY_DATA, {})
            new_status = resp_data.get(
                KEY_ONBOARDING_STATUS, constants.ONBOARDING_STATUS_NEEDS_CONTEXT
            )
            # Update state
            st.session_state[KEY_ONBOARDING_STATUS] = new_status
            assistant_response = resp_data.get("message", "Goal set! Provide context?")
            message_placeholder.markdown(assistant_response)  # Show response
            st.session_state.messages.append(
                {"role": "assistant", "content": assistant_response}
            )  # Add to history
            return True  # Indicate success
        else:
            status_code = response.get(KEY_STATUS_CODE, "N/A")
            logger.error(f"Unexpected status {status_code} set_goal.")
            message_placeholder.error(f"Unexpected error (Status: {status_code}).")
            st.session_state[KEY_ERROR_MESSAGE] = f"API Error: Status {status_code}"
            return False  # Indicate failure


def _handle_add_context(
    context_text: str, backend_url: str, fetch_hta_state_func: Callable[[], None]
) -> bool:
    """Handles context submission. Returns True on success."""
    st.session_state[KEY_ERROR_MESSAGE] = None
    logger.info("Submitting context during onboarding...")

    if not isinstance(st.session_state.get(KEY_MESSAGES), list):
        st.session_state[KEY_MESSAGES] = []
    st.session_state.messages.append({"role": "user", "content": context_text})
    # Display immediately in the main app's chat history area (caller handles this)

    with st.chat_message("assistant"):  # Show thinking message here
        message_placeholder = st.empty()
        message_placeholder.markdown("📝 Adding context...")
        response = call_forest_api(
            "/onboarding/add_context",
            method="POST",
            data={"context_reflection": context_text},
            backend_url=backend_url,
            api_token=st.session_state.get("token"),
        )

        if response.get(KEY_ERROR):
            error_msg = response.get(KEY_ERROR, "Unknown error")
            logger.error(f"API Fail add_context: {error_msg}")
            message_placeholder.error(f"Error: {error_msg}")
            st.session_state[KEY_ERROR_MESSAGE] = f"API Error: {error_msg}"
            return False
        elif response.get(KEY_STATUS_CODE) == 200:
            logger.info("Context added via API.")
            resp_data = response.get(KEY_DATA, {})
            new_status = resp_data.get(
                KEY_ONBOARDING_STATUS, constants.ONBOARDING_STATUS_COMPLETED
            )
            # Update state
            st.session_state[KEY_ONBOARDING_STATUS] = new_status
            assistant_response = resp_data.get("message", "Context added!")
            message_placeholder.markdown(assistant_response)
            st.session_state.messages.append(
                {"role": "assistant", "content": assistant_response}
            )
            # --- Fetch HTA state using the passed function ---
            fetch_hta_state_func()
            # Update current task state
            new_task = resp_data.get("task", resp_data.get("first_task"))
            st.session_state[KEY_CURRENT_TASK] = (
                new_task if isinstance(new_task, dict) else None
            )
            return True  # Indicate success
        else:
            status_code = response.get(KEY_STATUS_CODE, "N/A")
            logger.error(f"Unexpected status {status_code} add_context.")
            message_placeholder.error(f"Unexpected error (Status: {status_code}).")
            st.session_state[KEY_ERROR_MESSAGE] = f"API Error: Status {status_code}"
            return False


# --- Main Function to Display Onboarding Input ---


def display_onboarding_input(
    current_status: Optional[str],
    backend_url: str,
    fetch_hta_state_func: Callable[[], None],
) -> bool:
    """
    Displays the correct chat input and handles submission during onboarding.

    Args:
        current_status (Optional[str]): The user's current onboarding status.
        backend_url (str): The base URL for the backend API.
        fetch_hta_state_func (Callable): Function to call to refresh HTA state.

    Returns:
        bool: True if an onboarding action was successfully processed (requires rerun), False otherwise.
    """
    action_processed = False
    chat_disabled = (
        st.session_state.get(KEY_PENDING_CONFIRMATION) is not None
    )  # Check if confirmation pending

    if current_status == constants.ONBOARDING_STATUS_NEEDS_GOAL:
        st.info(
            "Let's start by defining your primary goal or intention for using Forest OS."
        )
        input_placeholder = "Enter your main goal here..."
        goal_prompt = st.chat_input(
            input_placeholder, key="goal_input", disabled=chat_disabled
        )
        if goal_prompt:
            # Display user message immediately (handled by main app loop)
            # Call handler
            if _handle_set_goal(goal_prompt, backend_url):
                action_processed = True

    elif current_status == constants.ONBOARDING_STATUS_NEEDS_CONTEXT:
        st.info(
            "Great! Now, provide some context about your goal. What's the background? What resources do you have? Any constraints?"
        )
        input_placeholder = "Add context for your goal..."
        context_prompt = st.chat_input(
            input_placeholder, key="context_input", disabled=chat_disabled
        )
        if context_prompt:
            # Display user message immediately (handled by main app loop)
            # Call handler
            if _handle_add_context(context_prompt, backend_url, fetch_hta_state_func):
                action_processed = True

    # Returns True if _handle_set_goal or _handle_add_context returned True
    return action_processed
