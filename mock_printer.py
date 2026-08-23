"""DEPRECATED Day 3 synchronous badge-printer REST simulation.

The Day 4 runtime uses ``run_vendor_worker.py`` and RabbitMQ instead.
"""

from __future__ import annotations

import json
import time
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


class PrinterHandler(BaseHTTPRequestHandler):
    def do_POST(self) -> None:
        if self.path != "/print":
            self._send_json(404, {"error": "endpoint not found"})
            return

        try:
            content_length = int(self.headers.get("Content-Length", "0"))
            payload = json.loads(self.rfile.read(content_length))
        except (ValueError, json.JSONDecodeError):
            self._send_json(400, {"error": "valid JSON body is required"})
            return

        attendee_id = payload.get("attendee_id")
        attendee_name = payload.get("attendee_name")
        if not attendee_id or not attendee_name:
            self._send_json(422, {"error": "attendee_id and attendee_name are required"})
            return

        time.sleep(0.25)
        self._send_json(
            200,
            {
                "status": "printed",
                "print_job_id": f"print-{uuid.uuid4().hex[:10]}",
                "attendee_id": attendee_id,
            },
        )

    def _send_json(self, status: int, payload: dict) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args) -> None:
        print(f"Printer: {format % args}")


def main() -> None:
    server = ThreadingHTTPServer(("127.0.0.1", 9100), PrinterHandler)
    print("Synchronous printer API listening at http://127.0.0.1:9100/print")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("Stopping synchronous printer")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
