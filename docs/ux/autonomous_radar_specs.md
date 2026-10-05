# Aegis 24/7 Autonomous Radar & Durable Event Queue: UX & Interaction Specification

- **Target Persona:** Platform Operations Engineers, AI System Architects, Research Reviewers, and Security Officers.
- **Upstream Author:** `@ux-designer`
- **Downstream Implementer:** `@frontend-dev` (`apps/web/`)
- **Compliance Standard:** WCAG 2.2 Level AA
- **Status:** Baseline Approved Specification
- **Scope:** Durable Task Queue Dashboard & Autonomous Research & Self-Improvement Radar

---

## 1. Executive Layout Topology & Component Hierarchy

The Autonomous Radar & Durable Event Queue interface provides real-time streaming supervision, human-in-the-loop (HITL) gate evaluation, self-improving prompt optimization telemetry, and policy candidate proposal management.

```
+----------------------------------------------------------------------------------------------------+
| Global Radar Header (Continuous Loop Status, Queue Ingestion Rate, Active Cluster, Auth Context)   |
+------------------------------------+---------------------------------------------------------------+
| System Mode & Partition Selector   | Command Bar (Pause Queue, Trigger ArXiv Scan, Emergency Drain)|
| - Event Stream Partitions (0..7)   +---------------------------------------------------------------+
| - Radar Focus Areas (NLP, Rego)    | Live Health & Telemetry Strip                                 |
| - Safety Bounds (Circuit Breaker)  | [Status: Nominal] [Lag: 124ms] [Backpressure: 4%] [Logfire UI]|
+------------------------------------+---------------------------------------------------------------+
| Main Stage: Split Supervision Grid                                                                 |
| +---------------------------------------------------+--------------------------------------------+ |
| | Section 1: Durable Task Queue Dashboard           | Section 2: Autonomous Research Radar       | |
| | +-----------------------------------------------+ | +----------------------------------------+ | |
| | | Subpanel 1A: Stream Ingestion & Active Leases  | | | Subpanel 2A: ArXiv Continuous Scan Feed  | | |
| | | - Rate Meters (msgs/sec)                      | | | - Candidate Papers with Relevance Meta | | |
| | | - Active Consumer Pods & Leases Table         | | | - Triggered Automated Extraction RFCs  | | |
| | +-----------------------------------------------+ | +----------------------------------------+ | |
| | | Subpanel 1B: Checkpoint Resumption & Watermark | | | Subpanel 2B: Paper Summary RFC Cards   | | |
| | | - Offset Progress Bar & Epoch Pins            | | | - HITL Approval Gates (Approve/Reject) | | |
| | | - Stream Replay & Partition Rewind Trigger    | | | - Architectural Impact Radiance Score  | | |
| | +-----------------------------------------------+ | +----------------------------------------+ | |
| | | Subpanel 1C: HITL Paused Queue & Dead-Letter  | | | Subpanel 2C: DSPy Prompt Score Diffs   | | |
| | | - Quarantined Events requiring human sign-off | | | - Accuracy & Cost Delta Metrics        | | |
| | | - Dead-Letter Queue (DLQ) Inspector & Redrive | | | - Candidate Prompt Version Comparison  | | |
| | +-----------------------------------------------+ | +----------------------------------------+ | |
| |                                                   | | Subpanel 2D: OPA Policy Proposal Diff  | | |
| |                                                   | | - Auto-generated Rego Policy Candidate   | | |
| |                                                   | | - Interactive Unified/Split Diff Viewer  | | |
| |                                                   | +----------------------------------------+ | |
| +---------------------------------------------------+--------------------------------------------+ |
+----------------------------------------------------------------------------------------------------+
| Global Annunciator Strip (Aria-Live Stream Region, WebSocket Connectivity, Circuit Breaker State)  |
+----------------------------------------------------------------------------------------------------+
```

---

## 2. Interaction State Matrices

### 2.1 Durable Task Queue State Matrix

| State Name | Visual & Layout Representation | Event / Ingestion Trigger | Action Button States & Modality | Recovery & Next State Transition |
| :--- | :--- | :--- | :--- | :--- |
| **1. Nominal Stream Ingestion** | Steady stream pulse (emerald status glyph, `120 msg/s` counter, sparkline chart active). Partition rows display solid green checkpoint chips (`offset: 4982103`). | Continuous incoming Kafka/Redis Stream messages; worker heartbeat within `< 5s`. | All consumer management controls enabled (`Pause Partition`, `Rebalance Consumer Leases`, `Rewind Checkpoint`). | Transitions to `Backpressure Active` if buffer exceeds 80%, or `Checkpoint Quiescent` if stream ends. |
| **2. Active Consumer Pool (Rebalancing)** | Amber pulse banner on top of consumer table (`bg-amber-500/10 border-amber-500/40`). Consumer rows show `Reallocating Lease` badges with shimmer animation. | Scale up/down of worker pods, node eviction, or manual rebalance trigger. | Primary lease allocation buttons disabled with `aria-busy="true"`. "Halt Rebalance" emergency stop remains enabled. | Auto-transitions to `Nominal Stream Ingestion` upon assignment acknowledgment (timeout: 10s). |
| **3. Checkpoint Resumption / Rewind** | Modal overlay with dual-offset slider (`From: Current (4982103)` to `Target: Replay Epoch`). Interactive confirmation input requires typing `CONFIRM REWIND`. | User clicks "Rewind Partition" on a specific stream partition or resumes stalled stream. | Modal traps focus. "Execute Rewind" button disabled until safety string matches. "Cancel" button focused by default. | Stream pauses consumer loop, seeks offset backwards, displays `Resuming from Checkpoint: <offset>`, transitions to `Nominal`. |
| **4. Paused / HITL Approval Required** | High-contrast Orange accent border (`border-orange-500 bg-orange-950/20`). Flashing priority badge (`HITL Gate: Pending Approval`). Task payload preview truncated with expander. | Pipeline encounters sensitive action (e.g., automated cloud resource provisioning, bulk privilege change). | Sticky action panel: `Approve and Resume` (primary green), `Reject and Abort` (destructive red), `Inspect Full Context` (ghost). | On Approval: task resumes, queue lock lifts. On Rejection: task routed to DLQ with audit reason, queue unblocks. |
| **5. Dead-Letter Queue (DLQ) Quarantine** | Rose warning banner (`border-rose-600 bg-rose-950/40 text-rose-200`). Table list shows failed payloads, attempt counter (e.g., `5/5 Retries Exhausted`), and exception hash. | Task fails maximum retry backoff schedule (5 consecutive faults or schema validation failure). | Per-row actions: `Redrive Single Task`, `Redrive All Safe`, `Purge Task`, `Export Trace Payload`. Redrive actions disabled if target partition is stopped. | Redriven item transitions to `Nominal Stream Ingestion` with redrive counter `redrive_count: 1`. Purged items enter audit archive. |
| **6. Stream Backpressure Warning** | Yellow warning banner across ingestion strip (`border-yellow-500/70 bg-yellow-950/30`). Throughput graph changes from emerald to amber. Buffer indicator reads `88% Capacity`. | Buffer queue utilization exceeds 85% or consumer lag grows by `> 2,000 items/sec`. | "Enable Dynamic Throttling", "Scale Consumer Fleet", "Sample Non-Critical Events" controls light up. | Returns to `Nominal` when queue capacity drops `< 60%`. Escalates to `Circuit Breaker Halt` if 98% breached. |

---

### 2.2 Autonomous Research & Self-Improvement Radar State Matrix

| State Name | Visual & Layout Representation | Event / Ingestion Trigger | Action Button States & Modality | Recovery & Next State Transition |
| :--- | :--- | :--- | :--- | :--- |
| **1. ArXiv Continuous Scan Feed** | Dynamic card feed with time-decay sorting. Highlighting badge for match confidence (e.g., `Relevance: 96% - Tool Synthesis`). Monospace ArXiv IDs (`2403.18921v1`). | Scheduled 6-hour cron or manual "Run ArXiv Scan" execution. ArXiv API query completes. | `Extract RFC Proposal` (primary button on card), `Dismiss Paper` (icon button), `View ArXiv Abstract` (external link). | Upon clicking `Extract RFC Proposal`, paper enters `RFC Synthesis in Progress`. |
| **2. Paper Summary RFC Synthesis** | Skeleton card with animated shimmer matching RFC structure (Abstract, System Delta, Threat Surface, Benchmark Plan). Micro-badge: `Synthesizing via LLM (Step 2/4)`. | User triggers extraction or autonomous radar triggers high-confidence ingest (> 95% match). | Card controls disabled with `aria-busy="true"`. Global "Cancel Synthesis" available in header. | Transitions to `RFC Review Pending (HITL)` when structured proposal JSON is generated. |
| **3. RFC Review Pending (HITL Gate)** | Distinct Cyan-Blue card perimeter (`border-cyan-500 bg-cyan-950/20`). RFC Score Breakdown pill: `Feasibility: 8.8/10`, `Safety: 9.4/10`. "Requires Architect Sign-Off". | RFC synthesis completes. Pipeline generates prompt delta or architectural blueprint. | `Open RFC Review Modal` (primary), `Quick Reject with Note` (secondary), `Snooze 24h` (tertiary). | Opening modal triggers full split-diff comparison and decision workflow. |
| **4. DSPy Prompt Optimization Eval** | Dual-pane comparative score card. Left: `Baseline Prompt (v1.4)`. Right: `Candidate Prompt (v2.0-dspy)`. Metrics table: Accuracy delta (+4.2%), Latency delta (-18ms), Cost delta ($0.0012/call). | DSPy teleprompter compiler completes bootstrap few-shot evaluation against ground-truth validation set. | `Promote to Staging`, `Roll Back Candidate`, `Run Full Benchmark (500 cases)`, `Inspect Prompt Diff`. | Promoting candidate deploys to staging canary with 10% traffic split. Rejection archives candidate. |
| **5. DSPy Evaluation Diverged / Stalled** | Amber warning card (`border-amber-600 bg-amber-950/30`). Metric displays non-converged status: `Score Delta: -3.8% (Failed Objective)`. Epoch counter: `Iteration 12/12 (Terminated)`. | Optimization loss function fails to meet convergence threshold (< 0.01 delta) or degrades baseline performance. | Primary button changes to `Inspect Loss Trajectory`. Secondary button `Re-run with Modified Teleprompter`. `Promote` button disabled. | User reconfigures few-shot demonstration seeds or reverts prompt compiler settings. |
| **6. OPA Policy Auto-Proposal Diff** | Side-by-side or unified code diff viewer. Red strikethrough for deleted Rego rules, Green background for proposed rules. Header pill: `Static Analysis: Passed OPA Check`. | Radar identifies emerging tool pattern and auto-synthesizes Rego security constraint (e.g., rate-limiting an external API). | `Approve & Commit Policy` (primary emerald), `Request Policy Modification` (ghost), `Reject Proposal` (destructive). | Approval commits to Git repository and dispatches to edge clusters. Rejection closes RFC. |

---

## 3. Human-Centered UX Error, Warning & Backpressure Copy

Constructive, fault-tolerant copy rules:
1. **Never blame the user or system operator.**
2. **State current data integrity and operational impact.**
3. **Offer two unambiguous action options (immediate resolution vs. diagnostic inspection).**

```
+----------------------------------------------------------------------------------------------------+
| [ICON: Warning / Octagon]  [Headline: Clear Operational Verdict]                                  |
| Impact: Specific impact on tasks, queue retention, and agent autonomy.                             |
| Details: Technical metrics, trace ID, partition indices, or evaluation iteration count.          |
|                                                                                                    |
| [Primary Action (Resolve / Mitigate)]        [Secondary Action (Inspect / Trace Diagnostics)]     |
+----------------------------------------------------------------------------------------------------+
```

### 3.1 Copy Inventory

#### State 1: Stream Backpressure Threshold Exceeded
- **Banner Headline:** "Event stream ingestion throttled due to downstream buffer pressure"
- **Operational Impact:** "Partition buffer reached 88% capacity. Ingestion rate has been automatically throttled from 1,200 msg/sec to 450 msg/sec to prevent message loss. No messages have been dropped."
- **Technical Footprint:** `Buffer: 8,820 / 10,000 items` • `Active Consumer Lag: +4,210 ms` • `Partitions Affected: 2, 4, 7`
- **Primary Action CTA:** `Scale Consumer Fleet (+3 Pods)`
- **Secondary Action CTA:** `View Ingestion Telemetry in Logfire`

#### State 2: Circuit Breaker Execution Halt (Emergency Invariant Breach)
- **Banner Headline:** "Autonomous execution loop halted by circuit breaker"
- **Operational Impact:** "The radar safety supervisor suspended automated operations after detecting 5 consecutive task exceptions across consumer workers. All active event leases are preserved in durable state; uncommitted checkpoints remain intact."
- **Technical Footprint:** `Circuit: TASK_DISPATCH_SUPERVISOR` • `Failure Rate: 100% (5/5 attempts)` • `Trip Reason: OPA_POLICY_TIMEOUT`
- **Primary Action CTA:** `Reset Circuit Breaker & Resume Stream`
- **Secondary Action CTA:** `Inspect Failing Task Traces in DLQ`

#### State 3: DSPy Prompt Evaluation Diverged / Un-Converged
- **Banner Headline:** "Prompt optimization terminated without achieving performance target"
- **Operational Impact:** "The DSPy teleprompter completed 12 evaluation epochs against the validation test bench, but candidate prompt scores degraded baseline accuracy by 3.8%. The current production prompt (v1.4) remains active and unmodified."
- **Technical Footprint:** `Metric: Task Exact Match` • `Baseline: 89.2%` • `Candidate: 85.4% (-3.8%)` • `Epochs: 12/12`
- **Primary Action CTA:** `Adjust Few-Shot Seeds & Retry Eval`
- **Secondary Action CTA:** `Examine Divergent Token Traces`

#### State 4: Checkpoint Resumption Mismatch
- **Banner Headline:** "Partition checkpoint offset ahead of stream watermark"
- **Operational Impact:** "Stored checkpoint offset `5,102,900` exceeds the broker's current high watermark `5,102,400`. Resumption has paused to prevent skipping uncommitted messages."
- **Technical Footprint:** `Stream: events.radar.telemetry` • `Partition: 0` • `Drift: +500 offsets`
- **Primary Action CTA:** `Align to Nearest Durable Snapshot`
- **Secondary Action CTA:** `Inspect Kafka Offset Log`

#### State 5: Dead-Letter Queue Redrive Failure
- **Banner Headline:** "Task quarantine redrive rejected by consumer schema validator"
- **Operational Impact:** "The redriven task payload could not be dispatched to the active queue because the schema version `v1` is incompatible with consumer protocol `v2`. The task has been safely returned to quarantine."
- **Technical Footprint:** `Task ID: tsk_019c44b9` • `Schema Error: Missing field 'idempotency_key'` • `DLQ Retention: 13d remaining`
- **Primary Action CTA:** `Edit Task Payload & Revalidate`
- **Secondary Action CTA:** `Archive Task Permanently`

---

## 4. WCAG 2.2 Level AA Accessibility Specifications

### 4.1 High-Contrast Queue & Status Badges (Contrast & Dual Encoding)

Every visual indicator must adhere to WCAG 2.2 AA Contrast Criteria (4.5:1 for normal text, 3:1 for graphical interface elements) and **must never rely solely on color to communicate state**.

| System State | Visual Treatment (Dark Theme Token) | Contrast Ratio vs Background (`#090d16`) | Non-Color Glyph / Icon | Screen Reader Announcement (`aria-label`) |
| :--- | :--- | :--- | :--- | :--- |
| **Stream Ingestion Active** | Background: `rgba(16, 185, 129, 0.15)`<br>Text: `#34d399` (Emerald 400)<br>Border: `#059669` (Emerald 600) | Text: `7.2:1`<br>Border: `3.8:1` | Solid Circle (`●`) | `aria-label="Queue status: Active stream ingestion at 120 messages per second"` |
| **Stream Backpressure Warning** | Background: `rgba(245, 158, 11, 0.15)`<br>Text: `#fbbf24` (Amber 400)<br>Border: `#d97706` (Amber 600) | Text: `8.4:1`<br>Border: `4.1:1` | Warning Triangle (`▲`) | `aria-label="Queue status: Backpressure warning. Buffer at 88 percent capacity"` |
| **Circuit Breaker Tripped / Halted** | Background: `rgba(225, 29, 72, 0.20)`<br>Text: `#fda4af` (Rose 300)<br>Border: `#e11d48` (Rose 600) | Text: `9.1:1`<br>Border: `4.6:1` | Octagonal Stop Glyph (`🛑`) | `aria-label="Queue status: Emergency halt. Circuit breaker tripped"` |
| **HITL Approval Pending** | Background: `rgba(249, 115, 22, 0.20)`<br>Text: `#fdba74` (Orange 300)<br>Border: `#ea580c` (Orange 600) | Text: `8.6:1`<br>Border: `4.3:1` | Hourglass Glyph (`⏳`) | `aria-label="Radar status: Human approval pending for synthesized RFC"` |
| **Dead-Letter Quarantined** | Background: `rgba(168, 85, 247, 0.20)`<br>Text: `#d8b4fe` (Purple 300)<br>Border: `#9333ea` (Purple 600) | Text: `7.8:1`<br>Border: `3.5:1` | Padlock Glyph (`🔒`) | `aria-label="Queue status: Task quarantined in dead letter queue"` |

---

### 4.2 Focus Management: RFC & Policy Diff Review Modal

The RFC review workflow opens an interactive side-by-side / unified diff modal. To comply with WCAG 2.2 AA (Success Criteria 2.1.1 Keyboard, 2.1.2 No Keyboard Trap, 2.4.3 Focus Order, 2.4.7 Focus Visible):

```
+----------------------------------------------------------------------------------------------------+
| RFC Review Modal: [Paper 2403.18921v1] - Multi-Turn Tool Policy Upgrade                            |
| [1. Close Button (X)] (Initial Focus Fallback)                                                    |
+----------------------------------------------------------------------------------------------------+
| Tab Navigation Strip:                                                                              |
| [ Tab: Summary ]    [ Tab: DSPy Prompt Diff ]    [*Tab: OPA Policy Diff*]    [ Tab: Threat Model ]  |
+----------------------------------------------------------------------------------------------------+
| Diff Inspector Controls:                                                                           |
| [ Split View Button (Active) ]    [ Unified View Button ]    [ Next Change (J) ] [ Prev (K) ]      |
+----------------------------------------------------------------------------------------------------+
| Diff Body: (Accessible code scroll container)                                                     |
| Line 42: - allow = false                                                                           |
| Line 42: + allow = true if input.token_valid == true                                               |
+----------------------------------------------------------------------------------------------------+
| Modal Sticky Footer:                                                                               |
| [ Reject Proposal Button ]              [ Request Changes Button ]        [ Approve & Merge (Enter)]|
+----------------------------------------------------------------------------------------------------+
```

#### Modal Focus Lifecycle Rules:
1. **Invocation & Initial Focus:**
   - On clicking `Open RFC Review Modal`, the triggering element's DOM reference is saved to `activeElementRef`.
   - The modal container is rendered with `role="dialog"`, `aria-modal="true"`, and `aria-labelledby="rfc-modal-title"`.
   - Focus is programmatically shifted to the **first interactive tab element** (`Tab: Summary`), providing immediate context without disorienting the user.
2. **Keyboard Trap & Tab Sequence:**
   - Keydown `Tab` cycles strictly through modal interactive nodes:
     `[Close Button]` -> `[View Tabs 1..4]` -> `[Diff Toggle Buttons]` -> `[Next/Prev Diff Buttons]` -> `[Diff Scroll Viewport]` -> `[Reject Button]` -> `[Request Changes Button]` -> `[Approve & Merge Button]`.
   - Pressing `Tab` from the `Approve & Merge Button` wraps back to the `[Close Button]`.
   - Pressing `Shift+Tab` from `[Close Button]` wraps backwards to `[Approve & Merge Button]`.
3. **Diff Navigation Shortcuts:**
   - `J` or `Down Arrow`: Jumps focus to next diff change chunk with an `aria-live` announcement: *"Navigated to change 2 of 5: Added rule rate_limit_window"*.
   - `K` or `Up Arrow`: Jumps focus to previous diff change chunk.
4. **Escape Key Handling:**
   - Pressing `Escape` triggers an immediate dismissal of the modal without saving changes.
   - If unsaved annotations or comments exist, an in-modal confirmation prompt asks: *"Discard review comments? [Cancel] [Discard]"* before closing.
5. **Dismissal Focus Restoration:**
   - Upon modal unmount, keyboard focus is immediately restored to `activeElementRef` (the card's `Open RFC Review Modal` button).
   - If the RFC was approved and removed from the active list, focus falls back to the adjacent RFC card's primary action button with an `aria-live` announcement: *"Proposal approved. Focused on next proposal: Paper 2404.09110"*.

---

### 4.3 Aria-Live Stream Annunciators (Audio & Screen Reader Ergonomics)

High-frequency telemetry streams must avoid flooding screen-reader speech buffers. Use tiered `aria-live` regions with debounced batching.

```html
<!-- High-Priority Alert Region: Interrupts ongoing speech for critical safety breaches -->
<div 
  id="aegis-critical-announcer" 
  role="alert" 
  aria-live="assertive" 
  aria-atomic="true" 
  class="sr-only">
  <!-- Dynamic insertion: "Emergency: Circuit breaker tripped on partition 2. Ingestion halted." -->
</div>

<!-- Standard Telemetry & Queue Status Region: Polite cadence, throttled to max 1 update per 5s -->
<div 
  id="aegis-polite-announcer" 
  role="status" 
  aria-live="polite" 
  aria-atomic="true" 
  class="sr-only">
  <!-- Dynamic insertion: "Autonomous scan complete: 3 candidate papers identified for review." -->
</div>
```

#### Annunciation Cadence Rules:
1. **Assertive (`aria-live="assertive"`):**
   - **Triggers:** Circuit breaker trip, emergency partition pause, fatal authorization failure.
   - **Delivery Policy:** Instantaneous dispatch. Bypasses queue.
2. **Polite (`aria-live="polite"`):**
   - **Triggers:** ArXiv scan completion, DSPy evaluation completion, RFC card creation, consumer lease rebalance completion.
   - **Delivery Policy:** Debounced with a **5,000ms minimum interval**. Rapid streaming metrics (messages/sec, offset numbers) are **never** piped to `aria-live` directly. Instead, summaries are emitted on milestone events (e.g., *"Ingestion nominal: 50,000 tasks processed"*).
3. **Diff Chunk Reader Semantics:**
   - Code diff lines in the policy inspector must include explicit line-type descriptors for screen readers:
     ```html
     <div role="text" aria-label="Line 42: Removed: allow = false">
       <span aria-hidden="true" class="text-rose-500">- allow = false</span>
     </div>
     <div role="text" aria-label="Line 42: Added: allow = true if input.token_valid == true">
       <span aria-hidden="true" class="text-emerald-500">+ allow = true if input.token_valid == true</span>
     </div>
     ```

---

## 5. Downstream Implementation Checklist for `@frontend-dev`

- [ ] **Component: `TaskQueueDashboard.tsx`**
  - Implement 6-state ingestion matrix (`Nominal`, `Rebalancing`, `CheckpointResumption`, `PausedHITL`, `DLQQuarantine`, `BackpressureWarning`).
  - Wire status pills using high-contrast color tokens and required unicode glyphs.
  - Implement debounced `aria-live="polite"` telemetry batching hook (`useStreamAnnouncer`).
- [ ] **Component: `CheckpointRewindModal.tsx`**
  - Implement focus-trap modal containing the dual-offset rewind slider.
  - Require literal verification input (`CONFIRM REWIND`) before enabling execution button.
  - Restore focus to rewind trigger button on dismissal.
- [ ] **Component: `AutonomousRadarView.tsx`**
  - Render ArXiv feed cards with relevance scores, decaying time sorts, and synthesis status.
  - Render DSPy comparison cards displaying accuracy, latency, and cost deltas.
  - Render diverged warning state when accuracy loss function fails.
- [ ] **Component: `RfcDiffModal.tsx`**
  - Construct split/unified Rego policy diff viewer.
  - Implement `J` / `K` shortcut navigation between diff chunks.
  - Add screen-reader line annotations (`aria-label="Line X: Added/Removed"`) to prevent raw +/- symbol ambiguity.
- [ ] **Accessibility & Keyboard Verification:**
  - Verify tab cycle containment in `RfcDiffModal` and `CheckpointRewindModal`.
  - Validate minimum 4.5:1 text and 3:1 graphical contrast across all status badges using Lighthouse or axe-core.
