#!/usr/bin/env python3
from __future__ import annotations

import json
import sqlite3
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PYTHON = sys.executable


def run(*args: str) -> dict:
    output = subprocess.check_output([PYTHON, str(ROOT / "ical_db.py"), *args], text=True)
    return json.loads(output)


def scalar(sql: str):
    with sqlite3.connect(ROOT / "arborvista_ical_test.db") as conn:
        row = conn.execute(sql).fetchone()
        return None if row is None else row[0]


def main() -> None:
    checks: list[tuple[str, bool, str]] = []
    run("init", "--reset")
    airbnb_first = run("sync", "src_airbnb", str(ROOT / "fixtures" / "airbnb_sample.ics"))
    vrbo_first = run("sync", "src_vrbo", str(ROOT / "fixtures" / "vrbo_sample.ics"))
    airbnb_second = run("sync", "src_airbnb", str(ROOT / "fixtures" / "airbnb_sample.ics"))

    checks.append(("Airbnb events inserted", airbnb_first["inserted"] == 2, str(airbnb_first)))
    checks.append(("Vrbo events inserted", vrbo_first["inserted"] == 2, str(vrbo_first)))
    checks.append(("Sync is idempotent", airbnb_second["inserted"] == 0 and airbnb_second["updated"] == 0, str(airbnb_second)))

    conflict = run("check", "2026-09-05", "2026-09-07")
    free = run("check", "2026-09-22", "2026-09-25")
    owner = run("check", "2026-10-13", "2026-10-14")
    checks.append(("Airbnb overlap detected", conflict["available"] is False and conflict["conflicts"][0]["source"] == "airbnb", str(conflict)))
    checks.append(("Free dates remain available", free["available"] is True, str(free)))
    checks.append(("Owner block detected", owner["available"] is False and owner["conflicts"][0]["source"] == "owner", str(owner)))

    direct = run("request", "2026-09-22", "2026-09-25", "QA Guest")
    duplicate = run("request", "2026-09-23", "2026-09-24", "Conflict Guest")
    checks.append(("Direct request created", direct["created"] is True, str(direct)))
    checks.append(("Conflicting request rejected", duplicate["created"] is False, str(duplicate)))

    exported = run("export", str(ROOT / "exports" / "arbor-vista.ics"))
    text = (ROOT / "exports" / "arbor-vista.ics").read_text(encoding="utf-8")
    checks.append(("Outbound ICS generated", exported["events_exported"] == 6 and text.count("BEGIN:VEVENT") == 6, str(exported)))
    checks.append(("Expected reservation count", scalar("SELECT COUNT(*) FROM reservations") == 5, str(scalar("SELECT COUNT(*) FROM reservations"))))
    checks.append(("Sync logs recorded", scalar("SELECT COUNT(*) FROM sync_runs") == 3, str(scalar("SELECT COUNT(*) FROM sync_runs"))))
    checks.append(("Audit log recorded", scalar("SELECT COUNT(*) FROM audit_log") >= 4, str(scalar("SELECT COUNT(*) FROM audit_log"))))
    checks.append(("Foreign key integrity", scalar("PRAGMA foreign_key_check") is None, "no violations"))

    passed = sum(1 for _, ok, _ in checks if ok)
    report = {
        "version": "2.8.0",
        "status": "PASS" if passed == len(checks) else "FAIL",
        "checks_passed": passed,
        "checks_total": len(checks),
        "checks": [{"name": name, "passed": ok, "detail": detail} for name, ok, detail in checks],
    }
    (ROOT.parent / "QA_REPORT_DATABASE.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    markdown = ["# Arbor Vista v2.8 iCal Database QA", "", f"**Status: {report['status']}**", "", f"Passed {passed} of {len(checks)} checks.", ""]
    for item in report["checks"]:
        markdown.append(f"- {'PASS' if item['passed'] else 'FAIL'} — {item['name']}")
    (ROOT.parent / "QA_REPORT_DATABASE.md").write_text("\n".join(markdown) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    if report["status"] != "PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
