\set ON_ERROR_STOP on

do $$
declare
  missing text[];
begin
  select array_agg(expected_name)
  into missing
  from (
    values
      ('app.properties'),
      ('secure.guests'),
      ('booking.reservations'),
      ('booking.calendar_sources'),
      ('messaging.email_outbox'),
      ('market.comparable_properties'),
      ('ai.conversations'),
      ('analytics.page_views')
  ) expected(expected_name)
  where to_regclass(expected_name) is null;

  if missing is not null then
    raise exception 'Missing required tables: %', missing;
  end if;
end;
$$;

select 'schema smoke checks passed' as result;
