from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import hashlib
import secrets
from typing import Callable, Generic, TypeVar

from fastapi import HTTPException, Request, Response, status

from .database import settings
from .security import BoundedInMemoryRateLimiter, get_client_ip_from_scope

InviteT = TypeVar("InviteT")
SessionT = TypeVar("SessionT")

SESSION_COOKIE = "invite_session"
SESSION_TTL = timedelta(days=30)
INVITE_TTL = timedelta(days=1)
EXCHANGE_RATE_LIMIT_WINDOW_SECONDS = 60
EXCHANGE_RATE_LIMIT_MAX_ATTEMPTS = 20

exchange_rate_limiter = BoundedInMemoryRateLimiter(
    EXCHANGE_RATE_LIMIT_WINDOW_SECONDS,
    EXCHANGE_RATE_LIMIT_MAX_ATTEMPTS,
)


@dataclass
class TokenExchangeResult(Generic[InviteT, SessionT]):
    invite: InviteT
    session: SessionT
    raw_session_token: str


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def as_utc_aware(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def generate_token() -> str:
    return secrets.token_urlsafe(32)


def cookie_max_age(expires_at: datetime) -> int:
    aware_expires_at = as_utc_aware(expires_at)
    if aware_expires_at is None:
        return 0
    return max(0, int((aware_expires_at - now_utc()).total_seconds()))


def set_session_cookie(response: Response, raw_token: str, expires_at: datetime, cookie_name: str = SESSION_COOKIE) -> None:
    response.set_cookie(
        key=cookie_name,
        value=raw_token,
        httponly=True,
        max_age=cookie_max_age(expires_at),
        samesite="lax",
        secure=settings.COOKIE_SECURE,
        path="/",
    )


def clear_session_cookie(response: Response, cookie_name: str = SESSION_COOKIE) -> None:
    response.delete_cookie(cookie_name, path="/")


def register_exchange_attempt(request: Request) -> None:
    client_ip = get_client_ip_from_scope(request.scope) or "unknown"
    if not exchange_rate_limiter.allow(client_ip, now=now_utc()):
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Too many invite exchange attempts")


def issue_invite(create_invite: Callable[[str, datetime], InviteT]) -> tuple[InviteT, str]:
    raw_token = generate_token()
    invite = create_invite(hash_token(raw_token), now_utc() + INVITE_TTL)
    return invite, raw_token


def revoke_token(record, *, revoked_at_attr: str = "revoked_at") -> None:
    setattr(record, revoked_at_attr, now_utc())


def exchange_invite(
    request: Request,
    raw_token: str,
    load_invite: Callable[[str], InviteT | None],
    create_session: Callable[[InviteT, str, datetime], SessionT],
    *,
    used_at_attr: str = "used_at",
    revoked_at_attr: str = "revoked_at",
    expires_at_attr: str = "expires_at",
) -> TokenExchangeResult[InviteT, SessionT]:
    register_exchange_attempt(request)
    token_hash = hash_token(raw_token)
    current = now_utc()
    invite = load_invite(token_hash)
    if not invite:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired invite")
    if getattr(invite, revoked_at_attr, None) is not None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired invite")
    if getattr(invite, used_at_attr, None) is not None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invite already used")

    invite_expires_at = as_utc_aware(getattr(invite, expires_at_attr, None))
    if invite_expires_at is None or invite_expires_at <= current:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invite expired")

    setattr(invite, used_at_attr, current)
    session_raw_token = generate_token()
    session = create_session(invite, hash_token(session_raw_token), current + SESSION_TTL)
    return TokenExchangeResult(invite=invite, session=session, raw_session_token=session_raw_token)
