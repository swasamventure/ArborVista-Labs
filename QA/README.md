# QA Runner

## Full suite

```bash
python QA/run_all_qa.py
```

## QA dependencies

The database suite uses the Python standard library. The website/browser suite additionally requires:

- Beautiful Soup 4
- Pillow
- Playwright for Python
- Chromium, Chrome, or Edge

Install the Python packages with:

```bash
python -m pip install -r QA/requirements-qa.txt
python -m playwright install chromium
```

The runner uses `CHROMIUM_EXECUTABLE` when set. Otherwise it searches for common Chromium/Chrome/Edge executables and finally falls back to Playwright's installed browser.

The browser suite serves the package over a local HTTP server, verifies HTTP responses, inlines local assets for controlled DOM testing, checks desktop/mobile overflow, and exercises the booking and guest-preview workflows.
