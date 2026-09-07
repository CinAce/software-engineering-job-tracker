"""Module 4 — the same business logic behind a function-shaped interface.

A function runtime, whatever the provider calls it, gives your code an event and
a context and expects a response. It does not give you a long-running process,
a warm cache, or a local disk you can rely on.

`functions/handler.py` is deliberately provider-neutral: `handler(event, context)`
is the shape every major runtime accepts with at most a two-line shim. This host
runs it over plain HTTP so you can exercise it with no account anywhere.

The module's lesson is the diff between this file and app/main.py, not either one
on its own.
"""

from __future__ import annotations

import json

import uvicorn
from fastapi import FastAPI, Request

from functions.handler import handler

app = FastAPI(title="itc531-function-host", version="1.0.0")


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "shape": "function"}


@app.post("/invoke")
async def invoke(request: Request) -> dict:
    body = await request.body()
    event = {
        "body": body.decode() or "{}",
        "headers": dict(request.headers),
        "queryStringParameters": dict(request.query_params),
        "requestContext": {"http": {"method": request.method, "path": "/invoke"}},
    }

    class Context:
        function_name = "itc531-local"
        memory_limit_in_mb = 512
        aws_request_id = "local-invocation"

    result = handler(event, Context())
    if isinstance(result, dict) and "body" in result:
        try:
            result["body"] = json.loads(result["body"])
        except (TypeError, ValueError):
            pass
    return result


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8001)
