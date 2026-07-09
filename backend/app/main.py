from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from starlette.middleware.sessions import SessionMiddleware

from . import auth, database, schemas
from .database import Base, close_request_db, engine, ensure_runtime_schema, get_db, settings, validate_runtime_configuration
from .models_school import Membership, PlatformAdmin, School, User
from .routes import authentication, dev, guardian, join, platform, school, teach
from .security import TrustedProxyHeadersMiddleware, parse_csv_values

if settings.DATABASE_URL.startswith("sqlite"):
    Base.metadata.create_all(bind=engine)
    ensure_runtime_schema()


def _me_payload(current_user: User, db: Session) -> dict:
    is_platform_admin = (
        db.query(PlatformAdmin)
        .filter(
            PlatformAdmin.user_id == current_user.id,
            PlatformAdmin.revoked_at.is_(None),
        )
        .first()
        is not None
    )
    memberships = (
        db.query(Membership, School)
        .join(School, Membership.school_id == School.id)
        .filter(
            Membership.user_id == current_user.id,
            Membership.status == "active",
            Membership.revoked_at.is_(None),
        )
        .all()
    )
    return {
        "user": {
            "id": current_user.id,
            "email": current_user.email,
            "name": current_user.name,
            "locale": current_user.locale,
        },
        "is_platform_admin": is_platform_admin,
        "memberships": [
            {
                "school_id": school.id,
                "school_name": school.name,
                "role": membership.role,
            }
            for membership, school in memberships
        ],
    }


def create_app() -> FastAPI:
    validate_runtime_configuration(settings)

    app = FastAPI(title=settings.APP_NAME if hasattr(settings, "APP_NAME") else "Class Hero Hub")
    app.state.runtime_environment = settings.runtime_environment

    app.add_middleware(TrustedProxyHeadersMiddleware, trusted_proxy_ips=settings.TRUSTED_PROXY_IPS)

    origins = parse_csv_values(settings.CORS_ORIGINS)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.add_middleware(SessionMiddleware, secret_key=settings.SESSION_SECRET)

    @app.middleware("http")
    async def db_session_cleanup_middleware(request: Request, call_next):
        try:
            response = await call_next(request)
            return response
        except Exception:
            close_request_db(request, rollback=True)
            raise
        finally:
            close_request_db(request, rollback=True)

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

    app.include_router(authentication.router, prefix="/api/auth", tags=["auth"])
    app.include_router(platform.router, prefix="/api/platform", tags=["platform"])
    app.include_router(platform.invite_router, prefix="/api/invites", tags=["invites"])
    app.include_router(join.router, prefix="/api/join", tags=["join"])
    app.include_router(school.router, prefix="/api/school", tags=["school"])
    app.include_router(teach.router, prefix="/api/teach", tags=["teach"])
    app.include_router(guardian.router, prefix="/api/guardian", tags=["guardian"])

    if settings.runtime_environment != "production":
        app.include_router(dev.router, prefix="/api/dev", tags=["dev"])

    return app


app = create_app()


@app.get("/api/me", response_model=schemas.MeResponse)
async def read_current_user(
    current_user: User = Depends(auth.get_current_user),
    db: Session = Depends(get_db),
):
    return _me_payload(current_user, db)


@app.get("/api/me/v2", response_model=schemas.MeResponse)
async def read_current_user_v2(
    current_user: User = Depends(auth.get_current_user),
    db: Session = Depends(get_db),
):
    return _me_payload(current_user, db)
