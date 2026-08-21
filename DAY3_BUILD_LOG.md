# Day 3 Build Log: Synchronous Check-in Baseline

**Learner:** Morinke Julius  
**Date:** 21/08/2026  
**Branch:** `day3/synchronous-checkin-baseline`

## Original workflow implemented

1. Staff scan an attendee ID at the kiosk.
2. The kiosk confirms that the attendee is registered.
3. The attendee is atomically moved to `PRINTING` to block a second scan.
4. The kiosk calls the simulated badge-printer REST API synchronously.
5. The kiosk waits for the printer's success response.
6. Only after success, the attendee becomes `CHECKED_IN`.
7. If printing fails, the attendee returns to `REGISTERED` and may be retried.

## Test attendees

| Attendee ID | Name |
| --- | --- |
| SOL-001 | Amina Njeri |
| SOL-002 | David Ochieng |
| SOL-003 | Grace Wanjiku |

## Evidence collected

Automated test command:

```bash
python3 -W error::ResourceWarning -m unittest -v
```

Result on 21/08/2026: **4 tests passed**.

- Three required attendees were seeded.
- A successful printer response changed the attendee to `CHECKED_IN`.
- A duplicate scan did not send a second print request.
- A printer failure did not falsely mark the attendee as checked in.

Live demonstration using `SOL-001`:

- First scan: `badge_printed: true`, `duplicate: false`, status `CHECKED_IN`.
- Repeated scan: `badge_printed: false`, `duplicate: true`.
- The same `print_job_id` remained attached to the attendee.

## What the synchronous design means

The kiosk request stays open while the badge printer works. This makes the
status rule straightforward, but it tightly couples kiosk response time and
availability to the vendor's REST service. If the printer is slow or offline,
the kiosk must wait or fail.

## Expected impact of the Day 4 pivot

The synchronous printer call cannot remain as the active workflow. The kiosk
will need to publish a print request to a message queue, immediately show a
`PENDING` state, and expose a webhook that changes the attendee to
`CHECKED_IN` only after the vendor confirms completion. Duplicate protection
must continue working while a job is pending and when callbacks arrive out of
order.
