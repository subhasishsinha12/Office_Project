"""BranchOne — FastAPI application (§45).

Startup registers agents and loads synthetic policy data; every request
after that flows through `apps.branchone_api.orchestrator`, which is the
only module that sequences BankAI Core's agents, rule engine, workflow
engine and tool gateway. Nothing here calls a model provider or the CBS
adapter directly.
"""
from __future__ import annotations

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from apps.branchone_api import orchestrator
from apps.branchone_api.schemas import request_to_dict
from apps.branchone_api.store import request_store
from bankai_core.agents.bootstrap import register_all_agents
from bankai_core.agents.document_agent import document_agent
from bankai_core.agents.intent_agent import intent_agent
from bankai_core.agents.policy_agent import policy_agent
from bankai_core.agents.registry import agent_registry
from bankai_core.governance.audit import audit_log
from bankai_core.policy.seed_data import load_seed_policies
from bankai_core.tools.registry import tool_registry
from workflow.maker_checker import SegregationOfDutyViolation
from workflow.state_machine import WorkflowState

app = FastAPI(title="BranchOne", description="Powered by BankAI Core")


@app.on_event("startup")
def _startup() -> None:
    register_all_agents()
    load_seed_policies()


def _get_request_or_404(request_id: str):
    req = request_store.get(request_id)
    if req is None:
        raise HTTPException(status_code=404, detail=f"request {request_id} not found")
    return req


# ---------------------------------------------------------------- requests

class CreateRequestBody(BaseModel):
    customer_id: str
    text: str
    caller_role: str = "CUSTOMER"
    caller_id: str
    channel: str = "BRANCH"
    recent_mobile_changes_90d: int = 0
    failed_otp_attempts: int = 0


@app.post("/requests")
def create_request(body: CreateRequestBody):
    try:
        req = orchestrator.create_request(
            customer_id=body.customer_id,
            text=body.text,
            caller_role=body.caller_role,
            caller_id=body.caller_id,
            channel=body.channel,
            recent_mobile_changes_90d=body.recent_mobile_changes_90d,
            failed_otp_attempts=body.failed_otp_attempts,
        )
    except orchestrator.HumanClarificationRequired as exc:
        return JSONResponse(status_code=422, content={"error": "HUMAN_CLARIFICATION_REQUIRED", "detail": str(exc)})
    return request_to_dict(req)


@app.get("/requests/{request_id}")
def get_request(request_id: str):
    return request_to_dict(_get_request_or_404(request_id))


class AuthenticateBody(BaseModel):
    otp_verified: bool
    actor: str
    actor_role: str = "CUSTOMER"


@app.post("/requests/{request_id}/authenticate")
def authenticate(request_id: str, body: AuthenticateBody):
    req = _get_request_or_404(request_id)
    try:
        orchestrator.authenticate(req, body.otp_verified, body.actor, body.actor_role)
    except orchestrator.OrchestratorError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return request_to_dict(req)


class DocumentsBody(BaseModel):
    actor: str
    actor_role: str = "EMPLOYEE"


@app.post("/requests/{request_id}/documents")
def submit_documents(request_id: str, body: DocumentsBody):
    req = _get_request_or_404(request_id)
    try:
        orchestrator.submit_documents(req, body.actor, body.actor_role)
    except orchestrator.OrchestratorError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return request_to_dict(req)


class MakerBody(BaseModel):
    employee_id: str
    proposed_value: dict
    reason: str | None = None


@app.post("/requests/{request_id}/maker")
def maker_decision(request_id: str, body: MakerBody):
    req = _get_request_or_404(request_id)
    try:
        orchestrator.submit_maker_decision(req, body.employee_id, body.proposed_value, body.reason)
    except Exception as exc:  # MakerCheckerError etc.
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return request_to_dict(req)


class CheckerBody(BaseModel):
    employee_id: str
    approve: bool
    reason: str | None = None


@app.post("/requests/{request_id}/checker")
def checker_decision(request_id: str, body: CheckerBody):
    req = _get_request_or_404(request_id)
    try:
        orchestrator.submit_checker_decision(req, body.employee_id, body.approve, body.reason)
    except SegregationOfDutyViolation as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return request_to_dict(req)


@app.post("/requests/{request_id}/execute")
def execute_request(request_id: str):
    req = _get_request_or_404(request_id)
    if req.state != WorkflowState.CBS_PENDING:
        raise HTTPException(status_code=409, detail=f"request is not CBS_PENDING (state={req.state.value})")
    orchestrator.execute(req, actor="API", actor_role="SYSTEM")
    return request_to_dict(req)


@app.get("/requests/{request_id}/audit")
def get_audit(request_id: str):
    _get_request_or_404(request_id)
    return [
        {
            "event_id": e.event_id,
            "event_type": e.event_type,
            "actor": e.actor,
            "actor_type": e.actor_type,
            "action": e.action,
            "decision": e.decision,
            "previous_value": e.previous_value,
            "requested_value": e.requested_value,
            "reason": e.reason,
            "evidence": e.evidence,
            "timestamp": e.timestamp,
        }
        for e in audit_log.for_subject(request_id)
    ]


# --------------------------------------------------------------------- AI

class IntentBody(BaseModel):
    text: str
    caller_role: str = "EMPLOYEE"
    caller_id: str = "anonymous"


@app.post("/ai/intent")
def ai_intent(body: IntentBody):
    result = intent_agent.classify(body.text, caller_role=body.caller_role, caller_id=body.caller_id)
    return {
        "intent_code": result.intent_code,
        "domain": result.domain,
        "service": result.service,
        "subservice": result.subservice,
        "action": result.action,
        "confidence": result.confidence,
        "human_clarification_required": result.human_clarification_required,
        "ai_role": "intent classification only — advisory",
    }


class DocumentAnalyseBody(BaseModel):
    ocr_text: str
    caller_role: str = "EMPLOYEE"
    caller_id: str = "anonymous"


@app.post("/ai/document/analyse")
def ai_document_analyse(body: DocumentAnalyseBody):
    result = document_agent.analyse(body.ocr_text, caller_role=body.caller_role, caller_id=body.caller_id)
    return {
        "pan_numbers_detected": result.pan_numbers_detected,
        "names_detected": result.names_detected,
        "fields_extracted": result.fields_extracted,
        "confidence": result.confidence,
        "verification_required": result.verification_required,
        "ai_role": "document extraction only — human verification required before use",
    }


class PolicyQueryBody(BaseModel):
    service: str
    customer_type: str
    caller_id: str = "anonymous"


@app.post("/policy/query")
def policy_query(body: PolicyQueryBody):
    result = policy_agent.retrieve(service=body.service, customer_type=body.customer_type, caller_id=body.caller_id)
    if result.confirmation_required:
        return {"found": False, "answer": "POLICY_CONFIRMATION_REQUIRED", "policy_basis": None, "ai_role": "policy retrieval only"}
    rule = result.rule
    return {
        "found": True,
        "policy_basis": {
            "rule_id": rule.rule_id,
            "circular": rule.circular,
            "clause": rule.clause,
            "status": rule.status.value,
            "maker_required": rule.maker_required,
            "checker_required": rule.checker_required,
            "document_requirement": rule.document_requirement,
            "source_reference": rule.source_reference,
        },
        "confidence": "HIGH",
        "ai_role": "policy retrieval only",
        "human_action_required": "maker review followed by checker approval" if rule.checker_required else "maker review",
    }


# ---------------------------------------------------------- control tower

@app.get("/dashboard")
def dashboard():
    requests = request_store.all()
    by_state: dict[str, int] = {}
    for r in requests:
        by_state[r.state.value] = by_state.get(r.state.value, 0) + 1
    return {
        "total_requests": len(requests),
        "by_state": by_state,
        "maker_pending": by_state.get(WorkflowState.MAKER_PENDING.value, 0),
        "checker_pending": by_state.get(WorkflowState.CHECKER_PENDING.value, 0),
        "fraud_review": by_state.get(WorkflowState.FRAUD_REVIEW.value, 0),
        "escalated": by_state.get(WorkflowState.ESCALATED.value, 0),
        "completed": by_state.get(WorkflowState.COMPLETED.value, 0),
    }


@app.get("/agents")
def list_agents():
    return [
        {
            "agent_id": e.agent_id,
            "agent_name": e.agent_name,
            "agent_class": e.agent_class.value,
            "risk_level": e.risk_level,
            "models_allowed": e.models_allowed,
            "tools_allowed": e.tools_allowed,
            "write_permissions": e.write_permissions,
            "deployment_status": e.deployment_status,
        }
        for e in agent_registry.all_entries()
    ]


@app.get("/tools")
def list_tools():
    return [
        {
            "tool_id": e.tool_id,
            "tool_name": e.tool_name,
            "mode": e.mode.value,
            "allowed_agents": e.allowed_agents,
            "required_approval": e.required_approval.value,
            "risk_level": e.risk_level,
        }
        for e in tool_registry.all_entries()
    ]
