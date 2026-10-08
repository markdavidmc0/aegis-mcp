# ADR-001: Dual-Layer Spatial / Control Plane Decoupling & Boundary Protocol

* **Date:** 2026-09-15  
* **Status:** RATIFIED  
* **Context:** Traditional agentic frameworks (e.g., standard LangChain/CrewAI chat loops) suffer from "agent entropy" and stochastic drift because user steering and code execution share an unstructured text conversation channel.  
* **Decision:** Decouple the system into two discrete layers separated by an RFC 6902 JSON Patch boundary:
  1. **InceptOS (Public Spatial Workbench):** A visual, human-in-the-loop canvas (React Flow / CopilotKit) where the architect pins immutable intent, AST constraints, and invariant seeds.
  2. **Aegis Engine (Internal Control Plane):** A deterministic, zero-trust backend execution engine operating via atomic `TaskBlackboard` state machines.
* **Alternatives Rejected:**
  - *Direct Chat-to-Code Loop:* Rejected due to high prompt drift, hallucinated scope expansion, and loss of structural boundaries.
  - *Full State-Blob Sync over WebSockets:* Rejected due to race conditions and lack of transactional field assertions.
* **Key Artifacts:** Section 1 & 2 of `architecture/spec - v0-0-1-alpha.md`.
