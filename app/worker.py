"""Module 3 background worker.

Consumes from the AMQP queue and does the slow thing the API declined to do
inline. Run by `docker compose up -d --wait`; also runnable directly with
`python -m app.worker`.
"""

from __future__ import annotations

import logging
import time

from app.ports.queue import Queue

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("worker")


def handle(message: dict) -> None:
    log.info("processing %s", message.get("id", "<no id>"))
    time.sleep(0.2)  # stands in for the slow work
    log.info("done %s", message.get("id", "<no id>"))


def main() -> None:
    queue = Queue("itc531.jobs")
    log.info("connecting to broker (retries for up to 60s while it starts)")
    queue.connect()
    log.info("consuming from %s", queue.name)
    queue.consume(handle)


if __name__ == "__main__":
    main()
