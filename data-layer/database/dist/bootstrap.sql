begin;

create extension if not exists pgcrypto;
create extension if not exists btree_gist;

create schema if not exists app;
create schema if not exists secure;
create schema if not exists booking;
create schema if not exists messaging;
create schema if not exists market;
create schema if not exists ai;
create schema if not exists analytics;
create schema if not exists api;

create table if not exists app.schema_migrations (
  version text primary key,
  description text not null,
  applied_at timestamptz not null default now()
);

create or replace function app.touch_updated_at()
returns trigger
language plpgsql
as $$
begin
  new.updated_at := now();
  return new;
end;
$$;

create or replace function app.current_user_id()
returns uuid
language sql
stable
as $$
  select nullif(current_setting('app.user_id', true), '')::uuid;
$$;

create or replace function app.current_request_id()
returns text
language sql
stable
as $$
  select nullif(current_setting('app.request_id', true), '');
$$;

insert into app.schema_migrations(version, description)
values ('001', 'Extensions, logical schemas, and shared functions')
on conflict (version) do nothing;

commit;


begin;

create table if not exists app.organizations (
  id uuid primary key default gen_random_uuid(),
  name text not null,
  slug text not null unique check (slug ~ '^[a-z0-9]+(?:-[a-z0-9]+)*$'),
  active boolean not null default true,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists app.users (
  id uuid primary key default gen_random_uuid(),
  external_auth_provider text not null default 'local',
  external_auth_subject text,
  display_name text,
  active boolean not null default true,
  last_login_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (external_auth_provider, external_auth_subject)
);

create table if not exists app.organization_members (
  organization_id uuid not null references app.organizations(id) on delete cascade,
  user_id uuid not null references app.users(id) on delete cascade,
  role text not null check (role in ('portfolio_owner','portfolio_admin','accountant','readonly')),
  created_at timestamptz not null default now(),
  primary key (organization_id, user_id)
);

create table if not exists app.properties (
  id uuid primary key default gen_random_uuid(),
  organization_id uuid not null references app.organizations(id) on delete cascade,
  code text not null unique,
  name text not null,
  slug text not null unique check (slug ~ '^[a-z0-9]+(?:-[a-z0-9]+)*$'),
  public_domain text unique,
  public_location_label text,
  timezone text not null default 'America/New_York',
  check_in_time time not null default '16:00',
  check_out_time time not null default '10:00',
  cleaning_duration_minutes integer not null default 240 check (cleaning_duration_minutes between 30 and 720),
  standard_sleeps integer not null default 6 check (standard_sleeps > 0),
  maximum_requested_guests integer not null default 8 check (maximum_requested_guests >= standard_sleeps),
  bedrooms numeric(4,1) check (bedrooms is null or bedrooms >= 0),
  bathrooms numeric(4,1) check (bathrooms is null or bathrooms >= 0),
  beds integer check (beds is null or beds >= 0),
  currency char(3) not null default 'USD',
  active boolean not null default true,
  publicly_listed boolean not null default true,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists app.property_domains (
  id uuid primary key default gen_random_uuid(),
  property_id uuid not null references app.properties(id) on delete cascade,
  hostname text not null unique,
  is_primary boolean not null default false,
  verified_at timestamptz,
  created_at timestamptz not null default now()
);

create unique index if not exists property_domains_one_primary_idx
  on app.property_domains(property_id) where is_primary;

create table if not exists app.property_members (
  property_id uuid not null references app.properties(id) on delete cascade,
  user_id uuid not null references app.users(id) on delete cascade,
  role text not null check (role in ('property_owner','manager','cohost','cleaner','maintenance','accountant','readonly')),
  created_at timestamptz not null default now(),
  primary key (property_id, user_id)
);

create table if not exists app.property_settings (
  property_id uuid not null references app.properties(id) on delete cascade,
  setting_key text not null,
  value_json jsonb not null default '{}'::jsonb,
  is_public boolean not null default false,
  updated_at timestamptz not null default now(),
  primary key (property_id, setting_key)
);

create table if not exists app.feature_flags (
  property_id uuid references app.properties(id) on delete cascade,
  flag_key text not null,
  enabled boolean not null default false,
  configuration jsonb not null default '{}'::jsonb,
  updated_at timestamptz not null default now(),
  unique (property_id, flag_key)
);

create table if not exists app.audit_log (
  id bigint generated always as identity primary key,
  organization_id uuid references app.organizations(id) on delete set null,
  property_id uuid references app.properties(id) on delete set null,
  actor_user_id uuid references app.users(id) on delete set null,
  actor_type text not null default 'user' check (actor_type in ('user','service','guest','system')),
  action text not null,
  entity_type text not null,
  entity_id text,
  request_id text,
  details jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);

create index if not exists audit_log_property_created_idx on app.audit_log(property_id, created_at desc);
create index if not exists audit_log_entity_idx on app.audit_log(entity_type, entity_id, created_at desc);

create table if not exists app.data_exports (
  id uuid primary key default gen_random_uuid(),
  property_id uuid not null references app.properties(id) on delete cascade,
  requested_by uuid references app.users(id) on delete set null,
  export_type text not null check (export_type in ('property_transfer','reservation_archive','market_data','audit_archive')),
  status text not null default 'queued' check (status in ('queued','running','created','expired','failed')),
  storage_path text,
  manifest jsonb,
  expires_at timestamptz,
  error_message text,
  created_at timestamptz not null default now(),
  completed_at timestamptz
);

create table if not exists app.data_retention_policies (
  id uuid primary key default gen_random_uuid(),
  organization_id uuid not null references app.organizations(id) on delete cascade,
  data_category text not null,
  retention_days integer not null check (retention_days >= 0),
  legal_hold boolean not null default false,
  updated_at timestamptz not null default now(),
  unique (organization_id, data_category)
);

create table if not exists app.data_subject_requests (
  id uuid primary key default gen_random_uuid(),
  organization_id uuid not null references app.organizations(id) on delete cascade,
  request_type text not null check (request_type in ('access','correction','deletion','export')),
  subject_lookup_hash bytea not null,
  status text not null default 'received' check (status in ('received','verifying','processing','completed','denied')),
  requested_at timestamptz not null default now(),
  completed_at timestamptz,
  notes text
);

create trigger organizations_touch_updated_at before update on app.organizations
for each row execute function app.touch_updated_at();
create trigger users_touch_updated_at before update on app.users
for each row execute function app.touch_updated_at();
create trigger properties_touch_updated_at before update on app.properties
for each row execute function app.touch_updated_at();

insert into app.schema_migrations(version, description)
values ('002', 'Organizations, users, properties, membership, configuration, audit, and retention')
on conflict (version) do nothing;

commit;


begin;

create table if not exists secure.property_addresses (
  property_id uuid primary key references app.properties(id) on delete cascade,
  address_line1_ciphertext bytea,
  address_line2_ciphertext bytea,
  city text,
  state_region text,
  postal_code_ciphertext bytea,
  country_code char(2) not null default 'US',
  latitude numeric(9,6),
  longitude numeric(9,6),
  encryption_key_version smallint not null default 1,
  updated_at timestamptz not null default now()
);

create table if not exists secure.guests (
  id uuid primary key default gen_random_uuid(),
  first_name_ciphertext bytea not null,
  last_name_ciphertext bytea not null,
  email_ciphertext bytea not null,
  email_lookup_hash bytea not null,
  phone_ciphertext bytea,
  phone_lookup_hash bytea,
  encryption_key_version smallint not null default 1,
  marketing_consent boolean not null default false,
  consent_recorded_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  deleted_at timestamptz
);

create unique index if not exists guests_email_lookup_unique_idx
  on secure.guests(email_lookup_hash) where deleted_at is null;
create index if not exists guests_phone_lookup_idx
  on secure.guests(phone_lookup_hash) where phone_lookup_hash is not null and deleted_at is null;

create table if not exists secure.integration_credentials (
  id uuid primary key default gen_random_uuid(),
  organization_id uuid not null references app.organizations(id) on delete cascade,
  property_id uuid references app.properties(id) on delete cascade,
  provider_type text not null,
  credential_name text not null,
  secret_ciphertext bytea not null,
  secret_fingerprint text not null,
  encryption_key_version smallint not null default 1,
  active boolean not null default true,
  expires_at timestamptz,
  rotated_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (organization_id, property_id, provider_type, credential_name)
);

create table if not exists secure.webhook_secrets (
  id uuid primary key default gen_random_uuid(),
  organization_id uuid not null references app.organizations(id) on delete cascade,
  property_id uuid references app.properties(id) on delete cascade,
  provider text not null,
  secret_ciphertext bytea not null,
  secret_fingerprint text not null,
  encryption_key_version smallint not null default 1,
  active boolean not null default true,
  created_at timestamptz not null default now(),
  rotated_at timestamptz
);

create trigger property_addresses_touch_updated_at before update on secure.property_addresses
for each row execute function app.touch_updated_at();
create trigger guests_touch_updated_at before update on secure.guests
for each row execute function app.touch_updated_at();
create trigger integration_credentials_touch_updated_at before update on secure.integration_credentials
for each row execute function app.touch_updated_at();

insert into app.schema_migrations(version, description)
values ('003', 'Encrypted property address, guest PII, and integration-secret storage')
on conflict (version) do nothing;

commit;


begin;

create table if not exists booking.calendar_sources (
  id uuid primary key default gen_random_uuid(),
  property_id uuid not null references app.properties(id) on delete cascade,
  source_type text not null check (source_type in ('airbnb','vrbo','direct','owner','booking_com','other')),
  name text not null,
  credential_id uuid references secure.integration_credentials(id) on delete set null,
  enabled boolean not null default true,
  sync_interval_minutes integer not null default 60 check (sync_interval_minutes between 15 and 10080),
  last_synced_at timestamptz,
  last_success_at timestamptz,
  last_etag text,
  last_modified text,
  next_sync_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (property_id, source_type, name)
);

create table if not exists booking.reservations (
  id uuid primary key default gen_random_uuid(),
  property_id uuid not null references app.properties(id) on delete cascade,
  calendar_source_id uuid references booking.calendar_sources(id) on delete set null,
  primary_guest_id uuid references secure.guests(id) on delete set null,
  external_uid text,
  booking_reference text,
  source_type text not null check (source_type in ('airbnb','vrbo','direct','owner','booking_com','other')),
  status text not null default 'pending' check (status in ('hold','pending','confirmed','cancelled','completed','blocked')),
  check_in date not null,
  check_out date not null,
  stay_range daterange generated always as (daterange(check_in, check_out, '[)')) stored,
  adults integer not null default 1 check (adults >= 1),
  children integer not null default 0 check (children >= 0),
  infants integer not null default 0 check (infants >= 0),
  pets integer not null default 0 check (pets >= 0),
  occupancy_approval_status text not null default 'not_required'
    check (occupancy_approval_status in ('not_required','required','approved','declined')),
  currency char(3) not null default 'USD',
  accommodation_amount_cents bigint check (accommodation_amount_cents is null or accommodation_amount_cents >= 0),
  fees_amount_cents bigint check (fees_amount_cents is null or fees_amount_cents >= 0),
  taxes_amount_cents bigint check (taxes_amount_cents is null or taxes_amount_cents >= 0),
  total_amount_cents bigint check (total_amount_cents is null or total_amount_cents >= 0),
  payment_status text not null default 'not_required'
    check (payment_status in ('not_required','unpaid','partially_paid','paid','refunded','failed')),
  public_summary text,
  cleaner_note text,
  internal_note_ciphertext bytea,
  conflict_override boolean not null default false,
  cancelled_at timestamptz,
  cancellation_reason text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  check (check_out > check_in),
  unique (calendar_source_id, external_uid)
);

create index if not exists reservations_property_range_gist_idx
  on booking.reservations using gist(property_id, stay_range);
create index if not exists reservations_property_status_dates_idx
  on booking.reservations(property_id, status, check_in, check_out);
create index if not exists reservations_guest_idx on booking.reservations(primary_guest_id);

create table if not exists booking.calendar_blocks (
  id uuid primary key default gen_random_uuid(),
  property_id uuid not null references app.properties(id) on delete cascade,
  check_in date not null,
  check_out date not null,
  stay_range daterange generated always as (daterange(check_in, check_out, '[)')) stored,
  reason text not null,
  block_type text not null default 'owner' check (block_type in ('owner','maintenance','cleaning','safety','other')),
  active boolean not null default true,
  conflict_override boolean not null default false,
  created_by uuid references app.users(id) on delete set null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  check (check_out > check_in)
);

create index if not exists calendar_blocks_property_range_gist_idx
  on booking.calendar_blocks using gist(property_id, stay_range);

create table if not exists booking.quotes (
  id uuid primary key default gen_random_uuid(),
  property_id uuid not null references app.properties(id) on delete cascade,
  guest_id uuid references secure.guests(id) on delete set null,
  check_in date not null,
  check_out date not null,
  adults integer not null default 1 check (adults >= 1),
  children integer not null default 0 check (children >= 0),
  currency char(3) not null default 'USD',
  subtotal_cents bigint not null default 0 check (subtotal_cents >= 0),
  fees_cents bigint not null default 0 check (fees_cents >= 0),
  taxes_cents bigint not null default 0 check (taxes_cents >= 0),
  total_cents bigint not null default 0 check (total_cents >= 0),
  pricing_version text not null,
  expires_at timestamptz not null,
  status text not null default 'active' check (status in ('active','accepted','expired','void')),
  calculation_details jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  check (check_out > check_in)
);

create table if not exists booking.quote_line_items (
  id uuid primary key default gen_random_uuid(),
  quote_id uuid not null references booking.quotes(id) on delete cascade,
  line_type text not null check (line_type in ('nightly_rate','cleaning_fee','guest_fee','discount','tax','other')),
  description text not null,
  quantity numeric(12,3) not null default 1,
  unit_amount_cents bigint not null,
  total_amount_cents bigint not null,
  sort_order integer not null default 0,
  metadata jsonb not null default '{}'::jsonb
);

create table if not exists booking.booking_requests (
  id uuid primary key default gen_random_uuid(),
  property_id uuid not null references app.properties(id) on delete cascade,
  quote_id uuid references booking.quotes(id) on delete set null,
  reservation_id uuid references booking.reservations(id) on delete set null,
  guest_id uuid not null references secure.guests(id) on delete restrict,
  check_in date not null,
  check_out date not null,
  adults integer not null check (adults >= 1),
  children integer not null default 0 check (children >= 0),
  infants integer not null default 0 check (infants >= 0),
  vehicles integer not null default 1 check (vehicles >= 0),
  special_requests_ciphertext bytea,
  status text not null default 'pending'
    check (status in ('draft','pending','approved','declined','cancelled','expired')),
  submitted_at timestamptz,
  reviewed_by uuid references app.users(id) on delete set null,
  reviewed_at timestamptz,
  review_note text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  check (check_out > check_in)
);

create table if not exists booking.rental_agreements (
  id uuid primary key default gen_random_uuid(),
  property_id uuid not null references app.properties(id) on delete cascade,
  booking_request_id uuid not null references booking.booking_requests(id) on delete cascade,
  agreement_version text not null,
  document_storage_path text,
  document_sha256 text not null,
  status text not null default 'pending' check (status in ('pending','signed','void')),
  created_at timestamptz not null default now(),
  signed_at timestamptz,
  unique (booking_request_id, agreement_version)
);

create table if not exists booking.agreement_signatures (
  id uuid primary key default gen_random_uuid(),
  rental_agreement_id uuid not null references booking.rental_agreements(id) on delete cascade,
  signer_guest_id uuid not null references secure.guests(id) on delete restrict,
  legal_name_ciphertext bytea not null,
  signature_ciphertext bytea not null,
  ip_lookup_hash bytea,
  user_agent_lookup_hash bytea,
  encryption_key_version smallint not null default 1,
  signed_at timestamptz not null default now()
);

create table if not exists booking.occupancy_approval_requests (
  id uuid primary key default gen_random_uuid(),
  property_id uuid not null references app.properties(id) on delete cascade,
  booking_request_id uuid references booking.booking_requests(id) on delete cascade,
  reservation_id uuid references booking.reservations(id) on delete cascade,
  requested_guest_count integer not null,
  status text not null default 'pending' check (status in ('pending','approved','declined','expired')),
  decided_by uuid references app.users(id) on delete set null,
  decided_at timestamptz,
  note text,
  created_at timestamptz not null default now(),
  check (booking_request_id is not null or reservation_id is not null)
);

create table if not exists booking.reservation_status_history (
  id bigint generated always as identity primary key,
  reservation_id uuid not null references booking.reservations(id) on delete cascade,
  old_status text,
  new_status text not null,
  changed_by uuid references app.users(id) on delete set null,
  reason text,
  changed_at timestamptz not null default now()
);

create table if not exists booking.calendar_sync_runs (
  id uuid primary key default gen_random_uuid(),
  calendar_source_id uuid not null references booking.calendar_sources(id) on delete cascade,
  started_at timestamptz not null default now(),
  finished_at timestamptz,
  status text not null default 'running' check (status in ('running','success','partial','failed')),
  events_seen integer not null default 0,
  events_inserted integer not null default 0,
  events_updated integer not null default 0,
  events_cancelled integer not null default 0,
  conflicts_found integer not null default 0,
  request_id text,
  error_code text,
  error_message text
);

create table if not exists booking.calendar_sync_events (
  id bigint generated always as identity primary key,
  sync_run_id uuid not null references booking.calendar_sync_runs(id) on delete cascade,
  external_uid text,
  action text not null check (action in ('seen','inserted','updated','cancelled','ignored','failed')),
  reservation_id uuid references booking.reservations(id) on delete set null,
  payload_sha256 text,
  detail jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);

create table if not exists booking.calendar_conflicts (
  id uuid primary key default gen_random_uuid(),
  property_id uuid not null references app.properties(id) on delete cascade,
  reservation_id_a uuid references booking.reservations(id) on delete cascade,
  reservation_id_b uuid references booking.reservations(id) on delete cascade,
  calendar_block_id uuid references booking.calendar_blocks(id) on delete cascade,
  conflict_range daterange not null,
  status text not null default 'open' check (status in ('open','acknowledged','resolved','ignored')),
  resolution_note text,
  created_at timestamptz not null default now(),
  resolved_at timestamptz,
  check (reservation_id_a is not null)
);

create table if not exists booking.cleaning_tasks (
  id uuid primary key default gen_random_uuid(),
  property_id uuid not null references app.properties(id) on delete cascade,
  reservation_id uuid references booking.reservations(id) on delete cascade,
  scheduled_start timestamptz not null,
  scheduled_end timestamptz not null,
  assigned_user_id uuid references app.users(id) on delete set null,
  status text not null default 'scheduled' check (status in ('scheduled','accepted','in_progress','completed','cancelled')),
  same_day_turnover boolean not null default false,
  incoming_guest_count integer,
  cleaner_note text,
  completed_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  check (scheduled_end > scheduled_start)
);

create table if not exists secure.guest_access_tokens (
  id uuid primary key default gen_random_uuid(),
  reservation_id uuid not null references booking.reservations(id) on delete cascade,
  token_hash bytea not null unique,
  token_hint text,
  active boolean not null default true,
  expires_at timestamptz not null,
  revoked_at timestamptz,
  last_used_at timestamptz,
  created_at timestamptz not null default now()
);

create table if not exists secure.access_credentials (
  id uuid primary key default gen_random_uuid(),
  reservation_id uuid not null references booking.reservations(id) on delete cascade,
  credential_type text not null check (credential_type in ('door_code','gate_code','wifi_password','other')),
  value_ciphertext bytea not null,
  encryption_key_version smallint not null default 1,
  valid_from timestamptz,
  valid_until timestamptz,
  revoked_at timestamptz,
  created_at timestamptz not null default now(),
  check (valid_until is null or valid_from is null or valid_until > valid_from)
);

create table if not exists secure.calendar_share_tokens (
  id uuid primary key default gen_random_uuid(),
  organization_id uuid not null references app.organizations(id) on delete cascade,
  label text not null,
  audience text not null check (audience in ('cleaner','maintenance','readonly')),
  token_hash bytea not null unique,
  token_hint text,
  active boolean not null default true,
  expires_at timestamptz,
  revoked_at timestamptz,
  created_by uuid references app.users(id) on delete set null,
  created_at timestamptz not null default now()
);

create table if not exists secure.calendar_share_properties (
  share_token_id uuid not null references secure.calendar_share_tokens(id) on delete cascade,
  property_id uuid not null references app.properties(id) on delete cascade,
  primary key (share_token_id, property_id)
);

create or replace function booking.assert_reservation_rules()
returns trigger
language plpgsql
as $$
declare
  v_standard integer;
  v_maximum integer;
  v_total_guests integer;
begin
  if new.status not in ('hold','pending','confirmed','blocked') then
    return new;
  end if;

  select standard_sleeps, maximum_requested_guests
    into v_standard, v_maximum
  from app.properties
  where id = new.property_id;

  if not found then
    raise exception 'Unknown property %', new.property_id using errcode = '23503';
  end if;

  v_total_guests := coalesce(new.adults, 0) + coalesce(new.children, 0);
  if v_total_guests > v_maximum then
    raise exception 'Guest count % exceeds property maximum %', v_total_guests, v_maximum using errcode = '23514';
  end if;

  if v_total_guests > v_standard and new.status = 'confirmed' and new.occupancy_approval_status <> 'approved' then
    raise exception 'Guest count above standard occupancy requires approval before confirmation' using errcode = '23514';
  end if;

  if new.conflict_override then
    return new;
  end if;

  perform pg_advisory_xact_lock(hashtextextended(new.property_id::text, 0));

  if exists (
    select 1 from booking.reservations r
    where r.property_id = new.property_id
      and r.id <> new.id
      and r.status in ('hold','pending','confirmed','blocked')
      and not r.conflict_override
      and r.stay_range && daterange(new.check_in, new.check_out, '[)')
  ) or exists (
    select 1 from booking.calendar_blocks b
    where b.property_id = new.property_id
      and b.active
      and not b.conflict_override
      and b.stay_range && daterange(new.check_in, new.check_out, '[)')
  ) then
    raise exception 'Property inventory is unavailable for % through %', new.check_in, new.check_out using errcode = '23P01';
  end if;

  return new;
end;
$$;

create or replace function booking.assert_calendar_block_rules()
returns trigger
language plpgsql
as $$
begin
  if not new.active or new.conflict_override then
    return new;
  end if;

  perform pg_advisory_xact_lock(hashtextextended(new.property_id::text, 0));

  if exists (
    select 1 from booking.reservations r
    where r.property_id = new.property_id
      and r.status in ('hold','pending','confirmed','blocked')
      and not r.conflict_override
      and r.stay_range && daterange(new.check_in, new.check_out, '[)')
  ) or exists (
    select 1 from booking.calendar_blocks b
    where b.property_id = new.property_id
      and b.id <> new.id
      and b.active
      and not b.conflict_override
      and b.stay_range && daterange(new.check_in, new.check_out, '[)')
  ) then
    raise exception 'Property inventory is unavailable for block % through %', new.check_in, new.check_out using errcode = '23P01';
  end if;

  return new;
end;
$$;

create or replace function booking.record_reservation_status_change()
returns trigger
language plpgsql
as $$
begin
  if old.status is distinct from new.status then
    insert into booking.reservation_status_history(reservation_id, old_status, new_status, changed_by)
    values (new.id, old.status, new.status, app.current_user_id());
  end if;
  return new;
end;
$$;

drop trigger if exists reservations_assert_rules on booking.reservations;
create trigger reservations_assert_rules
before insert or update of property_id, check_in, check_out, adults, children, status, occupancy_approval_status, conflict_override
on booking.reservations for each row execute function booking.assert_reservation_rules();

drop trigger if exists reservations_status_history on booking.reservations;
create trigger reservations_status_history
after update of status on booking.reservations for each row execute function booking.record_reservation_status_change();

drop trigger if exists calendar_blocks_assert_rules on booking.calendar_blocks;
create trigger calendar_blocks_assert_rules
before insert or update of property_id, check_in, check_out, active, conflict_override
on booking.calendar_blocks for each row execute function booking.assert_calendar_block_rules();

create trigger calendar_sources_touch_updated_at before update on booking.calendar_sources
for each row execute function app.touch_updated_at();
create trigger reservations_touch_updated_at before update on booking.reservations
for each row execute function app.touch_updated_at();
create trigger calendar_blocks_touch_updated_at before update on booking.calendar_blocks
for each row execute function app.touch_updated_at();
create trigger booking_requests_touch_updated_at before update on booking.booking_requests
for each row execute function app.touch_updated_at();
create trigger cleaning_tasks_touch_updated_at before update on booking.cleaning_tasks
for each row execute function app.touch_updated_at();

insert into app.schema_migrations(version, description)
values ('004', 'Reservation, availability, pricing, agreements, calendar sync, cleaning, and secure guest access')
on conflict (version) do nothing;

commit;


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


begin;

create table if not exists market.provider_configs (
  id uuid primary key default gen_random_uuid(),
  organization_id uuid not null references app.organizations(id) on delete cascade,
  provider text not null,
  credential_id uuid references secure.integration_credentials(id) on delete set null,
  active boolean not null default false,
  configuration jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (organization_id, provider)
);

create table if not exists market.search_profiles (
  id uuid primary key default gen_random_uuid(),
  property_id uuid not null references app.properties(id) on delete cascade,
  profile_name text not null,
  profile_mode text not null default 'exact' check (profile_mode in ('exact','expanded','custom')),
  radius_miles numeric(7,2) not null default 5 check (radius_miles > 0),
  bedrooms_min numeric(4,1),
  bedrooms_max numeric(4,1),
  bathrooms_min numeric(4,1),
  bathrooms_max numeric(4,1),
  guests_min integer,
  guests_max integer,
  amenity_filters jsonb not null default '{}'::jsonb,
  active boolean not null default true,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists market.comparable_properties (
  id uuid primary key default gen_random_uuid(),
  property_id uuid not null references app.properties(id) on delete cascade,
  physical_property_group_id uuid,
  provider text not null,
  provider_listing_id text not null,
  channel text,
  listing_url text,
  listing_name text,
  location_name text,
  property_type text,
  latitude numeric(9,6),
  longitude numeric(9,6),
  distance_miles numeric(7,2),
  bedrooms numeric(4,1),
  bathrooms numeric(4,1),
  accommodates integer,
  beds integer,
  rating numeric(3,2) check (rating is null or rating between 0 and 5),
  review_count integer check (review_count is null or review_count >= 0),
  amenities jsonb not null default '{}'::jsonb,
  source_label text not null default 'Manual entry',
  source_observed_at date,
  data_quality text,
  snapshot_notes text,
  included boolean not null default true,
  active boolean not null default true,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (property_id, provider, provider_listing_id)
);

create table if not exists market.public_listing_snapshots (
  id uuid primary key default gen_random_uuid(),
  comparable_property_id uuid not null references market.comparable_properties(id) on delete cascade,
  observed_at timestamptz not null,
  public_metadata jsonb not null default '{}'::jsonb,
  content_sha256 text,
  created_at timestamptz not null default now(),
  unique (comparable_property_id, observed_at)
);

create table if not exists market.rate_observations (
  id uuid primary key default gen_random_uuid(),
  comparable_property_id uuid not null references market.comparable_properties(id) on delete cascade,
  observed_at timestamptz not null default now(),
  check_in date not null,
  check_out date not null,
  guests integer not null check (guests > 0),
  available boolean,
  nightly_rate numeric(12,2),
  cleaning_fee numeric(12,2),
  taxes_and_fees numeric(12,2),
  total_stay_price numeric(12,2),
  currency char(3) not null default 'USD',
  taxes_fees_included boolean,
  source_url text,
  scenario_key text,
  notes text,
  check (check_out > check_in)
);

create table if not exists market.monthly_metrics (
  id uuid primary key default gen_random_uuid(),
  comparable_property_id uuid not null references market.comparable_properties(id) on delete cascade,
  month_start date not null,
  adr numeric(12,2),
  occupancy_percent numeric(6,3) check (occupancy_percent is null or occupancy_percent between 0 and 100),
  revenue numeric(14,2),
  revpar numeric(12,2),
  metric_type text not null default 'observed' check (metric_type in ('observed','provider_estimate','owner_actual')),
  source_label text,
  observed_at timestamptz not null default now(),
  unique (comparable_property_id, month_start, metric_type)
);

create table if not exists market.import_runs (
  id uuid primary key default gen_random_uuid(),
  property_id uuid not null references app.properties(id) on delete cascade,
  provider text not null,
  import_type text not null check (import_type in ('public_snapshot','rate_observation','monthly_metrics','csv','api')),
  status text not null default 'running' check (status in ('running','success','partial','failed')),
  rows_seen integer not null default 0,
  rows_inserted integer not null default 0,
  rows_updated integer not null default 0,
  rows_rejected integer not null default 0,
  started_at timestamptz not null default now(),
  finished_at timestamptz,
  error_message text
);

create index if not exists comparable_properties_property_included_idx
  on market.comparable_properties(property_id, included, active);
create index if not exists rate_observations_comp_dates_idx
  on market.rate_observations(comparable_property_id, check_in, check_out, observed_at desc);
create index if not exists monthly_metrics_comp_month_idx
  on market.monthly_metrics(comparable_property_id, month_start);

create trigger market_provider_configs_touch_updated_at before update on market.provider_configs
for each row execute function app.touch_updated_at();
create trigger market_search_profiles_touch_updated_at before update on market.search_profiles
for each row execute function app.touch_updated_at();
create trigger comparable_properties_touch_updated_at before update on market.comparable_properties
for each row execute function app.touch_updated_at();

insert into app.schema_migrations(version, description)
values ('006', 'Market comparable properties, public snapshots, recurring rate observations, and provider imports')
on conflict (version) do nothing;

commit;


begin;

create table if not exists ai.bot_configs (
  id uuid primary key default gen_random_uuid(),
  property_id uuid not null references app.properties(id) on delete cascade,
  public_enabled boolean not null default false,
  guest_portal_enabled boolean not null default false,
  provider text not null default 'openai',
  credential_id uuid references secure.integration_credentials(id) on delete set null,
  model_name text,
  system_rules text,
  rate_limit_per_hour integer not null default 30 check (rate_limit_per_hour between 1 and 10000),
  configuration jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (property_id)
);

create table if not exists ai.knowledge_documents (
  id uuid primary key default gen_random_uuid(),
  property_id uuid not null references app.properties(id) on delete cascade,
  document_key text not null,
  title text not null,
  document_type text not null,
  visibility text not null check (visibility in ('public','authenticated_guest','staff_private')),
  active boolean not null default true,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (property_id, document_key)
);

create table if not exists ai.knowledge_document_versions (
  id uuid primary key default gen_random_uuid(),
  knowledge_document_id uuid not null references ai.knowledge_documents(id) on delete cascade,
  version integer not null,
  content_text text,
  storage_path text,
  content_sha256 text not null,
  metadata jsonb not null default '{}'::jsonb,
  approved_by uuid references app.users(id) on delete set null,
  approved_at timestamptz,
  created_at timestamptz not null default now(),
  unique (knowledge_document_id, version)
);

create table if not exists ai.conversations (
  id uuid primary key default gen_random_uuid(),
  property_id uuid not null references app.properties(id) on delete cascade,
  mode text not null check (mode in ('public','authenticated_guest','staff')),
  anonymous_session_hash bytea,
  reservation_id uuid references booking.reservations(id) on delete set null,
  guest_access_token_id uuid references secure.guest_access_tokens(id) on delete set null,
  status text not null default 'open' check (status in ('open','escalated','resolved','expired')),
  started_at timestamptz not null default now(),
  last_message_at timestamptz not null default now(),
  expires_at timestamptz,
  metadata jsonb not null default '{}'::jsonb
);

create table if not exists ai.messages (
  id bigint generated always as identity primary key,
  conversation_id uuid not null references ai.conversations(id) on delete cascade,
  role text not null check (role in ('user','assistant','system','tool')),
  content_ciphertext bytea,
  content_redacted text,
  encryption_key_version smallint not null default 1,
  model_name text,
  input_tokens integer,
  output_tokens integer,
  safety_result jsonb,
  created_at timestamptz not null default now(),
  check (content_ciphertext is not null or content_redacted is not null)
);

create table if not exists ai.tool_calls (
  id uuid primary key default gen_random_uuid(),
  conversation_id uuid not null references ai.conversations(id) on delete cascade,
  message_id bigint references ai.messages(id) on delete set null,
  tool_name text not null,
  request_payload_redacted jsonb not null default '{}'::jsonb,
  response_payload_redacted jsonb not null default '{}'::jsonb,
  status text not null check (status in ('requested','confirmed','completed','failed','denied')),
  confirmation_required boolean not null default false,
  confirmed_at timestamptz,
  started_at timestamptz not null default now(),
  completed_at timestamptz,
  error_message text
);

create table if not exists ai.escalations (
  id uuid primary key default gen_random_uuid(),
  conversation_id uuid not null references ai.conversations(id) on delete cascade,
  contact_request_id uuid references messaging.contact_requests(id) on delete set null,
  reason text not null,
  priority text not null default 'normal' check (priority in ('low','normal','high','urgent')),
  status text not null default 'open' check (status in ('open','assigned','resolved','closed')),
  assigned_user_id uuid references app.users(id) on delete set null,
  created_at timestamptz not null default now(),
  resolved_at timestamptz
);

alter table messaging.contact_requests
  drop constraint if exists contact_requests_conversation_fk;
alter table messaging.contact_requests
  add constraint contact_requests_conversation_fk
  foreign key (conversation_id) references ai.conversations(id) on delete set null;

create table if not exists ai.feedback (
  id uuid primary key default gen_random_uuid(),
  conversation_id uuid not null references ai.conversations(id) on delete cascade,
  message_id bigint references ai.messages(id) on delete set null,
  rating smallint check (rating between 1 and 5),
  helpful boolean,
  comment_ciphertext bytea,
  created_at timestamptz not null default now()
);

create table if not exists ai.usage_daily (
  property_id uuid not null references app.properties(id) on delete cascade,
  usage_date date not null,
  provider text not null,
  model_name text not null,
  conversations integer not null default 0,
  input_tokens bigint not null default 0,
  output_tokens bigint not null default 0,
  tool_calls integer not null default 0,
  escalations integer not null default 0,
  estimated_cost_usd numeric(12,4) not null default 0,
  primary key (property_id, usage_date, provider, model_name)
);

create index if not exists ai_conversations_property_started_idx
  on ai.conversations(property_id, started_at desc);
create index if not exists ai_messages_conversation_idx
  on ai.messages(conversation_id, created_at);

create trigger ai_bot_configs_touch_updated_at before update on ai.bot_configs
for each row execute function app.touch_updated_at();
create trigger knowledge_documents_touch_updated_at before update on ai.knowledge_documents
for each row execute function app.touch_updated_at();

insert into app.schema_migrations(version, description)
values ('007', 'Property-scoped AI knowledge, conversations, tools, escalations, feedback, and cost tracking')
on conflict (version) do nothing;

commit;


begin;

create table if not exists analytics.web_sessions (
  id uuid primary key default gen_random_uuid(),
  organization_id uuid references app.organizations(id) on delete cascade,
  property_id uuid references app.properties(id) on delete cascade,
  anonymous_session_hash bytea not null,
  consent_status text not null default 'unknown' check (consent_status in ('unknown','essential_only','analytics_allowed','declined')),
  first_seen_at timestamptz not null default now(),
  last_seen_at timestamptz not null default now(),
  landing_path text,
  referrer_host text,
  utm_source text,
  utm_medium text,
  utm_campaign text,
  device_category text,
  country_code char(2),
  user_agent_hash bytea,
  ip_prefix_hash bytea,
  metadata jsonb not null default '{}'::jsonb
);

create index if not exists web_sessions_property_first_seen_idx
  on analytics.web_sessions(property_id, first_seen_at desc);

create table if not exists analytics.page_views (
  id bigint generated always as identity primary key,
  session_id uuid not null references analytics.web_sessions(id) on delete cascade,
  property_id uuid references app.properties(id) on delete cascade,
  path text not null,
  page_title text,
  referrer_path text,
  occurred_at timestamptz not null default now(),
  duration_seconds integer,
  scroll_depth_percent numeric(5,2),
  metadata jsonb not null default '{}'::jsonb
);

create index if not exists page_views_property_time_idx
  on analytics.page_views(property_id, occurred_at desc);

create table if not exists analytics.journey_events (
  id bigint generated always as identity primary key,
  session_id uuid references analytics.web_sessions(id) on delete set null,
  property_id uuid references app.properties(id) on delete cascade,
  event_name text not null,
  funnel_stage text,
  reservation_id uuid references booking.reservations(id) on delete set null,
  booking_request_id uuid references booking.booking_requests(id) on delete set null,
  occurred_at timestamptz not null default now(),
  properties jsonb not null default '{}'::jsonb
);

create index if not exists journey_events_property_stage_time_idx
  on analytics.journey_events(property_id, funnel_stage, occurred_at desc);

create table if not exists analytics.business_events (
  id bigint generated always as identity primary key,
  organization_id uuid references app.organizations(id) on delete cascade,
  property_id uuid references app.properties(id) on delete cascade,
  event_name text not null,
  entity_type text,
  entity_id text,
  amount_cents bigint,
  currency char(3),
  occurred_at timestamptz not null default now(),
  dimensions jsonb not null default '{}'::jsonb
);

create table if not exists analytics.service_health_samples (
  id bigint generated always as identity primary key,
  service_name text not null,
  environment text not null default 'development',
  property_id uuid references app.properties(id) on delete cascade,
  status text not null check (status in ('healthy','degraded','unhealthy')),
  response_time_ms integer,
  error_code text,
  checked_at timestamptz not null default now(),
  metadata jsonb not null default '{}'::jsonb
);

create index if not exists health_samples_service_time_idx
  on analytics.service_health_samples(service_name, checked_at desc);

create table if not exists analytics.http_metrics_hourly (
  bucket_start timestamptz not null,
  service_name text not null,
  route_pattern text not null,
  method text not null,
  request_count bigint not null default 0,
  error_count bigint not null default 0,
  p50_latency_ms numeric(12,2),
  p95_latency_ms numeric(12,2),
  p99_latency_ms numeric(12,2),
  bytes_in bigint not null default 0,
  bytes_out bigint not null default 0,
  primary key (bucket_start, service_name, route_pattern, method)
);

create table if not exists analytics.business_metrics_daily (
  metric_date date not null,
  property_id uuid not null references app.properties(id) on delete cascade,
  visits integer not null default 0,
  unique_sessions integer not null default 0,
  availability_searches integer not null default 0,
  booking_started integer not null default 0,
  booking_submitted integer not null default 0,
  booking_confirmed integer not null default 0,
  abandoned_booking integer not null default 0,
  gross_revenue_cents bigint not null default 0,
  occupied_nights integer not null default 0,
  chatbot_conversations integer not null default 0,
  chatbot_escalations integer not null default 0,
  primary key (metric_date, property_id)
);

create table if not exists analytics.consent_events (
  id bigint generated always as identity primary key,
  session_id uuid references analytics.web_sessions(id) on delete cascade,
  old_status text,
  new_status text not null,
  occurred_at timestamptz not null default now(),
  policy_version text
);

insert into app.schema_migrations(version, description)
values ('008', 'Privacy-aware web analytics, user journey, technical health, and business metrics')
on conflict (version) do nothing;

commit;


begin;

create or replace function app.has_org_role(p_organization_id uuid, p_allowed_roles text[])
returns boolean
language sql
stable
security definer
set search_path = app, public
as $$
  select exists (
    select 1
    from app.organization_members m
    where m.organization_id = p_organization_id
      and m.user_id = app.current_user_id()
      and m.role = any(p_allowed_roles)
  );
$$;

create or replace function app.has_property_role(p_property_id uuid, p_allowed_roles text[])
returns boolean
language sql
stable
security definer
set search_path = app, public
as $$
  select exists (
    select 1
    from app.properties p
    where p.id = p_property_id
      and (
        app.has_org_role(p.organization_id, p_allowed_roles)
        or exists (
          select 1 from app.property_members m
          where m.property_id = p_property_id
            and m.user_id = app.current_user_id()
            and m.role = any(p_allowed_roles)
        )
      )
  );
$$;

create or replace function app.can_read_property(p_property_id uuid)
returns boolean language sql stable as $$
  select app.has_property_role(
    p_property_id,
    array['portfolio_owner','portfolio_admin','property_owner','manager','cohost','cleaner','maintenance','accountant','readonly']
  );
$$;

create or replace function app.can_manage_property(p_property_id uuid)
returns boolean language sql stable as $$
  select app.has_property_role(
    p_property_id,
    array['portfolio_owner','portfolio_admin','property_owner','manager','cohost']
  );
$$;

create or replace function app.can_admin_property(p_property_id uuid)
returns boolean language sql stable as $$
  select app.has_property_role(
    p_property_id,
    array['portfolio_owner','portfolio_admin','property_owner','manager']
  );
$$;

create or replace function booking.is_available(
  p_property_id uuid,
  p_check_in date,
  p_check_out date,
  p_exclude_reservation_id uuid default null
)
returns boolean
language sql
stable
as $$
  select p_check_out > p_check_in
    and not exists (
      select 1 from booking.reservations r
      where r.property_id = p_property_id
        and r.status in ('hold','pending','confirmed','blocked')
        and not r.conflict_override
        and (p_exclude_reservation_id is null or r.id <> p_exclude_reservation_id)
        and r.stay_range && daterange(p_check_in, p_check_out, '[)')
    )
    and not exists (
      select 1 from booking.calendar_blocks b
      where b.property_id = p_property_id
        and b.active
        and not b.conflict_override
        and b.stay_range && daterange(p_check_in, p_check_out, '[)')
    );
$$;

create or replace view api.public_properties as
select
  p.id,
  p.code,
  p.name,
  p.slug,
  p.public_domain,
  p.public_location_label,
  p.timezone,
  p.check_in_time,
  p.check_out_time,
  p.standard_sleeps,
  p.maximum_requested_guests,
  p.bedrooms,
  p.bathrooms,
  p.beds,
  p.currency,
  coalesce(
    jsonb_object_agg(s.setting_key, s.value_json) filter (where s.setting_key is not null),
    '{}'::jsonb
  ) as public_settings
from app.properties p
left join app.property_settings s on s.property_id = p.id and s.is_public
where p.active and p.publicly_listed
group by p.id;

create or replace view api.property_reporting_summary as
select
  p.id as property_id,
  p.code,
  p.name,
  coalesce(r.reservations, 0) as reservations,
  coalesce(r.occupied_nights, 0) as occupied_nights,
  coalesce(r.gross_revenue_cents, 0) as gross_revenue_cents,
  coalesce(br.pending_booking_requests, 0) as pending_booking_requests
from app.properties p
left join lateral (
  select
    count(*) filter (where status in ('pending','confirmed','completed')) as reservations,
    coalesce(sum(check_out - check_in) filter (where status in ('confirmed','completed')), 0) as occupied_nights,
    coalesce(sum(total_amount_cents) filter (where status in ('confirmed','completed')), 0) as gross_revenue_cents
  from booking.reservations
  where property_id = p.id
) r on true
left join lateral (
  select count(*) filter (where status = 'pending') as pending_booking_requests
  from booking.booking_requests
  where property_id = p.id
) br on true;

create or replace view api.market_snapshot_summary as
select
  cp.property_id,
  count(*) filter (where cp.active) as total_comps,
  count(*) filter (where cp.active and cp.included) as included_comps,
  count(distinct cp.provider) filter (where cp.active) as providers,
  percentile_cont(0.5) within group (order by cp.rating) filter (where cp.rating is not null) as median_rating,
  percentile_cont(0.5) within group (order by cp.review_count) filter (where cp.review_count is not null) as median_review_count,
  max(cp.source_observed_at) as latest_snapshot_date
from market.comparable_properties cp
group by cp.property_id;

create or replace view api.booking_funnel_daily as
select
  property_id,
  occurred_at::date as event_date,
  count(*) filter (where event_name = 'availability_searched') as availability_searches,
  count(*) filter (where event_name = 'booking_started') as booking_started,
  count(*) filter (where event_name = 'booking_submitted') as booking_submitted,
  count(*) filter (where event_name = 'booking_confirmed') as booking_confirmed
from analytics.journey_events
group by property_id, occurred_at::date;

create or replace function api.cleaner_calendar_rows(
  p_token_hash bytea,
  p_property_slug text default null,
  p_from date default current_date - 1,
  p_to date default current_date + 180
)
returns table (
  reservation_id uuid,
  property_id uuid,
  property_code text,
  property_name text,
  property_slug text,
  timezone text,
  check_in_time time,
  check_out_time time,
  cleaning_duration_minutes integer,
  public_location_label text,
  address_line1_ciphertext bytea,
  address_line2_ciphertext bytea,
  city text,
  state_region text,
  postal_code_ciphertext bytea,
  check_in date,
  check_out date,
  guest_count integer,
  source_type text,
  cleaner_note text
)
language sql
stable
security definer
set search_path = secure, booking, app, public
as $$
  select
    r.id,
    p.id,
    p.code,
    p.name,
    p.slug,
    p.timezone,
    p.check_in_time,
    p.check_out_time,
    p.cleaning_duration_minutes,
    p.public_location_label,
    a.address_line1_ciphertext,
    a.address_line2_ciphertext,
    a.city,
    a.state_region,
    a.postal_code_ciphertext,
    r.check_in,
    r.check_out,
    r.adults + r.children,
    r.source_type,
    r.cleaner_note
  from secure.calendar_share_tokens t
  join secure.calendar_share_properties sp on sp.share_token_id = t.id
  join app.properties p on p.id = sp.property_id
  left join secure.property_addresses a on a.property_id = p.id
  join booking.reservations r on r.property_id = p.id
  where t.token_hash = p_token_hash
    and t.active
    and t.revoked_at is null
    and t.audience = 'cleaner'
    and (t.expires_at is null or t.expires_at > now())
    and r.status in ('pending','confirmed')
    and r.check_out >= p_from
    and r.check_in <= p_to
    and (p_property_slug is null or p.slug = p_property_slug)
  order by p.name, r.check_in;
$$;

revoke all on function api.cleaner_calendar_rows(bytea, text, date, date) from public;

insert into app.schema_migrations(version, description)
values ('009', 'Authorization helpers, availability function, safe public/reporting views, and cleaner feed function')
on conflict (version) do nothing;

commit;


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
