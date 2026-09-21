import json
import os
import time

import pika
import pika.exceptions


EXCHANGE = "job_tracker.events"
QUEUE = "analytics.events"

BINDING_KEYS = [
    "*.created",
    "job.deleted",
]


def connect():
    while True:
        try:
            return pika.BlockingConnection(
                pika.URLParameters(os.environ["BROKER_URL"])
            )
        except pika.exceptions.AMQPConnectionError:
            print("[ANALYTICS] Waiting for RabbitMQ...", flush=True)
            time.sleep(2)


def main():
    connection = connect()
    channel = connection.channel()

    channel.exchange_declare(
        exchange=EXCHANGE,
        exchange_type="topic",
        durable=True,
    )

    channel.queue_declare(
        queue=QUEUE,
        durable=True,
    )

    for binding_key in BINDING_KEYS:
        channel.queue_bind(
            exchange=EXCHANGE,
            queue=QUEUE,
            routing_key=binding_key,
        )

    channel.basic_qos(prefetch_count=1)

    print(
        f"[ANALYTICS] Listening queue={QUEUE} bindings={BINDING_KEYS}",
        flush=True,
    )

    def callback(ch, method, properties, body):
        try:
            event = json.loads(body)

            print(
                f"[ANALYTICS] RECEIVED "
                f"event_id={event.get('event_id')} "
                f"event_type={event.get('event_type')} "
                f"routing_key={method.routing_key}",
                flush=True,
            )

            print(
                f"[ANALYTICS] payload={event}",
                flush=True,
            )

            ch.basic_ack(
                delivery_tag=method.delivery_tag
            )

        except Exception as exc:
            print(
                f"[ANALYTICS] ERROR: {exc}",
                flush=True,
            )

            ch.basic_nack(
                delivery_tag=method.delivery_tag,
                requeue=False,
            )

    channel.basic_consume(
        queue=QUEUE,
        on_message_callback=callback,
        auto_ack=False,
    )

    channel.start_consuming()


if __name__ == "__main__":
    main()