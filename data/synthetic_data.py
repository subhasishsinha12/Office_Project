"""Synthetic data generator (§48).

Generates purely synthetic customers/accounts/employees/service requests/
risk & audit events as JSON files under `data/generated/`. Stdlib-only
(no Faker dependency) to keep the prototype's dependency footprint small.
Never touches real customer data — there is no code path here that reads
from any production or external source.

Run: python -m data.synthetic_data
"""
from __future__ import annotations

import json
import random
import string
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

_FIRST_NAMES = ["Ravi", "Suresh", "Anita", "Priya", "Vikram", "Kavita", "Arjun", "Meera", "Sanjay", "Deepa"]
_LAST_NAMES = ["Kumar", "Sharma", "Iyer", "Nair", "Patel", "Reddy", "Gupta", "Menon", "Rao", "Singh"]
_CUSTOMER_TYPES = ["INDIVIDUAL", "INDIVIDUAL", "INDIVIDUAL", "PARTNERSHIP", "COMPANY"]
_SERVICES = [
    ("CONTACT_DETAILS", "MOBILE"),
    ("CONTACT_DETAILS", "ADDRESS"),
    ("CONTACT_DETAILS", "EMAIL"),
    ("CONSTITUTION", "PARTNER"),
    ("MANDATE", "SIGNATORY"),
    ("CHEQUE_BOOK", "STOP_PAYMENT"),
    ("PROFILE", "NOMINEE"),
]
_ACCOUNT_TYPES = ["SAVINGS", "CURRENT", "LOAN", "FD"]
_STATES = [
    "DRAFT", "SUBMITTED", "MAKER_PENDING", "CHECKER_PENDING", "CBS_PENDING",
    "COMPLETED", "COMPLETED", "COMPLETED", "ESCALATED", "FRAUD_REVIEW", "REJECTED",
]

_rng = random.Random(42)  # deterministic output for reproducible demos


def _pan() -> str:
    return "".join(_rng.choices(string.ascii_uppercase, k=5)) + "".join(_rng.choices(string.digits, k=4)) + _rng.choice(string.ascii_uppercase)


def _mobile() -> str:
    return "9" + "".join(_rng.choices(string.digits, k=9))


def generate_customers(n: int) -> list[dict]:
    customers = []
    for i in range(1, n + 1):
        ctype = _rng.choice(_CUSTOMER_TYPES)
        name = f"{_rng.choice(_FIRST_NAMES)} {_rng.choice(_LAST_NAMES)}" if ctype == "INDIVIDUAL" else f"{_rng.choice(_LAST_NAMES)} & {_rng.choice(['Associates', 'Sons', 'Traders', 'Enterprises'])}"
        customers.append(
            {
                "customer_id": f"CUST-{i:04d}",
                "name": name,
                "customer_type": ctype,
                "pan": _pan(),
                "mobile": _mobile(),
                "kyc_status": _rng.choice(["VALID", "VALID", "VALID", "EXPIRED", "PENDING"]),
            }
        )
    return customers


def generate_accounts(customers: list[dict], n: int) -> list[dict]:
    accounts = []
    for i in range(1, n + 1):
        customer = _rng.choice(customers)
        accounts.append(
            {
                "account_id": f"ACC-{i:04d}",
                "customer_id": customer["customer_id"],
                "account_type": _rng.choice(_ACCOUNT_TYPES),
                "status": _rng.choice(["ACTIVE", "ACTIVE", "ACTIVE", "DORMANT", "FROZEN"]),
            }
        )
    return accounts


def generate_employees(n: int) -> list[dict]:
    roles = ["BRANCH_MAKER", "BRANCH_CHECKER", "BRANCH_MANAGER", "BRANCH_OPERATIONS_OFFICER"]
    employees = []
    for i in range(1, n + 1):
        employees.append(
            {
                "employee_id": f"EMP{i:04d}",
                "name": f"{_rng.choice(_FIRST_NAMES)} {_rng.choice(_LAST_NAMES)}",
                "role": _rng.choice(roles),
                "branch_code": f"BR{_rng.randint(1, 20):03d}",
            }
        )
    return employees


def generate_service_requests(customers: list[dict], n: int) -> list[dict]:
    requests = []
    base_time = datetime(2026, 1, 1, tzinfo=timezone.utc)
    for i in range(1, n + 1):
        customer = _rng.choice(customers)
        service, subservice = _rng.choice(_SERVICES)
        created = base_time + timedelta(hours=_rng.randint(0, 24 * 200))
        requests.append(
            {
                "request_id": f"BR-2026-{uuid.UUID(int=_rng.getrandbits(128)).hex[:8].upper()}",
                "customer_id": customer["customer_id"],
                "customer_type": customer["customer_type"],
                "service": service,
                "subservice": subservice,
                "state": _rng.choice(_STATES),
                "created_at": created.isoformat(),
            }
        )
    return requests


def generate_risk_alerts(requests: list[dict], n: int) -> list[dict]:
    sample = _rng.sample(requests, k=min(n, len(requests)))
    return [
        {
            "risk_flag_id": f"RSK-{i:04d}",
            "request_id": r["request_id"],
            "risk_score": _rng.randint(0, 100),
            "risk_class": _rng.choice(["GREEN", "GREEN", "AMBER", "RED"]),
        }
        for i, r in enumerate(sample, start=1)
    ]


def generate_audit_events(requests: list[dict], n: int) -> list[dict]:
    events = []
    for i in range(1, n + 1):
        r = _rng.choice(requests)
        events.append(
            {
                "event_id": i,
                "subject_id": r["request_id"],
                "event_type": _rng.choice(["WORKFLOW_TRANSITION", "MAKER_CHECKER_DECISION", "TOOL_CALL"]),
                "actor_type": _rng.choice(["EMPLOYEE", "AGENT", "SYSTEM"]),
            }
        )
    return events


def main() -> None:
    out_dir = Path(__file__).parent / "generated"
    out_dir.mkdir(exist_ok=True)

    customers = generate_customers(200)
    accounts = generate_accounts(customers, 300)
    employees = generate_employees(50)
    requests = generate_service_requests(customers, 200)
    risk_alerts = generate_risk_alerts(requests, 50)
    audit_events = generate_audit_events(requests, 200)

    datasets = {
        "customers.json": customers,
        "accounts.json": accounts,
        "employees.json": employees,
        "service_requests.json": requests,
        "risk_alerts.json": risk_alerts,
        "audit_events.json": audit_events,
    }
    for filename, data in datasets.items():
        (out_dir / filename).write_text(json.dumps(data, indent=2))
        print(f"wrote {len(data)} records to {out_dir / filename}")


if __name__ == "__main__":
    main()
