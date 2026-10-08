# ADR-008: Dual-Interface Topology: FastMCP Agent Gateway & Typer Platform Cockpit

* **Date:** 2026-10-08  
* **Status:** PROPOSED (TARGET: v0.0.1-BETA)  
* **Context:**
  Section 9 of `spec_v0-0-1-alpha.md` defined only four minimal FastMCP tool stubs (`aegis_acquire_lease`, `aegis_read_ast_skeleton`, `aegis_query_facet`, `aegis_slice_blob`) and listed a one-sentence placeholder for a CLI (`src/interfaces/cli.py`).
  
  This leaves critical interface contracts undefined:
  1. **Caller & Transport Ambiguity:** The spec does not distinguish between autonomous agent consumers (invoking tool primitives over JSON-RPC) and human/CI operators (driving session lifecycles, benchmarks, and daemon processes over POSIX shell).
  2. **Incomplete Agent Toolset:** Autonomous workers in long-horizon TDD loops lack tools to release leases (`aegis_release_lease`), execute sandboxed code (`aegis_execute_code`), and trigger targeted test verifiers (`aegis_run_verifier`) directly through the MCP interface.
  3. **Lack of Operational Control Plane Cockpit:** The CLI lacks concrete subcommands to initialize blackboards, inspect real-time context health ($H_{\text{ctx}}$), run offline OPA policy dry-runs, launch golden dataset eval benchmarks (ADR-007), and start server daemons.

* **Decision:**
  1. **Codify the Dual-Interface Topology:**
     Partition the platform's external surface into two discrete, non-overlapping interface layers:
     - **FastMCP Agent Gateway (`src/interfaces/mcp_server.py`):** The programmatic interface consumed exclusively by autonomous agent LLMs over `stdio` (local subprocess) or `SSE` (remote HTTP). Exposes 7 atomic tool primitives divided into Concurrency, Context Virtualization, and Sandbox Execution.
     - **Typer Platform Cockpit (`src/interfaces/cli.py`):** The administrative and CI/CD command-line interface consumed by human engineers, automated orchestrators, and pipeline runners.
  2. **Standardize the 7 FastMCP Tool Primitives:**
     - `aegis_acquire_lease(resource_urns: list[str], ttl_seconds: int = 300, allow_test_mutation: bool = False) -> LeaseResult`: Atomic concurrency acquisition.
     - `aegis_release_lease(lease_urn: str) -> bool`: Explicit lease relinquishment.
     - `aegis_read_ast_skeleton(file_path: str) -> ASTSymbolDigest`: Zero-token structural inspection of type signatures.
     - `aegis_query_facet(facet_name: str) -> str`: PRD and architectural constraint lookup.
     - `aegis_slice_blob(blob_urn: str, offset: int = 0, length: int = 2000) -> str`: Streaming retrieval from Content-Addressed Storage.
     - `aegis_execute_code(code_snippet: str, backend: "monty" | "gvisor") -> ExecutionResult`: Safe isolated script execution.
     - `aegis_run_verifier(target_test: str) -> VerifierResult`: Targeted test suite execution inside the ephemeral sandbox.
  3. **Standardize the 5 Typer CLI Command Groups:**
     - `aegis session [start|status|abort]`: Lifecycle management and terminal blackboard inspection.
     - `aegis context [health|compact]`: $H_{\text{ctx}}$ real-time monitoring and manual memory distillation.
     - `aegis policy [check]`: Offline OPA policy dry-run with explicit diagnostic deny reasons.
     - `aegis eval [run]`: Golden benchmark regression execution with Logfire spans (`eval.local_harness`) and CI exit codes (ADR-007).
     - `aegis serve [mcp|control-plane]`: Daemons supporting both `stdio` and `sse` transports.

* **Alternatives Rejected:**
  - *Unified Single-Protocol Surface:* Rejected because LLMs communicate via structured JSON-RPC tool calls, whereas CI runners and human operators require POSIX exit codes, formatted terminal tables, and shell flags.
  - *Relying on Generic Third-Party MCP Adapters:* Rejected to preserve native binding to `TaskBlackboard`, `FileLeaseManager`, and `OPAPolicyEngine`.

* **Key Artifacts:**
  - `src/interfaces/mcp_server.py` (FastMCP Gateway)
  - `src/interfaces/cli.py` (Typer CLI Cockpit)
  - `architecture/review_v0-0-1-alpha.md` (Gap 10)
  - `architecture/MIGRATION_PLAN.md` (Phase 7)
