from __future__ import annotations

import hashlib
import hmac
import json
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from fastapi import HTTPException, Request, status
from jose import JWTError, jwt
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .database import settings
from .models_school import (
    FhhLink,
    FhhMessagingAssertionUse,
    FhhMessagingIdentity,
    FhhMessagingIdentityLink,
)


ALGORITHM = "HS256"
MAX_ASSERTION_LIFETIME_SECONDS = 330
ALLOWED_CLOCK_SKEW_SECONDS = 30


def canonical_body_hash(value: Any) -> str:
    if value is None:
        raw = b""
    else:
        raw = json.dumps(
            value,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
            default=str,
        ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _deny(detail: str = "Invalid messaging actor assertion") -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
    )


def verify_and_consume_actor_assertion(
    db: Session,
    *,
    request: Request,
    link: FhhLink,
    assertion: str | None,
    body: Any = None,
) -> tuple[FhhMessagingIdentity, FhhMessagingIdentityLink]:
    if not settings.MESSAGING_ENABLED:
        raise HTTPException(status_code=404, detail="Messaging is unavailable")
    if not assertion or not settings.FHH_MESSAGING_ASSERTION_SECRET:
        raise _deny()
    try:
        claims = jwt.decode(
            assertion,
            settings.FHH_MESSAGING_ASSERTION_SECRET,
            algorithms=[ALGORITHM],
            audience=settings.FHH_MESSAGING_ASSERTION_AUDIENCE,
            issuer=settings.FHH_MESSAGING_ASSERTION_ISSUER,
            options={
                "require_exp": True,
                "require_iat": True,
                "require_jti": True,
                "require_sub": True,
            },
        )
    except JWTError as exc:
        raise _deny() from exc

    now = datetime.now(timezone.utc)
    try:
        issued_at = int(claims["iat"])
        expires_at = int(claims["exp"])
        jti = UUID(str(claims["jti"]))
        external_subject_ref = UUID(str(claims["sub"]))
        asserted_link_id = int(claims["link_id"])
    except (KeyError, TypeError, ValueError) as exc:
        raise _deny() from exc
    now_seconds = int(now.timestamp())
    if (
        issued_at > now_seconds + ALLOWED_CLOCK_SKEW_SECONDS
        or expires_at <= now_seconds
        or expires_at - issued_at > MAX_ASSERTION_LIFETIME_SECONDS
    ):
        raise _deny()
    if asserted_link_id != link.id:
        raise _deny()
    if claims.get("method") != request.method.upper():
        raise _deny()
    if claims.get("path") != request.url.path:
        raise _deny()
    if not hmac.compare_digest(
        str(claims.get("body_sha256", "")),
        canonical_body_hash(body),
    ):
        raise _deny()
    display_name = claims.get("display_name")
    locale = claims.get("locale")
    if (
        not isinstance(display_name, str)
        or not 1 <= len(display_name) <= 200
        or locale not in {"en", "ar"}
    ):
        raise _deny()

    row = (
        db.query(FhhMessagingIdentity, FhhMessagingIdentityLink)
        .join(
            FhhMessagingIdentityLink,
            FhhMessagingIdentityLink.identity_id == FhhMessagingIdentity.id,
        )
        .filter(
            FhhMessagingIdentity.school_id == link.school_id,
            FhhMessagingIdentity.provider == "fhh",
            FhhMessagingIdentity.external_subject_ref == external_subject_ref,
            FhhMessagingIdentity.status == "active",
            FhhMessagingIdentityLink.school_id == link.school_id,
            FhhMessagingIdentityLink.fhh_link_id == link.id,
            FhhMessagingIdentityLink.status == "active",
            FhhMessagingIdentityLink.revoked_at.is_(None),
        )
        .first()
    )
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Messaging identity synchronization is required",
        )
    identity, identity_link = row
    if (
        not hmac.compare_digest(
            identity.display_name.encode("utf-8"),
            display_name.encode("utf-8"),
        )
        or identity.preferred_locale != locale
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Messaging identity synchronization is required",
        )

    db.add(
        FhhMessagingAssertionUse(
            jti=jti,
            school_id=link.school_id,
            fhh_link_id=link.id,
            identity_id=identity.id,
            request_method=request.method.upper(),
            request_path_hash=hashlib.sha256(
                request.url.path.encode("utf-8")
            ).hexdigest(),
            body_hash=canonical_body_hash(body),
            expires_at=datetime.fromtimestamp(expires_at, tz=timezone.utc),
        )
    )
    try:
        db.flush()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Messaging actor assertion has already been used",
        ) from exc
    return identity, identity_link
