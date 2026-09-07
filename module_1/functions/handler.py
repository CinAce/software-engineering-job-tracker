"""A provider-neutral function handler.

`handler(event, context) -> response` is the lowest common denominator across
function runtimes. Keeping to it means the same file runs:

  * locally, under app/function_host.py            (module 4, no account)
  * on a provider's function service               (module 7, one line of shim)

Do not import a provider SDK here. If you need one, it goes in
app/adapters/ behind a port, exactly like storage and queue.
"""

from __future__ import annotations

import json
from typing import Any


def handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    try:
        payload = json.loads(event.get("body") or "{}")
    except ValueError:
        return _response(400, {"detail": "body is not valid JSON"})

    name = payload.get("name")
    if not isinstance(name, str) or not name.strip():
        return _response(422, {"detail": "field 'name' is required and must be a non-empty string"})

    return _response(
        200,
        {
            "greeting": f"hello, {name.strip()}",
            "invoked_by": getattr(context, "function_name", "unknown"),
            "memory_mb": getattr(context, "memory_limit_in_mb", None),
        },
    )


def _response(status: int, body: dict[str, Any]) -> dict[str, Any]:
    return {
        "statusCode": status,
        "headers": {"content-type": "application/json"},
        "body": json.dumps(body),
    }
