# ADR-012: Autonomous Git Worktree Virtualization and Branch Hygiene Engine

* **Date:** 2026-10-08  
* **Status:** RATIFIED (TARGET: v0.1.0-ALPHA)  
* **Context:**
  ADR-003 and ADR-006 establish concurrency control via `FileLeaseManager` and `ResourceLease` URNs, locking specific file paths (e.g. `urn:aegis:lease:src/control_plane/blackboard.py`).
  
  However, this leaves a severe operational hazard in actual development:
  1. **Working Directory Contamination:** If autonomous agents execute directly within the developer's primary workspace working tree, in-flight mutations collide with the human engineer's active edits in Cursor/Zed, pollute uncommitted local stashes, and dirty compiler/runtime artifact directories (`.venv`, `node_modules`, `__pycache__`, `target/`).
  2. **Speculative Execution Collisions:** When the DAG scheduler launches concurrent speculative lanes (e.g. evaluating two distinct architectural refactoring paths), shared working tree files cause build artifact corruption and race conditions.
  3. **Dirty Aborts:** When an agent hits the 25-turn ceiling, aborts on policy violations, or fails verification gates, leaving partially mutated files in the working directory requires tedious manual git recovery (`git reset --hard`, `git clean -fd`).

* **Decision:**
  1. **Formalize Ephemeral Worktree Virtualization (`src/orchestrator/worktree.py`):**
     Every agent session or speculative execution branch is provisioned with a dedicated, isolated **Git Worktree**:
     $$\text{Worktree Path} = \text{base\_repo} / \text{.aegis/worktrees} / \text{session\_urn\_hash}$$
     - Provisioned on-demand via `git worktree add -b aegis/task-{session_id} <path> <base_commit>`.
     - Completely separates file modification, virtualenvs, test runner state, and compiler outputs from the developer's active workspace.
  2. **Lifecycle and Atomic Merge Invariants:**
     - **Isolation Phase:** The agent reads context, acquires `ResourceLeases`, modifies source code, and executes gVisor/Monty test runners strictly inside its private worktree.
     - **Quality Gate Certification:** Only when the `GraderPipeline` (Tier 1 verifiers + Tier 2 AST complexity + Tier 3 Jev arbitration) passes 100% does the platform stage an atomic commit.
     - **Reconciliation & Fast-Forward Merge:** The platform cherry-picks or merges `aegis/task-{session_id}` into the target integration branch.
     - **Zero-Pollution Cleanup:** Upon session completion, cancellation, or unrecoverable error, `git worktree remove --force <path>` and `git branch -D aegis/task-{session_id}` are executed automatically. The human developer's active tree is never dirtied.
  3. **Worktree Cache Deduplication:**
     - Share read-only package caches (`uv cache`, `cargo cache`, `npm cache`) via symlinked or mounted read-only cache volumes to ensure sub-second worktree spin-up times.

* **Alternatives Rejected:**
  - *Direct Working Directory Mutation with Stash Management:* Rejected because `git stash save` / `git stash pop` frequently encounters merge conflicts, destroys staged states, and breaks if the IDE is holding open file handles.
  - *Full Repository Clones:* Rejected due to disk footprint and clone latency (cloning 500MB+ repos on every turn/task creates unbearable I/O overhead compared to lightweight zero-copy git worktrees).

* **Key Artifacts:**
  - `src/orchestrator/worktree.py` (Git worktree lifecycle manager)
  - `src/orchestrator/runtime.py` (Worktree provisioning hook in agent run loop)
  - `architecture/review_v0-0-1-alpha.md` (Gap 14)
