"""Post-Execution Verification Agent (§26) — advisory only.

Never assumes a CBS API 200/success means the business change actually
happened: compares the CBS adapter's own before/after state against what
was requested and flags a mismatch for escalation rather than closing the
request.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from cbs_adapter.base import CBSResult


@dataclass(frozen=True)
class VerificationResult:
    verified: bool
    mismatch_reason: str | None


class VerificationAgent:
    agent_id = "VERIFICATION_AGENT"

    def verify(self, cbs_result: CBSResult, expected_field: str, expected_value: Any) -> VerificationResult:
        if not cbs_result.success:
            return VerificationResult(False, f"CBS reported failure: {cbs_result.message}")
        actual_value = cbs_result.after_state.get(expected_field)
        if actual_value != expected_value:
            return VerificationResult(
                False,
                f"expected {expected_field}={expected_value!r} but CBS after-state shows {actual_value!r}",
            )
        return VerificationResult(True, None)


verification_agent = VerificationAgent()
