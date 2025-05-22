# forest_app/core/session_manager.py

"""
Manages per-user Forest sessions: state storage, heartbeat tasks, and concurrency.
"""

import asyncio
import logging
import threading
from typing import Any, Callable, Dict, Optional
from uuid import UUID

try:
    from forest_app.core.onboarding import onboard_user
    from forest_app.core.session_management import run_forest_session_async
except ImportError as e:
    logging.error(f"Failed to import onboard_user or run_forest_session_async: {e}")
    def onboard_user(snapshot, baselines, save_snapshot):
        return snapshot
    async def run_forest_session_async(snapshot, save_snapshot, lock):
        pass

logger = logging.getLogger(__name__)


class SessionInfo:
    """
    Holds the state and control primitives for a single user session.
    """

    def __init__(
        self,
        user_id: UUID,
        snapshot: Dict[str, Any],
        save_snapshot: Callable[[Dict[str, Any]], None],
        baselines: Dict[str, float],
    ):
        self.lock = threading.Lock()
        self.save_snapshot = save_snapshot
        self.user_id = user_id
        try:
            # Initialize and persist baselines; returns a new snapshot copy
            self.snapshot = onboard_user(snapshot, baselines, save_snapshot)
        except Exception as e:
            logger.error("Failed to onboard user '%s': %s", user_id, e, exc_info=True)
            raise
        self.task: Optional[asyncio.Task] = None


class SessionManager:
    """
    Singleton manager for all active user sessions.
    Provides safe access and control over per-user SessionInfo.
    """

    def __init__(self):
        self._sessions: Dict[UUID, SessionInfo] = {}

    def start_session(
        self,
        user_id: UUID,
        initial_snapshot: Dict[str, Any],
        baselines: Dict[str, float],
        save_snapshot: Callable[[Dict[str, Any]], None],
    ) -> None:
        """
        Launch an async heartbeat loop for the user.
        No-op if session already running.
        """
        if user_id in self._sessions:
            return
        info = SessionInfo(user_id, initial_snapshot, save_snapshot, baselines)
        info.task = asyncio.create_task(
            run_forest_session_async(info.snapshot, info.save_snapshot, info.lock)
        )
        self._sessions[user_id] = info
        logger.info("Started session for user '%s'", user_id)

    def stop_session(self, user_id: UUID) -> None:
        """
        Stop the heartbeat loop for the user and remove session.
        """
        info = self._sessions.pop(user_id, None)
        if info and info.task:
            info.task.cancel()
            logger.info("Stopped session for user '%s'", user_id)

    def stop_all_sessions(self) -> None:
        """
        Stop all active sessions for graceful shutdown.
        """
        for uid in list(self._sessions.keys()):
            self.stop_session(uid)

    def get_session_info(self, user_id: UUID) -> Optional[SessionInfo]:
        """
        Retrieve the SessionInfo object for a user.
        """
        return self._sessions.get(user_id)

    def get_session_lock(self, user_id: UUID) -> Optional[threading.Lock]:
        """
        Retrieve the threading.Lock for a user's session.
        """
        info = self.get_session_info(user_id)
        return info.lock if info else None

    def get_snapshot(self, user_id: UUID) -> Optional[Dict[str, Any]]:
        """
        Retrieve the live snapshot for a user. Use get_session_lock() to guard modifications.
        """
        info = self.get_session_info(user_id)
        return info.snapshot if info else None

    @classmethod
    def get_instance(cls):
        """Return the global singleton instance of SessionManager."""
        try:
            from forest_app.core.session_manager import session_manager
        except ImportError as e:
            logging.error(f"Failed to import session_manager: {e}")
            class DummySessionManager:
                pass
            return DummySessionManager()
        return session_manager


# Global session manager instance
session_manager = SessionManager()
