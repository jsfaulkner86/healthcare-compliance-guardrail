# Healthcare Compliance Guardrail

> **LangChain + Middleware** — The compliance layer every healthcare AI system needs, built as reusable infrastructure

[![Python](https://img.shields.io/badge/Python-3776AB?style=flat-square&logo=python&logoColor=white)]()
[![LangChain](https://img.shields.io/badge/LangChain-000000?style=flat-square)]()
[![HIPAA](https://img.shields.io/badge/HIPAA-Compliant-blue?style=flat-square)]()
[![Healthcare AI](https://img.shields.io/badge/Healthcare-AI-red?style=flat-square)]()

Built by [The Faulkner Group](https://thefaulknergroupadvisors.com) — designed from real HIPAA compliance requirements across enterprise Epic EHR deployments.

---

## Problem Statement

Most healthcare AI systems bolt compliance on as an afterthought — a regex check here, a disclaimer there. This creates compounding risk: PHI exposure in LLM API calls, hallucinated clinical guidance delivered to end users, and no audit trail to demonstrate what the system actually did.

This guardrail layer is the compliance infrastructure that wraps any healthcare agent. It intercepts inputs before they reach the LLM, enforces JCAHO compliance rules, scans outputs before delivery, and writes an immutable audit record on every execution — satisfying HIPAA 45 CFR §164.312(b) without requiring changes to the underlying agent.

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                   Incoming Agent Input                           │
│             raw clinical text · patient context                  │
└─────────────────────────────┬───────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                   Guardrail Middleware Layer                     │
│                                                                  │
│  [PHI Input Scan]         18-identifier regex + NER (roadmap)    │
│       │ PHI detected?                                            │
│       ▼ yes                                                       │
│  [PHI Masking]            replace with [PHI_TYPE] tokens          │
│       │                                                           │
│       ▼ (clean or masked input)                                   │
│  [JCAHO Checkpoint]       LLM-as-judge: PASS / FAIL              │
│       │ FAIL?                                                     │
│       ▼                                                           │
│  🚫 [ACTION BLOCKED]      rationale returned; execution halted    │
│       │ PASS                                                      │
│       ▼                                                           │
│  [Agent Execution]        agent_fn called with sanitized input    │
│       │                                                           │
│       ▼                                                           │
│  [PHI Output Scan]        check for PHI leakage in LLM response   │
│       │ PHI in output?                                            │
│       ▼ yes                                                       │
│  [Output Masking]         re-sanitize before delivery             │
│       │                                                           │
│       ▼                                                           │
│  [Audit Record Written]   SHA-256 hash · PostgreSQL append-only   │
│       │                                                           │
│       ▼                                                           │
│  ✅ Compliant Response Delivered                                   │
└─────────────────────────────────────────────────────────────────┘
          │ PostgreSQL append-only guardrail_audit_log
          ▼ (SHA-256 hash only — never raw PHI)
┌─────────────────────────────────────────────────────────────────┐
│  guardrail_audit_log                                              │
└─────────────────────────────────────────────────────────────────┘
```

### Core Design Principles

- **Guardrail is a wrapper, not a component** — the underlying agent function is unchanged. Wrap any `agent_fn(input) -> output` and compliance is enforced without modifying agent code.
- **Input hash, never raw content** — the audit log stores SHA-256 of raw input only. This satisfies the HIPAA audit trail requirement without creating a secondary PHI repository.
- **A failed audit write never bypasses the guardrail** — if Postgres is unavailable, the guardrail still runs and blocks non-compliant actions. The audit log is a record, not a gate.
- **JCAHO checkpoint is LLM-as-judge** — the compliance review is itself a GPT-4o call with a strict clinical safety prompt. This handles nuanced cases that regex alone misses.

---

## Repository Structure

```
healthcare-compliance-guardrail/
├── main.py                         # GuardrailMiddleware class + AuditRecord (SQLite)
├── requirements.txt
├── .env.example
│
├── audit/
│   ├── models.py                   # GuardrailAuditEvent Pydantic model (14 event types)
│   ├── logger.py                   # Append-only asyncpg PostgreSQL writer
│   ├── queries.py                  # PHI detection summary, block rate by agent, compliance KPIs
│   └── migrations/
│       └── 001_create_guardrail_audit_log.sql
│
└── tests/
    └── test_audit.py
```

---

## Technology Stack

| Layer | Technology | Rationale |
|---|---|---|
| **Middleware Framework** | LangChain | Chain composition for PHI scan → JCAHO check → agent → output scan |
| **PHI Detection** | Regex (8 identifiers) + Presidio (roadmap) | Regex for deterministic patterns; Presidio NER for names, dates, geographies |
| **JCAHO Review** | OpenAI GPT-4o (LLM-as-judge) | PASS/FAIL compliance gate with rationale — handles nuanced clinical scope violations |
| **Audit Store** | PostgreSQL + asyncpg (primary) + SQLite (local dev) | PostgreSQL for production; SQLite for zero-infrastructure local testing |
| **Language** | Python 3.11+ | Async-native; type hints throughout |

---

## HIPAA Threat Model

| Threat Vector | Risk | Guardrail Defense |
|---|---|---|
| PHI echo in LLM output | Model regurgitates patient identifiers | Output PHI scan + masking before response delivery |
| PHI in agent input | Clinical notes sent raw to LLM API | Input PHI detection + masking before LLM call |
| Audit trail gap | No record of agent execution | SHA-256 hashed input + append-only Postgres log per 45 CFR §164.312(b) |
| Hallucinated clinical guidance | LLM invents diagnoses, dosages, or treatment plans | JCAHO checkpoint — GPT-4o-as-judge blocks before execution |
| Out-of-scope agent action | Agent takes action beyond authorized clinical scope | Action classification + JCAHO PASS/FAIL gate |

---

## PHI Identifier Coverage

Current regex coverage (8 of 18 HIPAA Safe Harbor identifiers):

| Identifier | Pattern | Status |
|---|---|---|
| Social Security Number | `\d{3}-\d{2}-\d{4}` | ✅ |
| Date of Birth | MM/DD/YYYY | ✅ |
| Phone Number | US formats + E.164 | ✅ |
| Email Address | RFC 5322 | ✅ |
| Medical Record Number | `MRN: XXXXXXXX` | ✅ |
| ZIP Code | 5-digit + ZIP+4 | ✅ |
| IP Address | IPv4 | ✅ |
| Device Identifier | MAC address | ✅ |
| Full Name | NER required | 🔜 Roadmap |
| Geographic data (sub-ZIP) | NER required | 🔜 Roadmap |
| Other dates (admit, discharge) | Contextual | 🔜 Roadmap |
| Account / Certificate numbers | Domain patterns | 🔜 Roadmap |

> Full 18-identifier coverage requires NER — AWS Comprehend Medical or spaCy `en_core_med7`. See roadmap.

---

## Compliance Framework Alignment

| Control | Framework | Implementation |
|---|---|---|
| Audit controls | HIPAA 45 CFR §164.312(b) | SHA-256 input hash + timestamped `guardrail_audit_log` |
| Transmission security | HIPAA 45 CFR §164.312(e) | PHI masked before any LLM API call |
| Information integrity | JCAHO NPSG.01.01.01 | JCAHO checkpoint gate before agent execution |
| Minimum necessary | HIPAA Privacy Rule | PHI masked to token; raw content never stored or transmitted |
| Incident response | HITRUST CSF 11.a | All PHI detection and masking events logged with identifiers detected |
| Access control | HIPAA 45 CFR §164.312(a) | `agent_id` scoped per guardrail instance |

---

## Audit Event Lifecycle

```
input_received
    └── phi_scan_input
            └── phi_detected_input → phi_masked_input (if PHI found)
                    └── jcaho_checkpoint_started
                            └── jcaho_checkpoint_passed → agent_executed
                            │       └── phi_scan_output
                            │               └── phi_detected_output → phi_masked_output
                            │                       └── compliant_response_delivered
                            └── jcaho_checkpoint_failed → action_blocked
```

---

## Audit Analytics

| Query Method | Use Case |
|---|---|
| `get_execution_trail(execution_id)` | Full compliance trace for a single invocation |
| `get_phi_detection_summary()` | Most frequent PHI identifier types — guides regex coverage roadmap |
| `get_block_rate_by_agent()` | Which agents are producing non-compliant outputs |
| `get_compliance_summary()` | Aggregate KPIs: PHI detection rate, block rate, JCAHO failure rate |

---

## Integrating with Other Agents

This guardrail is designed to wrap any agent function:

```python
from main import guardrail_middleware

# Wrap any agent function
result = await guardrail_middleware(
    agent_fn=my_clinical_agent,
    agent_id="clinical-triage-agent",
    raw_input="Patient is presenting with...",
)
```

It integrates directly with the other agents in this portfolio:
- **clinical-triage-agent** — wrap the triage classification call
- **prior-auth-research-agent** — wrap before policy research fires
- **clinical-rag-agent** — wrap the query synthesis step
- **pph-risk-scoring-agent** — wrap the intervention recommendation node

---

## Known Failure Modes

| Failure Mode | Impact | Mitigation |
|---|---|---|
| JCAHO checkpoint LLM call latency | +500–1500ms added to every agent invocation | Cache JCAHO verdicts for identical input hashes; tune prompt for speed |
| Regex false positives (e.g., phone-like numbers) | PHI masking on non-PHI content | Context-window validation around match before masking |
| NER-detectable PHI (names, dates) passes regex scan | Partial PHI leakage | Presidio integration is the roadmap fix for this specific gap |
| SQLite audit log in production | Concurrency issues under load | Migrate to PostgreSQL `guardrail_audit_log` via `audit/logger.py` for production |

---

## Local Development

```bash
git clone https://github.com/jsfaulkner86/healthcare-compliance-guardrail
cd healthcare-compliance-guardrail
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env

psql $DATABASE_URL -f audit/migrations/001_create_guardrail_audit_log.sql

python main.py
pytest tests/ -v
```

---

## What's Next

- Full 18-identifier PHI coverage via Presidio NER
- Pluggable rule engine for custom compliance policies per agent
- HITRUST CSF control mapping layer
- Real-time PHI detection using AWS Comprehend Medical
- Migrate SQLite audit to PostgreSQL `guardrail_audit_log` by default

---

*Part of The Faulkner Group’s healthcare agentic AI portfolio → [github.com/jsfaulkner86](https://github.com/jsfaulkner86)*
