"""Read-side analytics for guardrail audit data."""
import os
import asyncpg
from datetime import datetime, timedelta
from typing import Optional


class GuardrailAuditQueryService:

    def __init__(self, dsn: Optional[str] = None) -> None:
        self.dsn = dsn or os.getenv("DATABASE_URL", "")
        self._pool: Optional[asyncpg.Pool] = None

    async def init(self) -> None:
        self._pool = await asyncpg.create_pool(self.dsn, min_size=1, max_size=3)

    async def close(self) -> None:
        if self._pool:
            await self._pool.close()

    async def get_execution_trail(self, execution_id: str) -> list[dict]:
        """Full event trail for a single agent invocation."""
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT * FROM guardrail_audit_log WHERE execution_id=$1 ORDER BY created_at ASC",
                execution_id,
            )
            return [dict(r) for r in rows]

    async def get_phi_detection_summary(
        self, since: Optional[datetime] = None
    ) -> list[dict]:
        """Most frequently detected PHI identifier types — use to prioritize regex coverage expansion."""
        since = since or (datetime.utcnow() - timedelta(days=30))
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT identifier, COUNT(*) AS detections
                FROM guardrail_audit_log,
                     UNNEST(phi_identifiers_detected) AS identifier
                WHERE created_at >= $1
                GROUP BY identifier ORDER BY detections DESC
                """,
                since,
            )
            return [dict(r) for r in rows]

    async def get_block_rate_by_agent(
        self, since: Optional[datetime] = None
    ) -> list[dict]:
        """Block rate by agent_id — identifies which agents are producing non-compliant outputs."""
        since = since or (datetime.utcnow() - timedelta(days=30))
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT agent_id,
                       COUNT(*) AS total_executions,
                       COUNT(*) FILTER (WHERE action_blocked = TRUE)  AS blocked,
                       ROUND(COUNT(*) FILTER (WHERE action_blocked = TRUE) * 100.0 / COUNT(*), 2) AS block_rate_pct
                FROM guardrail_audit_log
                WHERE event_type IN ('compliant_response_delivered','action_blocked') AND created_at >= $1
                GROUP BY agent_id ORDER BY block_rate_pct DESC
                """,
                since,
            )
            return [dict(r) for r in rows]

    async def get_compliance_summary(
        self, since: Optional[datetime] = None
    ) -> dict:
        """Aggregate compliance KPIs across all agents."""
        since = since or (datetime.utcnow() - timedelta(days=30))
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT
                    COUNT(*) FILTER (WHERE event_type='input_received')                  AS total_invocations,
                    COUNT(*) FILTER (WHERE event_type='phi_detected_input')              AS phi_detected_in_input,
                    COUNT(*) FILTER (WHERE event_type='phi_detected_output')             AS phi_detected_in_output,
                    COUNT(*) FILTER (WHERE event_type='action_blocked')                  AS actions_blocked,
                    COUNT(*) FILTER (WHERE event_type='compliant_response_delivered')    AS compliant_delivered,
                    COUNT(*) FILTER (WHERE event_type='jcaho_checkpoint_failed')         AS jcaho_failures
                FROM guardrail_audit_log WHERE created_at >= $1
                """,
                since,
            )
            return dict(row)
