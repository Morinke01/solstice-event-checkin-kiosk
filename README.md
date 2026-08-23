# Solstice Event Check-in Kiosk

Solo implementation of the Meridian Pivot simulation for Solstice Events Co.

## Current phase

Day 4 asynchronous pivot implementation is on
`day4/async-message-queue-pivot`. It uses RabbitMQ to queue badge requests and
a signed webhook to confirm completed printing.

The original synchronous implementation is preserved on
`day3/synchronous-checkin-baseline`. See `DAY3_BASELINE_PLAN.md` and
`DAY3_BUILD_LOG.md` for its requirements and evidence.

## Run the Day 3 baseline

First check out `day3/synchronous-checkin-baseline`, then follow its README.

## Set up the Day 4 pivot

Install and start RabbitMQ in WSL:

```bash
sudo apt update
sudo apt install -y rabbitmq-server python3-venv
sudo service rabbitmq-server start
```

Create the isolated Python environment and install Pika:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
```

Verify that the project can publish exactly one message while blocking a
duplicate scan:

```bash
.venv/bin/python verify_queue.py
```

## Run the Day 4 pivot

Open two terminals after RabbitMQ is running.

Terminal 1 starts the asynchronous kiosk and webhook endpoint:

```bash
.venv/bin/python run_kiosk.py
```

Terminal 2 starts the simulated badge-printer vendor queue worker:

```bash
.venv/bin/python run_vendor_worker.py
```

Open <http://127.0.0.1:8080>. Scan `SOL-001`, `SOL-002`, or `SOL-003`.
The attendee first becomes `PENDING`, then becomes `CHECKED_IN` only after the
worker sends a valid signed completion webhook. A repeated scan does not queue
another badge.

Run all pivot and regression tests:

```bash
.venv/bin/python -W error::ResourceWarning -m unittest -v
```

## Day 4 architecture

```text
Browser scan
    │
    ▼
Kiosk API ──persistent message──▶ RabbitMQ queue
    │                                  │
    │ returns PENDING                  ▼
    │                            Vendor worker
    │                                  │
    ◀────────signed webhook────────────┘
    │
    ▼
CHECKED_IN
```

## Historical Day 3 commands

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

Run the Day 3 automated evidence checks with:

```bash
python3 -m unittest -v
```
