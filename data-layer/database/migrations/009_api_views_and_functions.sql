begin;

create or replace function app.has_org_role(p_organization_id uuid, p_allowed_roles text[])
returns boolean
language sql
stable
security definer
set search_path = app, public
as $$
  select exists (
    select 1
    from app.organization_members m
    where m.organization_id = p_organization_id
      and m.user_id = app.current_user_id()
      and m.role = any(p_allowed_roles)
  );
$$;

create or replace function app.has_property_role(p_property_id uuid, p_allowed_roles text[])
returns boolean
language sql
stable
security definer
set search_path = app, public
as $$
  select exists (
    select 1
    from app.properties p
    where p.id = p_property_id
      and (
        app.has_org_role(p.organization_id, p_allowed_roles)
        or exists (
          select 1 from app.property_members m
          where m.property_id = p_property_id
            and m.user_id = app.current_user_id()
            and m.role = any(p_allowed_roles)
        )
      )
  );
$$;

create or replace function app.can_read_property(p_property_id uuid)
returns boolean language sql stable as $$
  select app.has_property_role(
    p_property_id,
    array['portfolio_owner','portfolio_admin','property_owner','manager','cohost','cleaner','maintenance','accountant','readonly']
  );
$$;

create or replace function app.can_manage_property(p_property_id uuid)
returns boolean language sql stable as $$
  select app.has_property_role(
    p_property_id,
    array['portfolio_owner','portfolio_admin','property_owner','manager','cohost']
  );
$$;

create or replace function app.can_admin_property(p_property_id uuid)
returns boolean language sql stable as $$
  select app.has_property_role(
    p_property_id,
    array['portfolio_owner','portfolio_admin','property_owner','manager']
  );
$$;

create or replace function booking.is_available(
  p_property_id uuid,
  p_check_in date,
  p_check_out date,
  p_exclude_reservation_id uuid default null
)
returns boolean
language sql
stable
as $$
  select p_check_out > p_check_in
    and not exists (
      select 1 from booking.reservations r
      where r.property_id = p_property_id
        and r.status in ('hold','pending','confirmed','blocked')
        and not r.conflict_override
        and (p_exclude_reservation_id is null or r.id <> p_exclude_reservation_id)
        and r.stay_range && daterange(p_check_in, p_check_out, '[)')
    )
    and not exists (
      select 1 from booking.calendar_blocks b
      where b.property_id = p_property_id
        and b.active
        and not b.conflict_override
        and b.stay_range && daterange(p_check_in, p_check_out, '[)')
    );
$$;

create or replace view api.public_properties as
select
  p.id,
  p.code,
  p.name,
  p.slug,
  p.public_domain,
  p.public_location_label,
  p.timezone,
  p.check_in_time,
  p.check_out_time,
  p.standard_sleeps,
  p.maximum_requested_guests,
  p.bedrooms,
  p.bathrooms,
  p.beds,
  p.currency,
  coalesce(
    jsonb_object_agg(s.setting_key, s.value_json) filter (where s.setting_key is not null),
    '{}'::jsonb
  ) as public_settings
from app.properties p
left join app.property_settings s on s.property_id = p.id and s.is_public
where p.active and p.publicly_listed
group by p.id;

create or replace view api.property_reporting_summary as
select
  p.id as property_id,
  p.code,
  p.name,
  coalesce(r.reservations, 0) as reservations,
  coalesce(r.occupied_nights, 0) as occupied_nights,
  coalesce(r.gross_revenue_cents, 0) as gross_revenue_cents,
  coalesce(br.pending_booking_requests, 0) as pending_booking_requests
from app.properties p
left join lateral (
  select
    count(*) filter (where status in ('pending','confirmed','completed')) as reservations,
    coalesce(sum(check_out - check_in) filter (where status in ('confirmed','completed')), 0) as occupied_nights,
    coalesce(sum(total_amount_cents) filter (where status in ('confirmed','completed')), 0) as gross_revenue_cents
  from booking.reservations
  where property_id = p.id
) r on true
left join lateral (
  select count(*) filter (where status = 'pending') as pending_booking_requests
  from booking.booking_requests
  where property_id = p.id
) br on true;

create or replace view api.market_snapshot_summary as
select
  cp.property_id,
  count(*) filter (where cp.active) as total_comps,
  count(*) filter (where cp.active and cp.included) as included_comps,
  count(distinct cp.provider) filter (where cp.active) as providers,
  percentile_cont(0.5) within group (order by cp.rating) filter (where cp.rating is not null) as median_rating,
  percentile_cont(0.5) within group (order by cp.review_count) filter (where cp.review_count is not null) as median_review_count,
  max(cp.source_observed_at) as latest_snapshot_date
from market.comparable_properties cp
group by cp.property_id;

create or replace view api.booking_funnel_daily as
select
  property_id,
  occurred_at::date as event_date,
  count(*) filter (where event_name = 'availability_searched') as availability_searches,
  count(*) filter (where event_name = 'booking_started') as booking_started,
  count(*) filter (where event_name = 'booking_submitted') as booking_submitted,
  count(*) filter (where event_name = 'booking_confirmed') as booking_confirmed
from analytics.journey_events
group by property_id, occurred_at::date;

create or replace function api.cleaner_calendar_rows(
  p_token_hash bytea,
  p_property_slug text default null,
  p_from date default current_date - 1,
  p_to date default current_date + 180
)
returns table (
  reservation_id uuid,
  property_id uuid,
  property_code text,
  property_name text,
  property_slug text,
  timezone text,
  check_in_time time,
  check_out_time time,
  cleaning_duration_minutes integer,
  public_location_label text,
  address_line1_ciphertext bytea,
  address_line2_ciphertext bytea,
  city text,
  state_region text,
  postal_code_ciphertext bytea,
  check_in date,
  check_out date,
  guest_count integer,
  source_type text,
  cleaner_note text
)
language sql
stable
security definer
set search_path = secure, booking, app, public
as $$
  select
    r.id,
    p.id,
    p.code,
    p.name,
    p.slug,
    p.timezone,
    p.check_in_time,
    p.check_out_time,
    p.cleaning_duration_minutes,
    p.public_location_label,
    a.address_line1_ciphertext,
    a.address_line2_ciphertext,
    a.city,
    a.state_region,
    a.postal_code_ciphertext,
    r.check_in,
    r.check_out,
    r.adults + r.children,
    r.source_type,
    r.cleaner_note
  from secure.calendar_share_tokens t
  join secure.calendar_share_properties sp on sp.share_token_id = t.id
  join app.properties p on p.id = sp.property_id
  left join secure.property_addresses a on a.property_id = p.id
  join booking.reservations r on r.property_id = p.id
  where t.token_hash = p_token_hash
    and t.active
    and t.revoked_at is null
    and t.audience = 'cleaner'
    and (t.expires_at is null or t.expires_at > now())
    and r.status in ('pending','confirmed')
    and r.check_out >= p_from
    and r.check_in <= p_to
    and (p_property_slug is null or p.slug = p_property_slug)
  order by p.name, r.check_in;
$$;

revoke all on function api.cleaner_calendar_rows(bytea, text, date, date) from public;

insert into app.schema_migrations(version, description)
values ('009', 'Authorization helpers, availability function, safe public/reporting views, and cleaner feed function')
on conflict (version) do nothing;

commit;
