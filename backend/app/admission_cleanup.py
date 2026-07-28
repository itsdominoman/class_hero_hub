from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import func
from sqlalchemy.orm import Session

from . import admission
from .models_school import (
    DevicePushRegistration,
    MagicLoginToken,
    User,
    UserRefreshSession,
)

UNAUTHORISED_REASON = (
    "no active platform administrator, admin/teacher school membership, "
    "or guardian link"
)
SEEDED_EXCEPTIONS = {
    "s9.guardian.qa@myeduzone.org": (
        "documented S9 guardian API-smoke identity retained inactive because "
        "immutable audit evidence references it"
    ),
}
REQUIRED_REMOVALS = {
    "google-admin@familyherohub.com",
    "test@familyherohub.com",
    "parent@familyherohub.com",
}


class CleanupBlocked(RuntimeError):
    pass


@dataclass(frozen=True)
class InventoryRow:
    email_address: str
    user_id: int
    creation_date: str
    last_successful_login: str
    authentication_method: str
    reason_classified_as_unauthorised: str
    disposition: str


def _iso(value) -> str:
    return value.isoformat() if value is not None else ""


def _authentication_method(db: Session, user: User) -> str:
    methods: list[str] = []
    if user.google_sub:
        methods.append("google")
    if (
        db.query(MagicLoginToken.id)
        .filter(
            func.lower(MagicLoginToken.email) == user.email.strip().lower(),
            MagicLoginToken.used_at.is_not(None),
        )
        .first()
        is not None
    ):
        methods.append("magic_link")
    if methods:
        return "+".join(methods)
    if user.email.strip().lower() in SEEDED_EXCEPTIONS:
        return "documented_api_smoke_seed"
    return "not_recorded"


def build_inventory(db: Session) -> list[InventoryRow]:
    rows: list[InventoryRow] = []
    for user in admission.unauthorised_user_query(db).order_by(User.id).all():
        email = user.email.strip().lower()
        rows.append(
            InventoryRow(
                email_address=email,
                user_id=user.id,
                creation_date=_iso(user.created_at),
                last_successful_login=_iso(user.last_login_at),
                authentication_method=_authentication_method(db, user),
                reason_classified_as_unauthorised=UNAUTHORISED_REASON,
                disposition=(
                    "preserved_seeded_identity"
                    if email in SEEDED_EXCEPTIONS
                    else "planned_removal"
                ),
            )
        )
    return rows


def apply_cleanup(db: Session, planned_user_ids: list[int]) -> list[int]:
    users = (
        db.query(User)
        .filter(User.id.in_(planned_user_ids))
        .order_by(User.id)
        .with_for_update()
        .all()
    )
    if len(users) != len(set(planned_user_ids)):
        raise CleanupBlocked("The dry-run user set changed; no accounts were removed.")

    for user in users:
        email = user.email.strip().lower()
        if email in SEEDED_EXCEPTIONS:
            raise CleanupBlocked(f"Seeded exception {email} was incorrectly marked for removal.")
        if admission.has_active_entitlement(db, user.id):
            raise CleanupBlocked(
                f"User {user.id} gained a valid entitlement after the dry run; no accounts were removed."
            )

    removed_ids: list[int] = []
    for user in users:
        email = user.email.strip().lower()
        db.query(UserRefreshSession).filter(UserRefreshSession.user_id == user.id).delete(
            synchronize_session=False
        )
        db.query(DevicePushRegistration).filter(
            DevicePushRegistration.user_id == user.id
        ).delete(synchronize_session=False)
        db.query(MagicLoginToken).filter(
            func.lower(MagicLoginToken.email) == email
        ).delete(synchronize_session=False)
        removed_ids.append(user.id)
        db.delete(user)

    db.flush()
    if (
        db.query(UserRefreshSession.id)
        .filter(UserRefreshSession.user_id.in_(removed_ids))
        .first()
        is not None
        or db.query(DevicePushRegistration.id)
        .filter(DevicePushRegistration.user_id.in_(removed_ids))
        .first()
        is not None
    ):
        raise CleanupBlocked("Account-owned authentication or device rows remain.")
    return removed_ids
