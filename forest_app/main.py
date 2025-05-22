# forest_app/main.py (MODIFIED: DI Wiring moved before router inclusion)

import logging
import os
import sys
from typing import Any  # Added Any

import sentry_sdk
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sentry_sdk.integrations.logging import LoggingIntegration
from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration

try:
    from forest_app.api import routers as api_routers
except ImportError as e:
    logging.error(f"Failed to import api.routers: {e}")
    api_routers = None

try:
    from forest_app.containers import ContainerManager
    CONTAINER = ContainerManager.get_instance()
except ImportError as e:
    logging.error(f"Failed to import CONTAINER from containers: {e}")
    CONTAINER = None

try:
    from forest_app.core.initialize_architecture import inject_enhanced_architecture
except ImportError as e:
    logging.error(f"Failed to import inject_enhanced_architecture: {e}")
    def inject_enhanced_architecture(app):
        pass

try:
    from forest_app.core.integrations.discovery_integration import setup_discovery_journey
except ImportError as e:
    logging.error(f"Failed to import setup_discovery_journey: {e}")
    def setup_discovery_journey(*args, **kwargs):
        pass

try:
    from forest_app.core.security import initialize_security_dependencies
except ImportError as e:
    logging.error(f"Failed to import initialize_security_dependencies: {e}")
    def initialize_security_dependencies(*args, **kwargs):
        pass

try:
    from forest_app.middleware.logging import LoggingMiddleware
except ImportError as e:
    logging.error(f"Failed to import LoggingMiddleware: {e}")
    class LoggingMiddleware:
        pass

try:
    from forest_app.persistence.database import init_db
except ImportError as e:
    logging.error(f"Failed to import init_db: {e}")
    def init_db(*args, **kwargs):
        pass

try:
    from forest_app.persistence.models import UserModel
except ImportError as e:
    logging.error(f"Failed to import UserModel: {e}")
    class UserModel:
        __annotations__ = {"email": str}

try:
    from forest_app.persistence.repository import get_user_by_email
except ImportError as e:
    logging.error(f"Failed to import get_user_by_email: {e}")
    def get_user_by_email(*args, **kwargs):
        return None

try:
    from forest_app.routers import (
        auth,
        core,
        goals,
        hta,
        onboarding,
        snapshots,
        trees,
        users,
    )
except ImportError as e:
    logging.error(f"Failed to import routers: {e}")
    auth = core = goals = hta = onboarding = snapshots = trees = users = None

try:
    from forest_app.api.routers import discovery_journey
except ImportError as e:
    logging.error(f"Failed to import discovery_journey router: {e}")
    # Create a dummy router to prevent startup errors
    from fastapi import APIRouter
    class DummyDiscoveryJourney:
        router = APIRouter()
    discovery_journey = DummyDiscoveryJourney()

# --- Explicitly add /app to sys.path ---
# This helps resolve module imports in some deployment environments
APP_ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if APP_ROOT_DIR not in sys.path:
    sys.path.insert(0, APP_ROOT_DIR)
    sys.path.insert(0, os.path.join(APP_ROOT_DIR, "forest_app"))
# --- End sys.path modification ---


# --- Sentry Integration Imports ---

# --- FastAPI Imports ---

# --- Core, Persistence & Feature Flag Imports ---
# Keep necessary imports for init_db, security, models etc.
# from forest_app.modules.trigger_phrase import TriggerPhraseHandler # Likely not needed globally now

# --- Import Feature Flags and Checker ---
try:
    from forest_app.core.feature_flags import Feature, is_enabled

    feature_flags_available = True
except ImportError as ff_import_err:
    # Log this potential error early after basic logging is configured
    logging.getLogger("main_init").error(
        "Failed to import Feature Flags components: %s", ff_import_err
    )
    feature_flags_available = False

    # Define dummies if needed for code structure, though checks later should handle it
    class Feature:
        pass

    def is_enabled(feature: Any) -> bool:
        return False


# --- Use Absolute Import for Container CLASS and INSTANCE --- ### MODIFIED ###

# --- Enhanced Architecture Components ---

# Initialize container
container = CONTAINER

# Import the new discovery journey router from api/routers

# --- Router Imports ---
# Keep these here as they might rely on container/models

# --------------------------------------------------------------------------
# Logging Setup
# --------------------------------------------------------------------------
log_handler = logging.StreamHandler(sys.stdout)
log_format_string = '{"timestamp": "%(asctime)s", "level": "%(levelname)s", "name": "%(name)s", "message": "%(message)s"}'
# Use datefmt for ISO8601 format in logs
date_format = "%Y-%m-%dT%H:%M:%S%z"  # Example ISO 8601 format

# Configure root logger
logging.basicConfig(
    level=logging.DEBUG,  # Keep DEBUG to capture all levels for now
    format=log_format_string,
    datefmt=date_format,
    handlers=[log_handler],
    force=True,  # Force override if already configured elsewhere
)
logger = logging.getLogger(__name__)  # Get logger for this module

# Log path modification confirmation now that logging is configured
if APP_ROOT_DIR not in sys.path:  # Check condition again (should be false now)
    pass  # Already added
else:
    logger.warning("--- Path %s was already in sys.path or added. ---", APP_ROOT_DIR)

logger.info("----- Forest OS API Starting Up (DI Enabled) -----")

# --- DEBUG LOGGING LINES ---
try:
    logger.debug("--- DEBUG: Current Working Directory: %s", os.getcwd())
    logger.debug("--- DEBUG: Python Path (post-modification): %s", sys.path)
except Exception as debug_e:
    logger.error("--- DEBUG: Failed to get CWD or sys.path: %s", debug_e)
# --- END DEBUG LOGGING LINES ---


# --------------------------------------------------------------------------
# Sentry Integration
# --------------------------------------------------------------------------
SENTRY_DSN = os.getenv("SENTRY_DSN")
if SENTRY_DSN:
    try:
        sentry_logging = LoggingIntegration(
            level=logging.INFO,  # Capture info and above as breadcrumbs
            event_level=logging.ERROR,  # Send errors as events (or WARNING)
        )
        sentry_sdk.init(
            dsn=SENTRY_DSN,
            traces_sample_rate=float(
                os.getenv("SENTRY_TRACES_SAMPLE_RATE", "0.1")
            ),  # Sample fewer traces usually
            profiles_sample_rate=float(os.getenv("SENTRY_PROFILES_SAMPLE_RATE", "0.1")),
            integrations=[
                SqlalchemyIntegration(),
                sentry_logging,
            ],  # Use configured logging integration
            environment=os.getenv("APP_ENV", "development"),
            release=os.getenv(
                "APP_RELEASE_VERSION", "unknown"
            ),  # Provide a default release
        )
        logger.info("Sentry SDK initialized successfully.")
    except Exception as sentry_init_e:
        logger.exception("Failed to initialize Sentry SDK: %s", sentry_init_e)
else:
    logger.warning(
        "SENTRY_DSN environment variable not found. Sentry integration skipped."
    )

# --------------------------------------------------------------------------
# Database Initialization
# --------------------------------------------------------------------------
try:
    logger.info("Attempting to initialize database tables via init_db()...")
    init_db()
    logger.info("Database initialization check complete.")
except Exception as db_init_e:
    logger.exception("CRITICAL Error during database initialization: %s", db_init_e)
    sys.exit("CRITICAL: Database initialization failed: %s", db_init_e)

# --------------------------------------------------------------------------
# Security Dependency Initialization
# --------------------------------------------------------------------------
logger.info("Initializing security dependencies...")
try:
    # Basic check if UserModel seems valid (has an email annotation)
    if (
        not hasattr(UserModel, "__annotations__")
        or "email" not in UserModel.__annotations__
    ):
        logger.critical(
            "UserModel may be incomplete or a dummy class. Security init might fail."
        )
    initialize_security_dependencies(get_user_by_email, UserModel)
    logger.info("Security dependencies initialized successfully.")
except TypeError as sec_init_err:
    logger.exception(
        "CRITICAL: Failed security init - check function signature in core.security: %s",
        sec_init_err,
    )
    sys.exit(
        "CRITICAL: Security dependency initialization failed (TypeError): %s",
        sec_init_err,
    )
except Exception as sec_init_gen_err:
    logger.exception(
        "CRITICAL: Unexpected error during security init: %s", sec_init_gen_err
    )
    sys.exit(
        "CRITICAL: Security dependency initialization failed unexpectedly: %s",
        sec_init_gen_err,
    )


# --------------------------------------------------------------------------
# --- DI Container Setup (Instance created on import) --- ### COMMENT UPDATED ###
# --------------------------------------------------------------------------
# Container instance is created when 'from forest_app.containers import container' runs
if not container:  # Basic check
    logger.warning("WARNING: DI Container instance is None - using simplified mode for MVP.")
    container = type('DummyContainer', (), {})()  # Create a dummy container for now
else:
    logger.info("DI Container instance imported successfully.")


# --------------------------------------------------------------------------
# FastAPI Application Instance Creation
# --------------------------------------------------------------------------
logger.info("Creating FastAPI application instance...")
app = FastAPI(
    title="Forest OS API",
    version="1.23",
    description="API for interacting with the Forest OS personal growth assistant.",
)

# --- Store container on app.state ---
app.state.container = container
logger.info("DI Container instance stored in app.state.")

# --- Initialize Enhanced Architecture ---
logger.info("Initializing enhanced scalable architecture components...")
inject_enhanced_architecture(app)

# --- Initialize Discovery Journey Module ---
logger.info("Initializing Journey of Discovery module...")
setup_discovery_journey(app)

# --------------------------------------------------------------------------
# **** DI Container Wiring (MOVED HERE - BEFORE ROUTERS) ****
# --------------------------------------------------------------------------
try:
    logger.info("Wiring Dependency Injection container...")
    # Use the imported container instance directly
    if hasattr(container, 'wire'):
        container.wire(
            modules=[
                __name__,  # Wire this main module if using @inject here
                "forest_app.routers.auth",
                "forest_app.routers.users", 
                "forest_app.routers.onboarding",
                "forest_app.routers.hta",
                "forest_app.routers.snapshots",
                "forest_app.routers.core",
                "forest_app.routers.goals",
                "forest_app.core.orchestrator",  # Add other modules using DI if needed
                "forest_app.helpers",
            ]
        )
        logger.info("Dependency Injection container wired successfully.")
    else:
        logger.warning("Container doesn't support wiring - running in simplified mode.")
except Exception as e:
    logger.warning("DI Container wiring failed - continuing in simplified mode: %s", e)
    # Don't exit, just continue without DI


# --------------------------------------------------------------------------
# Include Routers
# --------------------------------------------------------------------------
logger.info("Including API routers...")
routers_to_include = [
    (auth, "/auth", "Authentication"),
    (users, "/users", "Users"),
    (onboarding, "/onboarding", "Onboarding"),
    (hta, "/hta", "HTA"),
    (snapshots, "/snapshots", "Snapshots"),
    (core, "/core", "Core"),
    (goals, "/goals", "Goals"),
    (trees, "/trees", "Trees"),
    (discovery_journey, "", "Discovery Journey"),
]

for router_module, prefix, tag in routers_to_include:
    try:
        if router_module and hasattr(router_module, 'router'):
            app.include_router(router_module.router, prefix=prefix, tags=[tag])
            logger.info("Included %s router successfully.", tag)
        else:
            logger.warning("Skipping %s router - module not available.", tag)
    except Exception as router_err:
        logger.warning("Failed to include %s router: %s", tag, router_err)
        # Continue with other routers instead of exiting

logger.info("Router inclusion process completed.")


# --------------------------------------------------------------------------
# Middleware Configuration
# --------------------------------------------------------------------------
logger.info("Configuring middleware (CORS)...")
origins = [
    "http://localhost",
    "http://localhost:8000",
    "http://localhost:8501",
    # Ensure FRONTEND_URL env var is set in your deployment environment
    os.getenv("FRONTEND_URL", "*"),  # Use wildcard only if necessary and safe
]
# Remove potential duplicates and sort
origins = sorted(list(set(o for o in origins if o)))  # Filter out empty strings

app.add_middleware(LoggingMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,  # Use the cleaned list
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
logger.info("CORS middleware configured for origins: %s", origins)


# --------------------------------------------------------------------------
# Startup Event (Feature Flag Logging Only) ### UPDATED COMMENT ###
# --------------------------------------------------------------------------
@app.on_event("startup")
async def startup_event():
    logger.info("Application startup event executing...")

    # --- Feature Flag Logging (Kept in startup event) ---
    logger.info("--- Verifying Feature Flag Status (from settings) ---")
    if feature_flags_available and hasattr(Feature, "__members__"):
        for feature in Feature:
            try:
                # Use the imported is_enabled function
                status = is_enabled(feature)
                logger.info(
                    "Feature: %s Status: %s",
                    feature.name,
                    "ENABLED" if status else "DISABLED",
                )
            except Exception as e:
                logger.error(
                    "Error checking status for feature %s: %s", feature.name, e
                )
    elif not feature_flags_available:
        logger.error("Feature flags module failed import, cannot check status.")
    else:
        logger.warning("Feature enum has no members defined?")
    logger.info("-----------------------------------------------------")
    # --- END Feature Flag Logging ---

    # --- Log architecture status ---
    if hasattr(app.state, "architecture"):
        logger.info("Enhanced architecture is active and initialized")
        try:
            # Get and log metrics from components
            if hasattr(app.state.architecture, "task_queue"):
                task_queue = app.state.architecture.task_queue()
                queue_status = await task_queue.get_queue_status()
                logger.info("Task Queue Status: %s", queue_status)

            if hasattr(app.state.architecture, "cache_service"):
                cache_service = app.state.architecture.cache_service()
                logger.info(
                    "Cache Service Active: %s", cache_service.config.backend.value
                )

            if hasattr(app.state.architecture, "event_bus"):
                event_bus = app.state.architecture.event_bus()
                bus_metrics = event_bus.get_metrics()
                logger.info("Event Bus Metrics: %s", bus_metrics)
        except Exception as arch_err:
            logger.error("Error getting architecture component status: %s", arch_err)
    else:
        logger.warning("Enhanced architecture not found in app.state")

    logger.info("Startup event complete.")


# --------------------------------------------------------------------------
# Shutdown Event
# --------------------------------------------------------------------------
@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Application shutdown event executing...")

    # --- Graceful shutdown of enhanced architecture components ---
    if hasattr(app.state, "architecture"):
        logger.info("Shutting down enhanced architecture components...")
        try:
            # Stop task queue
            if hasattr(app.state.architecture, "task_queue"):
                task_queue = app.state.architecture.task_queue()
                await task_queue.stop()
                logger.info("Task Queue stopped successfully")
        except Exception as shutdown_err:
            logger.error(
                "Error during architecture component shutdown: %s", shutdown_err
            )

    logger.info("Shutdown event complete.")


# --------------------------------------------------------------------------
# Root Endpoint
# --------------------------------------------------------------------------
@app.get("/", tags=["Status"], include_in_schema=False)
async def read_root():
    """Basic status endpoint"""
    return {"message": "Welcome to the Forest OS API (Version %s)" % app.version}


# --------------------------------------------------------------------------
# Local Development Run Hook
# --------------------------------------------------------------------------
if __name__ == "__main__":
    try:
        import uvicorn
    except ImportError as e:
        logger.error(f"Failed to import uvicorn: {e}")
        class uvicorn:
            @staticmethod
            def run(*args, **kwargs):
                logger.error("uvicorn.run called, but uvicorn is not installed.")
                print("uvicorn.run called, but uvicorn is not installed.")

    logger.info("Starting Uvicorn development server directly via __main__...")
    reload_flag = os.getenv("APP_ENV", "development") == "development" and os.getenv(
        "UVICORN_RELOAD", "True"
    ).lower() in ("true", "1")

    # Make sure to pass the app object correctly
    # Use "forest_app.main:app" if running from outside the directory
    # Use "main:app" if running from within the forest_app directory
    uvicorn.run(
        "main:app",  # Changed for direct run
        host=os.getenv("HOST", "0.0.0.0"),
        port=int(os.getenv("PORT", "8000")),
        reload=reload_flag,
        log_level=os.getenv("UVICORN_LOG_LEVEL", "info").lower(),
    )
