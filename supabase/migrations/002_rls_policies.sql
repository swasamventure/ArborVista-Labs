-- Production authorization foundation. Review in a staging project before enabling live traffic.
create or replace function public.has_org_role(org_id uuid, allowed_roles text[])
returns boolean language sql stable security definer set search_path=public as $$
  select exists(
    select 1 from organization_members m
    where m.organization_id=org_id and m.user_id=auth.uid() and m.role=any(allowed_roles)
  );
$$;

create or replace function public.has_property_role(prop_id uuid, allowed_roles text[])
returns boolean language sql stable security definer set search_path=public as $$
  select exists(
    select 1 from properties p
    where p.id=prop_id and (
      public.has_org_role(p.organization_id,allowed_roles)
      or exists(select 1 from property_members m where m.property_id=prop_id and m.user_id=auth.uid() and m.role=any(allowed_roles))
    )
  );
$$;

alter table organizations enable row level security;
alter table profiles enable row level security;
alter table organization_members enable row level security;
alter table properties enable row level security;
alter table property_members enable row level security;
alter table calendar_sources enable row level security;
alter table guests enable row level security;
alter table reservations enable row level security;
alter table calendar_blocks enable row level security;
alter table booking_requests enable row level security;
alter table documents enable row level security;
alter table calendar_share_tokens enable row level security;
alter table calendar_share_properties enable row level security;
alter table audit_log enable row level security;
alter table data_exports enable row level security;

create policy properties_read on properties for select using(
  public.has_property_role(id,array['portfolio_owner','portfolio_admin','property_owner','manager','cohost','cleaner','maintenance','accountant','readonly'])
);
create policy reservations_read on reservations for select using(
  public.has_property_role(property_id,array['portfolio_owner','portfolio_admin','property_owner','manager','cohost','accountant','readonly'])
);
create policy reservations_manage on reservations for all using(
  public.has_property_role(property_id,array['portfolio_owner','portfolio_admin','property_owner','manager','cohost'])
) with check(
  public.has_property_role(property_id,array['portfolio_owner','portfolio_admin','property_owner','manager','cohost'])
);
create policy blocks_read on calendar_blocks for select using(
  public.has_property_role(property_id,array['portfolio_owner','portfolio_admin','property_owner','manager','cohost','cleaner','maintenance','accountant','readonly'])
);
create policy blocks_manage on calendar_blocks for all using(
  public.has_property_role(property_id,array['portfolio_owner','portfolio_admin','property_owner','manager','cohost'])
) with check(
  public.has_property_role(property_id,array['portfolio_owner','portfolio_admin','property_owner','manager','cohost'])
);
create policy sources_owner_only on calendar_sources for all using(
  public.has_property_role(property_id,array['portfolio_owner','portfolio_admin','property_owner','manager'])
) with check(
  public.has_property_role(property_id,array['portfolio_owner','portfolio_admin','property_owner','manager'])
);
create policy exports_owner_only on data_exports for all using(
  public.has_property_role(property_id,array['portfolio_owner','portfolio_admin','property_owner'])
) with check(
  public.has_property_role(property_id,array['portfolio_owner','portfolio_admin','property_owner'])
);

-- Guest/contact tables are intentionally not readable by cleaner roles.
create policy guests_admin_read on guests for select using(
  exists(select 1 from reservations r where r.guest_id=guests.id and public.has_property_role(r.property_id,array['portfolio_owner','portfolio_admin','property_owner','manager','cohost']))
);
