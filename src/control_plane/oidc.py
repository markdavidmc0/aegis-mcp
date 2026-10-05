"""Keycloak OIDC JWT token validation and extraction utilities."""

import os
from typing import Any

import jwt
from fastapi import HTTPException, status
from pydantic import BaseModel, ConfigDict, Field

from src.control_plane.schemas import AgentCompositeKey, UserContext


class TokenValidationConfig(BaseModel):
    """Configuration for OIDC token validation."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    secret: str = Field(default="")
    algorithm: str = Field(default="HS256")
    issuer: str | None = None
    audience: str | None = None


def validate_keycloak_jwt(token: str) -> dict[str, Any]:
    """Validate and decode Keycloak JWT token.

    Supports HS256/RS256 algorithms. Raises HTTPException 401 if invalid or expired.
    """
    secret = os.getenv("OIDC_JWT_SECRET", "test-jwt-secret-key-for-unit-tests-only")
    algorithm = os.getenv("OIDC_ALGORITHM", "HS256")

    # Clean token string
    token = token.strip()
    if not token or token.count(".") != 2:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Malformed JWT token",
        )

    try:
        payload = jwt.decode(
            token,
            secret,
            algorithms=[algorithm],
            options={
                "verify_signature": True,
                "verify_exp": True,
                "verify_nbf": True,
                "verify_iat": True,
                "verify_aud": False,
            },
        )
        return payload
    except jwt.ExpiredSignatureError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token signature has expired",
        ) from exc
    except jwt.InvalidTokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token signature: {exc}",
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Failed to decode token: {exc}",
        ) from exc


def extract_claims_from_token(
    payload: dict[str, Any],
    fallback_actor_id: str | None = None,
    fallback_agent_id: str | None = None,
    fallback_cost_centre_id: str | None = None,
    fallback_session_id: str | None = None,
) -> UserContext:
    """Extract canonical UserContext and 4-tuple AgentCompositeKey from decoded token payload.

    Falls back to Envoy header parameters if token claims are absent or None.
    """
    sub = payload.get("sub") or "anonymous"

    # Extract roles
    roles: list[str] = []
    realm_access = payload.get("realm_access")
    if isinstance(realm_access, dict):
        roles = realm_access.get("roles", [])
    primary_role = roles[0] if roles else payload.get("role", "user")

    # Extract scopes
    scopes_claim = payload.get("scope", "")
    if isinstance(scopes_claim, str):
        scopes = [s.strip() for s in scopes_claim.split() if s.strip()]
    elif isinstance(scopes_claim, list):
        scopes = [str(s).strip() for s in scopes_claim if str(s).strip()]
    else:
        scopes = []

    # Extract 4-tuple claims
    actor_id = payload.get("actor_id") or fallback_actor_id or sub
    agent_id = payload.get("agent_id") or fallback_agent_id or "default-agent"
    cost_centre_id = payload.get("cost_centre_id") or fallback_cost_centre_id or "default-cost-centre"
    session_id = payload.get("session_id") or fallback_session_id or "default-session"

    composite_key = AgentCompositeKey(
        actor_id=actor_id,
        agent_id=agent_id,
        cost_centre_id=cost_centre_id,
        session_id=session_id,
    )

    return UserContext(
        user_id=sub,
        role=primary_role,
        scopes=scopes,
        composite_key=composite_key,
    )
