# Arbor Vista Retreat v3.2 Merged QA Report

## Scope
Merged planned work from v2.9 through v3.2 into one test build.

Included:
- Local API-backed direct booking requests
- Availability and overlap checks
- Reservation approval, decline, and cancellation controls
- Owner blocks
- Airbnb and Vrbo iCal source settings and manual sync
- Generic and channel-specific outbound iCal feeds
- Admin dashboard, reservations, calendar, settings, sync logs, and audit logs
- Guest/contact and signed rental-agreement records
- Four charcoal-black kitchen WebP images

Explicitly excluded:
- Stripe and all payment functionality
- Cloudflare Email Routing setup
- Resend, SMTP, or any outbound email generation/delivery
- Production-grade authentication

## Automated results
- Existing database/iCal engine regression suite: 33/33 passed
- v3.2 structure and scope suite: 15/15 passed
- v3.2 booking/database integration suite: 10/10 passed
- Local HTTP/API smoke checks: health, availability, and admin page passed

## Important deployment limitation
GitHub Pages can serve the static public and admin pages, but it cannot run the included Python/SQLite API. Run `python Backend/server.py` for local testing. A hosted backend migration remains necessary before production use.

## Known QA note
The legacy v2.8 Playwright browser suite needs revision for the new API-first async booking workflow and is not counted in the v3.2 pass total.
