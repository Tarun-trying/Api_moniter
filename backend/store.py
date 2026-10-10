"""
MongoDB-backed data store for PulseMonitor.

Replaces the old in-memory dicts with async calls to MongoDB Atlas via motor.
All public functions keep the same signatures as the original in-memory store
so that the rest of the codebase (api/, services/, scheduler.py) is unchanged.

Collections
-----------
monitors  — one doc per monitor (config + cached last-status fields)
checks    — individual check result records
incidents — incident records
users     — registered users
"""
import logging
from datetime import datetime
from typing import Optional

from database import get_db

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _to_int_id(oid) -> int:
    """
    We expose integer IDs to the rest of the app; MongoDB uses ObjectIds internally.
    We store a numeric `id` field alongside `_id` for compatibility.
    """
    return oid


def _serialize(doc: dict) -> dict:
    """Strip `_id` and return a plain dict the rest of the app can consume."""
    if doc is None:
        return None
    d = dict(doc)
    d.pop("_id", None)
    return d


# ---------------------------------------------------------------------------
# Monitor helpers
# ---------------------------------------------------------------------------

async def make_monitor(
    name: str,
    url: str,
    method: str = "GET",
    interval: int = 300,
    timeout: int = 10,
    expected_status: Optional[int] = 200,
    expected_content: Optional[str] = None,
    user_id: Optional[str] = None,
) -> dict:
    db = get_db()
    now = datetime.utcnow()

    # Use an auto-increment counter stored in a `counters` collection
    counter_doc = await db.counters.find_one_and_update(
        {"_id": "monitors"},
        {"$inc": {"seq": 1}},
        upsert=True,
        return_document=True,
    )
    mid = counter_doc["seq"]

    m = {
        "id": mid,
        "user_id": user_id,
        "name": name,
        "url": url,
        "method": method,
        "interval": interval,
        "timeout": timeout,
        "expected_status": expected_status,
        "expected_content": expected_content,
        "is_active": True,
        "created_at": now,
        "updated_at": now,
        # cached check state
        "last_status": "checking",
        "last_response_time": None,
        "last_checked_at": None,
        "last_status_code": None,
        "last_error": None,
    }
    await db.monitors.insert_one({**m})
    return m


async def get_monitor(monitor_id: int, user_id: Optional[str] = None) -> Optional[dict]:
    db = get_db()
    query = {"id": monitor_id}
    if user_id is not None:
        query["user_id"] = user_id
    doc = await db.monitors.find_one(query)
    return _serialize(doc)


async def update_monitor_cache(monitor_id: int, **kwargs) -> None:
    """Update specific fields on the monitor document (e.g. after a check)."""
    db = get_db()
    kwargs["updated_at"] = datetime.utcnow()
    await db.monitors.update_one({"id": monitor_id}, {"$set": kwargs})


async def list_monitors_sorted(user_id: Optional[str] = None) -> list[dict]:
    """Return all monitors ordered by created_at descending, optionally scoped to a user."""
    db = get_db()
    query = {}
    if user_id is not None:
        query["user_id"] = user_id
    cursor = db.monitors.find(query).sort("created_at", -1)
    return [_serialize(doc) async for doc in cursor]


async def delete_monitor(monitor_id: int) -> bool:
    db = get_db()
    result = await db.monitors.delete_one({"id": monitor_id})
    if result.deleted_count == 0:
        return False
    # Cascade: remove related checks and incidents
    await db.checks.delete_many({"monitor_id": monitor_id})
    await db.incidents.delete_many({"monitor_id": monitor_id})
    return True


# ---------------------------------------------------------------------------
# Check helpers
# ---------------------------------------------------------------------------

async def add_check(
    monitor_id: int,
    status_code: Optional[int],
    response_time: Optional[float],
    success: bool,
    error_message: Optional[str],
    content_check_passed: Optional[bool],
    checked_at: datetime,
) -> dict:
    db = get_db()

    counter_doc = await db.counters.find_one_and_update(
        {"_id": "checks"},
        {"$inc": {"seq": 1}},
        upsert=True,
        return_document=True,
    )
    cid = counter_doc["seq"]

    c = {
        "id": cid,
        "monitor_id": monitor_id,
        "status_code": status_code,
        "response_time": response_time,
        "success": success,
        "error_message": error_message,
        "content_check_passed": content_check_passed,
        "checked_at": checked_at,
    }
    await db.checks.insert_one({**c})
    return c


async def get_checks_for(monitor_id: int, limit: int = 50) -> list[dict]:
    """Return checks for a monitor, most recent first, up to `limit`."""
    db = get_db()
    cursor = (
        db.checks.find({"monitor_id": monitor_id})
        .sort("checked_at", -1)
        .limit(limit)
    )
    return [_serialize(doc) async for doc in cursor]


async def get_checks_since(monitor_id: int, since: datetime) -> list[dict]:
    """Return all checks for a monitor after `since`, oldest first."""
    db = get_db()
    cursor = (
        db.checks.find({"monitor_id": monitor_id, "checked_at": {"$gte": since}})
        .sort("checked_at", 1)
    )
    return [_serialize(doc) async for doc in cursor]


async def get_all_checks_since(since: datetime, user_id: Optional[str] = None) -> list[dict]:
    """Return all checks across all (user-scoped) monitors since `since`."""
    db = get_db()
    if user_id is not None:
        # Get monitor IDs for this user first
        monitor_ids = [
            m["id"] async for m in db.monitors.find({"user_id": user_id}, {"id": 1})
        ]
        cursor = db.checks.find(
            {"monitor_id": {"$in": monitor_ids}, "checked_at": {"$gte": since}}
        )
    else:
        cursor = db.checks.find({"checked_at": {"$gte": since}})
    return [_serialize(doc) async for doc in cursor]


async def get_recent_results(monitor_id: int, n: int) -> list[bool]:
    """Return the `success` values of the last n checks (most recent first)."""
    db = get_db()
    cursor = (
        db.checks.find({"monitor_id": monitor_id}, {"success": 1})
        .sort("checked_at", -1)
        .limit(n)
    )
    return [doc["success"] async for doc in cursor]


# ---------------------------------------------------------------------------
# Incident helpers
# ---------------------------------------------------------------------------

async def add_incident(monitor_id: int, reason: str) -> dict:
    db = get_db()

    counter_doc = await db.counters.find_one_and_update(
        {"_id": "incidents"},
        {"$inc": {"seq": 1}},
        upsert=True,
        return_document=True,
    )
    iid = counter_doc["seq"]

    i = {
        "id": iid,
        "monitor_id": monitor_id,
        "started_at": datetime.utcnow(),
        "resolved_at": None,
        "reason": reason,
        "status": "ongoing",
    }
    await db.incidents.insert_one({**i})
    return i


async def get_ongoing_incident(monitor_id: int) -> Optional[dict]:
    db = get_db()
    cursor = (
        db.incidents.find({"monitor_id": monitor_id, "status": "ongoing"})
        .sort("started_at", -1)
        .limit(1)
    )
    docs = [_serialize(doc) async for doc in cursor]
    return docs[0] if docs else None


async def resolve_incident(incident_id: int) -> None:
    db = get_db()
    await db.incidents.update_one(
        {"id": incident_id},
        {"$set": {"status": "resolved", "resolved_at": datetime.utcnow()}},
    )


async def list_incidents(
    status_filter: Optional[str] = None,
    limit: int = 50,
    user_id: Optional[str] = None,
) -> list[dict]:
    db = get_db()
    if user_id is not None:
        monitor_ids = [
            m["id"] async for m in db.monitors.find({"user_id": user_id}, {"id": 1})
        ]
        query = {"monitor_id": {"$in": monitor_ids}}
    else:
        query = {}
    if status_filter:
        query["status"] = status_filter
    cursor = db.incidents.find(query).sort("started_at", -1).limit(limit)
    return [_serialize(doc) async for doc in cursor]


async def get_incidents_for(monitor_id: int, limit: int = 20) -> list[dict]:
    db = get_db()
    cursor = (
        db.incidents.find({"monitor_id": monitor_id})
        .sort("started_at", -1)
        .limit(limit)
    )
    return [_serialize(doc) async for doc in cursor]


async def get_all_incidents_since(
    since: datetime, user_id: Optional[str] = None
) -> list[dict]:
    db = get_db()
    if user_id is not None:
        monitor_ids = [
            m["id"] async for m in db.monitors.find({"user_id": user_id}, {"id": 1})
        ]
        cursor = db.incidents.find(
            {"monitor_id": {"$in": monitor_ids}, "started_at": {"$gte": since}}
        )
    else:
        cursor = db.incidents.find({"started_at": {"$gte": since}})
    return [_serialize(doc) async for doc in cursor]
