"""Authentication API routes."""
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import httpx

from app.core.config import settings
from app.core.database import get_db
from app.core.security import (
    create_access_token,
    create_refresh_token,
    generate_csrf_token,
)
from app.core.oidc import oidc_client
from app.models import User, UserRole
from app.api.deps import get_current_user
from app.api.schemas import (
    TokenResponse,
    AuthCallbackRequest,
    UserResponse,
    ErrorResponse,
)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/login")
async def login(request: Request):
    """Initiate OIDC login flow."""
    if not settings.oidc_enabled:
        raise HTTPException(status_code=400, detail="OIDC not enabled")

    auth_url, state, nonce, pkce_verifier = oidc_client.build_authorization_url()

    # Store state, nonce, pkce_verifier in session (server-side for security)
    request.session["oidc_state"] = state
    request.session["oidc_nonce"] = nonce
    request.session["pkce_verifier"] = pkce_verifier
    request.session["csrf_token"] = generate_csrf_token()

    return RedirectResponse(url=auth_url, status_code=302)


@router.get("/callback")
async def callback(
    request: Request,
    code: str = None,
    state: str = None,
    error: str = None,
    error_description: str = None,
    db: AsyncSession = Depends(get_db),
):
    """Handle OIDC callback."""
    if not settings.oidc_enabled:
        raise HTTPException(status_code=400, detail="OIDC not enabled")

    if error:
        raise HTTPException(status_code=400, detail=f"OIDC error: {error} - {error_description}")

    # Verify state
    stored_state = request.session.pop("oidc_state", None)
    if not stored_state or stored_state != state:
        raise HTTPException(status_code=400, detail="Invalid state parameter")

    nonce = request.session.pop("oidc_nonce", None)
    pkce_verifier = request.session.pop("pkce_verifier", None)

    if not nonce or not pkce_verifier:
        raise HTTPException(status_code=400, detail="Missing session data")

    # Exchange code for tokens
    try:
        token_response = await oidc_client.exchange_code_for_tokens(code, pkce_verifier)
    except httpx.HTTPError as e:
        raise HTTPException(status_code=400, detail=f"Token exchange failed: {e}")

    id_token = token_response.get("id_token")
    if not id_token:
        raise HTTPException(status_code=400, detail="No ID token in response")

    # Validate ID token
    claims = await oidc_client.validate_id_token(id_token, nonce)
    if not claims:
        raise HTTPException(status_code=400, detail="Invalid ID token")

    # Get or create user
    sub = claims.get("sub")
    email = claims.get("email")
    name = claims.get("name") or claims.get("preferred_username") or email

    if not sub or not email:
        raise HTTPException(status_code=400, detail="Missing required claims")

    result = await db.execute(select(User).where(User.sub == sub))
    user = result.scalar_one_or_none()

    if not user:
        user = User(sub=sub, email=email, name=name, role=UserRole.VIEWER)
        db.add(user)
    else:
        user.email = email
        user.name = name
        user.last_login = __import__("datetime").datetime.now(__import__("datetime").timezone.utc)

    await db.commit()
    await db.refresh(user)

    # Create session tokens
    access_token = create_access_token({"sub": str(user.id), "email": user.email, "role": user.role.value})
    refresh_token = create_refresh_token({"sub": str(user.id)})

    # Set HttpOnly cookie
    response = RedirectResponse(url=settings.frontend_url, status_code=302)
    response.set_cookie(
        key="session",
        value=access_token,
        httponly=True,
        secure=settings.cookie_secure,
        samesite=settings.cookie_samesite,
        max_age=30 * 60,  # 30 minutes
        path="/",
    )
    response.set_cookie(
        key="refresh",
        value=refresh_token,
        httponly=True,
        secure=settings.cookie_secure,
        samesite=settings.cookie_samesite,
        max_age=7 * 24 * 60 * 60,  # 7 days
        path="/auth/refresh",
    )

    return response


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(request: Request, db: AsyncSession = Depends(get_db)):
    """Refresh access token using refresh token."""
    refresh_token = request.cookies.get("refresh")
    if not refresh_token:
        raise HTTPException(status_code=401, detail="No refresh token")

    from app.core.security import decode_token
    payload = decode_token(refresh_token)
    if not payload or payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    user_id = payload.get("sub")
    result = await db.execute(select(User).where(User.id == int(user_id)))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    access_token = create_access_token({"sub": str(user.id), "email": user.email, "role": user.role.value})
    new_refresh_token = create_refresh_token({"sub": str(user.id)})

    response = TokenResponse(access_token=access_token, refresh_token=new_refresh_token)
    return response


@router.post("/logout")
async def logout(request: Request, response: Response, user: User = Depends(get_current_user)):
    """Logout user and clear session."""
    request.session.clear()
    response.delete_cookie("session", path="/")
    response.delete_cookie("refresh", path="/auth/refresh")

    # Redirect to Keycloak logout
    logout_url = await oidc_client.logout_url()
    return RedirectResponse(url=logout_url, status_code=302)


@router.get("/me", response_model=UserResponse)
async def get_me(user: User = Depends(get_current_user)):
    """Get current user profile."""
    return user


@router.get("/csrf")
async def get_csrf_token(request: Request):
    """Get CSRF token for form submissions."""
    csrf_token = request.session.get("csrf_token")
    if not csrf_token:
        from app.core.security import generate_csrf_token
        csrf_token = generate_csrf_token()
        request.session["csrf_token"] = csrf_token
    return {"csrf_token": csrf_token}