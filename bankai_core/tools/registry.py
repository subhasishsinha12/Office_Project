"""Tool Registry (§21).

Every tool an agent may call — read or write — is declared here before it
can be invoked. `ToolGateway.call()` (gateway.py) is the only caller of
`ToolRegistry.get()`; no agent looks a tool up and calls it directly.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class ToolMode(str, Enum):
    READ = "READ"
    WRITE = "WRITE"


class ApprovalRequirement(str, Enum):
    NONE = "NONE"
    MAKER = "MAKER"
    MAKER_CHECKER = "MAKER_CHECKER"


@dataclass(frozen=True)
class ToolRegistryEntry:
    tool_id: str
    tool_name: str
    mode: ToolMode
    data_scope: str
    allowed_agents: list[str]
    required_role: list[str]
    required_approval: ApprovalRequirement
    risk_level: str
    rate_limit_per_minute: int
    audit_requirement: str = "FULL"


class ToolRegistry:
    def __init__(self) -> None:
        self._entries: dict[str, ToolRegistryEntry] = {}

    def register(self, entry: ToolRegistryEntry) -> None:
        self._entries[entry.tool_id] = entry

    def get(self, tool_id: str) -> ToolRegistryEntry:
        try:
            return self._entries[tool_id]
        except KeyError as exc:
            raise ToolNotRegistered(tool_id) from exc

    def all_entries(self) -> list[ToolRegistryEntry]:
        return list(self._entries.values())


class ToolNotRegistered(RuntimeError):
    pass


tool_registry = ToolRegistry()

tool_registry.register(
    ToolRegistryEntry(
        tool_id="get_customer_profile",
        tool_name="Get Customer Profile",
        mode=ToolMode.READ,
        data_scope="CUSTOMER_PROFILE",
        allowed_agents=["INTENT_AGENT", "POLICY_AGENT", "RISK_AGENT", "DOCUMENT_AGENT", "CBS_ACTION_AGENT"],
        required_role=["EMPLOYEE", "SYSTEM"],
        required_approval=ApprovalRequirement.NONE,
        risk_level="LOW",
        rate_limit_per_minute=120,
    )
)
tool_registry.register(
    ToolRegistryEntry(
        tool_id="get_kyc_status",
        tool_name="Get KYC Status",
        mode=ToolMode.READ,
        data_scope="KYC",
        allowed_agents=["RISK_AGENT", "CBS_ACTION_AGENT"],
        required_role=["EMPLOYEE", "SYSTEM"],
        required_approval=ApprovalRequirement.NONE,
        risk_level="LOW",
        rate_limit_per_minute=120,
    )
)
tool_registry.register(
    ToolRegistryEntry(
        tool_id="update_mobile",
        tool_name="Update Mobile Number",
        mode=ToolMode.WRITE,
        data_scope="CUSTOMER_PROFILE",
        allowed_agents=["CBS_ACTION_AGENT"],
        required_role=["SYSTEM"],
        required_approval=ApprovalRequirement.MAKER_CHECKER,
        risk_level="MEDIUM",
        rate_limit_per_minute=30,
    )
)
tool_registry.register(
    ToolRegistryEntry(
        tool_id="update_address",
        tool_name="Update Address",
        mode=ToolMode.WRITE,
        data_scope="CUSTOMER_PROFILE",
        allowed_agents=["CBS_ACTION_AGENT"],
        required_role=["SYSTEM"],
        required_approval=ApprovalRequirement.MAKER_CHECKER,
        risk_level="MEDIUM",
        rate_limit_per_minute=30,
    )
)
tool_registry.register(
    ToolRegistryEntry(
        tool_id="stop_cheque",
        tool_name="Stop Cheque",
        mode=ToolMode.WRITE,
        data_scope="ACCOUNT",
        allowed_agents=["CBS_ACTION_AGENT"],
        required_role=["SYSTEM"],
        required_approval=ApprovalRequirement.MAKER,
        risk_level="MEDIUM",
        rate_limit_per_minute=30,
    )
)
tool_registry.register(
    ToolRegistryEntry(
        tool_id="send_notification",
        tool_name="Send Customer Notification",
        mode=ToolMode.WRITE,
        data_scope="NOTIFICATION",
        allowed_agents=["NOTIFICATION_AGENT"],
        required_role=["SYSTEM"],
        required_approval=ApprovalRequirement.NONE,
        risk_level="LOW",
        rate_limit_per_minute=120,
    )
)
