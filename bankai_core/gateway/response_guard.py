"""Response guard — defense in depth on the way out of the model.

The real control against a model output driving a CBS write is that the
workflow/tool layer never reads authorization fields from a model response
(see `workflow/maker_checker.py`). This guard exists to *detect and log*
an agent output that nonetheless looks like it's trying to assert one, so
AI Governance can see attempted-abuse patterns on the AI Control Tower —
it is a signal, not the control.
"""
from __future__ import annotations

_SUSPICIOUS_KEYS = {"approved", "checker_approved", "maker_approved", "skip_checker", "authorized", "bypass"}


def scan_response(structured: dict) -> list[str]:
    return [k for k in structured.keys() if k.lower() in _SUSPICIOUS_KEYS]
