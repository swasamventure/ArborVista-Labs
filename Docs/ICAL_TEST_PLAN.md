# iCal Integration Test Plan — v2.8

## Date model

All reservations use `[start_date, end_date)` semantics. A stay from September 4 through September 8 occupies nights September 4–7. Another stay may begin September 8.

## Automated coverage completed

- Airbnb fixture import
- Vrbo fixture import
- Repeated-feed idempotency
- Reservation date and summary updates
- Explicit `STATUS:CANCELLED`
- Event disappearance reconciliation
- Empty full-feed reconciliation
- Folded iCal lines
- Duplicate UIDs within one feed
- Malformed VEVENT rejection
- Failed-sync logging
- Overlap detection
- Adjacent-stay acceptance
- Owner blocks
- Direct booking requests
- Concurrent duplicate-request protection
- Reservation cancellation and date reopening
- Generic outbound ICS
- Airbnb-specific outbound ICS
- Vrbo-specific outbound ICS
- CRLF output and publish headers
- Round-trip parsing of generated ICS
- Database integrity and health checks

## Real-feed test procedure

1. Make a protected copy of the development database.
2. Obtain the private export URL from Airbnb or Vrbo.
3. Do not commit the URL to GitHub or documentation.
4. Run `sync-url` manually against the copied database.
5. Verify imported dates against the channel calendar.
6. Run the same sync again and confirm zero duplicate inserts.
7. Change or cancel a controlled test reservation and verify reconciliation.
8. Import the channel-specific Arbor Vista export back into the matching platform only after review.
9. Confirm direct/owner blocks appear without duplicating the channel's own reservations.
10. Record the platform refresh delay observed during the test.

## Not production-ready yet

- No scheduled background sync or retries
- No Supabase/PostgreSQL migration
- No secret storage
- No admin authentication
- No website-to-database API
- No live availability response on the Book Direct form
- No recurrence-rule expansion
- No timed-event/timezone conversion beyond all-day reservation dates
