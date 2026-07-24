# Shared Website Template

The shared template contains reusable booking, gallery, guest-portal, availability, SEO and accessibility components. Each property receives its own repository and configuration package so the website can be transferred with the property.

Use:

```bash
python tools/create_property.py "New Cabin Name" TN-03 --domain example.com
```

The management platform remains separate from the public property repository.


The shared template must never hard-code a property ID, domain, guest name, or calendar token.
