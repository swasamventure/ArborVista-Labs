#!/usr/bin/env python3
"""Arbor Vista v2.8 iCal reservation-engine prototype.

The module intentionally uses only the Python standard library so the test
harness can run on a clean machine. Dates use half-open [start, end) semantics.
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import uuid
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parent
DEFAULT_DB_PATH = ROOT / "arborvista_ical_test.db"
PROPERTY_ID = "prop_arbor_vista"


class ICalError(ValueError):
    """Raised when a calendar feed is structurally invalid."""


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def connect(db_path: Path = DEFAULT_DB_PATH) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path, timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA busy_timeout = 30000")
    return conn


def init_db(db_path: Path = DEFAULT_DB_PATH, reset: bool = False) -> None:
    if reset and db_path.exists():
        db_path.unlink()
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with connect(db_path) as conn:
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
    if "BEGIN:VCALENDAR" not in text or "END:VCALENDAR" not in text:
        raise ICalError("Feed is missing VCALENDAR boundaries")

    events: list[dict[str, str]] = []
    event: dict[str, str] | None = None
    for line in unfold_ical(text):
        line = line.strip("\n")
        if line == "BEGIN:VEVENT":
            if event is not None:
                raise ICalError("Nested VEVENT is not supported")
            event = {}
        elif line == "END:VEVENT":
            if event is None:
                raise ICalError("END:VEVENT without BEGIN:VEVENT")
            missing = {"UID", "DTSTART", "DTEND"} - set(event)
            if missing:
                raise ICalError(f"VEVENT is missing required fields: {', '.join(sorted(missing))}")
            events.append(event)
            event = None
        elif event is not None and ":" in line:
            key, value = line.split(":", 1)
            event[key.split(";", 1)[0].upper()] = value.strip()

    if event is not None:
        raise ICalError("Unclosed VEVENT")
    return events


def ical_date(value: str) -> str:
    raw = value.strip()
    if len(raw) >= 8 and raw[:8].isdigit():
        return datetime.strptime(raw[:8], "%Y%m%d").date().isoformat()
    raise ICalError(f"Unsupported iCal date: {value!r}")


def validate_range(start_date: str, end_date: str) -> tuple[str, str]:
    try:
        start = date.fromisoformat(start_date)
        end = date.fromisoformat(end_date)
    except ValueError as exc:
        raise ValueError("Dates must use valid YYYY-MM-DD values") from exc
    if end <= start:
        raise ValueError("end_date must be after start_date")
    return start.isoformat(), end.isoformat()


def _source(conn: sqlite3.Connection, source_id: str) -> sqlite3.Row:
    source = conn.execute(
        "SELECT * FROM calendar_sources WHERE id = ? AND enabled = 1", (source_id,)
    ).fetchone()
    if not source:
        raise ValueError(f"Unknown or disabled calendar source: {source_id}")
    return source


def _count_external_conflicts(
    conn: sqlite3.Connection, property_id: str, source_id: str
) -> int:
    row = conn.execute(
        """SELECT COUNT(*)
           FROM reservations a
           JOIN unavailable_periods b
             ON b.property_id=a.property_id
            AND b.source_id<>a.id
            AND date(b.start_date)<date(a.end_date)
            AND date(b.end_date)>date(a.start_date)
           WHERE a.property_id=?
             AND a.calendar_source_id=?
             AND a.status='confirmed'""",
        (property_id, source_id),
    ).fetchone()
    return int(row[0]) if row else 0


def sync_text(
    source_id: str,
    text: str,
    *,
    db_path: Path = DEFAULT_DB_PATH,
    reconcile_missing: bool = True,
) -> dict[str, int | str]:
    run_id = f"sync_{uuid.uuid4().hex[:12]}"
    started = utc_now()

    with connect(db_path) as conn:
        source = _source(conn, source_id)
        conn.execute(
            "INSERT INTO sync_runs (id,calendar_source_id,started_at,status) VALUES (?,?,?,'running')",
            (run_id, source_id, started),
        )

    try:
        events = parse_ical(text)
        normalized: list[dict[str, str]] = []
        seen_uids: set[str] = set()
        for event in events:
            uid = event["UID"].strip()
            if not uid:
                raise ICalError("VEVENT UID cannot be empty")
            if uid in seen_uids:
                raise ICalError(f"Duplicate UID in one feed: {uid}")
            seen_uids.add(uid)
            start_date, end_date = validate_range(
                ical_date(event["DTSTART"]), ical_date(event["DTEND"])
            )
            normalized.append(
                {
                    "uid": uid,
                    "start_date": start_date,
                    "end_date": end_date,
                    "summary": event.get("SUMMARY", "Reserved") or "Reserved",
                    "cancelled": str(event.get("STATUS", "")).upper() == "CANCELLED",
                    "raw": json.dumps(event, sort_keys=True),
                }
            )

        inserted = updated = cancelled = 0
        with connect(db_path) as conn:
            source = _source(conn, source_id)
            conn.execute("BEGIN IMMEDIATE")
            for event in normalized:
                existing = conn.execute(
                    """SELECT id,start_date,end_date,summary,status
                       FROM reservations
                       WHERE calendar_source_id=? AND external_uid=?""",
                    (source_id, event["uid"]),
                ).fetchone()

                target_status = "cancelled" if event["cancelled"] else "confirmed"
                if existing:
                    changed = (
                        existing["start_date"] != event["start_date"]
                        or existing["end_date"] != event["end_date"]
                        or existing["summary"] != event["summary"]
                        or existing["status"] != target_status
                    )
                    if changed:
                        conn.execute(
                            """UPDATE reservations
                               SET start_date=?,end_date=?,summary=?,status=?,raw_ical=?,updated_at=CURRENT_TIMESTAMP
                               WHERE id=?""",
                            (
                                event["start_date"],
                                event["end_date"],
                                event["summary"],
                                target_status,
                                event["raw"],
                                existing["id"],
                            ),
                        )
                        if target_status == "cancelled":
                            cancelled += 1
                        else:
                            updated += 1
                elif not event["cancelled"]:
                    reservation_id = f"res_{uuid.uuid4().hex[:12]}"
                    conn.execute(
                        """INSERT INTO reservations
                           (id,property_id,calendar_source_id,external_uid,source_type,start_date,end_date,status,summary,raw_ical)
                           VALUES (?,?,?,?,?,?,?,'confirmed',?,?)""",
                        (
                            reservation_id,
                            source["property_id"],
                            source_id,
                            event["uid"],
                            source["source_type"],
                            event["start_date"],
                            event["end_date"],
                            event["summary"],
                            event["raw"],
                        ),
                    )
                    inserted += 1

            if reconcile_missing:
                active_rows = conn.execute(
                    """SELECT id,external_uid FROM reservations
                       WHERE calendar_source_id=? AND status='confirmed'""",
                    (source_id,),
                ).fetchall()
                missing_ids = [row["id"] for row in active_rows if row["external_uid"] not in seen_uids]
                for reservation_id in missing_ids:
                    conn.execute(
                        "UPDATE reservations SET status='cancelled',updated_at=CURRENT_TIMESTAMP WHERE id=?",
                        (reservation_id,),
                    )
                cancelled += len(missing_ids)

            conflicts_found = _count_external_conflicts(conn, source["property_id"], source_id)
            finished = utc_now()
            conn.execute(
                """UPDATE sync_runs
                   SET finished_at=?,status='success',events_seen=?,events_inserted=?,events_updated=?,events_cancelled=?,conflicts_found=?
                   WHERE id=?""",
                (
                    finished,
                    len(normalized),
                    inserted,
                    updated,
                    cancelled,
                    conflicts_found,
                    run_id,
                ),
            )
            conn.execute(
                "UPDATE calendar_sources SET last_synced_at=? WHERE id=?", (finished, source_id)
            )
            conn.execute(
                """INSERT INTO audit_log
                   (property_id,actor,action,entity_type,entity_id,details_json)
                   VALUES (?,?,?,?,?,?)""",
                (
                    source["property_id"],
                    "local-test-harness",
                    "calendar_sync",
                    "calendar_source",
                    source_id,
                    json.dumps(
                        {
                            "seen": len(normalized),
                            "inserted": inserted,
                            "updated": updated,
                            "cancelled": cancelled,
                            "conflicts_found": conflicts_found,
                        },
                        sort_keys=True,
                    ),
                ),
            )
        return {
            "run_id": run_id,
            "seen": len(normalized),
            "inserted": inserted,
            "updated": updated,
            "cancelled": cancelled,
            "conflicts_found": conflicts_found,
        }
    except Exception as exc:
        with connect(db_path) as conn:
            conn.execute(
                """UPDATE sync_runs SET finished_at=?,status='failed',error_message=? WHERE id=?""",
                (utc_now(), str(exc)[:1000], run_id),
            )
        raise


def sync_fixture(
    source_id: str,
    fixture: Path,
    *,
    db_path: Path = DEFAULT_DB_PATH,
    reconcile_missing: bool = True,
) -> dict[str, int | str]:
    return sync_text(
        source_id,
        fixture.read_text(encoding="utf-8"),
        db_path=db_path,
        reconcile_missing=reconcile_missing,
    )


def fetch_ical(url: str, *, timeout: int = 20) -> tuple[str, dict[str, str]]:
    if not url.lower().startswith("https://"):
        raise ValueError("Calendar feed URL must use HTTPS")
    request = Request(url, headers={"User-Agent": "ArborVistaCalendar/2.8"})
    try:
        with urlopen(request, timeout=timeout) as response:
            content_type = response.headers.get("Content-Type", "")
            raw = response.read(5_000_000)
            return raw.decode("utf-8-sig"), {
                "etag": response.headers.get("ETag", ""),
                "last_modified": response.headers.get("Last-Modified", ""),
                "content_type": content_type,
            }
    except (HTTPError, URLError, TimeoutError) as exc:
        raise ConnectionError(f"Unable to download calendar feed: {exc}") from exc


def sync_url(
    source_id: str,
    url: str,
    *,
    db_path: Path = DEFAULT_DB_PATH,
    reconcile_missing: bool = True,
) -> dict[str, int | str]:
    text, headers = fetch_ical(url)
    result = sync_text(
        source_id,
        text,
        db_path=db_path,
        reconcile_missing=reconcile_missing,
    )
    with connect(db_path) as conn:
        conn.execute(
            "UPDATE calendar_sources SET feed_url=?,last_etag=?,last_modified=? WHERE id=?",
            (url, headers["etag"], headers["last_modified"], source_id),
        )
    return result


def conflicts(
    property_id: str,
    start_date: str,
    end_date: str,
    *,
    db_path: Path = DEFAULT_DB_PATH,
) -> list[dict[str, Any]]:
    start_date, end_date = validate_range(start_date, end_date)
    with connect(db_path) as conn:
        rows = conn.execute(
            """SELECT * FROM unavailable_periods
               WHERE property_id=? AND date(start_date) < date(?) AND date(end_date) > date(?)
               ORDER BY start_date, end_date""",
            (property_id, end_date, start_date),
        ).fetchall()
        return [dict(row) for row in rows]


def availability(
    property_id: str,
    start_date: str,
    end_date: str,
    *,
    db_path: Path = DEFAULT_DB_PATH,
) -> dict[str, Any]:
    start_date, end_date = validate_range(start_date, end_date)
    found = conflicts(property_id, start_date, end_date, db_path=db_path)
    return {
        "property_id": property_id,
        "start_date": start_date,
        "end_date": end_date,
        "available": not found,
        "conflicts": found,
    }


def create_booking_request(
    start_date: str,
    end_date: str,
    guest_name: str,
    *,
    db_path: Path = DEFAULT_DB_PATH,
) -> dict[str, Any]:
    start_date, end_date = validate_range(start_date, end_date)
    guest_name = " ".join(guest_name.split())
    if not guest_name:
        raise ValueError("guest_name is required")

    reservation_id = f"res_{uuid.uuid4().hex[:12]}"
    with connect(db_path) as conn:
        conn.execute("BEGIN IMMEDIATE")
        rows = conn.execute(
            """SELECT * FROM unavailable_periods
               WHERE property_id=? AND date(start_date) < date(?) AND date(end_date) > date(?)
               ORDER BY start_date""",
            (PROPERTY_ID, end_date, start_date),
        ).fetchall()
        found = [dict(row) for row in rows]
        if found:
            conn.rollback()
            return {
                "created": False,
                "property_id": PROPERTY_ID,
                "start_date": start_date,
                "end_date": end_date,
                "available": False,
                "conflicts": found,
            }
        conn.execute(
            """INSERT INTO reservations
               (id,property_id,calendar_source_id,source_type,guest_name,start_date,end_date,status,summary)
               VALUES (?, ?, 'src_direct', 'direct', ?, ?, ?, 'pending', 'Direct booking request')""",
            (reservation_id, PROPERTY_ID, guest_name, start_date, end_date),
        )
        conn.execute(
            """INSERT INTO audit_log
               (property_id,actor,action,entity_type,entity_id,details_json)
               VALUES (?,'website-test','create','reservation',?,?)""",
            (
                PROPERTY_ID,
                reservation_id,
                json.dumps({"start_date": start_date, "end_date": end_date}, sort_keys=True),
            ),
        )
    return {
        "created": True,
        "reservation_id": reservation_id,
        "property_id": PROPERTY_ID,
        "start_date": start_date,
        "end_date": end_date,
        "available": True,
        "conflicts": [],
    }


def cancel_reservation(
    reservation_id: str,
    *,
    db_path: Path = DEFAULT_DB_PATH,
    actor: str = "owner-test",
) -> bool:
    with connect(db_path) as conn:
        row = conn.execute(
            "SELECT property_id,status FROM reservations WHERE id=?", (reservation_id,)
        ).fetchone()
        if not row:
            return False
        if row["status"] != "cancelled":
            conn.execute(
                "UPDATE reservations SET status='cancelled',updated_at=CURRENT_TIMESTAMP WHERE id=?",
                (reservation_id,),
            )
            conn.execute(
                """INSERT INTO audit_log
                   (property_id,actor,action,entity_type,entity_id,details_json)
                   VALUES (?,?,?,?,?,?)""",
                (row["property_id"], actor, "cancel", "reservation", reservation_id, "{}"),
            )
        return True


def create_owner_block(
    start_date: str,
    end_date: str,
    reason: str,
    *,
    db_path: Path = DEFAULT_DB_PATH,
) -> dict[str, Any]:
    start_date, end_date = validate_range(start_date, end_date)
    reason = " ".join(reason.split())
    if not reason:
        raise ValueError("reason is required")
    found = conflicts(PROPERTY_ID, start_date, end_date, db_path=db_path)
    if found:
        return {"created": False, "conflicts": found}
    block_id = f"block_{uuid.uuid4().hex[:12]}"
    with connect(db_path) as conn:
        conn.execute(
            """INSERT INTO calendar_blocks
               (id,property_id,start_date,end_date,reason)
               VALUES (?,?,?,?,?)""",
            (block_id, PROPERTY_ID, start_date, end_date, reason),
        )
        conn.execute(
            """INSERT INTO audit_log
               (property_id,actor,action,entity_type,entity_id,details_json)
               VALUES (?,'owner-test','create','calendar_block',?,?)""",
            (
                PROPERTY_ID,
                block_id,
                json.dumps({"start_date": start_date, "end_date": end_date}, sort_keys=True),
            ),
        )
    return {"created": True, "block_id": block_id, "conflicts": []}


def _ics_escape(value: str) -> str:
    return (
        value.replace("\\", "\\\\")
        .replace("\n", "\\n")
        .replace(";", "\\;")
        .replace(",", "\\,")
    )


def _fold_ics_line(line: str, limit: int = 75) -> list[str]:
    # RFC 5545 counts octets. This implementation folds conservatively by UTF-8 bytes.
    chunks: list[str] = []
    current = ""
    for char in line:
        candidate = current + char
        if len(candidate.encode("utf-8")) > limit and current:
            chunks.append(current)
            current = " " + char
        else:
            current = candidate
    chunks.append(current)
    return chunks


def export_ics(
    output: Path,
    *,
    db_path: Path = DEFAULT_DB_PATH,
    exclude_source: str | None = None,
) -> int:
    allowed = {None, "airbnb", "vrbo", "direct", "owner", "other"}
    if exclude_source not in allowed:
        raise ValueError(f"Unsupported source exclusion: {exclude_source}")

    with connect(db_path) as conn:
        rows = conn.execute(
            """SELECT id,start_date,end_date,COALESCE(summary,'Reserved') AS summary,source_type
               FROM reservations
               WHERE property_id=? AND status IN ('pending','confirmed','blocked')
                 AND (? IS NULL OR source_type<>?)
               UNION ALL
               SELECT id,start_date,end_date,reason,'owner'
               FROM calendar_blocks
               WHERE property_id=? AND active=1
                 AND (? IS NULL OR ?<>'owner')
               ORDER BY start_date,end_date""",
            (PROPERTY_ID, exclude_source, exclude_source, PROPERTY_ID, exclude_source, exclude_source),
        ).fetchall()

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//Arbor Vista Retreat//Booking Calendar 2.8//EN",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        "X-WR-CALNAME:Arbor Vista Retreat Availability",
    ]
    for row in rows:
        description = f"Blocked by {row['source_type']} source."
        lines.extend(
            [
                "BEGIN:VEVENT",
                f"UID:{row['id']}@arborvistaretreat.com",
                f"DTSTAMP:{stamp}",
                f"DTSTART;VALUE=DATE:{row['start_date'].replace('-', '')}",
                f"DTEND;VALUE=DATE:{row['end_date'].replace('-', '')}",
                "SUMMARY:Reserved - Arbor Vista Retreat",
                f"DESCRIPTION:{_ics_escape(description)}",
                "TRANSP:OPAQUE",
                "END:VEVENT",
            ]
        )
    lines.append("END:VCALENDAR")
    folded = [part for line in lines for part in _fold_ics_line(line)]
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(("\r\n".join(folded) + "\r\n").encode("utf-8"))
    return len(rows)


def database_health(*, db_path: Path = DEFAULT_DB_PATH) -> dict[str, Any]:
    with connect(db_path) as conn:
        foreign_keys = [dict(row) for row in conn.execute("PRAGMA foreign_key_check").fetchall()]
        invalid_dates = conn.execute(
            """SELECT COUNT(*) FROM reservations
               WHERE date(start_date) IS NULL OR date(end_date) IS NULL OR date(end_date)<=date(start_date)"""
        ).fetchone()[0]
        duplicate_uids = conn.execute(
            """SELECT COUNT(*) FROM (
                 SELECT calendar_source_id,external_uid,COUNT(*) c
                 FROM reservations
                 WHERE external_uid IS NOT NULL
                 GROUP BY calendar_source_id,external_uid HAVING c>1
               )"""
        ).fetchone()[0]
        running_syncs = conn.execute(
            "SELECT COUNT(*) FROM sync_runs WHERE status='running'"
        ).fetchone()[0]
        orphan_sources = conn.execute(
            """SELECT COUNT(*) FROM reservations r
               LEFT JOIN calendar_sources s ON s.id=r.calendar_source_id
               WHERE r.calendar_source_id IS NOT NULL AND s.id IS NULL"""
        ).fetchone()[0]
    checks = {
        "foreign_key_violations": len(foreign_keys),
        "invalid_date_ranges": invalid_dates,
        "duplicate_external_uids": duplicate_uids,
        "stuck_sync_runs": running_syncs,
        "orphan_calendar_sources": orphan_sources,
    }
    return {
        "status": "PASS" if all(value == 0 for value in checks.values()) else "FAIL",
        "checks": checks,
        "foreign_key_details": foreign_keys,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, default=DEFAULT_DB_PATH)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("init").add_argument("--reset", action="store_true")
    sync = sub.add_parser("sync")
    sync.add_argument("source_id", choices=["src_airbnb", "src_vrbo"])
    sync.add_argument("fixture", type=Path)
    sync.add_argument("--no-reconcile", action="store_true")
    sync_remote = sub.add_parser("sync-url")
    sync_remote.add_argument("source_id", choices=["src_airbnb", "src_vrbo"])
    sync_remote.add_argument("url")
    check = sub.add_parser("check")
    check.add_argument("start_date")
    check.add_argument("end_date")
    request = sub.add_parser("request")
    request.add_argument("start_date")
    request.add_argument("end_date")
    request.add_argument("guest_name")
    cancel = sub.add_parser("cancel")
    cancel.add_argument("reservation_id")
    block = sub.add_parser("block")
    block.add_argument("start_date")
    block.add_argument("end_date")
    block.add_argument("reason")
    export = sub.add_parser("export")
    export.add_argument("output", type=Path, nargs="?", default=ROOT / "exports" / "arbor-vista.ics")
    export.add_argument("--exclude-source", choices=["airbnb", "vrbo", "direct", "owner", "other"])
    sub.add_parser("health")
    args = parser.parse_args()

    try:
        if args.command == "init":
            init_db(args.db, args.reset)
            result: Any = {"initialized": True, "database": str(args.db)}
        elif args.command == "sync":
            result = sync_fixture(
                args.source_id,
                args.fixture,
                db_path=args.db,
                reconcile_missing=not args.no_reconcile,
            )
        elif args.command == "sync-url":
            result = sync_url(args.source_id, args.url, db_path=args.db)
        elif args.command == "check":
            result = availability(PROPERTY_ID, args.start_date, args.end_date, db_path=args.db)
        elif args.command == "request":
            result = create_booking_request(
                args.start_date, args.end_date, args.guest_name, db_path=args.db
            )
        elif args.command == "cancel":
            result = {"cancelled": cancel_reservation(args.reservation_id, db_path=args.db)}
        elif args.command == "block":
            result = create_owner_block(
                args.start_date, args.end_date, args.reason, db_path=args.db
            )
        elif args.command == "export":
            result = {
                "events_exported": export_ics(
                    args.output, db_path=args.db, exclude_source=args.exclude_source
                ),
                "output": str(args.output),
                "exclude_source": args.exclude_source,
            }
        else:
            result = database_health(db_path=args.db)
        print(json.dumps(result, indent=2))
    except Exception as exc:
        print(json.dumps({"error": type(exc).__name__, "message": str(exc)}, indent=2))
        raise SystemExit(2) from exc


if __name__ == "__main__":
    main()
