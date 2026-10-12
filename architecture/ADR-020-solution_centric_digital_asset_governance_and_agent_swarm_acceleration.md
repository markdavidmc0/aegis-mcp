# ADR-020: Solution-Centric Digital Asset Governance & Agent Swarm Acceleration

* **Date:** 2026-10-09  
* **Status:** RATIFIED (TARGET: v0.2.0-BETA)  
* **Context:**
  Section 4, 6, and 7 of `spec_v0-0-1-alpha.md` and ADR-003/ADR-006 formulate concurrency and asset governance around isolated file locks (`FileLease`) and single-agent execution pipelines.
  
  In enterprise deployments, autonomous systems operate not as lone code-editing scripts, but as **heterogeneous multi-agent swarms** collaborating across high-order digital assets. This creates three critical governance bottlenecks:
  1. **Asset Granularity & Solution-Centric Decoupling:** Modern enterprise digital assets extend far beyond single file paths: they encompass entire solutions—monorepo packages, API schemas, microservices, cloud infrastructure stacks, database schema migrations, and transactional ledgers. Locking single files causes deadlocks in multi-file refactoring, while uncoordinated asset edits cause solution-level architectural drift.
  2. **Agent Swarm Coordination & Dynamic Delegation:** Hierarchical agent swarms (e.g. `@orchestrator` delegating concurrently to `@architect`, `@tdd-builder`, `@test-engineer`, and `@frontend-dev`) lack structured, deterministic protocols for lease propagation, sub-lease delegation, and collaborative swarm acceleration. When multiple agents attempt to modify interconnected assets within a solution, race conditions emerge in dependency synchronization.
  3. **High-Throughput Swarm Acceleration:** Naive FIFO queueing and single-lane scheduling force subagents to serialize execution, inflating end-to-end wall-clock latency for multi-step feature delivery. Swarms require an accelerated execution protocol with optimistic dependency resolution, lease inheritance trees, and automated conflict mitigation.

* **Decision:**
  1. **Adopt Solution-Centric Digital Asset Governance:**
     - Elevate digital asset modeling from point file leases to **Solution Asset Clusters** identified by canonical `AegisUrn` hierarchies:
       - `urn:aegis:asset:solution:<solution_id>:<cluster_path>`
       - `urn:aegis:asset:contract:<package_name>:<interface_id>`
       - `urn:aegis:asset:data:<schema_namespace>:<migration_id>`
     - **Solution Asset Boundary Manifest:** Each solution defines an immutable boundary contract registering all constituent files, exported symbols, public APIs, and external dependencies.
     - **Coarse-to-Fine Lease Hierarchy:** Agents can acquire solution-level read leases while obtaining fine-grained exclusive write sub-leases on targeted modules, preventing whole-solution lockout while guaranteeing cross-module integrity.
  2. **Hierarchical Swarm Delegation & Sub-Lease Propagation:**
     - When a parent agent (e.g. `@orchestrator`) acquires a solution-level lease scope, it can atomically delegate scoped sub-leases to worker subagents (`@tdd-builder`, `@test-engineer`) using **Parent-Child Lease Inheritance Trees**:
       ```python
       class SwarmLeaseDelegation(BaseModel):
           """Strict Pydantic model for swarm lease inheritance and delegation."""
           model_config = ConfigDict(extra="forbid", frozen=True)

           parent_lease_urn: str = Field(description="Parent lease URN held by orchestrator.")
           delegated_agent_urn: str = Field(description="Target subagent URN receiving delegation.")
           asset_urns: list[str] = Field(description="Subset of asset URNs partitioned for subagent.")
           delegation_ttl_seconds: int = Field(default=300, ge=10, le=3600)
           isolation_barrier: bool = Field(default=True, description="Enforce sandboxed git worktree per subagent.")
       ```
     - Sub-leases automatically expire upon worker completion or parent task termination, preventing zombie resource locks across the swarm.
  3. **Agent Swarm Acceleration Protocol:**
     - **Concurrent Non-Interfering Execution:** Leverage Welsh-Powell graph coloring across solution asset dependency DAGs to schedule non-overlapping subagent tasks simultaneously across isolated Git worktrees.
     - **Optimistic State Staging & Fast-Path Rebase:** Worker subagents emit RFC 6902 JSON patch streams and worktree commits against local branch heads. The orchestrator validates patches against the solution contract via `GraderPipeline` and fast-forward rebases certified diffs into the parent branch.
     - **Automated Swarm Conflict Arbitration:** If two subagents in a swarm produce conflicting asset mutations, the orchestrator invokes a lightweight AST reconciliation engine to merge non-overlapping symbol deltas or halts execution for human-in-the-loop escalation.

* **Alternatives Rejected:**
  - *Fine-Grained File Locks Only:* Rejected because multi-file refactors and cross-package architectural invariants require atomic, solution-level visibility and coordination.
  - *Uncoordinated Free-For-All Swarms:* Rejected due to high risk of silent regressions, corrupted shared states, and race conditions during concurrent git staging.
  - *Static Single-Agent Serialization:* Rejected because serializing multi-agent workflows imposes prohibitive latency on complex enterprise software initiatives.

* **Key Artifacts:**
  - `src/control_plane/asset_governance.py` (Solution asset clusters & boundary manifest)
  - `src/orchestrator/swarm_coordinator.py` (Swarm delegation protocol & sub-lease hierarchy)
  - `src/control_plane/lease_manager.py` (Hierarchical lease trees and sub-lease inheritance)
  - `architecture/review_v0-0-1-alpha.md` (Gap 17)
  - `architecture/MIGRATION_PLAN.md` (Beta Roadmap Alignment)
