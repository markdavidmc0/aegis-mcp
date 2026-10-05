"""In-memory and PGVector episodic vector memory store implementation."""

import math
from typing import Protocol

from src.memory.schemas import (
    EpisodicMemoryRecord,
    MemoryQueryRequest,
    MemoryQueryResult,
)


class VectorMemoryStore(Protocol):
    """Protocol interface for episodic vector memory stores."""

    async def store_record(self, record: EpisodicMemoryRecord) -> None:
        """Store an episodic memory record."""
        ...

    async def get_record(self, memory_id: str) -> EpisodicMemoryRecord | None:
        """Retrieve record by ID."""
        ...

    async def search_similar(self, query: MemoryQueryRequest) -> list[MemoryQueryResult]:
        """Search similar episodic records using cosine similarity."""
        ...


def compute_cosine_similarity(vec_a: list[float], vec_b: list[float]) -> float:
    """Compute cosine similarity between two float vectors."""
    if len(vec_a) != len(vec_b) or not vec_a:
        return 0.0

    dot_product = sum(a * b for a, b in zip(vec_a, vec_b, strict=False))
    norm_a = math.sqrt(sum(a * a for a in vec_a))
    norm_b = math.sqrt(sum(b * b for b in vec_b))

    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0

    return dot_product / (norm_a * norm_b)


class InMemoryVectorMemoryStore:
    """In-memory episodic memory store with cosine similarity ranking."""

    def __init__(self) -> None:
        self._records: dict[str, EpisodicMemoryRecord] = {}

    async def store_record(self, record: EpisodicMemoryRecord) -> None:
        """Store or replace an episodic memory record."""
        self._records[record.memory_id] = record

    async def get_record(self, memory_id: str) -> EpisodicMemoryRecord | None:
        """Retrieve record by ID."""
        return self._records.get(memory_id)

    async def search_similar(self, query: MemoryQueryRequest) -> list[MemoryQueryResult]:
        """Search similar episodic records using cosine similarity."""
        scored_records: list[MemoryQueryResult] = []

        for record in self._records.values():
            if query.cost_centre_id and record.cost_centre_id != query.cost_centre_id:
                continue
            if query.actor_id and record.actor_id != query.actor_id:
                continue
            if query.agent_id and record.agent_id != query.agent_id:
                continue

            similarity = compute_cosine_similarity(query.query_embedding, record.embedding)
            if similarity >= query.similarity_threshold:
                scored_records.append(
                    MemoryQueryResult(
                        record=record,
                        similarity_score=similarity,
                    )
                )

        # Sort descending by similarity score
        scored_records.sort(key=lambda item: item.similarity_score, reverse=True)

        return scored_records[: query.top_k]
