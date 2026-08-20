"""Slug helper.

Lived in `makes/service.py` originally, but vehicle models, garages and the
service catalog all need it, so it moved here rather than being imported
across domains.
"""

import re


def generate_slug(value: str) -> str:
    value = value.strip().lower()

    value = re.sub(
        r"[^a-z0-9]+",
        "-",
        value,
    )

    return value.strip("-")
