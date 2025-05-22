"""
Forest OS Session Management

This module contains functions for managing Forest OS sessions:
1. `run_forest_session`: Blocking heartbeat loop for session management
2. `run_forest_session_async`: Async heartbeat loop for session management

Both functions handle:
- Regular state updates (withering, etc.)
- State persistence
- Error handling and graceful shutdown
"""

from __future__ import annotations

import asyncio
import logging
import threading
import time
from typing import Any, Callable, Dict, Optional

try:
    from forest_app.config.constants import ORCHESTRATOR_HEARTBEAT_SEC
except ImportError as e:
    logging.error("Failed to import ORCHESTRATOR_HEARTBEAT_SEC: %s", e)
    ORCHESTRATOR_HEARTBEAT_SEC = 30

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class SessionError(Exception):
    """Base exception for session management errors."""
    pass


class SessionStateError(SessionError):
    """Raised when there's an error with session state management."""
    pass


class SessionPersistenceError(SessionError):
    """Raised when there's an error persisting session state."""
    pass


def run_forest_session(
    snapshot: Dict[str, Any],
    save_snapshot: Callable[[Dict[str, Any]], None],
    lock: Optional[threading.Lock] = None,
) -> None:
    """
    Run a blocking Forest OS session with heartbeat management.

    Args:
        snapshot: Session snapshot to manage
        save_snapshot: Function to call when saving state
        lock: Optional thread lock for thread-safe operations

    Raises:
        SessionStateError: If there's an error managing session state
        SessionPersistenceError: If there's an error persisting session state
    """
    session_id = snapshot.get("user_id", "unknown")
    logger.info(
        "Starting blocking forest session for session=%s (interval=%s sec)",
        session_id,
        ORCHESTRATOR_HEARTBEAT_SEC,
    )

    try:
        while True:
            start_time = time.monotonic()
            try:
                if lock:
                    with lock:
                        save_snapshot(snapshot)
                else:
                    save_snapshot(snapshot)
            except Exception as tick_err:
                logger.exception(
                    "Error during heartbeat tick for session=%s: %s",
                    session_id,
                    tick_err,
                )
                raise SessionPersistenceError(
                    f"Failed to persist session state: {tick_err}"
                ) from tick_err

            elapsed = time.monotonic() - start_time
            sleep_duration = max(0.0, float(ORCHESTRATOR_HEARTBEAT_SEC) - float(elapsed))
            try:
                time.sleep(sleep_duration)
            except KeyboardInterrupt:
                raise
            except Exception as sleep_err:
                logger.error(
                    "Error during heartbeat sleep for session=%s: %s",
                    session_id,
                    sleep_err,
                    exc_info=True,
                )
                raise SessionStateError(
                    f"Error in session heartbeat: {sleep_err}"
                ) from sleep_err

    except KeyboardInterrupt:
        logger.info("KeyboardInterrupt received; stopping session=%s", session_id)
        try:
            save_snapshot(snapshot)
        except Exception as e:
            logger.error(
                "Error saving state at shutdown for session=%s: %s",
                session_id,
                e,
                exc_info=True,
            )
            raise SessionPersistenceError(
                f"Failed to save final state: {e}"
            ) from e
    finally:
        logger.info("Blocking forest session stopped for session=%s", session_id)


async def run_forest_session_async(
    snapshot: Dict[str, Any],
    save_snapshot: Callable[[Dict[str, Any]], None],
    lock: Optional[threading.Lock] = None,
) -> None:
    """
    Run an async Forest OS session with heartbeat management.

    Args:
        snapshot: Session snapshot to manage
        save_snapshot: Function to call when saving state
        lock: Optional thread lock for thread-safe operations

    Raises:
        SessionStateError: If there's an error managing session state
        SessionPersistenceError: If there's an error persisting session state
    """
    session_id = snapshot.get("user_id", "unknown")
    logger.info(
        "Starting async forest session for session=%s (interval=%s sec)",
        session_id,
        ORCHESTRATOR_HEARTBEAT_SEC,
    )

    try:
        while True:
            start_time = asyncio.get_running_loop().time()
            try:
                if lock:
                    with lock:
                        save_snapshot(snapshot)
                else:
                    save_snapshot(snapshot)
            except Exception as tick_err:
                logger.exception(
                    "Error during async heartbeat tick for session=%s: %s",
                    session_id,
                    tick_err,
                )
                raise SessionPersistenceError(
                    f"Failed to persist session state: {tick_err}"
                ) from tick_err

            elapsed = asyncio.get_running_loop().time() - start_time
            sleep_duration = max(0.0, float(ORCHESTRATOR_HEARTBEAT_SEC) - float(elapsed))
            try:
                await asyncio.sleep(sleep_duration)
            except asyncio.CancelledError:
                raise
            except Exception as sleep_err:
                logger.error(
                    "Error during async heartbeat sleep for session=%s: %s",
                    session_id,
                    sleep_err,
                    exc_info=True,
                )
                raise SessionStateError(
                    f"Error in session heartbeat: {sleep_err}"
                ) from sleep_err

    except asyncio.CancelledError:
        logger.info("Async session cancelled for session=%s", session_id)
        try:
            save_snapshot(snapshot)
        except Exception as e:
            logger.error(
                "Error saving state at cancellation for session=%s: %s",
                session_id,
                e,
                exc_info=True,
            )
            raise SessionPersistenceError(
                f"Failed to save final state: {e}"
            ) from e
    except Exception as e:
        logger.error(
            "Unhandled error in async session for session=%s: %s",
            session_id,
            e,
            exc_info=True,
        )
        raise SessionStateError(
            f"Unhandled session error: {e}"
        ) from e
    finally:
        logger.info("Async forest session stopped for session=%s", session_id) 