\set ON_ERROR_STOP on
begin;

insert into app.organizations(id, name, slug)
values ('aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa', 'QA Organization', 'qa-organization')
on conflict do nothing;

insert into app.properties(
  id, organization_id, code, name, slug, standard_sleeps, maximum_requested_guests
)
values (
  'bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb',
  'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa',
  'QA-01', 'QA Property', 'qa-property', 6, 8
)
on conflict do nothing;

insert into booking.reservations(
  id, property_id, source_type, status, check_in, check_out, adults, children
)
values (
  'cccccccc-cccc-4ccc-8ccc-ccccccccccc1',
  'bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb',
  'direct', 'confirmed', date '2030-01-10', date '2030-01-12', 2, 2
);

do $$
begin
  begin
    insert into booking.reservations(
      id, property_id, source_type, status, check_in, check_out, adults, children
    ) values (
      'cccccccc-cccc-4ccc-8ccc-ccccccccccc2',
      'bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb',
      'airbnb', 'confirmed', date '2030-01-11', date '2030-01-13', 2, 0
    );
    raise exception 'Expected overlap rejection did not occur';
  exception when exclusion_violation then
    null;
  end;
end;
$$;

do $$
begin
  begin
    insert into booking.reservations(
      id, property_id, source_type, status, check_in, check_out, adults, children,
      occupancy_approval_status
    ) values (
      'cccccccc-cccc-4ccc-8ccc-ccccccccccc3',
      'bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb',
      'direct', 'confirmed', date '2030-02-10', date '2030-02-12', 6, 2,
      'required'
    );
    raise exception 'Expected occupancy approval rejection did not occur';
  exception when check_violation then
    null;
  end;
end;
$$;

insert into booking.reservations(
  id, property_id, source_type, status, check_in, check_out, adults, children,
  occupancy_approval_status
) values (
  'cccccccc-cccc-4ccc-8ccc-ccccccccccc4',
  'bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb',
  'direct', 'confirmed', date '2030-02-10', date '2030-02-12', 6, 2,
  'approved'
);

do $$
begin
  if booking.is_available(
    'bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb', date '2030-03-01', date '2030-03-03'
  ) is not true then
    raise exception 'Expected dates to be available';
  end if;
end;
$$;

rollback;
select 'business rule checks passed' as result;
