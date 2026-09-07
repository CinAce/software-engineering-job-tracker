"""Messaging port — AMQP 0-9-1.

Same principle as `storage.py`. AMQP is an on-the-wire protocol with many
implementations: RabbitMQ on your laptop, a managed RabbitMQ in the cloud, or
anything else that speaks 0-9-1. The URL changes; this file does not.

    modules 1-5   AMQP_URL=amqp://guest:guest@broker:5672/
    modules 6-8   AMQP_URL=amqps://...

If your chosen provider offers a queue that is NOT AMQP, you implement this same
interface over its SDK in `app/adapters/` and the application still does not
change. That substitution is the Module 7 extension exercise.
"""

from __future__ import annotations

import json
import os
from typing import Any, Callable

import pika
from tenacity import retry, stop_after_delay, wait_fixed


class Queue:
    def __init__(self, name: str, url: str | None = None) -> None:
        self.name = name
        self.url = url or os.environ["AMQP_URL"]
        self._conn: pika.BlockingConnection | None = None

    # A broker takes 10-30 seconds to accept connections after the container
    # starts. Without this retry the first run of every tutorial looks broken.
    # The compose files also declare a healthcheck; this is the belt to that
    # pair of braces, because a student running the app outside compose has no
    # healthcheck to depend on.
    @retry(stop=stop_after_delay(60), wait=wait_fixed(2), reraise=True)
    def connect(self) -> None:
        self._conn = pika.BlockingConnection(pika.URLParameters(self.url))
        channel = self._conn.channel()
        channel.queue_declare(queue=self.name, durable=True)
        channel.close()

    def _channel(self):
        if self._conn is None or self._conn.is_closed:
            self.connect()
        return self._conn.channel()

    def publish(self, payload: dict[str, Any]) -> None:
        channel = self._channel()
        channel.basic_publish(
            exchange="",
            routing_key=self.name,
            body=json.dumps(payload).encode(),
            properties=pika.BasicProperties(delivery_mode=2, content_type="application/json"),
        )
        channel.close()

    def consume(self, handler: Callable[[dict[str, Any]], None]) -> None:
        """Blocking consumer. Acknowledges only after the handler returns."""
        channel = self._channel()
        channel.basic_qos(prefetch_count=1)

        def _on_message(ch, method, _properties, body):
            handler(json.loads(body))
            ch.basic_ack(delivery_tag=method.delivery_tag)

        channel.basic_consume(queue=self.name, on_message_callback=_on_message)
        channel.start_consuming()

    def depth(self) -> int:
        """Messages currently waiting. Used by the module 3 drain script."""
        channel = self._channel()
        result = channel.queue_declare(queue=self.name, durable=True, passive=True)
        depth = result.method.message_count
        channel.close()
        return depth

    def close(self) -> None:
        if self._conn and self._conn.is_open:
            self._conn.close()
