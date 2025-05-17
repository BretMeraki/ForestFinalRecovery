"""
Import verification script for Forest App.
Ensures all critical imports are available and working.
"""

import importlib
import logging
import sys
from typing import Any, Dict, List, Tuple

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


def test_import(module_path: str) -> Tuple[bool, str]:
    """Test if a module can be imported."""
    try:
        importlib.import_module(module_path)
        return True, "Success"
    except ImportError as e:
        return False, str(e)
    except Exception as e:
        return False, f"Unexpected error: {str(e)}"


def verify_imports() -> Dict[str, List[Dict[str, Any]]]:
    """Verify all critical imports for the Forest App."""
    results = {"success": [], "failure": []}

    # Core imports
    core_modules = [
        "forest_app.core.snapshot",
        "forest_app.core.utils",
        "forest_app.core.processors",
        "forest_app.core.services",
        "forest_app.core.feature_flags",
        "forest_app.core.harmonic_framework",
        "forest_app.core.orchestrator",
    ]

    # Module imports
    module_imports = [
        "forest_app.modules.seed",
        "forest_app.modules.logging_tracking",
        "forest_app.modules.soft_deadline_manager",
        "forest_app.modules.types",
        "forest_app.modules.sentiment",
        "forest_app.modules.pattern_id",
        "forest_app.modules.practical_consequence",
        "forest_app.modules.metrics_specific",
        "forest_app.modules.relational",
        "forest_app.modules.narrative_modes",
        "forest_app.modules.offering_reward",
        "forest_app.modules.xp_mastery",
        "forest_app.modules.emotional_integrity",
        "forest_app.modules.task_engine",
        "forest_app.modules.snapshot_flow",
        "forest_app.modules.desire_engine",
        "forest_app.modules.financial_readiness",
    ]

    # Integration imports
    integration_imports = ["forest_app.integrations.llm"]

    # Config imports
    config_imports = ["forest_app.config.settings", "forest_app.config.constants"]

    # Test all imports
    all_imports = {
        "Core": core_modules,
        "Modules": module_imports,
        "Integrations": integration_imports,
        "Config": config_imports,
    }

    for category, modules in all_imports.items():
        logger.info("\nTesting %s imports...", category)
        for module in modules:
            success, message = test_import(module)
            result = {"module": module, "category": category, "message": message}
            if success:
                results["success"].append(result)
                logger.info("✓ %s", module)
            else:
                results["failure"].append(result)
                logger.error("✗ %s: %s", module, message)

    return results


def verify_protocol_implementations():
    """Verify that all Protocol implementations match their interfaces."""
    from forest_app.containers import DummySemanticMemoryManager
    from forest_app.core.services.semantic_memory import SemanticMemoryManager
    from forest_app.modules.types import SemanticMemoryProtocol

    logger.info("\nVerifying Protocol implementations...")

    # Get all required methods from the Protocol
    protocol_methods = [
        method for method in dir(SemanticMemoryProtocol) if not method.startswith("_")
    ]

    # Check SemanticMemoryManager
    logger.info("\nChecking SemanticMemoryManager implementation:")
    for method in protocol_methods:
        if hasattr(SemanticMemoryManager, method):
            logger.info("✓ %s", method)
        else:
            logger.error("✗ Missing method: %s", method)

    # Check DummySemanticMemoryManager
    logger.info("\nChecking DummySemanticMemoryManager implementation:")
    for method in protocol_methods:
        if hasattr(DummySemanticMemoryManager, method):
            logger.info("✓ %s", method)
        else:
            logger.error("✗ Missing method: %s", method)


def main():
    """Main entry point for import verification."""
    logger.info("Starting import verification...")

    # Test all imports
    results = verify_imports()

    # Verify Protocol implementations
    verify_protocol_implementations()

    # Summary
    total_imports = len(results["success"]) + len(results["failure"])
    success_rate = (len(results["success"]) / total_imports) * 100

    logger.info("\nImport Verification Summary:")
    logger.info("Total imports tested: %s", total_imports)
    logger.info("Successful imports: %s", len(results["success"]))
    logger.info("Failed imports: %s", len(results["failure"]))
    logger.info("Success rate: %.1f%%", success_rate)

    if results["failure"]:
        logger.error("\nFailed imports:")
        for failure in results["failure"]:
            logger.error(
                "%s - %s: %s",
                failure["category"],
                failure["module"],
                failure["message"],
            )
        sys.exit(1)
    else:
        logger.info("\nAll imports successful!")
        sys.exit(0)


if __name__ == "__main__":
    main()
