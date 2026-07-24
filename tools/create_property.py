#!/usr/bin/env python3
"""Create an independently transferable property configuration package."""
from __future__ import annotations
import argparse, json, re, shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def slugify(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("name")
    parser.add_argument("code")
    parser.add_argument("--slug")
    parser.add_argument("--domain")
    parser.add_argument("--sleeps", type=int, default=6)
    parser.add_argument("--max-guests", type=int, default=8)
    parser.add_argument("--timezone", default="America/New_York")
    parser.add_argument("--output", type=Path, default=ROOT / "properties")
    args = parser.parse_args()
    slug = args.slug or slugify(args.name)
    if args.max_guests < args.sleeps:
        raise SystemExit("--max-guests must be at least --sleeps")
    out = args.output / slug
    if out.exists():
        raise SystemExit(f"Property package already exists: {out}")
    out.mkdir(parents=True)
    config = {
        "schemaVersion": 1,
        "propertyId": f"prop_{slug.replace('-', '_')}",
        "code": args.code,
        "slug": slug,
        "brandName": args.name,
        "publicDomain": args.domain,
        "timezone": args.timezone,
        "standardSleeps": args.sleeps,
        "maximumRequestedGuests": args.max_guests,
        "features": {"payments": False, "outboundEmail": False, "calendarSync": True, "guestPortal": True},
    }
    (out / "property.json").write_text(json.dumps(config, indent=2), encoding="utf-8")
    (out / "images").mkdir()
    (out / "guest-guide").mkdir()
    (out / "README.md").write_text(
        f"# {args.name}\n\nIndependent property package generated from the shared template.\n",
        encoding="utf-8",
    )
    print(json.dumps({"created": str(out), "property": config}, indent=2))

if __name__ == "__main__":
    main()
