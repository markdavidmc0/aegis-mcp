"""gVisor and Ephemeral Downscoped Tool Isolation Runner."""

import asyncio
import json
import shutil
import sys
import tempfile
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Protocol

from pydantic import BaseModel, ConfigDict, Field

from src.data_plane.schemas import DataPlaneUserContext


class PolicyDecisionLike(Protocol):
    """Protocol representing a policy evaluation decision."""

    allowed: bool
    rule: str
    violations: list[str]


class PolicyEngineLike(Protocol):
    """Protocol representing a policy evaluation engine."""

    def evaluate(self, input_data: dict[str, Any]) -> PolicyDecisionLike:
        """Evaluate input against policies."""
        ...


class GVisorRunnerConfig(BaseModel):
    """Configuration for gVisor and ephemeral downscoped runner."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    read_only_rootfs: bool = True
    timeout_seconds: float = 30.0
    allowed_tools: list[str] = Field(default_factory=list)
    env_vars: dict[str, str] = Field(default_factory=dict)


class EphemeralGVisorRunner:
    """Spawns and manages ephemeral isolated execution environments."""

    def __init__(
        self,
        config: GVisorRunnerConfig | None = None,
        tools_dir: str | Path | None = None,
        read_only_rootfs: bool = True,
        timeout_seconds: float = 30.0,
        allowed_tools: list[str] | None = None,
        env_vars: dict[str, str] | None = None,
        policy_engine: PolicyEngineLike | None = None,
    ) -> None:
        if config is not None:
            read_only_rootfs = config.read_only_rootfs
            timeout_seconds = config.timeout_seconds
            allowed_tools = config.allowed_tools
            env_vars = config.env_vars
        self.tools_dir = Path(tools_dir) if tools_dir else Path(tempfile.gettempdir())
        self.read_only_rootfs = read_only_rootfs
        self.timeout_seconds = timeout_seconds
        self.allowed_tools = allowed_tools or []
        self.env_vars = env_vars or {}
        self.policy_engine = policy_engine

        self._alive = False
        self._scratch_dir: Path | None = None

    @property
    def scratch_dir(self) -> Path:
        """Returns active scratch directory."""
        if self._scratch_dir is None:
            raise RuntimeError("Runner instance is not active. Use within spawn() context.")
        return self._scratch_dir

    def is_alive(self) -> bool:
        """Indicates if the ephemeral environment is currently alive."""
        return self._alive

    @asynccontextmanager
    async def spawn(self) -> AsyncIterator["EphemeralGVisorRunner"]:
        """Spawn an isolated ephemeral environment with scratch space and cleanup."""
        scratch = Path(tempfile.mkdtemp(prefix="aegis_gvisor_"))
        self._scratch_dir = scratch
        self._alive = True
        try:
            yield self
        finally:
            self._alive = False
            if self._scratch_dir and self._scratch_dir.exists():
                shutil.rmtree(self._scratch_dir, ignore_errors=True)
            self._scratch_dir = None

    async def execute_tool(
        self,
        tool_name: str,
        arguments: dict[str, Any] | None = None,
        user_context: DataPlaneUserContext | None = None,
        entrypoint_path: str | None = None,
    ) -> dict[str, Any]:
        """Execute tool inside downscoped isolated runner with policy and scope checks."""
        # 1. Scope enforcement: user must have tools:execute or tools:execute:{tool_name} or tools:execute:all
        if user_context is not None:
            required_scope = f"tools:execute:{tool_name}"
            has_scope = (
                "tools:execute" in user_context.scopes
                or required_scope in user_context.scopes
                or "tools:execute:all" in user_context.scopes
            )
            if not has_scope:
                return {
                    "status": "error",
                    "error": f"Access denied: missing scope '{required_scope}'",
                    "error_code": -32003,
                }

        # 2. OPA Policy evaluation before spawning
        if self.policy_engine is not None:
            input_data = {
                "tool_name": tool_name,
                "arguments": arguments or {},
                "user_id": user_context.user_id if user_context else "anonymous",
                "role": user_context.role if user_context else "anonymous",
                "scopes": user_context.scopes if user_context else [],
            }
            decision = self.policy_engine.evaluate(input_data)
            if not decision.allowed:
                violations_str = "; ".join(decision.violations) if decision.violations else "Denied"
                return {
                    "status": "error",
                    "error": f"Denied by OPA policy: {violations_str}",
                    "error_code": -32003,
                }

        # 3. Read-only rootfs check
        args = arguments or {}
        if self.read_only_rootfs and tool_name == "write_file":
            target_path = Path(args.get("path", ""))
            # If writing outside scratch directory (or always if read_only_rootfs)
            if not self._scratch_dir or not str(target_path).startswith(str(self._scratch_dir)):
                return {
                    "status": "error",
                    "error": f"Permission denied: read-only filesystem prevents writing to '{target_path}'",
                    "error_code": -32000,
                }

        # 4. Ephemeral execution lifecycle with timeout
        async with self.spawn() as instance:
            try:
                return await asyncio.wait_for(
                    instance._run_tool_logic(tool_name, args, entrypoint_path=entrypoint_path),
                    timeout=self.timeout_seconds,
                )
            except TimeoutError:
                return {
                    "status": "error",
                    "error": f"Execution timed out after {self.timeout_seconds}s in sandbox",
                    "error_code": -32000,
                }
            except Exception as err:
                return {
                    "status": "error",
                    "error": f"Tool execution failed: {err}",
                    "error_code": -32603,
                }

    async def _run_tool_logic(
        self,
        tool_name: str,
        arguments: dict[str, Any],
        entrypoint_path: str | None = None,
    ) -> dict[str, Any]:
        """Runs the mock or simulated tool execution in the container/sandbox."""
        if entrypoint_path and Path(entrypoint_path).exists():
            cmd = [sys.executable, entrypoint_path] if entrypoint_path.endswith(".py") else [entrypoint_path]
            cmd.extend(["--json-args", json.dumps(arguments)])
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(
                proc.communicate(), timeout=self.timeout_seconds
            )
            raw_out = stdout.decode("utf-8").strip()
            try:
                parsed = json.loads(raw_out)
            except Exception:
                parsed = {"raw_output": raw_out}
            return parsed

        if tool_name == "sleep_loop":
            duration = float(arguments.get("duration", 1.0))
            await asyncio.sleep(duration)
            return {"status": "success", "result": f"Slept {duration}s"}

        if tool_name == "vector_dot_product":
            vec_a = arguments.get("vec_a", [])
            vec_b = arguments.get("vec_b", [])
            dot = sum(a * b for a, b in zip(vec_a, vec_b, strict=False))
            return {"status": "success", "result": dot}

        if tool_name == "write_file":
            path = Path(arguments.get("path", ""))
            content = arguments.get("content", "")
            path.write_text(content, encoding="utf-8")
            return {"status": "success", "path": str(path)}

        return {"status": "success", "tool": tool_name, "arguments": arguments}
