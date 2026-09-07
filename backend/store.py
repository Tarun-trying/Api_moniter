"""
In-memory data store for PulseMonitor.

All state lives in Python dicts — no database, no files.
Data is lost on server restart (by design).

Entities
--------
monitors  : dict[int, dict]   – monitor config + cached last-status fields
checks    : dict[int, dict]   – individual check results, keyed by check id
incidents : dict[int, dict]   – incidents, keyed by incident id

All write operations should be done inside `_lock` to stay thread-safe
(the asyncio event loop is single-threaded, but the scheduler can be
called from sync threads in some FastAPI configurations).
"""
import threading
from datetime import datetime
from typing import Optional

# ---------------------------------------------------------------------------
# Internal state
# ---------------------------------------------------------------------------

_lock = threading.Lock()

_next_ids: dict[str, int] = {"monitors": 1, "checks": 1, "incidents": 1}

monitors:  dict[int, dict] = {}
checks:    dict[int, dict] = {}
incidents: dict[int, dict] = {}


# ---------------------------------------------------------------------------
# ID helpers
# ---------------------------------------------------------------------------

def _next_id(kind: str) -> int:
    with _lock:
        id_ = _next_ids[kind]
        _next_ids[kind] += 1
        return id_


# ---------------------------------------------------------------------------
# Monitor helpers
# ---------------------------------------------------------------------------

def make_monitor(
    name: str,
    url: str,
    method: str = "GET",
    interval: int = 300,
    timeout: int = 10,
    expected_status: Optional[int] = 200,
    expected_content: Optional[str] = None,
) -> dict:
    mid = _next_id("monitors")
    now = datetime.utcnow()
    m = {
        "id": mid,
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
    with _lock:
        monitors[mid] = m
    return m


def get_monitor(monitor_id: int) -> Optional[dict]:
    return monitors.get(monitor_id)


def update_monitor_cache(monitor_id: int, **kwargs) -> None:
    """Update specific fields on the monitor dict (e.g. after a check)."""
    with _lock:
        m = monitors.get(monitor_id)
        if m:
            m.update(kwargs)
            m["updated_at"] = datetime.utcnow()


def list_monitors_sorted() -> list[dict]:
    """Return all monitors ordered by created_at descending."""
    return sorted(monitors.values(), key=lambda m: m["created_at"], reverse=True)


def delete_monitor(monitor_id: int) -> bool:
    with _lock:
        if monitor_id not in monitors:
            return False
        del monitors[monitor_id]
        # Cascade: remove related checks and incidents
        for cid in [cid for cid, c in checks.items() if c["monitor_id"] == monitor_id]:
            del checks[cid]
        for iid in [iid for iid, i in incidents.items() if i["monitor_id"] == monitor_id]:
            del incidents[iid]
    return True


# ---------------------------------------------------------------------------
# Check helpers
# ---------------------------------------------------------------------------

def add_check(
    monitor_id: int,
    status_code: Optional[int],
    response_time: Optional[float],
    success: bool,
    error_message: Optional[str],
    content_check_passed: Optional[bool],
    checked_at: datetime,
) -> dict:
    cid = _next_id("checks")
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
    with _lock:
        checks[cid] = c
    return c


def get_checks_for(monitor_id: int, limit: int = 50) -> list[dict]:
    """Return checks for a monitor, most recent first, up to `limit`."""
    relevant = [c for c in checks.values() if c["monitor_id"] == monitor_id]
    relevant.sort(key=lambda c: c["checked_at"], reverse=True)
    return relevant[:limit]


def get_checks_since(monitor_id: int, since: datetime) -> list[dict]:
    """Return all checks for a monitor after `since`, oldest first."""
    relevant = [
        c for c in checks.values()
        if c["monitor_id"] == monitor_id and c["checked_at"] >= since
    ]
    relevant.sort(key=lambda c: c["checked_at"])
    return relevant


def get_all_checks_since(since: datetime) -> list[dict]:
    """Return all checks across all monitors since `since`."""
    return [c for c in checks.values() if c["checked_at"] >= since]


def get_recent_results(monitor_id: int, n: int) -> list[bool]:
    """Return the `success` values of the last n checks (most recent first)."""
    relevant = [c for c in checks.values() if c["monitor_id"] == monitor_id]
    relevant.sort(key=lambda c: c["checked_at"], reverse=True)
    return [c["success"] for c in relevant[:n]]


# ---------------------------------------------------------------------------
# Incident helpers
# ---------------------------------------------------------------------------

def add_incident(monitor_id: int, reason: str) -> dict:
    iid = _next_id("incidents")
    i = {
        "id": iid,
        "monitor_id": monitor_id,
        "started_at": datetime.utcnow(),
        "resolved_at": None,
        "reason": reason,
        "status": "ongoing",
    }
    with _lock:
        incidents[iid] = i
    return i


def get_ongoing_incident(monitor_id: int) -> Optional[dict]:
    ongoing = [
        i for i in incidents.values()
        if i["monitor_id"] == monitor_id and i["status"] == "ongoing"
    ]
    if not ongoing:
        return None
    return max(ongoing, key=lambda i: i["started_at"])


def resolve_incident(incident_id: int) -> None:
    with _lock:
        i = incidents.get(incident_id)
        if i:
            i["status"] = "resolved"
            i["resolved_at"] = datetime.utcnow()


def list_incidents(status_filter: Optional[str] = None, limit: int = 50) -> list[dict]:
    result = list(incidents.values())
    if status_filter:
        result = [i for i in result if i["status"] == status_filter]
    result.sort(key=lambda i: i["started_at"], reverse=True)
    return result[:limit]


def get_incidents_for(monitor_id: int, limit: int = 20) -> list[dict]:
    result = [i for i in incidents.values() if i["monitor_id"] == monitor_id]
    result.sort(key=lambda i: i["started_at"], reverse=True)
    return result[:limit]


def get_all_incidents_since(since: datetime) -> list[dict]:
    return [i for i in incidents.values() if i["started_at"] >= since]
