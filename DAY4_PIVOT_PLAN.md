# Day 4 Pivot Plan: Asynchronous Badge Printing

**Learner:** Morinke Julius  
**Date:** 21/08/2026  
**Branch:** `day4/async-message-queue-pivot`

## Non-negotiable client change

The badge-printer vendor is deprecating its synchronous REST API. The kiosk
must publish print requests to a message queue and expose a webhook that the
vendor calls after printing completes. The deadline does not change.

## New technology

**RabbitMQ** is the message broker. The kiosk will publish a print-job message
to a durable RabbitMQ queue instead of waiting for an immediate printer REST
response.

## Scope delta

### Dropped

- The active synchronous REST call from the kiosk to the printer.
- The assumption that a scan can immediately display `CHECKED_IN`.

### Modified

- Check-in status flow changes from `REGISTERED → PRINTING → CHECKED_IN` to
  `REGISTERED → PENDING → CHECKED_IN`.
- Duplicate-scan protection must hold while a job is pending, not only after
  check-in completes.
- Printer failures are handled outside the original scan request.

### Added

- A RabbitMQ print-request publisher.
- A simulated vendor queue consumer.
- A signed webhook endpoint for print-completion callbacks.
- Webhook event idempotency for repeated or out-of-order callbacks.
- A visible `PENDING` state in the kiosk UI.

## Granular task breakdown

| Task | Estimate | Definition of Done |
| --- | ---: | --- |
| Record scope delta and architecture | 45 min | Dropped, modified, and added behavior is documented. |
| Install and verify RabbitMQ | 45 min | Broker accepts a local connection and queue declaration. |
| Refactor persistence for pending jobs | 1 hr | One attendee can have only one active print job. |
| Publish print requests | 1 hr | A scan returns `PENDING` after one durable message is queued. |
| Build vendor queue worker | 1.5 hrs | Worker consumes a job and sends a completion webhook. |
| Verify webhook callbacks | 1.5 hrs | Only a valid signed callback completes the matching job. |
| Protect duplicates and ordering | 1.5 hrs | Duplicate scans/callbacks and stale callbacks do not print or check in twice. |
| Update UI and regression tests | 1.5 hrs | UI shows pending and all new and retained requirements pass tests. |

Every task is below the four-hour anti-black-box limit.

## Target workflow

1. Staff scan a registered attendee.
2. The kiosk creates a unique print job and marks the attendee `PENDING`.
3. The kiosk publishes the job to RabbitMQ and responds without waiting for
   badge printing.
4. The vendor worker consumes and prints the badge.
5. The vendor sends a signed completion callback to the kiosk webhook.
6. The kiosk matches the callback to the active job and marks the attendee
   `CHECKED_IN`.
7. Duplicate scans and repeated or stale callbacks do not produce another
   badge or overwrite newer state.

## Rollback safety

If queue publishing fails during a scan, the attendee returns to `REGISTERED`
instead of becoming stuck in `PENDING`. The old synchronous files remain only
as the historical Day 3 baseline and will not be called by the Day 4 runtime.
