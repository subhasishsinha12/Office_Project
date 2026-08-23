"""AI Kill Switch (§43).

Lets AI Governance Administrators disable a model, agent, or tool, or force
the whole platform into manual mode. `AIGateway` and `ToolGateway` both
consult this before doing anything, so disabling here has an immediate,
system-wide effect without touching application code.
"""
from __future__ import annotations

import threading


class KillSwitch:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._disabled_models: set[str] = set()
        self._disabled_agents: set[str] = set()
        self._disabled_tools: set[str] = set()
        self._ai_writes_disabled = False
        self._manual_mode = False

    # -- disable --------------------------------------------------------
    def disable_model(self, model_id: str) -> None:
        with self._lock:
            self._disabled_models.add(model_id)

    def disable_agent(self, agent_id: str) -> None:
        with self._lock:
            self._disabled_agents.add(agent_id)

    def disable_tool(self, tool_id: str) -> None:
        with self._lock:
            self._disabled_tools.add(tool_id)

    def disable_ai_writes(self) -> None:
        with self._lock:
            self._ai_writes_disabled = True

    def enter_manual_mode(self) -> None:
        with self._lock:
            self._manual_mode = True

    # -- re-enable --------------------------------------------------------
    def enable_model(self, model_id: str) -> None:
        with self._lock:
            self._disabled_models.discard(model_id)

    def enable_agent(self, agent_id: str) -> None:
        with self._lock:
            self._disabled_agents.discard(agent_id)

    def enable_tool(self, tool_id: str) -> None:
        with self._lock:
            self._disabled_tools.discard(tool_id)

    def enable_ai_writes(self) -> None:
        with self._lock:
            self._ai_writes_disabled = False

    def exit_manual_mode(self) -> None:
        with self._lock:
            self._manual_mode = False

    # -- checks --------------------------------------------------------
    def is_manual_mode(self) -> bool:
        return self._manual_mode

    def check_model(self, model_id: str) -> None:
        if self._manual_mode or model_id in self._disabled_models:
            raise KillSwitchEngaged(f"model '{model_id}' is disabled")

    def check_agent(self, agent_id: str) -> None:
        if self._manual_mode or agent_id in self._disabled_agents:
            raise KillSwitchEngaged(f"agent '{agent_id}' is disabled")

    def check_tool_write(self, tool_id: str) -> None:
        if self._manual_mode or self._ai_writes_disabled or tool_id in self._disabled_tools:
            raise KillSwitchEngaged(f"tool '{tool_id}' write is disabled")


class KillSwitchEngaged(RuntimeError):
    """Raised when a caller hits a disabled model/agent/tool.

    Callers must catch this and fall back to manual/assisted mode
    (§25 Assisted CBS Mode) rather than retrying the AI path.
    """


kill_switch = KillSwitch()
