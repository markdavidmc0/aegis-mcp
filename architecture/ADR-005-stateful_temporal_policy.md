# ADR-005: Stateful Temporal Policy Evaluation via Trajectory Ingestion

* **Date:** 2026-10-08  
* **Status:** PROPOSED (TARGET: v0.0.1-BETA)  
* **Context:**
  AWS Strands Box introduced an OS-level sandbox governed by the Dogwood policy engine, which evaluates rules based on an agent's prior action sequences, execution history, and cumulative time-window limits (e.g. rate-capping notifications, requiring read before write).
  In Aegis v0.1.0-alpha, `policies/aegis_guardrails.rego` evaluates requests as memoryless, atomic snapshots (identity, path, lease, AST imports). While the `TaskBlackboard` tracks execution turns and retries, this temporal trajectory is not yet projected into the OPA/Rego input context, leaving sequential and rate-dependent safety rules unenforced at the policy boundary.

* **Decision:**
  1. **Retain OPA/Rego & Reject Dogwood:** Retain Open Policy Agent as the CNCF-standard, vendor-neutral declarative policy engine rather than adopting AWS-proprietary Dogwood.
  2. **Trajectory Ingestion into Policy Context:** Extend `PolicyEvaluationInput` (`src/control_plane/schemas.py`) and the Control Plane PEP to inject the agent's historical execution trajectory from `TaskBlackboard`:
     - `history.action_sequence`: Ordered list of preceding actions in the current session (e.g. `["read_ast_skeleton", "run_test"]`).
     - `history.sliding_window_counts`: Sliding window frequencies for sensitive verbs (e.g. tool calls per minute).
     - `history.failed_gate_attempts`: Cumulative count of gate rejections.
  3. **Temporal Rego Guardrails:** Codify sequence-prerequisite and sliding-window invariants inside `policies/aegis_guardrails.rego`:
     - *Sequence Prerequisite Invariant:* Mutating operations (`write_file`) require prior interface discovery (`read_ast_skeleton` or `read_file` present in `history.action_sequence`).
     - *Rate Limiting / Anomaly Invariant:* Deny operations if sliding window frequency exceeds configured threshold (e.g. $> 15$ tool calls / min).
     - *Repeated Violation Circuit Breaker:* Escalate session to `BLOCKED` if `failed_gate_attempts >= 3`.
  4. **Scope Staging:** The Week 1 MVP (`spec - v0-0-1-alpha.md`) remains focused on the 5 stateless structural gates. Trajectory ingestion and temporal Rego evaluation are formally staged under the `v0.0.1-Beta` milestone.

* **Alternatives Rejected:**
  - *Adopting AWS Strands Box / Dogwood Directly:* Rejected. Strands Box operates solely at the OS container layer without an intent inception workbench (InceptOS), AST static screening, or multi-agent DAG concurrency scheduling.
  - *Hardcoding Sequential Checks in Python Middleware:* Rejected. Violates separation of concerns; temporal policies must remain declarative, auditable, and hot-reloadable in Rego.
  - *Full Process Syscall Tracing for History:* Rejected due to high runtime virtualization overhead. Blackboard-level action history captures agent intent cleanly without kernel-level tracing lag.

* **Key Artifacts:**
  - `policies/aegis_guardrails.rego`
  - `src/control_plane/schemas.py` (`PolicyEvaluationInput.history`)
  - `src/control_plane/policy_engine.py`
  - `architecture/spec - v0-0-1-alpha.md`
  - `architecture/MIGRATION_PLAN.md`
