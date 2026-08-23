"""§43 — AI Kill Switch: disabling an agent/tool/model has an immediate,
system-wide effect, and the platform can be forced into manual mode.
"""
from __future__ import annotations

import pytest

from bankai_core.agents.intent_agent import intent_agent
from bankai_core.gateway.ai_gateway import AccessDenied
from bankai_core.guardrails.kill_switch import KillSwitchEngaged, kill_switch
from bankai_core.tools.gateway import tool_gateway


def test_disabling_agent_blocks_further_invocation():
    kill_switch.disable_agent("INTENT_AGENT")
    try:
        with pytest.raises(KillSwitchEngaged):
            intent_agent.classify("My mobile number has changed", caller_role="CUSTOMER", caller_id="CUST-0001")
    finally:
        kill_switch.enable_agent("INTENT_AGENT")

    # Re-enabled: works again.
    result = intent_agent.classify("My mobile number has changed", caller_role="CUSTOMER", caller_id="CUST-0001")
    assert result.intent_code == "CM_CONTACT_MOBILE_MOD"


def test_disabling_tool_write_blocks_cbs_write():
    kill_switch.disable_tool("update_mobile")
    try:
        with pytest.raises(KillSwitchEngaged):
            tool_gateway.call(
                "update_mobile",
                calling_agent_id="CBS_ACTION_AGENT",
                caller_role="SYSTEM",
                caller_id="test",
                authorization=None,
                customer_id="CUST-0001",
                new_mobile="9999999999",
                idempotency_key="idem-kill-switch-test",
            )
    finally:
        kill_switch.enable_tool("update_mobile")


def test_manual_mode_blocks_every_agent_and_write_tool():
    kill_switch.enter_manual_mode()
    try:
        with pytest.raises(KillSwitchEngaged):
            intent_agent.classify("My mobile number has changed", caller_role="CUSTOMER", caller_id="CUST-0001")
        with pytest.raises(KillSwitchEngaged):
            tool_gateway.call(
                "update_mobile",
                calling_agent_id="CBS_ACTION_AGENT",
                caller_role="SYSTEM",
                caller_id="test",
                customer_id="CUST-0001",
                new_mobile="9999999999",
                idempotency_key="idem-manual-mode-test",
            )
    finally:
        kill_switch.exit_manual_mode()
