# Arbor Vista Retreat v4.3.3 — Final Visual Cleanup Patch

Overlay this patch on the current **v4.3.3 Homepage Redesign** build.

## Approved changes

1. Removes the top utility sentence:
   `Escape. Unwind. Reconnect. Your mountain retreat awaits.`
2. Removes the temporary hero note:
   `Direct booking coming in v4.4 · Current reservations are securely completed on Airbnb.`
3. Uses the exact user-approved horizontal transparent logo.
4. Keeps the logo background transparent.
5. Uses a warm-cream sticky/scrolled navigation background matching the page.
6. Adds shape-only shadow/glow at the top of the hero so the logo remains readable.
7. Reduces the current redesigned logo dimensions by 20%.
8. Applies the same header-logo visibility treatment across all public pages.
9. Keeps the release version/tag at **v4.3.3** and adds no new features.

## Files

- `assets/v43.js` — replace the existing shared file.
- `assets/v433-final-cleanup.css` — new shared cleanup stylesheet.
- `assets/arbor-vista-logo-horizontal-final-v433.png` — approved PNG master.
- `assets/arbor-vista-logo-horizontal-final-v433.webp` — optimized WebP master.

The CSS embeds the approved optimized logo so the result does not depend on stale image-cache paths.

After deployment, perform a hard refresh once to bypass the older cached `v43.js?v=4.3.3`.
