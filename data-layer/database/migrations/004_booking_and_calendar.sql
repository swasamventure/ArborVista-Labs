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
