# v4.3.3 Production Deployment Checklist

1. Upload this package to the root of `swasamventure/ArborVista-Retreat`.
2. Confirm GitHub Pages publishes from the intended production branch/root.
3. Confirm the custom domain is `arborvistaretreat.com`.
4. Enable **Enforce HTTPS** in GitHub Pages settings.
5. Verify `http://arborvistaretreat.com` redirects to HTTPS.
6. Verify `/admin/login.html` and `/guest/` return 404.
7. Verify Book Direct does not display a form or collect PII.
8. Verify all availability buttons open the Airbnb listing.
9. Verify Privacy Notice, Website Terms, Gallery, and Rental Agreement pages load.
10. Create the Git tag `v4.3.3` only after production smoke testing passes.
