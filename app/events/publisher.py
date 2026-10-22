
import json
import os

import pika

from app.events.schemas import create_event


EXCHANGE = "job_tracker.events"


def publish_event(event_type: str, data: dict) -> dict:
    event = create_event(event_type, data)

    # Support both environment-variable names used by the project.
    broker_url = os.getenv("BROKER_URL") or os.getenv("AMQP_URL")

    if not broker_url:
        raise RuntimeError(
            "Missing broker URL: configure BROKER_URL or AMQP_URL"
        )

    connection = None

    try:
        connection = pika.BlockingConnection(
            pika.URLParameters(broker_url)
        )

        channel = connection.channel()

        channel.exchange_declare(
            exchange=EXCHANGE,
            exchange_type="topic",
            durable=True,
        )

        channel.basic_publish(
            exchange=EXCHANGE,
            routing_key=event_type,
            body=json.dumps(event).encode(),
            properties=pika.BasicProperties(
                delivery_mode=pika.DeliveryMode.Persistent,
                content_type="application/json",
            ),
        )

        return event

    finally:
        if connection is not None and connection.is_open:
            connection.close()
