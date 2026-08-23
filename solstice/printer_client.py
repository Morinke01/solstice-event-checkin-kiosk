"""DEPRECATED Day 3 synchronous printer client retained as audit evidence.

The Day 4 runtime publishes with ``RabbitMQPrintPublisher`` instead.
"""

from __future__ import annotations

import json
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


class PrinterError(RuntimeError):
    """Raised when the synchronous badge printer does not complete a job."""


class SynchronousPrinterClient:
    def __init__(self, printer_url: str, timeout: float = 5.0) -> None:
        self.printer_url = printer_url
        self.timeout = timeout

    def print_badge(self, attendee: dict) -> str:
        body = json.dumps(
            {
                "attendee_id": attendee["attendee_id"],
                "attendee_name": attendee["name"],
            }
        ).encode("utf-8")
        request = Request(
            self.printer_url,
            data=body,
            method="POST",
            headers={"Content-Type": "application/json"},
        )

        try:
            with urlopen(request, timeout=self.timeout) as response:
                payload = json.load(response)
        except (HTTPError, URLError, TimeoutError) as error:
            raise PrinterError("badge printer is unavailable") from error
        except json.JSONDecodeError as error:
            raise PrinterError("badge printer returned invalid JSON") from error

        if payload.get("status") != "printed" or not payload.get("print_job_id"):
            raise PrinterError("badge printer did not confirm completion")

        return str(payload["print_job_id"])
