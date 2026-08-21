# Solstice Event Check-in Kiosk

Solo implementation of the Meridian Pivot simulation for Solstice Events Co.

## Current phase

Day 3 synchronous baseline implementation is in progress on the
`day3/synchronous-checkin-baseline` branch.

The baseline will scan an attendee, call a badge-printer REST API
synchronously, wait for printing to finish, and show `CHECKED_IN` only after a
successful print response.

See `DAY3_BASELINE_PLAN.md` for the original requirements, task breakdown, and
Definition of Done.

## Run the Day 3 baseline

Open two terminals in this repository.

Terminal 1 starts the simulated badge-printer vendor:

```bash
python3 mock_printer.py
```

Terminal 2 starts the check-in kiosk:

```bash
python3 run_kiosk.py
```

Then open <http://127.0.0.1:8080> and scan `SOL-001`, `SOL-002`, or
`SOL-003`. A repeated scan must not print a second badge.

Run the automated evidence checks with:

```bash
python3 -m unittest -v
```
