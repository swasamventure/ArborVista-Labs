# Migration plan from current GitHub/local architecture

1. Create a staging PostgreSQL database.
2. Apply portable migrations and seed only non-sensitive property configuration.
3. Configure backend application-layer encryption and keyed lookup hashes.
4. Migrate properties and property settings.
5. Migrate reservations/calendar blocks with `conflict_override` only for known imported conflicts.
6. Store private iCal URLs as encrypted integration credentials.
7. Migrate signed agreements into private object storage and store hashes/paths.
8. Import the 83 public comp records using `seed/020_real_comp_snapshot.sql`.
9. Connect email outbox to the selected provider adapter.
10. Connect analytics ingestion and dashboard aggregates.
11. Apply the Supabase adapter only when Supabase is the selected authentication platform.
12. Run all SQL tests, backup/restore rehearsal, and security review before production cutover.
