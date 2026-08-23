"""Golden Demo 1 (§50) end to end, plus Golden Demo 4 (§53, fraud risk)."""
from __future__ import annotations

from apps.branchone_api import orchestrator
from apps.branchone_api.store import request_store
from bankai_core.governance.audit import audit_log
from cbs_adapter.mock_cbs import mock_cbs
from workflow.state_machine import WorkflowState


def test_golden_demo_1_mobile_update_end_to_end():
    req = orchestrator.create_request(
        customer_id="CUST-0001",
        text="My phone number has changed.",
        caller_role="CUSTOMER",
        caller_id="CUST-0001",
    )
    assert req.state == WorkflowState.AUTHENTICATION_PENDING
    assert req.maker_required is True
    assert req.checker_required is True
    assert req.policy_rule_id == "POL-CM-CONTACT-MOBILE-001"

    orchestrator.authenticate(req, otp_verified=True, actor="CUST-0001", actor_role="CUSTOMER")
    # The seeded mobile-update policy requires a self-declaration document.
    assert req.state == WorkflowState.DOCUMENT_PENDING

    orchestrator.submit_documents(req, actor="EMP0001", actor_role="EMPLOYEE")
    assert req.state == WorkflowState.MAKER_PENDING

    orchestrator.submit_maker_decision(req, employee_id="EMP0001", proposed_value={"new_mobile": "9123456780"})
    assert req.state == WorkflowState.CHECKER_PENDING

    orchestrator.submit_checker_decision(req, employee_id="EMP0002", approve=True)

    # Checker approval triggers execution internally (per API design, §45).
    assert req.state == WorkflowState.COMPLETED
    assert req.cbs_result.success is True
    assert req.cbs_result.after_state["mobile"] == "9123456780"

    # CBS is genuinely updated, not just the workflow object.
    assert mock_cbs.get_customer_profile("CUST-0001")["mobile"] == "9123456780"

    # Full evidence trail exists for this request.
    events = audit_log.for_subject(req.request_id)
    event_types = {e.event_type for e in events}
    assert "WORKFLOW_TRANSITION" in event_types
    assert "MAKER_CHECKER_DECISION" in event_types
    assert "AUTHORIZATION_TOKEN_ISSUED" in event_types
    assert "TOOL_CALL" in event_types

    assert request_store.get(req.request_id) is req


def test_golden_demo_4_simultaneous_sensitive_changes_raise_fraud_alert():
    """§53 — mobile + email + address changed together, plus a recent
    pattern of mobile changes, is the RED-risk scenario the brief
    describes. `RiskAgent` scores it, `FraudAgent` escalates it into an
    alert — advisory, never a fraud determination — and the workflow stops
    at FRAUD_REVIEW instead of proceeding to maker/checker."""
    from bankai_core.agents.fraud_agent import fraud_agent
    from bankai_core.agents.risk_agent import risk_agent

    risk_result = risk_agent.score(
        changed_fields=["MOBILE", "EMAIL", "ADDRESS"],
        caller_role="SYSTEM",
        caller_id="test",
        recent_mobile_changes_90d=2,
    )
    assert risk_result.risk_class == "RED"

    alert = fraud_agent.evaluate(risk_result, subject_id="BR-TEST-0001")
    assert alert.raised is True
    assert alert.requires_enhanced_review is True

    events = audit_log.for_subject("BR-TEST-0001")
    assert any(e.event_type == "FRAUD_ALERT_RAISED" for e in events)


def test_golden_demo_4_amber_risk_forces_checker_even_when_policy_allows_stp():
    """A service whose baseline policy allows STP (no checker) must still
    gain a checker requirement once risk is elevated to AMBER — §16/§53:
    "AMBER: human verification.\""""
    req = orchestrator.create_request(
        customer_id="CUST-0001",
        text="Please stop my cheque number 000123.",
        caller_role="CUSTOMER",
        caller_id="CUST-0001",
        recent_mobile_changes_90d=2,  # unrelated-looking signal, still elevates risk
        failed_otp_attempts=0,
    )
    assert req.risk_class == "AMBER"
    assert req.checker_required is True  # baseline stop-cheque policy alone would not require this


def test_unclassifiable_request_requires_human_clarification():
    import pytest

    with pytest.raises(orchestrator.HumanClarificationRequired):
        orchestrator.create_request(
            customer_id="CUST-0001",
            text="asdkfjaslkdfj random gibberish text",
            caller_role="CUSTOMER",
            caller_id="CUST-0001",
        )
