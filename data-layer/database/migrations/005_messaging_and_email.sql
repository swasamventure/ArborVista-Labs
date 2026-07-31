begin;

create table if not exists messaging.email_provider_configs (
  id uuid primary key default gen_random_uuid(),
  organization_id uuid not null references app.organizations(id) on delete cascade,
  property_id uuid references app.properties(id) on delete cascade,
  provider_type text not null default 'placeholder',
  credential_id uuid references secure.integration_credentials(id) on delete set null,
  from_name text,
  from_address_alias text,
  reply_to_alias text,
  active boolean not null default false,
  configuration jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (organization_id, property_id, provider_type)
);

create table if not exists messaging.email_templates (
  id uuid primary key default gen_random_uuid(),
  organization_id uuid not null references app.organizations(id) on delete cascade,
  property_id uuid references app.properties(id) on delete cascade,
  template_key text not null,
  version integer not null default 1,
  subject_template text not null,
  body_html_template text not null,
  body_text_template text,
  active boolean not null default true,
  variables_schema jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (organization_id, property_id, template_key, version)
);

create table if not exists messaging.email_outbox (
  id uuid primary key default gen_random_uuid(),
  organization_id uuid not null references app.organizations(id) on delete cascade,
  property_id uuid references app.properties(id) on delete cascade,
  reservation_id uuid references booking.reservations(id) on delete set null,
  booking_request_id uuid references booking.booking_requests(id) on delete set null,
  template_id uuid references messaging.email_templates(id) on delete set null,
  recipient_type text not null check (recipient_type in ('guest','owner','user','external')),
  recipient_guest_id uuid references secure.guests(id) on delete set null,
  recipient_user_id uuid references app.users(id) on delete set null,
  recipient_ciphertext bytea,
  recipient_lookup_hash bytea,
  payload jsonb not null default '{}'::jsonb,
  scheduled_for timestamptz not null default now(),
  status text not null default 'queued' check (status in ('queued','processing','sent','failed','cancelled')),
  deduplication_key text,
  attempt_count integer not null default 0,
  max_attempts integer not null default 5,
  last_error_code text,
  last_error_message text,
  created_at timestamptz not null default now(),
  sent_at timestamptz,
  check (
    recipient_guest_id is not null or recipient_user_id is not null or recipient_ciphertext is not null
  )
);

create unique index if not exists email_outbox_dedup_idx
  on messaging.email_outbox(deduplication_key) where deduplication_key is not null;
create index if not exists email_outbox_queue_idx
  on messaging.email_outbox(status, scheduled_for) where status in ('queued','failed');

create table if not exists messaging.email_delivery_attempts (
  id bigint generated always as identity primary key,
  email_outbox_id uuid not null references messaging.email_outbox(id) on delete cascade,
  provider_type text not null,
  provider_message_id text,
  attempt_number integer not null,
  status text not null check (status in ('started','accepted','delivered','bounced','failed')),
  response_code text,
  response_detail jsonb not null default '{}'::jsonb,
  started_at timestamptz not null default now(),
  finished_at timestamptz
);

create table if not exists messaging.notification_preferences (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references app.users(id) on delete cascade,
  property_id uuid references app.properties(id) on delete cascade,
  event_key text not null,
  email_enabled boolean not null default true,
  dashboard_enabled boolean not null default true,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (user_id, property_id, event_key)
);

create table if not exists messaging.contact_requests (
  id uuid primary key default gen_random_uuid(),
  property_id uuid references app.properties(id) on delete set null,
  source text not null check (source in ('website','chatbot','guest_portal','admin','other')),
  guest_id uuid references secure.guests(id) on delete set null,
  conversation_id uuid,
  category text,
  message_ciphertext bytea not null,
  encryption_key_version smallint not null default 1,
  status text not null default 'open' check (status in ('open','in_progress','resolved','closed')),
  assigned_user_id uuid references app.users(id) on delete set null,
  created_at timestamptz not null default now(),
  resolved_at timestamptz
);

create trigger email_provider_configs_touch_updated_at before update on messaging.email_provider_configs
for each row execute function app.touch_updated_at();
create trigger email_templates_touch_updated_at before update on messaging.email_templates
for each row execute function app.touch_updated_at();
create trigger notification_preferences_touch_updated_at before update on messaging.notification_preferences
for each row execute function app.touch_updated_at();

insert into app.schema_migrations(version, description)
values ('005', 'Provider-neutral email configuration, templates, outbox, delivery attempts, and contact requests')
on conflict (version) do nothing;

commit;
