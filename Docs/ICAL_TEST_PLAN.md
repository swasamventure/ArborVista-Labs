# iCal Integration Test Plan — v2.8

## Date model

All reservations use `[start_date, end_date)` semantics. A booking from September 4 through September 8 occupies nights September 4–7; another booking may begin September 8.

## Required production behaviors

1. Import Airbnb and Vrbo feeds on a schedule.
2. Identify events by source plus external UID.
3. Re-import without creating duplicates.
4. Update dates when an upstream event changes.
5. Preserve source attribution.
6. Combine imported reservations, direct requests, and owner blocks for availability.
7. Reject direct requests that overlap any active unavailable period.
8. Publish direct reservations and owner blocks through an outbound `.ics` feed.
9. Record each sync and each material change in logs.
10. Treat feed URLs and administrative actions as protected backend data.

## Not included yet

- Network download of private Airbnb/Vrbo feeds
- Cancellation reconciliation when an event disappears from a feed
- Recurrence rules
- Time-based events and timezone conversion
- Supabase Row Level Security
- Admin authentication
- Live website/API connection
- Background scheduling and retries
