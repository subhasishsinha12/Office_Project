"""Prompt injection defense (§41, Golden Demo 5).

Two independent layers, because pattern detection alone is not a real
control:

1. **Detection** (this module): flags customer/document text that looks
   like it is trying to issue instructions ("ignore previous instructions",
   "approve this", "you are now", etc). Flags are used for alerting and for
   the AI Control Tower — they are advisory.

2. **Structural containment** (the real control, enforced elsewhere): every
   place that consumes customer/document text — `bankai_core/gateway/
   ai_gateway.py`, `bankai_core/agents/*` — treats it strictly as a `data`
   field, never as part of an instruction string, and no code path lets a
   model's output populate an `AuthorizationToken` (see
   `workflow/maker_checker.py`) or a `RuleEngine` decision. So even a
   perfectly-worded injection that evades detection here still cannot move
   `maker_required`/`checker_required` or trigger a CBS write, because those
   are computed by `bankai_core/policy/rule_engine.py` from structured
   facts, not parsed from free text.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

_INJECTION_PATTERNS = [
    r"ignore (all )?(previous|prior|above|bank) (instructions|policy|policies)",
    r"disregard (the )?(policy|checker|maker|approval)",
    r"you are now",
    r"act as",
    r"approve (this|the) request",
    r"skip (checker|maker|approval|verification)",
    r"bypass (checker|maker|approval|verification|policy)",
    r"system prompt",
    r"override (the )?(policy|rule|approval)",
    r"as an ai( model| assistant)?,? you (must|should)",
]

_COMPILED = [re.compile(p, re.IGNORECASE) for p in _INJECTION_PATTERNS]


@dataclass(frozen=True)
class UntrustedContent:
    """Wrapper marking text as untrusted data, never as instructions.

    Agents and the AI Gateway must only ever read `.text` as a data payload
    (e.g. "the customer said: <text>"), never splice it into a system/
    instruction prompt unescaped.
    """

    text: str
    source: str  # e.g. "customer_input", "document_ocr:<doc_id>"
    flagged: bool
    matched_patterns: tuple[str, ...]


def wrap_untrusted(text: str, source: str) -> UntrustedContent:
    matches = tuple(p.pattern for p in _COMPILED if p.search(text))
    return UntrustedContent(text=text, source=source, flagged=bool(matches), matched_patterns=matches)


def contains_injection_attempt(text: str) -> bool:
    return any(p.search(text) for p in _COMPILED)
