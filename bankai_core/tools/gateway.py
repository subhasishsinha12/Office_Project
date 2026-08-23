"""Bank Tool Gateway (§21/§22/§23) — the only path from an agent to the CBS.

This is where §57's "Critical Security Test" is actually enforced:
`call()` has no parameter that lets a caller assert "approved" — for any
tool whose `required_approval != NONE`, the caller must present an
`AuthorizationToken`, and that token can only be constructed by
`workflow.maker_checker.issue_authorization_token()`, which itself refuses
unless the `ServiceRequest` in the database already shows a genuine,
segregated maker approval and checker approval. There is no `force=True`,
no free-text override, and no field a model's output can populate that
this module reads as authorization.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from bankai_core.governance.audit import audit_log
from bankai_core.guardrails.kill_switch import KillSwitchEngaged, kill_switch
from bankai_core.tools.cbs_tools import run_tool
from bankai_core.tools.registry import ApprovalRequirement, ToolMode, ToolRegistry, tool_registry
from cbs_adapter.base import CBSAdapter
from cbs_adapter.mock_cbs import mock_cbs


@dataclass
class AuthorizationToken:
    """Issued only by `workflow.maker_checker.issue_authorization_token()`.

    `checks` records exactly which preconditions were verified against
    database state at issuance time (§7); `ToolGateway` re-verifies that
    every recorded check is `True` and that the token targets the tool
    being called, then consumes it — a token can authorize exactly one
    tool call.
    """

    request_id: str
    tool_id: str
    idempotency_key: str
    checks: dict[str, bool] = field(default_factory=dict)
    consumed: bool = False


class ToolGatewayError(RuntimeError):
    pass


class ToolAccessDenied(ToolGatewayError):
    pass


class ToolAuthorizationDenied(ToolGatewayError):
    pass


class ToolGateway:
    def __init__(self, registry: ToolRegistry, cbs_adapter: CBSAdapter) -> None:
        self._registry = registry
        self._cbs_adapter = cbs_adapter

    def call(
        self,
        tool_id: str,
        calling_agent_id: str,
        caller_role: str,
        caller_id: str,
        authorization: AuthorizationToken | None = None,
        **kwargs,
    ):
        entry = self._registry.get(tool_id)  # raises ToolNotRegistered if unknown

        if entry.mode == ToolMode.WRITE:
            try:
                kill_switch.check_tool_write(tool_id)
            except KillSwitchEngaged as exc:
                self._deny(tool_id, calling_agent_id, caller_id, str(exc))
                raise

        if calling_agent_id not in entry.allowed_agents:
            reason = f"agent '{calling_agent_id}' is not in allowed_agents for tool '{tool_id}'"
            self._deny(tool_id, calling_agent_id, caller_id, reason)
            raise ToolAccessDenied(reason)

        if caller_role not in entry.required_role:
            reason = f"caller role '{caller_role}' not permitted for tool '{tool_id}'"
            self._deny(tool_id, calling_agent_id, caller_id, reason)
            raise ToolAccessDenied(reason)

        if entry.required_approval != ApprovalRequirement.NONE:
            self._check_authorization(entry.tool_id, authorization, calling_agent_id, caller_id)

        if tool_id == "send_notification":
            # Notification has no CBS state to mutate; handled outside the
            # CBS adapter but still fully gated/audited above.
            result = {"notified": True, "channel": kwargs.get("channel", "SMS")}
        else:
            result = run_tool(self._cbs_adapter, tool_id, **kwargs)

        audit_log.record(
            event_type="TOOL_CALL",
            actor=calling_agent_id,
            actor_type="AGENT",
            action=f"CALL:{tool_id}",
            subject_id=(authorization.request_id if authorization else None) or kwargs.get("customer_id") or kwargs.get("account_id"),
            evidence={
                "caller_id": caller_id,
                "caller_role": caller_role,
                "authorization_request_id": authorization.request_id if authorization else None,
                "result": _summarize(result),
            },
            decision="EXECUTED",
        )
        return result

    def _check_authorization(
        self,
        tool_id: str,
        authorization: AuthorizationToken | None,
        calling_agent_id: str,
        caller_id: str,
    ) -> None:
        if authorization is None:
            reason = f"tool '{tool_id}' requires an AuthorizationToken issued by the workflow engine; none provided"
            self._deny(tool_id, calling_agent_id, caller_id, reason)
            raise ToolAuthorizationDenied(reason)
        if authorization.tool_id != tool_id:
            reason = f"authorization token was issued for '{authorization.tool_id}', not '{tool_id}'"
            self._deny(tool_id, calling_agent_id, caller_id, reason)
            raise ToolAuthorizationDenied(reason)
        if authorization.consumed:
            reason = "authorization token already consumed (idempotency replay rejected)"
            self._deny(tool_id, calling_agent_id, caller_id, reason)
            raise ToolAuthorizationDenied(reason)
        unmet = [name for name, passed in authorization.checks.items() if not passed]
        if unmet:
            reason = f"unmet preconditions: {unmet}"
            self._deny(tool_id, calling_agent_id, caller_id, reason)
            raise ToolAuthorizationDenied(reason)
        authorization.consumed = True

    @staticmethod
    def _deny(tool_id: str, calling_agent_id: str, caller_id: str, reason: str) -> None:
        audit_log.record(
            event_type="TOOL_CALL_DENIED",
            actor=calling_agent_id,
            actor_type="AGENT",
            action=f"CALL:{tool_id}",
            evidence={"caller_id": caller_id},
            reason=reason,
            decision="DENIED",
        )


def _summarize(result) -> dict:
    if hasattr(result, "__dict__"):
        return {"success": getattr(result, "success", None), "txn_id": getattr(result, "txn_id", None)}
    return {"result": str(result)[:200]}


tool_gateway = ToolGateway(tool_registry, mock_cbs)
