"""§20 — Maker-Checker segregation of duty."""
from __future__ import annotations

import pytest

from workflow.maker_checker import (
    MakerCheckerError,
    SegregationOfDutyViolation,
    record_checker_decision,
    record_maker_decision,
)
from workflow.state_machine import ServiceRequest, WorkflowState, new_request_id, transition


def _request_at_maker_pending() -> ServiceRequest:
    req = ServiceRequest(
        request_id=new_request_id(),
        customer_id="CUST-0001",
        customer_type="INDIVIDUAL",
        service="CONTACT_DETAILS",
        subservice="MOBILE",
        intent_code="CM_CONTACT_MOBILE_MOD",
    )
    transition(req, WorkflowState.AUTHENTICATION_PENDING, "SYSTEM", "SYSTEM")
    transition(req, WorkflowState.MAKER_PENDING, "SYSTEM", "SYSTEM")
    return req


def test_same_employee_cannot_be_maker_and_checker():
    req = _request_at_maker_pending()
    record_maker_decision(req, employee_id="EMP0001", proposed_value={"new_mobile": "9999999999"})
    assert req.state == WorkflowState.CHECKER_PENDING

    with pytest.raises(SegregationOfDutyViolation):
        record_checker_decision(req, employee_id="EMP0001", approve=True)

    # State must not have moved — the illegal attempt is rejected, not
    # silently accepted with a warning.
    assert req.state == WorkflowState.CHECKER_PENDING


def test_checker_cannot_act_before_maker():
    req = _request_at_maker_pending()
    with pytest.raises(MakerCheckerError):
        record_checker_decision(req, employee_id="EMP0002", approve=True)


def test_checker_rejection_moves_to_rejected_state():
    req = _request_at_maker_pending()
    record_maker_decision(req, employee_id="EMP0001", proposed_value={"new_mobile": "9999999999"})
    record_checker_decision(req, employee_id="EMP0002", approve=False, reason="mismatch with signature card")
    assert req.state == WorkflowState.REJECTED
