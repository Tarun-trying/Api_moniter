"""
MongoDB Atlas connection manager for PulseMonitor.

Reads MONGODB_URI from environment / .env file.
Exposes `get_db()` to obtain the Mongo database handle.
"""
import os
import logging
from typing import Optional
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

_client: Optional[AsyncIOMotorClient] = None
_db = None


async def connect_db() -> None:
    """Open the MongoDB connection. Call this once at app startup."""
    global _client, _db

    uri = os.getenv("MONGODB_URI")
    if not uri:
        raise RuntimeError(
            "MONGODB_URI is not set. "
            "Create a .env file with MONGODB_URI=<your-atlas-connection-string>"
        )

    db_name = os.getenv("MONGODB_DB", "pulsemonitor")
    _client = AsyncIOMotorClient(uri)
    _db = _client[db_name]

    # Confirm the connection works
    await _client.admin.command("ping")
    logger.info("Connected to MongoDB Atlas (db=%s)", db_name)

    # Ensure indexes for query performance
    await _ensure_indexes(_db)


async def close_db() -> None:
    """Close the MongoDB connection. Call this at app shutdown."""
    global _client, _db
    if _client:
        _client.close()
        _client = None
        _db = None
        logger.info("MongoDB connection closed")


def get_db():
    """Return the active database handle. Raises if not connected."""
    if _db is None:
        raise RuntimeError("Database not initialised — call connect_db() first")
    return _db


async def _ensure_indexes(db) -> None:
    """Create indexes for frequently queried fields."""
    from pymongo import ASCENDING, DESCENDING
    # checks: look up by monitor + time
    await db.checks.create_index(
        [("monitor_id", ASCENDING), ("checked_at", DESCENDING)]
    )
    # incidents: look up ongoing incidents per monitor
    await db.incidents.create_index(
        [("monitor_id", ASCENDING), ("status", ASCENDING), ("started_at", DESCENDING)]
    )
    # monitors: unique numeric id
    await db.monitors.create_index([("id", ASCENDING)], unique=True)
    logger.info("MongoDB indexes ensured")

