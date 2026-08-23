"""Agent base classes (§8).

`AdvisoryAgent` and `TransactionalAgent` both route every model call through
`AIGateway.invoke()` — no agent implementation is allowed to import a
`ModelProvider` or `ModelRouter` directly (enforced by convention here and
by there being no other supported way to reach a model from `bankai_core.
agents.*`). The distinction that matters for safety is enforced structurally
elsewhere:

- `AgentRegistryEntry.__post_init__` refuses to register an `ADVISORY` agent
  that declares `write_permissions`.
- Any write a `TransactionalAgent` performs still goes through
  `bankai_core.tools.gateway.ToolGateway`, which independently re-checks
  maker/checker/policy state from the database before executing — the
  agent's own registry entry is necessary but never sufficient.
"""
from __future__ import annotations

from typing import Any

from bankai_core.gateway.ai_gateway import GatewayResult, ai_gateway


class BaseAgent:
    agent_id: str

    def _invoke(
        self,
        caller_role: str,
        caller_id: str,
        task_type: str,
        instructions: str,
        data: dict[str, Any],
        context: dict[str, Any] | None = None,
        untrusted_keys: tuple[str, ...] = ("text",),
    ) -> GatewayResult:
        return ai_gateway.invoke(
            agent_id=self.agent_id,
            caller_role=caller_role,
            caller_id=caller_id,
            task_type=task_type,
            instructions=instructions,
            data=data,
            context=context,
            untrusted_keys=untrusted_keys,
        )


class AdvisoryAgent(BaseAgent):
    """May recommend. May never execute a consequential change (§8)."""


class TransactionalAgent(BaseAgent):
    """May request a write via the Tool Gateway; cannot execute one itself."""
