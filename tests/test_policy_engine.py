"""§12 — Regulatory Digital Twin: drafts are never binding; unknown
services never get a hallucinated answer.
"""
from __future__ import annotations

from bankai_core.agents.policy_agent import policy_agent
from bankai_core.policy.regulatory_twin import RuleStatus, regulatory_twin


def test_draft_rule_is_never_returned_as_binding():
    rule = regulatory_twin.find(service="CONTACT_DETAILS", customer_type="INDIVIDUAL")
    assert rule is not None
    assert rule.status == RuleStatus.FINAL
    assert rule.rule_id != "POL-CM-CONTACT-MOBILE-002-DRAFT"

    all_draft_ids = {r.rule_id for r in regulatory_twin.all_rules() if r.status == RuleStatus.DRAFT}
    assert "POL-CM-CONTACT-MOBILE-002-DRAFT" in all_draft_ids  # exists, but...
    assert rule.rule_id not in all_draft_ids  # ...never what find() returns


def test_unknown_service_returns_confirmation_required_not_a_guess():
    result = policy_agent.retrieve(service="TREASURY_DERIVATIVES", customer_type="COMPANY", caller_id="test")
    assert result.found is False
    assert result.confirmation_required is True
    assert result.rule is None
