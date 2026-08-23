"""Agent Registry (§7/§8).

No agent may be invoked without a registry entry. `AIGateway` (via
`bankai_core/agents/base.py::AgentRuntime`) looks up the entry before every
call and enforces: the requested model is in `models_allowed`, the caller's
role is in `permitted_caller_roles`, and — critically — `ADVISORY` agents
can never carry `write_permissions` (enforced in `base.py`, not just by
convention here).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from enum import Enum


class AgentClass(str, Enum):
    ADVISORY = "ADVISORY"
    TRANSACTIONAL = "TRANSACTIONAL"


@dataclass
class AgentRegistryEntry:
    agent_id: str
    agent_name: str
    purpose: str
    agent_class: AgentClass
    business_owner: str
    technical_owner: str
    version: str
    risk_level: str  # LOW | MEDIUM | HIGH
    models_allowed: list[str]
    data_allowed: list[str]
    tools_allowed: list[str] = field(default_factory=list)
    read_permissions: list[str] = field(default_factory=list)
    write_permissions: list[str] = field(default_factory=list)
    approval_required: bool = False
    maximum_authority: str = "NONE"
    applicable_policies: list[str] = field(default_factory=list)
    permitted_caller_roles: list[str] = field(default_factory=lambda: ["EMPLOYEE", "CUSTOMER", "SYSTEM"])
    logging_level: str = "STANDARD"
    deployment_status: str = "ACTIVE"
    last_review: date = field(default_factory=date.today)

    def __post_init__(self) -> None:
        if self.agent_class == AgentClass.ADVISORY and self.write_permissions:
            raise ValueError(
                f"Agent '{self.agent_id}' is ADVISORY but declares write_permissions "
                f"{self.write_permissions}; advisory agents may only recommend, never "
                "execute consequential changes (§8)."
            )


class AgentRegistry:
    def __init__(self) -> None:
        self._entries: dict[str, AgentRegistryEntry] = {}

    def register(self, entry: AgentRegistryEntry) -> None:
        self._entries[entry.agent_id] = entry

    def get(self, agent_id: str) -> AgentRegistryEntry:
        try:
            return self._entries[agent_id]
        except KeyError as exc:
            raise AgentNotRegistered(agent_id) from exc

    def all_entries(self) -> list[AgentRegistryEntry]:
        return list(self._entries.values())


class AgentNotRegistered(RuntimeError):
    pass


agent_registry = AgentRegistry()
