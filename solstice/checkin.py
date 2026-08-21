"""Original synchronous attendee check-in workflow."""

from __future__ import annotations

from .attendees import AttendeeStore
from .printer_client import PrinterError, SynchronousPrinterClient


class AttendeeNotFoundError(LookupError):
    """Raised when a scan does not match a registered attendee."""


class CheckInService:
    def __init__(
        self,
        store: AttendeeStore,
        printer: SynchronousPrinterClient,
    ) -> None:
        self.store = store
        self.printer = printer

    def scan(self, attendee_id: str) -> dict:
        attendee = self.store.get_attendee(attendee_id)
        if attendee is None:
            raise AttendeeNotFoundError(f"attendee {attendee_id} was not found")

        if attendee["status"] != "REGISTERED":
            return {
                "attendee": attendee,
                "duplicate": True,
                "badge_printed": False,
                "message": "Attendee scan already handled; no second badge printed.",
            }

        if not self.store.begin_printing(attendee_id):
            current = self.store.get_attendee(attendee_id)
            return {
                "attendee": current,
                "duplicate": True,
                "badge_printed": False,
                "message": "Attendee scan already in progress; no second badge printed.",
            }

        try:
            print_job_id = self.printer.print_badge(attendee)
        except PrinterError:
            self.store.reset_after_print_failure(attendee_id)
            raise

        self.store.complete_check_in(attendee_id, print_job_id)
        checked_in = self.store.get_attendee(attendee_id)
        return {
            "attendee": checked_in,
            "duplicate": False,
            "badge_printed": True,
            "message": "Badge printed successfully. Attendee is checked in.",
        }
