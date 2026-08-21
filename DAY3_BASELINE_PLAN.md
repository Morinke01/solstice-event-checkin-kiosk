# Day 3: Synchronous Check-in Baseline Plan

**Learner:** Morinke Julius  
**Client:** Solstice Events Co.  
**Branch:** `day3/synchronous-checkin-baseline`  
**Date:** 21/08/2026

## Original workflow

```text
Staff scans attendee code
          |
          v
Kiosk validates attendee and duplicate status
          |
          v
Kiosk calls badge-printer REST API and waits
          |
          v
Printer returns success
          |
          v
Kiosk marks attendee CHECKED_IN
```

## Test attendees

| Attendee ID | Name | Initial status |
|---|---|---|
| `SOL-001` | Amina Njeri | `REGISTERED` |
| `SOL-002` | David Ochieng | `REGISTERED` |
| `SOL-003` | Grace Wanjiku | `REGISTERED` |

## Task breakdown

| Task | Priority | Estimate | Definition of Done |
|---|---|---:|---|
| Create attendee store | P0 | 45 min | Three attendees can be retrieved by ID |
| Build mock printer REST API | P0 | 45 min | A print request returns a successful job response |
| Build synchronous printer client | P0 | 45 min | Kiosk waits for and reads the printer response |
| Build scan endpoint | P0 | 60 min | Valid scan prints before returning `CHECKED_IN` |
| Add duplicate-scan protection | P0 | 45 min | Repeated checked-in scan creates no second print job |
| Add status endpoint | P1 | 30 min | Current attendee state can be queried |
| Add automated tests | P0 | 60 min | Three attendees and duplicate behavior are covered |
| Document and demonstrate | P1 | 30 min | Another user can run the baseline end to end |

Every task is under four hours and has one checkable completion condition.

## Definition of Done

The Day 3 baseline is complete when:

1. At least three attendees can be scanned.
2. Each first scan causes one synchronous printer request.
3. The scan waits for the printer success response.
4. `CHECKED_IN` is returned only after printing succeeds.
5. A duplicate scan does not create a second badge.
6. Automated and live end-to-end checks pass.

## Expected Day 4 impact

The synchronous printer call will later be replaced by a message-queue
publisher. The attendee will first enter `PRINT_PENDING`, and a printer webhook
will be required before the final `CHECKED_IN` state is shown.
