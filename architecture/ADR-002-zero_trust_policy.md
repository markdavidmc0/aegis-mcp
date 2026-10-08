# ADR-002: Declarative Zero-Trust Policy Enforcement via OPA/Rego

* **Date:** 2026-09-22  
* **Status:** RATIFIED  
* **Context:** Agents executing tool calls (file writes, process execution, bash commands) require rigorous safety boundaries to prevent sandbox escape, path traversal (`../`), and tampering with tests to fake test passage.
* **Decision:** Situate an Open Policy Agent (OPA) Wasm/Rego Policy Enforcement Point (PEP) at the Control Plane boundary enforcing five strict gates before dispatching to the Data Plane:
  1. *4-Tuple Identity Integrity* (`actor_id`, `agent_id`, `cost_centre_id`, `session_id`)
  2. *Path Containment Check* (Normalized relative path within workspace root)
  3. *Lease Matching* (Target path matches active exclusive `FileLease`)
  4. *Protected Test Mutation Guardrail* (Prohibits modifying `tests/` without explicit `allow_test_mutation=True`)
  5. *Forbidden AST Imports Denylist* (Blocks `subprocess`, `pty`, `socket`, `ctypes`)
* **Alternatives Rejected:**
  - *Application-level Python if/else checks:* Rejected because governance rules cannot be dynamically audited, hot-reloaded, or decoupled from application deployments.
  - *Post-execution container sandboxing alone:* Rejected because prevention is required before untrusted instructions reach execution runtime.
* **Key Artifacts:** `policies/aegis_guardrails.rego`, Section 5 of `architecture/spec - v0-0-1-alpha.md`.
