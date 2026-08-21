"""Start the original synchronous Solstice check-in kiosk."""

from __future__ import annotations

import argparse
from pathlib import Path

from solstice.api import create_server
from solstice.attendees import AttendeeStore
from solstice.checkin import CheckInService
from solstice.printer_client import SynchronousPrinterClient


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the Solstice check-in kiosk.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", default=8080, type=int)
    parser.add_argument("--printer-url", default="http://127.0.0.1:9100/print")
    parser.add_argument("--database", default="data/solstice.db")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    database_path = Path(args.database)
    database_path.parent.mkdir(parents=True, exist_ok=True)

    store = AttendeeStore(database_path)
    printer = SynchronousPrinterClient(args.printer_url)
    check_in = CheckInService(store, printer)
    server = create_server(store, check_in, args.host, args.port)

    print(f"Solstice kiosk listening at http://{args.host}:{args.port}")
    print(f"Waiting synchronously for printer at {args.printer_url}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("Stopping Solstice kiosk")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
