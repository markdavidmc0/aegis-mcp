# ADR-014: Jason Liu-Compliant Context Engineering: Typed Delta Compaction and Semantic Distillation

* **Date:** 2026-10-08  
* **Status:** RATIFIED (TARGET: v0.1.0-ALPHA)  
* **Context:**
  Section 6 of `spec_v0-0-1-alpha.md` introduces the Context Health Index ($H_{\text{ctx}}$), AST skeleton digestion, and Content-Addressed Storage (`BlobVault`).
  
  However, the specification falls short of the rigorous context engineering standards pioneered by **Jason Liu** (*Instructor*, *Extracting Knowledge from Large Language Models*):
  1. **Unstructured Conversation Compaction:** When an agent approaches the 25-turn ceiling or $H_{\text{ctx}}$ deteriorates below safe operating thresholds ($H_{\text{ctx}} < 0.35$), standard agent frameworks rely on lossy, unstructured summaries ("Summarize the chat history so far"). This destroys critical semantic invariants: exact variable identifiers, tested hypotheses, negative constraints, and precise file paths.
  2. **Context Window Contamination:** Free-form conversational history accumulates dead-end error traces, discarded thoughts, and verbose tool outputs that cause catastrophic in-context attention distraction.
  3. **Lack of Strongly Typed State Extraction:** Contextual state is held as unstructured lists of chat messages rather than first-class Pydantic v2 schemas that can be structurally inspected, validated, and transferred across agent turns.

* **Decision:**
  1. **Adopt Jason Liu's Typed Delta Compaction Protocol:**
     Ban naive narrative conversation summarization across the platform. When $H_{\text{ctx}} < 0.35$ or a session reaches turn compaction thresholds:
     - The runtime triggers a structured state extraction pass into an immutable, strictly validated schema:
       ```python
       class SessionDistillation(BaseModel):
           """Strict Pydantic schema representing distilled session state."""
           model_config = ConfigDict(extra="forbid", frozen=True)

           hypotheses_tested: list[str] = Field(description="Explicit hypotheses proven or disproven.")
           discovered_invariants: list[str] = Field(description="Architectural or boundary rules discovered.")
           failed_approaches: list[dict[str, str]] = Field(description="Strategies attempted and exact failure causes.")
           active_target_files: list[str] = Field(description="Files currently modified or slated for edits.")
           retained_symbol_signatures: list[str] = Field(description="Exact type and function signatures required.")
           unresolved_blockers: list[str] = Field(description="Current blockers requiring resolution in next phase.")
       ```
     - **Context Reset & Re-Injection:** The bloated raw message history is flushed from the prompt window. The agent's working context is re-initialized with the raw system prompt + this single typed `SessionDistillation` artifact, instantly restoring $H_{\text{ctx}} \to 1.0$ with zero loss of critical operational facts.
  2. **Progressive Disclosure & Zero-Token AST Projection:**
     - Enforce Jason Liu's tenet of **Progressive Disclosure**: Agents are prohibited from dumping entire files into working memory.
     - Files are projected as zero-token AST symbol digests (`read_ast_skeleton`). Full implementations are retrieved strictly on-demand via targeted chunk queries (`slice_blob`) or facet indices (`query_facet`).
  3. **Strict Structured Extraction on All Tool Boundaries:**
     - All FastMCP tool inputs and outputs must resolve to strict Pydantic v2 models with `extra="forbid"` and explicit field descriptions.
     - Markdown or conversational text outputs from tools are strictly prohibited unless wrapped in a typed container model.

* **Alternatives Rejected:**
  - *Naive Narrative Summarization:* Rejected because LLMs drop exact identifier names, forget subtle constraints, and hallucinate details when producing unstructured summaries.
  - *Sliding Window Truncation (FIFO dropping of older turns):* Rejected because early system constraints, PRD requirements, and discovered invariants located in Turns 1–3 are completely erased.

* **Key Artifacts:**
  - `src/context/distillation.py` (Typed compaction models & extractor)
  - `src/context/health_monitor.py` (Real-time $H_{\text{ctx}}$ calculation & threshold trigger)
  - `src/interfaces/cli.py` (`aegis context compact` command)
  - `architecture/review_v0-0-1-alpha.md` (Gap 16)
