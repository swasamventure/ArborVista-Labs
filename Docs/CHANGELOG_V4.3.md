# Arbor Vista Platform v4.3 — Premium UI Simplification

## Purpose

v4.3 applies the editorial visual direction preferred from the production site while reducing image density and preserving the v4.2.1 platform, booking, calendar, cleaning, Market Intelligence, and multi-property capabilities.

## Implemented

- Uses the supplied Arbor Vista logo lockup extracted from the left side of the approved brand image.
- Uses Playfair Display for editorial headings and DM Sans for body/navigation typography.
- Adds a restrained forest, cream, sand, and gold design system.
- Simplifies primary navigation to The Cabin, Gallery, Explore, FAQ, and Book Direct.
- Replaces the homepage image-heavy layout with one hero and six supporting images.
- Keeps the complete photo collection on the dedicated Gallery page.
- Redesigns The Cabin page with a smaller curated image set and stronger information hierarchy.
- Adds transparent-over-hero navigation that changes to cream after scrolling.
- Preserves static HTML output for GitHub Pages, S3, Azure Blob Storage, or another CDN/object store.
- Preserves the existing backend, iCal, dashboard, booking, guest portal, and Market Intelligence code.
- Includes Database v1.0 under `data-layer/database` as the logically separated data-layer package.

## Not included

- No API behavior changes.
- No authentication changes.
- No payment or outbound email provider integration.
- No chatbot implementation.
