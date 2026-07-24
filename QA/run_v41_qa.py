#!/usr/bin/env python3
from __future__ import annotations

import io
import json
import sqlite3
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "Backend"
sys.path.insert(0, str(BACKEND))

from ical_db import availability, connect, init_db
from operations import (
    AccessDenied,
    EXPORT_ROLES,
    authorized_properties,
    cleaning_feed_ics,
    list_reservations,
    property_export_bytes,
    report_summary,
    resolve_property_scope,
)
import server

checks: list[dict] = []

def check(name: str, condition: bool, detail="") -> None:
    checks.append({"name": name, "passed": bool(condition), "detail": str(detail)[:3000]})


def expect_raises(name: str, exc_type, fn) -> None:
    try:
        fn()
    except exc_type as exc:
        check(name, True, exc)
    except Exception as exc:
        check(name, False, f"Wrong exception: {type(exc).__name__}: {exc}")
    else:
        check(name, False, "No exception raised")


# Static feature coverage.
schema = (BACKEND / "schema.sql").read_text(encoding="utf-8")
for table in [
    "organizations", "users", "organization_members", "properties", "property_domains",
    "property_members", "property_settings", "reservations", "booking_requests", "guests",
    "calendar_sources", "calendar_blocks", "sync_runs", "calendar_share_tokens",
    "calendar_share_properties", "reporting_snapshots", "data_exports", "audit_log",
]:
    check(f"Database table exists: {table}", f"CREATE TABLE IF NOT EXISTS {table}" in schema)

for page in [
    "dashboard.html", "reservations.html", "calendar.html", "settings.html", "sync-log.html",
    "reports.html", "cleaning-calendar.html", "property-export.html", "login.html",
]:
    check(f"Dashboard page exists: {page}", (ROOT / "admin" / page).exists())

server_text = (BACKEND / "server.py").read_text(encoding="utf-8")
for endpoint in [
    "/properties", "/reservations", "/calendar/combined", "/reports/summary",
    "/ical/cleaning.ics", "/property-export", "/booking-requests",
]:
    check(f"API endpoint implemented: {endpoint}", endpoint in server_text)

check("Shared property template exists", (ROOT / "shared-template" / "property.schema.json").exists())
check("Property creation tool exists", (ROOT / "tools" / "create_property.py").exists())
check("Property export tool exists", (ROOT / "tools" / "export_property.py").exists())
check("Supabase base migration exists", (ROOT / "supabase/migrations/001_cloud_multi_property.sql").exists())
check("Supabase RLS migration exists", (ROOT / "supabase/migrations/002_rls_policies.sql").exists())
check("Supabase reporting/cleaner migration exists", (ROOT / "supabase/migrations/003_reporting_and_cleaner_feed.sql").exists())

# Syntax checks.
for rel in ["Backend/ical_db.py", "Backend/operations.py", "Backend/server.py", "tools/create_property.py", "tools/export_property.py"]:
    result = subprocess.run([sys.executable, "-m", "py_compile", str(ROOT / rel)], capture_output=True, text=True)
    check(f"Python syntax: {rel}", result.returncode == 0, result.stderr)
for rel in ["assets/script.js", "admin/admin.js", "config/runtime-config.js"]:
    result = subprocess.run(["node", "--check", str(ROOT / rel)], capture_output=True, text=True)
    check(f"JavaScript syntax: {rel}", result.returncode == 0, result.stderr)

# Integration tests use a fresh isolated database.
with tempfile.TemporaryDirectory(prefix="arbor-v41-") as tmp:
    db = Path(tmp) / "platform.db"
    init_db(db, reset=True)
    server.DB = db

    with connect(db) as conn:
        properties = [dict(r) for r in conn.execute("SELECT * FROM properties ORDER BY code")]
        check("Two-property test foundation initialized", len(properties) == 2, properties)
        check("Arbor Vista has stable property code", any(p["code"] == "AVR-TN-01" for p in properties), properties)
        check("Second property is marked demo", any(p["id"] == "prop_demo_smokies" and p["is_demo"] == 1 for p in properties), properties)

        owner_props = authorized_properties(conn, "user_owner")
        manager_props = authorized_properties(conn, "user_manager")
        cleaner_props = authorized_properties(conn, "user_cleaner")
        accountant_props = authorized_properties(conn, "user_accountant")
        check("Portfolio owner can access both properties", {p["id"] for p in owner_props} == {"prop_arbor_vista", "prop_demo_smokies"}, owner_props)
        check("Manager is limited to Arbor Vista", [p["id"] for p in manager_props] == ["prop_arbor_vista"], manager_props)
        check("Cleaner is assigned to both properties", {p["id"] for p in cleaner_props} == {"prop_arbor_vista", "prop_demo_smokies"}, cleaner_props)
        check("Organization accountant can see both properties", {p["id"] for p in accountant_props} == {"prop_arbor_vista", "prop_demo_smokies"}, accountant_props)
        expect_raises(
            "Cleaner cannot read admin reservation scope",
            AccessDenied,
            lambda: resolve_property_scope(conn, "user_cleaner", "all"),
        )
        expect_raises(
            "Manager cannot access property-sale export role",
            AccessDenied,
            lambda: resolve_property_scope(conn, "user_manager", "arbor-vista-retreat", EXPORT_ROLES),
        )

    # Reservation engine: create in Arbor Vista, reject overlap, allow same dates in another property.
    with connect(db) as conn:
        avr = dict(conn.execute("SELECT * FROM properties WHERE id='prop_arbor_vista'").fetchone())
        demo = dict(conn.execute("SELECT * FROM properties WHERE id='prop_demo_smokies'").fetchone())

    payload = {
        "check_in": "2028-03-10", "check_out": "2028-03-13", "adults": 4, "children": 2,
        "first_name": "Private", "last_name": "Guest", "email": "private@example.test",
        "phone": "5125551212", "legal_name": "Private Guest", "electronic_signature": "Private Guest",
        "agreement_date": "2028-01-01", "vehicles": 2,
    }
    created = server.create_booking(payload, avr)
    check("Direct booking request created", created["status"] == "pending" and created["property_id"] == "prop_arbor_vista", created)
    expect_raises("Overlapping booking is rejected within same property", ValueError, lambda: server.create_booking(payload, avr))
    created_demo = server.create_booking({**payload, "email": "other@example.test"}, demo)
    check("Same dates are allowed at a different property", created_demo["property_id"] == "prop_demo_smokies", created_demo)

    with connect(db) as conn:
        unavailable = availability("prop_arbor_vista", "2028-03-11", "2028-03-12", db_path=db)
        check("Pending request blocks availability", unavailable["available"] is False, unavailable)
        rows = list_reservations(conn, ["prop_arbor_vista", "prop_demo_smokies"])
        check("Reservation list carries property identity", all(r.get("property_code") and r.get("property_name") for r in rows), rows)

        report = report_summary(conn, ["prop_arbor_vista", "prop_demo_smokies"], "2027-01-01", "2029-01-01")
        check("Portfolio report includes both properties", report["portfolio"]["properties"] == 2, report)
        check("Reports include occupied nights and guest nights", report["portfolio"]["occupied_nights"] > 0 and report["portfolio"]["guest_nights"] > 0, report)

        # Cleaner feed: identity excluded, operational/property information retained.
        feed, event_count, property_codes = cleaning_feed_ics(conn, "demo-cleaner-token-change-me")
        check("Portfolio cleaning feed contains both properties", set(property_codes) == {"AVR-TN-01", "DEMO-TN-02"}, property_codes)
        check("Cleaning feed creates arrival and departure events", event_count >= 4 and "ARRIVAL" in feed and "DEPARTURE / CLEAN" in feed, event_count)
        check("Cleaning feed includes property names", "Arbor Vista Retreat" in feed and "Smoky Mountain Demo Cabin" in feed, feed[:1200])
        check("Cleaning feed includes property IDs", "prop_arbor_vista" in feed and "prop_demo_smokies" in feed, feed[:1200])
        check("Cleaning feed includes guest counts", "Guest count:" in feed and "6 guests" in feed, feed[:1200])
        forbidden = ["Jordan Smith", "Taylor Jones", "Private Guest", "Jordan S.", "Taylor J.", "Guest:", "private@example.test", "5125551212"]
        check("Cleaning feed excludes all guest identity and contact data", not any(value in feed for value in forbidden), [v for v in forbidden if v in feed])
        check("Cleaning feed explicitly documents privacy", "Guest names" in feed and "door codes" in feed, feed[:1600])
        avr_feed, avr_count, avr_codes = cleaning_feed_ics(conn, "demo-cleaner-token-change-me", "arbor-vista-retreat")
        check("Property-filtered cleaner feed contains only selected property", avr_codes == ["AVR-TN-01"] and "DEMO-TN-02" not in avr_feed, avr_codes)
        expect_raises("Invalid cleaner token is rejected", AccessDenied, lambda: cleaning_feed_ics(conn, "invalid-token"))

        # Property transfer export: one property only and private by default.
        export_bytes, manifest = property_export_bytes(conn, "arbor-vista-retreat", "user_owner", False)
        with zipfile.ZipFile(io.BytesIO(export_bytes)) as zf:
            names = set(zf.namelist())
            reservations_csv = zf.read("future-reservations.csv").decode("utf-8")
            property_json = zf.read("property.json").decode("utf-8")
            sources_json = zf.read("calendar-sources.json").decode("utf-8")
        check("Property export contains required transfer files", {"property.json", "future-reservations.csv", "calendar-sources.json", "owner-blocks.csv", "transfer-manifest.json", "TRANSFER_NOTES.md"}.issubset(names), names)
        check("Property export is scoped to Arbor Vista", "prop_arbor_vista" in property_json and "prop_demo_smokies" not in property_json and "Smoky Mountain Demo Cabin" not in reservations_csv, property_json)
        check("Property export redacts guest names by default", "Redacted" in reservations_csv and "Jordan Smith" not in reservations_csv and "Private Guest" not in reservations_csv, reservations_csv)
        check("Property export excludes calendar feed secrets", "feed_url" not in sources_json, sources_json)
        check("Property export manifest records privacy", manifest["privacy"]["futureGuestNamesIncluded"] is False, manifest)

# Supabase cleaner function must not return guest_name.
pg_cleaner = (ROOT / "supabase/migrations/003_reporting_and_cleaner_feed.sql").read_text(encoding="utf-8").lower()
check("Supabase cleaner row function excludes guest_name", "guest_name" not in pg_cleaner, pg_cleaner)
check("Supabase RLS excludes cleaner from reservation policy", "reservations_read" in (ROOT / "supabase/migrations/002_rls_policies.sql").read_text(encoding="utf-8"))

passed = sum(c["passed"] for c in checks)
report = {
    "version": "4.1",
    "status": "PASS" if passed == len(checks) else "FAIL",
    "checks_passed": passed,
    "checks_total": len(checks),
    "checks": checks,
}
(ROOT / "QA_REPORT_V4.1.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
print(json.dumps(report, indent=2))
if passed != len(checks):
    raise SystemExit(1)
