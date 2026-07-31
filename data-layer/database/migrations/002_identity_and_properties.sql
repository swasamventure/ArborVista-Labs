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
