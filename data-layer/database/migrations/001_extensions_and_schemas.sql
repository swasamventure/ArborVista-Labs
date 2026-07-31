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
