#!/usr/bin/env python
"""
Database initialization script for basic schema creation.
"""

import logging
import os

from dotenv import load_dotenv
from sqlalchemy import create_engine

from forest_app.persistence.models import Base

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def initialize_db():
    """Initialize the database with core models."""
    load_dotenv()

    # Get connection string from environment variables
    db_url = os.environ.get("DB_CONNECTION_STRING") or os.environ.get("DATABASE_URL")

    if not db_url:
        logger.error("Database connection string not found in environment variables")
        return False

    logger.info("Using database URL: %s...", db_url[:20])

    try:
        engine = create_engine(db_url)

        # Create tables
        logger.info("Creating database tables...")
        Base.metadata.create_all(engine)

        logger.info("Database initialized successfully!")
        return True

    except Exception as e:
        logger.error(f"Error initializing database: {str(e)}")
        return False


if __name__ == "__main__":
    success = initialize_db()
    exit(0 if success else 1)
