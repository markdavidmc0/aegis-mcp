# ADR-004: Embedding Gemma Integration & Scope Allocation

* **Date:** 2026-10-08  
* **Status:** APPROVED (STAGED FOR v0.0.1-BETA)  
* **Context:** Google DeepMind's Embedding Gemma introduces high-density bidirectional representations for code and text. We evaluated whether vector embeddings supersede the RFC 6902 JSON Patch state boundary between InceptOS and Aegis, and determined its release scope.  
* **Decision:**
  1. *Protocol Invariant:* Retain RFC 6902 JSON Patches for all control-plane state mutations. Continuous vector space cannot replace atomic, deterministic discrete state machine transitions or transactional OPA checks.
  2. *Scope Allocation:* Defer Embedding Gemma to `v0.0.1-Beta`. Keep Week 1 MVP (Tickets `TICK-001` through `TICK-012`) zero-dependency and stdlib-only.
  3. *Beta Application:* Use Embedding Gemma in `v0.0.1-Beta` for hierarchical PRD facet slicing (`src/context/facet_index.py`), measuring continuous cosine drift $\cos(\vec{v}_{\text{goal}}, \vec{v}_{\text{ast}})$ in $H_{\text{ctx}}$, and semantic coupling detection in `ConflictGraphDAGScheduler`.
* **Alternatives Rejected:**
  - *Replacing RFC 6902 with Embeddings:* Rejected due to stochastic drift, loss of transactional `test` operations, and non-deterministic policy evaluation.
  - *Incorporating Embedding Gemma into Week 1 MVP:* Rejected due to multi-gigabyte weight footprints destabilizing fast CI test suites (<1s inner loops).
* **Key Artifacts:** `architecture/spec - v0-0-1-alpha.md`, `architecture/MIGRATION_PLAN.md`.
