from fastapi import FastAPI, Depends, HTTPException, status, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from .database import engine, Base, get_db, settings
from . import models, schemas, auth
from .routes import children, ledger, redemptions, authentication, presets, rewards, family, child_devices, child_access, child_link, registration, admin, calendar, child_calendar
from starlette.middleware.sessions import SessionMiddleware
from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware

# Create database tables
Base.metadata.create_all(bind=engine)

app = FastAPI(title=settings.APP_NAME if hasattr(settings, 'APP_NAME') else "Family Hero Hub")

# Ensure the app respects X-Forwarded-Proto for redirects
app.add_middleware(ProxyHeadersMiddleware, trusted_hosts="*")

# CORS
origins = [o.strip() for o in settings.CORS_ORIGINS.split(",")]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Sessions for Google OAuth
app.add_middleware(SessionMiddleware, secret_key=settings.SESSION_SECRET)


@app.middleware("http")
async def csrf_protection_middleware(request: Request, call_next):
    try:
        auth.validate_csrf_request(request)
    except HTTPException as exc:
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.detail},
            headers=getattr(exc, "headers", None),
        )

    return await call_next(request)

@app.get("/api/health")
def health_check():
    return {"status": "ok"}

@app.get("/api/me", response_model=schemas.ParentUser)
async def read_current_parent(current_parent: models.ParentUser = Depends(auth.get_current_parent)):
    return current_parent

# Include routers
app.include_router(authentication.router, prefix="/api/auth", tags=["auth"])
app.include_router(children.router, prefix="/api/children", tags=["children"])
app.include_router(ledger.router, prefix="/api/children", tags=["ledger"])
app.include_router(redemptions.router, prefix="/api", tags=["redemptions"])
app.include_router(presets.router, prefix="/api/presets", tags=["presets"])
app.include_router(rewards.router, prefix="/api/rewards", tags=["rewards"])
app.include_router(family.router, prefix="/api/family", tags=["family"])
app.include_router(child_devices.router, prefix="/api", tags=["child-devices"])
app.include_router(child_link.router, prefix="/api/child-link", tags=["child-link"])
app.include_router(child_access.router, prefix="/api/child", tags=["child"])
app.include_router(registration.router, prefix="/api/registration-requests", tags=["registration"])
app.include_router(admin.router, prefix="/api/admin", tags=["admin"])
app.include_router(calendar.router, prefix="/api/calendar", tags=["calendar"])
app.include_router(child_calendar.router, prefix="/api/child/calendar", tags=["child-calendar"])
