-- Arbor Vista Platform v4.0 PostgreSQL/Supabase schema.
create extension if not exists pgcrypto;

create table if not exists organizations (
  id uuid primary key default gen_random_uuid(),
  name text not null,
  slug text not null unique,
  active boolean not null default true,
  created_at timestamptz not null default now()
);

create table if not exists profiles (
  id uuid primary key references auth.users(id) on delete cascade,
  display_name text,
  created_at timestamptz not null default now()
);

create table if not exists organization_members (
  organization_id uuid not null references organizations(id) on delete cascade,
  user_id uuid not null references auth.users(id) on delete cascade,
  role text not null check(role in ('portfolio_owner','portfolio_admin','accountant','readonly')),
  primary key(organization_id,user_id)
);

create table if not exists properties (
  id uuid primary key default gen_random_uuid(),
  organization_id uuid not null references organizations(id) on delete cascade,
  code text not null unique,
  name text not null,
  slug text not null unique,
  public_domain text unique,
  timezone text not null default 'America/New_York',
  check_in_time time not null default '16:00',
  check_out_time time not null default '10:00',
  cleaning_duration_minutes integer not null default 240 check(cleaning_duration_minutes between 30 and 720),
  standard_sleeps integer not null default 6 check(standard_sleeps > 0),
  maximum_requested_guests integer not null default 8 check(maximum_requested_guests >= standard_sleeps),
  location_label text,
  address_line1 text,
  address_line2 text,
  city text,
  state text,
  postal_code text,
  cleaner_notes text,
  active boolean not null default true,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists property_members (
  property_id uuid not null references properties(id) on delete cascade,
  user_id uuid not null references auth.users(id) on delete cascade,
  role text not null check(role in ('property_owner','manager','cohost','cleaner','maintenance','accountant','readonly')),
  primary key(property_id,user_id)
);

create table if not exists calendar_sources (
  id uuid primary key default gen_random_uuid(),
  property_id uuid not null references properties(id) on delete cascade,
  source_type text not null check(source_type in ('airbnb','vrbo','direct','owner','other')),
  name text not null,
  feed_url_encrypted text,
  enabled boolean not null default true,
  last_synced_at timestamptz,
  last_etag text,
  last_modified text,
  created_at timestamptz not null default now(),
  unique(property_id,source_type,name)
);

create table if not exists guests (
  id uuid primary key default gen_random_uuid(),
  first_name text not null,
  last_name text not null,
  email text not null,
  phone text,
  created_at timestamptz not null default now()
);

create table if not exists reservations (
  id uuid primary key default gen_random_uuid(),
  property_id uuid not null references properties(id) on delete cascade,
  calendar_source_id uuid references calendar_sources(id) on delete set null,
  external_uid text,
  source_type text not null check(source_type in ('airbnb','vrbo','direct','owner','other')),
  guest_id uuid references guests(id) on delete set null,
  guest_name text,
  start_date date not null,
  end_date date not null,
  adults integer check(adults is null or adults >= 1),
  children integer check(children is null or children >= 0),
  total_amount_cents bigint check(total_amount_cents is null or total_amount_cents >= 0),
  currency text not null default 'USD',
  status text not null default 'confirmed' check(status in ('pending','confirmed','cancelled','blocked')),
  summary text,
  cleaner_note text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  check(end_date > start_date),
  unique(calendar_source_id,external_uid)
);
create index if not exists reservations_property_dates_idx on reservations(property_id,start_date,end_date,status);

create table if not exists calendar_blocks (
  id uuid primary key default gen_random_uuid(),
  property_id uuid not null references properties(id) on delete cascade,
  start_date date not null,
  end_date date not null,
  reason text not null,
  created_by uuid references auth.users(id) on delete set null,
  active boolean not null default true,
  created_at timestamptz not null default now(),
  check(end_date > start_date)
);

create table if not exists booking_requests (
  id uuid primary key default gen_random_uuid(),
  property_id uuid not null references properties(id) on delete cascade,
  reservation_id uuid references reservations(id) on delete set null,
  guest_id uuid not null references guests(id) on delete restrict,
  adults integer not null check(adults >= 1),
  children integer not null default 0 check(children >= 0),
  vehicles integer not null default 1 check(vehicles >= 0),
  special_requests text,
  legal_name text not null,
  electronic_signature text not null,
  agreement_date date not null,
  status text not null default 'pending' check(status in ('pending','approved','declined','cancelled')),
  created_at timestamptz not null default now()
);

create table if not exists documents (
  id uuid primary key default gen_random_uuid(),
  booking_request_id uuid not null references booking_requests(id) on delete cascade,
  document_type text not null,
  content_json jsonb not null,
  signed_at timestamptz,
  created_at timestamptz not null default now()
);

create table if not exists calendar_share_tokens (
  id uuid primary key default gen_random_uuid(),
  organization_id uuid not null references organizations(id) on delete cascade,
  label text not null,
  audience text not null check(audience in ('cleaner','maintenance','readonly')),
  token_hash text not null unique,
  active boolean not null default true,
  expires_at timestamptz,
  created_by uuid references auth.users(id) on delete set null,
  created_at timestamptz not null default now()
);

create table if not exists calendar_share_properties (
  share_token_id uuid not null references calendar_share_tokens(id) on delete cascade,
  property_id uuid not null references properties(id) on delete cascade,
  primary key(share_token_id,property_id)
);

create table if not exists audit_log (
  id bigint generated always as identity primary key,
  property_id uuid references properties(id) on delete set null,
  actor uuid references auth.users(id) on delete set null,
  action text not null,
  entity_type text not null,
  entity_id text,
  details jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);

create table if not exists data_exports (
  id uuid primary key default gen_random_uuid(),
  property_id uuid not null references properties(id) on delete cascade,
  requested_by uuid references auth.users(id) on delete set null,
  export_type text not null,
  status text not null check(status in ('queued','created','failed')),
  storage_path text,
  manifest jsonb,
  created_at timestamptz not null default now()
);

-- Row Level Security is applied with ALTER TABLE ... ENABLE ROW LEVEL SECURITY in 002_rls_policies.sql.
