# Arbor Vista Platform v4.1 — Local Reference Backend

This standard-library Python/SQLite backend supports local development and QA for the shared multi-property platform.

## Included
- Property-scoped reservations and availability
- Airbnb/Vrbo iCal import and reconciliation
- Owner blocks and conflict prevention
- Combined portfolio calendar
- Token-protected cleaning iCal
- Local demo users and role enforcement
- Portfolio/property reporting
- Privacy-filtered property transfer export
- Audit and sync logs

The cleaning feed includes property identity, arrival/departure timing and guest count, but excludes guest names and contact information.

## Run
```bash
python Backend/server.py
```

## Full QA
```bash
python QA/run_all_qa.py
```

## Production boundary
SQLite and the `X-Demo-User` login simulation are for local development only. The `supabase/` migrations define the hosted PostgreSQL/Auth/RLS target. Do not commit real calendar URLs, guest data, production tokens, or secrets to a public repository.
