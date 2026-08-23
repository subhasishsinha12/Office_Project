"""Registers every agent implementation into the Agent Registry (§7).

`bankai_core.agents.base.AgentRuntime`/`AIGateway.invoke()` refuses to run
any agent_id that isn't registered here. Call `register_all_agents()` once
at application startup (see `apps/branchone_api/main.py`).
"""
from __future__ import annotations

from bankai_core.agents.registry import AgentClass, AgentRegistryEntry, agent_registry

_REGISTERED = False


def register_all_agents() -> None:
    global _REGISTERED
    if _REGISTERED:
        return

    agent_registry.register(
        AgentRegistryEntry(
            agent_id="INTENT_AGENT",
            agent_name="Intent Agent",
            purpose="Interpret customer/employee free-text requests into the canonical banking taxonomy.",
            agent_class=AgentClass.ADVISORY,
            business_owner="Branch Operations",
            technical_owner="GenAI Engineering",
            version="0.1.0",
            risk_level="LOW",
            models_allowed=["bankai-tier1-rules"],
            data_allowed=["MASKED_PII"],
            applicable_policies=["POL-CM-CONTACT-MOBILE-001"],
        )
    )
    agent_registry.register(
        AgentRegistryEntry(
            agent_id="DECOMPOSITION_AGENT",
            agent_name="Complex Request Decomposition Agent",
            purpose="Propose a parent/child request graph for compound service requests.",
            agent_class=AgentClass.ADVISORY,
            business_owner="Branch Operations",
            technical_owner="GenAI Engineering",
            version="0.1.0",
            risk_level="MEDIUM",
            models_allowed=["bankai-tier3-llm-mock"],
            data_allowed=["MASKED_PII"],
        )
    )
    agent_registry.register(
        AgentRegistryEntry(
            agent_id="DOCUMENT_AGENT",
            agent_name="Document Agent",
            purpose="Classify and extract fields from uploaded/scanned documents.",
            agent_class=AgentClass.ADVISORY,
            business_owner="Branch Operations",
            technical_owner="Multimodal AI Engineering",
            version="0.1.0",
            risk_level="MEDIUM",
            models_allowed=["bankai-tier2-slm-mock"],
            data_allowed=["MASKED_PII", "DOCUMENT_TEXT"],
        )
    )
    agent_registry.register(
        AgentRegistryEntry(
            agent_id="RISK_AGENT",
            agent_name="Risk Agent",
            purpose="Score operational/fraud-adjacent risk from structured signals.",
            agent_class=AgentClass.ADVISORY,
            business_owner="Risk",
            technical_owner="GenAI Engineering",
            version="0.1.0",
            risk_level="MEDIUM",
            models_allowed=["bankai-tier1-rules"],
            data_allowed=["INTERNAL"],
        )
    )
    agent_registry.register(
        AgentRegistryEntry(
            agent_id="POLICY_AGENT",
            agent_name="Policy Agent",
            purpose="Retrieve applicable, FINAL, effective rules from the Regulatory Digital Twin.",
            agent_class=AgentClass.ADVISORY,
            business_owner="Compliance",
            technical_owner="GenAI Engineering",
            version="0.1.0",
            risk_level="HIGH",
            models_allowed=[],  # deterministic DB lookup only, no model call
            data_allowed=["POLICY"],
        )
    )
    agent_registry.register(
        AgentRegistryEntry(
            agent_id="FRAUD_AGENT",
            agent_name="Fraud Agent",
            purpose="Escalate RED risk classifications into fraud-review alerts.",
            agent_class=AgentClass.ADVISORY,
            business_owner="Fraud Risk",
            technical_owner="GenAI Engineering",
            version="0.1.0",
            risk_level="HIGH",
            models_allowed=[],
            data_allowed=["INTERNAL"],
        )
    )
    agent_registry.register(
        AgentRegistryEntry(
            agent_id="NOTIFICATION_AGENT",
            agent_name="Notification Agent",
            purpose="Notify the customer of request status changes.",
            agent_class=AgentClass.TRANSACTIONAL,
            business_owner="Branch Operations",
            technical_owner="Full-Stack Engineering",
            version="0.1.0",
            risk_level="LOW",
            models_allowed=[],
            data_allowed=["MASKED_PII"],
            tools_allowed=["send_notification"],
            write_permissions=["notify_customer"],
            approval_required=False,
            maximum_authority="NOTIFY_ONLY",
        )
    )
    agent_registry.register(
        AgentRegistryEntry(
            agent_id="CBS_ACTION_AGENT",
            agent_name="CBS Action Agent",
            purpose="Request execution of an approved CBS write via the Tool Gateway.",
            agent_class=AgentClass.TRANSACTIONAL,
            business_owner="Branch Operations",
            technical_owner="Core Banking Integration",
            version="0.1.0",
            risk_level="HIGH",
            models_allowed=[],
            data_allowed=["INTERNAL"],
            tools_allowed=["update_mobile", "update_address", "stop_cheque"],
            write_permissions=["cbs_write"],
            approval_required=True,
            maximum_authority="CBS_WRITE_VIA_TOOL_GATEWAY_ONLY",
        )
    )

    _REGISTERED = True
