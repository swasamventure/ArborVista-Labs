# Arbor Vista Retreat v2.5 — Clean GitHub Pages Package

This package is prepared for the `ArborVista-Labs` GitHub Pages repository.

## Included fixes

- All deployed property images use `.webp`.
- Every HTML image reference was updated to the matching WebP path.
- Inline background images, Open Graph image metadata, and VacationRental schema were updated.
- Space-containing image paths were normalized for safer GitHub Pages deployment.
- Redundant photos were removed, with the gallery focused primarily on the house.
- Bedroom mapping remains:
  - King Suite: 2732PC-30, 31, 32
  - Queen Suite: 2732PC-24, 25, 26
  - Open Loft: 2732PC-34, 35, 37
- Lazy loading remains enabled on gallery/content images.
- `.nojekyll` is included.

## Upload

Upload the contents of this folder to the root of the `ArborVista-Labs` repository. Do not upload the enclosing folder itself.

After GitHub Pages deploys, hard-refresh the browser (Ctrl+F5 on Windows) to clear cached HTML and images.
