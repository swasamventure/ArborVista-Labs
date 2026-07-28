# Phase A Market Data Adapter Contract

Phase A is provider-neutral and does not call Airbnb, Vrbo, Booking.com, or a paid API. The browser dashboard accepts normalized CSV or workspace JSON.

A future server-side adapter should output:

- provider and channel listing identifiers
- public listing URL, when licensed
- approximate coordinates and distance from the subject property
- bedrooms, bathrooms, guest capacity, beds, rating, and review count
- normalized amenity flags
- monthly ADR, occupancy estimate, revenue estimate, and source label
- future nightly-rate observations
- retrieval timestamp and licensing/source metadata

API credentials must remain server-side after the Supabase migration. Never commit provider keys to a property repository or expose them in browser JavaScript.
