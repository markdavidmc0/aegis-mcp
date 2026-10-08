# ADR-003: Deterministic Concurrency Control via Leases & Graph Coloring DAG Scheduling

* **Date:** 2026-09-29  
* **Status:** RATIFIED  
* **Context:** When multiple subagents or background workers execute concurrently across a monorepo, uncoordinated file edits cause dirty writes, merge conflicts, and invalid AST states.
* **Decision:** Implement a two-tiered concurrency architecture:
  1. **Atomic In-Memory File Leases (`FileLeaseManager`):** File-level mutual exclusion locks with TTL expiration, owner verification, and explicit `allow_test_mutation` gating.
  2. **Welsh-Powell Graph Coloring Scheduler (`ConflictGraphDAGScheduler`):** Conflict graph $G=(V, E)$ where vertices are task sessions and edges represent overlapping `target_files` (capped at 1–5 files per task). Tasks assigned the same color execute in parallel non-conflicting lanes; conflicting tasks are serialized automatically.
* **Alternatives Rejected:**
  - *Git-merge / optimistic concurrency:* Rejected because agents cannot reliably resolve semantic merge conflicts autonomously.
  - *Monolithic single-agent serialization:* Rejected due to unacceptable latency bottlenecks in multi-agent workflows.
* **Key Artifacts:** `src/control_plane/lease_manager.py`, `src/control_plane/scheduler.py`, Section 4 & 7 of `architecture/spec - v0-0-1-alpha.md`.
