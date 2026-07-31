begin;

revoke all on schema secure from public;
revoke all on all tables in schema secure from public;
revoke all on all sequences in schema secure from public;
revoke all on all functions in schema secure from public;

alter table app.organizations enable row level security;
alter table app.users enable row level security;
alter table app.organization_members enable row level security;
alter table app.properties enable row level security;
alter table app.property_domains enable row level security;
alter table app.property_members enable row level security;
alter table app.property_settings enable row level security;
alter table app.feature_flags enable row level security;
alter table app.audit_log enable row level security;
alter table app.data_exports enable row level security;
alter table app.data_retention_policies enable row level security;
alter table app.data_subject_requests enable row level security;

alter table secure.property_addresses enable row level security;
alter table secure.guests enable row level security;
alter table secure.integration_credentials enable row level security;
alter table secure.webhook_secrets enable row level security;
alter table secure.guest_access_tokens enable row level security;
alter table secure.access_credentials enable row level security;
alter table secure.calendar_share_tokens enable row level security;
alter table secure.calendar_share_properties enable row level security;

alter table booking.calendar_sources enable row level security;
alter table booking.reservations enable row level security;
alter table booking.calendar_blocks enable row level security;
alter table booking.quotes enable row level security;
alter table booking.quote_line_items enable row level security;
alter table booking.booking_requests enable row level security;
alter table booking.rental_agreements enable row level security;
alter table booking.agreement_signatures enable row level security;
alter table booking.occupancy_approval_requests enable row level security;
alter table booking.reservation_status_history enable row level security;
alter table booking.calendar_sync_runs enable row level security;
alter table booking.calendar_sync_events enable row level security;
alter table booking.calendar_conflicts enable row level security;
alter table booking.cleaning_tasks enable row level security;

alter table messaging.email_provider_configs enable row level security;
alter table messaging.email_templates enable row level security;
alter table messaging.email_outbox enable row level security;
alter table messaging.email_delivery_attempts enable row level security;
alter table messaging.notification_preferences enable row level security;
alter table messaging.contact_requests enable row level security;

alter table market.provider_configs enable row level security;
alter table market.search_profiles enable row level security;
alter table market.comparable_properties enable row level security;
alter table market.public_listing_snapshots enable row level security;
alter table market.rate_observations enable row level security;
alter table market.monthly_metrics enable row level security;
alter table market.import_runs enable row level security;

alter table ai.bot_configs enable row level security;
alter table ai.knowledge_documents enable row level security;
alter table ai.knowledge_document_versions enable row level security;
alter table ai.conversations enable row level security;
alter table ai.messages enable row level security;
alter table ai.tool_calls enable row level security;
alter table ai.escalations enable row level security;
alter table ai.feedback enable row level security;
alter table ai.usage_daily enable row level security;

alter table analytics.web_sessions enable row level security;
alter table analytics.page_views enable row level security;
alter table analytics.journey_events enable row level security;
alter table analytics.business_events enable row level security;
alter table analytics.service_health_samples enable row level security;
alter table analytics.http_metrics_hourly enable row level security;
alter table analytics.business_metrics_daily enable row level security;
alter table analytics.consent_events enable row level security;

-- Drop/recreate selected policies so the migration is repeatable.
drop policy if exists properties_read on app.properties;
create policy properties_read on app.properties for select using (app.can_read_property(id));
drop policy if exists properties_manage on app.properties;
create policy properties_manage on app.properties for all
  using (app.can_admin_property(id)) with check (app.can_admin_property(id));

drop policy if exists property_settings_read on app.property_settings;
create policy property_settings_read on app.property_settings for select using (app.can_read_property(property_id));
drop policy if exists property_settings_manage on app.property_settings;
create policy property_settings_manage on app.property_settings for all
  using (app.can_admin_property(property_id)) with check (app.can_admin_property(property_id));

drop policy if exists reservations_read on booking.reservations;
create policy reservations_read on booking.reservations for select using (app.can_read_property(property_id));
drop policy if exists reservations_manage on booking.reservations;
create policy reservations_manage on booking.reservations for all
  using (app.can_manage_property(property_id)) with check (app.can_manage_property(property_id));

drop policy if exists booking_requests_read on booking.booking_requests;
create policy booking_requests_read on booking.booking_requests for select using (app.can_manage_property(property_id));
drop policy if exists booking_requests_manage on booking.booking_requests;
create policy booking_requests_manage on booking.booking_requests for all
  using (app.can_manage_property(property_id)) with check (app.can_manage_property(property_id));

drop policy if exists calendar_blocks_read on booking.calendar_blocks;
create policy calendar_blocks_read on booking.calendar_blocks for select using (app.can_read_property(property_id));
drop policy if exists calendar_blocks_manage on booking.calendar_blocks;
create policy calendar_blocks_manage on booking.calendar_blocks for all
  using (app.can_manage_property(property_id)) with check (app.can_manage_property(property_id));

drop policy if exists calendar_sources_admin on booking.calendar_sources;
create policy calendar_sources_admin on booking.calendar_sources for all
  using (app.can_admin_property(property_id)) with check (app.can_admin_property(property_id));

drop policy if exists cleaning_tasks_read on booking.cleaning_tasks;
create policy cleaning_tasks_read on booking.cleaning_tasks for select using (app.can_read_property(property_id));
drop policy if exists cleaning_tasks_manage on booking.cleaning_tasks;
create policy cleaning_tasks_manage on booking.cleaning_tasks for all
  using (app.can_manage_property(property_id)) with check (app.can_manage_property(property_id));

drop policy if exists property_addresses_read on secure.property_addresses;
create policy property_addresses_read on secure.property_addresses for select using (app.can_read_property(property_id));
drop policy if exists property_addresses_manage on secure.property_addresses;
create policy property_addresses_manage on secure.property_addresses for all
  using (app.can_admin_property(property_id)) with check (app.can_admin_property(property_id));

drop policy if exists comparable_properties_read on market.comparable_properties;
create policy comparable_properties_read on market.comparable_properties for select using (app.can_read_property(property_id));
drop policy if exists comparable_properties_manage on market.comparable_properties;
create policy comparable_properties_manage on market.comparable_properties for all
  using (app.can_manage_property(property_id)) with check (app.can_manage_property(property_id));

drop policy if exists search_profiles_read on market.search_profiles;
create policy search_profiles_read on market.search_profiles for select using (app.can_read_property(property_id));
drop policy if exists search_profiles_manage on market.search_profiles;
create policy search_profiles_manage on market.search_profiles for all
  using (app.can_manage_property(property_id)) with check (app.can_manage_property(property_id));

drop policy if exists ai_bot_configs_admin on ai.bot_configs;
create policy ai_bot_configs_admin on ai.bot_configs for all
  using (app.can_admin_property(property_id)) with check (app.can_admin_property(property_id));
drop policy if exists knowledge_documents_read on ai.knowledge_documents;
create policy knowledge_documents_read on ai.knowledge_documents for select using (app.can_read_property(property_id));
drop policy if exists knowledge_documents_manage on ai.knowledge_documents;
create policy knowledge_documents_manage on ai.knowledge_documents for all
  using (app.can_admin_property(property_id)) with check (app.can_admin_property(property_id));

drop policy if exists business_metrics_read on analytics.business_metrics_daily;
create policy business_metrics_read on analytics.business_metrics_daily for select using (app.can_read_property(property_id));

drop policy if exists web_sessions_read on analytics.web_sessions;
create policy web_sessions_read on analytics.web_sessions for select using (
  property_id is not null and app.can_admin_property(property_id)
);

-- Tables without an end-user policy remain service-role/backend-only by design.

insert into app.schema_migrations(version, description)
values ('010', 'Row Level Security foundation and selected property-scoped policies')
on conflict (version) do nothing;

commit;
