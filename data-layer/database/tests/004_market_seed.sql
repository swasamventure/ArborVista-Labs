\set ON_ERROR_STOP on

do $$
declare
  comp_count integer;
  performance_count integer;
begin
  select count(*) into comp_count
  from market.comparable_properties
  where property_id = '22222222-2222-4222-8222-222222222222';

  if comp_count <> 83 then
    raise exception 'Expected 83 Arbor Vista comparable properties; found %', comp_count;
  end if;

  select count(*) into performance_count
  from market.monthly_metrics mm
  join market.comparable_properties cp on cp.id = mm.comparable_property_id
  where cp.property_id = '22222222-2222-4222-8222-222222222222';

  if performance_count <> 0 then
    raise exception 'Real Comp Snapshot must not fabricate monthly competitor performance';
  end if;
end;
$$;

select 'market seed checks passed' as result;
