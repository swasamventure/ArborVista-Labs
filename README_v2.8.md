# Arbor Vista Retreat v2.8 — Thorough QA Release

This release hardens the existing v2.7.2 website and expands the local iCal/database prototype. It is intended for development and testing before real Airbnb or Vrbo calendar URLs are connected.

## What is included

### Website

- Existing public pages and guest-portal preview
- Four-step Book Direct workflow
- Clickable progress steps
- 24-hour draft autosave and restore
- Start Over that fully clears the saved draft
- Flexible occupancy requests: standard setup sleeps six; groups of seven or eight can be submitted for host approval
- Configurable request ceiling: eight guests total
- Mobile-phone validation
- Electronic signature/name matching
- Safe text rendering in review and guest-preview pages
- Gate-pass demo form with saved consent
- Mobile menu accessibility state

### Reservation engine

- SQLite development database
- Airbnb and Vrbo fixture imports
- Idempotent synchronization by source and UID
- Updated reservation reconciliation
- Explicit `STATUS:CANCELLED` handling
- Missing-event cancellation reconciliation
- Direct booking conflict checks
- Concurrent duplicate-request protection
- Owner blocks
- Audit logs and sync-run logs
- Database health checks
- Generic and channel-specific outbound ICS files
- Optional HTTPS feed download command for later real-feed testing

## Run all automated QA

```bash
python QA/run_all_qa.py
```

Individual suites:

```bash
python Backend/run_qa.py
python QA/run_web_qa.py
```

Expected result:

- Database/iCal: 33 of 33 PASS
- Website/workflow: 42 of 42 PASS
- Combined: 75 of 75 PASS

## Important deployment warning

The public website is still static. It is **not yet connected** to the SQLite database, and it does not yet check live channel availability when a guest submits the website form.

Do not publish the development database, real guest data, or private Airbnb/Vrbo feed URLs in a public GitHub repository.
