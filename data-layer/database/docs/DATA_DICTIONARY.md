# Data dictionary summary

## `app`

- `organizations`: portfolio/business tenant.
- `users`: portable identity record mapped to an external authentication provider.
- `organization_members`: portfolio-level roles.
- `properties`: transferable STR property identity and public operating facts.
- `property_domains`: independently transferable domains.
- `property_members`: property-level roles.
- `property_settings`: structured property configuration; explicitly flags public values.
- `feature_flags`: staged feature enablement.
- `audit_log`: security and operational audit trail.
- `data_exports`: privacy-scoped property/export jobs.
- `data_retention_policies`: retention configuration.
- `data_subject_requests`: privacy access/correction/deletion/export workflow.

## `secure`

- `property_addresses`: encrypted exact address fields.
- `guests`: encrypted guest identity/contact information plus HMAC lookup hashes.
- `integration_credentials`: encrypted provider credentials and private feed URLs.
- `webhook_secrets`: encrypted webhook-verification material.
- `guest_access_tokens`: hashed, expiring, revocable Guest Portal tokens.
- `access_credentials`: encrypted door/gate/Wi-Fi credentials.
- `calendar_share_tokens`: hashed, expiring cleaner/maintenance feed tokens.

## `booking`

- `calendar_sources`: Airbnb, Vrbo, direct, owner, Booking.com, and other sources.
- `reservations`: source of truth for stays/blocks and pricing status.
- `calendar_blocks`: owner, maintenance, cleaning, and safety blocks.
- `quotes` / `quote_line_items`: deterministic pricing result and components.
- `booking_requests`: guest booking request workflow.
- `rental_agreements` / `agreement_signatures`: versioned signed documents.
- `occupancy_approval_requests`: standard-six versus approved-seven/eight workflow.
- `calendar_sync_runs` / `calendar_sync_events`: iCal synchronization audit.
- `calendar_conflicts`: overlaps requiring owner review.
- `cleaning_tasks`: cleaning operations without guest PII.

## `messaging`

- `email_provider_configs`: placeholder/provider-neutral adapter settings.
- `email_templates`: versioned email templates.
- `email_outbox`: queued email intent and schedule.
- `email_delivery_attempts`: provider response and retry history.
- `notification_preferences`: staff notification settings.
- `contact_requests`: website/chatbot/portal escalation.

## `market`

- `search_profiles`: exact, expanded, and custom comp filters.
- `comparable_properties`: deduplicatable public listing identity/metadata.
- `public_listing_snapshots`: dated public metadata snapshots.
- `rate_observations`: repeated standardized public price observations.
- `monthly_metrics`: observed, provider-estimated, or owner-actual monthly metrics.
- `import_runs`: CSV/API/provider import audit.

## `ai`

- `bot_configs`: property-scoped chatbot feature and provider configuration.
- `knowledge_documents` / `knowledge_document_versions`: approved public/private knowledge.
- `conversations` / `messages`: public, authenticated guest, and staff conversations.
- `tool_calls`: validated availability, quote, booking, and escalation actions.
- `escalations`: owner/staff handoff.
- `feedback`: user feedback.
- `usage_daily`: token and estimated-cost accounting.

## `analytics`

- `web_sessions`: anonymized session and campaign context.
- `page_views`: page-level behavior.
- `journey_events`: booking-funnel and user-journey actions.
- `business_events`: auditable business events.
- `service_health_samples`: uptime/health observations.
- `http_metrics_hourly`: technical request aggregates.
- `business_metrics_daily`: dashboard-ready business aggregates.
- `consent_events`: analytics-consent history.
