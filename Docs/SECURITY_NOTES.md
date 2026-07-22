# Security Notes — v2.8

- Airbnb and Vrbo iCal URLs should be treated as private credentials because possession of the URL can reveal blocked/reserved dates.
- Never place real feed URLs in public HTML, JavaScript, screenshots, documentation, or a public GitHub repository.
- Never commit a database containing real guest names, email addresses, phone numbers, signatures, or reservation details.
- The current guest portal is a browser-only preview and is not authenticated.
- The current Book Direct form stores test information in browser localStorage; it is not secure production storage.
- Production synchronization should run on a protected backend with secret management, authentication, logging, rate limits, and database access controls.
- Channel-specific exports should be used so Airbnb does not receive Airbnb-origin events back from Arbor Vista, and Vrbo does not receive Vrbo-origin events back from Arbor Vista.
- Public ICS exports should use unguessable protected URLs or authenticated delivery when practical; do not include guest names or contact information in exported events.
