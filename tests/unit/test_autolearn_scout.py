"""Unit tests for Autonomous Research Scout and DSPy Optimizer."""

from datetime import datetime
from unittest.mock import patch

import pytest
from pydantic import ValidationError


@pytest.mark.unit
class TestAutoLearnSchemas:
    """Tests for AutoLearn schemas and strict invariant validation."""

    def test_paper_scout_result_schema_invariants(self) -> None:
        """Test PaperScoutResult schema validation (model_config = ConfigDict(extra='forbid', frozen=True))."""
        from src.autolearn.schemas import PaperScoutResult

        result = PaperScoutResult(
            paper_id="2401.12345",
            title="Efficient KV Cache Compression for Large Context LLMs",
            authors=["Alice Doe", "Bob Smith"],
            abstract="We present an adaptive KV cache compression mechanism...",
            keywords=["kv cache", "context compression", "prompt pruning"],
            published_date=datetime(2026, 3, 15, 12, 0, 0),
            arxiv_url="https://arxiv.org/abs/2401.12345",
            pdf_url="https://arxiv.org/pdf/2401.12345.pdf",
            relevance_score=0.95,
        )

        assert result.paper_id == "2401.12345"
        assert result.title.startswith("Efficient KV Cache")
        assert len(result.keywords) == 3
        assert result.relevance_score == 0.95

        # Check frozen invariant
        with pytest.raises((ValidationError, TypeError)):
            result.relevance_score = 1.0  # type: ignore[misc]

        # Check extra='forbid' invariant
        with pytest.raises(ValidationError):
            PaperScoutResult(
                paper_id="2401.12345",
                title="Title",
                authors=["Alice"],
                abstract="Abstract",
                keywords=["kv cache"],
                published_date=datetime.now(),
                arxiv_url="https://arxiv.org/abs/2401.12345",
                extra_forbidden_field="not_allowed",  # type: ignore[call-arg]
            )

    def test_prompt_optimization_result_schema_invariants(self) -> None:
        """Test PromptOptimizationResult schema and scoring contract."""
        from src.autolearn.schemas import PromptOptimizationResult

        opt = PromptOptimizationResult(
            optimization_id="opt_987",
            agent_id="agt_orchestrator",
            original_prompt="You are a helpful assistant.",
            optimized_prompt="You are a precise, security-hardened tool caller. Always validate inputs.",
            baseline_score=0.62,
            optimized_score=0.91,
            metric_name="tool_call_accuracy",
            iterations_run=3,
            metadata={"dspy_teleprompter": "MIPROv2"},
        )

        assert opt.optimization_id == "opt_987"
        assert opt.optimized_score > opt.baseline_score
        assert opt.metric_name == "tool_call_accuracy"
        assert opt.iterations_run == 3

        # Check frozen invariant
        with pytest.raises((ValidationError, TypeError)):
            opt.baseline_score = 0.70  # type: ignore[misc]

        # Check extra='forbid' invariant
        with pytest.raises(ValidationError):
            PromptOptimizationResult(
                optimization_id="opt_1",
                agent_id="agt_1",
                original_prompt="a",
                optimized_prompt="b",
                baseline_score=0.5,
                optimized_score=0.8,
                metric_name="acc",
                iterations_run=1,
                rogue_attribute="rejected",  # type: ignore[call-arg]
            )


@pytest.mark.unit
class TestPaperScoutFeedFiltering:
    """Tests for PaperScout query parser filtering arXiv feeds for keywords."""

    @pytest.mark.asyncio
    async def test_paper_scout_filters_target_keywords(self) -> None:
        """Test PaperScout query parser filters arXiv feed items matching keywords."""
        from src.autolearn.scout import PaperScout

        mock_feed_xml = """<?xml version="1.0" encoding="UTF-8"?>
        <feed xmlns="http://www.w3.org/2005/Atom">
          <entry>
            <id>http://arxiv.org/abs/2601.00001v1</id>
            <title>Context Compression and KV Cache Pruning in Multi-Turn Agents</title>
            <summary>A novel approach to context compression and KV cache reduction.</summary>
            <author><name>Dr. Ada Lovelace</name></author>
            <published>2026-03-01T00:00:00Z</published>
            <link rel="alternate" type="text/html" href="http://arxiv.org/abs/2601.00001v1"/>
          </entry>
          <entry>
            <id>http://arxiv.org/abs/2601.00002v1</id>
            <title>Unrelated Recipe Generation using Deep Convolutional Networks</title>
            <summary>Baking sourdough bread using neural networks.</summary>
            <author><name>Chef Gordon</name></author>
            <published>2026-03-02T00:00:00Z</published>
            <link rel="alternate" type="text/html" href="http://arxiv.org/abs/2601.00002v1"/>
          </entry>
          <entry>
            <id>http://arxiv.org/abs/2601.00003v1</id>
            <title>MCP Security: Defending Tool Protocols against Prompt Injections</title>
            <summary>Formally verified sandboxing for Model Context Protocol servers.</summary>
            <author><name>Prof. Turing</name></author>
            <published>2026-03-03T00:00:00Z</published>
            <link rel="alternate" type="text/html" href="http://arxiv.org/abs/2601.00003v1"/>
          </entry>
        </feed>
        """

        scout = PaperScout(
            target_keywords=[
                "context compression",
                "kv cache",
                "prompt pruning",
                "mcp security",
            ]
        )

        with patch.object(scout, "_fetch_arxiv_feed", return_value=mock_feed_xml):
            results = await scout.scout_recent_papers(max_results=10)

        assert len(results) == 2
        titles = [p.title for p in results]
        assert "Context Compression and KV Cache Pruning in Multi-Turn Agents" in titles
        assert "MCP Security: Defending Tool Protocols against Prompt Injections" in titles
        assert not any("Recipe Generation" in t for t in titles)

    @pytest.mark.asyncio
    async def test_paper_scout_scores_relevance(self) -> None:
        """Test PaperScout assigns higher relevance score to papers with multiple matching keywords."""
        from src.autolearn.scout import PaperScout

        mock_feed_xml = """<?xml version="1.0" encoding="UTF-8"?>
        <feed xmlns="http://www.w3.org/2005/Atom">
          <entry>
            <id>http://arxiv.org/abs/2601.00010v1</id>
            <title>KV Cache Optimization</title>
            <summary>Discussion on kv cache.</summary>
            <author><name>Researcher A</name></author>
            <published>2026-03-01T00:00:00Z</published>
          </entry>
          <entry>
            <id>http://arxiv.org/abs/2601.00011v1</id>
            <title>Advanced KV Cache with Context Compression and Prompt Pruning for MCP Security</title>
            <summary>Comprehensive study combining kv cache, context compression, prompt pruning, and mcp security.</summary>
            <author><name>Researcher B</name></author>
            <published>2026-03-01T00:00:00Z</published>
          </entry>
        </feed>
        """

        scout = PaperScout(
            target_keywords=[
                "context compression",
                "kv cache",
                "prompt pruning",
                "mcp security",
            ]
        )

        with patch.object(scout, "_fetch_arxiv_feed", return_value=mock_feed_xml):
            results = await scout.scout_recent_papers(max_results=5)

        assert len(results) == 2
        # Highest relevance first
        assert results[0].relevance_score > results[1].relevance_score
        assert "Comprehensive study" in results[0].abstract
