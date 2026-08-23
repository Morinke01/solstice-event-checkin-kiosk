"""Verify RabbitMQ publishing and pending duplicate protection."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pika

from solstice.async_checkin import AsyncCheckInService
from solstice.attendees import AttendeeStore
from solstice.queue import RabbitMQPrintPublisher


VERIFY_QUEUE = "solstice.verify_badge_print_requests"


def main() -> None:
    connection = pika.BlockingConnection(pika.ConnectionParameters("127.0.0.1"))
    channel = connection.channel()
    channel.queue_declare(queue=VERIFY_QUEUE, durable=True)
    channel.queue_purge(queue=VERIFY_QUEUE)

    try:
        with tempfile.TemporaryDirectory() as temporary_directory:
            store = AttendeeStore(Path(temporary_directory) / "queue-test.db")
            service = AsyncCheckInService(
                store,
                RabbitMQPrintPublisher(queue_name=VERIFY_QUEUE),
            )

            first = service.scan("SOL-001")
            duplicate = service.scan("SOL-001")
            queue_state = channel.queue_declare(
                queue=VERIFY_QUEUE,
                durable=True,
                passive=True,
            )

            print(f"first_status={first['attendee']['status']}")
            print(f"first_queued={str(first['queued']).lower()}")
            print(f"duplicate={str(duplicate['duplicate']).lower()}")
            print(f"queue_messages={queue_state.method.message_count}")
    finally:
        channel.queue_delete(queue=VERIFY_QUEUE)
        connection.close()


if __name__ == "__main__":
    main()
