"""Simulated vendor that consumes print jobs and confirms them by webhook."""

from __future__ import annotations

import argparse
import json
import os
import time
import uuid
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

import pika

from solstice.queue import PRINT_QUEUE
from solstice.webhook import SIGNATURE_HEADER, create_signature


def send_completion(webhook_url: str, secret: str, print_job: dict) -> None:
    payload = {
        "event_id": f"event-{uuid.uuid4().hex}",
        "print_job_id": print_job["print_job_id"],
        "attendee_id": print_job["attendee_id"],
    }
    body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    request = Request(
        webhook_url,
        data=body,
        method="POST",
        headers={
            "Content-Type": "application/json",
            SIGNATURE_HEADER: create_signature(body, secret),
        },
    )
    with urlopen(request, timeout=5) as response:
        if response.status != 200:
            raise RuntimeError(f"webhook returned HTTP {response.status}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the badge-printer queue worker.")
    parser.add_argument("--rabbitmq-host", default="127.0.0.1")
    parser.add_argument(
        "--webhook-url",
        default="http://127.0.0.1:8080/webhooks/badge-printed",
    )
    parser.add_argument("--print-delay", type=float, default=2.0)
    args = parser.parse_args()
    secret = os.environ.get("SOLSTICE_WEBHOOK_SECRET", "demo-secret")

    connection = pika.BlockingConnection(
        pika.ConnectionParameters(host=args.rabbitmq_host)
    )
    channel = connection.channel()
    channel.queue_declare(queue=PRINT_QUEUE, durable=True)
    channel.basic_qos(prefetch_count=1)

    def process_message(channel, method, properties, body: bytes) -> None:
        try:
            print_job = json.loads(body)
            print(
                f"Printing badge for {print_job['attendee_name']} "
                f"({print_job['attendee_id']})..."
            )
            time.sleep(args.print_delay)
            send_completion(args.webhook_url, secret, print_job)
        except (KeyError, json.JSONDecodeError, HTTPError, URLError, RuntimeError) as error:
            print(f"Print confirmation failed: {error}; message returned to queue")
            channel.basic_nack(delivery_tag=method.delivery_tag, requeue=True)
            return

        channel.basic_ack(delivery_tag=method.delivery_tag)
        print(f"Print completed and confirmed: {print_job['print_job_id']}")

    channel.basic_consume(queue=PRINT_QUEUE, on_message_callback=process_message)
    print(f"Vendor worker waiting on RabbitMQ queue {PRINT_QUEUE}")
    try:
        channel.start_consuming()
    except KeyboardInterrupt:
        print("Stopping vendor worker")
    finally:
        if channel.is_open:
            channel.stop_consuming()
        connection.close()


if __name__ == "__main__":
    main()
