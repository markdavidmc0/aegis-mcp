"""Unit tests for Keycloak OIDC JWT token validation and Envoy Edge Guard headers."""

import time
from typing import Any

import jwt
import pytest
from fastapi import HTTPException

from src.control_plane.dependencies import get_user_context
from src.control_plane.schemas import UserContext

TEST_SECRET = "test-jwt-secret-key-for-unit-tests-only"
TEST_ALGORITHM = "HS256"


def create_test_jwt(
    payload: dict[str, Any] | None = None,
    secret: str = TEST_SECRET,
    algorithm: str = TEST_ALGORITHM,
    expires_in: int = 3600,
) -> str:
    """Helper to generate JWT tokens with configurable claims and expiry."""
    now = int(time.time())
    base_claims: dict[str, Any] = {
        "sub": "user_kc_12345",
        "iss": "http://keycloak.aegis.local/realms/aegis",
        "aud": "aegis-mcp-control-plane",
        "exp": now + expires_in,
        "nbf": now - 10,
        "iat": now,
        "realm_access": {"roles": ["engineer", "admin"]},
        "scope": "openid email profile tools:execute",
        "actor_id": "actor_dev_01",
        "agent_id": "agent_code_v2",
        "cost_centre_id": "cc_deeplearning_09",
        "session_id": "sess_live_9981",
    }
    if payload:
        base_claims.update(payload)
    return jwt.encode(base_claims, secret, algorithm=algorithm)


@pytest.mark.unit
@pytest.mark.unauthenticated
class TestKeycloakOIDCAuthUnit:
    """Unit test suite for Keycloak OIDC JWT parsing, validation, and 4-tuple claims extraction."""

    @pytest.mark.asyncio
    async def test_valid_keycloak_jwt_parsing_with_4tuple(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Verifies valid Keycloak token parses and correctly extracts 4-tuple composite key."""
        monkeypatch.setenv("OIDC_ENABLED", "true")
        monkeypatch.setenv("OIDC_JWT_SECRET", TEST_SECRET)
        monkeypatch.setenv("OIDC_ALGORITHM", TEST_ALGORITHM)

        token = create_test_jwt(
            payload={
                "actor_id": "actor_prod_01",
                "agent_id": "agent_optimizer",
                "cost_centre_id": "cc_platform_12",
                "session_id": "sess_88320",
                "realm_access": {"roles": ["architect"]},
            }
        )

        auth_header = f"Bearer {token}"
        ctx: UserContext = await get_user_context(
            authorization=auth_header,
        )

        assert ctx.user_id == "user_kc_12345"
        assert ctx.role == "architect"
        assert "tools:execute" in ctx.scopes
        assert ctx.composite_key is not None
        assert ctx.composite_key.actor_id == "actor_prod_01"
        assert ctx.composite_key.agent_id == "agent_optimizer"
        assert ctx.composite_key.cost_centre_id == "cc_platform_12"
        assert ctx.composite_key.session_id == "sess_88320"
        assert (
            ctx.composite_key.urn
            == "urn:aegis:agent:actor_prod_01:agent_optimizer:cc_platform_12:sess_88320"
        )

    @pytest.mark.asyncio
    async def test_expired_token_rejection(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Verifies expired Keycloak tokens are rejected with 401 Unauthorized."""
        monkeypatch.setenv("OIDC_ENABLED", "true")
        monkeypatch.setenv("OIDC_JWT_SECRET", TEST_SECRET)

        expired_token = create_test_jwt(expires_in=-300)
        auth_header = f"Bearer {expired_token}"

        with pytest.raises(HTTPException) as exc_info:
            await get_user_context(authorization=auth_header)

        assert exc_info.value.status_code == 401
        assert "expired" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    async def test_invalid_signature_rejection(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Verifies JWT signed with mismatched secret is rejected with 401 Unauthorized."""
        monkeypatch.setenv("OIDC_ENABLED", "true")
        monkeypatch.setenv("OIDC_JWT_SECRET", TEST_SECRET)

        tampered_token = create_test_jwt(secret="wrong-secret-key-that-is-at-least-32-bytes-long")
        auth_header = f"Bearer {tampered_token}"

        with pytest.raises(HTTPException) as exc_info:
            await get_user_context(authorization=auth_header)

        assert exc_info.value.status_code == 401
        assert "signature" in exc_info.value.detail.lower() or "invalid" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    async def test_missing_claims_handling(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Verifies missing 4-tuple claims fallback cleanly to Envoy headers or defaults without 500 error."""
        monkeypatch.setenv("OIDC_ENABLED", "true")
        monkeypatch.setenv("OIDC_JWT_SECRET", TEST_SECRET)

        # Token missing actor_id, agent_id, cost_centre_id, session_id claims
        token_missing_claims = create_test_jwt(
            payload={
                "actor_id": None,
                "agent_id": None,
                "cost_centre_id": None,
                "session_id": None,
            }
        )
        auth_header = f"Bearer {token_missing_claims}"

        # Envoy headers provide fallback identity
        ctx: UserContext = await get_user_context(
            authorization=auth_header,
            x_actor_id="envoy_actor_fallback",
            x_agent_id="envoy_agent_fallback",
            x_cost_centre_id="envoy_cc_fallback",
            x_session_id="envoy_sess_fallback",
        )

        assert ctx.composite_key is not None
        assert ctx.composite_key.actor_id == "envoy_actor_fallback"
        assert ctx.composite_key.agent_id == "envoy_agent_fallback"
        assert ctx.composite_key.cost_centre_id == "envoy_cc_fallback"
        assert ctx.composite_key.session_id == "envoy_sess_fallback"

    @pytest.mark.asyncio
    async def test_malformed_bearer_header_rejection(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Verifies malformed Authorization header values trigger 401."""
        monkeypatch.setenv("OIDC_ENABLED", "true")

        with pytest.raises(HTTPException) as exc_info:
            await get_user_context(authorization="Basic invalid-auth-format")

        assert exc_info.value.status_code == 401

        with pytest.raises(HTTPException) as exc_info2:
            await get_user_context(authorization="Bearer not.a.valid.jwt")

        assert exc_info2.value.status_code == 401
