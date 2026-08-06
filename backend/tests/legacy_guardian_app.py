"""Test-only app for the retired direct CHH guardian handlers.

Production deliberately exposes family data only through the protected FHH
integration. The old handler modules still contain useful service-level
regression coverage, so legacy tests mount them on an isolated app without
changing or weakening the production route graph.
"""

from app.main import create_app, read_current_user
from app.routes import (
    announcements,
    behaviour,
    calendar,
    guardian,
    homework,
    join,
    messaging,
    updates,
)


def create_legacy_guardian_test_app():
    app = create_app()
    # ``/api/me`` is registered on the production module-level app after
    # ``create_app`` returns, so mirror that registration on this isolated app.
    app.add_api_route("/api/me", read_current_user, methods=["GET"])
    app.include_router(join.router, prefix="/api/join", tags=["legacy-test-join"])
    app.include_router(announcements.guardian_router, prefix="/api/guardian", tags=["legacy-test-announcements"])
    app.include_router(homework.guardian_router, prefix="/api/guardian", tags=["legacy-test-homework"])
    app.include_router(updates.guardian_router, prefix="/api/guardian", tags=["legacy-test-updates"])
    app.include_router(calendar.guardian_router, prefix="/api/guardian", tags=["legacy-test-calendar"])
    app.include_router(guardian.router, prefix="/api/guardian", tags=["legacy-test-dashboard"])
    app.include_router(
        messaging.guardian_router,
        prefix="/api/guardian/messaging",
        tags=["legacy-test-messaging"],
    )
    app.include_router(behaviour.guardian_router, prefix="/api/guardian", tags=["legacy-test-behaviour"])
    return app
