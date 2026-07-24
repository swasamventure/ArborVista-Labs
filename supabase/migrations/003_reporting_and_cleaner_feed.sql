create or replace view public.property_reporting_summary as
select p.id property_id,p.code,p.name,
       count(r.id) filter(where r.status in ('pending','confirmed')) reservations,
       coalesce(sum(r.end_date-r.start_date) filter(where r.status in ('pending','confirmed')),0) occupied_nights,
       coalesce(sum(r.total_amount_cents) filter(where r.status in ('pending','confirmed')),0) gross_revenue_cents
from properties p left join reservations r on r.property_id=p.id
group by p.id,p.code,p.name;

-- Safe rows for the cleaning calendar are returned only after an Edge Function verifies
-- a SHA-256 token against calendar_share_tokens. Guest identity, contact, payment, access-code, and private-guest-note fields are absent.
create or replace function public.cleaner_calendar_rows(p_token_hash text,p_property_slug text default null)
returns table(
  reservation_id uuid,property_id uuid,property_code text,property_name text,property_slug text,
  timezone text,check_in_time time,check_out_time time,cleaning_duration_minutes integer,
  location_label text,address_line1 text,address_line2 text,city text,state text,postal_code text,
  start_date date,end_date date,adults integer,children integer,source_type text,cleaner_note text
) language sql stable security definer set search_path=public as $$
  select r.id,p.id,p.code,p.name,p.slug,p.timezone,p.check_in_time,p.check_out_time,p.cleaning_duration_minutes,
         p.location_label,p.address_line1,p.address_line2,p.city,p.state,p.postal_code,
         r.start_date,r.end_date,r.adults,r.children,r.source_type,r.cleaner_note
  from calendar_share_tokens t
  join calendar_share_properties sp on sp.share_token_id=t.id
  join properties p on p.id=sp.property_id
  join reservations r on r.property_id=p.id
  where t.token_hash=p_token_hash and t.active=true and t.audience='cleaner'
    and (t.expires_at is null or t.expires_at>now())
    and r.status in ('pending','confirmed')
    and (p_property_slug is null or p.slug=p_property_slug)
  order by p.name,r.start_date;
$$;
revoke all on function public.cleaner_calendar_rows(text,text) from public,anon,authenticated;
grant execute on function public.cleaner_calendar_rows(text,text) to service_role;
