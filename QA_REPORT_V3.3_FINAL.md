# Arbor Vista Retreat v3.3 — Final QA Report

**Release:** Cloud-Ready Multi-Property Foundation  
**Overall status:** PASS  
**Automated checks:** 124/124 passed

## Results

| Suite | Passed | Total | Status |
|---|---:|---:|---|
| Cloud architecture | 24 | 24 | PASS |
| Database and iCal regression | 33 | 33 | PASS |
| v3.2 merged regression | 15 | 15 | PASS |
| Booking/database integration | 10 | 10 | PASS |
| Website and browser regression | 42 | 42 | PASS |

## Cloud-readiness improvements

- Frontend API location is controlled through `config/runtime-config.js`.
- Backend host, port, database path, default property, and CORS origins are environment-driven.
- API contract is versioned under `/api/v1`.
- Legacy `/api` routes remain available for migration compatibility.
- Requests carry a property slug and backend queries are property scoped.
- Browser draft and request storage can be isolated by property.
- Independent property package added under `properties/arbor-vista-retreat/`.
- Multi-property domain and member-role tables added to the local schema.
- PostgreSQL/Supabase migration starter included.
- Wildcard CORS was removed.
- Existing charcoal kitchen images and flexible occupancy request rules remain intact.

## Deliberately excluded

- Stripe and all payment processing
- Cloudflare/Resend/SMTP outbound email delivery
- Production authentication
- Live Supabase deployment and finalized Row Level Security policies

## Production warning

The bundled SQLite server remains a local reference backend. Before accepting real guest information, deploy the database and APIs to a secured cloud environment, enable authentication, configure Row Level Security, HTTPS, secrets management, backups, monitoring, and privacy controls.
