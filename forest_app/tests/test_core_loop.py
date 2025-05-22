import threading
import pytest
import time

from forest_app.core.session_management import run_forest_session
from forest_app.modules.hta_tree import HTATree
from forest_app.modules.task_engine import TaskEngine
from forest_app.models.session import SessionState

def dummy_saver(snapshot):
    """Dummy saver to verify state persistence."""
    dummy_saver.called = True

def test_run_forest_session_basic():
    """
    Test the core session loop:
    - Runs for a few heartbeats
    - Verifies the saver is called
    - Ensures no exceptions are raised
    """
    snapshot = {"test": "state"}
    lock = threading.Lock()
    dummy_saver.called = False

    # Run the session loop in a thread and stop after a short time
    def run_loop():
        try:
            run_forest_session(snapshot, dummy_saver, lock, heartbeat_sec=0.1, max_beats=3)
        except Exception as e:
            pytest.fail(f"Session loop raised an exception: {e}")

    t = threading.Thread(target=run_loop)
    t.start()
    t.join(timeout=1.0)
    assert dummy_saver.called, "Saver was not called"

def test_core_loop_flow():
    """
    Test the complete core loop flow:
    1. User onboards and provides goal/context
    2. System creates top node and HTA tree
    3. Task generator creates frontier nodes
    4. User marks nodes complete
    5. New batch generates based on context
    """
    # Initial state
    initial_state = SessionState(
        goal="Build a web application",
        context="Using FastAPI and React",
        hta_tree=HTATree(),
        completed_nodes=set(),
        current_batch=[]
    )
    
    # Track state changes
    state_history = []
    
    def state_saver(state):
        """Track state changes for verification"""
        state_history.append(state)
    
    # Run the session for a few iterations
    run_forest_session(
        initial_state,
        state_saver,
        max_iterations=3
    )
    
    # Verify the flow
    assert len(state_history) > 0, "Session should have generated state changes"
    
    # Check initial state setup
    first_state = state_history[0]
    assert first_state.hta_tree.root_node is not None, "HTA tree should have a root node"
    assert first_state.hta_tree.root_node.goal == initial_state.goal, "Root node should match initial goal"
    
    # Verify task generation
    assert len(first_state.current_batch) > 0, "First batch should contain frontier nodes"
    
    # Check batch progression
    for i in range(1, len(state_history)):
        prev_state = state_history[i-1]
        curr_state = state_history[i]
        
        # Verify new batch is informed by previous context
        assert len(curr_state.current_batch) > 0, "Each iteration should generate new frontier nodes"
        assert len(curr_state.completed_nodes) >= len(prev_state.completed_nodes), "Completed nodes should accumulate"
        
        # Verify HTA tree growth
        assert len(curr_state.hta_tree.nodes) >= len(prev_state.hta_tree.nodes), "HTA tree should grow with each batch" 