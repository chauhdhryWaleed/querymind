"""Auth surface: register, login, logout, refresh, password reset."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Cookie, Depends, HTTPException, Request, Response, status

from app.api.auth_deps import (
    current_session,
    current_user,
    get_auth_service,
    require_csrf,
)
from app.api.rate_limit import limiter
from app.config.settings import Settings, get_settings
from app.models.session import UserSession
from app.models.user import User
from app.schemas.auth import (
    AuthResponse,
    LoginRequest,
    PasswordChange,
    PasswordResetComplete,
    PasswordResetRequest,
    RegisterRequest,
    SessionOut,
    UserOut,
    WorkspaceOut,
)
from app.security import sessions as sess
from app.services.auth_service import AuthResult, AuthService, EmailTakenError

router = APIRouter(prefix="/auth", tags=["auth"])

_AUTH_RATE = get_settings().AUTH_RATE_LIMIT


def _client(request: Request) -> tuple[str | None, str | None]:
    ua = request.headers.get("user-agent")
    ip = request.client.host if request.client else None
    return ua, ip


def _set_cookies(response: Response, result: AuthResult, settings: Settings) -> None:
    sess.set_session_cookies(
        response,
        session_id=result.tokens.session_id,
        refresh_token=result.tokens.refresh_token,
        secure=settings.cookie_secure,
        samesite=settings.cookie_samesite,
        session_ttl=settings.SESSION_TTL,
        refresh_ttl=settings.REFRESH_TTL,
    )


def _auth_response(result: AuthResult) -> AuthResponse:
    return AuthResponse(
        user=UserOut(
            id=result.user.id,
            email=result.user.email,
            name=result.user.name,
            first_name=result.user.first_name,
            last_name=result.user.last_name,
            job_role=result.user.job_role,
            company=result.user.company,
            country=result.user.country,
            use_case=result.user.use_case,
            email_verified=result.user.email_verified_at is not None,
            created_at=result.user.created_at,
        ),
        workspace=WorkspaceOut(
            id=result.workspace.id,
            name=result.workspace.name,
            role="owner",
            default_model=result.workspace.default_model,
            max_rows=result.workspace.max_rows,
            statement_timeout_ms=result.workspace.statement_timeout_ms,
        ),
        csrf_token=result.tokens.csrf_token,
    )


@router.post("/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit(_AUTH_RATE)
async def register(
    payload: RegisterRequest,
    request: Request,
    response: Response,
    auth: Annotated[AuthService, Depends(get_auth_service)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> AuthResponse:
    ua, ip = _client(request)
    try:
        result = await auth.register(
            email=payload.email,
            password=payload.password,
            first_name=payload.first_name,
            last_name=payload.last_name,
            job_role=payload.job_role,
            company=payload.company,
            country=payload.country,
            use_case=payload.use_case,
            user_agent=ua,
            ip=ip,
        )
    except EmailTakenError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Email already registered"
        ) from None
    _set_cookies(response, result, settings)
    return _auth_response(result)


@router.post("/login", response_model=AuthResponse)
@limiter.limit(_AUTH_RATE)
async def login(
    payload: LoginRequest,
    request: Request,
    response: Response,
    auth: Annotated[AuthService, Depends(get_auth_service)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> AuthResponse:
    ua, ip = _client(request)
    result = await auth.login(payload.email, payload.password, user_agent=ua, ip=ip)
    if result is None:
        # Identical message whether the email is unknown or the password is wrong.
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password"
        )
    _set_cookies(response, result, settings)
    return _auth_response(result)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    response: Response,
    auth: Annotated[AuthService, Depends(get_auth_service)],
    settings: Annotated[Settings, Depends(get_settings)],
    session_cookie: Annotated[str | None, Cookie(alias=sess.SESSION_COOKIE)] = None,
) -> Response:
    if session_cookie:
        await auth.logout(session_cookie)
    sess.clear_session_cookies(response, secure=settings.cookie_secure, samesite=settings.cookie_samesite)
    response.status_code = status.HTTP_204_NO_CONTENT
    return response


@router.post("/refresh", response_model=dict)
async def refresh(
    response: Response,
    auth: Annotated[AuthService, Depends(get_auth_service)],
    settings: Annotated[Settings, Depends(get_settings)],
    session_cookie: Annotated[str | None, Cookie(alias=sess.SESSION_COOKIE)] = None,
    refresh_cookie: Annotated[str | None, Cookie(alias=sess.REFRESH_COOKIE)] = None,
) -> dict:
    if not session_cookie or not refresh_cookie:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="No session")
    rotated = await auth.refresh(session_cookie, refresh_cookie)
    if rotated is None:
        sess.clear_session_cookies(response, secure=settings.cookie_secure, samesite=settings.cookie_samesite)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Session expired")
    new_refresh, new_csrf = rotated
    # Re-issue cookies with the rotated refresh token; session id is unchanged.
    sess.set_session_cookies(
        response,
        session_id=session_cookie,
        refresh_token=new_refresh,
        secure=settings.cookie_secure,
        samesite=settings.cookie_samesite,
        session_ttl=settings.SESSION_TTL,
        refresh_ttl=settings.REFRESH_TTL,
    )
    return {"csrf_token": new_csrf}


@router.post("/password-reset/request", status_code=status.HTTP_202_ACCEPTED)
@limiter.limit(_AUTH_RATE)
async def password_reset_request(
    payload: PasswordResetRequest,
    request: Request,
    auth: Annotated[AuthService, Depends(get_auth_service)],
) -> dict:
    # Always 202 regardless of whether the email exists (no enumeration).
    await auth.request_password_reset(payload.email)
    return {"status": "accepted"}


@router.post("/password-reset/complete")
async def password_reset_complete(
    payload: PasswordResetComplete,
    auth: Annotated[AuthService, Depends(get_auth_service)],
) -> dict:
    ok = await auth.complete_password_reset(payload.token, payload.new_password)
    if not ok:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired token"
        )
    return {"status": "ok"}


@router.post("/password-change", dependencies=[Depends(require_csrf)])
async def password_change(
    payload: PasswordChange,
    auth: Annotated[AuthService, Depends(get_auth_service)],
    user: Annotated[User, Depends(current_user)],
    session: Annotated[UserSession, Depends(current_session)],
) -> dict:
    ok = await auth.change_password(
        user,
        payload.current_password,
        payload.new_password,
        keep_session_id=str(session.id),
    )
    if not ok:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Current password is incorrect"
        )
    return {"status": "ok"}


@router.get("/sessions", response_model=list[SessionOut])
async def list_sessions(
    auth: Annotated[AuthService, Depends(get_auth_service)],
    user: Annotated[User, Depends(current_user)],
    session: Annotated[UserSession, Depends(current_session)],
) -> list[SessionOut]:
    rows = await auth.list_sessions(user.id)
    return [
        SessionOut(
            id=s.id,
            user_agent=s.user_agent,
            ip=str(s.ip) if s.ip else None,
            created_at=s.created_at,
            expires_at=s.expires_at,
            current=s.id == session.id,
        )
        for s in rows
    ]


@router.delete(
    "/sessions/{session_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_csrf)],
)
async def revoke_session(
    session_id: str,
    response: Response,
    auth: Annotated[AuthService, Depends(get_auth_service)],
    settings: Annotated[Settings, Depends(get_settings)],
    user: Annotated[User, Depends(current_user)],
    session: Annotated[UserSession, Depends(current_session)],
) -> Response:
    ok = await auth.revoke_session(user.id, session_id)
    if not ok:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    # Revoking the active session ⇒ also clear this browser's cookies.
    if session_id == str(session.id):
        sess.clear_session_cookies(response, secure=settings.cookie_secure, samesite=settings.cookie_samesite)
    response.status_code = status.HTTP_204_NO_CONTENT
    return response


@router.post("/resend-verification", status_code=status.HTTP_202_ACCEPTED)
@limiter.limit(_AUTH_RATE)
async def resend_verification(
    request: Request,
    auth: Annotated[AuthService, Depends(get_auth_service)],
    user: Annotated[User, Depends(current_user)],
    _csrf: Annotated[None, Depends(require_csrf)],
) -> dict:
    await auth.resend_verification(user)
    return {"status": "accepted"}


@router.delete(
    "/account", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(require_csrf)]
)
async def delete_account(
    response: Response,
    auth: Annotated[AuthService, Depends(get_auth_service)],
    settings: Annotated[Settings, Depends(get_settings)],
    user: Annotated[User, Depends(current_user)],
) -> Response:
    await auth.delete_account(user)
    sess.clear_session_cookies(response, secure=settings.cookie_secure, samesite=settings.cookie_samesite)
    response.status_code = status.HTTP_204_NO_CONTENT
    return response
