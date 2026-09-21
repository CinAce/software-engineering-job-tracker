import json
import os

import pika

from app.events.schemas import create_event


EXCHANGE = "job_tracker.events"


def publish_event(event_type: str, data: dict) -> dict:
    event = create_event(event_type, data)

    connection = pika.BlockingConnection(
        pika.URLParameters(os.environ["BROKER_URL"])
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

    connection.close()

    return event