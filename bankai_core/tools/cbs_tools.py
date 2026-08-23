"""CBS tool implementations (§22) — thin wrappers around `cbs_adapter`.

Only `bankai_core.tools.gateway.ToolGateway` imports this module. No agent
imports `cbs_adapter` directly.
"""
from __future__ import annotations

from typing import Any, Callable

from cbs_adapter.base import CBSAdapter

TOOL_IMPLEMENTATIONS: dict[str, Callable[..., Any]] = {
    "get_customer_profile": lambda adapter, customer_id, **_: adapter.get_customer_profile(customer_id),
    "get_kyc_status": lambda adapter, customer_id, **_: adapter.get_kyc_status(customer_id),
    "update_mobile": lambda adapter, customer_id, new_mobile, idempotency_key, **_: adapter.update_mobile(
        customer_id, new_mobile, idempotency_key
    ),
    "update_address": lambda adapter, customer_id, new_address, idempotency_key, **_: adapter.update_address(
        customer_id, new_address, idempotency_key
    ),
    "stop_cheque": lambda adapter, account_id, cheque_number, idempotency_key, **_: adapter.stop_cheque(
        account_id, cheque_number, idempotency_key
    ),
}


def run_tool(adapter: CBSAdapter, tool_id: str, **kwargs: Any) -> Any:
    impl = TOOL_IMPLEMENTATIONS.get(tool_id)
    if impl is None:
        raise ValueError(f"no CBS implementation registered for tool_id={tool_id!r}")
    return impl(adapter, **kwargs)
