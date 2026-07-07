from datetime import datetime, timezone
from urllib.parse import urlparse

from authlib.integrations.starlette_client import OAuth
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from .. import auth, schemas
from ..database import get_db, settings
from ..models_school import User

router = APIRouter()

oauth = OAuth()
oauth.register(
    name="google",
    client_id=settings.GOOGLE_CLIENT_ID,
    client_secret=settings.GOOGLE_CLIENT_SECRET,
    server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
    client_kwargs={"scope": "openid email profile"},
)


@router.get("/me", response_model=schemas.MeResponse)
async def get_me(
    current_user: User = Depends(auth.get_current_user),
    db: Session = Depends(get_db),
):
    from ..main import _me_payload

    return _me_payload(current_user, db)


def _safe_return_path(value: str | None) -> str | None:
    candidate = (value or "").strip()
    if not candidate.startswith("/") or candidate.startswith("//"):
        return None
    parsed = urlparse(candidate)
    if parsed.scheme or parsed.netloc:
        return None
    return candidate


@router.get("/google/login")
async def google_login(request: Request):
    return_to = _safe_return_path(request.query_params.get("return_to"))
    if return_to:
        request.session["post_auth_redirect"] = return_to
    return await oauth.google.authorize_redirect(request, settings.GOOGLE_REDIRECT_URI)


@router.get("/google/callback")
async def google_callback(request: Request, db: Session = Depends(get_db)):
    try:
        token = await oauth.google.authorize_access_token(request)
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=f"Google auth failed: {str(exc)}")

    user_info = token.get("userinfo")
    if not user_info:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="No user info from Google")

    email = auth.normalize_email(user_info.get("email"))
    if not email:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="No email from Google")

    now = datetime.now(timezone.utc)
    user = db.query(User).filter(func.lower(User.email) == email).first()
    if not user:
        user = User(
            email=email,
            name=user_info.get("name"),
            google_sub=user_info.get("sub"),
            last_login_at=now,
        )
        db.add(user)
    else:
        user.email = email
        user.google_sub = user_info.get("sub")
        user.name = user_info.get("name")
        user.last_login_at = now
    db.commit()
    db.refresh(user)

    access_token = auth.create_access_token(data={"sub": user.email})
    session_max_age = auth.parent_session_cookie_max_age_seconds()

    response = Response(status_code=status.HTTP_302_FOUND)
    return_to = _safe_return_path(request.session.pop("post_auth_redirect", None))
    response.headers["Location"] = f"{settings.PUBLIC_APP_URL.rstrip('/')}{return_to or ''}"
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        max_age=session_max_age,
        expires=session_max_age,
        samesite="lax",
        secure=settings.COOKIE_SECURE,
        path="/",
    )
    auth.set_csrf_cookie(response, auth.create_csrf_token())
    return response


@router.post("/logout")
async def logout(response: Response):
    response.delete_cookie("access_token", path="/")
    auth.clear_csrf_cookie(response)
    return {"message": "Logged out"}
