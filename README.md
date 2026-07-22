# ArborVista Retreat v2.0

Production-ready static website for GitHub Pages.

## Deploy
1. Create a new public GitHub repository.
2. Upload everything inside this folder to the repository root.
3. Open **Settings → Pages**.
4. Choose **Deploy from a branch**, branch **main**, folder **/(root)**.
5. Save and wait for GitHub Pages to publish.

## Important before launch
- Update `robots.txt` and `sitemap.xml` if the repository name or custom domain changes.
- The Airbnb URL is already wired to listing `1587774879621242014`.
- Property facts are consistently: **2 bedrooms + open loft, 4 beds, 2.5 baths, sleeps 6**.
- Direct booking is intentionally not enabled; Airbnb remains the booking source of truth.

## Editing
- Global design: `assets/style.css`
- Menu behavior: `assets/script.js`
- Page content: individual `.html` files
- Photography: `images/`


## Shared image hosting

This build intentionally does not include an `images` folder. Property images load from the existing production GitHub Pages site:

`https://swasamventure.github.io/ArborVista-Retreat/`

Keep that repository and its image folders public and do not rename or delete those image files. If those URLs change, update the absolute image URLs in the HTML files and `assets/style.css`.


## Review carousel
The homepage review area is rotation-ready. It currently contains the verified review text publicly shown on the Airbnb listing. Add future 5-star reviews as additional `<article class="review-card">` blocks and matching review-dot buttons. Initials-based avatars are used instead of copying guest profile photographs.
