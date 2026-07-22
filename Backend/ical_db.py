#!/usr/bin/env python3
"""Arbor Vista v2.8 local iCal database test harness (stdlib only)."""
from __future__ import annotations

import argparse
import json
import sqlite3
import uuid
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Iterable

ROOT = Path(__file__).resolve().parent
DB_PATH = ROOT / "arborvista_ical_test.db"


def connect(db_path: Path = DB_PATH) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db(reset: bool = False) -> None:
    if reset and DB_PATH.exists():
        DB_PATH.unlink()
    with connect() as conn:
        conn.executescript((ROOT / "schema.sql").read_text(encoding="utf-8"))
        conn.executescript((ROOT / "seed.sql").read_text(encoding="utf-8"))


def unfold_ical(text: str) -> list[str]:
    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    unfolded: list[str] = []
    for line in lines:
        if line.startswith((" ", "\t")) and unfolded:
            unfolded[-1] += line[1:]
        else:
            unfolded.append(line)
    return unfolded


def parse_ical(text: str) -> list[dict[str, str]]:
    events: list[dict[str, str]] = []
    event: dict[str, str] | None = None
    for line in unfold_ical(text):
        if line == "BEGIN:VEVENT":
            event = {}
        elif line == "END:VEVENT" and event is not None:
            if {"UID", "DTSTART", "DTEND"}.issubset(event):
                events.append(event)
            event = None
        elif event is not None and ":" in line:
            key, value = line.split(":", 1)
            event[key.split(";", 1)[0].upper()] = value.strip()
    return events


def ical_date(value: str) -> str:
    raw = value.strip()
    if len(raw) >= 8 and raw[:8].isdigit():
        return datetime.strptime(raw[:8], "%Y%m%d").date().isoformat()
    raise ValueError(f"Unsupported iCal date: {value!r}")


def sync_fixture(source_id: str, fixture: Path) -> dict[str, int | str]:
    text = fixture.read_text(encoding="utf-8")
    events = parse_ical(text)
    run_id = f"sync_{uuid.uuid4().hex[:12]}"
    started = datetime.now(timezone.utc).isoformat()
    inserted = updated = 0

    with connect() as conn:
        source = conn.execute(
            "SELECT * FROM calendar_sources WHERE id = ? AND enabled = 1", (source_id,)
        ).fetchone()
        if not source:
            raise ValueError(f"Unknown or disabled calendar source: {source_id}")
        conn.execute(
            "INSERT INTO sync_runs (id,calendar_source_id,started_at,status) VALUES (?,?,?,'running')",
            (run_id, source_id, started),
        )
        for event in events:
            uid = event["UID"]
            start_date = ical_date(event["DTSTART"])
            end_date = ical_date(event["DTEND"])
            summary = event.get("SUMMARY", "Reserved")
            existing = conn.execute(
                "SELECT id,start_date,end_date,summary,status FROM reservations WHERE calendar_source_id=? AND external_uid=?",
                (source_id, uid),
            ).fetchone()
            if existing:
                changed = (
                    existing["start_date"] != start_date
                    or existing["end_date"] != end_date
                    or existing["summary"] != summary
                    or existing["status"] != "confirmed"
                )
                if changed:
                    conn.execute(
                        "UPDATE reservations SET start_date=?,end_date=?,summary=?,status='confirmed',raw_ical=?,updated_at=CURRENT_TIMESTAMP WHERE id=?",
                        (start_date, end_date, summary, json.dumps(event, sort_keys=True), existing["id"]),
                    )
                    updated += 1
            else:
                reservation_id = f"res_{uuid.uuid4().hex[:12]}"
                conn.execute(
                    """INSERT INTO reservations
                    (id,property_id,calendar_source_id,external_uid,source_type,start_date,end_date,status,summary,raw_ical)
                    VALUES (?,?,?,?,?,?,?,'confirmed',?,?)""",
                    (
                        reservation_id,
                        source["property_id"],
                        source_id,
                        uid,
                        source["source_type"],
                        start_date,
                        end_date,
                        summary,
                        json.dumps(event, sort_keys=True),
                    ),
                )
                inserted += 1
        finished = datetime.now(timezone.utc).isoformat()
        conn.execute(
            """UPDATE sync_runs SET finished_at=?,status='success',events_seen=?,events_inserted=?,events_updated=?
            WHERE id=?""",
            (finished, len(events), inserted, updated, run_id),
        )
        conn.execute(
            "UPDATE calendar_sources SET last_synced_at=? WHERE id=?", (finished, source_id)
        )
        conn.execute(
            "INSERT INTO audit_log (property_id,actor,action,entity_type,entity_id,details_json) VALUES (?,?,?,?,?,?)",
            (
                source["property_id"],
                "local-test-harness",
                "calendar_sync",
                "calendar_source",
                source_id,
                json.dumps({"seen": len(events), "inserted": inserted, "updated": updated}),
            ),
        )
    return {"run_id": run_id, "seen": len(events), "inserted": inserted, "updated": updated}


def conflicts(property_id: str, start_date: str, end_date: str) -> list[dict]:
    with connect() as conn:
        rows = conn.execute(
            """SELECT * FROM unavailable_periods
            WHERE property_id=? AND date(start_date) < date(?) AND date(end_date) > date(?)
            ORDER BY start_date""",
            (property_id, end_date, start_date),
        ).fetchall()
        return [dict(row) for row in rows]


def availability(property_id: str, start_date: str, end_date: str) -> dict:
    return {
        "property_id": property_id,
        "start_date": start_date,
        "end_date": end_date,
        "available": not conflicts(property_id, start_date, end_date),
        "conflicts": conflicts(property_id, start_date, end_date),
    }


def create_booking_request(start_date: str, end_date: str, guest_name: str) -> dict:
    result = availability("prop_arbor_vista", start_date, end_date)
    if not result["available"]:
        return {"created": False, **result}
    reservation_id = f"res_{uuid.uuid4().hex[:12]}"
    with connect() as conn:
        conn.execute(
            """INSERT INTO reservations
            (id,property_id,calendar_source_id,source_type,guest_name,start_date,end_date,status,summary)
            VALUES (?, 'prop_arbor_vista', 'src_direct', 'direct', ?, ?, ?, 'pending', 'Direct booking request')""",
            (reservation_id, guest_name, start_date, end_date),
        )
        conn.execute(
            "INSERT INTO audit_log (property_id,actor,action,entity_type,entity_id,details_json) VALUES ('prop_arbor_vista','website-test','create','reservation',?,?)",
            (reservation_id, json.dumps({"start_date": start_date, "end_date": end_date})),
        )
    return {"created": True, "reservation_id": reservation_id, **result}


def export_ics(output: Path) -> int:
    with connect() as conn:
        rows = conn.execute(
            """SELECT id,start_date,end_date,summary,source_type FROM reservations
            WHERE property_id='prop_arbor_vista' AND status IN ('pending','confirmed','blocked')
            UNION ALL
            SELECT id,start_date,end_date,reason,'owner' FROM calendar_blocks
            WHERE property_id='prop_arbor_vista' AND active=1
            ORDER BY start_date"""
        ).fetchall()
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    lines = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//Arbor Vista Retreat//Booking Calendar 2.8//EN", "CALSCALE:GREGORIAN"]
    for row in rows:
        lines += [
            "BEGIN:VEVENT",
            f"UID:{row['id']}@arborvistaretreat.com",
            f"DTSTAMP:{stamp}",
            f"DTSTART;VALUE=DATE:{row['start_date'].replace('-', '')}",
            f"DTEND;VALUE=DATE:{row['end_date'].replace('-', '')}",
            "SUMMARY:Reserved - Arbor Vista Retreat",
            f"DESCRIPTION:Blocked by {row['source_type']} source.",
            "END:VEVENT",
        ]
    lines.append("END:VCALENDAR")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\r\n".join(lines) + "\r\n", encoding="utf-8")
    return len(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("init").add_argument("--reset", action="store_true")
    sync = sub.add_parser("sync")
    sync.add_argument("source_id", choices=["src_airbnb", "src_vrbo"])
    sync.add_argument("fixture", type=Path)
    check = sub.add_parser("check")
    check.add_argument("start_date")
    check.add_argument("end_date")
    request = sub.add_parser("request")
    request.add_argument("start_date")
    request.add_argument("end_date")
    request.add_argument("guest_name")
    export = sub.add_parser("export")
    export.add_argument("output", type=Path, nargs="?", default=ROOT / "exports" / "arbor-vista.ics")
    args = parser.parse_args()

    if args.command == "init":
        init_db(args.reset)
        print(json.dumps({"initialized": True, "database": str(DB_PATH)}, indent=2))
    elif args.command == "sync":
        print(json.dumps(sync_fixture(args.source_id, args.fixture), indent=2))
    elif args.command == "check":
        print(json.dumps(availability("prop_arbor_vista", args.start_date, args.end_date), indent=2))
    elif args.command == "request":
        print(json.dumps(create_booking_request(args.start_date, args.end_date, args.guest_name), indent=2))
    elif args.command == "export":
        print(json.dumps({"events_exported": export_ics(args.output), "output": str(args.output)}, indent=2))


if __name__ == "__main__":
    main()
