"""Tests for the Day 3 synchronous Solstice check-in baseline."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from solstice.attendees import AttendeeStore
from solstice.checkin import CheckInService
from solstice.printer_client import PrinterError


class RecordingPrinter:
    def __init__(self, should_fail: bool = False) -> None:
        self.should_fail = should_fail
        self.calls: list[str] = []

    def print_badge(self, attendee: dict) -> str:
        self.calls.append(attendee["attendee_id"])
        if self.should_fail:
            raise PrinterError("badge printer is unavailable")
        return f"print-{attendee['attendee_id']}"


class SynchronousCheckInTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        database = Path(self.temporary_directory.name) / "solstice-test.db"
        self.store = AttendeeStore(database)

    def tearDown(self) -> None:
        self.temporary_directory.cleanup()

    def test_three_required_attendees_are_available(self) -> None:
        attendees = self.store.list_attendees()

        self.assertEqual(3, len(attendees))
        self.assertEqual(
            ["SOL-001", "SOL-002", "SOL-003"],
            [attendee["attendee_id"] for attendee in attendees],
        )

    def test_successful_print_marks_attendee_checked_in(self) -> None:
        printer = RecordingPrinter()
        service = CheckInService(self.store, printer)

        result = service.scan("SOL-001")

        self.assertTrue(result["badge_printed"])
        self.assertEqual("CHECKED_IN", result["attendee"]["status"])
        self.assertEqual(["SOL-001"], printer.calls)
        self.assertEqual(1, self.store.print_attempt_count("SOL-001"))

    def test_duplicate_scan_does_not_print_a_second_badge(self) -> None:
        printer = RecordingPrinter()
        service = CheckInService(self.store, printer)

        first_result = service.scan("SOL-002")
        duplicate_result = service.scan("SOL-002")

        self.assertFalse(first_result["duplicate"])
        self.assertTrue(duplicate_result["duplicate"])
        self.assertFalse(duplicate_result["badge_printed"])
        self.assertEqual(["SOL-002"], printer.calls)
        self.assertEqual(1, self.store.print_attempt_count("SOL-002"))

    def test_printer_failure_does_not_mark_attendee_checked_in(self) -> None:
        printer = RecordingPrinter(should_fail=True)
        service = CheckInService(self.store, printer)

        with self.assertRaises(PrinterError):
            service.scan("SOL-003")

        attendee = self.store.get_attendee("SOL-003")
        self.assertEqual("REGISTERED", attendee["status"])
        self.assertIsNone(attendee["checked_in_at"])
        self.assertEqual(0, self.store.print_attempt_count("SOL-003"))


if __name__ == "__main__":
    unittest.main()
