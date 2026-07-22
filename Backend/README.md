# Arbor Vista v2.8 Local Calendar Engine

This folder is a standard-library-only development prototype for calendar import, reservation conflict checking, owner blocks, direct booking requests, cancellation reconciliation, audit logging, and outbound ICS generation.

## Automated QA

```bash
python run_qa.py
```

The suite creates temporary databases and does not alter the packaged sample database. It covers 33 scenarios, including duplicates, updates, cancellations, missing events, malformed feeds, concurrent booking attempts, export filtering, and database integrity.

## Rebuild the packaged sample database

```bash
python ical_db.py --db arborvista_ical_test.db init --reset
python ical_db.py --db arborvista_ical_test.db sync src_airbnb fixtures/airbnb_sample.ics
python ical_db.py --db arborvista_ical_test.db sync src_vrbo fixtures/vrbo_sample.ics
python ical_db.py --db arborvista_ical_test.db health
```

## Availability check

Dates use half-open `[check-in, check-out)` semantics.

```bash
python ical_db.py --db arborvista_ical_test.db check 2026-09-05 2026-09-07
```

## Create and cancel a direct request

```bash
python ical_db.py --db arborvista_ical_test.db request 2026-11-01 2026-11-05 "Test Guest"
python ical_db.py --db arborvista_ical_test.db cancel RESERVATION_ID
```

## Owner block

```bash
python ical_db.py --db arborvista_ical_test.db block 2026-11-15 2026-11-18 "Owner stay"
```

## Outbound calendars

Generic export:

```bash
python ical_db.py --db arborvista_ical_test.db export exports/arbor-vista-all.ics
```

Airbnb-targeted export excludes reservations imported from Airbnb:

```bash
python ical_db.py --db arborvista_ical_test.db export exports/arbor-vista-for-airbnb.ics --exclude-source airbnb
```

Vrbo-targeted export excludes reservations imported from Vrbo:

```bash
python ical_db.py --db arborvista_ical_test.db export exports/arbor-vista-for-vrbo.ics --exclude-source vrbo
```

Channel-specific exports reduce the risk of feeding a channel's own reservation back to that same channel.

## Test a real HTTPS calendar feed later

```bash
python ical_db.py --db arborvista_ical_test.db sync-url src_airbnb "PRIVATE_HTTPS_ICAL_URL"
```

Keep the URL private. This prototype has no scheduler, secret manager, admin authentication, or production API yet.
