# Known Limitations — v4.1

1. The bundled backend uses SQLite and is intended for local development and QA only.
2. The dashboard login uses demo users through the `X-Demo-User` header; hosted Supabase Auth is not active yet.
3. The Supabase migrations define the cloud target, but they have not been deployed to a hosted Supabase project in this package.
4. Calendar synchronization is manual. There is no hosted scheduler, retry queue, monitoring, or alerting yet.
5. Real Airbnb and Vrbo feed URLs are intentionally not included and have not been exercised by the packaged QA.
6. The shared cleaning iCal uses a public demo token only for local testing. Production must use a private, revocable token over HTTPS.
7. Guest names are excluded from the cleaning calendar. Guest counts depend on the source data; Airbnb/Vrbo iCal feeds may not provide counts.
8. The guest portal remains a browser/local preview rather than a production authenticated portal.
9. Stripe, payment processing, refunds, and outbound email delivery remain excluded.
10. Production deployment still requires HTTPS, secrets management, rate limiting, database backups, monitoring, privacy controls, and final Row Level Security validation.
