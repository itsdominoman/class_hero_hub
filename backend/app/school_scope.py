from __future__ import annotations

from typing import Any

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models_school import AuditLog, ClassSection, Membership, PlatformAdmin, School, StaffAssignment, SubjectGroup, User


def _entity_type_and_id(entity: Any) -> tuple[str, int | None]:
    if isinstance(entity, tuple) and len(entity) == 2:
        entity_type, entity_id = entity
        return str(entity_type), entity_id

    if isinstance(entity, str):
        return entity, None

    entity_type = getattr(entity, "__tablename__", None)
    if entity_type is None:
        entity_type = getattr(entity.__class__, "__tablename__", entity.__class__.__name__)
    return str(entity_type), getattr(entity, "id", None)


def write_audit(
    db: Session,
    actor: Any,
    action: str,
    entity: Any,
    detail: dict[str, Any] | None,
    school_id: int | None = None,
) -> AuditLog:
    entity_type, entity_id = _entity_type_and_id(entity)
    actor_user_id = getattr(actor, "id", actor)
    audit_log = AuditLog(
        school_id=school_id,
        actor_user_id=actor_user_id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        detail=detail or {},
    )
    db.add(audit_log)
    db.flush()
    return audit_log


def require_platform_admin(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> User:
    platform_admin = (
        db.query(PlatformAdmin)
        .filter(
            PlatformAdmin.user_id == current_user.id,
            PlatformAdmin.revoked_at.is_(None),
        )
        .first()
    )
    if not platform_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Platform admin access required",
        )
    return current_user


def _school_id_from_request(request: Request) -> int:
    raw_school_id = request.path_params.get("school_id") or request.headers.get("X-School-Id")
    if raw_school_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="School context required",
        )
    try:
        return int(raw_school_id)
    except (TypeError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid school context",
        )


def require_school_role(*roles: str):
    allowed_roles = {role for role in roles if role}

    def dependency(
        request: Request,
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db),
    ) -> Membership:
        school_id = _school_id_from_request(request)
        school = db.query(School).filter(School.id == school_id).first()
        if not school:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="School access denied",
            )

        if (school.status or "").lower() == "suspended":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="This school account is currently suspended.",
            )

        query = db.query(Membership).filter(
            Membership.school_id == school_id,
            Membership.user_id == current_user.id,
            Membership.status == "active",
            Membership.revoked_at.is_(None),
        )
        if allowed_roles:
            query = query.filter(Membership.role.in_(allowed_roles))

        membership = query.first()
        if not membership:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="School role required",
            )

        return membership

    return dependency


def _target_id_from_request(request: Request, param_name: str) -> int | None:
    raw_value = request.path_params.get(param_name) or request.query_params.get(param_name)
    if raw_value is None:
        return None
    try:
        return int(raw_value)
    except (TypeError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid {param_name}",
        )


def _today():
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).date()


def require_teacher_of(
    *,
    class_section_param: str = "class_section_id",
    subject_group_param: str = "subject_group_id",
):
    def dependency(
        request: Request,
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db),
    ) -> Membership:
        school_id = _school_id_from_request(request)
        school = db.query(School).filter(School.id == school_id).first()
        if not school or (school.status or "").lower() == "suspended":
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="School access denied")

        class_section_id = _target_id_from_request(request, class_section_param)
        subject_group_id = _target_id_from_request(request, subject_group_param)
        if (class_section_id is None and subject_group_id is None) or (
            class_section_id is not None and subject_group_id is not None
        ):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Exactly one teacher target is required")

        teacher_membership = (
            db.query(Membership)
            .filter(
                Membership.school_id == school_id,
                Membership.user_id == current_user.id,
                Membership.role == "teacher",
                Membership.status == "active",
                Membership.revoked_at.is_(None),
            )
            .first()
        )
        if not teacher_membership:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Teacher access required")

        if class_section_id is not None:
            target = (
                db.query(ClassSection)
                .filter(ClassSection.id == class_section_id, ClassSection.school_id == school_id)
                .first()
            )
            target_filter = StaffAssignment.class_section_id == class_section_id
        else:
            target = (
                db.query(SubjectGroup)
                .filter(SubjectGroup.id == subject_group_id, SubjectGroup.school_id == school_id)
                .first()
            )
            target_filter = StaffAssignment.subject_group_id == subject_group_id

        if not target:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Teacher target not found")

        today = _today()
        assignment = (
            db.query(StaffAssignment)
            .filter(
                StaffAssignment.school_id == school_id,
                StaffAssignment.membership_id == teacher_membership.id,
                target_filter,
                StaffAssignment.valid_from <= today,
                (StaffAssignment.valid_to.is_(None)) | (StaffAssignment.valid_to > today),
            )
            .first()
        )
        if not assignment:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Teacher assignment required")

        return teacher_membership

    return dependency
