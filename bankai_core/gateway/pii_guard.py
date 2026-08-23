"""PII masking / DLP layer, applied before any text reaches a ModelProvider.

Pattern-based masking for the identifiers most common in Indian banking
service requests: PAN, Aadhaar, mobile numbers, email, and account numbers.
This is intentionally conservative (over-masks rather than under-masks) —
false positives cost readability, false negatives leak PII to a model.
"""
from __future__ import annotations

import re

_PATTERNS: dict[str, re.Pattern] = {
    "PAN": re.compile(r"\b[A-Z]{5}[0-9]{4}[A-Z]\b"),
    "AADHAAR": re.compile(r"\b\d{4}\s?\d{4}\s?\d{4}\b"),
    "MOBILE": re.compile(r"\b(?:\+?91[\s-]?)?[6-9]\d{9}\b"),
    "EMAIL": re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b"),
    "ACCOUNT_NUMBER": re.compile(r"\b\d{9,18}\b"),
}


def mask_pii(text: str) -> tuple[str, dict[str, int]]:
    """Returns (masked_text, counts_by_type)."""
    masked = text
    counts: dict[str, int] = {}
    for label, pattern in _PATTERNS.items():
        matches = pattern.findall(masked)
        if matches:
            counts[label] = len(matches)
            masked = pattern.sub(f"[MASKED_{label}]", masked)
    return masked, counts
