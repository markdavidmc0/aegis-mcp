"""Unit and contract tests for multi-project agent hierarchy and 4-tuple attribution enrichment.

Strictly tests:
1. EnrichedAgentSpan Pydantic v2 domain model (frozen=True, extra="forbid").
2. extract_hierarchy_and_project parsing project names from various directory layouts.
3. Subagent delegation flow detection from session titles.
4. 4-tuple URN synthesis (urn:aegis:agent:{actor_id}:{agent_id}:{project_name}:{session_id}).
5. SQLite session schema reading and enrichment integration with mocked DB queries.
"""

from __future__ import annotations

import sqlite3
from typing import Any

import pytest
from pydantic import ValidationError
from src.orchestrator.telemetry_enricher import (
    EnrichedAgentSpan,
    enrich_session_record,
    extract_hierarchy_and_project,
)


@pytest.mark.unit
def test_enriched_agent_span_schema_strictness():
    """Verify EnrichedAgentSpan enforces immutability and forbids extra fields."""
    span = EnrichedAgentSpan(
        actor_id="usr_admin",
        agent_id="architect",
        project_name="aegis-mcp-control-plane",
        session_id="ses_abc123",
        parent_agent_id=None,
        delegation_flow=None,
        urn="urn:aegis:agent:usr_admin:architect:aegis-mcp-control-plane:ses_abc123",
    )
    assert span.actor_id == "usr_admin"
    assert span.agent_id == "architect"
    assert span.project_name == "aegis-mcp-control-plane"
    assert span.session_id == "ses_abc123"
    assert span.parent_agent_id is None
    assert span.delegation_flow is None
    assert span.urn == "urn:aegis:agent:usr_admin:architect:aegis-mcp-control-plane:ses_abc123"

    # Enforce frozen immutability
    with pytest.raises(ValidationError):
        span.agent_id = "code-reviewer"  # type: ignore[misc]

    # Enforce extra="forbid"
    with pytest.raises(ValidationError):
        EnrichedAgentSpan(
            actor_id="usr_admin",
            agent_id="architect",
            project_name="aegis-mcp-control-plane",
            session_id="ses_abc123",
            parent_agent_id=None,
            delegation_flow=None,
            urn="urn:aegis:agent:usr_admin:architect:aegis-mcp-control-plane:ses_abc123",
            unexpected_field="disallowed",  # type: ignore[call-arg]
        )


@pytest.mark.unit
@pytest.mark.parametrize(
    ("session_dir", "expected_project"),
    [
        ("/Users/markmcnaught/Repos/aegis-mcp-control-plane", "aegis-mcp-control-plane"),
        ("/Users/markmcnaught/Repos/semper-ai", "semper-ai"),
        ("/Users/markmcnaught/vault", "vault"),
        ("/Users/markmcnaught/dev/sandbox-tooling", "sandbox-tooling"),
        ("/Users/alice/projects/deep-research/", "deep-research"),
        ("repos/embedded-agent", "embedded-agent"),
        ("/workspace", "workspace"),
    ],
)
def test_extract_project_name_from_directories(session_dir: str, expected_project: str):
    """Verify parsing session_directory extracts clean project_name across path formats."""
    result = extract_hierarchy_and_project(
        session_directory=session_dir,
        session_title="Stand-alone discussion",
    )
    assert result["project_name"] == expected_project


@pytest.mark.unit
@pytest.mark.parametrize(
    ("title", "expected_parent", "expected_subagent", "expected_flow"),
    [
        (
            "Audit entire repository diff and verification gates (@code-reviewer subagent)",
            "architect",
            "code-reviewer",
            "architect ➔ code-reviewer",
        ),
        (
            "Green implementation for Sprints A, B, and C (@tdd-builder subagent)",
            "architect",
            "tdd-builder",
            "architect ➔ tdd-builder",
        ),
        (
            "Sandbox verification harness (@microworld-dev subagent)",
            "architect",
            "microworld-dev",
            "architect ➔ microworld-dev",
        ),
        (
            "Interaction spec and accessibility matrix (@ux-designer subagent)",
            "architect",
            "ux-designer",
            "architect ➔ ux-designer",
        ),
        (
            "Contract and failure diagnostic suites (@test-engineer subagent)",
            "architect",
            "test-engineer",
            "architect ➔ test-engineer",
        ),
        (
            "General architectural planning session",
            None,
            None,
            None,
        ),
        (
            "New session - 2026-09-18T10:00:00.000Z",
            None,
            None,
            None,
        ),
    ],
)
def test_extract_hierarchy_from_session_titles(
    title: str,
    expected_parent: str | None,
    expected_subagent: str | None,
    expected_flow: str | None,
):
    """Verify delegation hierarchy is detected from subagent annotations in session titles."""
    result = extract_hierarchy_and_project(
        session_directory="/Users/markmcnaught/Repos/aegis-mcp-control-plane",
        session_title=title,
    )
    assert result["parent_agent"] == expected_parent
    assert result["subagent"] == expected_subagent
    assert result["delegation_flow"] == expected_flow


@pytest.mark.unit
def test_synthesize_urn_and_enriched_span():
    """Verify correct 4-tuple URN synthesis and populated EnrichedAgentSpan."""
    enriched = enrich_session_record(
        actor_id="user_developer_1",
        session_id="ses_987654321",
        session_directory="/Users/markmcnaught/Repos/semper-ai",
        session_title="Phase 1: Code Mode & Monty Sandbox (@tdd-builder subagent)",
        default_agent_id="architect",
    )
    assert isinstance(enriched, EnrichedAgentSpan)
    assert enriched.actor_id == "user_developer_1"
    assert enriched.agent_id == "tdd-builder"
    assert enriched.parent_agent_id == "architect"
    assert enriched.project_name == "semper-ai"
    assert enriched.session_id == "ses_987654321"
    assert enriched.delegation_flow == "architect ➔ tdd-builder"
    assert (
        enriched.urn
        == "urn:aegis:agent:user_developer_1:tdd-builder:semper-ai:ses_987654321"
    )


@pytest.mark.unit
def test_enrich_session_record_standalone_default_agent():
    """Verify standalone session retains root agent and produces clean URN without delegation."""
    enriched = enrich_session_record(
        actor_id="usr_ops",
        session_id="ses_root_001",
        session_directory="/Users/markmcnaught/vault",
        session_title="Daily system status review",
        default_agent_id="architect",
    )
    assert enriched.agent_id == "architect"
    assert enriched.parent_agent_id is None
    assert enriched.delegation_flow is None
    assert enriched.project_name == "vault"
    assert enriched.urn == "urn:aegis:agent:usr_ops:architect:vault:ses_root_001"


@pytest.mark.unit
def test_sqlite_session_schema_reading_integration():
    """Verify enrichment correctly maps rows querying OpenCode SQLite session schema."""
    conn = sqlite3.connect(":memory:")
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE session (
            id text PRIMARY KEY,
            title text NOT NULL,
            directory text NOT NULL,
            agent text
        )
    """)

    sample_sessions: list[tuple[str, str, str, str | None]] = [
        (
            "ses_f6e2ac789ffefhy",
            "Audit diff against invariants (@code-reviewer subagent)",
            "/Users/markmcnaught/Repos/aegis-mcp-control-plane",
            "code-reviewer",
        ),
        (
            "ses_f72ef3f82ffeyIp",
            "New session - 2026-09-10T20:44:40.445Z",
            "/Users/markmcnaught/vault",
            None,
        ),
    ]

    cursor.executemany(
        "INSERT INTO session (id, title, directory, agent) VALUES (?, ?, ?, ?)",
        sample_sessions,
    )
    conn.commit()

    cursor.execute("SELECT id, title, directory, agent FROM session ORDER BY id ASC")
    rows: list[Any] = cursor.fetchall()

    enriched_records: list[EnrichedAgentSpan] = []
    for sess_id, title, directory, db_agent in rows:
        span = enrich_session_record(
            actor_id="local_user",
            session_id=sess_id,
            session_directory=directory,
            session_title=title,
            default_agent_id=db_agent or "architect",
        )
        enriched_records.append(span)

    conn.close()

    assert len(enriched_records) == 2

    # Check delegated session
    delegated = next(r for r in enriched_records if r.session_id == "ses_f6e2ac789ffefhy")
    assert delegated.agent_id == "code-reviewer"
    assert delegated.parent_agent_id == "architect"
    assert delegated.project_name == "aegis-mcp-control-plane"
    assert delegated.delegation_flow == "architect ➔ code-reviewer"
    assert (
        delegated.urn
        == "urn:aegis:agent:local_user:code-reviewer:aegis-mcp-control-plane:ses_f6e2ac789ffefhy"
    )

    # Check standalone vault session
    standalone = next(r for r in enriched_records if r.session_id == "ses_f72ef3f82ffeyIp")
    assert standalone.agent_id == "architect"
    assert standalone.parent_agent_id is None
    assert standalone.delegation_flow is None
    assert standalone.project_name == "vault"
    assert (
        standalone.urn
        == "urn:aegis:agent:local_user:architect:vault:ses_f72ef3f82ffeyIp"
    )
