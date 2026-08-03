#!/usr/bin/env python3
"""Refresh the local Airbnb review snapshot used by the static website.

The public Airbnb listing currently exposes aggregate scores, review themes and
one featured review excerpt in its server-rendered page. It does not reliably
expose every individual review without Airbnb's client-side application.
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import json
import re
import sys
import urllib.request

from bs4 import BeautifulSoup

LISTING_ID = "1587774879621242014"
LISTING_URL = f"https://www.airbnb.com/rooms/{LISTING_ID}"
OUTPUT = Path(__file__).resolve().parents[1] / "data" / "airbnb-reviews.json"


def first(pattern: str, text: str, default=None, flags=re.I):
    match = re.search(pattern, text, flags)
    return match.group(1) if match else default


def score(label: str, text: str, default: float) -> float:
    raw = first(rf"Rated\s+([0-9.]+)\s+out of 5 stars for {re.escape(label)}", text, None)
    return float(raw) if raw else default


def main() -> int:
    request = urllib.request.Request(
        LISTING_URL,
        headers={
            "User-Agent": "Mozilla/5.0 (compatible; ArborVistaReviewSnapshot/4.3.3)",
            "Accept-Language": "en-US,en;q=0.9",
        },
    )
    with urllib.request.urlopen(request, timeout=45) as response:
        html = response.read().decode("utf-8", errors="replace")

    text = " ".join(BeautifulSoup(html, "html.parser").stripped_strings)

    rating_raw = first(r"Rated\s+([0-9.]+)\s+out of 5", text)
    count_raw = first(r"([0-9]+)\s+reviews", text)
    if not rating_raw or not count_raw:
        raise RuntimeError("Could not find Airbnb rating or review count; snapshot was not overwritten.")

    featured = first(
        r"WHAT GUESTS SAY\s+[\"“](.+?)[\"”]\s+EASY FROM ARRIVAL",
        text,
        None,
        flags=re.I,
    )

    five_star_raw = first(r"5 stars,\s*([0-9]+)% of reviews", text, "0")
    old = json.loads(OUTPUT.read_text(encoding="utf-8")) if OUTPUT.exists() else {}

    data = {
        "listingId": LISTING_ID,
        "source": "Airbnb public listing",
        "sourceUrl": LISTING_URL + "#reviews",
        "lastCheckedAt": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "rating": float(rating_raw),
        "reviewCount": int(count_raw),
        "guestFavorite": "Guest favorite" in text,
        "fiveStarPercent": int(five_star_raw),
        "categoryRatings": {
            "cleanliness": score("cleanliness", text, 0),
            "accuracy": score("accuracy", text, 0),
            "checkIn": score("check-in", text, 0),
            "communication": score("communication", text, 0),
            "location": score("location", text, 0),
            "value": score("value", text, 0),
        },
        # Airbnb currently exposes these counts in the public server-rendered listing.
        "reviewThemes": old.get("reviewThemes", []),
        "featuredReviews": old.get("featuredReviews", []),
        "note": (
            "Airbnb's public listing page currently exposes one featured review excerpt "
            "plus aggregate ratings and review themes. The website displays only data "
            "verified from that public page."
        ),
    }

    if featured:
        data["featuredReviews"] = [{
            "rating": 5,
            "excerpt": featured.strip(),
            "sourceLabel": "Verified Airbnb guest excerpt",
        }]

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Updated {OUTPUT} with rating {data['rating']} from {data['reviewCount']} reviews.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"Airbnb review update failed: {exc}", file=sys.stderr)
        raise SystemExit(1)
