# Day 4 Pivot Log: RabbitMQ and Webhook Refactor

**Learner:** Morinke Julius  
**Date:** 21/08/2026  
**Branch:** `day4/async-message-queue-pivot`

## Pivot implementation completed

The kiosk no longer calls the badge printer synchronously. It now reserves an
attendee as `PENDING`, publishes one persistent message to RabbitMQ, and
returns control to the kiosk. A separate simulated vendor worker consumes the
message and sends a signed webhook after printing. Only that matching callback
changes the attendee to `CHECKED_IN`.

## New technology evidence

- RabbitMQ `4.0.5` installed and running locally.
- AMQP listener verified on port `5672`.
- Durable queue created: `solstice.badge_print_requests`.
- Pika `1.3.2` installed in the project `.venv`.
- `verify_queue.py` produced:

```text
first_status=PENDING
first_queued=true
duplicate=true
queue_messages=1
```

## End-to-end evidence

Live test with `SOL-001`:

```text
FirstResponseStatus : PENDING
FirstQueued         : True
DuplicateDetected   : True
DuplicateQueued     : False
FinalStatus         : CHECKED_IN
```

The UI was also corrected after observation: the attendee card initially
updated to `CHECKED_IN`, but the explanatory message still said it was waiting.
The refresh logic now changes both the attendee status and the message after
webhook completion.

## Regression check

Command:

```bash
.venv/bin/python -W error::ResourceWarning -m unittest -v
```

Result: **11 tests passed** — seven Day 4 pivot tests and four retained Day 3
tests.

The tests cover:

- Three required attendees.
- Pending state and durable queue publishing.
- Duplicate scan protection while pending.
- Rollback when queue publishing fails.
- Valid webhook completion.
- Invalid signature rejection.
- Duplicate webhook idempotency.
- Stale/out-of-order callback rejection.
- Original synchronous behavior as regression evidence.

## Architectural integrity

- Database reservation happens before publishing, preventing concurrent scans
  from creating two jobs.
- A failed publish removes the unfinished job and returns the attendee to
  `REGISTERED`.
- RabbitMQ messages are persistent and the queue is durable.
- The worker acknowledges a queue message only after the webhook succeeds.
- A callback must have a valid HMAC signature and match the attendee's current
  print job.
- Callback event IDs are stored so repeated deliveries are safe.

## Cost of the pivot

- Added RabbitMQ and Pika as operational dependencies.
- Added a vendor worker process and webhook secret configuration.
- Added more persistence state for jobs and webhook events.
- Increased test scope to cover failure, duplication, and message ordering.
- The UI required a pending state and background refresh rather than an
  immediate final response.

## Known limitations and follow-up work

- The prototype uses RabbitMQ's local `guest` account; production needs a
  dedicated least-privilege account and TLS.
- The demo webhook secret defaults to `demo-secret`; production must inject a
  strong secret through a secret manager.
- SQLite is appropriate for the solo MVP but a shared production deployment
  should use a transactional server database.
- The browser polls once per second; production could use server-sent events or
  WebSockets.
- Failed jobs are requeued immediately; production should add bounded retries,
  exponential backoff, and a dead-letter queue.
