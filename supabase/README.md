# Supabase migration target

The SQLite backend remains the local reference implementation. This directory defines the cloud target.

Principles:
- Every operational row is scoped by `property_id`.
- Property websites are separate deployable packages.
- The management dashboard is shared.
- Authentication and Row Level Security are mandatory before production.
- Stripe and outbound email remain intentionally excluded from this release.
