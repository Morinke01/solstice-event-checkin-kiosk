"""Tests for the Day 4 RabbitMQ and webhook pivot behavior."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from solstice.async_checkin import AsyncCheckInService
from solstice.attendees import AttendeeStore
from solstice.queue import QueuePublishError
from solstice.webhook import WebhookService, create_signature


class RecordingPublisher:
    def __init__(self, should_fail: bool = False) -> None:
        self.should_fail = should_fail
        self.messages: list[dict] = []

    def publish(self, message: dict) -> None:
        if self.should_fail:
            raise QueuePublishError("print request could not be queued")
        self.messages.append(message)


class AsyncCheckInTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        database = Path(self.temporary_directory.name) / "solstice-test.db"
        self.store = AttendeeStore(database)
        self.publisher = RecordingPublisher()
        self.service = AsyncCheckInService(self.store, self.publisher)
        self.webhook = WebhookService(self.store, "test-secret")

    def tearDown(self) -> None:
        self.temporary_directory.cleanup()

    def scan_and_job(self, attendee_id: str = "SOL-001") -> tuple[dict, dict]:
        result = self.service.scan(attendee_id)
        return result, self.publisher.messages[-1]

    def webhook_payload(self, job: dict, event_id: str = "event-001") -> tuple[bytes, dict]:
        payload = {
            "event_id": event_id,
            "attendee_id": job["attendee_id"],
            "print_job_id": job["print_job_id"],
        }
        return json.dumps(payload).encode("utf-8"), payload

    def test_scan_becomes_pending_and_publishes_one_job(self) -> None:
        result, job = self.scan_and_job()

        self.assertEqual("PENDING", result["attendee"]["status"])
        self.assertTrue(result["queued"])
        self.assertEqual("SOL-001", job["attendee_id"])
        self.assertEqual(1, self.store.async_job_count("SOL-001"))

    def test_duplicate_scan_while_pending_does_not_publish_again(self) -> None:
        self.service.scan("SOL-002")
        duplicate = self.service.scan("SOL-002")

        self.assertTrue(duplicate["duplicate"])
        self.assertFalse(duplicate["queued"])
        self.assertEqual(1, len(self.publisher.messages))
        self.assertEqual(1, self.store.async_job_count("SOL-002"))

    def test_publish_failure_returns_attendee_to_registered(self) -> None:
        service = AsyncCheckInService(self.store, RecordingPublisher(True))

        with self.assertRaises(QueuePublishError):
            service.scan("SOL-003")

        self.assertEqual("REGISTERED", self.store.get_attendee("SOL-003")["status"])
        self.assertEqual(0, self.store.async_job_count("SOL-003"))

    def test_valid_signed_callback_completes_check_in(self) -> None:
        _, job = self.scan_and_job()
        body, payload = self.webhook_payload(job)

        result = self.webhook.process(
            body,
            create_signature(body, "test-secret"),
            payload,
        )

        self.assertTrue(result["processed"])
        self.assertEqual("CHECKED_IN", self.store.get_attendee("SOL-001")["status"])

    def test_invalid_signature_cannot_complete_check_in(self) -> None:
        _, job = self.scan_and_job()
        body, payload = self.webhook_payload(job)

        with self.assertRaises(PermissionError):
            self.webhook.process(body, "forged-signature", payload)

        self.assertEqual("PENDING", self.store.get_attendee("SOL-001")["status"])

    def test_duplicate_callback_is_processed_only_once(self) -> None:
        _, job = self.scan_and_job()
        body, payload = self.webhook_payload(job)
        signature = create_signature(body, "test-secret")

        first = self.webhook.process(body, signature, payload)
        duplicate = self.webhook.process(body, signature, payload)

        self.assertTrue(first["processed"])
        self.assertTrue(duplicate["duplicate"])
        self.assertFalse(duplicate["processed"])

    def test_out_of_order_callback_for_wrong_job_is_ignored(self) -> None:
        _, job = self.scan_and_job()
        job["print_job_id"] = "job-stale"
        body, payload = self.webhook_payload(job, event_id="event-stale")

        result = self.webhook.process(
            body,
            create_signature(body, "test-secret"),
            payload,
        )

        self.assertTrue(result["stale"])
        self.assertFalse(result["processed"])
        self.assertEqual("PENDING", self.store.get_attendee("SOL-001")["status"])


if __name__ == "__main__":
    unittest.main()
