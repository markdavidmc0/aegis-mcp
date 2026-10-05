"""Contract and unit tests for Vector and Episodic Memory Store."""

import math
from datetime import UTC, datetime

import pytest
from pydantic import ValidationError


@pytest.mark.contract
class TestMemoryStoreContract:
    """Contract test suite validating memory schemas and vector similarity interfaces."""

    def test_episodic_run_schema_immutability_and_forbid_extra(self) -> None:
        """Verifies EpisodicMemoryRecord enforces frozen=True and extra='forbid'."""
        from src.memory.schemas import EpisodicMemoryRecord

        now = datetime.now(UTC)
        record = EpisodicMemoryRecord(
            memory_id="mem_ep_001",
            actor_id="actor_lead",
            agent_id="agent_planner",
            cost_centre_id="cc_infra",
            session_id="sess_alpha",
            task_prompt="Optimize memory latency across clusters",
            final_outcome="Achieved 42% latency reduction via vector caching",
            embedding=[0.1, 0.2, 0.3, 0.4],
            created_at=now,
            metadata={"environment": "production"},
        )

        assert record.memory_id == "mem_ep_001"
        assert record.actor_id == "actor_lead"
        assert record.embedding == [0.1, 0.2, 0.3, 0.4]

        # Immutability validation (frozen=True)
        with pytest.raises((ValidationError, TypeError)):
            record.final_outcome = "Mutated outcome"  # type: ignore[misc]

        # Extra field rejection (extra="forbid")
        with pytest.raises(ValidationError):
            EpisodicMemoryRecord(
                memory_id="mem_ep_002",
                actor_id="actor_lead",
                agent_id="agent_planner",
                cost_centre_id="cc_infra",
                session_id="sess_alpha",
                task_prompt="test",
                final_outcome="test",
                embedding=[0.1, 0.2],
                created_at=now,
                unexpected_field="forbidden",  # type: ignore[call-arg]
            )

    def test_memory_query_schema_invariants(self) -> None:
        """Verifies MemoryQueryRequest strictly validates bounds and forbids extra properties."""
        from src.memory.schemas import MemoryQueryRequest

        query = MemoryQueryRequest(
            query_embedding=[0.05, 0.15, 0.25, 0.35],
            top_k=5,
            similarity_threshold=0.75,
            cost_centre_id="cc_infra",
        )
        assert query.top_k == 5
        assert query.similarity_threshold == 0.75

        # Bounds validation
        with pytest.raises(ValidationError):
            MemoryQueryRequest(
                query_embedding=[0.1],
                top_k=0,  # top_k must be >= 1
            )

        with pytest.raises(ValidationError):
            MemoryQueryRequest(
                query_embedding=[0.1],
                similarity_threshold=1.5,  # threshold must be <= 1.0
            )

    @pytest.mark.asyncio
    async def test_episodic_run_serialization_and_retrieval(self) -> None:
        """Verifies storing and retrieving episodic execution records roundtrips cleanly."""
        from src.memory.schemas import EpisodicMemoryRecord
        from src.memory.store import InMemoryVectorMemoryStore

        store = InMemoryVectorMemoryStore()
        now = datetime.now(UTC)
        record = EpisodicMemoryRecord(
            memory_id="mem_001",
            actor_id="actor_dev",
            agent_id="agent_bench",
            cost_centre_id="cc_gpu",
            session_id="sess_100",
            task_prompt="Run GEMM kernel benchmarks",
            final_outcome="Success with 120 TFLOPS",
            embedding=[1.0, 0.0, 0.0],
            created_at=now,
        )

        await store.store_record(record)
        retrieved = await store.get_record("mem_001")

        assert retrieved is not None
        assert retrieved.memory_id == record.memory_id
        assert retrieved.task_prompt == record.task_prompt
        assert retrieved.final_outcome == record.final_outcome
        assert retrieved.embedding == record.embedding

    @pytest.mark.asyncio
    async def test_cosine_similarity_vector_query_ranking(self) -> None:
        """Verifies vector search computes cosine similarity and ranks nearest matches."""
        from src.memory.schemas import EpisodicMemoryRecord, MemoryQueryRequest
        from src.memory.store import InMemoryVectorMemoryStore

        store = InMemoryVectorMemoryStore()
        now = datetime.now(UTC)

        # Record 1: Exact match direction [1.0, 0.0, 0.0] -> cosine sim = 1.0
        rec_exact = EpisodicMemoryRecord(
            memory_id="rec_exact",
            actor_id="actor_1",
            agent_id="agent_1",
            cost_centre_id="cc_1",
            session_id="s1",
            task_prompt="Kernel 1",
            final_outcome="Done",
            embedding=[1.0, 0.0, 0.0],
            created_at=now,
        )

        # Record 2: 45 degree angle [1.0, 1.0, 0.0] -> cosine sim ~ 0.707
        rec_mid = EpisodicMemoryRecord(
            memory_id="rec_mid",
            actor_id="actor_1",
            agent_id="agent_1",
            cost_centre_id="cc_1",
            session_id="s1",
            task_prompt="Kernel 2",
            final_outcome="Done",
            embedding=[1.0, 1.0, 0.0],
            created_at=now,
        )

        # Record 3: Orthogonal [0.0, 1.0, 0.0] -> cosine sim = 0.0
        rec_ortho = EpisodicMemoryRecord(
            memory_id="rec_ortho",
            actor_id="actor_1",
            agent_id="agent_1",
            cost_centre_id="cc_1",
            session_id="s1",
            task_prompt="Kernel 3",
            final_outcome="Done",
            embedding=[0.0, 1.0, 0.0],
            created_at=now,
        )

        await store.store_record(rec_exact)
        await store.store_record(rec_mid)
        await store.store_record(rec_ortho)

        # Query along [1.0, 0.0, 0.0]
        query = MemoryQueryRequest(
            query_embedding=[1.0, 0.0, 0.0],
            top_k=2,
            similarity_threshold=0.5,
        )

        matches = await store.search_similar(query)

        assert len(matches) == 2
        # First match must be rec_exact with similarity 1.0
        assert matches[0].record.memory_id == "rec_exact"
        assert math.isclose(matches[0].similarity_score, 1.0, rel_tol=1e-4)

        # Second match must be rec_mid with similarity ~ 0.7071
        assert matches[1].record.memory_id == "rec_mid"
        assert math.isclose(matches[1].similarity_score, 1.0 / math.sqrt(2), rel_tol=1e-4)

    @pytest.mark.asyncio
    async def test_cosine_similarity_threshold_filtering(self) -> None:
        """Verifies results below similarity_threshold are excluded."""
        from src.memory.schemas import EpisodicMemoryRecord, MemoryQueryRequest
        from src.memory.store import InMemoryVectorMemoryStore

        store = InMemoryVectorMemoryStore()
        now = datetime.now(UTC)

        # Angle orthogonal to query
        rec_ortho = EpisodicMemoryRecord(
            memory_id="rec_low",
            actor_id="actor_1",
            agent_id="agent_1",
            cost_centre_id="cc_1",
            session_id="s1",
            task_prompt="Unrelated memory",
            final_outcome="Done",
            embedding=[0.0, 1.0, 0.0],
            created_at=now,
        )
        await store.store_record(rec_ortho)

        query = MemoryQueryRequest(
            query_embedding=[1.0, 0.0, 0.0],
            top_k=5,
            similarity_threshold=0.8,
        )

        matches = await store.search_similar(query)
        assert len(matches) == 0
