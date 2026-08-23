"""§42 — Agent Permission Test.

An agent not listed in a tool's `allowed_agents` must be denied, regardless
of role or any authorization token it presents.
"""
from __future__ import annotations

import pytest

from bankai_core.tools.gateway import ToolAccessDenied, tool_gateway
from bankai_core.tools.registry import ToolNotRegistered


def test_advisory_agent_cannot_call_cbs_write_tool():
    with pytest.raises(ToolAccessDenied):
        tool_gateway.call(
            "update_mobile",
            calling_agent_id="INTENT_AGENT",  # advisory, not in allowed_agents for this tool
            caller_role="SYSTEM",
            caller_id="test",
            authorization=None,
            customer_id="CUST-0001",
            new_mobile="9999999999",
            idempotency_key="idem-test-1",
        )


def test_unregistered_tool_is_rejected():
    with pytest.raises(ToolNotRegistered):
        tool_gateway.call(
            "delete_customer",  # never registered — no such tool exists
            calling_agent_id="CBS_ACTION_AGENT",
            caller_role="SYSTEM",
            caller_id="test",
        )


def test_wrong_caller_role_is_denied_for_read_tool():
    with pytest.raises(ToolAccessDenied):
        tool_gateway.call(
            "get_customer_profile",
            calling_agent_id="INTENT_AGENT",
            caller_role="CUSTOMER",  # get_customer_profile requires EMPLOYEE|SYSTEM
            caller_id="test",
            customer_id="CUST-0001",
        )
