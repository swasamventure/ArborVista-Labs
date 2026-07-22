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

## v2.3 Book Direct upgrade

The Book Direct page now uses a four-step guided flow:
1. Stay details
2. Guest details
3. Rental agreement and electronic signature
4. Review and confirmation

For testing on GitHub Pages, submissions are saved to the visitor's browser localStorage. No payment is collected and no data is transmitted. The confirmation screen generates a preview guest URL in the format `/guest/first-last-1234`.


## v2.3.1 cabin/gallery correction
- Corrected bedroom labels: `2732PC-30.jpeg` is the king suite and `2732PC-24.jpeg` is the queen suite.
- Expanded the Cabin page to show all bedroom, loft, living, kitchen, dining, bathroom, and hot-tub images.
- Expanded the Gallery page to include every image currently hosted in the production image library.


## v2.3.2 image-library update

- Includes all 86 images from the supplied `images.zip` directory.
- Replaces remote property-image dependencies with local GitHub-hosted assets.
- Uses every uploaded image on at least one website page.
- Adds complete Exterior, Property, Laundry, Shagbark Amenities, and Explore the Smokies collections.
- Keeps the corrected bedroom mapping: 2732PC-30/31/32 = King Suite; 2732PC-24/25/26 = Queen Suite.


## v2.3.3 Image Optimization

- Optimized 86 website images for GitHub Pages.
- Maximum image dimension: 1920 pixels.
- JPEG quality: 82, progressive and optimized.
- Original image payload: 219.4 MB.
- Optimized image payload: 56.3 MB.
- Reduction: 74.3%.
- Original master photos should be retained separately; this package contains web-ready copies.
