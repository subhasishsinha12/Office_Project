# Document Automation Project #
## Overview ##
This project automates the generation of Word documents using data from an Excel file. The script reads data from an Excel spreadsheet and replaces placeholders in Word document templates with the actual data, saving the modified documents in a specified output directory. This is particularly useful for generating personalized documents such as affidavits, agreements, and declarations based on standardized templates.

---

## BankAI Core + BranchOne

This repository also contains a separate prototype: **BankAI Core**, a
bank-owned, governed AI platform, and **BranchOne**, its first agentic
banking application. It does not depend on, and is not depended on by,
the document automation project above.

- Start with `docs/ARCHITECTURE.md` — system architecture, trust boundary,
  registries, and the control-validation checklist.
- `bankai_core/` — AI Gateway, Model Router, Agent/Tool/Model registries,
  Regulatory Digital Twin + deterministic Rule Engine, guardrails, audit.
- `workflow/` — state machine + maker-checker engine.
- `cbs_adapter/` — generic core-banking adapter interface + mock CBS.
- `apps/branchone_api/` — FastAPI application wiring the above into the
  request lifecycle (Golden Demo 1: mobile number update, end to end).
- `data/schema.sql` — target PostgreSQL schema; `data/synthetic_data.py` —
  synthetic customers/accounts/employees/requests generator.
- `tests/` — automated proof of the control invariants (maker-checker
  cannot be bypassed, unauthorized tool calls are denied, prompt injection
  has no effect on binding policy, kill switch works).

Setup:

```bash
pip install -r requirements-bankai.txt
pytest                                   # run the control + golden-demo tests
uvicorn apps.branchone_api.main:app --reload   # run the API locally
```
