begin;

insert into app.organizations(id, name, slug)
values ('11111111-1111-4111-8111-111111111111', 'Swasam Venture', 'swasam-venture')
on conflict (id) do update set name = excluded.name, slug = excluded.slug;

insert into app.properties(
  id, organization_id, code, name, slug, public_domain, public_location_label,
  timezone, check_in_time, check_out_time, cleaning_duration_minutes,
  standard_sleeps, maximum_requested_guests, bedrooms, bathrooms, beds,
  active, publicly_listed
)
values (
  '22222222-2222-4222-8222-222222222222',
  '11111111-1111-4111-8111-111111111111',
  'AVR-TN-01',
  'Arbor Vista Retreat',
  'arbor-vista-retreat',
  null,
  'Sevierville, Tennessee',
  'America/New_York',
  '16:00',
  '10:00',
  240,
  6,
  8,
  2,
  2.5,
  4,
  true,
  true
)
on conflict (id) do update set
  name = excluded.name,
  code = excluded.code,
  slug = excluded.slug,
  public_location_label = excluded.public_location_label,
  standard_sleeps = excluded.standard_sleeps,
  maximum_requested_guests = excluded.maximum_requested_guests,
  bedrooms = excluded.bedrooms,
  bathrooms = excluded.bathrooms,
  beds = excluded.beds,
  updated_at = now();

insert into app.property_settings(property_id, setting_key, value_json, is_public)
values
  ('22222222-2222-4222-8222-222222222222', 'amenities',
    '{"hotTub":true,"arcade":true,"fireplace":true,"resortAmenities":true,"petFriendly":false}'::jsonb, true),
  ('22222222-2222-4222-8222-222222222222', 'sleeping_arrangements',
    '{"kingSuites":1,"queenSuites":1,"loftTwinBeds":2,"standardGuests":6,"expandedGuests":8,"expandedRequiresApproval":true}'::jsonb, true),
  ('22222222-2222-4222-8222-222222222222', 'house_rules',
    '{"petsAllowed":false,"smokingAllowed":false,"minimumBookingAge":23,"parkingVehicles":3}'::jsonb, true)
on conflict (property_id, setting_key) do update
  set value_json = excluded.value_json, is_public = excluded.is_public, updated_at = now();

insert into app.feature_flags(property_id, flag_key, enabled, configuration)
values
  ('22222222-2222-4222-8222-222222222222', 'direct_booking', true, '{}'::jsonb),
  ('22222222-2222-4222-8222-222222222222', 'email_delivery', false, '{"adapter":"placeholder"}'::jsonb),
  ('22222222-2222-4222-8222-222222222222', 'ai_guest_assistant', false, '{"phase":"v4.3"}'::jsonb),
  ('22222222-2222-4222-8222-222222222222', 'stripe_payments', false, '{"status":"deferred"}'::jsonb)
on conflict (property_id, flag_key) do update
  set enabled = excluded.enabled, configuration = excluded.configuration, updated_at = now();

insert into booking.calendar_sources(id, property_id, source_type, name, enabled)
values
  ('33333333-3333-4333-8333-333333333331', '22222222-2222-4222-8222-222222222222', 'direct', 'Arbor Vista Direct Bookings', true),
  ('33333333-3333-4333-8333-333333333332', '22222222-2222-4222-8222-222222222222', 'owner', 'Owner Blocks', true)
on conflict (id) do nothing;

insert into market.search_profiles(
  id, property_id, profile_name, profile_mode, radius_miles,
  bedrooms_min, bedrooms_max, bathrooms_min, bathrooms_max,
  guests_min, guests_max, amenity_filters, active
)
values
  ('44444444-4444-4444-8444-444444444441', '22222222-2222-4222-8222-222222222222', 'Exact match', 'exact', 5,
   2, 2, 2, 3, 5, 7, '{"hotTub":true}'::jsonb, true),
  ('44444444-4444-4444-8444-444444444442', '22222222-2222-4222-8222-222222222222', 'Expanded match', 'expanded', 12,
   2, 3, 1.5, 3.5, 5, 8, '{"hotTub":true}'::jsonb, true)
on conflict (id) do update set updated_at = now();

insert into messaging.email_provider_configs(
  id, organization_id, property_id, provider_type, from_name, from_address_alias, reply_to_alias, active, configuration
)
values (
  '55555555-5555-4555-8555-555555555551',
  '11111111-1111-4111-8111-111111111111',
  '22222222-2222-4222-8222-222222222222',
  'placeholder',
  'Arbor Vista Retreat',
  'property_booking_sender',
  'owner_primary',
  false,
  '{"futureProviders":["aws_ses","azure_communication_services","resend","smtp"]}'::jsonb
)
on conflict (id) do update set configuration = excluded.configuration, updated_at = now();

insert into messaging.email_templates(
  id, organization_id, property_id, template_key, version, subject_template,
  body_html_template, body_text_template, active, variables_schema
)
values
  ('66666666-6666-4666-8666-666666666661', '11111111-1111-4111-8111-111111111111', '22222222-2222-4222-8222-222222222222',
   'guest_booking_confirmation', 1, 'Your Arbor Vista booking request',
   '<p>Thank you for your Arbor Vista booking request.</p>',
   'Thank you for your Arbor Vista booking request.', true,
   '{"required":["guestFirstName","checkIn","checkOut","guestPortalUrl"]}'::jsonb),
  ('66666666-6666-4666-8666-666666666662', '11111111-1111-4111-8111-111111111111', '22222222-2222-4222-8222-222222222222',
   'guest_pre_arrival_3_day', 1, 'Your Arbor Vista arrival information',
   '<p>Your Arbor Vista stay begins in three days. Open your secure Guest Portal for current details.</p>',
   'Your Arbor Vista stay begins in three days. Open your secure Guest Portal for current details.', true,
   '{"required":["guestFirstName","checkIn","guestPortalUrl"]}'::jsonb),
  ('66666666-6666-4666-8666-666666666663', '11111111-1111-4111-8111-111111111111', '22222222-2222-4222-8222-222222222222',
   'owner_booking_request', 1, 'New Arbor Vista booking request',
   '<p>A new Arbor Vista booking request requires review.</p>',
   'A new Arbor Vista booking request requires review.', true,
   '{"required":["bookingRequestId","checkIn","checkOut","guestCount"]}'::jsonb)
on conflict (id) do update set
  subject_template = excluded.subject_template,
  body_html_template = excluded.body_html_template,
  body_text_template = excluded.body_text_template,
  variables_schema = excluded.variables_schema,
  updated_at = now();

insert into ai.bot_configs(
  id, property_id, public_enabled, guest_portal_enabled, provider, model_name,
  rate_limit_per_hour, configuration
)
values (
  '77777777-7777-4777-8777-777777777771',
  '22222222-2222-4222-8222-222222222222',
  false,
  false,
  'openai',
  null,
  30,
  '{"phase":"v4.3","availabilityTool":false,"hostEscalation":true,"storeRawMessages":false}'::jsonb
)
on conflict (id) do update set configuration = excluded.configuration, updated_at = now();

insert into app.data_retention_policies(organization_id, data_category, retention_days)
values
  ('11111111-1111-4111-8111-111111111111', 'web_analytics_raw', 395),
  ('11111111-1111-4111-8111-111111111111', 'chatbot_messages', 90),
  ('11111111-1111-4111-8111-111111111111', 'email_delivery_logs', 730),
  ('11111111-1111-4111-8111-111111111111', 'audit_log', 2555)
on conflict (organization_id, data_category) do update set retention_days = excluded.retention_days, updated_at = now();

commit;
