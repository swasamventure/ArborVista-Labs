# Planned v4.4 — AI Guest Assistant

Planned capabilities:

- Property-scoped answers for amenities, occupancy, house rules, check-in/check-out, resort information, and local attractions.
- Availability lookup only through the approved reservation API.
- No exposure of guest names, phone numbers, email addresses, door codes, private iCal URLs, owner notes, or financial data.
- Clear handoff to the owner for discounts, exceptions, cancellations, payments, emergencies, and policy disputes.
- Retrieval from approved property configuration, FAQ, guest guidebook, and local-area content.
- Conversation logging and retention controls in Supabase after cloud migration.
- Rate limiting, abuse protection, prompt-injection defenses, and property-level RLS.
- Cloudflare Worker/Pages Function or Supabase Edge Function as the server-side gateway; no model API key in browser code.
