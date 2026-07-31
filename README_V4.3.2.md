# Arbor Vista Platform v4.3.2 — UI Stabilization

This release stabilizes the premium v4.3 design without changing backend behavior.

## Test locally

```bash
python -m http.server 8000
```

Open `http://localhost:8000/`. Do not open the HTML files directly because browser security rules can affect JSON and JavaScript behavior.

## Main test paths

- `/` — premium homepage and signature-experience rotator
- `/cabin.html` — darker hero, sleeping-space and kitchen rotators
- `/gallery.html` — single-image filtered gallery
- `/explore.html` — single destination rotator
- `/book-direct.html` — four-step direct-booking request workflow

## Boundary

This is still a GitHub/static and local-backend test release. Real authentication, production email, Stripe, scheduled cloud sync, and hosted PostgreSQL deployment are not activated.
