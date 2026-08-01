# Arbor Vista Platform v4.3.1 — UI Rotation + Direct Booking Restore

This corrective test release keeps the v4.3 premium visual direction while fixing the issues identified during review.

## Corrections

- Replaced the blank/broken PNG header logo with a responsive HTML/SVG Arbor Vista lockup inspired by the supplied left-side logo.
- Darkened the entire Cabin hero background so white text is readable.
- Replaced multi-image grids with one visible image per area and automatic 3-second fade rotation.
- Homepage signature experiences rotate through three images.
- Cabin sleeping spaces rotate through king suite, queen suite, and open loft.
- Cabin kitchen rotates between the two approved charcoal-kitchen images.
- Restored and emphasized the full four-step Book Direct flow.
- Added a Book Direct section to the homepage and a booking-step proof bar on the booking page.
- Removed the hard-coded `/ArborVista-Labs/` base from root pages so the same package works in Labs, the production repository, or `arborvistaretreat.com`.

## Direct booking flow preserved

1. Stay details
2. Guest details
3. Rental agreement
4. Review and submit
5. Browser-based confirmation and guest portal preview

No production payment or email is connected in this test release.
