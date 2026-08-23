"""Mock CBS (§49).

In-memory core banking simulator. Supports before/after state capture,
transaction IDs, and idempotency-key deduplication — a write submitted
twice with the same idempotency_key executes exactly once and returns the
original result the second time, matching real CBS/payment-rail behaviour.
"""
from __future__ import annotations

import itertools
import threading
from typing import Any

from cbs_adapter.base import CBSResult


class MockCBS:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._txn_counter = itertools.count(1)
        self._idempotency_store: dict[str, CBSResult] = {}
        # customer_id -> profile
        self._customers: dict[str, dict[str, Any]] = {
            "CUST-0001": {
                "customer_id": "CUST-0001",
                "name": "Ravi Kumar",
                "customer_type": "INDIVIDUAL",
                "mobile": "9800000001",
                "address": "12 MG Road, Pune",
                "kyc_status": "VALID",
            },
            "CUST-0002": {
                "customer_id": "CUST-0002",
                "name": "Suresh & Associates",
                "customer_type": "PARTNERSHIP",
                "mobile": "9800000002",
                "address": "45 Anna Salai, Chennai",
                "kyc_status": "VALID",
            },
        }
        self._accounts: dict[str, dict[str, Any]] = {
            "ACC-1001": {"account_id": "ACC-1001", "customer_id": "CUST-0001", "status": "ACTIVE"},
            "ACC-1002": {"account_id": "ACC-1002", "customer_id": "CUST-0002", "status": "ACTIVE"},
        }

    def _next_txn_id(self) -> str:
        return f"TXN-{next(self._txn_counter):08d}"

    def get_customer_profile(self, customer_id: str) -> dict[str, Any]:
        return dict(self._customers.get(customer_id, {}))

    def get_account_status(self, account_id: str) -> dict[str, Any]:
        return dict(self._accounts.get(account_id, {}))

    def get_kyc_status(self, customer_id: str) -> dict[str, Any]:
        customer = self._customers.get(customer_id, {})
        return {"customer_id": customer_id, "kyc_status": customer.get("kyc_status", "UNKNOWN")}

    def _with_idempotency(self, idempotency_key: str, action) -> CBSResult:
        with self._lock:
            if idempotency_key in self._idempotency_store:
                return self._idempotency_store[idempotency_key]
            result = action()
            self._idempotency_store[idempotency_key] = result
            return result

    def update_mobile(self, customer_id: str, new_mobile: str, idempotency_key: str) -> CBSResult:
        def action() -> CBSResult:
            customer = self._customers.get(customer_id)
            if customer is None:
                return CBSResult(False, self._next_txn_id(), {}, {}, message=f"customer {customer_id} not found")
            before = dict(customer)
            customer["mobile"] = new_mobile
            after = dict(customer)
            return CBSResult(True, self._next_txn_id(), before, after, message="mobile updated")

        return self._with_idempotency(idempotency_key, action)

    def update_address(self, customer_id: str, new_address: str, idempotency_key: str) -> CBSResult:
        def action() -> CBSResult:
            customer = self._customers.get(customer_id)
            if customer is None:
                return CBSResult(False, self._next_txn_id(), {}, {}, message=f"customer {customer_id} not found")
            before = dict(customer)
            customer["address"] = new_address
            after = dict(customer)
            return CBSResult(True, self._next_txn_id(), before, after, message="address updated")

        return self._with_idempotency(idempotency_key, action)

    def stop_cheque(self, account_id: str, cheque_number: str, idempotency_key: str) -> CBSResult:
        def action() -> CBSResult:
            account = self._accounts.get(account_id)
            if account is None:
                return CBSResult(False, self._next_txn_id(), {}, {}, message=f"account {account_id} not found")
            before = dict(account)
            stopped = set(account.get("stopped_cheques", set()))
            stopped.add(cheque_number)
            account["stopped_cheques"] = stopped
            after = dict(account)
            return CBSResult(True, self._next_txn_id(), before, after, message=f"cheque {cheque_number} stopped")

        return self._with_idempotency(idempotency_key, action)


mock_cbs = MockCBS()
