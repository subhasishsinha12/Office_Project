-- BankAI Core + BranchOne — target PostgreSQL schema (§44)
--
-- This is the schema of record. The Phase-0/1 prototype (apps/branchone_api)
-- keeps ServiceRequest state in-process for review-diff simplicity (see
-- apps/branchone_api/store.py); wiring SQLAlchemy models to this DDL is a
-- mechanical follow-up that does not change bankai_core or workflow.

CREATE TABLE customer (
    customer_id VARCHAR(20) PRIMARY KEY,
    name VARCHAR(200) NOT NULL,
    customer_type VARCHAR(30) NOT NULL, -- INDIVIDUAL | PARTNERSHIP | COMPANY | TRUST
    pan_masked VARCHAR(20),
    mobile_masked VARCHAR(20),
    email_masked VARCHAR(100),
    kyc_status VARCHAR(20) NOT NULL DEFAULT 'PENDING',
    data_owner VARCHAR(50) NOT NULL DEFAULT 'RETAIL_OPERATIONS', -- data governance (§36)
    system_of_record VARCHAR(50) NOT NULL DEFAULT 'CBS',
    sensitivity VARCHAR(20) NOT NULL DEFAULT 'RESTRICTED',
    access_classification VARCHAR(20) NOT NULL DEFAULT 'PII',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE account (
    account_id VARCHAR(20) PRIMARY KEY,
    customer_id VARCHAR(20) NOT NULL REFERENCES customer(customer_id),
    account_type VARCHAR(30) NOT NULL, -- SAVINGS | CURRENT | LOAN | FD
    status VARCHAR(20) NOT NULL DEFAULT 'ACTIVE',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE employee (
    employee_id VARCHAR(20) PRIMARY KEY,
    name VARCHAR(200) NOT NULL,
    role VARCHAR(40) NOT NULL, -- BRANCH_MAKER | BRANCH_CHECKER | BRANCH_MANAGER | ...
    branch_code VARCHAR(10) NOT NULL,
    active BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE TABLE role (
    role_code VARCHAR(40) PRIMARY KEY,
    description VARCHAR(200) NOT NULL
);

CREATE TABLE service (
    service_code VARCHAR(40) PRIMARY KEY,
    domain VARCHAR(40) NOT NULL,
    description VARCHAR(200) NOT NULL
);

CREATE TABLE service_request (
    request_id VARCHAR(30) PRIMARY KEY,
    customer_id VARCHAR(20) NOT NULL REFERENCES customer(customer_id),
    service_code VARCHAR(40) NOT NULL REFERENCES service(service_code),
    subservice VARCHAR(40),
    intent_code VARCHAR(60),
    channel VARCHAR(20) NOT NULL DEFAULT 'BRANCH',
    state VARCHAR(40) NOT NULL DEFAULT 'DRAFT',
    maker_required BOOLEAN NOT NULL DEFAULT TRUE,
    checker_required BOOLEAN NOT NULL DEFAULT TRUE,
    authentication_status VARCHAR(20) NOT NULL DEFAULT 'PENDING',
    documents_status VARCHAR(20) NOT NULL DEFAULT 'NOT_REQUIRED',
    policy_validation_status VARCHAR(20) NOT NULL DEFAULT 'PENDING',
    risk_status VARCHAR(20) NOT NULL DEFAULT 'PENDING',
    risk_class VARCHAR(10) NOT NULL DEFAULT 'GREEN',
    policy_rule_id VARCHAR(60),
    proposed_value_json JSONB,
    idempotency_key VARCHAR(64) NOT NULL UNIQUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE request_relationship (
    parent_request_id VARCHAR(30) NOT NULL REFERENCES service_request(request_id),
    child_request_id VARCHAR(30) NOT NULL REFERENCES service_request(request_id),
    dependency_type VARCHAR(20) NOT NULL DEFAULT 'SEQUENTIAL', -- SEQUENTIAL | PARALLEL
    PRIMARY KEY (parent_request_id, child_request_id)
);

CREATE TABLE document (
    document_id VARCHAR(30) PRIMARY KEY,
    request_id VARCHAR(30) NOT NULL REFERENCES service_request(request_id),
    document_type VARCHAR(60) NOT NULL,
    storage_reference VARCHAR(200) NOT NULL,
    uploaded_by VARCHAR(20) NOT NULL,
    uploaded_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE document_extraction (
    extraction_id VARCHAR(30) PRIMARY KEY,
    document_id VARCHAR(30) NOT NULL REFERENCES document(document_id),
    field_name VARCHAR(60) NOT NULL,
    field_value TEXT,
    confidence NUMERIC(4,3) NOT NULL,
    verification_required BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE TABLE document_verification (
    verification_id VARCHAR(30) PRIMARY KEY,
    document_id VARCHAR(30) NOT NULL REFERENCES document(document_id),
    verified_by VARCHAR(20) NOT NULL,
    verification_result VARCHAR(20) NOT NULL, -- PASSED | FAILED | MISMATCH
    notes TEXT,
    verified_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE authentication (
    authentication_id VARCHAR(30) PRIMARY KEY,
    request_id VARCHAR(30) NOT NULL REFERENCES service_request(request_id),
    method VARCHAR(20) NOT NULL, -- OTP | IN_PERSON | VIDEO_KYC
    result VARCHAR(20) NOT NULL,
    performed_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE consent (
    consent_id VARCHAR(30) PRIMARY KEY,
    customer_id VARCHAR(20) NOT NULL REFERENCES customer(customer_id),
    purpose VARCHAR(100) NOT NULL,
    granted_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    expires_at TIMESTAMPTZ
);

CREATE TABLE workflow_step (
    step_id VARCHAR(30) PRIMARY KEY,
    request_id VARCHAR(30) NOT NULL REFERENCES service_request(request_id),
    step_name VARCHAR(60) NOT NULL,
    target_state VARCHAR(40) NOT NULL,
    required BOOLEAN NOT NULL DEFAULT TRUE,
    sequence_no INT NOT NULL
);

CREATE TABLE regulation (
    rule_id VARCHAR(60) PRIMARY KEY,
    regulator VARCHAR(60) NOT NULL,
    regulation_name VARCHAR(200) NOT NULL,
    circular VARCHAR(100),
    clause VARCHAR(20),
    status VARCHAR(20) NOT NULL, -- FINAL | DRAFT | INTERNAL | SUPERSEDED
    publication_date DATE NOT NULL,
    effective_from DATE NOT NULL,
    effective_until DATE,
    supersedes VARCHAR(60) REFERENCES regulation(rule_id),
    customer_type VARCHAR(30) NOT NULL DEFAULT 'ALL',
    account_type VARCHAR(30) NOT NULL DEFAULT 'ALL',
    service_code VARCHAR(40) NOT NULL REFERENCES service(service_code),
    document_requirement_json JSONB,
    authentication VARCHAR(20) NOT NULL DEFAULT 'OTP',
    maker_required BOOLEAN NOT NULL DEFAULT TRUE,
    checker_required BOOLEAN NOT NULL DEFAULT TRUE,
    approval_authority VARCHAR(40) NOT NULL DEFAULT 'BRANCH_MANAGER',
    permitted_channel_json JSONB,
    cbs_action VARCHAR(60),
    sla_hours INT NOT NULL DEFAULT 24,
    retention_rule VARCHAR(20) NOT NULL DEFAULT '7_YEARS',
    notification_rule VARCHAR(60),
    source_reference VARCHAR(200)
);

CREATE TABLE policy_rule (
    policy_rule_id VARCHAR(30) PRIMARY KEY,
    description VARCHAR(200) NOT NULL,
    condition_expression TEXT NOT NULL, -- serialized decision-table condition
    maker_required BOOLEAN NOT NULL,
    checker_required BOOLEAN NOT NULL,
    kyc_revalidation VARCHAR(20) NOT NULL DEFAULT 'NOT_REQUIRED'
);

CREATE TABLE risk_flag (
    risk_flag_id VARCHAR(30) PRIMARY KEY,
    request_id VARCHAR(30) NOT NULL REFERENCES service_request(request_id),
    risk_score INT NOT NULL,
    risk_class VARCHAR(10) NOT NULL,
    reasons_json JSONB,
    raised_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE fraud_alert (
    fraud_alert_id VARCHAR(30) PRIMARY KEY,
    request_id VARCHAR(30) NOT NULL REFERENCES service_request(request_id),
    reasons_json JSONB,
    requires_enhanced_review BOOLEAN NOT NULL DEFAULT TRUE,
    raised_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    resolved_by VARCHAR(20),
    resolution VARCHAR(20) -- CONFIRMED_FRAUD | FALSE_POSITIVE
);

CREATE TABLE approval (
    approval_id VARCHAR(30) PRIMARY KEY,
    request_id VARCHAR(30) NOT NULL REFERENCES service_request(request_id),
    employee_id VARCHAR(20) NOT NULL REFERENCES employee(employee_id),
    role VARCHAR(40) NOT NULL, -- MAKER | CHECKER | APPROVER
    decision VARCHAR(20) NOT NULL,
    previous_value TEXT,
    requested_value TEXT,
    reason TEXT,
    evidence_json JSONB,
    decided_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE cbs_action (
    cbs_action_id VARCHAR(30) PRIMARY KEY,
    request_id VARCHAR(30) NOT NULL REFERENCES service_request(request_id),
    tool_id VARCHAR(60) NOT NULL,
    idempotency_key VARCHAR(64) NOT NULL UNIQUE,
    authorization_checks_json JSONB NOT NULL,
    initiated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE cbs_response (
    cbs_response_id VARCHAR(30) PRIMARY KEY,
    cbs_action_id VARCHAR(30) NOT NULL REFERENCES cbs_action(cbs_action_id),
    txn_id VARCHAR(30) NOT NULL,
    success BOOLEAN NOT NULL,
    before_state_json JSONB,
    after_state_json JSONB,
    message VARCHAR(200),
    received_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE audit_event (
    event_id VARCHAR(30) PRIMARY KEY,
    event_type VARCHAR(40) NOT NULL,
    actor VARCHAR(40) NOT NULL,
    actor_type VARCHAR(20) NOT NULL, -- EMPLOYEE | CUSTOMER | AGENT | SYSTEM
    subject_id VARCHAR(30),
    action VARCHAR(60) NOT NULL,
    decision VARCHAR(30),
    previous_value TEXT,
    requested_value TEXT,
    reason TEXT,
    evidence_json JSONB,
    occurred_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE notification (
    notification_id VARCHAR(30) PRIMARY KEY,
    request_id VARCHAR(30) NOT NULL REFERENCES service_request(request_id),
    channel VARCHAR(20) NOT NULL, -- SMS | EMAIL | PUSH
    sent_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE sla (
    sla_id VARCHAR(30) PRIMARY KEY,
    request_id VARCHAR(30) NOT NULL REFERENCES service_request(request_id),
    target_hours INT NOT NULL,
    breached BOOLEAN NOT NULL DEFAULT FALSE
);

CREATE TABLE escalation (
    escalation_id VARCHAR(30) PRIMARY KEY,
    request_id VARCHAR(30) NOT NULL REFERENCES service_request(request_id),
    reason TEXT NOT NULL,
    escalated_to VARCHAR(40) NOT NULL,
    escalated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE ai_agent (
    agent_id VARCHAR(40) PRIMARY KEY,
    agent_name VARCHAR(100) NOT NULL,
    agent_class VARCHAR(20) NOT NULL, -- ADVISORY | TRANSACTIONAL
    business_owner VARCHAR(60) NOT NULL,
    technical_owner VARCHAR(60) NOT NULL,
    version VARCHAR(20) NOT NULL,
    risk_level VARCHAR(10) NOT NULL,
    approval_required BOOLEAN NOT NULL DEFAULT FALSE,
    deployment_status VARCHAR(20) NOT NULL DEFAULT 'ACTIVE',
    last_review DATE NOT NULL
);

CREATE TABLE ai_model (
    model_id VARCHAR(60) PRIMARY KEY,
    model_name VARCHAR(100) NOT NULL,
    provider_org VARCHAR(60) NOT NULL,
    version VARCHAR(20) NOT NULL,
    tier VARCHAR(30) NOT NULL,
    owner VARCHAR(60) NOT NULL,
    risk_class VARCHAR(10) NOT NULL,
    hosting_mode VARCHAR(20) NOT NULL,
    validation_status VARCHAR(20) NOT NULL,
    approval_status VARCHAR(20) NOT NULL,
    last_review DATE NOT NULL,
    retirement_status VARCHAR(20) NOT NULL DEFAULT 'ACTIVE'
);

CREATE TABLE ai_run (
    run_id VARCHAR(30) PRIMARY KEY,
    agent_id VARCHAR(40) NOT NULL REFERENCES ai_agent(agent_id),
    model_id VARCHAR(60) NOT NULL REFERENCES ai_model(model_id),
    input_hash VARCHAR(64) NOT NULL,
    response_hash VARCHAR(64) NOT NULL,
    confidence NUMERIC(4,3),
    decision VARCHAR(60),
    caller_id VARCHAR(40) NOT NULL,
    occurred_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE ai_tool (
    tool_id VARCHAR(60) PRIMARY KEY,
    tool_name VARCHAR(100) NOT NULL,
    mode VARCHAR(10) NOT NULL, -- READ | WRITE
    data_scope VARCHAR(60) NOT NULL,
    required_approval VARCHAR(20) NOT NULL,
    risk_level VARCHAR(10) NOT NULL,
    rate_limit_per_minute INT NOT NULL
);

CREATE TABLE ai_tool_call (
    tool_call_id VARCHAR(30) PRIMARY KEY,
    run_id VARCHAR(30) REFERENCES ai_run(run_id),
    tool_id VARCHAR(60) NOT NULL REFERENCES ai_tool(tool_id),
    agent_id VARCHAR(40) NOT NULL REFERENCES ai_agent(agent_id),
    authorized BOOLEAN NOT NULL,
    denial_reason VARCHAR(200),
    occurred_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE data_asset (
    data_asset_id VARCHAR(40) PRIMARY KEY,
    field_name VARCHAR(60) NOT NULL,
    table_name VARCHAR(60) NOT NULL,
    data_owner VARCHAR(60) NOT NULL,
    system_of_record VARCHAR(60) NOT NULL,
    sensitivity VARCHAR(20) NOT NULL,
    retention VARCHAR(20) NOT NULL,
    access_classification VARCHAR(20) NOT NULL
);

CREATE TABLE data_lineage (
    lineage_id VARCHAR(40) PRIMARY KEY,
    data_asset_id VARCHAR(40) NOT NULL REFERENCES data_asset(data_asset_id),
    source_system VARCHAR(60) NOT NULL,
    transformation VARCHAR(200),
    last_verified TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE vendor (
    vendor_id VARCHAR(30) PRIMARY KEY,
    vendor_name VARCHAR(100) NOT NULL,
    service_provided VARCHAR(200) NOT NULL,
    review_due_date DATE
);

CREATE TABLE model_validation (
    validation_id VARCHAR(30) PRIMARY KEY,
    model_id VARCHAR(60) NOT NULL REFERENCES ai_model(model_id),
    validated_by VARCHAR(60) NOT NULL,
    validation_date DATE NOT NULL,
    result VARCHAR(20) NOT NULL, -- PASS | FAIL | CONDITIONAL
    notes TEXT
);

CREATE INDEX idx_service_request_customer ON service_request(customer_id);
CREATE INDEX idx_service_request_state ON service_request(state);
CREATE INDEX idx_audit_event_subject ON audit_event(subject_id);
CREATE INDEX idx_regulation_service ON regulation(service_code, status);
