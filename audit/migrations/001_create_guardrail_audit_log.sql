-- Migration: 001_create_guardrail_audit_log
-- Audit log per HIPAA 45 CFR §164.312(b) — Information System Activity Review.
-- input_hash stores SHA-256 of raw input only — raw PHI must never be written here.
-- This table must have UPDATE and DELETE revoked on all application roles.

CREATE TABLE IF NOT EXISTS guardrail_audit_log (
    id                        UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at                TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    event_type                TEXT NOT NULL,
    execution_id              TEXT,          -- groups events for one agent invocation
    agent_id                  TEXT,
    input_hash                TEXT,          -- SHA-256 of raw input ONLY; never store raw content
    phi_identifiers_detected  TEXT[],        -- e.g. {"SSN","DOB","MRN"}
    phi_masked                BOOLEAN NOT NULL DEFAULT FALSE,
    jcaho_passed              BOOLEAN,
    jcaho_rationale           TEXT,
    action_blocked            BOOLEAN NOT NULL DEFAULT FALSE,
    block_reason              TEXT,
    output_safe               BOOLEAN,
    latency_ms                INTEGER,
    error_detail              TEXT,
    metadata                  JSONB
);

CREATE INDEX IF NOT EXISTS idx_guardrail_event_type    ON guardrail_audit_log (event_type);
CREATE INDEX IF NOT EXISTS idx_guardrail_execution_id  ON guardrail_audit_log (execution_id);
CREATE INDEX IF NOT EXISTS idx_guardrail_agent_id      ON guardrail_audit_log (agent_id);
CREATE INDEX IF NOT EXISTS idx_guardrail_blocked       ON guardrail_audit_log (action_blocked);
CREATE INDEX IF NOT EXISTS idx_guardrail_created_at    ON guardrail_audit_log (created_at DESC);

-- Revoke mutation access on application role
-- REVOKE UPDATE, DELETE ON guardrail_audit_log FROM app_role;

COMMENT ON TABLE guardrail_audit_log IS
    'HIPAA 45 CFR §164.312(b) audit log. Stores SHA-256 input hash only. Never raw PHI. Never UPDATE or DELETE rows.';
