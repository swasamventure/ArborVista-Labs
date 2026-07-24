#!/usr/bin/env python3
"""Arbor Vista Platform v4.1 local multi-property reference server.

Implemented for Git/local QA:
- Multi-property dashboard APIs
- Reservation and calendar engines
- Local role simulation plus Supabase/RLS migration target
- Portfolio reporting
- Property-transfer export
- Tokenized portfolio cleaning iCal

Deliberately excluded: Stripe and outbound email delivery.
"""
from __future__ import annotations

import json
import os
import sys
import uuid
from datetime import datetime, timezone
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from urllib.parse import parse_qs, urlparse

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "Backend"))

from ical_db import availability, connect, export_ics, init_db, sync_url, validate_range
from operations import (
    ADMIN_ROLES,
    CLEANER_ROLES,
    EXPORT_ROLES,
    REPORT_ROLES,
    AccessDenied,
    authorized_properties,
    cleaning_feed_ics,
    list_blocks,
    list_calendar_sources,
    list_reservations,
    property_export_bytes,
    report_summary,
    resolve_property_scope,
    user_access,
)


def env_path(name: str, default: Path) -> Path:
    value = os.getenv(name)
    if not value:
        return default
    path = Path(value)
    return path if path.is_absolute() else ROOT / path


DB = env_path("ARBOR_DB_PATH", ROOT / "Backend" / "arborvista_v40.db")
HOST = os.getenv("ARBOR_HOST", "127.0.0.1")
PORT = int(os.getenv("PORT", "8000"))
DEFAULT_PROPERTY_SLUG = os.getenv("ARBOR_DEFAULT_PROPERTY_SLUG", "arbor-vista-retreat")
REQUIRE_DEMO_AUTH = os.getenv("ARBOR_REQUIRE_DEMO_AUTH", "0") == "1"
ALLOWED_ORIGINS = {
    value.strip()
    for value in os.getenv(
        "ARBOR_ALLOWED_ORIGINS",
        "http://localhost:8000,http://127.0.0.1:8000",
    ).split(",")
    if value.strip()
}


class APIError(Exception):
    def __init__(self, status: int, message: str):
        super().__init__(message)
        self.status = status
        self.message = message


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def body(handler) -> dict:
    length = int(handler.headers.get("Content-Length", "0") or 0)
    raw = handler.rfile.read(length) if length else b"{}"
    try:
        return json.loads(raw or b"{}")
    except json.JSONDecodeError as exc:
        raise APIError(400, "Request body must be valid JSON.") from exc


def rows(cursor) -> list[dict]:
    return [dict(row) for row in cursor.fetchall()]


def cors_origin(handler) -> str | None:
    origin = handler.headers.get("Origin")
    if not origin:
        return None
    return origin if origin in ALLOWED_ORIGINS else None


def reply(handler, status: int, data, content_type: str = "application/json", extra_headers: dict | None = None):
    if isinstance(data, (bytes, bytearray)):
        raw = bytes(data)
    elif content_type.startswith("application/json"):
        raw = json.dumps(data, indent=2).encode("utf-8")
    else:
        raw = str(data).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", content_type)
    handler.send_header("Content-Length", str(len(raw)))
    origin = cors_origin(handler)
    if origin:
        handler.send_header("Access-Control-Allow-Origin", origin)
        handler.send_header("Vary", "Origin")
    handler.send_header("Access-Control-Allow-Headers", "Content-Type, X-Property-Slug, X-Demo-User, Authorization")
    handler.send_header("Access-Control-Allow-Methods", "GET, POST, PATCH, OPTIONS")
    handler.send_header("Cache-Control", "no-store")
    for key, value in (extra_headers or {}).items():
        handler.send_header(key, value)
    handler.end_headers()
    handler.wfile.write(raw)


def api_path(path: str) -> str:
    if path.startswith("/api/v1"):
        return path[7:] or "/"
    if path.startswith("/api"):
        return path[4:] or "/"
    return path


def actor_id(handler) -> str:
    user_id = handler.headers.get("X-Demo-User", "").strip()
    if not user_id and not REQUIRE_DEMO_AUTH:
        user_id = "user_owner"
    if not user_id:
        raise APIError(401, "Authentication is required.")
    return user_id


def requested_scope(handler) -> str:
    query = parse_qs(urlparse(handler.path).query)
    return (
        handler.headers.get("X-Property-Slug")
        or query.get("property", [DEFAULT_PROPERTY_SLUG])[0]
        or DEFAULT_PROPERTY_SLUG
    )


def scoped_properties(conn, handler, roles: set[str] = REPORT_ROLES) -> list[dict]:
    try:
        return resolve_property_scope(conn, actor_id(handler), requested_scope(handler), roles)
    except AccessDenied as exc:
        raise APIError(403, str(exc)) from exc


def public_property(conn, handler) -> dict:
    slug = requested_scope(handler)
    if slug == "all":
        slug = DEFAULT_PROPERTY_SLUG
    row = conn.execute("SELECT * FROM properties WHERE slug=? AND active=1", (slug,)).fetchone()
    if not row:
        raise APIError(404, "Unknown or inactive property.")
    return dict(row)


def audit(conn, property_id: str | None, actor: str, action: str, entity_type: str, entity_id: str | None, details=None):
    conn.execute(
        "INSERT INTO audit_log(property_id,actor,action,entity_type,entity_id,details_json) VALUES(?,?,?,?,?,?)",
        (property_id, actor, action, entity_type, entity_id, json.dumps(details or {}, sort_keys=True)),
    )


def create_booking(data: dict, property_row: dict | None = None) -> dict:
    if property_row is None:
        with connect(DB) as conn:
            row = conn.execute("SELECT * FROM properties WHERE slug=? AND active=1", (DEFAULT_PROPERTY_SLUG,)).fetchone()
            property_row = dict(row) if row else None
    if not property_row:
        raise ValueError("Property is not initialized.")

    start, end = validate_range(str(data.get("check_in", "")), str(data.get("check_out", "")))
    adults = int(data.get("adults", 1))
    children = int(data.get("children", 0))
    maximum = int(property_row["maximum_requested_guests"])
    if adults < 1 or children < 0 or adults + children > maximum:
        raise ValueError(f"Guest count must be between 1 and {maximum} total.")

    first = str(data.get("first_name", "")).strip()
    last = str(data.get("last_name", "")).strip()
    email = str(data.get("email", "")).strip()
    phone = str(data.get("phone", "")).strip()
    legal = str(data.get("legal_name", "")).strip()
    signature = str(data.get("electronic_signature", "")).strip()
    if not all([first, last, email, legal, signature]):
        raise ValueError("Missing required guest or agreement details.")
    if " ".join(signature.lower().split()) != " ".join(legal.lower().split()):
        raise ValueError("Electronic signature must match legal name.")

    property_id = property_row["id"]
    with connect(DB) as conn:
        conn.execute("BEGIN IMMEDIATE")
        conflict = conn.execute(
            """SELECT 1 FROM unavailable_periods
               WHERE property_id=? AND date(start_date)<date(?) AND date(end_date)>date(?) LIMIT 1""",
            (property_id, end, start),
        ).fetchone()
        if conflict:
            raise ValueError("Those dates are no longer available.")
        direct_source = conn.execute(
            "SELECT id FROM calendar_sources WHERE property_id=? AND source_type='direct' LIMIT 1",
            (property_id,),
        ).fetchone()
        guest_id = "gst_" + uuid.uuid4().hex[:12]
        reservation_id = "res_" + uuid.uuid4().hex[:12]
        request_id = "req_" + uuid.uuid4().hex[:12]
        conn.execute(
            "INSERT INTO guests(id,first_name,last_name,email,phone) VALUES(?,?,?,?,?)",
            (guest_id, first, last, email, phone),
        )
        conn.execute(
            """INSERT INTO reservations(
                 id,property_id,calendar_source_id,source_type,guest_name,start_date,end_date,
                 adults,children,status,summary,cleaner_note
               ) VALUES(?,?,?,?,?,?,?,?,?,'pending','Direct booking request',?)""",
            (
                reservation_id,
                property_id,
                direct_source["id"] if direct_source else None,
                "direct",
                f"{first} {last}",
                start,
                end,
                adults,
                children,
                "Guest count and turnover details available in the dashboard.",
            ),
        )
        conn.execute(
            """INSERT INTO booking_requests(
                 id,property_id,reservation_id,guest_id,adults,children,vehicles,special_requests,
                 legal_name,electronic_signature,agreement_date,status
               ) VALUES(?,?,?,?,?,?,?,?,?,?,?,'pending')""",
            (
                request_id,
                property_id,
                reservation_id,
                guest_id,
                adults,
                children,
                int(data.get("vehicles") or 0),
                data.get("special_requests", ""),
                legal,
                signature,
                data.get("agreement_date") or datetime.now().date().isoformat(),
            ),
        )
        conn.execute(
            "INSERT INTO documents(id,booking_request_id,document_type,content_json,signed_at) VALUES(?,?,?,?,?)",
            (
                "doc_" + uuid.uuid4().hex[:12],
                request_id,
                "rental_agreement",
                json.dumps({"legal_name": legal, "signature": signature, "agreement_date": data.get("agreement_date")}),
                now(),
            ),
        )
        conn.execute(
            """INSERT INTO notification_log(id,booking_request_id,channel,recipient,status,details)
               VALUES(?,?,'disabled','swasam.venture@gmail.com','disabled','Outbound email intentionally excluded from v4.1')""",
            ("ntf_" + uuid.uuid4().hex[:12], request_id),
        )
        audit(conn, property_id, "public-booking-form", "create", "booking_request", request_id, {"reservation_id": reservation_id})
        conn.commit()
    return {
        "booking_request_id": request_id,
        "reservation_id": reservation_id,
        "property_id": property_id,
        "property_code": property_row["code"],
        "status": "pending",
        "email_status": "disabled",
    }


class Handler(SimpleHTTPRequestHandler):
    def translate_path(self, path):
        rel = urlparse(path).path.lstrip("/") or "index.html"
        candidate = ROOT / rel
        if candidate.is_dir():
            candidate = candidate / "index.html"
        return str(candidate)

    def log_message(self, fmt, *args):
        print("[server]", fmt % args)

    def do_OPTIONS(self):
        return reply(self, 204, b"", "text/plain")

    def do_GET(self):
        parsed = urlparse(self.path)
        path = api_path(parsed.path)
        query = parse_qs(parsed.query)
        try:
            if not parsed.path.startswith("/api"):
                return super().do_GET()

            # Token-protected external feed; no dashboard authentication required.
            if path == "/ical/cleaning.ics":
                token = query.get("token", [""])[0]
                property_slug = query.get("property", [None])[0]
                if not token:
                    raise APIError(401, "Cleaning calendar token is required.")
                with connect(DB) as conn:
                    text, event_count, property_codes = cleaning_feed_ics(conn, token, property_slug)
                return reply(
                    self,
                    200,
                    text,
                    "text/calendar; charset=utf-8",
                    {"X-Arbor-Event-Count": str(event_count), "X-Arbor-Property-Codes": ",".join(property_codes)},
                )

            if path == "/health":
                return reply(self, 200, {
                    "status": "ok",
                    "version": "4.1",
                    "apiVersion": "v1",
                    "architecture": "multi-property",
                    "stripe": "excluded",
                    "email": "excluded",
                    "cleaningCalendar": "enabled-local-reference",
                })

            if path == "/auth/users":
                with connect(DB) as conn:
                    data = rows(conn.execute("SELECT id,email,display_name,active FROM users WHERE active=1 ORDER BY display_name"))
                return reply(self, 200, data)

            with connect(DB) as conn:
                user_id = actor_id(self)
                if path == "/auth/me":
                    access = user_access(conn, user_id)
                    user = dict(conn.execute("SELECT id,email,display_name FROM users WHERE id=?", (user_id,)).fetchone())
                    user["organization_roles"] = access.organization_roles
                    user["property_roles"] = access.property_roles
                    return reply(self, 200, user)

                if path == "/properties":
                    return reply(self, 200, authorized_properties(conn, user_id))

                if path == "/availability":
                    prop = public_property(conn, self)
                    start, end = validate_range(query.get("start", [""])[0], query.get("end", [""])[0])
                    return reply(self, 200, availability(prop["id"], start, end, db_path=DB))

                if path == "/reservations":
                    props = scoped_properties(conn, self, REPORT_ROLES)
                    return reply(self, 200, list_reservations(conn, [p["id"] for p in props]))

                if path == "/blocks":
                    props = scoped_properties(conn, self, REPORT_ROLES)
                    return reply(self, 200, list_blocks(conn, [p["id"] for p in props]))

                if path == "/calendar-sources":
                    props = scoped_properties(conn, self, REPORT_ROLES)
                    return reply(self, 200, list_calendar_sources(conn, [p["id"] for p in props]))

                if path == "/calendar/combined":
                    props = scoped_properties(conn, self, REPORT_ROLES)
                    property_ids = [p["id"] for p in props]
                    items = list_reservations(conn, property_ids)
                    blocks = list_blocks(conn, property_ids)
                    for item in blocks:
                        item.update({"source_type": "owner", "status": "blocked", "guest_name": None, "summary": item["reason"]})
                    combined = sorted(items + blocks, key=lambda item: (item["start_date"], item.get("property_name", "")))
                    return reply(self, 200, combined)

                if path == "/sync-runs":
                    props = scoped_properties(conn, self, REPORT_ROLES)
                    ids = [p["id"] for p in props]
                    data = rows(conn.execute(
                        f"""SELECT s.*,c.name source_name,p.code property_code,p.name property_name
                            FROM sync_runs s JOIN calendar_sources c ON c.id=s.calendar_source_id
                            JOIN properties p ON p.id=c.property_id
                            WHERE p.id IN ({','.join('?' for _ in ids)})
                            ORDER BY s.started_at DESC LIMIT 100""",
                        ids,
                    ))
                    return reply(self, 200, data)

                if path == "/audit":
                    props = scoped_properties(conn, self, REPORT_ROLES)
                    ids = [p["id"] for p in props]
                    data = rows(conn.execute(
                        f"""SELECT a.*,p.code property_code,p.name property_name FROM audit_log a
                            LEFT JOIN properties p ON p.id=a.property_id
                            WHERE a.property_id IN ({','.join('?' for _ in ids)})
                            ORDER BY a.created_at DESC LIMIT 100""",
                        ids,
                    ))
                    return reply(self, 200, data)

                if path == "/reports/summary":
                    props = scoped_properties(conn, self, REPORT_ROLES)
                    result = report_summary(
                        conn,
                        [p["id"] for p in props],
                        query.get("start", [None])[0],
                        query.get("end", [None])[0],
                    )
                    return reply(self, 200, result)

                if path == "/cleaning-feed/info":
                    props = scoped_properties(conn, self, ADMIN_ROLES | {"cleaner", "maintenance"})
                    base = f"http://{HOST}:{PORT}/api/v1/ical/cleaning.ics"
                    return reply(self, 200, {
                        "feed_url_template": base + "?token=YOUR_PRIVATE_TOKEN",
                        "demo_feed_url": base + "?token=demo-cleaner-token-change-me",
                        "properties": [{"id": p["id"], "code": p["code"], "name": p["name"], "slug": p["slug"]} for p in props],
                        "privacy": "Includes property identity, arrival/departure timing, guest count, source, reservation reference, and turnover details. Guest names, email, phone, payment information, door codes, and private guest notes are excluded.",
                    })

                if path == "/export.ics":
                    props = scoped_properties(conn, self, REPORT_ROLES)
                    if len(props) != 1:
                        raise APIError(400, "Select one property for a channel availability export.")
                    excluded = query.get("exclude_source", [None])[0]
                    temp = ROOT / "Backend" / "exports" / f"{props[0]['slug']}-live-export.ics"
                    export_ics(temp, db_path=DB, property_id=props[0]["id"], exclude_source=excluded)
                    return reply(self, 200, temp.read_text(encoding="utf-8"), "text/calendar; charset=utf-8")

                if path == "/property-export/preview":
                    props = scoped_properties(conn, self, EXPORT_ROLES)
                    if len(props) != 1:
                        raise APIError(400, "Select one property to preview its transfer export.")
                    prop = props[0]
                    future = conn.execute(
                        "SELECT COUNT(*) FROM reservations WHERE property_id=? AND end_date>=date('now')",
                        (prop["id"],),
                    ).fetchone()[0]
                    return reply(self, 200, {
                        "property": {"id": prop["id"], "code": prop["code"], "name": prop["name"], "slug": prop["slug"]},
                        "future_reservations": future,
                        "default_privacy": {"guest_names": "redacted", "emails": "excluded", "phones": "excluded", "payments": "excluded"},
                    })

                raise APIError(404, "Not found.")
        except APIError as exc:
            return reply(self, exc.status, {"error": exc.message})
        except AccessDenied as exc:
            return reply(self, 403, {"error": str(exc)})
        except Exception as exc:
            return reply(self, 400, {"error": str(exc)})

    def do_POST(self):
        parsed = urlparse(self.path)
        path = api_path(parsed.path)
        try:
            data = body(self)
            if path == "/booking-requests":
                with connect(DB) as conn:
                    prop = public_property(conn, self)
                return reply(self, 201, create_booking(data, prop))

            with connect(DB) as conn:
                user_id = actor_id(self)
                if path == "/blocks":
                    props = scoped_properties(conn, self, ADMIN_ROLES)
                    if len(props) != 1:
                        raise APIError(400, "Select one property to create an owner block.")
                    prop = props[0]
                    start, end = validate_range(data.get("start_date", ""), data.get("end_date", ""))
                    conflict = conn.execute(
                        """SELECT 1 FROM unavailable_periods
                           WHERE property_id=? AND date(start_date)<date(?) AND date(end_date)>date(?) LIMIT 1""",
                        (prop["id"], end, start),
                    ).fetchone()
                    if conflict:
                        raise APIError(409, "Block conflicts with an existing unavailable period.")
                    block_id = "blk_" + uuid.uuid4().hex[:12]
                    conn.execute(
                        "INSERT INTO calendar_blocks(id,property_id,start_date,end_date,reason,created_by) VALUES(?,?,?,?,?,?)",
                        (block_id, prop["id"], start, end, data.get("reason") or "Owner block", user_id),
                    )
                    audit(conn, prop["id"], user_id, "create", "calendar_block", block_id)
                    conn.commit()
                    return reply(self, 201, {"id": block_id, "property_code": prop["code"]})

                if path.startswith("/sync/"):
                    props = scoped_properties(conn, self, ADMIN_ROLES)
                    source_id = path.rsplit("/", 1)[-1]
                    source = conn.execute(
                        "SELECT * FROM calendar_sources WHERE id=? AND property_id IN ({})".format(
                            ",".join("?" for _ in props)
                        ),
                        [source_id, *[p["id"] for p in props]],
                    ).fetchone()
                    if not source or not source["feed_url"]:
                        raise APIError(400, "Calendar source does not have an HTTPS feed URL.")
                    return reply(self, 200, sync_url(source_id, source["feed_url"], db_path=DB))

                if path == "/property-export":
                    props = scoped_properties(conn, self, EXPORT_ROLES)
                    if len(props) != 1:
                        raise APIError(400, "Select one property to create its transfer export.")
                    include_names = bool(data.get("include_future_guest_names", False))
                    payload, manifest = property_export_bytes(conn, props[0]["slug"], user_id, include_names)
                    conn.commit()
                    filename = f"{props[0]['slug']}-transfer.zip"
                    return reply(
                        self,
                        200,
                        payload,
                        "application/zip",
                        {"Content-Disposition": f'attachment; filename="{filename}"', "X-Arbor-Export-Id": manifest["exportId"]},
                    )

                raise APIError(404, "Not found.")
        except APIError as exc:
            return reply(self, exc.status, {"error": exc.message})
        except AccessDenied as exc:
            return reply(self, 403, {"error": str(exc)})
        except Exception as exc:
            return reply(self, 400, {"error": str(exc)})

    def do_PATCH(self):
        parsed = urlparse(self.path)
        path = api_path(parsed.path)
        try:
            data = body(self)
            with connect(DB) as conn:
                user_id = actor_id(self)
                props = scoped_properties(conn, self, ADMIN_ROLES)
                property_ids = [p["id"] for p in props]
                if path.startswith("/reservations/"):
                    reservation_id = path.rsplit("/", 1)[-1]
                    status = data.get("status")
                    if status not in ("pending", "confirmed", "cancelled", "blocked"):
                        raise APIError(400, "Invalid reservation status.")
                    found = conn.execute(
                        f"SELECT property_id FROM reservations WHERE id=? AND property_id IN ({','.join('?' for _ in property_ids)})",
                        [reservation_id, *property_ids],
                    ).fetchone()
                    if not found:
                        raise APIError(404, "Reservation not found in the selected property scope.")
                    conn.execute("UPDATE reservations SET status=? WHERE id=?", (status, reservation_id))
                    mapped = {"confirmed": "approved", "cancelled": "cancelled", "pending": "pending", "blocked": "declined"}[status]
                    conn.execute("UPDATE booking_requests SET status=? WHERE reservation_id=?", (mapped, reservation_id))
                    audit(conn, found["property_id"], user_id, "status_change", "reservation", reservation_id, {"status": status})
                    conn.commit()
                    return reply(self, 200, {"id": reservation_id, "status": status})

                if path.startswith("/calendar-sources/"):
                    source_id = path.rsplit("/", 1)[-1]
                    found = conn.execute(
                        f"SELECT property_id FROM calendar_sources WHERE id=? AND property_id IN ({','.join('?' for _ in property_ids)})",
                        [source_id, *property_ids],
                    ).fetchone()
                    if not found:
                        raise APIError(404, "Calendar source not found in the selected property scope.")
                    conn.execute(
                        "UPDATE calendar_sources SET feed_url=?,enabled=? WHERE id=?",
                        (data.get("feed_url"), 1 if data.get("enabled", True) else 0, source_id),
                    )
                    audit(conn, found["property_id"], user_id, "update", "calendar_source", source_id)
                    conn.commit()
                    return reply(self, 200, {"id": source_id})

                raise APIError(404, "Not found.")
        except APIError as exc:
            return reply(self, exc.status, {"error": exc.message})
        except AccessDenied as exc:
            return reply(self, 403, {"error": str(exc)})
        except Exception as exc:
            return reply(self, 400, {"error": str(exc)})


def main():
    init_db(DB, reset=False)
    print(f"Arbor Vista Platform v4.1: http://{HOST}:{PORT}")
    print(f"Database: {DB}")
    print("Dashboard: /admin/dashboard.html")
    print("API: /api/v1")
    ThreadingHTTPServer((HOST, PORT), Handler).serve_forever()


if __name__ == "__main__":
    main()
