"""Unit tests for Durable Task Queue & Event-Driven Engine."""

from datetime import datetime

import pytest
from pydantic import ValidationError

from src.control_plane.schemas import AgentCompositeKey


@pytest.mark.unit
class TestDurableQueueContracts:
    """Validate schemas, invariants, and queue contracts for DurableTaskQueue."""

    def test_queue_task_schema_invariants(self) -> None:
        """Validate QueueTask enforces strict invariants (frozen=True, extra='forbid')."""
        from src.orchestrator.queue import QueueTask, TaskStatus

        key = AgentCompositeKey(
            actor_id="usr_123",
            agent_id="agt_worker",
            cost_centre_id="dept_ai",
            session_id="sess_abc",
        )
        task = QueueTask(
            task_id="task_001",
            composite_key=key,
            status=TaskStatus.PENDING,
            payload={"action": "analyze", "data": "test"},
            retry_count=0,
            max_retries=5,
        )

        assert task.task_id == "task_001"
        assert task.composite_key == key
        assert task.status == TaskStatus.PENDING
        assert task.payload == {"action": "analyze", "data": "test"}
        assert task.retry_count == 0
        assert task.max_retries == 5
        assert isinstance(task.created_at, datetime)

        # Immutability check
        with pytest.raises((ValidationError, TypeError)):
            task.status = TaskStatus.RUNNING  # type: ignore[misc]

        # Forbid extra fields check
        with pytest.raises(ValidationError):
            QueueTask(
                task_id="task_002",
                composite_key=key,
                status=TaskStatus.PENDING,
                payload={},
                unauthorized_field="illegal",  # type: ignore[call-arg]
            )

    def test_task_status_enum_values(self) -> None:
        """Validate TaskStatus enum contains PENDING, RUNNING, COMPLETED, FAILED."""
        from src.orchestrator.queue import TaskStatus

        assert TaskStatus.PENDING == "PENDING"
        assert TaskStatus.RUNNING == "RUNNING"
        assert TaskStatus.COMPLETED == "COMPLETED"
        assert TaskStatus.FAILED == "FAILED"


@pytest.mark.unit
class TestDurableTaskQueueOperations:
    """Validate enqueueing, consumer dequeueing, checkpointing, and retry handling."""

    @pytest.fixture
    def composite_key(self) -> AgentCompositeKey:
        """Fixture providing a valid 4-tuple AgentCompositeKey for tests."""
        return AgentCompositeKey(
            actor_id="usr_alice",
            agent_id="agt_researcher",
            cost_centre_id="cc_01",
            session_id="sess_01",
        )

    @pytest.mark.asyncio
    async def test_enqueue_and_dequeue_flow(self, composite_key: AgentCompositeKey) -> None:
        """Test enqueueing task and consumer dequeueing with state tracking."""
        from src.orchestrator.queue import DurableTaskQueue, TaskStatus

        queue = DurableTaskQueue()
        task = await queue.enqueue(
            composite_key=composite_key,
            payload={"job": "index_papers"},
        )

        assert task.task_id is not None
        assert task.composite_key == composite_key
        assert task.status == TaskStatus.PENDING
        assert task.payload == {"job": "index_papers"}

        # Dequeue
        dequeued = await queue.dequeue(consumer_id="consumer_1")
        assert dequeued is not None
        assert dequeued.task_id == task.task_id
        assert dequeued.status == TaskStatus.RUNNING

    @pytest.mark.asyncio
    async def test_checkpoint_completion(self, composite_key: AgentCompositeKey) -> None:
        """Test checkpointing a task as COMPLETED with output payload."""
        from src.orchestrator.queue import DurableTaskQueue, TaskStatus

        queue = DurableTaskQueue()
        task = await queue.enqueue(composite_key=composite_key, payload={"job": "train"})
        dequeued = await queue.dequeue(consumer_id="consumer_1")
        assert dequeued is not None

        completed_task = await queue.checkpoint(
            task_id=task.task_id,
            status=TaskStatus.COMPLETED,
            result={"status": "ok", "loss": 0.01},
        )

        assert completed_task.status == TaskStatus.COMPLETED
        assert completed_task.result == {"status": "ok", "loss": 0.01}

    @pytest.mark.asyncio
    async def test_retry_handling_circuit_breaker(self, composite_key: AgentCompositeKey) -> None:
        """Test retry handling up to 5 attempts (Circuit Breaker) before marking as FAILED."""
        from src.orchestrator.queue import (
            CircuitBreakerTriggeredError,
            DurableTaskQueue,
            TaskStatus,
        )

        queue = DurableTaskQueue()
        task = await queue.enqueue(
            composite_key=composite_key,
            payload={"job": "fragile_work"},
            max_retries=5,
        )

        # Retry 5 times
        for attempt in range(1, 6):
            dequeued = await queue.dequeue(consumer_id="worker_fail")
            assert dequeued is not None
            assert dequeued.task_id == task.task_id

            retried = await queue.record_failure(
                task_id=task.task_id,
                error_message=f"Transient failure #{attempt}",
            )
            if attempt < 5:
                assert retried.status == TaskStatus.PENDING
                assert retried.retry_count == attempt
            else:
                # 5th attempt exhausts retries -> FAILED
                assert retried.status == TaskStatus.FAILED
                assert retried.retry_count == 5

        # Attempting further dequeue should return None (queue empty or task dead-lettered)
        next_task = await queue.dequeue(consumer_id="worker_fail")
        assert next_task is None

        # Attempting to retry an already failed task raises CircuitBreakerTriggeredError
        with pytest.raises(CircuitBreakerTriggeredError):
            await queue.record_failure(
                task_id=task.task_id,
                error_message="Attempt beyond circuit breaker",
            )
