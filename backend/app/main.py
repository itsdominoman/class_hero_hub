from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from .database import engine, Base, get_db, settings
from . import models, schemas, auth
from .routes import children, ledger, redemptions, authentication, presets
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
