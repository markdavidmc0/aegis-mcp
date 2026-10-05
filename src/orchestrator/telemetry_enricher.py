"""Multi-project agent hierarchy and 4-tuple attribution telemetry enricher.

Extracts project, agent hierarchy, and delegation flow from OpenCode session records,
synthesizing canonical 4-tuple Aegis URNs and enriched span attributes.
"""

from __future__ import annotations

import re
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

# Pattern detecting subagents in session titles, e.g. "(@code-reviewer subagent)" or "(@tdd-builder)"
SUBAGENT_PATTERN = re.compile(r"\(@([a-zA-Z0-9_\-]+)(?:\s+subagent)?\)")


class EnrichedAgentSpan(BaseModel):
    """Enriched domain model for multi-project agent hierarchy and 4-tuple attribution."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    actor_id: str = Field(..., description="Unique actor or caller identifier")
    agent_id: str = Field(..., description="Active executing agent identifier")
    project_name: str = Field(..., description="Target project or workspace name")
    session_id: str = Field(..., description="Execution session identifier")
    parent_agent_id: str | None = Field(
        default=None, description="Parent agent ID in delegation hierarchy"
    )
    delegation_flow: str | None = Field(
        default=None, description="Human-readable delegation path, e.g. parent ➔ subagent"
    )
    urn: str = Field(..., description="Canonical Aegis 4-tuple URN")


def extract_hierarchy_and_project(
    session_directory: str, session_title: str
) -> dict[str, str | None]:
    """Parse project name and delegation hierarchy from session directory and title.

    Args:
        session_directory: Working directory path of the session.
        session_title: Descriptive title or label of the session.

    Returns:
        dict containing 'project_name', 'parent_agent', 'subagent', and 'delegation_flow'.
    """
    cleaned_dir = session_directory.rstrip("/")
    path_parts = Path(cleaned_dir).parts
    project_name = path_parts[-1] if path_parts else "workspace"

    match = SUBAGENT_PATTERN.search(session_title)
    if match:
        subagent = match.group(1)
        parent_agent = "architect"
        delegation_flow = f"{parent_agent} ➔ {subagent}"
    else:
        subagent = None
        parent_agent = None
        delegation_flow = None

    return {
        "project_name": project_name,
        "parent_agent": parent_agent,
        "subagent": subagent,
        "delegation_flow": delegation_flow,
    }


def enrich_session_record(
    session_id: str,
    session_directory: str,
    session_title: str,
    actor_id: str = "markmcnaught",
    default_agent_id: str = "architect",
    agent_name: str | None = None,
) -> EnrichedAgentSpan:
    """Enrich a session record into a canonical EnrichedAgentSpan.

    Args:
        session_id: Unique session identifier.
        session_directory: Working directory of the session.
        session_title: Title or prompt summary of the session.
        actor_id: Identifier of the invoking actor / user.
        default_agent_id: Fallback agent identifier if no subagent detected.
        agent_name: Optional explicit agent override.

    Returns:
        EnrichedAgentSpan instance with strict validation and frozen immutability.
    """
    hierarchy = extract_hierarchy_and_project(
        session_directory=session_directory, session_title=session_title
    )
    project_name = hierarchy["project_name"] or "workspace"
    parent_agent = hierarchy["parent_agent"]
    detected_subagent = hierarchy["subagent"]
    delegation_flow = hierarchy["delegation_flow"]

    resolved_agent = agent_name or detected_subagent or default_agent_id
    urn = f"urn:aegis:agent:{actor_id}:{resolved_agent}:{project_name}:{session_id}"

    return EnrichedAgentSpan(
        actor_id=actor_id,
        agent_id=resolved_agent,
        project_name=project_name,
        session_id=session_id,
        parent_agent_id=parent_agent,
        delegation_flow=delegation_flow,
        urn=urn,
    )
