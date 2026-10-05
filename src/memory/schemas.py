"""Episodic Memory Schemas."""

from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class EpisodicMemoryRecord(BaseModel):
    """Immutable episodic run execution record with vector embeddings."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    memory_id: str = Field(..., min_length=1)
    actor_id: str = Field(..., min_length=1)
    agent_id: str = Field(..., min_length=1)
    cost_centre_id: str = Field(..., min_length=1)
    session_id: str = Field(..., min_length=1)
    task_prompt: str = Field(..., min_length=1)
    final_outcome: str = Field(..., min_length=1)
    embedding: list[float] = Field(..., min_length=1)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    metadata: dict[str, Any] = Field(default_factory=dict)


class MemoryQueryRequest(BaseModel):
    """Query model for vector similarity search over episodic memory records."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    query_embedding: list[float] = Field(..., min_length=1)
    top_k: int = Field(default=5, ge=1, le=100)
    similarity_threshold: float = Field(default=0.0, ge=-1.0, le=1.0)
    cost_centre_id: str | None = None
    actor_id: str | None = None
    agent_id: str | None = None


class MemoryQueryResult(BaseModel):
    """Result of vector similarity search containing matching record and score."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    record: EpisodicMemoryRecord
    similarity_score: float = Field(..., ge=-1.0, le=1.0)


# Aliases for compatibility
EpisodicRecord = EpisodicMemoryRecord
MemoryQuery = MemoryQueryRequest
