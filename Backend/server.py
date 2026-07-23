#!/usr/bin/env python3
"""Cloud-ready local reference API for Arbor Vista v3.3.

Payments and outbound email are intentionally excluded.
The implementation remains SQLite for local QA, but the interface is
environment-driven, property-scoped, versioned, and portable to PostgreSQL.
"""
from __future__ import annotations
import json, os, sqlite3, uuid, sys
from datetime import datetime, timezone
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from urllib.parse import urlparse, parse_qs

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "Backend"))
from ical_db import init_db, connect, validate_range, sync_url, export_ics, availability

def env_path(name: str, default: Path) -> Path:
    value = os.getenv(name)
    if not value:
        return default
    path = Path(value)
    return path if path.is_absolute() else ROOT / path

DB = env_path("ARBOR_DB_PATH", ROOT / "Backend" / "arborvista_v33.db")
HOST = os.getenv("ARBOR_HOST", "127.0.0.1")
PORT = int(os.getenv("PORT", "8000"))
DEFAULT_PROPERTY_SLUG = os.getenv("ARBOR_DEFAULT_PROPERTY_SLUG", "arbor-vista-retreat")
ALLOWED_ORIGINS = {x.strip() for x in os.getenv(
    "ARBOR_ALLOWED_ORIGINS",
    "http://localhost:8000,http://127.0.0.1:8000"
).split(",") if x.strip()}

def now(): return datetime.now(timezone.utc).isoformat()
def body(handler):
    n = int(handler.headers.get("Content-Length", "0") or 0)
    return json.loads(handler.rfile.read(n) or b"{}")
def rows(cur): return [dict(r) for r in cur.fetchall()]

def resolve_property(conn, handler):
    parsed = urlparse(handler.path)
    query = parse_qs(parsed.query)
    slug = handler.headers.get("X-Property-Slug") or query.get("property", [DEFAULT_PROPERTY_SLUG])[0]
    row = conn.execute("SELECT * FROM properties WHERE slug=? AND active=1", (slug,)).fetchone()
    if not row:
        raise ValueError("Unknown or inactive property.")
    return row

def cors_origin(handler):
    origin = handler.headers.get("Origin")
    if not origin:
        return None
    return origin if origin in ALLOWED_ORIGINS else None

def reply(h, status, data, ctype="application/json"):
    raw = data if isinstance(data, (bytes, bytearray)) else (
        json.dumps(data, indent=2).encode() if ctype == "application/json" else str(data).encode()
    )
    h.send_response(status)
    h.send_header("Content-Type", ctype)
    h.send_header("Content-Length", str(len(raw)))
    origin = cors_origin(h)
    if origin:
        h.send_header("Access-Control-Allow-Origin", origin)
        h.send_header("Vary", "Origin")
    h.send_header("Access-Control-Allow-Headers", "Content-Type, X-Property-Slug, Authorization")
    h.send_header("Access-Control-Allow-Methods", "GET, POST, PATCH, OPTIONS")
    h.send_header("Cache-Control", "no-store")
    h.end_headers()
    h.wfile.write(raw)

def audit(conn, property_id, action, etype, eid, details=None):
    conn.execute(
        "INSERT INTO audit_log(property_id,actor,action,entity_type,entity_id,details_json) VALUES(?,?,?,?,?,?)",
        (property_id, "local-admin", action, etype, eid, json.dumps(details or {}))
    )

def create_booking(data, property_row=None):
    if property_row is None:
        with connect(DB) as _conn:
            property_row = _conn.execute(
                "SELECT * FROM properties WHERE slug=? AND active=1",
                (DEFAULT_PROPERTY_SLUG,)
            ).fetchone()
        if not property_row:
            raise ValueError("Default property is not initialized.")
    start, end = validate_range(data.get("check_in", ""), data.get("check_out", ""))
    adults = int(data.get("adults", 1))
    children = int(data.get("children", 0))
    max_guests = int(data.get("_maximum_requested_guests") or 8)
    if adults < 1 or children < 0 or adults + children > max_guests:
        raise ValueError(f"Guest count must be between 1 and {max_guests} total.")
    first = str(data.get("first_name", "")).strip()
    last = str(data.get("last_name", "")).strip()
    email = str(data.get("email", "")).strip()
    phone = str(data.get("phone", "")).strip()
    legal = str(data.get("legal_name", "")).strip()
    sig = str(data.get("electronic_signature", "")).strip()
    if not all([first, last, email, legal, sig]):
        raise ValueError("Missing required guest or agreement details.")
    if " ".join(sig.lower().split()) != " ".join(legal.lower().split()):
        raise ValueError("Electronic signature must match legal name.")
    property_id = property_row["id"]
    with connect(DB) as conn:
        conn.execute("BEGIN IMMEDIATE")
        conflict = conn.execute(
            "SELECT 1 FROM unavailable_periods WHERE property_id=? AND date(start_date)<date(?) AND date(end_date)>date(?) LIMIT 1",
            (property_id, end, start)
        ).fetchone()
        if conflict:
            raise ValueError("Those dates are no longer available.")
        guest_id = "gst_" + uuid.uuid4().hex[:12]
        res_id = "res_" + uuid.uuid4().hex[:12]
        req_id = "req_" + uuid.uuid4().hex[:12]
        conn.execute("INSERT INTO guests(id,first_name,last_name,email,phone) VALUES(?,?,?,?,?)",
                     (guest_id, first, last, email, phone))
        conn.execute(
            "INSERT INTO reservations(id,property_id,source_type,guest_name,start_date,end_date,status,summary) VALUES(?,?, 'direct', ?,?,?, 'pending',?)",
            (res_id, property_id, f"{first} {last}", start, end, "Direct booking request")
        )
        conn.execute("""INSERT INTO booking_requests
          (id,property_id,reservation_id,guest_id,adults,children,vehicles,special_requests,legal_name,electronic_signature,agreement_date,status)
          VALUES(?,?,?,?,?,?,?,?,?,?,?,'pending')""",
          (req_id, property_id, res_id, guest_id, adults, children, int(data.get("vehicles") or 0),
           data.get("special_requests", ""), legal, sig,
           data.get("agreement_date") or datetime.now().date().isoformat()))
        conn.execute(
            "INSERT INTO documents(id,booking_request_id,document_type,content_json,signed_at) VALUES(?,?,?,?,?)",
            ("doc_" + uuid.uuid4().hex[:12], req_id, "rental_agreement",
             json.dumps({"legal_name": legal, "signature": sig, "agreement_date": data.get("agreement_date")}), now())
        )
        conn.execute(
            "INSERT INTO notification_log(id,booking_request_id,channel,recipient,status,details) VALUES(?,?, 'disabled', 'swasam.venture@gmail.com','disabled','Outbound email intentionally excluded')",
            ("ntf_" + uuid.uuid4().hex[:12], req_id)
        )
        audit(conn, property_id, "create", "booking_request", req_id, {"reservation_id": res_id})
        conn.commit()
    return {"booking_request_id": req_id, "reservation_id": res_id, "status": "pending", "email_status": "disabled"}

# Backward-compatible endpoint: /api/export.ics

def api_path(path: str) -> str:
    if path.startswith("/api/v1"):
        return path[7:] or "/"
    if path.startswith("/api"):
        return path[4:] or "/"
    return path

class Handler(SimpleHTTPRequestHandler):
    def translate_path(self, path):
        path = urlparse(path).path
        rel = path.lstrip("/") or "index.html"
        candidate = ROOT / rel
        if candidate.is_dir():
            candidate = candidate / "index.html"
        return str(candidate)
    def log_message(self, fmt, *args): print("[server]", fmt % args)
    def do_OPTIONS(self): return reply(self, 204, b"", "text/plain")

    def do_GET(self):
        u = urlparse(self.path)
        q = parse_qs(u.query)
        p = api_path(u.path)
        try:
            if u.path.startswith("/api"):
                with connect(DB) as c:
                    prop = resolve_property(c, self)
                property_id = prop["id"]
                if p == "/health":
                    return reply(self, 200, {
                        "status": "ok", "version": "3.3", "apiVersion": "v1",
                        "stripe": "excluded", "email": "excluded",
                        "property": {"id": property_id, "slug": prop["slug"], "name": prop["name"]}
                    })
                if p == "/availability":
                    start, end = validate_range(q.get("start", [""])[0], q.get("end", [""])[0])
                    return reply(self, 200, availability(property_id, start, end, db_path=DB))
                if p == "/reservations":
                    with connect(DB) as c:
                        r = rows(c.execute("""SELECT r.*,g.email,g.phone,b.id booking_request_id,b.adults,b.children,b.vehicles,b.special_requests
                        FROM reservations r LEFT JOIN booking_requests b ON b.reservation_id=r.id
                        LEFT JOIN guests g ON g.id=b.guest_id WHERE r.property_id=? ORDER BY start_date""", (property_id,)))
                    return reply(self, 200, r)
                if p == "/blocks":
                    with connect(DB) as c:
                        r = rows(c.execute("SELECT * FROM calendar_blocks WHERE property_id=? AND active=1 ORDER BY start_date", (property_id,)))
                    return reply(self, 200, r)
                if p == "/calendar-sources":
                    with connect(DB) as c:
                        r = rows(c.execute("SELECT * FROM calendar_sources WHERE property_id=? ORDER BY source_type", (property_id,)))
                    return reply(self, 200, r)
                if p == "/sync-runs":
                    with connect(DB) as c:
                        r = rows(c.execute("""SELECT s.*,c.name source_name FROM sync_runs s
                        JOIN calendar_sources c ON c.id=s.calendar_source_id
                        WHERE c.property_id=? ORDER BY started_at DESC LIMIT 100""", (property_id,)))
                    return reply(self, 200, r)
                if p == "/audit":
                    with connect(DB) as c:
                        r = rows(c.execute("SELECT * FROM audit_log WHERE property_id=? ORDER BY created_at DESC LIMIT 100", (property_id,)))
                    return reply(self, 200, r)
                if p == "/export.ics":
                    ex = q.get("exclude_source", [None])[0]
                    temp = ROOT / "Backend" / "exports" / f"{prop['slug']}-live-export.ics"
                    temp.parent.mkdir(exist_ok=True)
                    export_ics(temp, db_path=DB, property_id=property_id, exclude_source=ex)
                    return reply(self, 200, temp.read_text(encoding="utf-8"), "text/calendar; charset=utf-8")
                return reply(self, 404, {"error": "Not found"})
            return super().do_GET()
        except Exception as e:
            return reply(self, 400, {"error": str(e)})

    def do_POST(self):
        raw_path = urlparse(self.path).path
        p = api_path(raw_path)
        try:
            data = body(self)
            with connect(DB) as c:
                prop = resolve_property(c, self)
            property_id = prop["id"]
            if p == "/booking-requests":
                return reply(self, 201, create_booking(data, prop))
            if p == "/blocks":
                start, end = validate_range(data.get("start_date", ""), data.get("end_date", ""))
                bid = "blk_" + uuid.uuid4().hex[:12]
                with connect(DB) as c:
                    c.execute("BEGIN IMMEDIATE")
                    conflict = c.execute(
                        "SELECT 1 FROM unavailable_periods WHERE property_id=? AND date(start_date)<date(?) AND date(end_date)>date(?) LIMIT 1",
                        (property_id, end, start)
                    ).fetchone()
                    if conflict:
                        raise ValueError("Block conflicts with an existing unavailable period.")
                    c.execute("INSERT INTO calendar_blocks(id,property_id,start_date,end_date,reason) VALUES(?,?,?,?,?)",
                              (bid, property_id, start, end, data.get("reason") or "Owner block"))
                    audit(c, property_id, "create", "calendar_block", bid)
                    c.commit()
                return reply(self, 201, {"id": bid})
            if p.startswith("/sync/"):
                sid = p.rsplit("/", 1)[-1]
                with connect(DB) as c:
                    src = c.execute("SELECT feed_url FROM calendar_sources WHERE id=? AND property_id=?", (sid, property_id)).fetchone()
                if not src or not src["feed_url"]:
                    raise ValueError("Calendar source does not have a feed URL.")
                return reply(self, 200, sync_url(sid, src["feed_url"], db_path=DB))
            return reply(self, 404, {"error": "Not found"})
        except Exception as e:
            return reply(self, 400, {"error": str(e)})

    def do_PATCH(self):
        raw_path = urlparse(self.path).path
        p = api_path(raw_path)
        try:
            data = body(self)
            with connect(DB) as c:
                prop = resolve_property(c, self)
            property_id = prop["id"]
            if p.startswith("/reservations/"):
                rid = p.rsplit("/", 1)[-1]
                status = data.get("status")
                if status not in ("pending", "confirmed", "cancelled", "blocked"):
                    raise ValueError("Invalid status")
                with connect(DB) as c:
                    found = c.execute("SELECT 1 FROM reservations WHERE id=? AND property_id=?", (rid, property_id)).fetchone()
                    if not found:
                        raise ValueError("Reservation not found for this property.")
                    c.execute("UPDATE reservations SET status=? WHERE id=? AND property_id=?", (status, rid, property_id))
                    c.execute("UPDATE booking_requests SET status=? WHERE reservation_id=? AND property_id=?",
                              ({"confirmed":"approved","cancelled":"cancelled","pending":"pending","blocked":"declined"}[status], rid, property_id))
                    audit(c, property_id, "status_change", "reservation", rid, {"status": status})
                    c.commit()
                return reply(self, 200, {"id": rid, "status": status})
            if p.startswith("/calendar-sources/"):
                sid = p.rsplit("/", 1)[-1]
                with connect(DB) as c:
                    c.execute("UPDATE calendar_sources SET feed_url=?,enabled=? WHERE id=? AND property_id=?",
                              (data.get("feed_url"), 1 if data.get("enabled", True) else 0, sid, property_id))
                    if c.total_changes == 0:
                        raise ValueError("Calendar source not found for this property.")
                    audit(c, property_id, "update", "calendar_source", sid)
                    c.commit()
                return reply(self, 200, {"id": sid})
            return reply(self, 404, {"error": "Not found"})
        except Exception as e:
            return reply(self, 400, {"error": str(e)})

def main():
    init_db(DB, reset=False)
    print(f"Arbor Vista v3.3 server: http://{HOST}:{PORT}")
    print(f"Database: {DB}")
    print("API: /api/v1")
    ThreadingHTTPServer((HOST, PORT), Handler).serve_forever()

if __name__ == "__main__":
    main()
