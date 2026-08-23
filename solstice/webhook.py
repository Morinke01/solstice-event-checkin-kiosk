"""Signature verification and processing for printer completion webhooks."""

from __future__ import annotations

import hashlib
import hmac

from .attendees import AttendeeStore


SIGNATURE_HEADER = "X-Solstice-Signature"


def create_signature(body: bytes, secret: str) -> str:
    return hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()


def signature_is_valid(body: bytes, supplied_signature: str, secret: str) -> bool:
    expected = create_signature(body, secret)
    return hmac.compare_digest(expected, supplied_signature)


class WebhookService:
    def __init__(self, store: AttendeeStore, secret: str) -> None:
        self.store = store
        self.secret = secret

    def process(self, body: bytes, supplied_signature: str, payload: dict) -> dict:
        if not signature_is_valid(body, supplied_signature, self.secret):
            raise PermissionError("webhook signature is invalid")

        return self.store.complete_async_print(
            event_id=payload["event_id"],
            attendee_id=payload["attendee_id"],
            print_job_id=payload["print_job_id"],
        )
