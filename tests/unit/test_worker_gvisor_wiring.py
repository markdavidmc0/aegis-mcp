"""Unit tests for Ephemeral Runner Wiring in Data Plane."""

import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.data_plane.gvisor_runner import EphemeralGVisorRunner
from src.data_plane.schemas import DataPlaneUserContext
from src.data_plane.worker import LocalToolDispatcher


@pytest.mark.asyncio
@pytest.mark.unit
async def test_dispatcher_uses_ephemeral_gvisor_runner_for_catalog_tools(
    tmp_path: Path,
) -> None:
    """Test LocalToolDispatcher dispatches catalog tools via EphemeralGVisorRunner."""
    tool_binary = tmp_path / "custom_tool.py"
    tool_binary.write_text("print('mock')", encoding="utf-8")

    catalog = {
        "tools": [
            {
                "name": "custom_tool",
                "entrypoint": "custom_tool.py",
                "description": "A catalog tool",
            }
        ]
    }
    (tmp_path / "catalog.json").write_text(json.dumps(catalog), encoding="utf-8")

    mock_runner = MagicMock(spec=EphemeralGVisorRunner)
    mock_runner.read_only_rootfs = True
    mock_runner.timeout_seconds = 10.0
    mock_runner.execute_tool = AsyncMock(
        return_value={
            "status": "success",
            "result": {"output": "sandboxed_val"},
        }
    )

    user_ctx = DataPlaneUserContext(
        user_id="user_123",
        role="engineer",
        scopes=["tools:execute:custom_tool"],
    )

    # LocalToolDispatcher should accept ephemeral_runner or wire it up
    dispatcher = LocalToolDispatcher(
        tools_dir=tmp_path,
        ephemeral_runner=mock_runner,
    )

    res = await dispatcher.dispatch_tool_call(
        tool_name="custom_tool",
        arguments={"arg": 42},
        user_context=user_ctx,
    )

    assert mock_runner.execute_tool.called
    call_kwargs = mock_runner.execute_tool.call_args.kwargs
    assert call_kwargs.get("tool_name") == "custom_tool"
    assert call_kwargs.get("arguments") == {"arg": 42}
    assert call_kwargs.get("user_context") == user_ctx
    assert res["jsonrpc"] == "2.0"
    assert "result" in res
    assert res["result"]["status"] == "SUCCESS"


@pytest.mark.asyncio
@pytest.mark.unit
async def test_dispatcher_ephemeral_runner_scope_violation_returns_32003(
    tmp_path: Path,
) -> None:
    """Test that scope violation in EphemeralGVisorRunner denies execution with -32003."""
    tool_binary = tmp_path / "secure_tool.py"
    tool_binary.write_text("print('secure')", encoding="utf-8")

    catalog = {
        "tools": [
            {
                "name": "secure_tool",
                "entrypoint": "secure_tool.py",
            }
        ]
    }
    (tmp_path / "catalog.json").write_text(json.dumps(catalog), encoding="utf-8")

    mock_runner = MagicMock(spec=EphemeralGVisorRunner)
    mock_runner.execute_tool = AsyncMock(
        return_value={
            "status": "error",
            "error": "Access denied: missing scope 'tools:execute:secure_tool'",
            "error_code": -32003,
        }
    )

    user_ctx = DataPlaneUserContext(
        user_id="user_unauthorized",
        role="viewer",
        scopes=["tools:execute:other_tool"],
    )

    dispatcher = LocalToolDispatcher(
        tools_dir=tmp_path,
        ephemeral_runner=mock_runner,
    )

    res = await dispatcher.dispatch_tool_call(
        tool_name="secure_tool",
        arguments={},
        user_context=user_ctx,
    )

    assert res["jsonrpc"] == "2.0"
    assert "error" in res
    assert res["error"]["code"] == -32003
    assert "access denied" in res["error"]["message"].lower() or "scope" in res["error"]["message"].lower()


@pytest.mark.asyncio
@pytest.mark.unit
async def test_dispatcher_ephemeral_runner_timeout_returns_32603(
    tmp_path: Path,
) -> None:
    """Test that execution timeouts in EphemeralGVisorRunner return -32603."""
    tool_binary = tmp_path / "timeout_tool.py"
    tool_binary.write_text("print('timeout')", encoding="utf-8")

    catalog = {
        "tools": [
            {
                "name": "timeout_tool",
                "entrypoint": "timeout_tool.py",
            }
        ]
    }
    (tmp_path / "catalog.json").write_text(json.dumps(catalog), encoding="utf-8")

    mock_runner = MagicMock(spec=EphemeralGVisorRunner)
    mock_runner.execute_tool = AsyncMock(
        return_value={
            "status": "error",
            "error": "Execution timed out after 0.5s in sandbox",
            "error_code": -32000,
        }
    )

    user_ctx = DataPlaneUserContext(
        user_id="user_timed",
        role="engineer",
        scopes=["tools:execute:timeout_tool"],
    )

    dispatcher = LocalToolDispatcher(
        tools_dir=tmp_path,
        ephemeral_runner=mock_runner,
    )

    res = await dispatcher.dispatch_tool_call(
        tool_name="timeout_tool",
        arguments={},
        user_context=user_ctx,
    )

    assert res["jsonrpc"] == "2.0"
    assert "error" in res
    assert res["error"]["code"] == -32603
    assert "timed out" in res["error"]["message"].lower()


@pytest.mark.asyncio
@pytest.mark.unit
async def test_dispatcher_default_wires_ephemeral_gvisor_runner_with_readonly_rootfs(
    tmp_path: Path,
) -> None:
    """Test that LocalToolDispatcher defaults to instantiating EphemeralGVisorRunner with read_only_rootfs=True."""
    dispatcher = LocalToolDispatcher(tools_dir=tmp_path)
    assert hasattr(dispatcher, "ephemeral_runner")
    assert isinstance(dispatcher.ephemeral_runner, EphemeralGVisorRunner)
    assert dispatcher.ephemeral_runner.read_only_rootfs is True
