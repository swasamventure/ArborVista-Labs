# Cloud Migration Architecture

## Target model

- Independent public website per STR and domain
- Shared multi-property management dashboard
- Shared API and PostgreSQL database
- Every API request resolves a property by authenticated access and/or property slug
- GitHub remains the source repository and CI trigger
- Frontend hosting can move among GitHub Pages, Cloudflare Pages, Vercel, or similar without code rewrites

## Environment contract

Frontend reads `config/runtime-config.js`:
- `apiBaseUrl`
- `propertySlug`
- `environment`
- `requestTimeoutMs`

Backend reads environment variables:
- `ARBOR_DB_PATH`
- `ARBOR_HOST`
- `PORT`
- `ARBOR_ALLOWED_ORIGINS`
- `ARBOR_DEFAULT_PROPERTY_SLUG`

## Property sale

Each property has a self-contained folder under `properties/<slug>/`. Public website assets and domain can be transferred independently. The shared platform exports only that property's approved data.
