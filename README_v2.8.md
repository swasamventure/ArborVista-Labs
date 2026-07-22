# Arbor Vista Retreat v2.8 — iCal Database QA Build

This release extends v2.7.2 without rebuilding the public website. The existing website remains intact. A new `Backend/` test harness provides the first database foundation for iCal synchronization.

## Included

- Existing v2.7.2 public website and booking-form draft preservation
- SQLite test database: `Backend/arborvista_ical_test.db`
- Database schema and seed data
- Sample Airbnb and Vrbo `.ics` fixtures
- Import, conflict-checking, direct-request, and outbound-export commands
- Database QA automation and reports
- iCal integration test plan

## Start testing

```bash
cd Backend
python run_qa.py
```

This is a local development build. Do not upload the database, private calendar URLs, or real guest data to the public GitHub Pages repository.
