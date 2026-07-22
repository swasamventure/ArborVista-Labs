#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def run(script: Path) -> None:
    subprocess.run([sys.executable, str(script)], cwd=ROOT, check=True)


def main() -> None:
    run(ROOT / "Backend" / "run_qa.py")
    run(ROOT / "QA" / "run_web_qa.py")

    database = json.loads((ROOT / "QA_REPORT_DATABASE.json").read_text(encoding="utf-8"))
    website = json.loads((ROOT / "QA_REPORT_WEB_V2.8.json").read_text(encoding="utf-8"))
    passed = database["checks_passed"] + website["checks_passed"]
    total = database["checks_total"] + website["checks_total"]
    report = {
        "version": "2.8.1-final",
        "status": "PASS" if database["status"] == website["status"] == "PASS" else "FAIL",
        "checks_passed": passed,
        "checks_total": total,
        "suites": {
            "database_ical": {
                "status": database["status"],
                "passed": database["checks_passed"],
                "total": database["checks_total"],
            },
            "website_workflow": {
                "status": website["status"],
                "passed": website["checks_passed"],
                "total": website["checks_total"],
            },
        },
    }
    (ROOT / "QA_REPORT_FINAL.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    markdown = [
        "# Arbor Vista Retreat v2.8 Final QA",
        "",
        f"**Status: {report['status']}**",
        "",
        f"**Combined result: {passed} of {total} checks passed.**",
        "",
        f"- Database and iCal engine: {database['checks_passed']} of {database['checks_total']} PASS",
        f"- Website and booking workflow: {website['checks_passed']} of {website['checks_total']} PASS",
        "",
        "See `QA_REPORT_DATABASE.md` and `QA_REPORT_WEB_V2.8.md` for the full check lists.",
        "",
        "## Release boundary",
        "",
        "This confirms the packaged static website and local development calendar engine. It does not claim that real Airbnb/Vrbo feeds, scheduled cloud sync, or a live website-to-database API are connected.",
    ]
    (ROOT / "QA_REPORT_FINAL.md").write_text("\n".join(markdown) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    if report["status"] != "PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
