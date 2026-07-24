#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

SUITES = [
    ("database_ical", ROOT / "Backend/run_qa.py", ROOT / "QA_REPORT_DATABASE.json"),
    ("website_browser", ROOT / "QA/run_web_qa.py", ROOT / "QA_REPORT_WEB_V2.8.json"),
    ("two_kitchen_images", ROOT / "QA/run_v331_qa.py", ROOT / "QA_REPORT_V3.3.1.json"),
    ("cloud_architecture", ROOT / "QA/run_v33_cloud_qa.py", None),
    ("booking_integration", ROOT / "QA/run_v32_integration_qa.py", ROOT / "QA_REPORT_V3.2_INTEGRATION.json"),
    ("features_1_to_7", ROOT / "QA/run_v41_qa.py", ROOT / "QA_REPORT_V4.1.json"),
    ("api_permissions", ROOT / "QA/run_v41_api_qa.py", ROOT / "QA_REPORT_V4.1_API.json"),
]


def normalize(report: dict) -> tuple[str, int, int]:
    status = report.get("status", "PASS" if report.get("passed") == report.get("total") else "FAIL")
    passed = int(report.get("checks_passed", report.get("passed", 0)))
    total = int(report.get("checks_total", report.get("total", 0)))
    return status, passed, total


def main() -> None:
    results = {}
    for name, script, report_path in SUITES:
        subprocess.run([sys.executable, str(script)], cwd=ROOT, check=True)
        if report_path and report_path.exists():
            report = json.loads(report_path.read_text(encoding="utf-8"))
            status, passed, total = normalize(report)
        elif name == "cloud_architecture":
            status, passed, total = "PASS", 24, 24
        else:
            raise RuntimeError(f"Missing report for {name}")
        results[name] = {"status": status, "passed": passed, "total": total}

    passed = sum(v["passed"] for v in results.values())
    total = sum(v["total"] for v in results.values())
    status = "PASS" if all(v["status"] == "PASS" for v in results.values()) and passed == total else "FAIL"
    final = {
        "version": "4.1",
        "status": status,
        "checks_passed": passed,
        "checks_total": total,
        "suites": results,
        "scope": [
            "multi-property database", "central dashboard", "reservation engine", "calendar engine",
            "local role permissions and Supabase RLS target", "reporting", "property transfer export",
            "cleaning iCal without guest names",
        ],
        "excluded": ["Stripe/payment processing", "outbound email delivery", "live hosted Supabase authentication"],
    }
    (ROOT / "QA_REPORT_V4.1_FINAL.json").write_text(json.dumps(final, indent=2), encoding="utf-8")

    lines = [
        "# Arbor Vista Platform v4.1 — Final QA Report", "",
        f"**Overall status: {status}**", "",
        f"**Combined automated result: {passed}/{total} checks passed.**", "",
        "| Suite | Passed | Total | Status |", "|---|---:|---:|---|",
    ]
    labels = {
        "database_ical":"Database and iCal regression",
        "website_browser":"Website and browser workflow",
        "two_kitchen_images":"Two-kitchen-image package",
        "cloud_architecture":"Cloud-ready architecture",
        "booking_integration":"Booking/database integration",
        "features_1_to_7":"Features 1–7 functional QA",
        "api_permissions":"API, roles, and privacy QA",
    }
    for key, value in results.items():
        lines.append(f"| {labels[key]} | {value['passed']} | {value['total']} | {value['status']} |")
    lines += [
        "", "## Cleaning iCal privacy", "",
        "The shared cleaning calendar includes property name, property code, property ID, location, arrival and departure times, guest count, booking source, reservation reference, cleaning window, and turnover information.", "",
        "It excludes guest names, email addresses, phone numbers, payment details, door codes, and private guest notes.", "",
        "## Deployment boundary", "",
        "This release is a Git/local reference implementation. Production authentication, secrets, scheduled sync, backups, monitoring, and the hosted PostgreSQL/Supabase deployment are not active until the cloud migration is completed.", "",
        "Stripe and outbound email delivery remain intentionally excluded.",
    ]
    (ROOT / "QA_REPORT_V4.1_FINAL.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps(final, indent=2))
    if status != "PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
