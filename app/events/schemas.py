from datetime import datetime, timezone
from typing import Any
import uuid


EVENT_TYPES = {
    "application.created",
    "application.status_updated",
    "resume.uploaded",
    "job.created",
    "job.deleted",
}


def create_event(
    event_type: str,
    data: dict[str, Any],
    source: str = "job-tracker-api",
) -> dict[str, Any]:
    if event_type not in EVENT_TYPES:
        raise ValueError(f"Unsupported event type: {event_type}")

    return {
        "event_id": str(uuid.uuid4()),
        "event_type": event_type,
        "version": "v1",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "source": source,
        "data": data,
    }