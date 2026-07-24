# Arbor Vista Platform v4.1 — Multi-Property Operations

This Git/local build implements features 1–7 requested for the shared STR platform while keeping each property website independently transferable.

## Implemented
1. Multi-property database design
2. Central dashboard
3. Reservation engine
4. Calendar engine
5. Local role simulation plus Supabase Auth/RLS migration target
6. Portfolio/property reporting
7. Privacy-filtered property transfer package

The common cleaning iCal contains property name, code, internal property ID, arrival/departure timing, guest count, source, reservation reference, cleaning window, and turnover indicators. **Guest names are not included.**

## Run locally
```bash
python Backend/server.py
```

Open:
- Public property website: `http://localhost:8000/`
- Central dashboard: `http://localhost:8000/admin/login.html`
- Demo cleaning feed: `http://localhost:8000/api/v1/ical/cleaning.ics?token=demo-cleaner-token-change-me`

## QA
```bash
python QA/run_v41_qa.py
```

## Deliberately excluded
- Stripe and payment processing
- Outbound email generation/delivery
- Live hosted Supabase authentication
- Production scheduler, monitoring, and secrets infrastructure

The local SQLite API is a reference implementation. Before collecting real guest data, deploy the PostgreSQL/Supabase target, enable authentication and Row Level Security, store secrets outside Git, use HTTPS, and configure backups and monitoring.
