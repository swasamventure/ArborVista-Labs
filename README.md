# Arbor Vista Retreat v2.8 Final QA Build

Upload the contents of this folder to the root of the `ArborVista-Labs` repository only after reviewing the deployment warning in `README_v2.8.md`.

This package contains:

- The complete static Arbor Vista Retreat website
- The hardened Book Direct and guest-preview workflows
- A local SQLite/iCal reservation-engine prototype
- Sample Airbnb and Vrbo fixtures
- Generic and channel-specific outbound ICS examples
- Automated database, website, browser-workflow, accessibility, integrity, and responsive-layout QA

Run:

```bash
python QA/run_all_qa.py
```

Current verified result: **75 of 75 checks PASS**.

The static website is not yet connected to the database. Private feed URLs, live guest data, and the SQLite database must not be published to a public GitHub repository.
