"""HTTP API and browser kiosk for the asynchronous Day 4 workflow."""

from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

from .attendees import AttendeeStore
from .checkin import AttendeeNotFoundError
from .queue import QueuePublishError
from .webhook import SIGNATURE_HEADER, WebhookService


KIOSK_HTML = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Solstice Check-in</title>
  <style>
    :root { color-scheme: dark; font-family: Inter, system-ui, sans-serif; }
    body { margin: 0; background: #08111f; color: #eef5ff; }
    main { width: min(900px, 92vw); margin: 50px auto; }
    h1 { font-size: clamp(2.2rem, 7vw, 4.5rem); margin-bottom: 8px; }
    .subtitle { color: #9eb0ca; margin-bottom: 32px; }
    .panel { background: #111f33; border: 1px solid #28405f; border-radius: 18px; padding: 24px; }
    .scan { display: flex; gap: 12px; flex-wrap: wrap; }
    input, button { font: inherit; border-radius: 10px; padding: 13px 16px; }
    input { flex: 1; min-width: 210px; border: 1px solid #426080; background: #091523; color: white; }
    button { border: 0; background: #59e3b3; color: #062117; font-weight: 800; cursor: pointer; }
    #result { min-height: 26px; margin: 18px 0; color: #8ff0cc; }
    .attendees { display: grid; gap: 12px; margin-top: 24px; }
    .attendee { display: flex; justify-content: space-between; gap: 16px; padding: 16px; background: #0a1727; border-radius: 12px; }
    .status { font-weight: 800; color: #ffd166; }
    .status.checked { color: #59e3b3; }
    .status.pending { color: #73b7ff; }
  </style>
</head>
<body>
<main>
  <p class="subtitle">SOLSTICE EVENTS CO. · STAFF KIOSK</p>
  <h1>Conference check-in</h1>
  <p class="subtitle">Scan once. Badge printing completes asynchronously.</p>
  <section class="panel">
    <form id="scan-form" class="scan">
      <input id="attendee-id" aria-label="Attendee ID" placeholder="Try SOL-001" required>
      <button type="submit">Scan attendee</button>
    </form>
    <p id="result" role="status"></p>
    <div id="attendees" class="attendees"></div>
  </section>
</main>
<script>
  const list = document.querySelector('#attendees');
  const result = document.querySelector('#result');
  let activeAttendeeId = null;
  async function refresh() {
    const response = await fetch('/api/attendees');
    const data = await response.json();
    list.innerHTML = data.attendees.map(a => `
      <div class="attendee">
        <span><strong>${a.name}</strong><br>${a.attendee_id}</span>
        <span class="status ${a.status === 'CHECKED_IN' ? 'checked' : a.status === 'PENDING' ? 'pending' : ''}">${a.status}</span>
      </div>`).join('');
    const activeAttendee = data.attendees.find(a => a.attendee_id === activeAttendeeId);
    if (activeAttendee?.status === 'CHECKED_IN' && result.dataset.waiting === 'true') {
      result.textContent = 'Badge printed successfully. Attendee is checked in.';
      result.dataset.waiting = 'false';
    }
  }
  document.querySelector('#scan-form').addEventListener('submit', async event => {
    event.preventDefault();
    result.textContent = 'Sending badge request…';
    const attendeeId = document.querySelector('#attendee-id').value.trim();
    activeAttendeeId = attendeeId;
    result.dataset.waiting = 'false';
    const response = await fetch('/api/scan', {
      method: 'POST', headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({attendee_id: attendeeId})
    });
    const data = await response.json();
    result.textContent = data.message || data.error;
    result.dataset.waiting = String(data.attendee?.status === 'PENDING');
    await refresh();
  });
  refresh();
  setInterval(refresh, 1000);
</script>
</body>
</html>
"""


def create_handler(store: AttendeeStore, check_in, webhook: WebhookService):
    class KioskHandler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            path = urlparse(self.path).path
            if path == "/":
                self._send_html(200, KIOSK_HTML)
                return
            if path == "/health":
                self._send_json(200, {"status": "ok", "print_mode": "asynchronous"})
                return
            if path == "/api/attendees":
                self._send_json(200, {"attendees": store.list_attendees()})
                return
            if path.startswith("/api/attendees/"):
                attendee_id = path.removeprefix("/api/attendees/")
                attendee = store.get_attendee(attendee_id)
                if attendee is None:
                    self._send_json(404, {"error": "attendee not found"})
                    return
                self._send_json(200, attendee)
                return
            self._send_json(404, {"error": "endpoint not found"})

        def do_POST(self) -> None:
            path = urlparse(self.path).path
            if path == "/webhooks/badge-printed":
                self._handle_webhook()
                return
            if path != "/api/scan":
                self._send_json(404, {"error": "endpoint not found"})
                return

            try:
                length = int(self.headers.get("Content-Length", "0"))
                payload = json.loads(self.rfile.read(length))
            except (ValueError, json.JSONDecodeError):
                self._send_json(400, {"error": "valid JSON body is required"})
                return

            attendee_id = payload.get("attendee_id")
            if not isinstance(attendee_id, str) or not attendee_id.strip():
                self._send_json(422, {"error": "attendee_id is required"})
                return

            try:
                result = check_in.scan(attendee_id.strip())
            except AttendeeNotFoundError as error:
                self._send_json(404, {"error": str(error)})
                return
            except QueuePublishError as error:
                self._send_json(503, {"error": str(error)})
                return

            self._send_json(202 if result["queued"] else 200, result)

        def _handle_webhook(self) -> None:
            try:
                length = int(self.headers.get("Content-Length", "0"))
                body = self.rfile.read(length)
                payload = json.loads(body)
            except (ValueError, json.JSONDecodeError):
                self._send_json(400, {"error": "valid JSON body is required"})
                return

            required = ("event_id", "attendee_id", "print_job_id")
            if any(not isinstance(payload.get(field), str) for field in required):
                self._send_json(422, {"error": "webhook payload is incomplete"})
                return

            try:
                result = webhook.process(
                    body,
                    self.headers.get(SIGNATURE_HEADER, ""),
                    payload,
                )
            except PermissionError as error:
                self._send_json(401, {"error": str(error)})
                return

            self._send_json(200, result)

        def _send_json(self, status: int, payload: dict) -> None:
            body = json.dumps(payload).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _send_html(self, status: int, html: str) -> None:
            body = html.encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, format: str, *args) -> None:
            print(f"Kiosk: {format % args}")

    return KioskHandler


def create_server(
    store: AttendeeStore,
    check_in,
    webhook: WebhookService,
    host: str,
    port: int,
) -> ThreadingHTTPServer:
    return ThreadingHTTPServer((host, port), create_handler(store, check_in, webhook))
