#!/usr/bin/env python3
from __future__ import annotations

import contextlib
import json
import os
import socket
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from urllib.parse import urlparse

from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
QA_DIR = ROOT / "QA"
SCREENSHOT_DIR = QA_DIR / "screenshots"
PUBLIC_PAGES = [
    "index.html",
    "cabin.html",
    "gallery.html",
    "explore.html",
    "plan.html",
    "faq.html",
    "welcome.html",
    "rental-agreement.html",
    "book-direct.html",
    "404.html",
    "guest/index.html",
    "guest/john-smith-4827/index.html",
]


class QA:
    def __init__(self) -> None:
        self.checks: list[dict] = []

    def check(self, name: str, condition: bool, detail: object = "") -> None:
        self.checks.append({"name": name, "passed": bool(condition), "detail": str(detail)[:3000]})



def browser_launch_options() -> dict:
    explicit = os.environ.get("CHROMIUM_EXECUTABLE")
    candidates = [explicit] if explicit else []
    candidates += [
        shutil.which("chromium"),
        shutil.which("chromium-browser"),
        shutil.which("google-chrome"),
        shutil.which("google-chrome-stable"),
        shutil.which("msedge"),
        shutil.which("microsoft-edge"),
    ]
    executable = next((candidate for candidate in candidates if candidate and Path(candidate).exists()), None)
    options = {
        "headless": True,
        "args": ["--no-sandbox", "--disable-dev-shm-usage"],
    }
    if executable:
        options["executable_path"] = executable
    return options

def find_free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def local_target(value: str) -> str | None:
    parsed = urlparse(value)
    if parsed.scheme or parsed.netloc or value.startswith(("mailto:", "tel:", "javascript:")):
        return None
    path = parsed.path
    if not path or path.startswith("#"):
        return None
    if path.startswith("/ArborVista-Labs/"):
        path = path.removeprefix("/ArborVista-Labs/")
    elif path.startswith("/"):
        return None
    return path


def static_checks(qa: QA) -> None:
    missing: list[str] = []
    duplicate_ids: list[str] = []
    missing_alt: list[str] = []
    unlabeled: list[str] = []
    missing_metadata: list[str] = []
    wrong_base: list[str] = []

    for rel in PUBLIC_PAGES:
        path = ROOT / rel
        soup = BeautifulSoup(path.read_text(encoding="utf-8"), "html.parser")
        if not soup.title or not soup.title.get_text(strip=True):
            missing_metadata.append(f"{rel}: title")
        viewport = soup.find("meta", attrs={"name": "viewport"})
        if not viewport:
            missing_metadata.append(f"{rel}: viewport")
        base = soup.find("base")
        if not base or base.get("href") != "/ArborVista-Labs/":
            wrong_base.append(rel)

        ids: dict[str, int] = {}
        for element in soup.find_all(attrs={"id": True}):
            ids[element["id"]] = ids.get(element["id"], 0) + 1
        duplicate_ids.extend(f"{rel}#{key}" for key, count in ids.items() if count > 1)

        for img in soup.find_all("img"):
            if not img.has_attr("alt"):
                missing_alt.append(f"{rel}:{img.get('src', '')}")

        for element in soup.find_all(["input", "select", "textarea"]):
            if element.get("type") == "hidden":
                continue
            element_id = element.get("id")
            wrapped = element.find_parent("label") is not None
            matching = bool(element_id and soup.find("label", attrs={"for": element_id}))
            if not (wrapped or matching):
                unlabeled.append(f"{rel}:{element.name}[name={element.get('name', '')}]")

        for tag, attr in (("a", "href"), ("link", "href"), ("script", "src"), ("img", "src")):
            for element in soup.find_all(tag):
                value = element.get(attr)
                if not value:
                    continue
                target = local_target(value)
                if target is None:
                    continue
                candidate = ROOT / target
                if target.endswith("/"):
                    candidate = candidate / "index.html"
                elif not candidate.suffix and not candidate.exists():
                    html_candidate = candidate.with_suffix(".html")
                    if html_candidate.exists():
                        candidate = html_candidate
                if not candidate.exists():
                    missing.append(f"{rel}: {value}")

    qa.check("All expected HTML pages exist", all((ROOT / page).exists() for page in PUBLIC_PAGES), PUBLIC_PAGES)
    qa.check("All local HTML/CSS/JS/image references resolve", not missing, missing)

    # Decode each packaged image file, not only the browser placeholders used below.
    from PIL import Image
    corrupt_images = []
    for image_path in sorted((ROOT / "images").rglob("*")):
        if not image_path.is_file():
            continue
        try:
            with Image.open(image_path) as image:
                image.verify()
        except Exception as exc:
            corrupt_images.append(f"{image_path.relative_to(ROOT)}: {exc}")
    qa.check("All packaged image files decode successfully", not corrupt_images, corrupt_images)
    qa.check("HTML IDs are unique per page", not duplicate_ids, duplicate_ids)
    qa.check("Every image has alt text", not missing_alt, missing_alt)
    qa.check("Form controls have accessible labels", not unlabeled, unlabeled)
    qa.check("Every page has title and viewport metadata", not missing_metadata, missing_metadata)
    qa.check("GitHub Pages base path is consistent", not wrong_base, wrong_base)

    all_html = "\n".join((ROOT / page).read_text(encoding="utf-8") for page in PUBLIC_PAGES).lower()
    qa.check("Property is never described as three bedrooms", "3 bedroom" not in all_html and "three bedroom" not in all_html)
    qa.check("Occupancy language supports approved seven-to-eight guest requests", "sleeps 6" in all_html and "seven or eight" in all_html and "maximum occupancy of six" not in all_html)
    qa.check("Correct room model is present", "2 bedrooms + open loft" in all_html or "2 bedrooms + loft" in all_html)
    qa.check("Guest paths are excluded from robots", "Disallow: /guest/" in (ROOT / "robots.txt").read_text())

    node = subprocess.run(["node", "--check", str(ROOT / "assets" / "script.js")], capture_output=True, text=True)
    qa.check("Shared JavaScript passes syntax check", node.returncode == 0, node.stderr)

    py_files = [ROOT / "Backend" / "ical_db.py", ROOT / "Backend" / "run_qa.py", ROOT / "QA" / "run_web_qa.py"]
    compile_result = subprocess.run([sys.executable, "-m", "py_compile", *map(str, py_files)], capture_output=True, text=True)
    qa.check("Python QA and backend files compile", compile_result.returncode == 0, compile_result.stderr)


def route_external(route) -> None:
    url = route.request.url
    if url.startswith("http://127.0.0.1"):
        route.continue_()
    elif "fonts.googleapis.com" in url:
        route.fulfill(status=200, content_type="text/css", body="")
    elif "fonts.gstatic.com" in url:
        route.fulfill(status=200, content_type="font/woff2", body=b"wOF2")
    else:
        route.abort()


def render_page(rel: str) -> str:
    """Inline local assets so Chromium can test on about:blank despite URL policy."""
    import base64
    import mimetypes

    soup = BeautifulSoup((ROOT / rel).read_text(encoding="utf-8"), "html.parser")
    if soup.base:
        soup.base["href"] = "https://arborvista.test/ArborVista-Labs/"

    for link in list(soup.find_all("link")):
        href = link.get("href", "")
        target = local_target(href)
        if target == "assets/style.css":
            style = soup.new_tag("style")
            style.string = (ROOT / "assets" / "style.css").read_text(encoding="utf-8")
            link.replace_with(style)
        elif href.startswith("https://"):
            link.decompose()

    for script in list(soup.find_all("script", src=True)):
        script.decompose()

    for img in soup.find_all("img"):
        src = img.get("src", "")
        target = local_target(src)
        if not target:
            continue
        path = ROOT / target
        from PIL import Image
        with Image.open(path) as image:
            width, height = image.size
        svg = f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}"><rect width="100%" height="100%" fill="#d8dedb"/></svg>'
        encoded = base64.b64encode(svg.encode("utf-8")).decode("ascii")
        img["src"] = f"data:image/svg+xml;base64,{encoded}"

    return str(soup)


def install_storage_polyfill(page) -> None:
    page.evaluate("""
      if (!window.__qaStorage) window.__qaStorage = new Map();
      Object.defineProperty(window, 'localStorage', {
        configurable: true,
        value: {
          getItem: key => window.__qaStorage.has(String(key)) ? window.__qaStorage.get(String(key)) : null,
          setItem: (key, value) => window.__qaStorage.set(String(key), String(value)),
          removeItem: key => window.__qaStorage.delete(String(key)),
          clear: () => window.__qaStorage.clear(),
          key: index => [...window.__qaStorage.keys()][index] ?? null,
          get length() { return window.__qaStorage.size; }
        }
      });
    """)


def browser_checks(qa: QA) -> None:
    SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)
    for old in SCREENSHOT_DIR.glob("*.png"):
        old.unlink()

    # Verify the package can actually be served over HTTP using Python's local server.
    with tempfile.TemporaryDirectory(prefix="arborvista-web-root-") as tmp:
        import urllib.request
        web_root = Path(tmp)
        os.symlink(ROOT, web_root / "ArborVista-Labs", target_is_directory=True)
        port = find_free_port()
        server = subprocess.Popen(
            [sys.executable, "-m", "http.server", str(port), "--bind", "127.0.0.1"],
            cwd=web_root,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        try:
            for _ in range(40):
                with socket.socket() as sock:
                    if sock.connect_ex(("127.0.0.1", port)) == 0:
                        break
                time.sleep(0.1)
            statuses = []
            for rel in PUBLIC_PAGES:
                with urllib.request.urlopen(f"http://127.0.0.1:{port}/ArborVista-Labs/{rel}", timeout=5) as response:
                    statuses.append((rel, response.status, response.headers.get_content_type()))
            qa.check("All website pages return HTTP 200", all(status == 200 for _, status, _ in statuses), statuses)
        finally:
            server.terminate()
            with contextlib.suppress(subprocess.TimeoutExpired):
                server.wait(timeout=3)
            if server.poll() is None:
                server.kill()

    shared_js = (ROOT / "assets" / "script.js").read_text(encoding="utf-8")
    wrapped_js = "(function(){\n" + shared_js + "\n})();"
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(**browser_launch_options())
        context = browser.new_context(viewport={"width": 1440, "height": 1000})
        page = context.new_page()
        page.set_default_timeout(5000)
        install_storage_polyfill(page)
        page_errors: list[str] = []
        page.on("pageerror", lambda error: page_errors.append(str(error)))

        def load(rel: str) -> None:
            page.set_content(render_page(rel), wait_until="domcontentloaded")
            install_storage_polyfill(page)
            page.add_script_tag(content=wrapped_js)
            page.wait_for_timeout(50)

        page_results = []
        for rel in PUBLIC_PAGES:
            load(rel)
            page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            page.wait_for_timeout(50)
            broken_images = page.locator("img").evaluate_all(
                "els => els.filter(e => e.complete && e.naturalWidth === 0).map(e => e.getAttribute('alt'))"
            )
            overflow = page.evaluate("document.documentElement.scrollWidth > document.documentElement.clientWidth + 2")
            page_results.append({"page": rel, "broken_images": broken_images, "horizontal_overflow": overflow})
        qa.check("All inlined page images decode in Chromium", all(not item["broken_images"] for item in page_results), page_results)
        qa.check("Desktop pages have no horizontal overflow", all(not item["horizontal_overflow"] for item in page_results), page_results)
        qa.check("Website produces no uncaught JavaScript errors", not page_errors, page_errors)

        mobile = browser.new_context(viewport={"width": 390, "height": 844})
        mobile_page = mobile.new_page()
        mobile_page.set_default_timeout(5000)
        install_storage_polyfill(mobile_page)

        def load_mobile(rel: str) -> None:
            mobile_page.set_content(render_page(rel), wait_until="domcontentloaded")
            install_storage_polyfill(mobile_page)
            mobile_page.add_script_tag(content=wrapped_js)
            mobile_page.wait_for_timeout(50)

        load_mobile("index.html")
        menu_button = mobile_page.locator(".menu")
        menu_button.click()
        qa.check(
            "Mobile menu opens and updates aria-expanded",
            menu_button.get_attribute("aria-expanded") == "true"
            and "open" in (mobile_page.locator(".links").get_attribute("class") or ""),
            menu_button.get_attribute("aria-expanded"),
        )
        mobile_overflow = []
        for rel in PUBLIC_PAGES[:10]:
            load_mobile(rel)
            mobile_overflow.append((rel, mobile_page.evaluate("document.documentElement.scrollWidth > document.documentElement.clientWidth + 2")))
        qa.check("Mobile pages have no horizontal overflow", not any(value for _, value in mobile_overflow), mobile_overflow)
        load_mobile("index.html")
        mobile_page.screenshot(path=str(SCREENSHOT_DIR / "home-mobile.png"), full_page=True)
        mobile.close()

        # Draft restore and start-over behavior.
        load("book-direct.html")
        page.evaluate("localStorage.clear()")
        load("book-direct.html")
        page.fill("#check_in", "2026-12-10")
        page.fill("#check_out", "2026-12-14")
        page.select_option("#adults", "2")
        page.select_option("#children", "2")
        page.click('[data-booking-step="1"] [data-next]')
        page.fill("#first_name", "Draft", timeout=3000)
        page.fill("#last_name", "Guest")
        page.fill("#email", "draft@example.com")
        page.fill("#phone", "512-555-1212")
        page.wait_for_timeout(400)
        load("book-direct.html")
        qa.check(
            "Booking draft restores after refresh",
            page.locator('[data-booking-step="2"]').evaluate("e => e.classList.contains('active')")
            and page.input_value("#first_name") == "Draft"
            and page.input_value("#check_in") == "2026-12-10",
            page.input_value("#first_name"),
        )
        qa.check(
            "Restored check-in recalculates checkout minimum",
            page.get_attribute("#check_out", "min") == "2026-12-11",
            page.get_attribute("#check_out", "min"),
        )
        page.get_by_role("button", name="Start over").click()
        qa.check(
            "Start over clears the restored draft",
            page.input_value("#first_name") == ""
            and page.input_value("#check_in") == ""
            and page.evaluate("localStorage.getItem('arbor-vista-booking-draft-v2')") is None,
            "draft cleared",
        )

        # Complete form validation and submission.
        page.click('[data-booking-step="1"] [data-next]')
        qa.check(
            "Blank Step 1 cannot advance",
            page.locator('[data-booking-step="1"]').evaluate("e => e.classList.contains('active')")
            and page.locator('[data-booking-step="1"] .field-error').count() >= 3,
            page.locator('[data-booking-step="1"] .field-error').count(),
        )
        page.fill("#check_in", "2026-12-10")
        page.fill("#check_out", "2026-12-14")
        page.select_option("#adults", "6")
        page.select_option("#children", "1")
        page.click('[data-booking-step="1"] [data-next]')
        qa.check(
            "Seven-guest request is allowed for host review",
            page.locator('[data-booking-step="2"]').evaluate("e => e.classList.contains('active')"),
            page.locator('[data-booking-step="2"]').inner_text(),
        )
        page.click('[data-booking-step="2"] [data-back]')
        page.select_option("#adults", "8")
        page.select_option("#children", "1")
        page.click('[data-booking-step="1"] [data-next]')
        qa.check(
            "More than eight total guests is rejected",
            "limited to eight guests" in page.locator('[data-booking-step="1"]').inner_text().lower(),
            page.locator('[data-booking-step="1"]').inner_text(),
        )
        page.select_option("#adults", "6")
        page.select_option("#children", "0")
        page.click('[data-booking-step="1"] [data-next]')
        qa.check("Valid Step 1 advances", page.locator('[data-booking-step="2"]').evaluate("e => e.classList.contains('active')"))

        xss_name = 'QA <img id="xss-marker" src=x onerror="window.xss=1">'
        page.fill("#first_name", xss_name)
        page.fill("#last_name", "Guest")
        page.fill("#email", "qa@example.com")
        page.fill("#phone", "123")
        page.click('[data-booking-step="2"] [data-next]')
        qa.check(
            "Invalid phone number cannot advance",
            "valid mobile phone" in page.locator('[data-booking-step="2"]').inner_text().lower(),
            page.locator('[data-booking-step="2"]').inner_text(),
        )
        page.fill("#phone", "+1 (512) 555-1212")
        page.click('[data-booking-step="2"] [data-next]')
        qa.check("Valid Step 2 advances", page.locator('[data-booking-step="3"]').evaluate("e => e.classList.contains('active')"))

        legal_name = page.input_value("#legal_name")
        page.fill("#electronic_signature", "Different Name")
        page.check("#agree_terms")
        page.check("#certify")
        page.click('[data-booking-step="3"] [data-next]')
        qa.check(
            "Electronic signature must match legal name",
            "Signature must match" in page.locator('[data-booking-step="3"]').inner_text(),
            page.locator('[data-booking-step="3"]').inner_text(),
        )
        page.fill("#electronic_signature", legal_name)
        page.click('[data-booking-step="3"] [data-next]')
        qa.check("Valid agreement advances to review", page.locator('[data-booking-step="4"]').evaluate("e => e.classList.contains('active')"))
        qa.check(
            "Review renders guest text without HTML injection",
            page.locator("#xss-marker").count() == 0
            and xss_name in page.locator("[data-booking-review]").inner_text()
            and page.evaluate("window.xss") is None,
            page.locator("[data-booking-review]").inner_text(),
        )

        page.click('[data-step-nav="1"]')
        preserved = page.input_value("#check_in") == "2026-12-10" and page.input_value("#first_name") == xss_name
        page.click('[data-step-nav="4"]')
        qa.check(
            "Clickable progress steps preserve completed information",
            preserved and page.locator('[data-booking-step="4"]').evaluate("e => e.classList.contains('active')"),
            "preserved",
        )

        page.click('button[type="submit"]')
        qa.check(
            "Successful request shows confirmation",
            page.locator('[data-booking-step="5"]').evaluate("e => e.classList.contains('active')")
            and "Thank you" in page.locator('[data-booking-step="5"]').inner_text(),
            page.locator('[data-booking-step="5"]').inner_text(),
        )
        guest_href = page.get_attribute("[data-guest-link]", "href") or ""
        qa.check("Confirmation creates a working guest preview link", "/guest/?id=" in guest_href, guest_href)
        qa.check(
            "Submission keeps request but clears unfinished draft",
            page.evaluate("localStorage.getItem('arbor-vista-booking-request') !== null")
            and page.evaluate("localStorage.getItem('arbor-vista-booking-draft-v2') === null"),
            "storage state",
        )
        page.screenshot(path=str(SCREENSHOT_DIR / "booking-confirmation-desktop.png"), full_page=True)

        load("guest/index.html")
        qa.check(
            "Guest preview loads submitted request safely",
            page.locator("#xss-marker").count() == 0
            and xss_name in page.locator("[data-portal-review]").inner_text()
            and page.evaluate("window.xss") is None,
            page.locator("[data-portal-review]").inner_text(),
        )
        page.screenshot(path=str(SCREENSHOT_DIR / "guest-preview-desktop.png"), full_page=True)

        page.evaluate("localStorage.setItem('arbor-vista-booking-request', '{bad json')")
        load("guest/index.html")
        qa.check(
            "Corrupted guest-preview storage fails safely",
            "preview unavailable" in page.locator("[data-portal-review]").inner_text().lower(),
            page.locator("[data-portal-review]").inner_text(),
        )

        load("guest/john-smith-4827/index.html")
        page.evaluate("localStorage.removeItem('gate-pass-demo')")
        load("guest/john-smith-4827/index.html")
        page.click('form[data-save="gate-pass-demo"] button')
        qa.check(
            "Blank gate-pass form is not stored",
            page.evaluate("localStorage.getItem('gate-pass-demo')") is None,
            "no storage",
        )
        page.fill("#driver_name", "QA Driver")
        page.fill("#gate_email", "driver@example.com")
        page.fill("#gate_phone", "5125551212")
        page.select_option("#gate_vehicles", "2")
        page.check("#consent")
        page.click('form[data-save="gate-pass-demo"] button')
        stored_gate = page.evaluate("JSON.parse(localStorage.getItem('gate-pass-demo'))")
        qa.check(
            "Gate-pass form stores valid data and consent",
            stored_gate.get("driver_name") == "QA Driver" and stored_gate.get("consent") is True,
            stored_gate,
        )
        qa.check(
            "Gate-pass success message appears",
            page.locator('[data-success="gate-pass-demo"]').evaluate("e => e.classList.contains('show')"),
            "success visible",
        )
        load("guest/john-smith-4827/index.html")
        qa.check(
            "Gate-pass status persists after refresh",
            "Information received" in page.locator("[data-gate-status]").inner_text(),
            page.locator("[data-gate-status]").inner_text(),
        )
        browser.close()

def main() -> None:
    qa = QA()
    static_checks(qa)
    browser_checks(qa)
    passed = sum(1 for item in qa.checks if item["passed"])
    report = {
        "version": "2.8.1-final",
        "status": "PASS" if passed == len(qa.checks) else "FAIL",
        "checks_passed": passed,
        "checks_total": len(qa.checks),
        "checks": qa.checks,
    }
    (ROOT / "QA_REPORT_WEB_V2.8.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    lines = [
        "# Arbor Vista v2.8 Website QA",
        "",
        f"**Status: {report['status']}**",
        "",
        f"Passed {passed} of {len(qa.checks)} automated checks.",
        "",
    ]
    lines.extend(f"- {'PASS' if item['passed'] else 'FAIL'} — {item['name']}" for item in qa.checks)
    (ROOT / "QA_REPORT_WEB_V2.8.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    if report["status"] != "PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
