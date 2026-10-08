# ADR-004: Multimodal Cross-Representation Engine: Gemma 2 Voice, Spatial Diagram-to-AST, and Visual Verification

* **Date:** 2026-10-08  
* **Status:** APPROVED (STAGED FOR v0.2.0-BETA)  
* **Context:**
  The initial draft of ADR-004 treated vector embeddings conventionally as text/code cosine distance measures for PRD facet slicing and context health ($H_{\text{ctx}}$).
  
  However, InceptOS is conceived as a human-in-the-loop spatial ideation workbench (`spec_v0-0-1-alpha.md` Section 1). Frontier open-weights multimodal representation models (specifically Google DeepMind's Gemma 2 multimodal architectures and unified projection spaces) enable continuous joint representation across **voice, visual diagrams, screen recordings, natural language, and symbolic ASTs**.

  Restricting embeddings to text search fails to capitalize on how human architects naturally design software: via spoken nuance, architectural whiteboard diagrams, UI wireframes, and video walkthroughs.

* **Decision:**
  1. **Dual-Layer Boundary Invariant Preserved:**
     Continuous latent spaces **never** supersede deterministic RFC 6902 JSON Patches for transactional control-plane state transitions, OPA policy gates, or AST boundary invariants. Discrete, verifiable state machines remain the sole authority of the Aegis Kernel.
  2. **Elevate Gemma 2 Multimodal Latent Space to Beta Core:**
     In `v0.2.0-BETA`, deploy Gemma 2 multimodal representations across four cross-representation workflows:
     - **Spatial Diagram-to-AST Projection (Visual Design $\rightarrow$ Code):**
       Architects draw boxes, boundary clusters, and flow arrows on the InceptOS Canvas (or import Excalidraw, Figma, or Mermaid diagrams). Gemma 2 maps visual clusters directly into codebase AST symbol trees (`src/control_plane/...`), generating precise `TARGET_FILES` and resource lease scopes without requiring manual file path entry.
     - **Continuous Voice Steering & Ambient Prompt Modulation:**
       Human supervisors dictate voice instructions via InceptOS Mobile or Slack audio snippets. Gemma 2 audio-to-text latent alignment directly encodes voice tone, emphasis, and intent into the active session intent vector $\vec{v}_{\text{intent}}$, steering in-flight agent loops with zero transcription drift.
     - **Visual Grounding & UI Regression Verification:**
       For frontend, canvas, and visualization components, ephemeral test runners capture headless browser snapshots and WebGL canvas states. Gemma 2 calculates perceptual semantic divergence $\Delta(\text{mockup}, \text{actual\_render})$ to enforce visual invariants alongside unit tests.
     - **Heterogeneous PRD Multi-Modal Facet Graph:**
       PRD documentation containing product mockups, architectural diagrams, Loom video walkthrough transcripts, and OpenAPI JSON schemas are embedded into a single multimodal facet graph (`src/context/facet_index.py`), enabling progressive semantic retrieval across modalities.
  3. **Release Milestone Boundary:**
     - `v0.1.0-ALPHA`: Zero-dependency, stdlib-first deterministic execution. Uses exact AST projections and string/hash facets.
     - `v0.2.0-BETA`: Launches the Gemma 2 multimodal service (`src/multimodal/`) as a dedicated GPU/local inference worker feeding InceptOS spatial canvas interactions.

* **Alternatives Rejected:**
  - *Text-Only Embedding Models (e.g., text-embedding-3-large):* Rejected because they cannot ground visual architecture diagrams, UI screenshots, or raw voice steering.
  - *Pure End-to-End Multimodal Generation (Discarding ASTs):* Rejected because generating raw code directly from image tokens produces severe hallucinations and unmaintainable syntax errors. Multimodal representations must resolve to discrete AST symbols.

* **Key Artifacts:**
  - `src/multimodal/gemma_engine.py` (Multimodal embedding and cross-representation projector)
  - `src/context/facet_index.py` (Multimodal PRD facet graph)
  - `architecture/review_v0-0-1-alpha.md` (Gap 8 & Beta Milestone)
