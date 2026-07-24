# Arbor Vista Platform v4.1 — Features 1–7 Implemented

## 1. Multi-property database design
Organizations, users, organization memberships, properties, domains, property memberships, settings, reservations, guests, booking requests, documents, calendar sources, owner blocks, sync history, reporting snapshots, share tokens, exports, and audit logs are property-scoped.

## 2. Central dashboard
The dashboard includes portfolio/property selection, reservations, combined calendar, calendar sources, sync logs, reports, cleaning calendar, and property transfer export.

## 3. Reservation engine
Direct booking requests, occupancy validation, date conflict prevention, approval/decline/cancellation, agreement records, and audit logging are implemented in the local reference API.

## 4. Calendar engine
Airbnb/Vrbo iCal import logic, owner blocks, combined calendar, channel-specific outbound availability feeds, sync logs, and a token-protected portfolio cleaning feed are included. The cleaning feed contains property name/code/ID, arrival/departure time, guest count, source, reservation reference, and turnover information. It does not contain guest names or contact details.

## 5. Authentication and permissions
Local development uses explicit demo users and role checks. Supabase migrations define the production authentication/RLS target. This is not a live production login system until Supabase is deployed and configured.

## 6. Reporting
Portfolio and property reporting includes reservation count, occupied nights, arrivals, departures, guest nights, source mix, occupancy percentage, and recorded gross revenue.

## 7. Property transfer package
A property-specific export includes configuration, future reservations with guest names redacted by default, calendar-source metadata without feed secrets, owner blocks, a transfer manifest, and privacy notes. Other properties and shared-platform credentials are excluded.

## Exclusions
Stripe/payment processing and outbound email delivery remain excluded.
