"""Unit tests for GVisor and Ephemeral Downscoped Tool Isolation Runner."""

from pathlib import Path
from unittest.mock import MagicMock

import pytest
from pydantic import ValidationError

from src.data_plane.schemas import DataPlaneUserContext


@pytest.mark.unit
class TestGVisorDispatcherUnit:
    """Unit test suite for secondary downscoped tool isolation and gVisor runner."""

    def test_ephemeral_runner_config_invariants(self) -> None:
        """Verifies GVisorRunnerConfig enforces strict schema invariants (frozen, extra=forbid)."""
        from src.data_plane.gvisor_runner import GVisorRunnerConfig

        config = GVisorRunnerConfig(
            read_only_rootfs=True,
            timeout_seconds=5.0,
            allowed_tools=["calculator"],
            env_vars={"ENV": "sandbox"},
        )
        assert config.read_only_rootfs is True
        assert config.timeout_seconds == 5.0
        assert config.allowed_tools == ["calculator"]
        assert config.env_vars == {"ENV": "sandbox"}

        # Immutability invariant
        with pytest.raises((ValidationError, TypeError)):
            config.timeout_seconds = 10.0  # type: ignore[misc]

        # Forbid extra fields invariant
        with pytest.raises(ValidationError):
            GVisorRunnerConfig(
                read_only_rootfs=True,
                extra_field="disallowed",  # type: ignore[call-arg]
            )

    @pytest.mark.asyncio
    async def test_ephemeral_runner_instantiation_and_lifecycle(self, tmp_path: Path) -> None:
        """Verifies ephemeral runner instantiates with isolated scratch directory and cleans up."""
        from src.data_plane.gvisor_runner import EphemeralGVisorRunner

        runner = EphemeralGVisorRunner(
            tools_dir=tmp_path,
            read_only_rootfs=True,
            timeout_seconds=2.0,
        )

        assert runner.read_only_rootfs is True
        assert runner.timeout_seconds == 2.0
        assert runner.is_alive() is False

        async with runner.spawn() as instance:
            assert instance.is_alive() is True
            assert instance.scratch_dir.exists()
            scratch_path = instance.scratch_dir

        # Verifies teardown and cleanup upon exit
        assert runner.is_alive() is False
        assert not scratch_path.exists()

    @pytest.mark.asyncio
    async def test_downscoped_scope_permission_enforcement_allowed(self) -> None:
        """Verifies execution succeeds when caller has the specific downscoped tool grant."""
        from src.data_plane.gvisor_runner import EphemeralGVisorRunner

        runner = EphemeralGVisorRunner()
        # Specific grant for 'vector_dot_product'
        scoped_user = DataPlaneUserContext(
            user_id="actor_99",
            role="agent",
            scopes=["tools:execute:vector_dot_product"],
        )

        result = await runner.execute_tool(
            tool_name="vector_dot_product",
            arguments={"vec_a": [1, 2], "vec_b": [3, 4]},
            user_context=scoped_user,
        )
        assert result["status"] == "success"

    @pytest.mark.asyncio
    async def test_downscoped_scope_permission_enforcement_denied(self) -> None:
        """Verifies execution is denied when caller lacks scope for the requested tool."""
        from src.data_plane.gvisor_runner import EphemeralGVisorRunner

        runner = EphemeralGVisorRunner()
        # Caller only has grant for 'matrix_mult', but requests 'delete_table'
        scoped_user = DataPlaneUserContext(
            user_id="actor_99",
            role="agent",
            scopes=["tools:execute:matrix_mult"],
        )

        result = await runner.execute_tool(
            tool_name="delete_table",
            arguments={"table": "users"},
            user_context=scoped_user,
        )
        assert result["status"] == "error"
        assert "access denied" in result["error"].lower() or "scope" in result["error"].lower()
        assert result.get("error_code") == -32003

    @pytest.mark.asyncio
    async def test_isolation_invariant_blocks_filesystem_writes(self, tmp_path: Path) -> None:
        """Verifies isolation invariants strictly block unauthorized filesystem writes in read-only mode."""
        from src.data_plane.gvisor_runner import EphemeralGVisorRunner

        runner = EphemeralGVisorRunner(read_only_rootfs=True)
        scoped_user = DataPlaneUserContext(
            user_id="actor_write_test",
            role="agent",
            scopes=["tools:execute:write_file"],
        )

        # Attempting to write to rootfs or unauthorized location outside scratch space
        result = await runner.execute_tool(
            tool_name="write_file",
            arguments={"path": "/etc/injected_payload.sh", "content": "rm -rf /"},
            user_context=scoped_user,
        )
        assert result["status"] == "error"
        assert "read-only" in result["error"].lower() or "permission denied" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_isolation_timeout_enforcement(self) -> None:
        """Verifies runner kills process and returns timeout error when execution exceeds bound."""
        from src.data_plane.gvisor_runner import EphemeralGVisorRunner

        runner = EphemeralGVisorRunner(timeout_seconds=0.1)
        scoped_user = DataPlaneUserContext(
            user_id="actor_timeout",
            role="agent",
            scopes=["tools:execute:sleep_loop"],
        )

        result = await runner.execute_tool(
            tool_name="sleep_loop",
            arguments={"duration": 5.0},
            user_context=scoped_user,
        )
        assert result["status"] == "error"
        assert "timed out" in result["error"].lower()
        assert result.get("error_code") in [-32603, -32000]

    @pytest.mark.asyncio
    async def test_opa_policy_evaluation_before_spawning(self) -> None:
        """Verifies OPA policy engine is evaluated prior to container/runner instantiation."""
        from src.data_plane.gvisor_runner import EphemeralGVisorRunner

        from src.control_plane.policy_engine import PolicyEngine

        mock_policy_engine = MagicMock(spec=PolicyEngine)
        from src.control_plane.schemas import PolicyDecision

        # Policy rejects spawning
        mock_policy_engine.evaluate.return_value = PolicyDecision(
            allowed=False,
            rule="aegis.tools.sandbox.allow",
            violations=["Spawning unvetted container runner denied by OPA policy"],
        )

        runner = EphemeralGVisorRunner(policy_engine=mock_policy_engine)
        user_ctx = DataPlaneUserContext(
            user_id="actor_opa",
            role="agent",
            scopes=["tools:execute:all"],
        )

        result = await runner.execute_tool(
            tool_name="restricted_tool",
            arguments={},
            user_context=user_ctx,
        )

        assert result["status"] == "error"
        assert "denied by opa" in result["error"].lower() or "policy" in result["error"].lower()
        assert mock_policy_engine.evaluate.called
