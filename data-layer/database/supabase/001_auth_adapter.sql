-- Run only inside a Supabase project after the portable migrations.
begin;

create or replace function app.current_user_id()
returns uuid
language sql
stable
as $$
  select auth.uid();
$$;

create or replace function app.handle_new_supabase_user()
returns trigger
language plpgsql
security definer
set search_path = app, public
as $$
begin
  insert into app.users(id, external_auth_provider, external_auth_subject, display_name)
  values (
    new.id,
    'supabase',
    new.id::text,
    coalesce(new.raw_user_meta_data ->> 'display_name', new.email)
  )
  on conflict (id) do update
    set display_name = excluded.display_name,
        updated_at = now();
  return new;
end;
$$;

drop trigger if exists on_auth_user_created_arbor_vista on auth.users;
create trigger on_auth_user_created_arbor_vista
after insert or update of raw_user_meta_data on auth.users
for each row execute function app.handle_new_supabase_user();

commit;
