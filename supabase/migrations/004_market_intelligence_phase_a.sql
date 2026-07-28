-- Phase A market intelligence schema target for future Supabase deployment.
-- Not required by the GitHub Pages browser preview.
create table if not exists public.comp_search_profiles (
  id uuid primary key default gen_random_uuid(),
  property_id uuid not null references public.properties(id) on delete cascade,
  profile_name text not null default 'Exact match',
  radius_miles numeric(6,2) not null default 5,
  bedrooms_min numeric(4,1), bedrooms_max numeric(4,1),
  bathrooms_min numeric(4,1), bathrooms_max numeric(4,1),
  guests_min integer, guests_max integer,
  amenity_filters jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.comparable_properties (
  id uuid primary key default gen_random_uuid(),
  property_id uuid not null references public.properties(id) on delete cascade,
  physical_property_group_id uuid,
  provider text not null default 'manual',
  provider_listing_id text,
  channel text, listing_url text, listing_name text,
  latitude double precision, longitude double precision, distance_miles numeric(7,2),
  bedrooms numeric(4,1), bathrooms numeric(4,1), accommodates integer, beds integer,
  rating numeric(3,2), review_count integer, amenities jsonb not null default '{}'::jsonb,
  source_label text not null default 'Manual estimate',
  included boolean not null default true,
  observed_at timestamptz, created_at timestamptz not null default now(), updated_at timestamptz not null default now(),
  unique(property_id, provider, provider_listing_id)
);

create table if not exists public.comp_monthly_metrics (
  id uuid primary key default gen_random_uuid(),
  comparable_property_id uuid not null references public.comparable_properties(id) on delete cascade,
  month_start date not null, estimated_adr numeric(12,2), estimated_occupancy numeric(6,3),
  estimated_revenue numeric(14,2), estimated_revpar numeric(12,2), source_label text,
  observed_at timestamptz not null default now(), unique(comparable_property_id, month_start)
);

create table if not exists public.comp_daily_rates (
  id uuid primary key default gen_random_uuid(),
  comparable_property_id uuid not null references public.comparable_properties(id) on delete cascade,
  stay_date date not null, available boolean, nightly_rate numeric(12,2), cleaning_fee numeric(12,2),
  taxes_and_fees numeric(12,2), total_stay_price numeric(12,2), observed_at timestamptz not null default now(),
  unique(comparable_property_id, stay_date, observed_at)
);

create index if not exists comparable_properties_property_idx on public.comparable_properties(property_id, included);
create index if not exists comp_monthly_metrics_comp_month_idx on public.comp_monthly_metrics(comparable_property_id, month_start);
