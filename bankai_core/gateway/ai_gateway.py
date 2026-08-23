"""Bank AI Gateway (§5.1) — the single entry point for every AI call.

No application code and no agent implementation calls a `ModelProvider` or
`ModelRouter` directly; everything goes through `AIGateway.invoke()`, which
enforces, in order: agent registration + kill switch, RBAC, PII masking,
prompt-injection tagging, model routing, response scanning, and audit —
exactly the pipeline in `docs/ARCHITECTURE.md` §4.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from bankai_core.agents.registry import AgentRegistry, agent_registry
from bankai_core.gateway.pii_guard import mask_pii
from bankai_core.gateway.prompt_guard import build_payload
from bankai_core.gateway.response_guard import scan_response
from bankai_core.governance.audit import audit_log
from bankai_core.governance.prompt_audit import prompt_audit
from bankai_core.guardrails.kill_switch import KillSwitchEngaged, kill_switch
from bankai_core.models.base import ModelResponse
from bankai_core.models.registry import ModelRegistryEntry
from bankai_core.router.model_router import ModelRouter, TaskSpec, model_router


@dataclass(frozen=True)
class GatewayResult:
    response: ModelResponse
    model_entry: ModelRegistryEntry
    pii_masked_counts: dict[str, int]
    injection_flagged: bool


class AIGatewayError(RuntimeError):
    pass


class AccessDenied(AIGatewayError):
    pass


class AIGateway:
    def __init__(self, registry: AgentRegistry, router: ModelRouter) -> None:
        self._registry = registry
        self._router = router

    def invoke(
        self,
        agent_id: str,
        caller_role: str,
        caller_id: str,
        task_type: str,
        instructions: str,
        data: dict[str, Any],
        context: dict[str, Any] | None = None,
        untrusted_keys: tuple[str, ...] = ("text",),
    ) -> GatewayResult:
        agent_entry = self._registry.get(agent_id)  # raises AgentNotRegistered if unknown

        try:
            kill_switch.check_agent(agent_id)
        except KillSwitchEngaged as exc:
            audit_log.record(
                event_type="AI_GATEWAY_DENIED",
                actor=agent_id,
                actor_type="AGENT",
                action="INVOKE",
                reason=str(exc),
            )
            raise

        if caller_role not in agent_entry.permitted_caller_roles:
            audit_log.record(
                event_type="AI_GATEWAY_DENIED",
                actor=caller_id,
                actor_type=caller_role,
                action=f"INVOKE:{agent_id}",
                reason=f"role '{caller_role}' not permitted for agent '{agent_id}'",
            )
            raise AccessDenied(f"role '{caller_role}' may not invoke agent '{agent_id}'")

        # PII masking / DLP — applied to every string field before any
        # model sees it.
        masked_data: dict[str, Any] = {}
        pii_counts: dict[str, int] = {}
        for key, value in data.items():
            if isinstance(value, str):
                masked, counts = mask_pii(value)
                masked_data[key] = masked
                for label, n in counts.items():
                    pii_counts[label] = pii_counts.get(label, 0) + n
            else:
                masked_data[key] = value

        payload, injection_flags = build_payload(
            task_type=task_type,
            instructions=instructions,
            data=masked_data,
            context=context,
            untrusted_keys=untrusted_keys,
        )
        injection_flagged = any(f.flagged for f in injection_flags)
        if injection_flagged:
            audit_log.record(
                event_type="PROMPT_INJECTION_FLAGGED",
                actor=agent_id,
                actor_type="AGENT",
                action=f"INVOKE:{task_type}",
                evidence={"sources": [f.source for f in injection_flags if f.flagged]},
                reason="untrusted content matched injection heuristics; content still treated as data-only",
            )

        spec = TaskSpec(task_type=task_type)
        model_entry, response = self._router.invoke(spec, payload)

        if model_entry.model_id not in agent_entry.models_allowed:
            audit_log.record(
                event_type="AI_GATEWAY_DENIED",
                actor=agent_id,
                actor_type="AGENT",
                action=f"INVOKE:{model_entry.model_id}",
                reason="model not in agent's models_allowed",
            )
            raise AccessDenied(f"agent '{agent_id}' is not permitted to use model '{model_entry.model_id}'")

        suspicious_keys = scan_response(response.structured)
        if suspicious_keys:
            audit_log.record(
                event_type="RESPONSE_GUARD_FLAGGED",
                actor=agent_id,
                actor_type="AGENT",
                action=f"INVOKE:{task_type}",
                evidence={"suspicious_keys": suspicious_keys},
                reason="model response contained authorization-like keys; ignored by workflow layer regardless",
            )

        prompt_audit.record(
            model=model_entry.model_id,
            model_version=response.model_version,
            agent=agent_id,
            input_text=str(masked_data),
            response_text=response.text,
            decision=response.structured.get("intent_code") or response.structured.get("risk_class") or "N/A",
            user=caller_id,
        )
        audit_log.record(
            event_type="AI_RUN",
            actor=agent_id,
            actor_type="AGENT",
            action=f"INVOKE:{task_type}",
            evidence={"model_id": model_entry.model_id, "confidence": response.confidence},
        )

        return GatewayResult(
            response=response,
            model_entry=model_entry,
            pii_masked_counts=pii_counts,
            injection_flagged=injection_flagged,
        )


ai_gateway = AIGateway(agent_registry, model_router)
