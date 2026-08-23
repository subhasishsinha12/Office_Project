"""JSON-safe serialization for workflow/domain objects.

Kept separate from pydantic request/response models in `main.py` because
`ServiceRequest` (workflow/state_machine.py) is the trusted domain object,
not an API contract — the API layer should never accidentally deserialize
untrusted input straight into it.
"""
from __future__ import annotations

from dataclasses import asdict, is_dataclass
from typing import Any

from workflow.state_machine import ServiceRequest


def _jsonable(value: Any) -> Any:
    if is_dataclass(value) and not isinstance(value, type):
        return {k: _jsonable(v) for k, v in asdict(value).items()}
    if hasattr(value, "value") and hasattr(value, "name") and not isinstance(value, (int, str)):
        # Enum
        return value.value
    if isinstance(value, dict):
        return {k: _jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_jsonable(v) for v in value]
    return value


def request_to_dict(request: ServiceRequest) -> dict:
    data = {
        "request_id": request.request_id,
        "customer_id": request.customer_id,
        "customer_type": request.customer_type,
        "service": request.service,
        "subservice": request.subservice,
        "intent_code": request.intent_code,
        "channel": request.channel,
        "state": request.state.value,
        "maker_required": request.maker_required,
        "checker_required": request.checker_required,
        "authentication_status": request.authentication_status,
        "documents_status": request.documents_status,
        "policy_validation_status": request.policy_validation_status,
        "risk_status": request.risk_status,
        "risk_class": request.risk_class,
        "policy_rule_id": request.policy_rule_id,
        "proposed_value": request.proposed_value,
        "maker_decision": _jsonable(request.maker_decision) if request.maker_decision else None,
        "checker_decision": _jsonable(request.checker_decision) if request.checker_decision else None,
        "cbs_result": _jsonable(request.cbs_result) if request.cbs_result else None,
    }
    return data
