# v2.8 Final QA Changelog

## Website fixes

- Removed the hard-coded six-guest rejection. The request form now accepts groups of seven or eight for host review when sofa-bed availability is confirmed.
- Added a configurable eight-guest request ceiling and retained the standard six-guest sleeping description until the sofa-bed setup is active.
- Added mobile-phone validation.
- Required the electronic signature to match the guest legal name.
- Restricted the agreement date to the current local date.
- Corrected checkout minimum after draft restoration.
- Corrected Start Over so it removes the draft instead of immediately saving an empty replacement.
- Displayed all missing required-field errors on a step.
- Removed unsafe `innerHTML` rendering of guest-provided values.
- Added safe handling for corrupted guest-preview browser data.
- Added accessible labels and saved consent to the gate-pass demo.
- Added `aria-expanded` handling to the mobile menu.
- Updated cache-busting references to v2.8.1.

## Calendar/database fixes

- Added strict ISO-date constraints.
- Added transaction locking and recheck for concurrent direct-booking attempts.
- Added explicit cancellation and missing-event reconciliation.
- Added failed-sync recording.
- Added update reconciliation and duplicate-UID rejection.
- Added owner-block creation and conflict rejection.
- Added database health reporting.
- Added channel-specific outbound calendars that exclude the destination channel's own reservations.
- Added ICS publish headers, CRLF output, escaping, and line folding.
- Added optional HTTPS feed download support for controlled future testing.

## QA

- 33 database/iCal automated checks
- 42 website/workflow automated checks
- 75 combined checks
- Desktop and mobile overflow testing
- Browser workflow testing
- Static link, metadata, accessibility, image-decoding, syntax, and integrity checks
