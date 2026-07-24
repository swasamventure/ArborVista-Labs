#!/usr/bin/env python3
"""Create a privacy-filtered property transfer ZIP from the local database."""
from __future__ import annotations
import argparse, json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "Backend"))
from ical_db import connect, init_db
from operations import property_export_bytes

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("property_slug")
    parser.add_argument("--db", type=Path, default=ROOT / "Backend" / "arborvista_v41.db")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--include-future-guest-names", action="store_true")
    args = parser.parse_args()
    init_db(args.db, reset=False)
    with connect(args.db) as conn:
        payload, manifest = property_export_bytes(
            conn,
            args.property_slug,
            "cli-user",
            args.include_future_guest_names,
        )
        conn.commit()
    output = args.output or ROOT / "Backend" / "exports" / f"{args.property_slug}-transfer.zip"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(payload)
    print(json.dumps({"output": str(output), "manifest": manifest}, indent=2))

if __name__ == "__main__":
    main()
