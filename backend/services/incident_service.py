"""
Incident auto-create and auto-resolve logic (in-memory store version).

Rules:
- Create incident: 3 consecutive failures on the same monitor.
- Resolve incident: 2 consecutive successes after an ongoing incident.
"""
import store

FAILURE_THRESHOLD = 3    # consecutive failures before incident
RECOVERY_THRESHOLD = 2   # consecutive successes before resolving


def evaluate_incident(monitor_id: int, latest_check: dict) -> None:
    """
    Called after every check result is saved.
    Decides whether to open or close an incident.
    """
    ongoing = store.get_ongoing_incident(monitor_id)

    if not latest_check["success"]:
        # Already has an incident — nothing to do
        if ongoing:
            return

        # Check if we've hit the failure threshold
        recent = store.get_recent_results(monitor_id, FAILURE_THRESHOLD)
        if len(recent) >= FAILURE_THRESHOLD and all(not s for s in recent):
            reason = latest_check["error_message"] or (
                f"HTTP {latest_check['status_code']}"
                if latest_check["status_code"]
                else "Check failed"
            )
            store.add_incident(monitor_id=monitor_id, reason=reason)
    else:
        # Service is back — can we resolve?
        if not ongoing:
            return

        recent = store.get_recent_results(monitor_id, RECOVERY_THRESHOLD)
        if len(recent) >= RECOVERY_THRESHOLD and all(s for s in recent):
            store.resolve_incident(ongoing["id"])
