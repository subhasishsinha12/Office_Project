"""Policy Agent (§11) — advisory only.

Retrieves from `regulatory_twin` only. It has no free-text generation path
for policy content — there is no code here that could hallucinate a
circular. If nothing matches, it returns `POLICY_CONFIRMATION_REQUIRED`.
Because retrieval is a pure, deterministic database lookup (not a model
call), this agent does not route through `AIGateway`/`ModelProvider` — but
every retrieval is still written to the audit trail like any other agent
action, satisfying the same accountability requirement.
"""
from __future__ import annotations

from dataclasses import dataclass

from bankai_core.governance.audit import audit_log
from bankai_core.policy.regulatory_twin import RegulatoryRule, regulatory_twin


@dataclass(frozen=True)
class PolicyLookupResult:
    found: bool
    rule: RegulatoryRule | None
    confirmation_required: bool


class PolicyAgent:
    agent_id = "POLICY_AGENT"

    def retrieve(self, service: str, customer_type: str, caller_id: str) -> PolicyLookupResult:
        rule = regulatory_twin.find(service=service, customer_type=customer_type)
        audit_log.record(
            event_type="POLICY_RETRIEVAL",
            actor=self.agent_id,
            actor_type="AGENT",
            action=f"RETRIEVE:{service}:{customer_type}",
            evidence={"rule_id": rule.rule_id if rule else None},
            reason="POLICY_CONFIRMATION_REQUIRED" if rule is None else "matched FINAL, effective rule",
        )
        return PolicyLookupResult(found=rule is not None, rule=rule, confirmation_required=rule is None)


policy_agent = PolicyAgent()
