"""BranchOne request orchestrator.

This is the only place that sequences agents + rule engine + workflow +
tool gateway for a service request. It contains no policy logic of its own
(that lives in `bankai_core.policy.rule_engine`) and never calls
`cbs_adapter` directly — every CBS interaction goes through
`bankai_core.tools.gateway.tool_gateway`, matching the trust-boundary
diagram in `docs/ARCHITECTURE.md` §2.
"""
from __future__ import annotations

from bankai_core.agents.fraud_agent import fraud_agent
from bankai_core.agents.intent_agent import intent_agent
from bankai_core.agents.policy_agent import policy_agent
from bankai_core.agents.risk_agent import risk_agent
from bankai_core.agents.verification_agent import verification_agent
from bankai_core.policy.rule_engine import Facts, rule_engine
from bankai_core.tools.gateway import tool_gateway
from apps.branchone_api.store import request_store
from workflow.maker_checker import issue_authorization_token, record_checker_decision, record_maker_decision
from workflow.state_machine import ServiceRequest, WorkflowState, new_request_id, transition

_TOOL_BY_SUBSERVICE = {"MOBILE": "update_mobile", "ADDRESS": "update_address"}
_FIELD_BY_SUBSERVICE = {"MOBILE": "mobile", "ADDRESS": "address"}
_PROPOSED_KEY_BY_SUBSERVICE = {"MOBILE": "new_mobile", "ADDRESS": "new_address"}


class OrchestratorError(RuntimeError):
    pass


class HumanClarificationRequired(OrchestratorError):
    def __init__(self, text: str, confidence: float) -> None:
        super().__init__(f"could not confidently classify request (confidence={confidence:.2f}): {text!r}")
        self.confidence = confidence


class UnsupportedService(OrchestratorError):
    pass


def create_request(
    customer_id: str,
    text: str,
    caller_role: str,
    caller_id: str,
    channel: str = "BRANCH",
    recent_mobile_changes_90d: int = 0,
    failed_otp_attempts: int = 0,
) -> ServiceRequest:
    intent = intent_agent.classify(text, caller_role=caller_role, caller_id=caller_id)
    if intent.human_clarification_required:
        raise HumanClarificationRequired(text, intent.confidence)

    profile = tool_gateway.call(
        "get_customer_profile",
        calling_agent_id="CBS_ACTION_AGENT",
        caller_role="SYSTEM",
        caller_id=caller_id,
        customer_id=customer_id,
    )
    customer_type = profile.get("customer_type", "INDIVIDUAL")

    policy_result = policy_agent.retrieve(service=intent.service, customer_type=customer_type, caller_id=caller_id)

    risk_result = risk_agent.score(
        changed_fields=[intent.subservice],
        caller_role=caller_role,
        caller_id=caller_id,
        recent_mobile_changes_90d=recent_mobile_changes_90d,
        failed_otp_attempts=failed_otp_attempts,
    )

    facts = Facts(customer_type=customer_type, service=intent.service, subservice=intent.subservice, risk_class=risk_result.risk_class)
    rule_outcome = rule_engine.evaluate(facts, policy_result.rule)

    request = ServiceRequest(
        request_id=new_request_id(),
        customer_id=customer_id,
        customer_type=customer_type,
        service=intent.service,
        subservice=intent.subservice,
        intent_code=intent.intent_code,
        channel=channel,
        maker_required=rule_outcome.maker_required,
        checker_required=rule_outcome.checker_required,
        risk_class=risk_result.risk_class,
        policy_rule_id=policy_result.rule.rule_id if policy_result.rule else None,
    )
    request_store.save(request)

    fraud_alert = fraud_agent.evaluate(risk_result, subject_id=request.request_id)

    transition(request, WorkflowState.SUBMITTED, actor=caller_id, actor_type=caller_role, reason="request submitted")

    if policy_result.confirmation_required:
        transition(
            request,
            WorkflowState.ESCALATED,
            actor="POLICY_AGENT",
            actor_type="AGENT",
            reason="POLICY_CONFIRMATION_REQUIRED: no FINAL effective policy matched",
        )
        return request

    if fraud_alert.raised:
        transition(
            request,
            WorkflowState.FRAUD_REVIEW,
            actor="FRAUD_AGENT",
            actor_type="AGENT",
            reason=f"elevated risk: {'; '.join(fraud_alert.reasons)}",
        )
        return request

    request.documents_status = "PENDING" if (policy_result.rule and policy_result.rule.document_requirement) else "NOT_REQUIRED"
    request.policy_validation_status = "PASSED"
    transition(request, WorkflowState.AUTHENTICATION_PENDING, actor="SYSTEM", actor_type="SYSTEM", reason="awaiting authentication")
    return request


def authenticate(request: ServiceRequest, otp_verified: bool, actor: str, actor_role: str) -> ServiceRequest:
    if request.state != WorkflowState.AUTHENTICATION_PENDING:
        raise OrchestratorError(f"request {request.request_id} is not awaiting authentication (state={request.state})")

    request.authentication_status = "PASSED" if otp_verified else "FAILED"
    if not otp_verified:
        transition(request, WorkflowState.CUSTOMER_ACTION_PENDING, actor, actor_role, "authentication failed")
        return request

    if request.documents_status == "PENDING":
        transition(request, WorkflowState.DOCUMENT_PENDING, actor, actor_role, "authentication passed; documents required")
    else:
        transition(request, WorkflowState.DOCUMENT_VERIFICATION, actor, actor_role, "authentication passed; no documents required")
        _advance_to_maker(request, actor, actor_role)
    return request


def submit_documents(request: ServiceRequest, actor: str, actor_role: str) -> ServiceRequest:
    if request.state != WorkflowState.DOCUMENT_PENDING:
        raise OrchestratorError(f"request {request.request_id} is not awaiting documents (state={request.state})")
    request.documents_status = "PASSED"
    transition(request, WorkflowState.DOCUMENT_VERIFICATION, actor, actor_role, "documents submitted and validated")
    _advance_to_maker(request, actor, actor_role)
    return request


def _advance_to_maker(request: ServiceRequest, actor: str, actor_role: str) -> None:
    transition(request, WorkflowState.POLICY_VALIDATION, actor, actor_role, "policy validated at intake")
    transition(request, WorkflowState.RISK_REVIEW, actor, actor_role, "risk scored at intake")
    request.risk_status = "PASSED"
    next_state = WorkflowState.MAKER_PENDING if request.maker_required else WorkflowState.APPROVAL_PENDING
    transition(request, next_state, actor, actor_role, "ready for maker review" if request.maker_required else "no maker required")


def submit_maker_decision(request: ServiceRequest, employee_id: str, proposed_value: dict, reason: str | None = None) -> ServiceRequest:
    record_maker_decision(request, employee_id, proposed_value, reason)
    return request


def submit_checker_decision(request: ServiceRequest, employee_id: str, approve: bool, reason: str | None = None) -> ServiceRequest:
    record_checker_decision(request, employee_id, approve, reason)
    if approve and request.state == WorkflowState.CBS_PENDING:
        execute(request, actor=employee_id, actor_role="EMPLOYEE")
    return request


def execute(request: ServiceRequest, actor: str, actor_role: str) -> ServiceRequest:
    if request.state != WorkflowState.CBS_PENDING:
        raise OrchestratorError(f"request {request.request_id} is not ready for CBS execution (state={request.state})")

    tool_id = _TOOL_BY_SUBSERVICE.get(request.subservice)
    if tool_id is None:
        raise UnsupportedService(f"no CBS write tool wired for subservice={request.subservice!r} in this prototype slice")

    token = issue_authorization_token(request, tool_id)
    proposed_key = _PROPOSED_KEY_BY_SUBSERVICE[request.subservice]
    kwargs = {
        "customer_id": request.customer_id,
        proposed_key: request.proposed_value[proposed_key],
        "idempotency_key": request.idempotency_key,
    }
    result = tool_gateway.call(
        tool_id,
        calling_agent_id="CBS_ACTION_AGENT",
        caller_role="SYSTEM",
        caller_id=actor,
        authorization=token,
        **kwargs,
    )
    request.cbs_result = result

    if not result.success:
        transition(request, WorkflowState.CBS_FAILED, actor, actor_role, result.message)
        return request

    transition(request, WorkflowState.CBS_SUCCESS, actor, actor_role, "CBS write succeeded")

    field_name = _FIELD_BY_SUBSERVICE[request.subservice]
    verification = verification_agent.verify(result, expected_field=field_name, expected_value=request.proposed_value[proposed_key])
    transition(request, WorkflowState.POST_VERIFICATION, actor, actor_role, "post-execution verification")

    if not verification.verified:
        transition(request, WorkflowState.ESCALATED, actor, actor_role, verification.mismatch_reason)
        return request

    tool_gateway.call(
        "send_notification",
        calling_agent_id="NOTIFICATION_AGENT",
        caller_role="SYSTEM",
        caller_id=actor,
        customer_id=request.customer_id,
        channel="SMS",
    )
    transition(request, WorkflowState.COMPLETED, actor, actor_role, "customer notified; request closed")
    return request
