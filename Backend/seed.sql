INSERT OR IGNORE INTO organizations(id,name,slug)
VALUES('org_swasam','Swasam Venture','swasam-venture');

INSERT OR IGNORE INTO users(id,email,display_name) VALUES
 ('user_owner','swasam.venture@gmail.com','Portfolio Owner'),
 ('user_manager','manager.demo@local.test','Arbor Vista Manager'),
 ('user_cleaner','cleaner.demo@local.test','Cleaning Team Demo'),
 ('user_accountant','accountant.demo@local.test','Portfolio Accountant');

INSERT OR IGNORE INTO organization_members(organization_id,user_id,role) VALUES
 ('org_swasam','user_owner','portfolio_owner'),
 ('org_swasam','user_accountant','accountant');

INSERT OR IGNORE INTO properties(
 id,organization_id,code,name,slug,public_domain,timezone,check_in_time,check_out_time,
 cleaning_duration_minutes,standard_sleeps,maximum_requested_guests,location_label,city,state,is_demo
) VALUES
 ('prop_arbor_vista','org_swasam','AVR-TN-01','Arbor Vista Retreat','arbor-vista-retreat','arborvistaretreat.com','America/New_York','16:00','10:00',240,6,8,'Arbor Vista Retreat — Shagbark Resort, Sevierville, TN','Sevierville','TN',0),
 ('prop_demo_smokies','org_swasam','DEMO-TN-02','Smoky Mountain Demo Cabin','smoky-mountain-demo-cabin',NULL,'America/New_York','16:00','10:00',240,8,10,'Demo property — Sevierville, TN','Sevierville','TN',1);

INSERT OR IGNORE INTO property_domains(id,property_id,hostname,is_primary) VALUES
 ('domain_avr','prop_arbor_vista','arborvistaretreat.com',1);

INSERT OR IGNORE INTO property_members(property_id,user_id,role) VALUES
 ('prop_arbor_vista','user_owner','property_owner'),
 ('prop_demo_smokies','user_owner','property_owner'),
 ('prop_arbor_vista','user_manager','manager'),
 ('prop_arbor_vista','user_cleaner','cleaner'),
 ('prop_demo_smokies','user_cleaner','cleaner');

INSERT OR IGNORE INTO calendar_sources(id,property_id,source_type,name,feed_url) VALUES
 ('src_airbnb','prop_arbor_vista','airbnb','Airbnb test feed','fixtures/airbnb_sample.ics'),
 ('src_vrbo','prop_arbor_vista','vrbo','Vrbo test feed','fixtures/vrbo_sample.ics'),
 ('src_direct','prop_arbor_vista','direct','Direct bookings',NULL),
 ('src_demo_direct','prop_demo_smokies','direct','Demo direct bookings',NULL);

INSERT OR IGNORE INTO calendar_blocks(id,property_id,start_date,end_date,reason) VALUES
 ('block_owner_001','prop_arbor_vista','2026-10-12','2026-10-15','Owner maintenance visit');

INSERT OR IGNORE INTO reservations(
 id,property_id,calendar_source_id,source_type,guest_name,start_date,end_date,adults,children,total_amount_cents,status,summary,cleaner_note
) VALUES
 ('res_seed_avr_2027','prop_arbor_vista','src_direct','direct','Jordan Smith','2027-02-10','2027-02-13',4,2,180000,'confirmed','Direct reservation','Prepare sofa bed only if approved in dashboard.'),
 ('res_seed_demo_2027','prop_demo_smokies','src_demo_direct','direct','Taylor Jones','2027-02-13','2027-02-17',2,2,160000,'confirmed','Demo reservation','Demo property turnover.');

-- SHA-256 of demo-cleaner-token-change-me. Public demo token only; never use in production.
INSERT OR IGNORE INTO calendar_share_tokens(
 id,organization_id,label,audience,token_hash,created_by
) VALUES(
 'share_cleaner_demo','org_swasam','Portfolio cleaning calendar demo','cleaner',
 'a495154d3f7092a31cacab30d7cacb7d23f998d87838b90f5bc8dafc3444e978','user_owner'
);

INSERT OR IGNORE INTO calendar_share_properties(share_token_id,property_id) VALUES
 ('share_cleaner_demo','prop_arbor_vista'),
 ('share_cleaner_demo','prop_demo_smokies');
