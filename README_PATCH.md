# Arbor Vista Retreat v4.3.3 — Final Verified Cleanup + What Guests Say

This overlay patch is built against the current `swasamventure/ArborVista-Labs`
v4.3.3 homepage-redesign baseline.

## Corrections included

- Removes the redundant top utility sentence.
- Removes the temporary hero booking-status sentence.
- Preserves the approved horizontal transparent logo and its scrolled-header visibility.
- Restores a real **What Guests Say** section rather than a link-only review prompt.
- Displays the current Airbnb aggregate rating, review count, category scores,
  review themes, five-star percentage and a short verified featured excerpt.
- Links guests to the complete Airbnb review list.
- Loads the page from `data/airbnb-reviews.json`, so GitHub Pages never makes an
  unreliable browser-to-Airbnb cross-origin request.
- Includes a scheduled/manual GitHub Actions updater that refreshes the local
  Airbnb snapshot from the public listing page.

## Important review-data limitation

Airbnb's server-rendered public listing currently exposes aggregate rating data,
review themes and one featured review excerpt. It does not reliably expose every
individual review to a static GitHub Pages site. This patch therefore does not
invent or paraphrase additional guest quotations.

The supplied workflow refreshes only information available from the public
listing. If Airbnb blocks an update, the workflow fails safely and leaves the
last verified snapshot in place.

## Install

1. Back up the repository.
2. Extract this ZIP over the repository root.
3. Use the included `index.html` replacement, or run:

```bash
python -m pip install beautifulsoup4
python apply_v433_final_cleanup.py /path/to/ArborVista-Labs
```

4. Verify:

```bash
python verify_v433_final_cleanup.py /path/to/ArborVista-Labs
```

5. Commit, deploy and hard-refresh the browser once.

## Automatic review refresh

The included workflow is:

```text
.github/workflows/update-airbnb-reviews.yml
```

It runs weekly and can also be started manually from GitHub Actions. It updates:

```text
data/airbnb-reviews.json
```

The website displays the last verified snapshot even when a later refresh fails.

## Release

The release remains **v4.3.3**. This restores an omitted, previously expected
homepage component and does not reopen the feature roadmap before v4.4.
