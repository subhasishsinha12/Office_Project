"""Workflow State Machine (§19).

`ServiceRequest.state` may only be changed via `transition()`, which (a)
checks the move is in `ALLOWED_TRANSITIONS`, and (b) appends an
`AUDIT_EVENT` — there is no other code path that assigns to `.state`
directly, anywhere in this codebase (including inside agents).
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional

from bankai_core.governance.audit import audit_log


class WorkflowState(str, Enum):
    DRAFT = "DRAFT"
    SUBMITTED = "SUBMITTED"
    AUTHENTICATION_PENDING = "AUTHENTICATION_PENDING"
    DOCUMENT_PENDING = "DOCUMENT_PENDING"
    DOCUMENT_VERIFICATION = "DOCUMENT_VERIFICATION"
    POLICY_VALIDATION = "POLICY_VALIDATION"
    RISK_REVIEW = "RISK_REVIEW"
    MAKER_PENDING = "MAKER_PENDING"
    CHECKER_PENDING = "CHECKER_PENDING"
    APPROVAL_PENDING = "APPROVAL_PENDING"
    CBS_PENDING = "CBS_PENDING"
    CBS_SUCCESS = "CBS_SUCCESS"
    POST_VERIFICATION = "POST_VERIFICATION"
    COMPLETED = "COMPLETED"
    # exception states
    QUERY_RAISED = "QUERY_RAISED"
    CUSTOMER_ACTION_PENDING = "CUSTOMER_ACTION_PENDING"
    POLICY_CONFLICT = "POLICY_CONFLICT"
    FRAUD_REVIEW = "FRAUD_REVIEW"
    LEGAL_REVIEW = "LEGAL_REVIEW"
    ESCALATED = "ESCALATED"
    REJECTED = "REJECTED"
    CBS_FAILED = "CBS_FAILED"
    CANCELLED = "CANCELLED"


_HAPPY_PATH = [
    WorkflowState.DRAFT,
    WorkflowState.SUBMITTED,
    WorkflowState.AUTHENTICATION_PENDING,
    WorkflowState.DOCUMENT_PENDING,
    WorkflowState.DOCUMENT_VERIFICATION,
    WorkflowState.POLICY_VALIDATION,
    WorkflowState.RISK_REVIEW,
    WorkflowState.MAKER_PENDING,
    WorkflowState.CHECKER_PENDING,
    WorkflowState.APPROVAL_PENDING,
    WorkflowState.CBS_PENDING,
    WorkflowState.CBS_SUCCESS,
    WorkflowState.POST_VERIFICATION,
    WorkflowState.COMPLETED,
]

_EXCEPTION_STATES = {
    WorkflowState.QUERY_RAISED,
    WorkflowState.CUSTOMER_ACTION_PENDING,
    WorkflowState.POLICY_CONFLICT,
    WorkflowState.FRAUD_REVIEW,
    WorkflowState.LEGAL_REVIEW,
    WorkflowState.ESCALATED,
    WorkflowState.REJECTED,
    WorkflowState.CBS_FAILED,
    WorkflowState.CANCELLED,
}

# Forward happy-path transitions, allowing steps to be skipped (e.g. no
# documents required) but never allowing a *backward* jump, and allowing
# any non-terminal state to move into an exception state.
ALLOWED_TRANSITIONS: dict[WorkflowState, set[WorkflowState]] = {}
for i, state in enumerate(_HAPPY_PATH[:-1]):
    ALLOWED_TRANSITIONS[state] = set(_HAPPY_PATH[i + 1 :]) | _EXCEPTION_STATES
ALLOWED_TRANSITIONS[WorkflowState.COMPLETED] = set()
for exc_state in _EXCEPTION_STATES:
    # From an exception state, a human can resume onto the happy path
    # (re-review) or move to a terminal exception state.
    ALLOWED_TRANSITIONS[exc_state] = set(_HAPPY_PATH) | _EXCEPTION_STATES - {exc_state}


class IllegalTransition(RuntimeError):
    pass


@dataclass
class Decision:
    employee_id: str
    role: str
    action: str
    decision: str  # APPROVED | REJECTED
    previous_value: Optional[str] = None
    requested_value: Optional[str] = None
    reason: Optional[str] = None
    evidence: Optional[dict] = None
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@dataclass
class ServiceRequest:
    request_id: str
    customer_id: str
    customer_type: str
    service: str
    subservice: str
    intent_code: str
    channel: str = "BRANCH"
    state: WorkflowState = WorkflowState.DRAFT
    maker_required: bool = True
    checker_required: bool = True
    authentication_status: str = "PENDING"  # PENDING | PASSED | FAILED
    documents_status: str = "NOT_REQUIRED"  # NOT_REQUIRED | PENDING | PASSED
    policy_validation_status: str = "PENDING"  # PENDING | PASSED | FAILED
    risk_status: str = "PENDING"  # PENDING | PASSED
    risk_class: str = "GREEN"
    policy_rule_id: Optional[str] = None
    proposed_value: dict[str, Any] = field(default_factory=dict)
    idempotency_key: str = field(default_factory=lambda: str(uuid.uuid4()))
    maker_decision: Optional[Decision] = None
    checker_decision: Optional[Decision] = None
    cbs_result: Optional[Any] = None

    def __post_init__(self) -> None:
        audit_log.record(
            event_type="WORKFLOW_TRANSITION",
            actor="SYSTEM",
            actor_type="SYSTEM",
            subject_id=self.request_id,
            action="CREATE",
            requested_value=self.state.value,
        )


def transition(request: ServiceRequest, new_state: WorkflowState, actor: str, actor_type: str, reason: str | None = None) -> None:
    allowed = ALLOWED_TRANSITIONS.get(request.state, set())
    if new_state not in allowed and new_state != request.state:
        raise IllegalTransition(f"cannot move request {request.request_id} from {request.state} to {new_state}")
    previous = request.state
    request.state = new_state
    audit_log.record(
        event_type="WORKFLOW_TRANSITION",
        actor=actor,
        actor_type=actor_type,
        subject_id=request.request_id,
        action="TRANSITION",
        previous_value=previous.value,
        requested_value=new_state.value,
        reason=reason,
    )


def new_request_id() -> str:
    return f"BR-{datetime.now(timezone.utc).year}-{uuid.uuid4().hex[:8].upper()}"
