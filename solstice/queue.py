"""RabbitMQ publisher for asynchronous badge-print requests."""

from __future__ import annotations

import json

import pika


PRINT_QUEUE = "solstice.badge_print_requests"


class QueuePublishError(RuntimeError):
    """Raised when a print request cannot be accepted by RabbitMQ."""


class RabbitMQPrintPublisher:
    def __init__(self, host: str = "127.0.0.1", queue_name: str = PRINT_QUEUE) -> None:
        self.host = host
        self.queue_name = queue_name

    def publish(self, message: dict) -> None:
        connection = None
        try:
            connection = pika.BlockingConnection(
                pika.ConnectionParameters(host=self.host)
            )
            channel = connection.channel()
            channel.queue_declare(queue=self.queue_name, durable=True)
            channel.confirm_delivery()
            channel.basic_publish(
                exchange="",
                routing_key=self.queue_name,
                body=json.dumps(message).encode("utf-8"),
                properties=pika.BasicProperties(
                    content_type="application/json",
                    delivery_mode=pika.DeliveryMode.Persistent,
                    message_id=message["print_job_id"],
                ),
                mandatory=True,
            )
        except (pika.exceptions.AMQPError, OSError) as error:
            raise QueuePublishError("print request could not be queued") from error
        finally:
            if connection is not None and connection.is_open:
                connection.close()
