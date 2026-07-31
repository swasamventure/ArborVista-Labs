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
