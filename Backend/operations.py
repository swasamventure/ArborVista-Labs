#!/usr/bin/env python3
"""Multi-property operational services for the local reference platform.

This module contains portable business logic that can later be moved to
PostgreSQL/Supabase Edge Functions without changing the browser contract.
"""
from __future__ import annotations

import csv
import hashlib
import io
import json
import uuid
import zipfile
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable
from zoneinfo import ZoneInfo

from ical_db import connect, _fold_ics_line, _ics_escape


ADMIN_ROLES = {"portfolio_owner", "portfolio_admin", "property_owner", "manager", "cohost"}
REPORT_ROLES = ADMIN_ROLES | {"accountant", "readonly"}
CLEANER_ROLES = ADMIN_ROLES | {"cleaner", "maintenance"}
EXPORT_ROLES = {"portfolio_owner", "portfolio_admin", "property_owner"}


class AccessDenied(PermissionError):
    pass


@dataclass(frozen=True)
class UserAccess:
    user_id: str
    organization_roles: dict[str, str]
    property_roles: dict[str, str]

    def is_portfolio_admin(self, organization_id: str) -> bool:
        return self.organization_roles.get(organization_id) in {"portfolio_owner", "portfolio_admin"}


def token_digest(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def user_access(conn, user_id: str) -> UserAccess:
    user = conn.execute("SELECT id FROM users WHERE id=? AND active=1", (user_id,)).fetchone()
    if not user:
        raise AccessDenied("Unknown or inactive user.")
    org_roles = {
        row["organization_id"]: row["role"]
        for row in conn.execute(
            "SELECT organization_id,role FROM organization_members WHERE user_id=?", (user_id,)
        )
    }
    property_roles = {
        row["property_id"]: row["role"]
        for row in conn.execute(
            "SELECT property_id,role FROM property_members WHERE user_id=?", (user_id,)
        )
    }
    return UserAccess(user_id, org_roles, property_roles)


def authorized_properties(conn, user_id: str, include_demo: bool = True) -> list[dict[str, Any]]:
    access = user_access(conn, user_id)
    rows = conn.execute(
        "SELECT * FROM properties WHERE active=1 ORDER BY is_demo,name"
    ).fetchall()
    result = []
    for row in rows:
        if not include_demo and row["is_demo"]:
            continue
        if row["organization_id"] in access.organization_roles or row["id"] in access.property_roles:
            item = dict(row)
            item["role"] = access.organization_roles.get(row["organization_id"]) or access.property_roles.get(row["id"])
            result.append(item)
    return result


def resolve_property_scope(conn, user_id: str, requested_slug: str, required_roles: set[str] = REPORT_ROLES) -> list[dict[str, Any]]:
    access = user_access(conn, user_id)
    available = authorized_properties(conn, user_id)
    if requested_slug == "all":
        # Only portfolio-level roles may aggregate all properties.
        permitted = [p for p in available if access.organization_roles.get(p["organization_id"]) in required_roles]
        if not permitted:
            raise AccessDenied("Portfolio-wide access is not permitted for this user.")
        return permitted
    prop = next((p for p in available if p["slug"] == requested_slug), None)
    if not prop:
        raise AccessDenied("The user is not assigned to this property.")
    role = access.organization_roles.get(prop["organization_id"]) or access.property_roles.get(prop["id"])
    if role not in required_roles:
        raise AccessDenied("The user's role does not permit this action.")
    return [prop]


def _placeholders(count: int) -> str:
    return ",".join("?" for _ in range(count))


def list_reservations(conn, property_ids: list[str]) -> list[dict[str, Any]]:
    if not property_ids:
        return []
    sql = f"""SELECT r.*,p.code property_code,p.name property_name,p.slug property_slug,
                     g.email,g.phone,b.id booking_request_id,b.vehicles,b.special_requests
              FROM reservations r
              JOIN properties p ON p.id=r.property_id
              LEFT JOIN booking_requests b ON b.reservation_id=r.id
              LEFT JOIN guests g ON g.id=b.guest_id
              WHERE r.property_id IN ({_placeholders(len(property_ids))})
              ORDER BY r.start_date,p.name"""
    return [dict(r) for r in conn.execute(sql, property_ids).fetchall()]


def list_blocks(conn, property_ids: list[str]) -> list[dict[str, Any]]:
    if not property_ids:
        return []
    sql = f"""SELECT b.*,p.code property_code,p.name property_name,p.slug property_slug
              FROM calendar_blocks b JOIN properties p ON p.id=b.property_id
              WHERE b.active=1 AND b.property_id IN ({_placeholders(len(property_ids))})
              ORDER BY b.start_date,p.name"""
    return [dict(r) for r in conn.execute(sql, property_ids).fetchall()]


def list_calendar_sources(conn, property_ids: list[str]) -> list[dict[str, Any]]:
    if not property_ids:
        return []
    sql = f"""SELECT c.*,p.code property_code,p.name property_name,p.slug property_slug
              FROM calendar_sources c JOIN properties p ON p.id=c.property_id
              WHERE c.property_id IN ({_placeholders(len(property_ids))})
              ORDER BY p.name,c.source_type"""
    return [dict(r) for r in conn.execute(sql, property_ids).fetchall()]


def report_summary(conn, property_ids: list[str], start_date: str | None = None, end_date: str | None = None) -> dict[str, Any]:
    if not property_ids:
        return {"portfolio": {}, "properties": []}
    start = date.fromisoformat(start_date) if start_date else date.today().replace(month=1, day=1)
    end = date.fromisoformat(end_date) if end_date else date(start.year + 1, 1, 1)
    if end <= start:
        raise ValueError("Report end date must be after start date.")

    properties = {
        r["id"]: dict(r)
        for r in conn.execute(
            f"SELECT id,code,name,slug,is_demo FROM properties WHERE id IN ({_placeholders(len(property_ids))})",
            property_ids,
        ).fetchall()
    }
    rows = conn.execute(
        f"""SELECT * FROM reservations
             WHERE property_id IN ({_placeholders(len(property_ids))})
               AND status IN ('pending','confirmed')
               AND date(start_date)<date(?) AND date(end_date)>date(?)""",
        [*property_ids, end.isoformat(), start.isoformat()],
    ).fetchall()

    metrics: dict[str, dict[str, Any]] = {}
    for pid, prop in properties.items():
        metrics[pid] = {
            "property_id": pid,
            "property_code": prop["code"],
            "property_name": prop["name"],
            "property_slug": prop["slug"],
            "is_demo": bool(prop["is_demo"]),
            "reservations": 0,
            "occupied_nights": 0,
            "arrivals": 0,
            "departures": 0,
            "guest_nights": 0,
            "gross_revenue_cents": 0,
            "sources": {"airbnb": 0, "vrbo": 0, "direct": 0, "owner": 0, "other": 0},
        }
    for row in rows:
        m = metrics[row["property_id"]]
        res_start = max(date.fromisoformat(row["start_date"]), start)
        res_end = min(date.fromisoformat(row["end_date"]), end)
        nights = max(0, (res_end - res_start).days)
        guests = (row["adults"] or 0) + (row["children"] or 0)
        m["reservations"] += 1
        m["occupied_nights"] += nights
        m["arrivals"] += int(start <= date.fromisoformat(row["start_date"]) < end)
        m["departures"] += int(start < date.fromisoformat(row["end_date"]) <= end)
        m["guest_nights"] += nights * guests
        m["gross_revenue_cents"] += row["total_amount_cents"] or 0
        m["sources"][row["source_type"]] = m["sources"].get(row["source_type"], 0) + 1

    period_nights = (end - start).days
    for m in metrics.values():
        m["occupancy_percent"] = round(100 * m["occupied_nights"] / period_nights, 1) if period_nights else 0
        m["gross_revenue"] = round(m["gross_revenue_cents"] / 100, 2)

    portfolio = {
        "start_date": start.isoformat(),
        "end_date": end.isoformat(),
        "properties": len(metrics),
        "reservations": sum(m["reservations"] for m in metrics.values()),
        "occupied_nights": sum(m["occupied_nights"] for m in metrics.values()),
        "arrivals": sum(m["arrivals"] for m in metrics.values()),
        "departures": sum(m["departures"] for m in metrics.values()),
        "guest_nights": sum(m["guest_nights"] for m in metrics.values()),
        "gross_revenue_cents": sum(m["gross_revenue_cents"] for m in metrics.values()),
    }
    portfolio["gross_revenue"] = round(portfolio["gross_revenue_cents"] / 100, 2)
    return {"portfolio": portfolio, "properties": list(metrics.values())}


def _location(prop: dict[str, Any]) -> str:
    address = ", ".join(
        part for part in [prop.get("address_line1"), prop.get("address_line2"), prop.get("city"), prop.get("state"), prop.get("postal_code")] if part
    )
    return address or prop.get("location_label") or f"{prop['name']} ({prop['code']})"


def _local_dt(day: str, hhmm: str, timezone_name: str) -> datetime:
    hour, minute = [int(v) for v in hhmm.split(":", 1)]
    d = date.fromisoformat(day)
    return datetime(d.year, d.month, d.day, hour, minute, tzinfo=ZoneInfo(timezone_name))


def _ics_dt(value: datetime) -> str:
    return value.strftime("%Y%m%dT%H%M%S")


def _cleaning_event_lines(row: dict[str, Any], kind: str, next_arrival: dict[str, Any] | None = None) -> list[str]:
    prop = row
    guest_count = (row.get("adults") or 0) + (row.get("children") or 0)
    guest_count_text = str(guest_count) if guest_count else "not provided"
    timezone_name = row["timezone"]
    arrival = _local_dt(row["start_date"], row["check_in_time"], timezone_name)
    departure = _local_dt(row["end_date"], row["check_out_time"], timezone_name)
    same_day = bool(next_arrival and next_arrival["start_date"] == row["end_date"])

    if kind == "arrival":
        start = arrival
        end = arrival + timedelta(minutes=30)
        summary = f"[{row['property_code']}] ARRIVAL · {guest_count_text} guests"
        categories = "ARRIVAL,CLEANING"
        uid = f"clean-arrival-{row['id']}@swasamventure.com"
    else:
        start = departure
        end = departure + timedelta(minutes=int(row["cleaning_duration_minutes"]))
        summary = f"[{row['property_code']}] DEPARTURE / CLEAN · {guest_count_text} guests"
        categories = "DEPARTURE,CLEANING"
        uid = f"clean-departure-{row['id']}@swasamventure.com"

    description_lines = [
        f"Property ID: {row['property_id']}",
        f"Property code: {row['property_code']}",
        f"Property: {row['property_name']}",
        f"Location: {_location(row)}",
        f"Guest count: {guest_count_text}",
        f"Arrival: {arrival.strftime('%Y-%m-%d %I:%M %p')}",
        f"Departure: {departure.strftime('%Y-%m-%d %I:%M %p')}",
        f"Source: {row['source_type']}",
        f"Reservation ID: {row['id']}",
    ]
    if row.get("cleaner_note"):
        description_lines.append(f"Cleaning note: {row['cleaner_note']}")
    if kind == "departure":
        description_lines.append(f"Same-day turnover: {'YES' if same_day else 'NO'}")
        if next_arrival:
            description_lines.append(
                f"Next arrival: {next_arrival['start_date']} {next_arrival['check_in_time']} · {((next_arrival.get('adults') or 0) + (next_arrival.get('children') or 0)) or 'guest count not provided'} guests"
            )
    description_lines.append("Privacy: Guest names, email addresses, phone numbers, payment details, door codes, and private guest notes are intentionally excluded from this calendar.")

    return [
        "BEGIN:VEVENT",
        f"UID:{uid}",
        f"DTSTAMP:{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}",
        f"DTSTART;TZID={timezone_name}:{_ics_dt(start)}",
        f"DTEND;TZID={timezone_name}:{_ics_dt(end)}",
        f"SUMMARY:{_ics_escape(summary)}",
        f"LOCATION:{_ics_escape(_location(row))}",
        f"DESCRIPTION:{_ics_escape(chr(10).join(description_lines))}",
        f"CATEGORIES:{categories}",
        f"X-ARBOR-PROPERTY-ID:{row['property_id']}",
        f"X-ARBOR-PROPERTY-CODE:{row['property_code']}",
        f"X-ARBOR-EVENT-TYPE:{kind.upper()}",
        "TRANSP:TRANSPARENT",
        "END:VEVENT",
    ]


def cleaning_feed_ics(conn, token: str, property_slug: str | None = None) -> tuple[str, int, list[str]]:
    digest = token_digest(token)
    share = conn.execute(
        """SELECT * FROM calendar_share_tokens
           WHERE token_hash=? AND active=1 AND audience='cleaner'
             AND (expires_at IS NULL OR datetime(expires_at)>datetime('now'))""",
        (digest,),
    ).fetchone()
    if not share:
        raise AccessDenied("Invalid or expired cleaning calendar token.")
    properties = conn.execute(
        """SELECT p.* FROM properties p
           JOIN calendar_share_properties sp ON sp.property_id=p.id
           WHERE sp.share_token_id=? AND p.active=1
           ORDER BY p.name""",
        (share["id"],),
    ).fetchall()
    if property_slug:
        properties = [p for p in properties if p["slug"] == property_slug]
        if not properties:
            raise AccessDenied("This cleaning calendar token does not include the requested property.")
    property_ids = [p["id"] for p in properties]
    prop_map = {p["id"]: dict(p) for p in properties}
    if not property_ids:
        raise AccessDenied("No active properties are assigned to this calendar token.")

    reservations = conn.execute(
        f"""SELECT * FROM reservations
             WHERE property_id IN ({_placeholders(len(property_ids))})
               AND status IN ('pending','confirmed')
             ORDER BY property_id,start_date,end_date""",
        property_ids,
    ).fetchall()
    enriched = []
    for r in reservations:
        item = dict(r)
        p = prop_map[r["property_id"]]
        item.update({
            "property_code": p["code"], "property_name": p["name"], "property_slug": p["slug"],
            "timezone": p["timezone"], "check_in_time": p["check_in_time"],
            "check_out_time": p["check_out_time"], "cleaning_duration_minutes": p["cleaning_duration_minutes"],
            "location_label": p["location_label"], "address_line1": p["address_line1"],
            "address_line2": p["address_line2"], "city": p["city"], "state": p["state"], "postal_code": p["postal_code"],
        })
        enriched.append(item)

    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//Swasam Venture//Multi-Property Cleaning Calendar 4.1//EN",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        f"X-WR-CALNAME:{_ics_escape(share['label'])}",
        "X-PUBLISHED-TTL:PT30M",
        "REFRESH-INTERVAL;VALUE=DURATION:PT30M",
    ]
    for idx, row in enumerate(enriched):
        next_arrival = next(
            (candidate for candidate in enriched if candidate["property_id"] == row["property_id"] and candidate["start_date"] >= row["end_date"] and candidate["id"] != row["id"]),
            None,
        )
        lines.extend(_cleaning_event_lines(row, "arrival"))
        lines.extend(_cleaning_event_lines(row, "departure", next_arrival))
    lines.append("END:VCALENDAR")
    folded = [part for line in lines for part in _fold_ics_line(line)]
    return "\r\n".join(folded) + "\r\n", len(enriched) * 2, [p["code"] for p in properties]


def property_export_bytes(conn, property_slug: str, requested_by: str, include_future_guest_names: bool = False) -> tuple[bytes, dict[str, Any]]:
    prop = conn.execute("SELECT * FROM properties WHERE slug=?", (property_slug,)).fetchone()
    if not prop:
        raise ValueError("Property not found.")
    prop = dict(prop)
    today = date.today().isoformat()
    reservations = [dict(r) for r in conn.execute(
        """SELECT id,source_type,guest_name,start_date,end_date,adults,children,status,summary
           FROM reservations WHERE property_id=? AND end_date>=? ORDER BY start_date""",
        (prop["id"], today),
    ).fetchall()]
    if not include_future_guest_names:
        for r in reservations:
            r["guest_name"] = "Redacted"
    sources = [dict(r) for r in conn.execute(
        "SELECT id,source_type,name,enabled,last_synced_at FROM calendar_sources WHERE property_id=?",
        (prop["id"],),
    ).fetchall()]
    blocks = [dict(r) for r in conn.execute(
        "SELECT id,start_date,end_date,reason,active FROM calendar_blocks WHERE property_id=? ORDER BY start_date",
        (prop["id"],),
    ).fetchall()]

    export_id = f"export_{uuid.uuid4().hex[:12]}"
    file_name = f"{prop['slug']}-transfer-{date.today().isoformat()}.zip"
    manifest = {
        "schemaVersion": 1,
        "exportId": export_id,
        "createdAt": datetime.now(timezone.utc).isoformat(),
        "requestedBy": requested_by,
        "propertyId": prop["id"],
        "propertyCode": prop["code"],
        "propertySlug": prop["slug"],
        "privacy": {
            "historicalGuestsIncluded": False,
            "guestEmailsIncluded": False,
            "guestPhonesIncluded": False,
            "futureGuestNamesIncluded": include_future_guest_names,
        },
        "files": ["property.json", "future-reservations.csv", "calendar-sources.json", "owner-blocks.csv", "TRANSFER_NOTES.md"],
    }

    def csv_bytes(rows: list[dict[str, Any]], fields: list[str]) -> bytes:
        s = io.StringIO(newline="")
        writer = csv.DictWriter(s, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
        return s.getvalue().encode("utf-8")

    out = io.BytesIO()
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as zf:
        safe_prop = {k: v for k, v in prop.items() if k not in {"cleaner_notes"}}
        zf.writestr("property.json", json.dumps(safe_prop, indent=2))
        zf.writestr("future-reservations.csv", csv_bytes(reservations, ["id","source_type","guest_name","start_date","end_date","adults","children","status","summary"]))
        zf.writestr("calendar-sources.json", json.dumps(sources, indent=2))
        zf.writestr("owner-blocks.csv", csv_bytes(blocks, ["id","start_date","end_date","reason","active"]))
        zf.writestr("transfer-manifest.json", json.dumps(manifest, indent=2))
        zf.writestr("TRANSFER_NOTES.md", "# Property Transfer Export\n\nThis export intentionally excludes guest email, phone, payment credentials, shared platform credentials, and other properties. Review legal and privacy obligations before transferring future reservation information.\n")
    conn.execute(
        "INSERT INTO data_exports(id,property_id,requested_by,export_type,status,file_name,manifest_json) VALUES(?,?,?,'property_transfer','created',?,?)",
        (export_id, prop["id"], requested_by, file_name, json.dumps(manifest)),
    )
    return out.getvalue(), manifest
