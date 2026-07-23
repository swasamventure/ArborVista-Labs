PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS properties (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  slug TEXT NOT NULL UNIQUE,
  timezone TEXT NOT NULL DEFAULT 'America/New_York',
  check_in_time TEXT NOT NULL DEFAULT '16:00',
  check_out_time TEXT NOT NULL DEFAULT '10:00',
  active INTEGER NOT NULL DEFAULT 1 CHECK (active IN (0,1)),
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS calendar_sources (
  id TEXT PRIMARY KEY,
  property_id TEXT NOT NULL REFERENCES properties(id) ON DELETE CASCADE,
  source_type TEXT NOT NULL CHECK (source_type IN ('airbnb','vrbo','direct','owner','other')),
  name TEXT NOT NULL,
  feed_url TEXT,
  enabled INTEGER NOT NULL DEFAULT 1 CHECK (enabled IN (0,1)),
  last_synced_at TEXT,
  last_etag TEXT,
  last_modified TEXT,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE(property_id, source_type, name)
);

CREATE TABLE IF NOT EXISTS reservations (
  id TEXT PRIMARY KEY,
  property_id TEXT NOT NULL REFERENCES properties(id) ON DELETE CASCADE,
  calendar_source_id TEXT REFERENCES calendar_sources(id) ON DELETE SET NULL,
  external_uid TEXT,
  source_type TEXT NOT NULL CHECK (source_type IN ('airbnb','vrbo','direct','owner','other')),
  guest_name TEXT,
  start_date TEXT NOT NULL,
  end_date TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'confirmed' CHECK (status IN ('pending','confirmed','cancelled','blocked')),
  summary TEXT,
  raw_ical TEXT,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CHECK (
    date(start_date) IS NOT NULL
    AND date(end_date) IS NOT NULL
    AND date(end_date) > date(start_date)
    AND start_date = date(start_date)
    AND end_date = date(end_date)
  ),
  UNIQUE(calendar_source_id, external_uid)
);

CREATE INDEX IF NOT EXISTS idx_reservations_property_dates
  ON reservations(property_id, start_date, end_date, status);

CREATE TABLE IF NOT EXISTS calendar_blocks (
  id TEXT PRIMARY KEY,
  property_id TEXT NOT NULL REFERENCES properties(id) ON DELETE CASCADE,
  start_date TEXT NOT NULL,
  end_date TEXT NOT NULL,
  reason TEXT NOT NULL,
  created_by TEXT NOT NULL DEFAULT 'owner',
  active INTEGER NOT NULL DEFAULT 1 CHECK (active IN (0,1)),
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CHECK (
    date(start_date) IS NOT NULL
    AND date(end_date) IS NOT NULL
    AND date(end_date) > date(start_date)
    AND start_date = date(start_date)
    AND end_date = date(end_date)
  )
);

CREATE INDEX IF NOT EXISTS idx_blocks_property_dates
  ON calendar_blocks(property_id, start_date, end_date, active);

CREATE TABLE IF NOT EXISTS sync_runs (
  id TEXT PRIMARY KEY,
  calendar_source_id TEXT NOT NULL REFERENCES calendar_sources(id) ON DELETE CASCADE,
  started_at TEXT NOT NULL,
  finished_at TEXT,
  status TEXT NOT NULL CHECK (status IN ('running','success','partial','failed')),
  events_seen INTEGER NOT NULL DEFAULT 0,
  events_inserted INTEGER NOT NULL DEFAULT 0,
  events_updated INTEGER NOT NULL DEFAULT 0,
  events_cancelled INTEGER NOT NULL DEFAULT 0,
  conflicts_found INTEGER NOT NULL DEFAULT 0,
  error_message TEXT
);

CREATE TABLE IF NOT EXISTS audit_log (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  property_id TEXT REFERENCES properties(id) ON DELETE SET NULL,
  actor TEXT NOT NULL,
  action TEXT NOT NULL,
  entity_type TEXT NOT NULL,
  entity_id TEXT,
  details_json TEXT,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TRIGGER IF NOT EXISTS reservations_touch_updated_at
AFTER UPDATE ON reservations
FOR EACH ROW WHEN NEW.updated_at = OLD.updated_at
BEGIN
  UPDATE reservations SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
END;

CREATE TRIGGER IF NOT EXISTS blocks_touch_updated_at
AFTER UPDATE ON calendar_blocks
FOR EACH ROW WHEN NEW.updated_at = OLD.updated_at
BEGIN
  UPDATE calendar_blocks SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
END;

CREATE VIEW IF NOT EXISTS unavailable_periods AS
SELECT property_id, start_date, end_date, source_type AS source, id AS source_id, status
FROM reservations
WHERE status IN ('pending','confirmed','blocked')
UNION ALL
SELECT property_id, start_date, end_date, 'owner' AS source, id AS source_id, 'blocked' AS status
FROM calendar_blocks
WHERE active = 1;


CREATE TABLE IF NOT EXISTS guests (
  id TEXT PRIMARY KEY,
  first_name TEXT NOT NULL,
  last_name TEXT NOT NULL,
  email TEXT NOT NULL,
  phone TEXT,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS booking_requests (
  id TEXT PRIMARY KEY,
  property_id TEXT NOT NULL REFERENCES properties(id) ON DELETE CASCADE,
  reservation_id TEXT REFERENCES reservations(id) ON DELETE SET NULL,
  guest_id TEXT NOT NULL REFERENCES guests(id) ON DELETE RESTRICT,
  adults INTEGER NOT NULL DEFAULT 1 CHECK(adults >= 1),
  children INTEGER NOT NULL DEFAULT 0 CHECK(children >= 0),
  vehicles INTEGER NOT NULL DEFAULT 1 CHECK(vehicles >= 0),
  special_requests TEXT,
  legal_name TEXT NOT NULL,
  electronic_signature TEXT NOT NULL,
  agreement_date TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'pending' CHECK(status IN ('pending','approved','declined','cancelled')),
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS documents (
  id TEXT PRIMARY KEY,
  booking_request_id TEXT NOT NULL REFERENCES booking_requests(id) ON DELETE CASCADE,
  document_type TEXT NOT NULL,
  content_json TEXT NOT NULL,
  signed_at TEXT,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS notification_log (
  id TEXT PRIMARY KEY,
  booking_request_id TEXT REFERENCES booking_requests(id) ON DELETE SET NULL,
  channel TEXT NOT NULL DEFAULT 'disabled',
  recipient TEXT,
  status TEXT NOT NULL CHECK(status IN ('disabled','queued','sent','failed')),
  details TEXT,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);


CREATE TABLE IF NOT EXISTS organizations (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS property_domains (
  id TEXT PRIMARY KEY,
  property_id TEXT NOT NULL REFERENCES properties(id) ON DELETE CASCADE,
  hostname TEXT NOT NULL UNIQUE,
  is_primary INTEGER NOT NULL DEFAULT 0 CHECK(is_primary IN (0,1)),
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS property_members (
  property_id TEXT NOT NULL REFERENCES properties(id) ON DELETE CASCADE,
  user_id TEXT NOT NULL,
  role TEXT NOT NULL CHECK(role IN ('portfolio_owner','property_owner','manager','cohost','cleaner','maintenance','accountant','readonly')),
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY(property_id,user_id)
);
