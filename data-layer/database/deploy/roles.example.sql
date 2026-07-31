-- Optional example. Review names and password/authentication strategy before production use.
-- Managed providers may create these roles through their own control plane.

create role arbor_backend nologin;
create role arbor_readonly nologin;

revoke all on schema secure from public;
grant usage on schemas app, booking, messaging, market, ai, analytics, api to arbor_backend;
grant usage on schema secure to arbor_backend;
grant select, insert, update, delete on all tables in schemas app, secure, booking, messaging, market, ai, analytics to arbor_backend;
grant usage, select on all sequences in schemas app, secure, booking, messaging, market, ai, analytics to arbor_backend;
grant execute on all functions in schemas app, booking, messaging, market, ai, analytics, api to arbor_backend;

grant usage on schema api to arbor_readonly;
grant select on all tables in schema api to arbor_readonly;
