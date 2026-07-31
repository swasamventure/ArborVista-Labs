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
