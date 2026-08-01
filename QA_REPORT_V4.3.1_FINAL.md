# Arbor Vista Platform v4.3.1 — Final QA Report

**Release:** v4.3.1 — UI Rotation + Direct Booking Restore  
**Status:** PASS  
**Prepared:** July 31, 2026

## Corrections delivered

- Replaced the missing/blank logo with a responsive mountain, pine, **Arbor Vista**, script **Retreat**, and *Smoky Mountain Cabin Escape* lockup.
- Darkened the Cabin hero background across its full width so the white heading and description remain readable.
- Replaced crowded multi-image grids with single-image fade rotators.
- Rotators change every **3 seconds**, hide the previous slide, and display only one slide at a time.
- Homepage signature experiences rotate through three images.
- Cabin sleeping spaces rotate through king suite, queen suite, and open loft.
- Cabin kitchen rotates only the two approved charcoal-kitchen images.
- Restored and emphasized the complete Book Direct workflow.
- Added a direct-booking section on the homepage and a four-step proof bar on the booking page.
- Removed the hard-coded `/ArborVista-Labs/` base from root pages so the package is portable to Labs, production, or the custom domain.

## Direct booking verification

The following flow remains in the package and was exercised in Chromium:

1. Stay details
2. Guest details
3. Rental agreement
4. Review and submit
5. Browser-based confirmation and guest-portal preview

A valid Step 1 request successfully advanced to Step 2 during focused browser QA.

## QA suites

| Suite | Result |
|---|---:|
| v4.3.1 static contract | 14/14 passed |
| v4.3.1 focused browser | 24/24 passed |
| Public website regression | 42/42 passed |
| Database/calendar regression | 33/33 passed |
| Multi-property/platform API | 80/80 passed |

## Preview files

- `QA/screenshots/home-v431-desktop.png`
- `QA/screenshots/home-v431-mobile.png`
- `QA/screenshots/cabin-v431-desktop.png`
- `QA/screenshots/book-direct-v431-desktop.png`

## Important test-release limitation

The booking form works as a browser/local preview. Production email delivery, secure cloud storage, authentication, live pricing, and payments are still pending.
