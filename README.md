# Arbor Vista Retreat v2.2 — Guest Experience Test

GitHub Pages-ready static test package.

## Added in v2.2
- Luxury-style `book-direct.html` request form
- Branded `rental-agreement.html` draft
- Public mobile-friendly `welcome.html` guide
- Personalized demo portal: `guest/john-smith-4827/`
- Shagbark vehicle-registration test form
- Booking and 3-day-arrival message templates
- Professional signature links
- SEO metadata, VacationRental structured data, sitemap and robots rules
- Remote property images from the production ArborVista-Retreat repository

## Test locally
Open `index.html`, or run:

```bash
python -m http.server 8000
```

Then visit `http://localhost:8000`.

## GitHub deployment
Upload the contents of this folder to the **root** of `ArborVista-Labs`, commit, and enable GitHub Pages from `main` / `(root)`.

## Demo guest URL
On GitHub Pages:
`https://swasamventure.github.io/ArborVista-Labs/guest/john-smith-4827/`

Future production format:
`https://arborvistaretreat.com/guest/<first-name>-<last-name>-<4-digit-random-number>`

## Important limitations
This static version simulates form submission with browser `localStorage`. It does not email, create guest records, schedule messages, validate PINs, or securely reveal address/codes. Sensitive details must not be embedded until a secure backend is added.

The rental agreement is a working content draft, not legal advice. Obtain Tennessee legal review before using it with guests.
