"""Schemas for Autonomous Research Scout and DSPy Prompt Optimization."""

from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class PaperScoutResult(BaseModel):
    """Result of an arXiv or literature paper scout analysis."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    paper_id: str
    title: str
    authors: list[str] = Field(default_factory=list)
    abstract: str
    keywords: list[str] = Field(default_factory=list)
    published_date: datetime = Field(default_factory=lambda: datetime.now(UTC))
    arxiv_url: str | None = None
    pdf_url: str | None = None
    url: str | None = None
    relevance_score: float = Field(default=0.0, ge=0.0, le=1.0)


class PromptOptimizationResult(BaseModel):
    """Result of a prompt optimization loop using DSPy or automated teleprompters."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    optimization_id: str | None = None
    prompt_name: str | None = None
    agent_id: str | None = None
    original_prompt: str | None = None
    original_template: str | None = None
    optimized_prompt: str | None = None
    optimized_template: str | None = None
    baseline_score: float = Field(default=0.0, ge=0.0, le=1.0)
    optimized_score: float = Field(default=0.0, ge=0.0, le=1.0)
    metric_name: str = "accuracy"
    token_reduction_pct: float = 0.0
    iteration: int = 1
    iterations_run: int = 1
    metadata: dict[str, Any] = Field(default_factory=dict)


__all__ = [
    "PaperScoutResult",
    "PromptOptimizationResult",
]
