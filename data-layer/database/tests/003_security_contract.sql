\set ON_ERROR_STOP on

do $$
declare
  exposed_count integer;
begin
  select count(*) into exposed_count
  from information_schema.columns
  where table_schema = 'api'
    and table_name = 'public_properties'
    and column_name in (
      'address_line1_ciphertext', 'address_line2_ciphertext', 'postal_code_ciphertext',
      'email_ciphertext', 'phone_ciphertext', 'secret_ciphertext'
    );

  if exposed_count <> 0 then
    raise exception 'Public property view exposes protected columns';
  end if;

  if not exists (
    select 1 from pg_class c join pg_namespace n on n.oid = c.relnamespace
    where n.nspname = 'secure' and c.relname = 'guests' and c.relrowsecurity
  ) then
    raise exception 'RLS is not enabled on secure.guests';
  end if;
end;
$$;

select 'security contract checks passed' as result;
