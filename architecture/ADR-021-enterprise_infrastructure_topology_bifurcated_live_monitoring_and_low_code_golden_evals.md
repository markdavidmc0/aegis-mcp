# ADR-021: Enterprise Infrastructure Topology, Bifurcated Live Monitoring, and Low-Code Golden Evals

* **Date:** 2026-10-09  
* **Status:** RATIFIED (TARGET: v0.2.0-BETA)  
* **Context:**
  Sections 1, 2, and 8 of `spec_v0-0-1-alpha.md` outline baseline execution, sandboxing, and test evaluation.
  
  However, real-world enterprise deployments demand three essential production capabilities:
  1. **Enterprise Infrastructure Topology:** Deploying Aegis across enterprise hybrid-cloud environments requires a hardened, cloud-native infrastructure topology: Kubernetes (GKE/KinD), containerd `runsc` (gVisor) runtime isolation, CloudNativePG (`pgvector`) high availability, Envoy AI Gateway ingress with OIDC/Keycloak authentication, and GitOps-managed lifecycle via ArgoCD. The current specification leaves enterprise cluster deployment topologies unformalized.
  2. **Bifurcated Live Monitoring:** Telemetry and live monitoring in enterprise agent platforms must serve two fundamentally different operational audiences with distinct latency, fidelity, and analytical requirements:
     - **Platform SRE / Infrastructure Engineering:** Requires macro cluster metrics, pod health, container cgroup resource limits, Envoy rate limits, queue backpressure, and database connection pools.
     - **Agent Behavior / Swarm Diagnostics:** Requires micro-level GenAI semantic spans, tool call waterfalls, LLM roundtrip latencies, 4-tuple attribution (`actor_id`, `agent_id`, `cost_centre_id`, `session_id`), blackboard phase transitions, and prompt token efficiency.
     Conflating these or relying on a single monolithic dashboard causes alert fatigue and obscures root-cause diagnostics.
  3. **Low-Code Golden Evals & Benchmark Authoring:** ADR-007 introduced dual-track evals, but authoring test cases requires hand-crafting JSON schemas or writing Python test harness code. Enterprise domain experts (QA leads, product managers, security auditors) require an accessible, low-code interface to author, curate, and review "Golden Datasets" and regression suites with instant verifier feedback.

* **Decision:**
  1. **Codify Enterprise Infrastructure Topology:**
     - Standardize the cloud-native deployment topology:
       - **Compute & Sandbox Layer:** GKE/KinD clusters configured with `containerd` and `runsc` (gVisor) runtime handler class for Tier B sandboxing.
       - **Ingress & Edge Guard:** Envoy AI Gateway with WebAssembly (Wasm) filters and Keycloak OIDC JWT verification, propagating validated 4-tuple identity headers (`X-Actor-Id`, `X-Agent-Id`, `X-Cost-Centre-Id`, `X-Session-Id`) into the Control Plane.
       - **State & Memory Layer:** CloudNativePG cluster with automated failover, WAL archiving, and `pgvector` extension for L2 cross-session episodic retrieval.
       - **GitOps Continuous Delivery:** ArgoCD App-of-Apps pattern managing declarative Kustomize overlays across local KinD (`infra/k8s/gitops/overlays/local-kind/`) and production GCP (`infra/k8s/gitops/overlays/prod-gcp/`).
  2. **Deploy Bifurcated Live Monitoring Architecture:**
     - Partition operational observability into two dedicated, decoupled monitoring planes:
       - **Infra Plane (Prometheus / Grafana / Perses):** Scrapes Envoy metrics, container CPU/memory usage, gVisor sandbox sandbox lifecycle events, PostgreSQL connection pools, and Redis/DurableQueue depths.
       - **Agent Intelligence Plane (Pydantic Logfire & OpenTelemetry GenAI):** Ingests fine-grained distributed traces with W3C `traceparent` propagation across all agent turns, OPA policy evaluations, tool invocations, and LLM completions. Enriches every span with 4-tuple composite keys and project hierarchy. Exposes dedicated Perses/Logfire dashboards (`dashboards/aegis_agent_overview.json`) with interactive delegation waterfalls and bottleneck analytics.
  3. **Provide Low-Code Golden Evals Authoring & Verification Harness:**
     - Implement a low-code evaluation authoring studio (integrated into InceptOS and `demo_ui.py`):
       - Allows non-engineering domain experts to define golden test cases with inputs, expected constraints, allowed tool boundaries, and custom rubrics without writing Python code.
       - Interactive validation button executes the candidate prompt against the target agent model in an ephemeral sandbox, generating instant grader scores (`DeterministicVerifierGrader`, `SpecIntentModelGrader`).
       - Curated test cases are exported directly to version-controlled golden datasets (`evals/test_cases.json`) and run in CI/CD regression gates via `aegis eval run`.

* **Alternatives Rejected:**
  - *Monolithic Monitoring Stack:* Rejected because infrastructure metrics drown out semantic agent reasoning traces, while high-cardinality GenAI traces overwhelm traditional time-series databases.
  - *Developer-Only Code Evals:* Rejected because domain specialists and compliance officers cannot participate in model quality assurance without low-code authoring tools.
  - *Bare Virtual Machine Deployment:* Rejected due to lack of elastic scaling, gVisor runtime automation, and declarative GitOps reproducibility.

* **Key Artifacts:**
  - `infra/k8s/charts/aegis/` (Production Helm charts & Envoy sidecars)
  - `infra/k8s/gitops/` (ArgoCD root application & declarative Kustomize overlays)
  - `dashboards/aegis_agent_overview.json` (Perses & Logfire bifurcated agent dashboard)
  - `src/evaluation/golden_studio.py` (Low-code eval generator and dataset curator)
  - `architecture/review_v0-0-1-alpha.md` (Gap 18)
  - `architecture/MIGRATION_PLAN.md` (Beta Roadmap Alignment)
