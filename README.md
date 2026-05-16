<div align="center">

<br />

# 🛡️ Healthcare Compliance Guardrail

**Every healthcare AI team builds this from scratch.**
**PHI check here. Disclaimer there. Regex on the output. Hope for the best.**
**That's not a compliance posture.**

This is the **compliance middleware layer** that wraps any healthcare agent —
PHI scan, JCAHO gate, LLM execution, output scan, append-only audit trail —
in a single `await guardrail_middleware(agent_fn, input)` call.

<br />

[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=flat-square&logo=python&logoColor=white)](https://python.org)
[![LangChain](https://img.shields.io/badge/LangChain-Middleware%20Chain-000000?style=flat-square)](https://langchain.com)
[![HIPAA](https://img.shields.io/badge/HIPAA-45%20CFR%20%C2%A7164.312(b)-0EA5E9?style=flat-square)]()
[![JCAHO](https://img.shields.io/badge/JCAHO-NPSG%20Checkpoint-6E93B0?style=flat-square)]()
[![HITRUST](https://img.shields.io/badge/HITRUST-CSF%2011.a%20Aligned-22c55e?style=flat-square)]()
[![License](https://img.shields.io/badge/License-MIT-gray?style=flat-square)](LICENSE)

<br />

[Architecture](#system-architecture) · [HIPAA Threat Model](#hipaa-threat-model) · [PHI Coverage](#phi-identifier-coverage) · [Compliance Alignment](#compliance-framework-alignment) · [Quick Start](#local-development)

<br />

</div>

---

## The Problem With "Bolt-On" Compliance

I've reviewed healthcare AI implementations across 12 enterprise health systems. The compliance posture looks the same at almost all of them:

> A regex strip on the input. A disclaimer appended to the output. Maybe a log to a flat file. An assumption that the LLM won't hallucinate something clinically dangerous. No audit trail. No JCAHO review gate. No way to prove what the system did if a patient is harmed.

This isn't compliance. It's the appearance of compliance.

When a healthcare AI system produces a hallucinated diagnosis, routes PHI to a non-BAA LLM vendor, or takes a clinical action outside its authorized scope — "we had a regex" is not a defense.

This guardrail is infrastructure-grade compliance: **input PHI masking → JCAHO gate → agent execution → output scan → append-only audit** — wrapping *any* agent without modifying it.

---

## One-Line Integration

```python
from main import guardrail_middleware

# Wrap any agent function — no changes to the underlying agent required
result = await guardrail_middleware(
    agent_fn=my_clinical_agent,
    agent_id="clinical-triage-agent",
    raw_input="Patient presenting with...",
)
```

That's it. PHI masking, JCAHO compliance gate, audit record, and output scan all fire automatically.

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
│       ▼ yes                                                      │
│  [PHI Masking]            replace with [PHI_TYPE] tokens         │
│       │                                                          │
│       ▼ (clean or masked input)                                  │
│  [JCAHO Checkpoint]       LLM-as-judge: PASS / FAIL              │
│       │ FAIL?                                                    │
│       ▼                                                          │
│  🚫 [ACTION BLOCKED]      rationale returned; execution halted   │
│       │ PASS                                                     │
│       ▼                                                          │
│  [Agent Execution]        agent_fn called with sanitized input   │
│       │                                                          │
│       ▼                                                          │
│  [PHI Output Scan]        check for PHI leakage in LLM response  │
│       │ PHI in output?                                           │
│       ▼ yes                                                      │
│  [Output Masking]         re-sanitize before delivery            │
│       │                                                          │
│       ▼                                                          │
│  [Audit Record Written]   SHA-256 hash · PostgreSQL append-only  │
│       │                                                          │
│       ▼                                                          │
│  ✅ Compliant Response Delivered                                  │
└─────────────────────────────────────────────────────────────────┘
          │ PostgreSQL append-only guardrail_audit_log
          ▼ (SHA-256 hash only — never raw PHI)
┌─────────────────────────────────────────────────────────────────┐
│  guardrail_audit_log                                             │
└─────────────────────────────────────────────────────────────────┘
```

### Core Design Principles

- **Guardrail is a wrapper, not a component** — the underlying agent is unchanged. Wrap any `agent_fn(input) -> output` and compliance is enforced without touching agent code.
- **Input hash, never raw content** — the audit log stores SHA-256 of raw input only. Satisfies HIPAA audit trail requirements without creating a secondary PHI repository.
- **A failed audit write never bypasses the guardrail** — if Postgres is unavailable, the guardrail still runs and blocks non-compliant actions. The audit log is a record, not a gate.
- **JCAHO checkpoint is LLM-as-judge** — GPT-4o with a strict clinical safety prompt. Handles nuanced cases that regex alone misses — scope violations, hallucinated clinical guidance, and unauthorized actions.

---

## Use This With Your Existing Agents

This guardrail wraps any agent in this portfolio (or yours):

| Agent | Integration Point |
|---|---|
| [`clinical-triage-agent`](https://github.com/jsfaulkner86/clinical-triage-agent) | Wrap the triage classification call |
| [`agentic-healthcare-ops`](https://github.com/jsfaulkner86/agentic-healthcare-ops) | Wrap prior auth LangGraph pipeline before Availity submission |
| [`clinical-rag-agent`](https://github.com/jsfaulkner86/clinical-rag-agent) | Wrap the query synthesis step |
| [`pph-risk-scoring-agent`](https://github.com/jsfaulkner86/pph-risk-scoring-agent) | Wrap the intervention recommendation node |
| Your custom agent | Any `async def agent_fn(input: str) -> str` |

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

Current regex coverage (8 of 18 HIPAA Safe Harbor identifiers). Full 18-identifier coverage requires NER — see roadmap.

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

> Full 18-identifier coverage: AWS Comprehend Medical or spaCy `en_core_med7`. See roadmap.

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

Every guardrail execution writes an immutable event trail. No silent operations.

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
| `get_phi_detection_summary()` | Most frequent PHI identifier types — guides coverage roadmap |
| `get_block_rate_by_agent()` | Which agents are producing non-compliant outputs |
| `get_compliance_summary()` | Aggregate KPIs: PHI detection rate, block rate, JCAHO failure rate |

---

## Technology Stack

| Layer | Technology | Rationale |
|---|---|---|
| **Middleware Framework** | LangChain | Chain composition for PHI scan → JCAHO check → agent → output scan |
| **PHI Detection** | Regex (8 identifiers) + Presidio (roadmap) | Regex for deterministic patterns; Presidio NER for names, dates, geographies |
| **JCAHO Review** | OpenAI GPT-4o (LLM-as-judge) | PASS/FAIL compliance gate with rationale |
| **Audit Store** | PostgreSQL + asyncpg (production) + SQLite (local dev) | PostgreSQL for production; SQLite for zero-infrastructure local testing |
| **Language** | Python 3.11+ | Async-native; Pydantic v2; type hints throughout |

---

## Repository Structure

```
healthcare-compliance-guardrail/
├── main.py                         # GuardrailMiddleware class + AuditRecord
├── requirements.txt
├── .env.example
│
├── audit/
│   ├── models.py                   # GuardrailAuditEvent Pydantic model (14 event types)
│   ├── logger.py                   # Append-only asyncpg PostgreSQL writer
│   ├── queries.py                  # PHI summary, block rate by agent, compliance KPIs
│   └── migrations/
│       └── 001_create_guardrail_audit_log.sql
│
└── tests/
    └── test_audit.py
```

---

## Known Failure Modes

Production healthcare AI needs an honest failure mode table. Here's mine.

| Failure Mode | Impact | Mitigation |
|---|---|---|
| JCAHO checkpoint LLM latency | +500–1500ms per agent invocation | Cache JCAHO verdicts for identical input hashes; tune prompt for speed |
| Regex false positives (phone-like numbers) | PHI masking on non-PHI content | Context-window validation around match before masking |
| NER-detectable PHI passes regex scan | Partial PHI leakage | Presidio integration is the roadmap fix for this gap |
| SQLite audit log in production | Concurrency issues under load | Migrate to PostgreSQL `guardrail_audit_log` via `audit/logger.py` |

---

## Local Development

```bash
git clone https://github.com/jsfaulkner86/healthcare-compliance-guardrail
cd healthcare-compliance-guardrail
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env

# Initialize audit log
psql $DATABASE_URL -f audit/migrations/001_create_guardrail_audit_log.sql

python main.py
pytest tests/ -v
```

---

## Roadmap

- [ ] Full 18-identifier PHI coverage via Presidio NER
- [ ] Pluggable rule engine for custom compliance policies per agent
- [ ] HITRUST CSF control mapping layer
- [ ] Real-time PHI detection via AWS Comprehend Medical
- [ ] LangSmith tracing integration for production observability

---

## If You're Building Healthcare AI

If this pattern is useful to you, a ⭐ helps others find it.

If you're building clinical AI and need a compliance architecture that will hold up to a HIPAA audit — this is the kind of infrastructure I design at [The Faulkner Group](https://thefaulknergroupadvisors.com).

> ⚠️ See [DISCLAIMER.md](./DISCLAIMER.md) for important limitations on PHI coverage, JCAHO checkpoint reliability, and production deployment requirements.

---

<div align="center">

*Part of The Faulkner Group's healthcare agentic AI portfolio → [github.com/jsfaulkner86](https://github.com/jsfaulkner86)*

*Built from 14 years and 12 Epic enterprise health system deployments.*

</div>
