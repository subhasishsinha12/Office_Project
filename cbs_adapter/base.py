"""Generic CBS Adapter interface (§24).

`bankai_core.tools.gateway.ToolGateway` depends only on this protocol.
Swapping the mock for a real Finacle/BaNCS/Flexcube adapter means writing
one class that implements `CBSAdapter` — no change to the Tool Gateway,
Tool Registry, or any agent.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol


@dataclass(frozen=True)
class CBSResult:
    success: bool
    txn_id: str
    before_state: dict[str, Any]
    after_state: dict[str, Any]
    message: str = ""


class CBSAdapter(Protocol):
    def get_customer_profile(self, customer_id: str) -> dict[str, Any]: ...

    def get_account_status(self, account_id: str) -> dict[str, Any]: ...

    def get_kyc_status(self, customer_id: str) -> dict[str, Any]: ...

    def update_mobile(self, customer_id: str, new_mobile: str, idempotency_key: str) -> CBSResult: ...

    def update_address(self, customer_id: str, new_address: str, idempotency_key: str) -> CBSResult: ...

    def stop_cheque(self, account_id: str, cheque_number: str, idempotency_key: str) -> CBSResult: ...
