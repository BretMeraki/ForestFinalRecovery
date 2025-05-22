# forest_app/core/onboarding.py

"""
Forest OS Onboarding and Session‑Management

This module contains:
  1. `onboard_user`: one‑time initialization of a JSON snapshot
     with NLP‑derived baselines (deep‑copy + persist).
  2. `run_onboarding`: CLI flow to capture a top‑level goal (Seed),
     target date, journey path, reflection, and baseline assessment.
"""

from __future__ import annotations

import asyncio
import copy
import logging
import sys
import threading
import time
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from forest_app.core.orchestrator import ForestOrchestrator

try:
    from forest_app.config.constants import ORCHESTRATOR_HEARTBEAT_SEC
except ImportError as e:
    logging.error(f"Failed to import ORCHESTRATOR_HEARTBEAT_SEC: {e}")
    ORCHESTRATOR_HEARTBEAT_SEC = 30

try:
    from forest_app.core.snapshot import MemorySnapshot
except ImportError as e:
    logging.error(f"Failed to import MemorySnapshot: {e}")
    class MemorySnapshot:
        pass

try:
    from forest_app.modules.baseline_assessment import BaselineAssessmentEngine
except ImportError as e:
    logging.error(f"Failed to import BaselineAssessmentEngine: {e}")
    class BaselineAssessmentEngine:
        def __init__(self):
            pass
        def assess(self, *args, **kwargs):
            return {}

try:
    from forest_app.modules.seed import SeedManager
except ImportError as e:
    logging.error(f"Failed to import SeedManager: {e}")
    class SeedManager:
        def plant_seed(self, *args, **kwargs):
            class DummySeed:
                hta_tree = {"child_count": 1}
            return DummySeed()
        def to_dict(self):
            return {}

try:
    from forest_app.utils.baseline_loader import load_user_baselines
except ImportError as e:
    logging.error(f"Failed to import load_user_baselines: {e}")
    def load_user_baselines(snapshot):
        return snapshot

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


# -----------------------------------------------------------------------------
# 1. One‑time, programmatic baseline injection
# -----------------------------------------------------------------------------


def onboard_user(
    snapshot: Dict[str, Any],
    baselines: Dict[str, float],
    save_snapshot: Callable[[Dict[str, Any]], None],
) -> Dict[str, Any]:
    """
    One-time initialization of the user snapshot from NLP-derived baselines.

    - Deep-copies the incoming snapshot to avoid mutating shared state.
    - Injects and validates baseline metrics into component_state.
    - Persists the resulting snapshot as the session's starting state.

    Call this exactly once at session start, before any reflections or task processing.
    """
    new_snapshot = copy.deepcopy(snapshot)
    cs = new_snapshot.setdefault("component_state", {})
    cs["baselines"] = baselines

    # Validate and populate baselines (may raise on invalid data)
    new_snapshot = load_user_baselines(new_snapshot)

    try:
        save_snapshot(new_snapshot)
        logger.info("Initial snapshot persisted during onboarding.")
    except Exception as e:
        logger.error("Failed to save snapshot during onboarding: %s", e, exc_info=True)
        raise

    return new_snapshot


# -----------------------------------------------------------------------------
# 2. CLI‑driven HTA seed onboarding flow
# -----------------------------------------------------------------------------


def _prompt(text: str) -> str:
    sys.stdout.write(f"{text.strip()}\n> ")
    sys.stdout.flush()
    return sys.stdin.readline().strip()


def _parse_date_iso(date_str: str) -> Optional[str]:
    try:
        dt = datetime.fromisoformat(date_str.strip())
        return dt.date().isoformat()
    except ValueError:
        return None


def _recommend_completion_date(hta_scope: int) -> str:
    days = max(hta_scope, 1) * 2
    return (datetime.utcnow() + timedelta(days=days)).date().isoformat()


def run_onboarding(snapshot: MemorySnapshot) -> None:
    """
    Run the entire CLI onboarding flow and mutate `snapshot` in place.

    Steps:
      0. Capture a top-level goal (Seed) & domain
      1. Ask or recommend a completion date
      2. Choose journey path (structured/blended/open)
      3. Collect a "Where are you now?" reflection
      4. Run baseline assessment and seed the FullDevelopmentIndex
    """
    try:
        # 0. Seed details
        goal_title = _prompt(
            "What is the primary goal you wish to cultivate? "
            "(e.g. 'Run a 5k', 'Launch my blog')"
        )
        seed_domain = _prompt(
            "In one word, which life domain does this goal belong to? "
            "(e.g. health, career, creativity)"
        )
    except (EOFError, KeyboardInterrupt) as e:
        logger.error(
            "Onboarding interrupted during initial prompts: %s", e, exc_info=True
        )
        sys.exit(1)

    seed_manager = SeedManager()
    seed = seed_manager.plant_seed(goal_title, seed_domain, additional_context=None)
    snapshot.component_state["seed_manager"] = seed_manager.to_dict()

    # Estimate HTA scope for date recommendation
    try:
        tree = getattr(seed, "hta_tree", None)
        if hasattr(tree, "child_count"):
            hta_scope = tree.child_count
        else:
            hta_scope = tree.get("root", {}).get("child_count", 1)
    except Exception:
        hta_scope = 1

    # 1. Completion date
    while True:
        try:
            date_input = _prompt(
                "Enter your target completion date for this goal (YYYY‑MM‑DD) "
                "or type 'recommend' to let the forest suggest one:"
            )
        except (EOFError, KeyboardInterrupt) as e:
            logger.error(
                "Onboarding interrupted during date prompt: %s", e, exc_info=True
            )
            sys.exit(1)

        if date_input.lower() == "recommend":
            date_iso = _recommend_completion_date(hta_scope)
            print(f"\n🌲 The forest recommends {date_iso} as a gentle target.\n")
            break

        date_iso = _parse_date_iso(date_input)
        if date_iso:
            break

        print("\n❌ Invalid date format. Please use YYYY‑MM‑DD.\n")

    # 2. Journey path
    while True:
        try:
            path = _prompt(
                "Choose your journey path:\n"
                "1. Structured (guided, step‑by‑step)\n"
                "2. Blended (mix of guidance and freedom)\n"
                "3. Open (complete freedom, minimal guidance)\n"
                "Enter 1, 2, or 3:"
            )
        except (EOFError, KeyboardInterrupt) as e:
            logger.error(
                "Onboarding interrupted during path prompt: %s", e, exc_info=True
            )
            sys.exit(1)

        if path in ["1", "2", "3"]:
            break

        print("\n❌ Please enter 1, 2, or 3.\n")

    # 3. Reflection
    try:
        reflection = _prompt(
            "\nTake a moment to reflect on where you are now with this goal.\n"
            "What's your current state, challenges, and hopes?\n"
        )
    except (EOFError, KeyboardInterrupt) as e:
        logger.error(
            "Onboarding interrupted during reflection prompt: %s", e, exc_info=True
        )
        sys.exit(1)

    # 4. Baseline assessment
    assessment_engine = BaselineAssessmentEngine()
    baselines = assessment_engine.assess(reflection)

    # Update snapshot with onboarding data
    snapshot.component_state.update(
        {
            "goal": {
                "title": goal_title,
                "domain": seed_domain,
                "target_date": date_iso,
                "path": ["structured", "blended", "open"][int(path) - 1],
            },
            "reflection": reflection,
            "baselines": baselines,
        }
    )

    logger.info("Onboarding completed successfully.")
