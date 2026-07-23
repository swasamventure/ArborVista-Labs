# Arbor Vista Retreat v3.2 — Merged v2.9 through v3.2

This release combines the planned calendar, reservation, admin-dashboard, manual-blocking, direct-request, rental-agreement record, outbound-iCal, and local API work.

## Deliberately excluded
- Stripe/payment collection
- Cloudflare/Resend email generation or delivery
- Production authentication

## Run locally
```bash
python Backend/server.py
```
Open `http://localhost:8000/` and `http://localhost:8000/admin/dashboard.html`.

GitHub Pages can host the public/admin static pages, but the SQLite API only runs locally. Production deployment will require a hosted backend such as Supabase or another server environment.
