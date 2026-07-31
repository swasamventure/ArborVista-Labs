# Arbor Vista Platform Database v1.0

Portable PostgreSQL data layer for the Arbor Vista / Swasam Venture platform.

## Design goals

- Multi-property by default; every operational record is property-scoped.
- Modular schemas for identity, secure data, booking/calendar, messaging, market intelligence, AI, and analytics.
- Public website remains statically deployable; all private operations use backend APIs.
- Cloud-neutral PostgreSQL core with an optional Supabase authentication adapter.
- Application-layer encryption placeholders for personal data and integration secrets.
- Transaction-safe availability checks using property-scoped advisory locks.
- Provider-neutral email, market-data, and AI integration tables.
- Technical and business observability without storing raw IP addresses.
- Simple modular-monolith deployment now, independently separable components later.

## Package layout

```text
migrations/             Portable PostgreSQL schema migrations
seed/                   Arbor Vista base seed and 83 public comparable listings
tests/                  SQL smoke, business-rule, security, and seed tests
scripts/                Migration, seed, test, reset, and backup helpers
supabase/               Optional Supabase Auth adapter and RLS integration
deploy/                 Example database roles and single-host Docker assets
docs/                   Architecture, ERD, data dictionary, security, and operations
.github/workflows/      PostgreSQL CI workflow
dist/bootstrap.sql      Consolidated portable schema
```

## Local start

```bash
cp .env.example .env
docker compose up -d
```

On the first database initialization, Docker applies the consolidated schema and both seed files automatically.

For an existing database:

```bash
./scripts/migrate.sh
./scripts/seed.sh
./scripts/test.sh
```

## Default local connection

```text
Host: localhost
Port: 5432
Database: arbor_vista
User: arbor_app
```

Never use the example password in production. Production credentials, encryption keys, API keys, private iCal URLs, and email-provider credentials must be stored in the selected cloud secret manager.

## Deployment targets

The core SQL is PostgreSQL-compatible and is intended to support:

- A PostgreSQL container on a single development host
- AWS-managed PostgreSQL
- Azure-managed PostgreSQL
- Supabase PostgreSQL using the optional adapter
- GitHub Actions for migration and regression testing

The database should normally run as a managed service or dedicated process in production. The UI, backend, and data-layer code remain logically separated even when initially deployed together on one host/task.

The seed uses the logical recipient alias `owner_primary`. During email-adapter implementation, the backend must resolve that alias from encrypted configuration/secret management to `swasam.venture@gmail.com`; the plaintext owner address is intentionally not placed in the public seed SQL.

## Security model

Sensitive values are represented as ciphertext plus one-way lookup hashes. Encryption and decryption occur in the backend with a cloud-managed key. The database never stores the plaintext encryption key.

See `docs/SECURITY_AND_PRIVACY.md` before loading real guest information.
