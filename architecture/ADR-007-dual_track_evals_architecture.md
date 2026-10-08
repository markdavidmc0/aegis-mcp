# ADR-007: Dual-Track Evaluation Architecture & Vault EvalOps Unification

* **Date:** 2026-10-08  
* **Status:** PROPOSED (TARGET: v0.0.1-BETA)  
* **Context:**
  Section 8 of `spec_v0-0-1-alpha.md` defined a monolithic 30-line `GraderPipeline` helper method evaluating four hardcoded integer/float arguments (`pytest_exit_code`, `ruff_violations_count`, `prompt_intent_score`, `turn_ceiling`).
  
  This design exhibits three critical deficiencies:
  1. **Conflation of Task Gates with EvalOps Benchmarking:** It treats in-flight, inner-loop task verification (`TDD_INNER_LOOP` completion) identically to pre-deployment agent capability benchmarking across prompt iterations and model tiers.
  2. **Software-Only Coupling:** It hardcodes Python test runners and linters (`pytest`, `ruff`), providing zero evaluation primitives for non-code organizational agents (structured data, schema compliance, regex formatting, token safety).
  3. **Fragmented Tooling Risk:** Building a new eval runner from scratch in the platform would duplicate the mature, tested modular grader engine already operational in `~/vault/evals/run_evals.py` (`DeterministicVerifierGrader`, `FormatSchemaGrader`, `GuardrailGrader`, `SpecIntentModelGrader`, `TelemetryBudgetGrader`), while importing heavy third-party open-source eval frameworks (DeepEval, Ragas) would inject massive dependency bloat and non-deterministic LLM-judge variance.

* **Decision:**
  1. **Unify Platform Evals on the `vault` Modular Grader Architecture:**
     Adopt the `vault` grader chain directly into the platform core under `src/evaluation/`:
     - `DeterministicVerifierGrader`: Subprocess execution verifier (`pytest`, `cargo`, `tsc`, SQL validation).
     - `FormatSchemaGrader`: JSON schema compliance and strict regex pattern enforcement.
     - `GuardrailGrader`: Forbidden token matching, PII boundaries, and safety assertion rules.
     - `SpecIntentModelGrader`: Rubric-based model grader evaluating intent satisfaction.
     - `TelemetryBudgetGrader`: Hard turn count, token budget, and execution duration enforcement.
  2. **Establish the Dual-Track Evaluation Operating Model:**
     Decouple execution into two distinct operational loops sharing the identical underlying grader engine:
     - **Track 1: In-Flight Runtime Task PEP (Synchronous):**
       Executed dynamically inside `TaskBlackboardManager` when advancing from `EVALUATING` $\rightarrow$ `COMPLETED` or looping back to `TDD_INNER_LOOP`. Emits execution spans into Logfire.
     - **Track 2: Offline EvalOps Benchmark Harness (Asynchronous / CI):**
       Exposed via CLI command `aegis eval run --dataset <path> --ci`. Evaluates prompt templates, agent manifests, and model routing tiers against golden regression datasets (`evals/test_cases.json`). Emits `eval.local_harness` spans and formats summary tables.
  3. **Reject External OS Eval Platform Dependencies:**
     Prohibit importing third-party RAG-centric eval libraries into the core control plane. Evaluation remains zero-dependency, local-first, and deterministic.

* **Alternatives Rejected:**
  - *Adopting Third-Party OS Eval Frameworks (DeepEval, Ragas, Braintrust):* Rejected due to heavy dependency trees (LangChain, PyTorch), network egress requirements, and mismatch with stateful agent tool/AST evaluation.
  - *Retaining Section 8's Naive 30-Line Snippet:* Rejected because it cannot evaluate non-code organizational workflows or support golden dataset regression testing.
  - *Maintaining Disjoint Eval Tools in `vault/` and `aegis-mcp/`:* Rejected to preserve a single source of truth (SSOT) across local agent development and platform runtime.

* **Key Artifacts:**
  - `src/evaluation/graders.py` (Modular grader suite)
  - `src/evaluation/grader_pipeline.py` (Core coordinator)
  - `src/interfaces/cli.py` (`aegis eval run` subcommands)
  - `evals/test_cases.json` (Golden regression benchmark dataset)
  - `architecture/review_v0-0-1-alpha.md` (Gap 9)
  - `architecture/MIGRATION_PLAN.md` (Phase 6)
