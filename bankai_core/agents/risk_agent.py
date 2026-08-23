"""Risk Agent (§16) — advisory only."""
from __future__ import annotations

from dataclasses import dataclass

from bankai_core.agents.base import AdvisoryAgent


@dataclass(frozen=True)
class RiskResult:
    risk_score: int
    risk_class: str  # GREEN | AMBER | RED
    risk_reasons: list[str]


class RiskAgent(AdvisoryAgent):
    agent_id = "RISK_AGENT"

    def score(
        self,
        changed_fields: list[str],
        caller_role: str,
        caller_id: str,
        recent_mobile_changes_90d: int = 0,
        failed_otp_attempts: int = 0,
    ) -> RiskResult:
        result = self._invoke(
            caller_role=caller_role,
            caller_id=caller_id,
            task_type="risk_scoring",
            instructions="Score operational risk of this service request from structured signals only.",
            data={
                "changed_fields": changed_fields,
                "recent_mobile_changes_90d": recent_mobile_changes_90d,
                "failed_otp_attempts": failed_otp_attempts,
            },
            untrusted_keys=(),  # structured/numeric signals only, nothing free-text here
        )
        structured = result.response.structured
        return RiskResult(
            risk_score=structured["risk_score"],
            risk_class=structured["risk_class"],
            risk_reasons=structured["risk_reasons"],
        )


risk_agent = RiskAgent()
