# Arbor Vista Platform v4.3.2 — UI Stabilization

## Completed

- Standardized the v4.3 visual system across all public pages.
- Preserved the mountain-and-pine Arbor Vista Retreat logo lockup in every header and footer.
- Added active-navigation state, keyboard focus treatment, skip links, canonical URLs, Open Graph metadata, favicon, and updated sitemap.
- Added consistent direct-booking calls to action and a mobile sticky availability button across the public site.
- Upgraded every content rotator to a three-second fade with previous, next, pause/play, dots, keyboard, swipe, hover/focus pause, visibility pause, and reduced-motion support.
- Converted the Explore destination grid to one rotating destination at a time.
- Rebuilt the Gallery as a single-image filtered viewer. The full collection remains available without loading or displaying dozens of images simultaneously.
- Deferred inactive rotator images until needed and added hero preloads and asynchronous image decoding.
- Added a provider-neutral, privacy-safe analytics placeholder for page views, navigation, booking CTA, booking progress, gallery, and rotator events. It sends nothing unless an analytics endpoint is configured.
- Rebuilt the 404 page with the shared visual system and booking path.

## Not changed

- Reservation, calendar, iCal, database, admin-dashboard, Market Intelligence, rental-agreement, and guest-portal backend behavior.
- Stripe and production email delivery remain deferred.
- The analytics placeholder deliberately excludes personal-form fields.
