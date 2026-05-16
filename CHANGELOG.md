# Changelog

All notable changes to the Healthcare Compliance Guardrail are documented here.

Format: [Keep a Changelog](https://keepachangelog.com/en/1.0.0/)
Versioning: [Semantic Versioning](https://semver.org/)

---

## [1.0.0] — 2026-04-05

### Added
- `guardrail_middleware(agent_fn, agent_id, raw_input)` — single-call wrapper for any async agent function
- PHI input scan — regex detection of 8 HIPAA Safe Harbor identifiers
- PHI masking — replaces detected identifiers with typed tokens (e.g., `[SSN]`, `[DOB]`, `[PHONE]`)
- JCAHO checkpoint — GPT-4o LLM-as-judge PASS/FAIL gate with rationale before agent execution
- PHI output scan — post-execution re-scan of LLM response for PHI leakage
- Output masking — re-sanitizes response before delivery if PHI detected in output
- Append-only `guardrail_audit_log` (PostgreSQL + asyncpg; SQLite for local dev)
  - SHA-256 input hash — never raw PHI stored
  - 14 distinct audit event types across full execution lifecycle
- `GuardrailMiddleware` class + `AuditRecord` Pydantic model
- `audit/models.py` — GuardrailAuditEvent Pydantic model
- `audit/logger.py` — append-only asyncpg writer (never raises on audit failure)
- `audit/queries.py` — `get_execution_trail()`, `get_phi_detection_summary()`, `get_block_rate_by_agent()`, `get_compliance_summary()`
- `audit/migrations/001_create_guardrail_audit_log.sql`
- Compliance framework alignment table: HIPAA 45 CFR §164.312(b), HIPAA 45 CFR §164.312(e), JCAHO NPSG.01.01.01, HIPAA Privacy Rule, HITRUST CSF 11.a
- PHI identifier coverage table (8 of 18 Safe Harbor identifiers; NER roadmap documented)
- `.env.example`

---

## [Unreleased]

### Planned
- Full 18-identifier PHI coverage via Microsoft Presidio NER
- Pluggable rule engine for custom compliance policies per agent
- HITRUST CSF control mapping layer
- Real-time PHI detection via AWS Comprehend Medical
- LangSmith tracing integration for production observability
