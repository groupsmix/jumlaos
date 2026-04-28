"""Thin typed adapters around third-party SDKs (WhatsApp Cloud API, SMS, ...).

Each adapter exposes the minimal surface the rest of the codebase needs and
isolates ``Any``-typed third-party shapes from the typed core.
"""
