"""Maker-Checker Engine (§20) and CBS write authorization (§7/§23).

`issue_authorization_token()` is the only function in the codebase that
constructs a `bankai_core.tools.gateway.AuthorizationToken`. It builds the
token's `checks` dict entirely by reading `ServiceRequest` fields that were
themselves only ever set by trusted code in this module and
`workflow/state_machine.py` — never by parsing an agent/model response. This
is the concrete mechanism behind §57's "Critical Security Test": there is no
prompt that can make this function return a fully-passed token, because the
token reflects database state, not instructions.
"""
from __future__ import annotations

from bankai_core.governance.audit import audit_log
from bankai_core.tools.gateway import AuthorizationToken
from workflow.state_machine import Decision, ServiceRequest, WorkflowState, transition


class SegregationOfDutyViolation(RuntimeError):
    pass


class MakerCheckerError(RuntimeError):
    pass


def record_maker_decision(
    request: ServiceRequest,
    employee_id: str,
    proposed_value: dict,
    reason: str | None = None,
) -> None:
    if request.state != WorkflowState.MAKER_PENDING:
        raise MakerCheckerError(f"request {request.request_id} is not awaiting a maker decision (state={request.state})")

    request.proposed_value = proposed_value
    request.maker_decision = Decision(
        employee_id=employee_id,
        role="BRANCH_MAKER",
        action="PROPOSE_CHANGE",
        decision="APPROVED",
        requested_value=str(proposed_value),
        reason=reason,
    )
    audit_log.record(
        event_type="MAKER_CHECKER_DECISION",
        actor=employee_id,
        actor_type="EMPLOYEE",
        subject_id=request.request_id,
        action="MAKER_SUBMIT",
        requested_value=str(proposed_value),
        reason=reason,
    )
    next_state = WorkflowState.CHECKER_PENDING if request.checker_required else WorkflowState.APPROVAL_PENDING
    transition(request, next_state, actor=employee_id, actor_type="EMPLOYEE", reason="maker submitted proposed change")


def record_checker_decision(
    request: ServiceRequest,
    employee_id: str,
    approve: bool,
    reason: str | None = None,
) -> None:
    if request.state != WorkflowState.CHECKER_PENDING:
        raise MakerCheckerError(f"request {request.request_id} is not awaiting a checker decision (state={request.state})")
    if request.maker_decision is None:
        raise MakerCheckerError("no maker decision recorded; cannot checker-approve")
    if employee_id == request.maker_decision.employee_id:
        audit_log.record(
            event_type="SEGREGATION_OF_DUTY_VIOLATION",
            actor=employee_id,
            actor_type="EMPLOYEE",
            subject_id=request.request_id,
            action="CHECKER_DECISION_DENIED",
            reason="checker cannot be the same employee as the maker",
        )
        raise SegregationOfDutyViolation(
            f"employee {employee_id} was the maker on {request.request_id} and cannot also be the checker"
        )

    decision_value = "APPROVED" if approve else "REJECTED"
    request.checker_decision = Decision(
        employee_id=employee_id,
        role="BRANCH_CHECKER",
        action="REVIEW_CHANGE",
        decision=decision_value,
        previous_value=str(request.maker_decision.requested_value),
        reason=reason,
    )
    audit_log.record(
        event_type="MAKER_CHECKER_DECISION",
        actor=employee_id,
        actor_type="EMPLOYEE",
        subject_id=request.request_id,
        action="CHECKER_DECISION",
        decision=decision_value,
        reason=reason,
    )
    if approve:
        transition(request, WorkflowState.CBS_PENDING, actor=employee_id, actor_type="EMPLOYEE", reason="checker approved")
    else:
        transition(request, WorkflowState.REJECTED, actor=employee_id, actor_type="EMPLOYEE", reason=reason or "checker rejected")


def issue_authorization_token(request: ServiceRequest, tool_id: str) -> AuthorizationToken:
    """Build the (single-use) authorization for one CBS write.

    Every check here reads `ServiceRequest` state — nothing is taken from a
    function argument the caller could spoof with a favorable value.
    """
    checker_ok = (not request.checker_required) or (
        request.checker_decision is not None and request.checker_decision.decision == "APPROVED"
    )
    segregation_ok = (
        request.maker_decision is not None
        and (
            not request.checker_required
            or (request.checker_decision is not None and request.checker_decision.employee_id != request.maker_decision.employee_id)
        )
    )
    checks = {
        "authentication_passed": request.authentication_status == "PASSED",
        "policy_validation_passed": request.policy_validation_status == "PASSED",
        "documents_passed_or_not_required": request.documents_status in ("PASSED", "NOT_REQUIRED"),
        "risk_control_passed": request.risk_status == "PASSED",
        "maker_approved": request.maker_decision is not None and request.maker_decision.decision == "APPROVED",
        "checker_approved_or_not_required": checker_ok,
        "segregation_of_duty": segregation_ok,
        "state_is_cbs_pending": request.state == WorkflowState.CBS_PENDING,
    }
    token = AuthorizationToken(
        request_id=request.request_id,
        tool_id=tool_id,
        idempotency_key=request.idempotency_key,
        checks=checks,
    )
    audit_log.record(
        event_type="AUTHORIZATION_TOKEN_ISSUED",
        actor="WORKFLOW_ENGINE",
        actor_type="SYSTEM",
        subject_id=request.request_id,
        action=f"ISSUE:{tool_id}",
        evidence=checks,
        decision="ALL_CHECKS_PASSED" if all(checks.values()) else "SOME_CHECKS_FAILED",
    )
    return token
