"""Start the asynchronous Solstice check-in kiosk."""

from __future__ import annotations

import argparse
import os
from pathlib import Path

from solstice.async_checkin import AsyncCheckInService
from solstice.api import create_server
from solstice.attendees import AttendeeStore
from solstice.queue import RabbitMQPrintPublisher
from solstice.webhook import WebhookService


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the Solstice check-in kiosk.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", default=8080, type=int)
    parser.add_argument("--rabbitmq-host", default="127.0.0.1")
    parser.add_argument("--database", default="data/solstice.db")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    database_path = Path(args.database)
    database_path.parent.mkdir(parents=True, exist_ok=True)

    store = AttendeeStore(database_path)
    publisher = RabbitMQPrintPublisher(args.rabbitmq_host)
    check_in = AsyncCheckInService(store, publisher)
    webhook = WebhookService(
        store,
        os.environ.get("SOLSTICE_WEBHOOK_SECRET", "demo-secret"),
    )
    server = create_server(store, check_in, webhook, args.host, args.port)

    print(f"Solstice kiosk listening at http://{args.host}:{args.port}")
    print(f"Publishing badge requests to RabbitMQ at {args.rabbitmq_host}:5672")
    print("Webhook endpoint: /webhooks/badge-printed")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("Stopping Solstice kiosk")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
