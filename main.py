import re
import json
import hashlib
import sqlite3
from datetime import datetime
from typing import Any, Optional
from pydantic import BaseModel
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate

# ── PHI IDENTIFIER PATTERNS (HIPAA 18 Identifiers) ────

PHI_PATTERNS = {
    "SSN": r"\b\d{3}-\d{2}-\d{4}\b",
    "DATE_OF_BIRTH": r"\b(0[1-9]|1[0-2])/(0[1-9]|[12]\d|3[01])/\d{4}\b",
    "PHONE": r"\b(\+1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b",
    "EMAIL": r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
    "MRN": r"\bMRN[-:\s]?\d{6,10}\b",
    "ZIP_CODE": r"\b\d{5}(-\d{4})?\b",
    "IP_ADDRESS": r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b",
    "DEVICE_ID": r"\b[0-9A-Fa-f]{2}(:[0-9A-Fa-f]{2}){5}\b"
}

# ── AUDIT RECORD MODEL ─────────────────────────────────

class AuditRecord(BaseModel):
    timestamp: str
    agent_id: str
    action: str
    input_hash: str
    phi_detected: list
    phi_masked: bool
    jcaho_check_passed: bool
    output_safe: bool
    notes: Optional[str] = None

# ── COMPLIANCE GUARDRAIL LAYER ─────────────────────────

class HealthcareComplianceGuardrail:

    def __init__(self, agent_id: str, db_path: str = "audit_trail.db"):
        self.agent_id = agent_id
        self.db_path = db_path
        self.llm = ChatOpenAI(model="gpt-4", temperature=0)
        self._init_audit_db()

    def _init_audit_db(self):
        conn = sqlite3.connect(self.db_path)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS audit_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT,
                agent_id TEXT,
                action TEXT,
                input_hash TEXT,
                phi_detected TEXT,
                phi_masked INTEGER,
                jcaho_check_passed INTEGER,
                output_safe INTEGER,
                notes TEXT
            )
        """)
        conn.commit()
        conn.close()

    # ── PHI DETECTION ──────────────────────────────────

    def detect_phi(self, text: str) -> list:
        detected = []
        for phi_type, pattern in PHI_PATTERNS.items():
            if re.search(pattern, text, re.IGNORECASE):
                detected.append(phi_type)
        return detected

    # ── PHI MASKING ────────────────────────────────────

    def mask_phi(self, text: str) -> str:
        masked = text
        replacements = {
            "SSN": "[SSN-REDACTED]",
            "DATE_OF_BIRTH": "[DOB-REDACTED]",
            "PHONE": "[PHONE-REDACTED]",
            "EMAIL": "[EMAIL-REDACTED]",
            "MRN": "[MRN-REDACTED]",
            "ZIP_CODE": "[ZIP-REDACTED]",
            "IP_ADDRESS": "[IP-REDACTED]",
            "DEVICE_ID": "[DEVICE-REDACTED]"
        }
        for phi_type, pattern in PHI_PATTERNS.items():
            masked = re.sub(pattern, replacements[phi_type], masked, flags=re.IGNORECASE)
        return masked

    # ── JCAHO CHECKPOINT ───────────────────────────────

    def jcaho_checkpoint(self, action: str, clinical_context: str) -> tuple[bool, str]:
        prompt = ChatPromptTemplate.from_messages([
            ("system", """You are a JCAHO compliance officer reviewing an 
            AI agent action in a healthcare setting. Determine if this action 
            meets JCAHO standards for patient safety, documentation, and care quality.
            Respond with PASS or FAIL followed by a one-sentence rationale."""),
            ("human", "Agent action: {action}\nClinical context: {context}")
        ])

        response = self.llm.invoke(prompt.format_messages(
            action=action,
            context=clinical_context
        ))

        result = response.content.strip()
        passed = result.upper().startswith("PASS")
        return passed, result

    # ── OUTPUT SAFETY CHECK ────────────────────────────

    def check_output_safety(self, output: str) -> tuple[bool, list]:
        phi_in_output = self.detect_phi(output)
        is_safe = len(phi_in_output) == 0
        return is_safe, phi_in_output

    # ── WRITE AUDIT RECORD ─────────────────────────────

    def write_audit_record(self, record: AuditRecord):
        conn = sqlite3.connect(self.db_path)
        conn.execute("""
            INSERT INTO audit_log 
            (timestamp, agent_id, action, input_hash, phi_detected, 
             phi_masked, jcaho_check_passed, output_safe, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            record.timestamp,
            record.agent_id,
            record.action,
            record.input_hash,
            json.dumps(record.phi_detected),
            int(record.phi_masked),
            int(record.jcaho_check_passed),
            int(record.output_safe),
            record.notes
        ))
        conn.commit()
        conn.close()

    # ── MAIN GUARDRAIL WRAPPER ─────────────────────────

    def run_with_compliance(self, agent_action: str, input_text: str, agent_fn) -> dict:
        print(f"\n🔒 COMPLIANCE LAYER ACTIVE — Agent: {self.agent_id}")

        # Step 1: Detect PHI in input
        phi_detected = self.detect_phi(input_text)
        phi_masked = len(phi_detected) > 0

        if phi_masked:
            print(f"⚠️  PHI detected: {phi_detected} — masking before LLM call")
            safe_input = self.mask_phi(input_text)
        else:
            safe_input = input_text

        # Step 2: JCAHO checkpoint before execution
        jcaho_passed, jcaho_rationale = self.jcaho_checkpoint(agent_action, safe_input)
        if not jcaho_passed:
            print(f"🚫 JCAHO CHECKPOINT FAILED: {jcaho_rationale}")
            return {"error": "Action blocked by JCAHO compliance checkpoint", "rationale": jcaho_rationale}

        print(f"✅ JCAHO checkpoint passed")

        # Step 3: Execute agent
        output = agent_fn(safe_input)

        # Step 4: Check output for PHI leakage
        output_safe, phi_in_output = self.check_output_safety(str(output))
        if not output_safe:
            print(f"🚫 PHI detected in output — masking: {phi_in_output}")
            output = self.mask_phi(str(output))

        # Step 5: Write immutable audit record
        record = AuditRecord(
            timestamp=datetime.utcnow().isoformat(),
            agent_id=self.agent_id,
            action=agent_action,
            input_hash=hashlib.sha256(input_text.encode()).hexdigest(),
            phi_detected=phi_detected,
            phi_masked=phi_masked,
            jcaho_check_passed=jcaho_passed,
            output_safe=output_safe,
            notes=jcaho_rationale
        )
        self.write_audit_record(record)
        print(f"📋 Audit record written — hash: {record.input_hash[:16]}...")

        return {"output": output, "compliant": True, "audit_record": record.dict()}

# ── MAIN ──────────────────────────────────────────────

if __name__ == "__main__":
    guardrail = HealthcareComplianceGuardrail(agent_id="prior-auth-agent-v1")

    # Simulate agent function
    def mock_agent(text: str) -> str:
        return f"Prior authorization recommendation generated based on: {text[:100]}..."

    # Test with PHI-laden input
    test_input = """
    Patient Jane Smith, DOB 03/15/1978, MRN: 8849201, 
    SSN: 234-56-7890, requesting prior auth for CPT 27447.
    Diagnosis: Severe osteoarthritis, conservative treatment failed.
    """

    result = guardrail.run_with_compliance(
        agent_action="Generate prior authorization recommendation",
        input_text=test_input,
        agent_fn=mock_agent
    )

    print("\n── RESULT ──")
    print(f"Output: {result.get('output')}")
    print(f"Compliant: {result.get('compliant')}")
