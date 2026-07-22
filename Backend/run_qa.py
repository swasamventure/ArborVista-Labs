#!/usr/bin/env python3
from __future__ import annotations

import json
import sqlite3
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import ical_db

ROOT = Path(__file__).resolve().parent
FIXTURES = ROOT / "fixtures"


class QA:
    def __init__(self) -> None:
        self.checks: list[dict] = []

    def check(self, name: str, condition: bool, detail: object = "") -> None:
        self.checks.append(
            {"name": name, "passed": bool(condition), "detail": str(detail)[:2000]}
        )

    def raises(self, name: str, expected: type[BaseException], func, *args, **kwargs) -> None:
        try:
            func(*args, **kwargs)
        except expected as exc:
            self.check(name, True, f"{type(exc).__name__}: {exc}")
        except Exception as exc:  # pragma: no cover - diagnostic path
            self.check(name, False, f"unexpected {type(exc).__name__}: {exc}")
        else:
            self.check(name, False, "no exception raised")


def scalar(db: Path, sql: str, params: tuple = ()):
    with sqlite3.connect(db) as conn:
        row = conn.execute(sql, params).fetchone()
        return None if row is None else row[0]


def main() -> None:
    qa = QA()
    with tempfile.TemporaryDirectory(prefix="arborvista-v28-qa-") as tmp:
        tmp_path = Path(tmp)

        # Core reservation engine and channel import tests.
        db = tmp_path / "core.db"
        ical_db.init_db(db, reset=True)
        qa.check("Database initializes", db.exists() and db.stat().st_size > 0, db)

        with sqlite3.connect(db) as conn:
            try:
                conn.execute(
                    """INSERT INTO reservations
                       (id,property_id,source_type,start_date,end_date,status)
                       VALUES ('bad_date','prop_arbor_vista','direct','not-a-date','2026-09-01','pending')"""
                )
            except sqlite3.IntegrityError as exc:
                qa.check("Schema rejects invalid date strings", True, exc)
            else:
                qa.check("Schema rejects invalid date strings", False, "invalid row inserted")

        airbnb_first = ical_db.sync_fixture(
            "src_airbnb", FIXTURES / "airbnb_sample.ics", db_path=db
        )
        vrbo_first = ical_db.sync_fixture(
            "src_vrbo", FIXTURES / "vrbo_sample.ics", db_path=db
        )
        airbnb_second = ical_db.sync_fixture(
            "src_airbnb", FIXTURES / "airbnb_sample.ics", db_path=db
        )
        qa.check("Airbnb events inserted", airbnb_first["inserted"] == 2, airbnb_first)
        qa.check("Vrbo events inserted", vrbo_first["inserted"] == 2, vrbo_first)
        qa.check(
            "Repeated sync is idempotent",
            airbnb_second["inserted"] == 0
            and airbnb_second["updated"] == 0
            and airbnb_second["cancelled"] == 0,
            airbnb_second,
        )

        overlap = ical_db.availability(
            ical_db.PROPERTY_ID, "2026-09-05", "2026-09-07", db_path=db
        )
        adjacent = ical_db.availability(
            ical_db.PROPERTY_ID, "2026-09-08", "2026-09-11", db_path=db
        )
        owner = ical_db.availability(
            ical_db.PROPERTY_ID, "2026-10-13", "2026-10-14", db_path=db
        )
        qa.check(
            "Airbnb overlap detected",
            overlap["available"] is False and overlap["conflicts"][0]["source"] == "airbnb",
            overlap,
        )
        qa.check("Adjacent stays are allowed", adjacent["available"] is True, adjacent)
        qa.check(
            "Seeded owner block detected",
            owner["available"] is False and owner["conflicts"][0]["source"] == "owner",
            owner,
        )

        direct = ical_db.create_booking_request(
            "2026-09-22", "2026-09-25", "QA Guest", db_path=db
        )
        duplicate = ical_db.create_booking_request(
            "2026-09-23", "2026-09-24", "Conflict Guest", db_path=db
        )
        qa.check("Direct request created", direct["created"] is True, direct)
        qa.check("Conflicting direct request rejected", duplicate["created"] is False, duplicate)

        # Race test: BEGIN IMMEDIATE + recheck means only one request can win.
        def race_request(name: str):
            return ical_db.create_booking_request(
                "2026-11-10", "2026-11-12", name, db_path=db
            )

        with ThreadPoolExecutor(max_workers=2) as pool:
            race_results = list(pool.map(race_request, ["Race One", "Race Two"]))
        qa.check(
            "Concurrent duplicate booking race is prevented",
            sum(1 for result in race_results if result["created"]) == 1,
            race_results,
        )

        block = ical_db.create_owner_block(
            "2026-11-20", "2026-11-22", "Deep cleaning", db_path=db
        )
        block_duplicate = ical_db.create_owner_block(
            "2026-11-21", "2026-11-23", "Overlap", db_path=db
        )
        qa.check("Owner block created", block["created"] is True, block)
        qa.check("Overlapping owner block rejected", block_duplicate["created"] is False, block_duplicate)

        qa.check(
            "Cancellation succeeds",
            ical_db.cancel_reservation(direct["reservation_id"], db_path=db),
            direct["reservation_id"],
        )
        restored = ical_db.availability(
            ical_db.PROPERTY_ID, "2026-09-22", "2026-09-25", db_path=db
        )
        qa.check("Cancelled direct dates become available", restored["available"] is True, restored)

        exports = tmp_path / "exports"
        generic_path = exports / "all.ics"
        airbnb_path = exports / "for-airbnb.ics"
        vrbo_path = exports / "for-vrbo.ics"
        generic_count = ical_db.export_ics(generic_path, db_path=db)
        airbnb_count = ical_db.export_ics(
            airbnb_path, db_path=db, exclude_source="airbnb"
        )
        vrbo_count = ical_db.export_ics(vrbo_path, db_path=db, exclude_source="vrbo")
        generic_text = generic_path.read_bytes()
        qa.check("Generic outbound ICS generated", generic_count > 0, generic_count)
        qa.check(
            "Outbound ICS uses CRLF and publishing headers",
            b"\r\nMETHOD:PUBLISH\r\n" in generic_text
            and b"\n" in generic_text
            and b"\r\n" in generic_text,
            generic_text[:300],
        )
        qa.check(
            "Airbnb-targeted export excludes Airbnb-origin reservations",
            airbnb_count == generic_count - 2
            and b"Blocked by airbnb source" not in airbnb_path.read_bytes(),
            {"generic": generic_count, "airbnb": airbnb_count},
        )
        qa.check(
            "Vrbo-targeted export excludes Vrbo-origin reservations",
            vrbo_count == generic_count - 2
            and b"Blocked by vrbo source" not in vrbo_path.read_bytes(),
            {"generic": generic_count, "vrbo": vrbo_count},
        )
        qa.check(
            "Export contains no cancelled reservations",
            direct["reservation_id"].encode() not in generic_text,
            direct["reservation_id"],
        )
        qa.check(
            "Exported ICS parses back successfully",
            len(ical_db.parse_ical(generic_text.decode("utf-8"))) == generic_count,
            generic_count,
        )

        health = ical_db.database_health(db_path=db)
        qa.check("Database health report passes", health["status"] == "PASS", health)
        qa.check(
            "Audit log captures material actions",
            scalar(db, "SELECT COUNT(*) FROM audit_log") >= 7,
            scalar(db, "SELECT COUNT(*) FROM audit_log"),
        )
        qa.check(
            "Foreign-key integrity passes",
            scalar(db, "PRAGMA foreign_key_check") is None,
            "no violations",
        )

        # Update, cancellation and disappearance reconciliation.
        reconcile_db = tmp_path / "reconcile.db"
        ical_db.init_db(reconcile_db, reset=True)
        ical_db.sync_fixture(
            "src_airbnb", FIXTURES / "airbnb_sample.ics", db_path=reconcile_db
        )
        changed = ical_db.sync_fixture(
            "src_airbnb", FIXTURES / "airbnb_updated_missing.ics", db_path=reconcile_db
        )
        qa.check(
            "Changed event updates and missing event cancels",
            changed["updated"] == 1 and changed["cancelled"] == 1,
            changed,
        )
        explicit_cancel = ical_db.sync_fixture(
            "src_airbnb", FIXTURES / "airbnb_cancelled.ics", db_path=reconcile_db
        )
        qa.check(
            "Explicit STATUS:CANCELLED is reconciled",
            explicit_cancel["cancelled"] == 1
            and scalar(
                reconcile_db,
                "SELECT COUNT(*) FROM reservations WHERE calendar_source_id='src_airbnb' AND status='confirmed'",
            )
            == 0,
            explicit_cancel,
        )

        empty_db = tmp_path / "empty.db"
        ical_db.init_db(empty_db, reset=True)
        ical_db.sync_fixture("src_airbnb", FIXTURES / "airbnb_sample.ics", db_path=empty_db)
        empty_result = ical_db.sync_fixture(
            "src_airbnb", FIXTURES / "empty_calendar.ics", db_path=empty_db
        )
        qa.check(
            "Empty full feed cancels disappeared active events",
            empty_result["cancelled"] == 2,
            empty_result,
        )

        folded = ical_db.parse_ical((FIXTURES / "folded_line.ics").read_text())
        qa.check(
            "Folded iCal lines unfold correctly",
            len(folded) == 1 and "parser verification" in folded[0]["SUMMARY"],
            folded,
        )

        malformed_db = tmp_path / "malformed.db"
        ical_db.init_db(malformed_db, reset=True)
        qa.raises(
            "Malformed VEVENT is rejected",
            ical_db.ICalError,
            ical_db.sync_fixture,
            "src_airbnb",
            FIXTURES / "malformed_missing_dtend.ics",
            db_path=malformed_db,
        )
        qa.check(
            "Failed sync is logged",
            scalar(malformed_db, "SELECT COUNT(*) FROM sync_runs WHERE status='failed'") == 1,
            scalar(malformed_db, "SELECT status||':'||COALESCE(error_message,'') FROM sync_runs"),
        )
        qa.raises(
            "Duplicate UID in a single feed is rejected",
            ical_db.ICalError,
            ical_db.sync_fixture,
            "src_airbnb",
            FIXTURES / "duplicate_uid.ics",
            db_path=malformed_db,
        )

        qa.raises(
            "Invalid date range is rejected",
            ValueError,
            ical_db.availability,
            ical_db.PROPERTY_ID,
            "2026-09-10",
            "2026-09-10",
            db_path=db,
        )
        qa.raises(
            "Invalid calendar URL scheme is rejected",
            ValueError,
            ical_db.fetch_ical,
            "http://example.com/calendar.ics",
        )

        passed = sum(1 for item in qa.checks if item["passed"])
        report = {
            "version": "2.8.1-final",
            "status": "PASS" if passed == len(qa.checks) else "FAIL",
            "checks_passed": passed,
            "checks_total": len(qa.checks),
            "checks": qa.checks,
        }

    output_json = ROOT.parent / "QA_REPORT_DATABASE.json"
    output_md = ROOT.parent / "QA_REPORT_DATABASE.md"
    output_json.write_text(json.dumps(report, indent=2), encoding="utf-8")
    markdown = [
        "# Arbor Vista v2.8 Database and iCal QA",
        "",
        f"**Status: {report['status']}**",
        "",
        f"Passed {passed} of {len(qa.checks)} automated checks.",
        "",
    ]
    for item in qa.checks:
        markdown.append(f"- {'PASS' if item['passed'] else 'FAIL'} — {item['name']}")
    output_md.write_text("\n".join(markdown) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    if report["status"] != "PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
