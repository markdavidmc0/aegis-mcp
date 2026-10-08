# ADR-006: Polymorphic Resource Leases & Multi-Domain Verifiers (Generalizing Beyond Software Agents)

* **Date:** 2026-10-08  
* **Status:** PROPOSED (TARGET: v0.0.1-BETA)  
* **Context:**
  `spec_v0-0-1-alpha.md` couples the platform to Python software engineering workflows:
  1. Concurrency is restricted to filesystem paths (`FileLease`).
  2. Static analysis assumes Python ASTs (`ASTProjector` with stdlib `ast`).
  3. Quality control (`GraderPipeline`) hardcodes `pytest`, `ruff`, and cyclomatic complexity limits.
  4. Security guardrails target filesystem patterns (`tests/`, `subprocess`, `pty`).

  If deployed for non-software enterprise workloads (Finance, Legal, SecOps, Supply Chain), the engine breaks: it cannot lock database rows, API entity records, or cloud roles, and it cannot evaluate business-rule invariants. Furthermore, Section 7's Welsh-Powell scheduling performs static resource partition concurrency rather than exploratory solution-space optimization (hypothesis tree search with verifier-guided pruning).

* **Decision:**
  1. **Polymorphic `ResourceLease` Model:**
     Replace disk-path-specific `FileLease` with universal `ResourceLease` referencing canonical resource URNs:
     - Software Domain: `urn:aegis:resource:file:src/control_plane/blackboard.py`
     - Financial Operations: `urn:aegis:resource:entity:ledger_account_acct_402`
     - Cloud / SecOps: `urn:aegis:resource:iam:aws_role_arn_prod`
     - Database Records: `urn:aegis:resource:row:orders:ord_992182`
  2. **Pluggable Domain Verifiers (`DomainVerifier` Protocol):**
     Abstract `GraderPipeline` into a polymorphic evaluation harness where tasks declare their verification protocol:
     - `DeterministicCodeVerifier`: `pytest`, `ruff`, compiler gates (`cargo`, `tsc`).
     - `DeterministicSchemaVerifier`: Pydantic model validation, SQL constraint checks, API contract assertions.
     - `PolicyComplianceVerifier`: Declarative OPA/Rego policy rules against business inputs.
     - `DeterministicIdempotencyVerifier`: Double-execution dry-run ensuring zero side-effect drift.
  3. **Hierarchical Context Compaction & Active Distillation:**
     Upgrade Section 6 from a passive flat CAS cache to an active context distiller:
     - When $H_{\text{ctx}} < 0.70$, execute deterministic AST/semantic compaction: prune completed turns, distill verified interface contracts, and store raw trajectories in L1 CAS (`BlobVault`) while retaining active summary state on `TaskBlackboard`.
  4. **Speculative Parallel Solution-Space Exploration:**
     Extend Section 7 scheduling beyond non-conflicting FIFO lanes to support speculative hypothesis search:
     - Allow orchestrators to spawn $K$ competing candidate branches for high-uncertainty tasks.
     - Evaluate branches against the target domain's `DomainVerifier`.
     - Winning branch acquires the commit lock and commits to the blackboard; losing branches are evicted.

* **Alternatives Rejected:**
  - *Maintaining Software-Only Scope:* Rejected. Limits commercial TAM exclusively to coding tools, ignoring enterprise demand for autonomous operations across ERP, CRM, and financial reconciliation.
  - *Generic Unchecked Parallelism:* Rejected. Spawning competing agent rollouts without deterministic verifiers causes runaway token consumption with no convergence guarantees.

* **Key Artifacts:**
  - `src/control_plane/schemas.py` (`ResourceLease`, `ResourceKind`)
  - `src/evaluation/grader_pipeline.py` (`DomainVerifier`, `DeterministicSchemaVerifier`)
  - `src/context/compactor.py` (Active context compaction engine)
  - `src/control_plane/scheduler.py` (`SpeculativeBranchScheduler`)
  - `architecture/spec_v0-0-1-alpha.md`
  - `architecture/MIGRATION_PLAN.md`
