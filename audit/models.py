"""Audit event models for the Healthcare Compliance Guardrail."""
import uuid
from datetime import datetime
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


class GuardrailAuditEventType(str, Enum):
    INPUT_RECEIVED = "input_received"
    PHI_SCAN_INPUT = "phi_scan_input"
    PHI_DETECTED_INPUT = "phi_detected_input"
    PHI_MASKED_INPUT = "phi_masked_input"
    JCAHO_CHECKPOINT_STARTED = "jcaho_checkpoint_started"
    JCAHO_CHECKPOINT_PASSED = "jcaho_checkpoint_passed"
    JCAHO_CHECKPOINT_FAILED = "jcaho_checkpoint_failed"
    AGENT_EXECUTED = "agent_executed"
    PHI_SCAN_OUTPUT = "phi_scan_output"
    PHI_DETECTED_OUTPUT = "phi_detected_output"
    PHI_MASKED_OUTPUT = "phi_masked_output"
    COMPLIANT_RESPONSE_DELIVERED = "compliant_response_delivered"
    ACTION_BLOCKED = "action_blocked"
    GUARDRAIL_ERROR = "guardrail_error"


class GuardrailAuditEvent(BaseModel):
    """Immutable audit record for a single guardrail execution event."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = Field(default_factory=datetime.utcnow)
    event_type: GuardrailAuditEventType
    execution_id: Optional[str] = None     # groups all events for one agent invocation
    agent_id: Optional[str] = None
    input_hash: Optional[str] = None       # SHA-256 of raw input — never store raw PHI
    phi_identifiers_detected: Optional[list[str]] = None  # e.g. ["SSN", "DOB"]
    phi_masked: bool = False
    jcaho_passed: Optional[bool] = None
    jcaho_rationale: Optional[str] = None
    action_blocked: bool = False
    block_reason: Optional[str] = None
    output_safe: Optional[bool] = None
    latency_ms: Optional[int] = None
    error_detail: Optional[str] = None
    metadata: Optional[dict] = None


AUDIT_TABLE_DDL = """
CREATE TABLE IF NOT EXISTS guardrail_audit_log (
    id                        UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at                TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    event_type                TEXT NOT NULL,
    execution_id              TEXT,
    agent_id                  TEXT,
    input_hash                TEXT,          -- SHA-256 only; never raw content
    phi_identifiers_detected  TEXT[],
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

COMMENT ON TABLE guardrail_audit_log IS
    'Immutable audit log per 45 CFR §164.312(b). Stores input_hash only — never raw PHI content. Never UPDATE or DELETE rows.';
"""
