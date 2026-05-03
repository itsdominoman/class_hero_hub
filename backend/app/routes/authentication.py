from fastapi import APIRouter, Depends, HTTPException, status, Request, Response
from sqlalchemy.orm import Session
from sqlalchemy import func
from ..database import get_db, settings
from .. import models, schemas, auth
from authlib.integrations.starlette_client import OAuth
import time

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

    # Verify allowlist
    allowed_emails = [auth.normalize_email(e) for e in settings.PARENT_EMAILS.split(",")]
    if email not in allowed_emails:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Email not in allowlist")

    parent = db.query(models.ParentUser).filter(func.lower(models.ParentUser.email) == email).first()
    invite = db.query(models.FamilyInvite).filter(
        func.lower(models.FamilyInvite.email) == email,
        models.FamilyInvite.status == "pending"
    ).first()

    if not parent:
        if invite:
            family_id = invite.family_id
            invite.status = "accepted"
            invite.accepted_at = models.func.now()
        else:
            # Create new family for new parent
            new_family = models.Family()
            db.add(new_family)
            db.commit()
            db.refresh(new_family)
            family_id = new_family.id

        parent = models.ParentUser(
            email=email, 
            name=name, 
            google_sub=google_sub,
            family_id=family_id
        )
        db.add(parent)
        db.commit()
        db.refresh(parent)
    else:
        if parent.family_id is None:
            if invite:
                parent.family_id = invite.family_id
                invite.status = "accepted"
                invite.accepted_at = models.func.now()
            else:
                new_family = models.Family()
                db.add(new_family)
                db.flush()
                parent.family_id = new_family.id
        parent.email = email
        parent.google_sub = google_sub
        parent.name = name
        parent.last_login_at = models.func.now()
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
    return response

@router.post("/logout")
async def logout(response: Response):
    response.delete_cookie("access_token", path="/")
    return {"message": "Logged out"}
