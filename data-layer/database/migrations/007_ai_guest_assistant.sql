begin;

create table if not exists ai.bot_configs (
  id uuid primary key default gen_random_uuid(),
  property_id uuid not null references app.properties(id) on delete cascade,
  public_enabled boolean not null default false,
  guest_portal_enabled boolean not null default false,
  provider text not null default 'openai',
  credential_id uuid references secure.integration_credentials(id) on delete set null,
  model_name text,
  system_rules text,
  rate_limit_per_hour integer not null default 30 check (rate_limit_per_hour between 1 and 10000),
  configuration jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (property_id)
);

create table if not exists ai.knowledge_documents (
  id uuid primary key default gen_random_uuid(),
  property_id uuid not null references app.properties(id) on delete cascade,
  document_key text not null,
  title text not null,
  document_type text not null,
  visibility text not null check (visibility in ('public','authenticated_guest','staff_private')),
  active boolean not null default true,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (property_id, document_key)
);

create table if not exists ai.knowledge_document_versions (
  id uuid primary key default gen_random_uuid(),
  knowledge_document_id uuid not null references ai.knowledge_documents(id) on delete cascade,
  version integer not null,
  content_text text,
  storage_path text,
  content_sha256 text not null,
  metadata jsonb not null default '{}'::jsonb,
  approved_by uuid references app.users(id) on delete set null,
  approved_at timestamptz,
  created_at timestamptz not null default now(),
  unique (knowledge_document_id, version)
);

create table if not exists ai.conversations (
  id uuid primary key default gen_random_uuid(),
  property_id uuid not null references app.properties(id) on delete cascade,
  mode text not null check (mode in ('public','authenticated_guest','staff')),
  anonymous_session_hash bytea,
  reservation_id uuid references booking.reservations(id) on delete set null,
  guest_access_token_id uuid references secure.guest_access_tokens(id) on delete set null,
  status text not null default 'open' check (status in ('open','escalated','resolved','expired')),
  started_at timestamptz not null default now(),
  last_message_at timestamptz not null default now(),
  expires_at timestamptz,
  metadata jsonb not null default '{}'::jsonb
);

create table if not exists ai.messages (
  id bigint generated always as identity primary key,
  conversation_id uuid not null references ai.conversations(id) on delete cascade,
  role text not null check (role in ('user','assistant','system','tool')),
  content_ciphertext bytea,
  content_redacted text,
  encryption_key_version smallint not null default 1,
  model_name text,
  input_tokens integer,
  output_tokens integer,
  safety_result jsonb,
  created_at timestamptz not null default now(),
  check (content_ciphertext is not null or content_redacted is not null)
);

create table if not exists ai.tool_calls (
  id uuid primary key default gen_random_uuid(),
  conversation_id uuid not null references ai.conversations(id) on delete cascade,
  message_id bigint references ai.messages(id) on delete set null,
  tool_name text not null,
  request_payload_redacted jsonb not null default '{}'::jsonb,
  response_payload_redacted jsonb not null default '{}'::jsonb,
  status text not null check (status in ('requested','confirmed','completed','failed','denied')),
  confirmation_required boolean not null default false,
  confirmed_at timestamptz,
  started_at timestamptz not null default now(),
  completed_at timestamptz,
  error_message text
);

create table if not exists ai.escalations (
  id uuid primary key default gen_random_uuid(),
  conversation_id uuid not null references ai.conversations(id) on delete cascade,
  contact_request_id uuid references messaging.contact_requests(id) on delete set null,
  reason text not null,
  priority text not null default 'normal' check (priority in ('low','normal','high','urgent')),
  status text not null default 'open' check (status in ('open','assigned','resolved','closed')),
  assigned_user_id uuid references app.users(id) on delete set null,
  created_at timestamptz not null default now(),
  resolved_at timestamptz
);

alter table messaging.contact_requests
  drop constraint if exists contact_requests_conversation_fk;
alter table messaging.contact_requests
  add constraint contact_requests_conversation_fk
  foreign key (conversation_id) references ai.conversations(id) on delete set null;

create table if not exists ai.feedback (
  id uuid primary key default gen_random_uuid(),
  conversation_id uuid not null references ai.conversations(id) on delete cascade,
  message_id bigint references ai.messages(id) on delete set null,
  rating smallint check (rating between 1 and 5),
  helpful boolean,
  comment_ciphertext bytea,
  created_at timestamptz not null default now()
);

create table if not exists ai.usage_daily (
  property_id uuid not null references app.properties(id) on delete cascade,
  usage_date date not null,
  provider text not null,
  model_name text not null,
  conversations integer not null default 0,
  input_tokens bigint not null default 0,
  output_tokens bigint not null default 0,
  tool_calls integer not null default 0,
  escalations integer not null default 0,
  estimated_cost_usd numeric(12,4) not null default 0,
  primary key (property_id, usage_date, provider, model_name)
);

create index if not exists ai_conversations_property_started_idx
  on ai.conversations(property_id, started_at desc);
create index if not exists ai_messages_conversation_idx
  on ai.messages(conversation_id, created_at);

create trigger ai_bot_configs_touch_updated_at before update on ai.bot_configs
for each row execute function app.touch_updated_at();
create trigger knowledge_documents_touch_updated_at before update on ai.knowledge_documents
for each row execute function app.touch_updated_at();

insert into app.schema_migrations(version, description)
values ('007', 'Property-scoped AI knowledge, conversations, tools, escalations, feedback, and cost tracking')
on conflict (version) do nothing;

commit;
