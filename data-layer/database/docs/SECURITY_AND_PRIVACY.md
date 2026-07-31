# Security and privacy requirements

## Encryption in transit

- Require TLS for browser-to-backend and backend-to-database connections.
- Reject plaintext database connections outside local development.
- Use HSTS and secure cookies for authenticated portals.

## Encryption at rest

- Use provider-managed disk/database encryption.
- Encrypt guest PII, exact addresses when treated as private, integration secrets, access codes, agreement signatures, and private chatbot content at the application layer.
- Store encryption keys only in AWS KMS/Secrets Manager, Azure Key Vault, Supabase/Vault-compatible secret storage, or the selected deployment secret manager.
- Never store the plaintext encryption key in PostgreSQL, GitHub, container images, logs, or browser code.

## Lookup hashes

Use a keyed HMAC for email/phone/token lookup hashes. A plain SHA-256 hash of predictable PII is not sufficient. Rotate the HMAC key with a documented migration process.

## Least privilege

- Static website: no database credentials.
- Backend: dedicated application role.
- Migration pipeline: separate migration role.
- Reporting: read-only API views or reporting role.
- Cleaner feed: backend verifies a revocable token and returns only cleaning-safe fields.

## Logging

Do not log raw guest names, email, phone, access codes, iCal feed URLs, API keys, agreement signatures, or full chatbot messages. Use request IDs, entity IDs, redacted summaries, and error codes.

## Retention

The seed provides starting retention categories, not legal advice. Review retention periods with counsel and the actual operational requirements before production launch.
