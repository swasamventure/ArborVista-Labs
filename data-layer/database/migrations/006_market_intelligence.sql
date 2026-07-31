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
