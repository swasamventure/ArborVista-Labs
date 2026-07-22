INSERT OR IGNORE INTO properties (id,name,slug,timezone)
VALUES ('prop_arbor_vista','Arbor Vista Retreat','arbor-vista-retreat','America/New_York');

INSERT OR IGNORE INTO calendar_sources (id,property_id,source_type,name,feed_url)
VALUES
 ('src_airbnb','prop_arbor_vista','airbnb','Airbnb test feed','fixtures/airbnb_sample.ics'),
 ('src_vrbo','prop_arbor_vista','vrbo','Vrbo test feed','fixtures/vrbo_sample.ics'),
 ('src_direct','prop_arbor_vista','direct','Direct bookings',NULL);

INSERT OR IGNORE INTO calendar_blocks (id,property_id,start_date,end_date,reason)
VALUES ('block_owner_001','prop_arbor_vista','2026-10-12','2026-10-15','Owner maintenance visit');
