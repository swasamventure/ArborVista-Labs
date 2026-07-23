-- Cloud-ready PostgreSQL/Supabase foundation.
create extension if not exists pgcrypto;

create table if not exists organizations (
  id uuid primary key default gen_random_uuid(),
  name text not null,
  created_at timestamptz not null default now()
);

create table if not exists properties (
  id uuid primary key default gen_random_uuid(),
  organization_id uuid not null references organizations(id) on delete cascade,
  slug text not null unique,
  name text not null,
  public_domain text unique,
  timezone text not null default 'America/New_York',
  standard_sleeps integer not null default 6 check (standard_sleeps > 0),
  maximum_requested_guests integer not null default 8 check (maximum_requested_guests >= standard_sleeps),
  active boolean not null default true,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists property_members (
  property_id uuid not null references properties(id) on delete cascade,
  user_id uuid not null,
  role text not null check (role in ('portfolio_owner','property_owner','manager','cohost','cleaner','maintenance','accountant','readonly')),
  primary key (property_id, user_id)
);

create table if not exists reservations (
  id uuid primary key default gen_random_uuid(),
  property_id uuid not null references properties(id) on delete cascade,
  external_uid text,
  source_type text not null check (source_type in ('airbnb','vrbo','direct','owner','other')),
  guest_name text,
  start_date date not null,
  end_date date not null,
  status text not null default 'confirmed' check (status in ('pending','confirmed','cancelled','blocked')),
  summary text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  check (end_date > start_date)
);

create index if not exists reservations_property_dates_idx
on reservations(property_id, start_date, end_date, status);

-- Production deployments must enable RLS and add policies tied to property_members.
alter table properties enable row level security;
alter table property_members enable row level security;
alter table reservations enable row level security;
