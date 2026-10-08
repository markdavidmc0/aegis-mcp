# ADR-010: Durable Execution, Event-Sourced Agent Replay, and Unified Logfire Observability

* **Date:** 2026-10-08  
* **Status:** RATIFIED (TARGET: v0.1.0-ALPHA)  
* **Context:**
  Autonomous agent tasks in Aegis operate across extended execution horizons (up to the 25-turn ceiling specified in `spec_v0-0-1-alpha.md`). In the current codebase:
  1. `src/orchestrator/queue.py` implements an in-memory queue with an ephemeral checkpoint stub (`.checkpoint(...)`). If an execution worker crashes on Turn 18 of 25, or if a container is preempted or evicted, the entire execution context is lost.
  2. Re-running a failed or halted session from scratch forces the agent to re-invoke costly LLM inference calls and re-execute external tool mutations that may not be idempotent (e.g., branch creation, external API posts).
  3. While `logfire` is actively configured and instrumented across `src/control_plane/main.py`, `src/data_plane/worker.py`, and `src/orchestrator/runtime.py`, execution spans lack standard W3C `traceparent` context propagation across asynchronous queue boundaries, subprocesses, and ephemeral gVisor sandboxes. Observability is disjoint across distributed process boundaries.

* **Decision:**
  1. **Adopt Event-Sourced Durable State Checkpointing:**
     Transition `TaskBlackboard` state persistence to an append-only event log (`TaskCheckpointRecord`).
     - **Turn-Level Snapshots:** After every completed reasoning turn ($k \in [1, 25]$), the runtime writes an atomic checkpoint containing:
       - Current `ExecutionPhase` (`ANALYSIS`, `TDD_INNER_LOOP`, `EVALUATING`, etc.).
       - Cumulative conversation history (turns, thoughts, tool inputs, outputs).
       - Active `ResourceLease` holdings and TTL status.
       - Context health metrics ($H_{\text{ctx}}$, token usage $B_t$).
     - **Storage Backend:** Persistent Postgres event store backing `TaskBlackboardManager` in production, with an async write-ahead log (WAL) protocol and fallback in-memory ring-buffer for test harnesses.
  2. **Implement Tool-Call Memoization & Idempotency Keys:**
     - Every tool invocation dispatched by the native shell or external gateway is assigned a deterministic idempotency key:
       $$\text{Key} = \text{SHA256}(\text{session\_urn} \parallel \text{turn\_index} \parallel \text{tool\_name} \parallel \text{canonical\_args\_json})$$
     - During crash recovery or session resumption (`aegis session resume <urn>`), the execution engine executes in **Replay Mode**:
       - Completed turns and memoized tool results are replayed from the event log in microseconds without invoking LLMs or repeating side-effecting mutations.
       - Execution smoothly resumes live token generation exactly at turn $k+1$.
  3. **Standardize Unified Pydantic Logfire Observability Across All Boundaries:**
     - Enforce Pydantic Logfire as the mandatory operational telemetry standard across all platform components.
     - **W3C Distributed Trace Propagation:** Inject and extract `traceparent` headers across FastAPI HTTP requests, asynchronous durable queue payloads, and gVisor container environments.
     - **Structured Span Attributes:** All execution spans (`orchestrator.turn`, `policy.pdp_eval`, `sandbox.execution`, `grader.eval`) must include standardized OTel GenAI and Aegis attributes:
       - `aegis.session_urn`, `aegis.turn_index`, `aegis.phase`
       - `gen_ai.system`, `gen_ai.request.model`, `gen_ai.usage.input_tokens`, `gen_ai.usage.output_tokens`
       - `lease.urns`, `policy.decision`, `policy.deny_reasons`
     - Keep static complexity metrics confined to CI linters (`ruff`), reserving Logfire runtime spans strictly for operational latencies, token consumption, error rates, and state transitions.

* **Alternatives Rejected:**
  - *Adopting Heavyweight External Workflow Orchestrators (Temporal / Cadence):* Rejected because embedding a full external Temporal cluster introduces substantial infrastructure overhead, complex gRPC worker daemons, and language-crossing serialization impedance. Event-sourced blackboard checkpoints in PostgreSQL deliver identical turn resumption with zero external cluster dependencies.
  - *Stateless Re-Execution from Scratch:* Rejected because frontier LLM costs, rate-limiting risks, and non-idempotent tool side-effects make full-task restarts unviable in production.

* **Key Artifacts:**
  - `src/orchestrator/checkpoint.py` (Event-sourced state models & replay coordinator)
  - `src/control_plane/blackboard.py` (WAL persistence integration)
  - `src/orchestrator/telemetry_enricher.py` (W3C traceparent Logfire context propagator)
  - `architecture/review_v0-0-1-alpha.md` (Gap 12)
