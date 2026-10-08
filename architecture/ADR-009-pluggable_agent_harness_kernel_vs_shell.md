# ADR-009: Pluggable Agent Harness Topology: Kernel vs. Shell Architecture

* **Date:** 2026-10-08  
* **Status:** RATIFIED (TARGET: v0.1.0-ALPHA)  
* **Context:**
  `spec_v0-0-1-alpha.md` rigorously specifies platform governance primitives (monotonic blackboard state machines, atomic file leases, OPA policy guardrails, AST projection, and grader pipelines), but treats the actual inner agent reasoning loop (prompt assembly $\rightarrow$ LLM inference $\rightarrow$ tool call parsing $\rightarrow$ reflection/retry cycle) as an abstract black box.
  
  In the current codebase:
  - `src/orchestrator/runtime.py` (`AgentRuntimeOrchestrator`) implements a rudimentary mock execution loop (`_execute_agent_steps`) simulating step artifacts rather than driving a true LLM reasoning and tool-calling cycle.
  - `src/orchestrator/registry.py` (`AgentRegistry`) tracks capabilities, model tiers, and handoff delegation rules, but lacks a binding to an active execution harness.
  - `src/data_plane/worker.py` (`DataPlaneSandboxRunner`) executes code in Monty or gVisor, but does not drive the agent trajectory.

  When formalizing the agent execution harness for an enterprise platform, three architectural paradigms emerge:
  1. **Option A: Proprietary Built-In Harness (Build Your Own):** Code an end-to-end bespoke ReAct/reflection loop and streaming tool parser directly in `src/orchestrator/`.  
     *Trade-off:* High maintenance liability. Frontier LLMs (Claude 3.7/Sonnet, Gemini 2.5/Flash, GPT-4o) frequently modify tool-calling schemas, reasoning token delimiters (`<thought>`), and streaming protocols. The platform team ends up maintaining a brittle LLM client SDK rather than an enterprise governance control plane.
  2. **Option B: Bring-Your-Own Harness (BYOH / "Server Only"):** Expose solely the FastMCP server and OPA policy gate, forcing clients to supply external agent harnesses (Cursor, Claude Code, OpenCode, LangGraph).  
     *Trade-off:* Zero out-of-the-box governance for headless execution. In unattended CI/CD tickets, automated PR generation, or `v build` workflows, unguided client loops drift, violate blackboard invariants, or burn token budgets in infinite retry loops without platform mediation.
  3. **Option C: Pluggable Native Harness Engine ("Kernel vs. Shell"):** Adopt standard typed agent protocols (Pydantic AI / LiteLLM / FastMCP) for an opinionated built-in headless runner, while exposing an open FastMCP gateway for external developer agents.

* **Decision:**
  Adopt the **Kernel vs. Shell Architecture** (Option C), establishing an un-opinionated zero-trust governance kernel decoupled from pluggable execution shells:

  ```
                         INCEPTOS SPATIAL WORKBENCH
                                     │
                           RFC 6902 JSON Patches
                                     ▼
               +───────────────────────────────────────────+
               |        AEGIS CONTROL PLANE KERNEL         |
               |  (Blackboard, LeaseManager, OPA, Memory)  |
               +───────────────────────────────────────────+
                                     │
          ┌──────────────────────────┴──────────────────────────┐
          ▼                                                     ▼
  ┌───────────────────────────────┐             ┌───────────────────────────────┐
  │     BUILT-IN HARNESS RUNNER   │             │    EXTERNAL HARNESS CLIENTS   │
  │     ("The Native Shell")      │             │    ("Bring Your Own Agent")   │
  ├───────────────────────────────┤             ├───────────────────────────────┤
  │ • aegis run / orchestrator    │             │ • OpenCode CLI                │
  │ • Pydantic AI / Monty runtime │             │ • Cursor / Claude Code / Zed  │
  │ • Enforces 25-turn ceiling    │             │ • Custom LangGraph / CrewAI   │
  │ • Drives TDD state machine    │             │ • Connects via FastMCP stdio  │
  └───────────────────────────────┘             └───────────────────────────────┘
  ```

  1. **The Kernel (Governance & Security Invariants):**
     The Aegis Control Plane (`TaskBlackboard`, `FileLeaseManager`, `OPAPolicyEngine`, `GraderPipeline`) acts as the unbypassable Kernel. It remains agnostic to token-generation mechanics. It enforces:
     - Mutual exclusion via resource leases prior to mutation.
     - Static AST boundary compliance and cyclomatic complexity ceilings ($M \le 10$).
     - Strict 25-turn execution ceilings and token budgets ($B_t$).
     - Dual-tier sandboxed execution and post-flight grading verification.

  2. **The Native Shell (Built-In Turn-Key Runner):**
     For autonomous CI/CD pipelines, headless background tickets, and unattended `v build` execution:
     - Implement an opinionated, lightweight Pydantic AI / LiteLLM execution loop in `src/orchestrator/runtime.py` exposed via `aegis run`.
     - The native runner consumes `AgentSpec`, resolves authorized tools, queries `ModelFailoverRouter`, and automatically transitions `TaskBlackboard` through `ANALYSIS` $\rightarrow$ `TDD_INNER_LOOP` $\rightarrow$ `EVALUATING`.
     - Native harness execution operates entirely out-of-the-box without external CLI dependencies.

  3. **The Open Shell (First-Class FastMCP Ecosystem Gateway):**
     For interactive human-in-the-loop engineering across IDEs and local harnesses (OpenCode, Cursor, Zed, Claude Code):
     - The platform serves tools over FastMCP (`aegis serve mcp --transport stdio|sse`).
     - External agents discover and invoke Aegis primitives (`aegis_acquire_lease`, `aegis_read_ast_skeleton`, `aegis_execute_code`, `aegis_run_verifier`).
     - External harnesses drive their own reasoning and conversational loops, while the Aegis Kernel enforces zero-drift policy and lease compliance at the tool boundary.

* **Comparison of Candidate Harness Frameworks:**
  - **OpenCode Architecture:** Excellent developer-first local CLI pattern with native subagent configurations (`@architect`, `@tdd-builder`) and workspace isolation. In Aegis, OpenCode is supported as a first-class external client over FastMCP, while Aegis's internal subagent scoping model (`SubagentSkillScoping`) directly mirrors OpenCode's role topology.
  - **Pi 1.0 (Physical Intelligence):** Designed for multi-modal robotic trajectories and physical rollout policies. Incompatible with symbolic AST contracts and enterprise software workflows; rejected.
  - **Pydantic AI / FastMCP:** Sam Colvin's typed agent framework natively designed around Pydantic v2 (`ConfigDict(extra="forbid", frozen=True)`), Python 3.12+, and FastMCP. Directly matches Aegis's core domain models and validation architecture; chosen as the foundation for the native built-in runner.

* **Harness Capability Ownership Matrix:**
  | Harness Capability | Who Owns It? | How It’s Implemented in Aegis |
  | :--- | :--- | :--- |
  | **Tool Calling & Sandboxing** | Platform Core (Kernel) | FastMCP + Monty / gVisor (`src/data_plane/worker.py`) |
  | **State & Concurrency** | Platform Core (Kernel) | `TaskBlackboard` + `FileLeaseManager` |
  | **Safety & Policy Gating** | Platform Core (Kernel) | OPA / Rego guardrails (`policies/aegis_guardrails.rego`) |
  | **Default Headless Execution** | Built-in Native Harness (Shell) | Pydantic AI / LiteLLM loop in `src/orchestrator/runtime.py` via `aegis run` |
  | **Interactive Developer UI** | Ecosystem / Pluggable (Shell) | OpenCode, Cursor, Zed, InceptOS Canvas connecting over FastMCP |

* **Alternatives Rejected:**
  - *Proprietary Scratch-Built ReAct Engine:* Rejected due to severe ongoing maintenance costs following LLM provider schema drift.
  - *Server-Only (BYOH) Architecture:* Rejected because automated platform pipelines (CI/CD, unattended builds) require a reliable, turn-key runner that guarantees state machine convergence.

* **Key Artifacts:**
  - `src/orchestrator/runtime.py` (Pydantic AI native execution loop)
  - `src/interfaces/mcp_server.py` (FastMCP Gateway for external harnesses)
  - `src/interfaces/cli.py` (`aegis run` entry point)
  - `architecture/review_v0-0-1-alpha.md` (Gap 11)
  - `architecture/MIGRATION_PLAN.md` (Phase 8)
