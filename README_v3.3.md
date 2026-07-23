# Arbor Vista v3.3 — Cloud-Ready Multi-Property Foundation

This release prepares the platform for a future move from GitHub/local hosting to cloud hosting without locking the project to one provider.

## Included
- Versioned `/api/v1` contract with backward-compatible `/api` routes
- Runtime frontend configuration
- Environment-driven backend configuration
- Property-scoped API requests
- Independent transferable property package
- Multi-property tables and access-role foundation
- Supabase/PostgreSQL migration starter
- Restricted configurable CORS
- Property-specific browser storage
- Existing booking, calendar, admin, iCal, and flexible eight-guest request behavior

## Deliberately excluded
- Stripe/payment processing
- Cloudflare/Resend outbound email generation
- Production authentication and live Row Level Security policies

## Local run
```bash
python Backend/server.py
```

Open:
- `http://localhost:8000/`
- `http://localhost:8000/admin/dashboard.html`

Environment settings are documented in `.env.example`.
