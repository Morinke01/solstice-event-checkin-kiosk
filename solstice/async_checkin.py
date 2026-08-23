"""Day 4 asynchronous attendee check-in workflow."""

from __future__ import annotations

import uuid

from .attendees import AttendeeStore
from .checkin import AttendeeNotFoundError
from .queue import QueuePublishError


class AsyncCheckInService:
    def __init__(self, store: AttendeeStore, publisher) -> None:
        self.store = store
        self.publisher = publisher

    def scan(self, attendee_id: str) -> dict:
        attendee = self.store.get_attendee(attendee_id)
        if attendee is None:
            raise AttendeeNotFoundError(f"attendee {attendee_id} was not found")

        if attendee["status"] != "REGISTERED":
            return {
                "attendee": attendee,
                "duplicate": True,
                "queued": False,
                "message": "Attendee scan already handled; no second badge requested.",
            }

        print_job_id = f"job-{uuid.uuid4().hex}"
        if not self.store.begin_pending_print(attendee_id, print_job_id):
            return {
                "attendee": self.store.get_attendee(attendee_id),
                "duplicate": True,
                "queued": False,
                "message": "Attendee scan already in progress; no second badge requested.",
            }

        message = {
            "print_job_id": print_job_id,
            "attendee_id": attendee_id,
            "attendee_name": attendee["name"],
        }
        try:
            self.publisher.publish(message)
        except QueuePublishError:
            self.store.reset_after_publish_failure(attendee_id, print_job_id)
            raise

        pending = self.store.get_attendee(attendee_id)
        return {
            "attendee": pending,
            "duplicate": False,
            "queued": True,
            "message": "Badge request queued. Waiting for printer confirmation.",
        }
