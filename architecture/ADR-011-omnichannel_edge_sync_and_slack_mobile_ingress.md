# ADR-011: Omnichannel Edge Sync: Slack Mobile Ingress, Cross-Device Presence, and RFC 6902 Patch Streams

* **Date:** 2026-10-08  
* **Status:** PROPOSED (TARGET: v0.0.1-BETA)  
* **Context:**
  Enterprise software agents cannot operate as desktop-siloed command-line processes. Human supervisors frequently monitor and steer agents from mobile devices (e.g., Slack mobile, mobile browsers/PWA) while the agent is executing long-horizon tasks on desktop workstations or remote CI/CD clusters.
  
  In the current architecture:
  1. Interfaces are restricted to local/remote JSON-RPC (`FastMCP` in ADR-008) and POSIX terminal shell (`Typer CLI`).
  2. There is no asynchronous human-in-the-loop (HITL) notification bridge. When an agent requires human elevation (e.g. lease conflicts, test mutation unlock, or dangerous tool approval), execution either halts or aborts.
  3. There is no bidirectional synchronization mechanism between desktop workstations (InceptOS Spatial Workbench, Cursor, Zed) and mobile touchpoints, causing state drift and stale client views.

* **Decision:**
  1. **Slack Socket Mode Mobile Ingress Gateway (`src/interfaces/slack_gateway.py`):**
     - Deploy a bi-directional Slack integration using Slack Socket Mode (avoiding public inbound webhook ingress requirements for enterprise security compliance).
     - **HITL Interactive Escalations:** When `TaskBlackboard` transitions to `HUMAN_INTERVENTION_REQUIRED` or an agent requests an out-of-policy tool action:
       - Aegis posts an interactive Slack Block Kit message with rich Markdown diffs, AST violation summaries, and atomic actions (`[Approve]`, `[Reject]`, `[Steer]`).
       - Supervisors can approve, reject, or provide steering instructions directly from the Slack mobile application.
     - **Mobile Steering Prompts:** Slack slash commands (`/aegis steer <session_urn> "focus on edge cases"`) inject real-time guidance directly into the active session blackboard.
  2. **Cross-Device State Sync via RFC 6902 JSON Patch Streams over SSE / WebSockets:**
     - Extend `src/control_plane/mcp_router.py` with a real-time reactive event stream (`GET /api/v1/sessions/{session_urn}/stream`).
     - State transitions, blackboard field changes, tool logs, and agent artifacts are broadcast as standardized RFC 6902 JSON Patches (`add`, `replace`, `remove`).
     - Desktop clients (InceptOS Desktop, IDE extensions) and mobile web clients (InceptOS Mobile PWA) subscribe to the identical stream, achieving sub-100ms cross-device synchronization.
  3. **Optimistic Mutation & Monotonic Vector Clock Reconciliation:**
     - Mobile clients can initiate modifications (prompt tweaks, turn ceiling adjustments, emergency cancellation) while experiencing intermittent cellular connectivity.
     - Every blackboard patch includes the target blackboard revision number ($v_k$).
     - The Aegis Control Plane evaluates incoming patches against the current state version. If $v_{\text{client}} < v_{\text{server}}$, the Control Plane performs three-way operational transformation or rejects the patch with `CONCURRENCY_CONFLICT`, notifying the mobile client to rebase its state.

* **Alternatives Rejected:**
  - *Periodic Polling over HTTP:* Rejected due to high mobile battery drain, latency lag during time-critical supervisor approvals, and excessive server load.
  - *Direct WhatsApp / SMS Gateways:* Rejected because enterprise auditability, RBAC permissioning, and cryptographic identity attribution are natively provided by enterprise Slack workspaces (Slack SSO + Keycloak OIDC mappings).

* **Key Artifacts:**
  - `src/interfaces/slack_gateway.py` (Slack Socket Mode bot & Block Kit interactive renderer)
  - `src/control_plane/patch_stream.py` (RFC 6902 SSE/WebSocket broadcast manager)
  - `architecture/review_v0-0-1-alpha.md` (Gap 13)
