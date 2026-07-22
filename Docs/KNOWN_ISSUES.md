# Known Limitations — v2.8

1. The GitHub Pages website is static and does not call the reservation database.
2. The Book Direct submission is saved only in the current browser for preview testing.
3. The included SQLite database and ICS exports contain sample data, not live reservations.
4. Real Airbnb and Vrbo feed URLs have not been tested in this package.
5. `sync-url` is manual; there is no hourly scheduler, retry policy, alerting, or secret manager.
6. Guest portal URLs are browser previews, not authenticated server-side portals.
7. Email delivery, payments, refunds, pricing, taxes, cleaning, and maintenance are outside v2.8.
8. The parser supports the all-day reservation events expected from channel feeds; recurrence rules and general-purpose calendar features are not implemented.
9. Channel calendar refresh timing is controlled by Airbnb/Vrbo and must be measured during live testing.
