"""Fraud Agent (§17) — advisory only.

Raises alerts; never declares fraud. A RED risk classification from
`RiskAgent` (e.g. simultaneous mobile+email+address change, §4/Golden Demo
4) is escalated here into a `FraudAlert` that forces the workflow into
`FRAUD_REVIEW` — a human (Fraud/Risk role) makes the actual determination.
"""
from __future__ import annotations

from dataclasses import dataclass

from bankai_core.agents.risk_agent import RiskResult
from bankai_core.governance.audit import audit_log


@dataclass(frozen=True)
class FraudAlert:
    raised: bool
    reasons: list[str]
    requires_enhanced_review: bool


class FraudAgent:
    """Not registered in the AI Gateway model path — this agent reasons over
    another agent's structured output (deterministic escalation logic), it
    does not itself call a model. Still logged to the audit trail like any
    other agent decision.
    """

    agent_id = "FRAUD_AGENT"

    def evaluate(self, risk_result: RiskResult, subject_id: str) -> FraudAlert:
        raised = risk_result.risk_class == "RED"
        alert = FraudAlert(
            raised=raised,
            reasons=risk_result.risk_reasons,
            requires_enhanced_review=raised,
        )
        if raised:
            audit_log.record(
                event_type="FRAUD_ALERT_RAISED",
                actor=self.agent_id,
                actor_type="AGENT",
                action="EVALUATE",
                subject_id=subject_id,
                evidence={"reasons": risk_result.risk_reasons, "risk_score": risk_result.risk_score},
                reason="AI raised an alert; fraud determination requires human Fraud/Risk review",
            )
        return alert


fraud_agent = FraudAgent()
