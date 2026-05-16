# Disclaimer

**Healthcare Compliance Guardrail**
The Faulkner Group | Version 1.0.0

---

## Not a Medical Device

This software is a **reference implementation and architectural demonstration** of a compliance middleware layer for healthcare AI agents. It is not a cleared or approved medical device, legal compliance instrument, or certified HIPAA compliance tool. It has not been submitted to or reviewed by the U.S. Food and Drug Administration, HHS Office for Civil Rights, or any other regulatory authority.

The PHI detection patterns, JCAHO compliance gate, audit log design, and output masking demonstrated in this repository are for architectural and educational purposes only. They are not a substitute for a formal HIPAA risk analysis, organizational compliance program, or legal review.

---

## Not Legal or Compliance Advice

All references to HIPAA (45 CFR Part 164), JCAHO/NPSG, HITRUST CSF, or other regulatory frameworks are for **architectural and informational reference only**. The Faulkner Group is not a law firm and does not provide legal advice. Consult qualified legal counsel and a certified HIPAA compliance officer before deploying this or any AI system in a regulated healthcare environment.

---

## PHI Coverage Limitations

This guardrail implements regex-based detection of **8 of the 18 HIPAA Safe Harbor identifiers**. It does not detect all PHI patterns. Specifically:

- Full patient names, provider names, and geographic data below ZIP code level require NER (Presidio, AWS Comprehend Medical, or equivalent)
- Account numbers, certificate numbers, and contextual date patterns (admission/discharge dates) are on the roadmap but not yet implemented
- This partial coverage must not be represented as full HIPAA Safe Harbor de-identification to any patient, regulator, or compliance auditor

Organizations requiring full 18-identifier de-identification must integrate NER-based PHI detection before production deployment.

---

## HIPAA and BAA Requirements

This codebase does not by itself make any system HIPAA-compliant. Organizations must:

- Conduct an independent HIPAA Security Rule risk analysis
- Execute Business Associate Agreements with OpenAI and all applicable vendors before processing PHI
- Confirm `HIPAA_MODE=true` is enforced in all production deployments
- Validate that SHA-256 hashing of raw input satisfies their organization's audit trail requirements under 45 CFR §164.312(b)

The Faulkner Group assumes no liability for PHI exposure, data breaches, HIPAA violations, or regulatory penalties arising from the use of this codebase.

---

## JCAHO Checkpoint Limitations

The JCAHO compliance gate uses GPT-4o as a judge. LLM-based judges can produce inconsistent verdicts, especially on edge cases involving nuanced clinical scope boundaries. This gate:

- Adds 500–1500ms latency per invocation
- Should be supplemented with deterministic rule checks for high-stakes clinical actions
- Must not be the sole governance control for any action with direct patient safety implications

---

## No Warranty

This software is provided **"as is"**, without warranty of any kind. In no event shall the authors or The Faulkner Group be liable for any claim, damages, or other liability — including but not limited to PHI exposure, compliance violations, patient harm, or regulatory penalties — arising from the use of this software.

See [LICENSE](./LICENSE) for full terms.

---

*The Faulkner Group provides healthcare IT architecture advisory services. For production deployment guidance, contact [john@thefaulknergroupadvisors.com](mailto:john@thefaulknergroupadvisors.com).*
