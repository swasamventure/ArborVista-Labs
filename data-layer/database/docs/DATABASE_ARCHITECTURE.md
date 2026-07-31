# Database architecture

## Logical boundaries

| Schema | Responsibility |
|---|---|
| `app` | Organizations, users, properties, memberships, settings, audit, exports, retention |
| `secure` | Encrypted PII, exact address, integration credentials, access tokens, access codes |
| `booking` | Reservations, blocks, quotes, booking requests, agreements, calendars, cleaning |
| `messaging` | Email adapter configuration, templates, outbox, delivery attempts, contact requests |
| `market` | Comparable properties, public snapshots, recurring rates, licensed-provider metrics |
| `ai` | Bot configuration, approved knowledge, conversations, tools, escalation, cost |
| `analytics` | Website visits, journey events, business metrics, service health, latency |
| `api` | Deliberately limited public/reporting views and token-verified cleaning function |

## Initial deployment

All packages can initially run on one host/task to keep cost and maintenance low. The boundaries are preserved so the static UI can later move to object storage/CDN, the backend to a container service, and PostgreSQL to a managed database without changing the logical data model.

## Multi-property rule

Operational data is tied directly or indirectly to `property_id`. Property export jobs can therefore isolate one property while excluding unrelated properties, guest records, credentials, and shared platform code.

## Availability concurrency

Reservation and calendar-block triggers acquire a transaction-scoped advisory lock using the property UUID. They then check both reservation and block ranges before accepting inventory-changing writes. This prevents concurrent direct writes from double-booking a property when all inventory writes use the database tables/functions.

Imported channel conflicts can be stored with `conflict_override=true` only through a privileged backend workflow and must create a `booking.calendar_conflicts` record for owner review.

## Personal data

The database stores encrypted bytes and lookup hashes for guest contact data. The backend performs authenticated encryption with a cloud-managed key and includes a key-version value for rotation. Exact property address and guest access credentials are isolated in `secure`.

## Static website compatibility

Public static pages read only intentionally public data from a generated JSON build artifact or a restricted public API. Static browser code never connects directly to database tables and never receives secrets.
