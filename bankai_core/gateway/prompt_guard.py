"""Builds the structured payload sent to a model, tagging untrusted fields.

This is the "structural containment" half of prompt injection defense
described in `bankai_core/guardrails/injection_defense.py`: untrusted text
is wrapped and flagged, but always passed as a `data` field — never
appended to `instructions` — so even a flagged, unmitigated injection
attempt has nothing to inject into.
"""
from __future__ import annotations

from typing import Any

from bankai_core.guardrails.injection_defense import UntrustedContent, wrap_untrusted
from bankai_core.models.base import PromptPayload


def build_payload(
    task_type: str,
    instructions: str,
    data: dict[str, Any],
    context: dict[str, Any] | None = None,
    untrusted_keys: tuple[str, ...] = ("text",),
) -> tuple[PromptPayload, list[UntrustedContent]]:
    flags: list[UntrustedContent] = []
    safe_data = dict(data)
    for key in untrusted_keys:
        if key in safe_data and isinstance(safe_data[key], str):
            wrapped = wrap_untrusted(safe_data[key], source=f"data.{key}")
            flags.append(wrapped)
            # Content itself is left intact for the classifier to read as
            # data; only the flag is used for detection/alerting.
    payload = PromptPayload(task_type=task_type, instructions=instructions, data=safe_data, context=context or {})
    return payload, flags
