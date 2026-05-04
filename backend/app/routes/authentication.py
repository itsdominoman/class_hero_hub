from fastapi import APIRouter, Depends, HTTPException, status, Request, Response
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy import func
from ..database import get_db, settings
from .. import models, schemas, auth
from authlib.integrations.starlette_client import OAuth
import time
import hashlib
from datetime import datetime, timezone

router = APIRouter()

oauth = OAuth()
oauth.register(
    name='google',
    client_id=settings.GOOGLE_CLIENT_ID,
    client_secret=settings.GOOGLE_CLIENT_SECRET,
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    client_kwargs={
        'scope': 'openid email profile'
    }
)

@router.get("/me", response_model=schemas.ParentUser)
async def get_me(current_parent: models.ParentUser = Depends(auth.get_current_parent)):
    return current_parent

@router.get("/google/login")
async def google_login(request: Request):
    redirect_uri = settings.GOOGLE_REDIRECT_URI
    return await oauth.google.authorize_redirect(request, redirect_uri)

@router.get("/google/callback")
async def google_callback(request: Request, db: Session = Depends(get_db)):
    try:
        token = await oauth.google.authorize_access_token(request)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=f"Google auth failed: {str(e)}")
    
    user_info = token.get('userinfo')
    if not user_info:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="No user info from Google")
    
    email = auth.normalize_email(user_info.get('email'))
    name = user_info.get('name')
    google_sub = user_info.get('sub')

    # 1. Check for invite token in cookie.
    # Invite token is optional for normal bootstrap/returning login,
    # but if present it must be valid, pending, unexpired, unrevoked,
    # and must match the Google email exactly.
    invite_token = request.cookies.get(auth.INVITE_COOKIE_NAME)
    invite = None
    if invite_token:
        token_hash = hashlib.sha256(invite_token.encode()).hexdigest()
        invite = db.query(models.FamilyInvite).filter(
            models.FamilyInvite.token_hash == token_hash,
            models.FamilyInvite.status == "pending",
            models.FamilyInvite.revoked_at.is_(None),
            models.FamilyInvite.accepted_at.is_(None),
        ).first()

        if not invite:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Invite not found or already used",
            )

        if invite.expires_at and invite.expires_at.replace(tzinfo=timezone.utc) < datetime.now(timezone.utc):
            invite.status = "expired"
            db.commit()
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Invite expired",
            )

        if auth.normalize_email(invite.email) != email:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Invite email does not match Google account",
            )

    # 2. Check allowlist or database approvals if not invited
    allowed_emails = [auth.normalize_email(e) for e in settings.PARENT_EMAILS.split(",")]
    is_in_bootstrap = email in allowed_emails
    
    # Check for DB-based approval
    db_approval = db.query(models.ApprovedParentEmail).filter(
        models.ApprovedParentEmail.normalized_email == email,
        models.ApprovedParentEmail.status == "active"
    ).first()
    is_db_approved = db_approval is not None

    parent = db.query(models.ParentUser).filter(func.lower(models.ParentUser.email) == email).first()

    if not parent:
        # New user: must be invited OR in bootstrap OR DB approved
        if not invite and not is_in_bootstrap and not is_db_approved:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Email not approved and no valid invite found")

        family_id = None
        if invite:
            family_id = invite.family_id
            invite.status = "accepted"
            invite.accepted_at = datetime.now(timezone.utc)
        else:
            # Bootstrap or DB Approved: Create new family
            new_family = models.Family()
            db.add(new_family)
            db.commit()
            db.refresh(new_family)
            family_id = new_family.id

        parent = models.ParentUser(
            email=email, 
            name=name, 
            google_sub=google_sub,
            family_id=family_id,
            last_login_at=datetime.now(timezone.utc)
        )
        db.add(parent)
        db.commit()
        db.refresh(parent)
        
        if invite:
            invite.accepted_by_parent_id = parent.id
            db.commit()
    else:
        # Existing user
        if invite:
            if parent.family_id is not None and parent.family_id != invite.family_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="This Google account already belongs to another family",
                )

            parent.family_id = invite.family_id
            invite.status = "accepted"
            invite.accepted_at = datetime.now(timezone.utc)
            invite.accepted_by_parent_id = parent.id

        elif parent.family_id is None:
            if is_in_bootstrap or is_db_approved:
                new_family = models.Family()
                db.add(new_family)
                db.flush()
                parent.family_id = new_family.id
            else:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Parent has no family and no valid approval found")
        
        parent.email = email
        parent.google_sub = google_sub
        parent.name = name
        parent.last_login_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(parent)

    # Create JWT
    access_token = auth.create_access_token(data={"sub": parent.email})
    
    # Redirect to frontend dashboard with token in cookie
    response = Response(status_code=status.HTTP_302_FOUND)
    response.headers["Location"] = f"{settings.PUBLIC_APP_URL.rstrip('/')}/parent"
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        max_age=1800,
        expires=1800,
        samesite="lax",
        secure=settings.COOKIE_SECURE,
        path="/"
    )
    auth.set_csrf_cookie(response, auth.create_csrf_token())
    # Clear invite token cookie
    response.delete_cookie(auth.INVITE_COOKIE_NAME, path="/")
    return response

@router.get("/invite/verify/{token}")
async def verify_invite_token(token: str, db: Session = Depends(get_db)):
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    invite = db.query(models.FamilyInvite).filter(
        models.FamilyInvite.token_hash == token_hash,
        models.FamilyInvite.status == "pending"
    ).first()

    if not invite:
        raise HTTPException(status_code=404, detail="Invite not found or already used")
    
    if invite.expires_at and invite.expires_at.replace(tzinfo=timezone.utc) < datetime.now(timezone.utc):
        invite.status = "expired"
        db.commit()
        raise HTTPException(status_code=400, detail="Invite expired")
    
    # Set short-lived invite cookie used by the Google OAuth callback.
    # IMPORTANT: return the response object that has the cookie attached.
    response = JSONResponse(content={"email": invite.email})
    response.set_cookie(
        key=auth.INVITE_COOKIE_NAME,
        value=token,
        httponly=True,
        max_age=3600,  # 1 hour
        expires=3600,
        samesite="lax",
        secure=settings.COOKIE_SECURE,
        path="/"
    )
    return response

@router.post("/logout")
async def logout(response: Response):
    response.delete_cookie("access_token", path="/")
    auth.clear_csrf_cookie(response)
    return {"message": "Logged out"}
