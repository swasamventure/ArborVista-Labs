# Arbor Vista Retreat v4.3.3 - Final Production-Safety Release

This is the final v4.3.x public-site package. Feature development is frozen until v4.4.

## Current booking state

- Direct-booking submission is disabled.
- The website collects no guest PII, signatures, or payment information.
- Current availability and reservations use Airbnb: https://www.airbnb.com/rooms/1587774879621242014
- Admin and guest-preview routes are excluded from the production package.

## Deploy

Upload the contents of this ZIP to the root of the production `ArborVista-Retreat` repository. In GitHub Pages settings, enable **Enforce HTTPS**. The bundled `CNAME` contains `arborvistaretreat.com`.

Do not restore `/admin`, `/guest`, the local role simulator, or the browser-only booking form before v4.4 authentication and secure persistence are live.

### Approved brand asset

The final v4.3.3 package uses `assets/arbor-vista-logo-v433.webp`, created from the approved circular cabin-and-mountain logo with the tagline **Rest. Renew. Reconnect.** The PNG master is included at `assets/arbor-vista-logo-v433.png`.
