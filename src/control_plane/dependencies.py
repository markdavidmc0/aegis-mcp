"""Control Plane FastAPI Dependencies."""

import os
from collections.abc import AsyncGenerator

import httpx
from fastapi import Header, HTTPException, status

from src.config import get_settings
from src.control_plane.oidc import extract_claims_from_token, validate_keycloak_jwt
from src.control_plane.schemas import AgentCompositeKey, UserContext


async def get_user_context(
    authorization: str | None = Header(None, alias="Authorization"),
    x_user_id: str | None = Header(None, alias="X-User-ID"),
    x_actor_id: str | None = Header(None, alias="X-Actor-ID"),
    x_agent_id: str | None = Header("default-agent", alias="X-Agent-ID"),
    x_cost_centre_id: str | None = Header("default-cost-centre", alias="X-Cost-Centre-ID"),
    x_session_id: str | None = Header("default-session", alias="X-Session-ID"),
    x_user_role: str | None = Header("user", alias="X-User-Role"),
    x_user_scopes: str | None = Header("", alias="X-User-Scopes"),
) -> UserContext:
    """Extracts and validates downstream Envoy identity and composite agent headers or OIDC Bearer tokens."""
    # Check if OIDC is explicitly enabled or Authorization header is provided
    oidc_enabled = os.getenv("OIDC_ENABLED", "false").lower() in ("true", "1", "yes")

    if authorization or oidc_enabled:
        if not authorization:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Missing Authorization header",
            )
        parts = authorization.split()
        if len(parts) != 2 or parts[0].lower() != "bearer":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid Authorization header format. Expected 'Bearer <token>'",
            )
        token = parts[1]
        payload = validate_keycloak_jwt(token)
        return extract_claims_from_token(
            payload,
            fallback_actor_id=x_actor_id,
            fallback_agent_id=x_agent_id,
            fallback_cost_centre_id=x_cost_centre_id,
            fallback_session_id=x_session_id,
        )

    effective_actor = (x_actor_id.strip() if x_actor_id and x_actor_id.strip() else None)
    effective_user = (x_user_id.strip() if x_user_id and x_user_id.strip() else None)

    actor = effective_actor or effective_user
    if not actor:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing required upstream identity header: X-User-ID",
        )

    # Ensures whitespace-only roles default back to "user"
    cleaned_role = x_user_role.strip() if x_user_role and x_user_role.strip() else "user"
    scopes = [s.strip() for s in x_user_scopes.split(",") if s.strip()] if x_user_scopes else []

    agent = x_agent_id.strip() if x_agent_id and x_agent_id.strip() else "default-agent"
    cost_centre = (
        x_cost_centre_id.strip()
        if x_cost_centre_id and x_cost_centre_id.strip()
        else "default-cost-centre"
    )
    session = x_session_id.strip() if x_session_id and x_session_id.strip() else "default-session"

    try:
        composite_key = AgentCompositeKey(
            actor_id=actor,
            agent_id=agent,
            cost_centre_id=cost_centre,
            session_id=session,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid composite identity headers: {exc}",
        ) from exc

    return UserContext(
        user_id=effective_user or actor,
        role=cleaned_role,
        scopes=scopes,
        composite_key=composite_key,
    )


async def get_data_plane_client() -> AsyncGenerator[httpx.AsyncClient, None]:
    """Provides an HTTP/2 AsyncClient for forwarding requests to Data Plane."""
    settings = get_settings()
    async with httpx.AsyncClient(
        base_url=settings.DATA_PLANE_URL,
        timeout=settings.DATA_PLANE_TIMEOUT_SECONDS,
        http2=True,
    ) as client:
        yield client
