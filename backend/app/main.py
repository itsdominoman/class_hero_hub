import logging

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from starlette.middleware.sessions import SessionMiddleware

from . import auth, database, schemas
from .database import Base, close_request_db, engine, ensure_runtime_schema, get_db, settings, validate_runtime_configuration
from .models_school import Membership, PlatformAdmin, School, User
from .message_media_service import MESSAGE_MEDIA_ROOT
from .routes import announcements, authentication, behaviour, calendar, dev, guardian, homework, integrations_fhh, integrations_fhh_messaging, join, messaging, messaging_policy, platform, school, school_reports, teach, updates
from .security import TrustedProxyHeadersMiddleware, parse_csv_values

if settings.DATABASE_URL.startswith("sqlite"):
    Base.metadata.create_all(bind=engine)
    ensure_runtime_schema()

# Lives under the ./data bind mount (docker-compose.yml), so uploads survive
# container rebuilds/restarts. Create it defensively in case the mount is
# ever fresh (e.g. a new environment).
announcements.UPLOAD_ROOT.mkdir(parents=True, exist_ok=True)
homework.UPLOAD_ROOT.mkdir(parents=True, exist_ok=True)
updates.UPLOAD_ROOT.mkdir(parents=True, exist_ok=True)
MESSAGE_MEDIA_ROOT.mkdir(parents=True, exist_ok=True)


class ProtectedMediaAccessLogFilter(logging.Filter):
    """Redact protected integration media parameters from Uvicorn access logs."""

    def filter(self, record: logging.LogRecord) -> bool:
        if not isinstance(record.args, tuple) or len(record.args) < 5:
            return True
        path = str(record.args[2])
        is_protected_media = (
            path.startswith("/api/integrations/fhh/links/")
            and ("/attachments/" in path or "/photos/" in path)
        )
        is_fhh_messaging = (
            path.startswith("/api/integrations/fhh/links/")
            and "/messaging" in path
        )
        is_chh_messaging_media = (
            (path.startswith("/api/messaging/") or path.startswith("/api/guardian/messaging/"))
            and "/media/" in path
        )
        if is_protected_media or is_fhh_messaging or is_chh_messaging_media:
            args = list(record.args)
            args[2] = (
                "/api/integrations/fhh/links/<redacted>/messaging/<redacted>"
                if is_fhh_messaging
                else "/api/messaging/<redacted>/<protected-media>"
                if is_chh_messaging_media
                else "/api/integrations/fhh/links/<redacted>/<protected-media>"
            )
            record.args = tuple(args)
        return True


protected_media_access_log_filter = ProtectedMediaAccessLogFilter()


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
                "membership_id": membership.id,
                "role": membership.role,
            }
            for membership, school in memberships
        ],
    }


def create_app() -> FastAPI:
    validate_runtime_configuration(settings)

    app = FastAPI(title=settings.APP_NAME if hasattr(settings, "APP_NAME") else "Class Hero Hub")
    app.state.runtime_environment = settings.runtime_environment

    @app.on_event("startup")
    async def install_protected_media_access_log_filter() -> None:
        access_logger = logging.getLogger("uvicorn.access")
        if protected_media_access_log_filter not in access_logger.filters:
            access_logger.addFilter(protected_media_access_log_filter)

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
    app.include_router(announcements.staff_router, prefix="/api/school", tags=["announcements"])
    app.include_router(calendar.staff_router, prefix="/api/school", tags=["calendar"])
    app.include_router(school.router, prefix="/api/school", tags=["school"])
    app.include_router(messaging_policy.router, prefix="/api/school", tags=["messaging-policy"])
    app.include_router(messaging.staff_router, prefix="/api/messaging", tags=["messaging"])
    app.include_router(behaviour.school_router, prefix="/api/school", tags=["behaviour"])
    app.include_router(school_reports.router, prefix="/api/school", tags=["reports"])
    app.include_router(teach.router, prefix="/api/teach", tags=["teach"])
    app.include_router(behaviour.teacher_router, prefix="/api/teach", tags=["behaviour"])
    app.include_router(announcements.teacher_router, prefix="/api/teach", tags=["announcements"])
    app.include_router(homework.teacher_router, prefix="/api/teach", tags=["homework"])
    app.include_router(updates.teacher_router, prefix="/api/teach", tags=["updates"])
    app.include_router(calendar.teacher_router, prefix="/api/teach", tags=["calendar"])
    app.include_router(announcements.guardian_router, prefix="/api/guardian", tags=["announcements"])
    app.include_router(homework.guardian_router, prefix="/api/guardian", tags=["homework"])
    app.include_router(updates.guardian_router, prefix="/api/guardian", tags=["updates"])
    app.include_router(calendar.guardian_router, prefix="/api/guardian", tags=["calendar"])
    app.include_router(guardian.router, prefix="/api/guardian", tags=["guardian"])
    app.include_router(
        messaging.guardian_router,
        prefix="/api/guardian/messaging",
        tags=["guardian-messaging"],
    )
    app.include_router(behaviour.guardian_router, prefix="/api/guardian", tags=["behaviour"])
    app.include_router(integrations_fhh.router, prefix="/api/integrations/fhh", tags=["fhh-integration"])
    app.include_router(
        integrations_fhh_messaging.router,
        prefix="/api/integrations/fhh",
        tags=["fhh-messaging-integration"],
    )

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
