# Phase A — Market Intelligence

## GitHub Pages access

After extracting this package into the `ArborVista-Labs` repository and publishing GitHub Pages, open:

`https://swasamventure.github.io/ArborVista-Labs/admin/market-intelligence.html`

The Market Intelligence page is intentionally static and works without the local Python API. Other admin pages still require the local API until the Cloudflare/Supabase migration.

## Included

- Multi-property browser workspaces
- Address, radius, exact/expanded/custom comp profiles
- Fictional demonstration dataset
- CSV comp import with flexible column aliases
- Manual comp creation, inclusion/exclusion, deletion, and search
- Monthly ADR, occupancy, RevPAR, and revenue charts
- ADR-versus-occupancy scatter chart
- Future rate chart
- Amenity premium analysis
- Sleeps-six versus sleeps-seven/eight capacity analysis
- Comparable similarity ranking
- Editable property monthly actuals
- Browser localStorage persistence
- Workspace JSON import/export and analysis CSV export
- Provider-neutral Supabase schema starter

## Data safety

GitHub Pages is public. Do not commit private data or API credentials. Imported files remain in the browser unless the user explicitly exports them. Clear browser site data to remove a workspace.

## CSV format

Use `admin/data/market-comp-import-template.csv`. One listing can appear in 12 rows—one row per month. Supported aliases include `listing_name`/`name`, `review_count`/`reviews`, `distance_miles`/`distance`, `guests`/`accommodates`, and `data_source`/`source_label`.
