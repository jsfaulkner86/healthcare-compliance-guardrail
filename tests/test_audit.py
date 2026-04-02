"""Tests for healthcare compliance guardrail audit layer."""
import pytest
from datetime import datetime
from unittest.mock import AsyncMock
from audit.models import GuardrailAuditEvent, GuardrailAuditEventType
from audit.logger import GuardrailAuditLogger


def test_audit_event_model():
    event = GuardrailAuditEvent(
        event_type=GuardrailAuditEventType.ACTION_BLOCKED,
        execution_id="EXEC-001",
        agent_id="clinical-triage-agent",
        input_hash="abc123sha256",
        action_blocked=True,
        block_reason="JCAHO checkpoint failed: out-of-scope clinical recommendation",
        phi_identifiers_detected=["SSN", "DOB"],
        phi_masked=True,
    )
    assert event.id is not None
    assert event.action_blocked is True
    assert "SSN" in event.phi_identifiers_detected


@pytest.mark.asyncio
async def test_logger_never_raises_without_pool():
    logger = GuardrailAuditLogger(dsn="postgresql://test")
    logger._pool = None
    await logger.log(GuardrailAuditEvent(
        event_type=GuardrailAuditEventType.GUARDRAIL_ERROR,
        execution_id="EXEC-FAIL",
        error_detail="Test failure",
    ))


@pytest.mark.asyncio
async def test_logger_writes_compliant_delivered():
    logger = GuardrailAuditLogger(dsn="postgresql://test")
    mock_conn = AsyncMock()
    mock_pool = AsyncMock()
    mock_pool.acquire.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
    mock_pool.acquire.return_value.__aexit__ = AsyncMock(return_value=False)
    logger._pool = mock_pool
    await logger.log_compliant_delivered(
        execution_id="EXEC-001",
        agent_id="prior-auth-agent",
        input_hash="sha256hashhere",
        phi_masked=True,
        phi_identifiers=["MRN"],
        latency_ms=342,
    )
    mock_conn.execute.assert_called_once()
