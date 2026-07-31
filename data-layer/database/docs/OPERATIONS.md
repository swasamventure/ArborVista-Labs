# Operations

## Health checks

- Database connectivity
- Migration version
- Calendar sync success/failure age
- Email outbox backlog and delivery failures
- API p50/p95/p99 latency
- Error rate by route
- Backup completion and restore tests

## Business dashboard metrics

- Website visits and unique sessions
- Traffic source and campaign
- Page flow and booking funnel
- Availability searches
- Booking started/submitted/confirmed
- Abandonment rate
- Occupied nights and gross revenue
- Chatbot conversations, unanswered questions, escalations, and cost

## Backups

Use managed PITR where available and scheduled logical backups. Test restores periodically. Encrypt backup storage and keep it outside the primary runtime account when practical.

## Cost control

Start with one PostgreSQL database and a modular-monolith backend. Use daily/hourly aggregates for dashboards instead of expensive real-time queries over raw events. Apply retention and partitioning only when volume requires it.
