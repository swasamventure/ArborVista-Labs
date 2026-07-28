-- v4.2.1 future hosted schema; not active on GitHub Pages
create table if not exists public.market_public_listing_snapshots (
  id uuid primary key default gen_random_uuid(), property_id uuid references public.properties(id) on delete cascade,
  provider text not null, provider_listing_id text not null, listing_url text, observed_at timestamptz not null,
  public_metadata jsonb not null default '{}'::jsonb, unique(property_id,provider,provider_listing_id,observed_at)
);
create table if not exists public.market_rate_observations (
  id uuid primary key default gen_random_uuid(), property_id uuid references public.properties(id) on delete cascade,
  provider text not null, provider_listing_id text not null, observed_at timestamptz not null, check_in date, check_out date,
  guests integer, total_price numeric(12,2), nightly_rate numeric(12,2), currency text default 'USD',
  taxes_fees_included boolean, availability_status text, source_url text, notes text
);
