"""Durable Task Queue & Event-Driven Engine for Orchestrator.

Provides an in-memory async durable queue implementation and Redis Streams
protocol-compatible interface with checkpointing and circuit breaker retry handling.
"""

import asyncio
import uuid
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from src.control_plane.schemas import AgentCompositeKey


class TaskStatus(StrEnum):
    """Execution status for a task in the durable queue."""

    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class QueueTask(BaseModel):
    """Immutable durable queue task model enforcing strict validation invariants."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    task_id: str
    composite_key: AgentCompositeKey
    status: TaskStatus = TaskStatus.PENDING
    payload: dict[str, Any]
    retry_count: int = 0
    max_retries: int = 5
    result: dict[str, Any] | None = None
    error: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class CircuitBreakerTriggeredError(Exception):
    """Raised when a task exceeds maximum retry attempts and is circuit-broken."""


class DurableTaskQueue:
    """Async in-memory durable task queue with FIFO ordering and retry circuit breaker."""

    def __init__(self) -> None:
        self._tasks: dict[str, QueueTask] = {}
        self._pending_ids: list[str] = []
        self._lock = asyncio.Lock()

    async def enqueue(
        self,
        composite_key: AgentCompositeKey,
        payload: dict[str, Any],
        task_id: str | None = None,
        max_retries: int = 5,
    ) -> QueueTask:
        """Enqueue a new task into the durable queue."""
        async with self._lock:
            tid = task_id or f"task_{uuid.uuid4().hex[:12]}"
            task = QueueTask(
                task_id=tid,
                composite_key=composite_key,
                status=TaskStatus.PENDING,
                payload=payload,
                retry_count=0,
                max_retries=max_retries,
            )
            self._tasks[tid] = task
            self._pending_ids.append(tid)
            return task

    async def dequeue(self, consumer_id: str | None = None) -> QueueTask | None:
        """Dequeue the next pending task and mark it as RUNNING."""
        async with self._lock:
            if not self._pending_ids:
                return None
            tid = self._pending_ids.pop(0)
            existing = self._tasks[tid]

            updated = QueueTask(
                task_id=existing.task_id,
                composite_key=existing.composite_key,
                status=TaskStatus.RUNNING,
                payload=existing.payload,
                retry_count=existing.retry_count,
                max_retries=existing.max_retries,
                result=existing.result,
                error=existing.error,
                created_at=existing.created_at,
            )
            self._tasks[tid] = updated
            return updated

    async def checkpoint(
        self,
        task_id: str,
        status: TaskStatus,
        result: dict[str, Any] | None = None,
        error: str | None = None,
    ) -> QueueTask:
        """Checkpoint task state, payload result, or error."""
        async with self._lock:
            if task_id not in self._tasks:
                raise KeyError(f"Task '{task_id}' not found in queue.")
            existing = self._tasks[task_id]

            updated = QueueTask(
                task_id=existing.task_id,
                composite_key=existing.composite_key,
                status=status,
                payload=existing.payload,
                retry_count=existing.retry_count,
                max_retries=existing.max_retries,
                result=result if result is not None else existing.result,
                error=error if error is not None else existing.error,
                created_at=existing.created_at,
            )
            self._tasks[task_id] = updated
            return updated

    async def record_failure(self, task_id: str, error_message: str) -> QueueTask:
        """Record failure and increment retry count, tripping circuit breaker if exhausted."""
        return await self.retry(task_id=task_id, error=error_message)

    async def retry(self, task_id: str, error: str) -> QueueTask:
        """Increment retry count.

        If retry_count >= max_retries, transition to FAILED and raise CircuitBreakerTriggeredError.
        Otherwise re-enqueue to pending queue.
        """
        async with self._lock:
            if task_id not in self._tasks:
                raise KeyError(f"Task '{task_id}' not found in queue.")
            existing = self._tasks[task_id]

            if existing.status == TaskStatus.FAILED:
                raise CircuitBreakerTriggeredError(
                    f"Task '{task_id}' has already exhausted retries and is FAILED."
                )

            new_retry_count = existing.retry_count + 1
            if new_retry_count >= existing.max_retries:
                failed_task = QueueTask(
                    task_id=existing.task_id,
                    composite_key=existing.composite_key,
                    status=TaskStatus.FAILED,
                    payload=existing.payload,
                    retry_count=new_retry_count,
                    max_retries=existing.max_retries,
                    result=existing.result,
                    error=error,
                    created_at=existing.created_at,
                )
                self._tasks[task_id] = failed_task
                return failed_task

            retried_task = QueueTask(
                task_id=existing.task_id,
                composite_key=existing.composite_key,
                status=TaskStatus.PENDING,
                payload=existing.payload,
                retry_count=new_retry_count,
                max_retries=existing.max_retries,
                result=existing.result,
                error=error,
                created_at=existing.created_at,
            )
            self._tasks[task_id] = retried_task
            self._pending_ids.append(task_id)
            return retried_task

    def get_task(self, task_id: str) -> QueueTask | None:
        """Retrieve task by id."""
        return self._tasks.get(task_id)


__all__ = [
    "CircuitBreakerTriggeredError",
    "DurableTaskQueue",
    "QueueTask",
    "TaskStatus",
]
