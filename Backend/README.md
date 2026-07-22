# Arbor Vista v2.8 — Local iCal Database Test Harness

This folder is a safe, local prototype for Phase 1 calendar synchronization. It does **not** connect to Airbnb, Vrbo, Supabase, or the production website.

## What it tests

- SQLite schema for properties, calendar sources, reservations, owner blocks, sync runs, and audit logs
- Airbnb-style and Vrbo-style `.ics` imports
- Idempotent re-sync using `calendar_source_id + external_uid`
- Date-overlap conflict detection using half-open stays: check-in is occupied; checkout is available
- Direct booking request creation
- Owner blocks
- Outbound Arbor Vista `.ics` generation

## Run

From the `Backend` folder:

```bash
python run_qa.py
```

The QA script resets and rebuilds `arborvista_ical_test.db`, imports both fixtures, tests conflicts, inserts one direct request, exports `exports/arbor-vista.ics`, and writes the database QA reports in the project root.

## Useful commands

```bash
python ical_db.py init --reset
python ical_db.py sync src_airbnb fixtures/airbnb_sample.ics
python ical_db.py sync src_vrbo fixtures/vrbo_sample.ics
python ical_db.py check 2026-09-05 2026-09-07
python ical_db.py request 2026-09-22 2026-09-25 "Test Guest"
python ical_db.py export exports/arbor-vista.ics
```

## Production boundary

GitHub Pages cannot access this SQLite database. The production phase should migrate the same logical schema to Supabase/PostgreSQL and expose availability through authenticated/server-side endpoints. Real Airbnb/Vrbo feed URLs must be stored as secrets and never committed to GitHub.
