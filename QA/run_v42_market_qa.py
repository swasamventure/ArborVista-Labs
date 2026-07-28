#!/usr/bin/env python3
from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
ADMIN = ROOT / "admin"
checks: list[dict] = []


def check(name: str, condition: bool, detail="") -> None:
    checks.append({"name": name, "passed": bool(condition), "detail": str(detail)[:3000]})


required = [
    ADMIN / "market-intelligence.html",
    ADMIN / "market-intelligence.css",
    ADMIN / "market-intelligence.js",
    ADMIN / "data/market-intelligence-demo.json",
    ADMIN / "data/market-intelligence-demo.js",
    ADMIN / "data/market-comp-import-template.csv",
    ROOT / "Docs/PHASE_A_MARKET_INTELLIGENCE.md",
    ROOT / "UPLOAD_TO_GITHUB.md",
    ROOT / "market-data/providers/ADAPTER_CONTRACT.md",
    ROOT / "supabase/migrations/004_market_intelligence_phase_a.sql",
]
for path in required:
    check(f"Required Phase A file exists: {path.relative_to(ROOT)}", path.exists())

html = (ADMIN / "market-intelligence.html").read_text(encoding="utf-8")
js = (ADMIN / "market-intelligence.js").read_text(encoding="utf-8")
css = (ADMIN / "market-intelligence.css").read_text(encoding="utf-8")
demo = json.loads((ADMIN / "data/market-intelligence-demo.json").read_text(encoding="utf-8"))
migration = (ROOT / "supabase/migrations/004_market_intelligence_phase_a.sql").read_text(encoding="utf-8").lower()

for element_id in [
    "miPropertySelector", "miAddress", "miProfile", "miRadius", "miCsvInput", "miJsonInput",
    "miSummaryMetrics", "miAdrChart", "miOccupancyChart", "miRevparChart", "miRevenueChart",
    "miScatterChart", "miFutureChart", "miAmenityChart", "miCapacityChart", "miRankingChart",
    "miReviewChart", "miCompTable", "miAddCompForm", "miActualsTable",
]:
    check(f"Market page contains #{element_id}", f'id="{element_id}"' in html)

check("Market page is GitHub project-path compatible", '<base href="/admin/">' not in html)
check("Market page warns that Phase A does not scrape channels", "does not scrape Airbnb, Vrbo, or Booking.com" in html)
check("Market page warns against storing secrets", "Do not place API keys" in html)
check("Two-property demo workspace included", len(demo.get("properties", [])) == 2)
check("Arbor Vista is the primary demo property", demo["properties"][0]["slug"] == "arbor-vista-retreat")
check("Arbor Vista retains standard occupancy six", demo["properties"][0]["standardGuests"] == 6)
check("Arbor Vista expanded scenario is eight", demo["properties"][0]["expandedGuests"] == 8)
check("Demo contains twelve fictional comps", len(demo["properties"][0]["comps"]) == 12)
check("Every demo comp is explicitly demo-labeled", all(c.get("sourceLabel") == "Demo data" for c in demo["properties"][0]["comps"]))
check("Demo comp names are fictional", all(c.get("name", "").startswith("Demo ") for c in demo["properties"][0]["comps"]))
check("No guest identity is included in market demo", not re.search(r"guest_name|guest email|guest phone", json.dumps(demo), re.I))
check("CSV parser implemented", "function parseCSV" in js)
check("CSV import grouping implemented", "function compsFromCSV" in js)
check("Workspace import/export implemented", "miExportWorkspace" in js and "miJsonInput" in js)
check("Browser persistence implemented", "arbor-market-workspace-v42" in js)
check("Graceful storage fallback implemented", "const storage" in js and "try { window.localStorage" in js)
check("Similarity scoring implemented", "function similarity" in js)
check("Amenity premium calculation implemented", "divergingBarChart" in js)
check("Capacity analysis implemented", "Sleeps ≤6" in js and "Sleeps 7–8" in js)
check("No external chart library dependency", "chart.js" not in html.lower() and "recharts" not in html.lower())
check("Responsive market CSS included", "@media(max-width:800px)" in css)

for table in ["comp_search_profiles", "comparable_properties", "comp_monthly_metrics", "comp_daily_rates"]:
    check(f"Supabase market migration table exists: {table}", f"create table if not exists public.{table}" in migration)

node = subprocess.run(["node", "--check", str(ADMIN / "market-intelligence.js")], capture_output=True, text=True)
check("Market JavaScript syntax passes", node.returncode == 0, node.stderr)

# Every admin page must use relative paths and offer the Market Intelligence navigation item.
for page in ADMIN.glob("*.html"):
    text = page.read_text(encoding="utf-8")
    check(f"No absolute admin base in {page.name}", '<base href="/admin/">' not in text)
    if page.name != "login.html":
        check(f"Market Intelligence navigation in {page.name}", "market-intelligence.html" in text)

# Browser QA uses an inlined document to avoid network dependencies in the test environment.
admin_css = (ADMIN / "admin.css").read_text(encoding="utf-8")
market_css = (ADMIN / "market-intelligence.css").read_text(encoding="utf-8")
demo_js = (ADMIN / "data/market-intelligence-demo.js").read_text(encoding="utf-8")
inline_html = re.sub(
    r'<link rel="stylesheet" href="admin.css\?v=4.2">\s*<link rel="stylesheet" href="market-intelligence.css\?v=4.2">',
    lambda _: f"<style>{admin_css}\n{market_css}</style>",
    html,
)
inline_html = re.sub(
    r'<script src="data/market-intelligence-demo.js\?v=4.2"></script>\s*<script src="market-intelligence.js\?v=4.2"></script>',
    lambda _: f"<script>{demo_js}</script><script>{js}</script>",
    inline_html,
)

inline_html = inline_html.replace('<script src="../config/runtime-config.js"></script>', '')

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True, executable_path="/usr/bin/chromium", args=["--no-sandbox"])
    page = browser.new_page(viewport={"width": 1440, "height": 1000}, accept_downloads=True)
    errors: list[str] = []
    page.on("console", lambda msg: errors.append(f"console {msg.type}: {msg.text}") if msg.type == "error" else None)
    page.on("pageerror", lambda err: errors.append(f"pageerror: {err}"))
    page.set_content(inline_html, wait_until="load")
    page.wait_for_selector("#miSummaryMetrics article")
    check("Browser renders five summary metrics", page.locator("#miSummaryMetrics article").count() == 5)
    check("Browser renders twelve initial comp rows", page.locator("#miCompTable tbody tr").count() == 12)
    check("Browser renders ten dynamic charts", page.locator("svg.market-chart").count() == 10)
    check("Browser renders two property choices", page.locator("#miPropertySelector option").count() == 2)
    check("Browser has no JavaScript errors", not errors, errors)

    page.click("#miApplyProfile")
    included = page.locator('#miCompTable input[data-mi-action="toggle"]:checked').count()
    check("Exact-match profile dynamically filters comps", 1 <= included < 12, included)

    initial_rows = page.locator("#miCompTable tbody tr").count()
    page.locator("#miAddCompForm").evaluate("form => form.closest('details').open = true")
    page.locator("#miAddCompForm input[name=name]").fill("Manual QA Cabin")
    page.locator("#miAddCompForm input[name=distanceMiles]").fill("1.8")
    page.locator("#miAddCompForm input[name=bedrooms]").fill("2")
    page.locator("#miAddCompForm input[name=bathrooms]").fill("2.5")
    page.locator("#miAddCompForm input[name=guests]").fill("6")
    page.locator("#miAddCompForm input[name=adr]").fill("260")
    page.locator("#miAddCompForm input[name=occupancy]").fill("65")
    page.locator("#miAddCompForm button[type=submit]").click()
    check("Manual comparable can be added", page.locator("#miCompTable tbody tr").count() == initial_rows + 1)

    with page.expect_download() as workspace_download:
        page.click("#miExportWorkspace")
    check("Workspace JSON export downloads", workspace_download.value.suggested_filename.endswith("market-workspace.json"))
    with page.expect_download() as analysis_download:
        page.click("#miExportAnalysis")
    check("Analysis CSV export downloads", analysis_download.value.suggested_filename.endswith("market-analysis.csv"))

    page.select_option("#miPropertySelector", "demo-smoky-cabin")
    check("Property selector switches the browser workspace", page.locator("#miAddress").input_value() == "Sevierville, TN")

    (ROOT / "QA/screenshots").mkdir(parents=True, exist_ok=True)
    page.screenshot(path=str(ROOT / "QA/screenshots/market-intelligence-desktop.png"), full_page=True)
    page.set_viewport_size({"width": 390, "height": 844})
    page.set_content(inline_html, wait_until="load")
    page.wait_for_selector("#miSummaryMetrics article")
    check("Mobile view retains all ten charts", page.locator("svg.market-chart").count() == 10)
    page.screenshot(path=str(ROOT / "QA/screenshots/market-intelligence-mobile.png"), full_page=True)
    browser.close()

passed = sum(item["passed"] for item in checks)
report = {
    "version": "4.2",
    "status": "PASS" if passed == len(checks) else "FAIL",
    "checks_passed": passed,
    "checks_total": len(checks),
    "checks": checks,
}
(ROOT / "QA_REPORT_V4.2_MARKET.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
print(json.dumps(report, indent=2))
if passed != len(checks):
    raise SystemExit(1)
