"""Append-only audit logger for guardrail execution events."""
import os
import json
import logging
import asyncpg
from typing import Optional
from .models import GuardrailAuditEvent, GuardrailAuditEventType

logger = logging.getLogger(__name__)


class GuardrailAuditLogger:
    """
    Append-only PostgreSQL audit logger.
    Complements the existing SQLite audit record in main.py.
    Stores input_hash only — never raw PHI — per 45 CFR §164.312(b).
    Never raises — a failed audit write must never cause a guardrail bypass.
    """

    def __init__(self, dsn: Optional[str] = None) -> None:
        self.dsn = dsn or os.getenv("DATABASE_URL", "")
        self._pool: Optional[asyncpg.Pool] = None

    async def init(self) -> None:
        self._pool = await asyncpg.create_pool(self.dsn, min_size=1, max_size=5)

    async def close(self) -> None:
        if self._pool:
            await self._pool.close()

    async def log(self, event: GuardrailAuditEvent) -> None:
        if not self._pool:
            logger.warning("GuardrailAuditLogger not initialized — event dropped: %s", event.event_type)
            return
        try:
            async with self._pool.acquire() as conn:
                await conn.execute(
                    """
                    INSERT INTO guardrail_audit_log (
                        id, created_at, event_type, execution_id, agent_id,
                        input_hash, phi_identifiers_detected, phi_masked,
                        jcaho_passed, jcaho_rationale, action_blocked,
                        block_reason, output_safe, latency_ms, error_detail, metadata
                    ) VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14,$15,$16)
                    """,
                    event.id, event.created_at, event.event_type.value,
                    event.execution_id, event.agent_id, event.input_hash,
                    event.phi_identifiers_detected, event.phi_masked,
                    event.jcaho_passed, event.jcaho_rationale,
                    event.action_blocked, event.block_reason,
                    event.output_safe, event.latency_ms, event.error_detail,
                    json.dumps(event.metadata) if event.metadata else None,
                )
        except Exception as e:
            logger.error("Guardrail audit write failed [%s]: %s", event.execution_id, e)

    async def log_action_blocked(
        self,
        execution_id: str,
        agent_id: str,
        block_reason: str,
        input_hash: str,
        jcaho_rationale: Optional[str] = None,
    ) -> None:
        await self.log(GuardrailAuditEvent(
            event_type=GuardrailAuditEventType.ACTION_BLOCKED,
            execution_id=execution_id,
            agent_id=agent_id,
            input_hash=input_hash,
            action_blocked=True,
            block_reason=block_reason,
            jcaho_passed=False,
            jcaho_rationale=jcaho_rationale,
        ))

    async def log_compliant_delivered(
        self,
        execution_id: str,
        agent_id: str,
        input_hash: str,
        phi_masked: bool,
        phi_identifiers: list[str],
        latency_ms: int,
    ) -> None:
        await self.log(GuardrailAuditEvent(
            event_type=GuardrailAuditEventType.COMPLIANT_RESPONSE_DELIVERED,
            execution_id=execution_id,
            agent_id=agent_id,
            input_hash=input_hash,
            phi_masked=phi_masked,
            phi_identifiers_detected=phi_identifiers,
            jcaho_passed=True,
            output_safe=True,
            latency_ms=latency_ms,
        ))


audit_logger = GuardrailAuditLogger()
