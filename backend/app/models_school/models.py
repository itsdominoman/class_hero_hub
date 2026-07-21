import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import BigInteger, Boolean, CheckConstraint, Column, Date, DateTime, ForeignKey, Index, Integer, JSON, String, Text, Time, UniqueConstraint, Uuid, event, inspect as sa_inspect, text as sql_text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func

from app.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    name = Column(String)
    name_ar = Column(String, nullable=True)
    google_sub = Column(String, unique=True, index=True, nullable=True)
    locale = Column(String, default="en")
    status = Column(String, default="active")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    last_login_at = Column(DateTime(timezone=True), nullable=True)


class School(Base):
    __tablename__ = "schools"

    id = Column(Integer, primary_key=True, index=True)
    messaging_remote_ref = Column(Uuid(as_uuid=True), nullable=False, unique=True, default=uuid.uuid4)
    name = Column(String)
    name_ar = Column(String, nullable=True)
    slug = Column(String, unique=True, index=True)
    timezone = Column(String, default="Asia/Muscat")
    locale_default = Column(String, default="en")
    points_label = Column(String, default="Points")
    grade_level_label = Column(String, default="Grade")
    status = Column(String, default="pending_setup")
    suspended_at = Column(DateTime(timezone=True), nullable=True)
    suspended_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    suspend_reason = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Membership(Base):
    __tablename__ = "memberships"

    id = Column(Integer, primary_key=True, index=True)
    school_id = Column(Integer, ForeignKey("schools.id"))
    branch_campus_id = Column(Integer, ForeignKey("branch_campuses.id"), nullable=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    role = Column(String)
    status = Column(String, default="active")
    created_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    revoked_at = Column(DateTime(timezone=True), nullable=True)
    revoked_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    __table_args__ = (
        UniqueConstraint("school_id", "user_id", "role", name="uq_memberships_school_user_role"),
        Index("ix_memberships_school_role_status", "school_id", "role", "status"),
    )


class SchoolSystemOwner(Base):
    """Explicit, school-scoped System Owner state; never inferred from row age."""

    __tablename__ = "school_system_owners"

    school_id = Column(Integer, ForeignKey("schools.id", ondelete="RESTRICT"), primary_key=True)
    membership_id = Column(Integer, ForeignKey("memberships.id", ondelete="RESTRICT"), nullable=False, unique=True)
    owner_version = Column(Integer, nullable=False, default=1, server_default="1")
    owner_since = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        CheckConstraint("owner_version >= 1", name="ck_school_system_owners_version"),
        Index("ix_school_system_owners_membership", "membership_id", "school_id"),
    )


class SchoolSystemOwnerEvent(Base):
    """Append-only bootstrap, transfer, and emergency-recovery evidence."""

    __tablename__ = "school_system_owner_events"

    id = Column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True)
    event_id = Column(Uuid(as_uuid=True), nullable=False, unique=True, default=uuid.uuid4)
    school_id = Column(Integer, ForeignKey("schools.id", ondelete="RESTRICT"), nullable=False, index=True)
    action = Column(String(32), nullable=False)
    previous_membership_id = Column(Integer, ForeignKey("memberships.id", ondelete="RESTRICT"), nullable=True)
    new_membership_id = Column(Integer, ForeignKey("memberships.id", ondelete="RESTRICT"), nullable=True)
    actor_kind = Column(String(24), nullable=False)
    actor_user_id = Column(Integer, ForeignKey("users.id", ondelete="RESTRICT"), nullable=True)
    actor_membership_id = Column(Integer, ForeignKey("memberships.id", ondelete="RESTRICT"), nullable=True)
    reason = Column(Text, nullable=False)
    owner_version = Column(Integer, nullable=False)
    occurred_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    __table_args__ = (
        CheckConstraint(
            "action IN ('bootstrap', 'transfer', 'recovery_required', 'platform_recovery')",
            name="ck_school_system_owner_events_action",
        ),
        CheckConstraint(
            "actor_kind IN ('system', 'school_owner', 'platform_admin')",
            name="ck_school_system_owner_events_actor_kind",
        ),
        CheckConstraint("length(reason) BETWEEN 8 AND 2000", name="ck_school_system_owner_events_reason"),
        CheckConstraint("owner_version >= 1", name="ck_school_system_owner_events_version"),
        Index("ix_school_system_owner_events_school_time", "school_id", "occurred_at", "id"),
    )


class BranchCampus(Base):
    __tablename__ = "branch_campuses"

    id = Column(Integer, primary_key=True, index=True)
    school_id = Column(Integer, ForeignKey("schools.id"), nullable=False, index=True)
    code = Column(String, nullable=False)
    name = Column(String, nullable=False)
    name_ar = Column(String, nullable=True)
    sort_order = Column(Integer, default=0)
    status = Column(String, default="active")
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        UniqueConstraint("school_id", "code", name="uq_branch_campuses_school_code"),
    )


class EducationStage(Base):
    __tablename__ = "education_stages"

    id = Column(Integer, primary_key=True, index=True)
    school_id = Column(Integer, ForeignKey("schools.id"), nullable=False, index=True)
    code = Column(String, nullable=False)
    name = Column(String, nullable=False)
    name_ar = Column(String, nullable=True)
    sort_order = Column(Integer, default=0)
    status = Column(String, default="active")
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        UniqueConstraint("school_id", "code", name="uq_education_stages_school_code"),
    )


class AcademicYear(Base):
    __tablename__ = "academic_years"

    id = Column(Integer, primary_key=True, index=True)
    school_id = Column(Integer, ForeignKey("schools.id"), nullable=False, index=True)
    code = Column(String, nullable=False)
    name = Column(String, nullable=False)
    name_ar = Column(String, nullable=True)
    sort_order = Column(Integer, default=0)
    status = Column(String, default="active")
    is_current = Column(Boolean, default=False, nullable=False)
    start_date = Column(Date, nullable=True)
    end_date = Column(Date, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        UniqueConstraint("school_id", "code", name="uq_academic_years_school_code"),
        UniqueConstraint("school_id", "name", name="uq_academic_years_school_name"),
    )


class GradeLevel(Base):
    __tablename__ = "grade_levels"

    id = Column(Integer, primary_key=True, index=True)
    school_id = Column(Integer, ForeignKey("schools.id"), nullable=False, index=True)
    education_stage_id = Column(Integer, ForeignKey("education_stages.id"), nullable=True)
    code = Column(String, nullable=False)
    name = Column(String, nullable=False)
    name_ar = Column(String, nullable=True)
    sort_order = Column(Integer, default=0)
    status = Column(String, default="active")
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        UniqueConstraint("school_id", "code", name="uq_grade_levels_school_code"),
    )


class ClassSection(Base):
    __tablename__ = "class_sections"

    id = Column(Integer, primary_key=True, index=True)
    school_id = Column(Integer, ForeignKey("schools.id"), nullable=False, index=True)
    branch_campus_id = Column(Integer, ForeignKey("branch_campuses.id"), nullable=False)
    academic_year_id = Column(Integer, ForeignKey("academic_years.id"), nullable=False)
    grade_level_id = Column(Integer, ForeignKey("grade_levels.id"), nullable=False)
    code = Column(String, nullable=False)
    name = Column(String, nullable=False)
    name_ar = Column(String, nullable=True)
    sort_order = Column(Integer, default=0)
    status = Column(String, default="active")
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        UniqueConstraint(
            "school_id",
            "branch_campus_id",
            "academic_year_id",
            "grade_level_id",
            "code",
            name="uq_class_sections_school_branch_year_level_code",
        ),
    )


class Subject(Base):
    __tablename__ = "subjects"

    id = Column(Integer, primary_key=True, index=True)
    school_id = Column(Integer, ForeignKey("schools.id"), nullable=False, index=True)
    code = Column(String, nullable=False)
    name = Column(String, nullable=False)
    name_ar = Column(String, nullable=True)
    sort_order = Column(Integer, default=0)
    status = Column(String, default="active")
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        UniqueConstraint("school_id", "code", name="uq_subjects_school_code"),
    )


class SubjectGroup(Base):
    __tablename__ = "subject_groups"

    id = Column(Integer, primary_key=True, index=True)
    school_id = Column(Integer, ForeignKey("schools.id"), nullable=False, index=True)
    academic_year_id = Column(Integer, ForeignKey("academic_years.id"), nullable=False)
    class_section_id = Column(Integer, ForeignKey("class_sections.id"), nullable=True)
    grade_level_id = Column(Integer, ForeignKey("grade_levels.id"), nullable=True)
    subject_id = Column(Integer, ForeignKey("subjects.id"), nullable=False)
    code = Column(String, nullable=False)
    name = Column(String, nullable=False)
    name_ar = Column(String, nullable=True)
    sort_order = Column(Integer, default=0)
    status = Column(String, default="active")
    enrolment_policy = Column(String, nullable=False, default="explicit_only", server_default="explicit_only")
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        UniqueConstraint(
            "school_id",
            "academic_year_id",
            "class_section_id",
            "grade_level_id",
            "subject_id",
            "code",
            name="uq_subject_groups_school_year_section_level_subject_code",
        ),
        CheckConstraint("class_section_id IS NOT NULL OR grade_level_id IS NOT NULL", name="ck_subject_groups_context_required"),
        CheckConstraint(
            "enrolment_policy IN ('explicit_only', 'default_for_section', 'default_for_grade')",
            name="ck_subject_groups_enrolment_policy",
        ),
        Index("ix_subject_groups_school_status", "school_id", "status"),
    )


def _default_staff_invite_expires_at():
    return datetime.now(timezone.utc) + timedelta(days=7)


class StaffInvite(Base):
    __tablename__ = "staff_invites"

    id = Column(Integer, primary_key=True, index=True)
    school_id = Column(Integer, ForeignKey("schools.id"))
    email = Column(String, index=True)
    role = Column(String, default="school_admin")
    token_hash = Column(String, unique=True, index=True)
    invited_by_user_id = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    expires_at = Column(DateTime(timezone=True), default=_default_staff_invite_expires_at)
    revoked_at = Column(DateTime(timezone=True), nullable=True)
    accepted_at = Column(DateTime(timezone=True), nullable=True)
    accepted_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    send_status = Column(String, default="pending")
    last_send_error = Column(String, nullable=True)


def _default_assignment_valid_from():
    return datetime.now(timezone.utc).date()


class StaffAssignment(Base):
    __tablename__ = "staff_assignments"

    id = Column(Integer, primary_key=True, index=True)
    school_id = Column(Integer, ForeignKey("schools.id"), nullable=False, index=True)
    membership_id = Column(Integer, ForeignKey("memberships.id"), nullable=False, index=True)
    class_section_id = Column(Integer, ForeignKey("class_sections.id"), nullable=True, index=True)
    subject_group_id = Column(Integer, ForeignKey("subject_groups.id"), nullable=True, index=True)
    role = Column(String, nullable=False)
    valid_from = Column(Date, nullable=False, default=_default_assignment_valid_from)
    valid_to = Column(Date, nullable=True)
    created_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        CheckConstraint(
            "(class_section_id IS NOT NULL AND subject_group_id IS NULL) OR "
            "(class_section_id IS NULL AND subject_group_id IS NOT NULL)",
            name="ck_staff_assignments_exactly_one_target",
        ),
        Index("ix_staff_assignments_school_membership", "school_id", "membership_id"),
    )


class DemoSeedRecord(Base):
    __tablename__ = "demo_seed_records"

    id = Column(Integer, primary_key=True, index=True)
    seed_namespace = Column(String, nullable=False, index=True)
    entity_type = Column(String, nullable=False, index=True)
    entity_key = Column(String, nullable=False)
    model_name = Column(String, nullable=False)
    model_id = Column(Integer, nullable=True, index=True)
    metadata_json = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    __table_args__ = (
        UniqueConstraint("seed_namespace", "entity_type", "entity_key", name="uq_demo_seed_records_namespace_type_key"),
        Index("ix_demo_seed_records_namespace_type", "seed_namespace", "entity_type"),
    )


class Student(Base):
    __tablename__ = "students"

    id = Column(Integer, primary_key=True, index=True)
    school_id = Column(Integer, ForeignKey("schools.id"), nullable=False, index=True)
    external_ref = Column(String, nullable=True, index=True)
    first_name = Column(String, nullable=False)
    last_name = Column(String, nullable=False)
    preferred_name = Column(String, nullable=True)
    name_ar = Column(String, nullable=True)
    date_of_birth = Column(Date, nullable=True)
    gender = Column(String, nullable=True)
    avatar_id = Column(Integer, nullable=True)
    status = Column(String, default="active", nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index("ix_students_school_status", "school_id", "status"),
    )


def _default_enrolment_valid_from():
    return datetime.now(timezone.utc).date()


class Enrolment(Base):
    __tablename__ = "enrolments"

    id = Column(Integer, primary_key=True, index=True)
    school_id = Column(Integer, ForeignKey("schools.id"), nullable=False, index=True)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False, index=True)
    class_section_id = Column(Integer, ForeignKey("class_sections.id"), nullable=True, index=True)
    subject_group_id = Column(Integer, ForeignKey("subject_groups.id"), nullable=True, index=True)
    kind = Column(String, nullable=False, default="member", server_default="member")
    valid_from = Column(Date, nullable=False, default=_default_enrolment_valid_from)
    valid_to = Column(Date, nullable=True)
    created_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        CheckConstraint(
            "(class_section_id IS NOT NULL AND subject_group_id IS NULL) OR "
            "(class_section_id IS NULL AND subject_group_id IS NOT NULL)",
            name="ck_enrolments_exactly_one_target",
        ),
        CheckConstraint("kind IN ('member', 'excluded')", name="ck_enrolments_kind"),
        Index("ix_enrolments_school_section_kind", "school_id", "class_section_id", "kind"),
        Index("ix_enrolments_school_group_kind", "school_id", "subject_group_id", "kind"),
    )


class DefaultSubjectTemplate(Base):
    __tablename__ = "default_subject_templates"

    id = Column(Integer, primary_key=True, index=True)
    school_id = Column(Integer, ForeignKey("schools.id"), nullable=False, index=True)
    education_stage_id = Column(Integer, ForeignKey("education_stages.id"), nullable=True)
    grade_level_id = Column(Integer, ForeignKey("grade_levels.id"), nullable=True)
    subject_id = Column(Integer, ForeignKey("subjects.id"), nullable=False)
    status = Column(String, default="active", nullable=False)
    sort_order = Column(Integer, default=0)
    created_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        UniqueConstraint(
            "school_id",
            "education_stage_id",
            "grade_level_id",
            "subject_id",
            name="uq_default_subject_templates_school_stage_grade_subject",
        ),
        CheckConstraint(
            "(education_stage_id IS NOT NULL AND grade_level_id IS NULL) OR "
            "(education_stage_id IS NULL AND grade_level_id IS NOT NULL)",
            name="ck_default_subject_templates_exactly_one_scope",
        ),
        Index("ix_default_subject_templates_school_status", "school_id", "status"),
    )


class Import(Base):
    __tablename__ = "imports"

    id = Column(Integer, primary_key=True, index=True)
    school_id = Column(Integer, ForeignKey("schools.id"), nullable=False, index=True)
    kind = Column(String, nullable=False, default="students", server_default="students")
    filename = Column(String, nullable=True)
    status = Column(String, nullable=False, default="staged", server_default="staged")
    uploaded_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    summary = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    committed_at = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        CheckConstraint(
            "status IN ('staged', 'committed', 'discarded')",
            name="ck_imports_status",
        ),
        Index("ix_imports_school_status", "school_id", "status"),
    )


class ImportRow(Base):
    __tablename__ = "import_rows"

    id = Column(Integer, primary_key=True, index=True)
    import_id = Column(Integer, ForeignKey("imports.id"), nullable=False, index=True)
    row_number = Column(Integer, nullable=False)
    raw = Column(JSON, nullable=False)
    action = Column(String, nullable=False)
    errors = Column(JSON, nullable=True)
    warnings = Column(JSON, nullable=True)
    applied_entity_id = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        CheckConstraint(
            "action IN ('create', 'update', 'move', 'restore', 'skip', 'error')",
            name="ck_import_rows_action",
        ),
    )


class StudentGuardianContact(Base):
    """A draft guardian contact staged by import (never a login, never contacted).

    S9 guardian onboarding is expected to consume/migrate these rows into
    real `guardian_links` + invites once that workflow exists; `status`
    tracks that lifecycle (`draft` until S9 acts on it, then `linked` or
    `ignored`) so a later re-import never silently overwrites a decision S9
    has already made.
    """

    __tablename__ = "student_guardian_contacts"

    id = Column(Integer, primary_key=True, index=True)
    school_id = Column(Integer, ForeignKey("schools.id"), nullable=False, index=True)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False, index=True)
    slot = Column(Integer, nullable=False)
    name = Column(String, nullable=True)
    email = Column(String, nullable=True)
    relationship = Column(String, nullable=True)
    source_import_id = Column(Integer, ForeignKey("imports.id"), nullable=True)
    status = Column(String, nullable=False, default="draft", server_default="draft")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        UniqueConstraint("school_id", "student_id", "slot", name="uq_student_guardian_contacts_school_student_slot"),
        CheckConstraint("slot IN (1, 2)", name="ck_student_guardian_contacts_slot"),
        CheckConstraint(
            "relationship IS NULL OR relationship IN ('mother', 'father', 'guardian', 'other')",
            name="ck_student_guardian_contacts_relationship",
        ),
        CheckConstraint("status IN ('draft', 'linked', 'ignored')", name="ck_student_guardian_contacts_status"),
        Index("ix_student_guardian_contacts_school_student", "school_id", "student_id"),
    )


def _default_guardian_invite_expires_at():
    return datetime.now(timezone.utc) + timedelta(days=30)


class GuardianInvite(Base):
    __tablename__ = "guardian_invites"

    id = Column(Integer, primary_key=True, index=True)
    school_id = Column(Integer, ForeignKey("schools.id"), nullable=False, index=True)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False, index=True)
    student_guardian_contact_id = Column(Integer, ForeignKey("student_guardian_contacts.id"), nullable=True, index=True)
    slot = Column(Integer, nullable=True)
    token_hash = Column(String, unique=True, index=True, nullable=False)
    display_code_last4 = Column(String, nullable=True)
    relationship = Column(String, nullable=True)
    guardian_name = Column(String, nullable=True)
    guardian_email = Column(String, nullable=True)
    expires_at = Column(DateTime(timezone=True), default=_default_guardian_invite_expires_at, nullable=False)
    revoked_at = Column(DateTime(timezone=True), nullable=True)
    revoked_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    claimed_at = Column(DateTime(timezone=True), nullable=True)
    claimed_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        CheckConstraint("slot IS NULL OR slot IN (1, 2)", name="ck_guardian_invites_slot"),
        CheckConstraint(
            "relationship IS NULL OR relationship IN ('mother', 'father', 'guardian', 'other')",
            name="ck_guardian_invites_relationship",
        ),
        Index("ix_guardian_invites_school_student", "school_id", "student_id"),
    )


class GuardianLink(Base):
    __tablename__ = "guardian_links"

    id = Column(Integer, primary_key=True, index=True)
    school_id = Column(Integer, ForeignKey("schools.id"), nullable=False, index=True)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    relationship = Column(String, nullable=True)
    display_name = Column(String, nullable=True)
    source_guardian_invite_id = Column(Integer, ForeignKey("guardian_invites.id"), nullable=True)
    student_guardian_contact_id = Column(Integer, ForeignKey("student_guardian_contacts.id"), nullable=True)
    email_matched_contact = Column(Boolean, default=False, server_default="false", nullable=True)
    status = Column(String, default="active", server_default="active", nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    revoked_at = Column(DateTime(timezone=True), nullable=True)
    revoked_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    __table_args__ = (
        UniqueConstraint("student_id", "user_id", name="uq_guardian_links_student_user"),
        CheckConstraint(
            "relationship IS NULL OR relationship IN ('mother', 'father', 'guardian', 'other')",
            name="ck_guardian_links_relationship",
        ),
        CheckConstraint("status IN ('active', 'revoked')", name="ck_guardian_links_status"),
        Index("ix_guardian_links_school_user", "school_id", "user_id"),
    )


def _default_fhh_invite_expires_at():
    return datetime.now(timezone.utc) + timedelta(hours=72)


class FhhLinkInvite(Base):
    __tablename__ = "fhh_link_invites"

    id = Column(Integer, primary_key=True, index=True)
    school_id = Column(Integer, ForeignKey("schools.id"), nullable=False, index=True)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False, index=True)
    token_hash = Column(String, unique=True, nullable=False, index=True)
    display_code_last4 = Column(String, nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False, default=_default_fhh_invite_expires_at)
    consumed_at = Column(DateTime(timezone=True), nullable=True)
    consumed_by = Column(String, nullable=True)
    revoked_at = Column(DateTime(timezone=True), nullable=True)
    revoked_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (Index("ix_fhh_link_invites_school_student", "school_id", "student_id"),)


class FhhLink(Base):
    __tablename__ = "fhh_links"

    id = Column(Integer, primary_key=True, index=True)
    school_id = Column(Integer, ForeignKey("schools.id"), nullable=False, index=True)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False, index=True)
    source_invite_id = Column(Integer, ForeignKey("fhh_link_invites.id"), nullable=False, unique=True)
    link_token_hash = Column(String, unique=True, nullable=False, index=True)
    fhh_child_ref = Column(String, nullable=False)
    status = Column(String, nullable=False, default="active", server_default="active")
    revoked_at = Column(DateTime(timezone=True), nullable=True)
    revoked_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        CheckConstraint("status IN ('active', 'revoked')", name="ck_fhh_links_status"),
        Index("ix_fhh_links_school_student_status", "school_id", "student_id", "status"),
    )


class SchoolMessagingPolicy(Base):
    __tablename__ = "school_messaging_policies"

    school_id = Column(Integer, ForeignKey("schools.id", ondelete="RESTRICT"), primary_key=True)
    enabled = Column(Boolean, nullable=False, default=False, server_default="false")
    guardian_replies_enabled = Column(Boolean, nullable=False, default=True, server_default="true")
    delivery_receipts_visible = Column(Boolean, nullable=False, default=True, server_default="true")
    read_receipts_visible = Column(Boolean, nullable=False, default=False, server_default="false")
    allow_staff_out_of_hours_opt_in = Column(Boolean, nullable=False, default=False, server_default="false")
    teachers_may_mark_urgent = Column(Boolean, nullable=False, default=False, server_default="false")
    contact_hours_enabled = Column(Boolean, nullable=False, default=False, server_default="false")
    notification_delay_mode = Column(
        String(40),
        nullable=False,
        default="delay_notifications_only",
        server_default="delay_notifications_only",
    )
    notification_preview_mode = Column(String(24), nullable=False, default="generic", server_default="generic")
    retention_days = Column(Integer, nullable=False, default=2557, server_default="2557")
    email_mode = Column(String(16), nullable=False, default="off", server_default="off")
    policy_version = Column(Integer, nullable=False, default=1, server_default="1")
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
    updated_by_membership_id = Column(Integer, ForeignKey("memberships.id", ondelete="SET NULL"), nullable=True)

    __table_args__ = (
        CheckConstraint("notification_preview_mode IN ('generic', 'sender_only', 'body')", name="ck_school_messaging_policies_preview"),
        CheckConstraint(
            "notification_delay_mode = 'delay_notifications_only'",
            name="ck_school_messaging_policies_delay_mode",
        ),
        CheckConstraint("email_mode IN ('off', 'immediate', 'digest')", name="ck_school_messaging_policies_email_mode"),
        CheckConstraint("retention_days BETWEEN 30 AND 36500", name="ck_school_messaging_policies_retention"),
        CheckConstraint("policy_version >= 1", name="ck_school_messaging_policies_version"),
    )


class SchoolContactWindow(Base):
    __tablename__ = "school_contact_windows"

    id = Column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True)
    school_id = Column(Integer, ForeignKey("schools.id", ondelete="RESTRICT"), nullable=False, index=True)
    weekday = Column(Integer, nullable=False)
    start_local = Column(Time, nullable=False)
    end_local = Column(Time, nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        UniqueConstraint("school_id", "weekday", name="uq_school_contact_windows_school_weekday"),
        CheckConstraint("weekday BETWEEN 1 AND 7", name="ck_school_contact_windows_weekday"),
        CheckConstraint("start_local <> end_local", name="ck_school_contact_windows_nonempty"),
        Index("ix_school_contact_windows_school_weekday", "school_id", "weekday"),
    )


class SchoolContactException(Base):
    __tablename__ = "school_contact_exceptions"

    id = Column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True)
    school_id = Column(Integer, ForeignKey("schools.id", ondelete="RESTRICT"), nullable=False, index=True)
    local_date = Column(Date, nullable=False)
    kind = Column(String(16), nullable=False)
    start_local = Column(Time, nullable=True)
    end_local = Column(Time, nullable=True)
    label = Column(String(160), nullable=True)
    label_ar = Column(String(160), nullable=True)
    created_by_membership_id = Column(
        Integer,
        ForeignKey("memberships.id", ondelete="SET NULL"),
        nullable=True,
    )
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        UniqueConstraint("school_id", "local_date", name="uq_school_contact_exceptions_school_date"),
        CheckConstraint("kind IN ('closed', 'custom')", name="ck_school_contact_exceptions_kind"),
        CheckConstraint(
            "(kind = 'closed' AND start_local IS NULL AND end_local IS NULL) OR "
            "(kind = 'custom' AND start_local IS NOT NULL AND end_local IS NOT NULL "
            "AND start_local <> end_local)",
            name="ck_school_contact_exceptions_window_shape",
        ),
        Index("ix_school_contact_exceptions_school_date", "school_id", "local_date"),
    )


class StaffMessagingPreference(Base):
    __tablename__ = "staff_messaging_preferences"

    membership_id = Column(
        Integer,
        ForeignKey("memberships.id", ondelete="RESTRICT"),
        primary_key=True,
    )
    school_id = Column(Integer, ForeignKey("schools.id", ondelete="RESTRICT"), nullable=False, index=True)
    out_of_hours_notifications_enabled = Column(Boolean, nullable=False, default=False, server_default="false")
    preference_version = Column(Integer, nullable=False, default=1, server_default="1")
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        CheckConstraint("preference_version >= 1", name="ck_staff_messaging_preferences_version"),
        Index("ix_staff_messaging_preferences_school_membership", "school_id", "membership_id"),
    )


class SchoolFeatureControl(Base):
    """Current school-level state for jurisdiction-sensitive product features."""

    __tablename__ = "school_feature_controls"

    id = Column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True)
    school_id = Column(Integer, ForeignKey("schools.id", ondelete="RESTRICT"), nullable=False, index=True)
    feature = Column(String(40), nullable=False)
    enabled = Column(Boolean, nullable=False, default=False, server_default="false")
    control_version = Column(Integer, nullable=False, default=1, server_default="1")
    disclosure_version = Column(String(40), nullable=False)
    updated_by_membership_id = Column(Integer, ForeignKey("memberships.id", ondelete="RESTRICT"), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        UniqueConstraint("school_id", "feature", name="uq_school_feature_controls_school_feature"),
        CheckConstraint("feature IN ('voice_notes')", name="ck_school_feature_controls_feature"),
        CheckConstraint("control_version >= 1", name="ck_school_feature_controls_version"),
    )


class SchoolFeatureControlAuditEvent(Base):
    """Append-only evidence for every compliance-controlled feature decision."""

    __tablename__ = "school_feature_control_audit_events"

    id = Column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True)
    event_id = Column(Uuid(as_uuid=True), nullable=False, unique=True, default=uuid.uuid4)
    school_id = Column(Integer, ForeignKey("schools.id", ondelete="RESTRICT"), nullable=False, index=True)
    feature = Column(String(40), nullable=False)
    enabled = Column(Boolean, nullable=False)
    control_version = Column(Integer, nullable=False)
    disclosure_version = Column(String(40), nullable=False)
    acknowledging_user_id = Column(Integer, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    acknowledging_membership_id = Column(Integer, ForeignKey("memberships.id", ondelete="RESTRICT"), nullable=False)
    occurred_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    __table_args__ = (
        CheckConstraint("feature IN ('voice_notes')", name="ck_school_feature_audit_feature"),
        CheckConstraint("control_version >= 1", name="ck_school_feature_audit_version"),
        Index("ix_school_feature_audit_school_feature_time", "school_id", "feature", "occurred_at", "id"),
    )


class FhhMessagingIdentity(Base):
    """Minimal lifecycle identity synchronized from FHH; not a participant."""

    __tablename__ = "fhh_messaging_identities"

    id = Column(Integer, primary_key=True)
    school_id = Column(Integer, ForeignKey("schools.id", ondelete="RESTRICT"), nullable=False, index=True)
    provider = Column(String(24), nullable=False, default="fhh", server_default="fhh")
    external_subject_ref = Column(Uuid(as_uuid=True), nullable=False)
    display_name = Column(String(200), nullable=False)
    preferred_locale = Column(String(8), nullable=False, default="en", server_default="en")
    status = Column(String(16), nullable=False, default="active", server_default="active")
    first_seen_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    last_seen_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    revoked_at = Column(DateTime(timezone=True), nullable=True)
    anonymized_at = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        UniqueConstraint("school_id", "provider", "external_subject_ref", name="uq_fhh_messaging_identity_subject"),
        CheckConstraint("preferred_locale IN ('en', 'ar')", name="ck_fhh_messaging_identities_locale"),
        CheckConstraint("status IN ('active', 'revoked', 'anonymized')", name="ck_fhh_messaging_identities_status"),
    )


class FhhMessagingIdentityLink(Base):
    __tablename__ = "fhh_messaging_identity_links"

    id = Column(Integer, primary_key=True)
    school_id = Column(Integer, ForeignKey("schools.id", ondelete="RESTRICT"), nullable=False, index=True)
    fhh_link_id = Column(Integer, ForeignKey("fhh_links.id", ondelete="RESTRICT"), nullable=False, index=True)
    identity_id = Column(Integer, ForeignKey("fhh_messaging_identities.id", ondelete="RESTRICT"), nullable=False, index=True)
    status = Column(String(16), nullable=False, default="active", server_default="active")
    sync_version = Column(Integer, nullable=False, default=1, server_default="1")
    granted_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    revoked_at = Column(DateTime(timezone=True), nullable=True)
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        UniqueConstraint("fhh_link_id", "identity_id", name="uq_fhh_messaging_identity_link"),
        CheckConstraint("status IN ('active', 'revoked')", name="ck_fhh_messaging_identity_links_status"),
        CheckConstraint("sync_version >= 1", name="ck_fhh_messaging_identity_links_version"),
        Index("ix_fhh_messaging_identity_links_school_status", "school_id", "status"),
    )


class FhhMessagingLifecycleEvent(Base):
    __tablename__ = "fhh_messaging_lifecycle_events"

    id = Column(Integer, primary_key=True)
    event_id = Column(Uuid(as_uuid=True), nullable=False, unique=True)
    school_id = Column(Integer, ForeignKey("schools.id", ondelete="RESTRICT"), nullable=False, index=True)
    fhh_link_id = Column(Integer, ForeignKey("fhh_links.id", ondelete="RESTRICT"), nullable=False, index=True)
    action = Column(String(40), nullable=False)
    external_subject_ref = Column(Uuid(as_uuid=True), nullable=True)
    sync_version = Column(Integer, nullable=False)
    outcome = Column(String(24), nullable=False)
    occurred_at = Column(DateTime(timezone=True), nullable=False)
    applied_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    __table_args__ = (
        CheckConstraint(
            "action IN ('parent_granted', 'parent_profile_changed', 'parent_revoked', "
            "'identity_anonymized', 'link_revoked', 'family_deleted')",
            name="ck_fhh_messaging_lifecycle_events_action",
        ),
        CheckConstraint("sync_version >= 1", name="ck_fhh_messaging_lifecycle_events_version"),
        CheckConstraint("outcome IN ('applied', 'stale_ignored')", name="ck_fhh_messaging_lifecycle_events_outcome"),
        Index("ix_fhh_messaging_lifecycle_events_link_applied", "fhh_link_id", "applied_at"),
    )


class FhhMessagingAssertionUse(Base):
    """One-time actor assertion evidence; assertion material is never retained."""

    __tablename__ = "fhh_messaging_assertion_uses"

    id = Column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True)
    jti = Column(Uuid(as_uuid=True), nullable=False)
    school_id = Column(
        Integer, ForeignKey("schools.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    fhh_link_id = Column(
        Integer, ForeignKey("fhh_links.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    identity_id = Column(
        Integer,
        ForeignKey("fhh_messaging_identities.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    request_method = Column(String(8), nullable=False)
    request_path_hash = Column(String(64), nullable=False)
    body_hash = Column(String(64), nullable=False)
    used_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    expires_at = Column(DateTime(timezone=True), nullable=False)

    __table_args__ = (
        UniqueConstraint(
            "jti",
            name="uq_fhh_messaging_assertion_uses_jti",
        ),
        CheckConstraint(
            "request_method IN ('GET', 'POST')",
            name="ck_fhh_messaging_assertion_uses_method",
        ),
        Index(
            "ix_fhh_messaging_assertion_uses_expiry",
            "expires_at",
            "id",
        ),
        Index(
            "ix_fhh_messaging_assertion_uses_link_used",
            "fhh_link_id",
            "used_at",
        ),
    )


class Conversation(Base):
    __tablename__ = "conversations"

    id = Column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True)
    public_id = Column(Uuid(as_uuid=True), nullable=False, unique=True, default=uuid.uuid4)
    school_id = Column(Integer, ForeignKey("schools.id", ondelete="RESTRICT"), nullable=False, index=True)
    branch_campus_id = Column(Integer, ForeignKey("branch_campuses.id", ondelete="RESTRICT"), nullable=True)
    kind = Column(String(24), nullable=False)
    student_id = Column(Integer, ForeignKey("students.id", ondelete="RESTRICT"), nullable=True)
    primary_staff_membership_id = Column(Integer, ForeignKey("memberships.id", ondelete="RESTRICT"), nullable=True)
    staff_membership_low_id = Column(Integer, ForeignKey("memberships.id", ondelete="RESTRICT"), nullable=True)
    staff_membership_high_id = Column(Integer, ForeignKey("memberships.id", ondelete="RESTRICT"), nullable=True)
    internal_guardian_user_id = Column(Integer, ForeignKey("users.id", ondelete="RESTRICT"), nullable=True)
    external_guardian_participant_id = Column(
        Integer,
        ForeignKey("fhh_messaging_identities.id", ondelete="RESTRICT"),
        nullable=True,
    )
    context_class_section_id = Column(Integer, ForeignKey("class_sections.id", ondelete="SET NULL"), nullable=True)
    context_subject_group_id = Column(Integer, ForeignKey("subject_groups.id", ondelete="SET NULL"), nullable=True)
    context_label = Column(String(200), nullable=True)
    context_label_ar = Column(String(200), nullable=True)
    status = Column(String(32), nullable=False, default="active", server_default="active")
    last_message_sequence = Column(BigInteger, nullable=False, default=0, server_default="0")
    last_message_at = Column(DateTime(timezone=True), nullable=True)
    created_by_participant_id = Column(
        BigInteger().with_variant(Integer, "sqlite"),
        ForeignKey(
            "conversation_participants.id",
            ondelete="SET NULL",
            use_alter=True,
            name="fk_conversations_created_by_participant",
        ),
        nullable=True,
    )
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    closed_at = Column(DateTime(timezone=True), nullable=True)
    closed_reason = Column(String(64), nullable=True)
    restriction_type = Column(String(32), nullable=True)
    restricted_at = Column(DateTime(timezone=True), nullable=True)
    restricted_by_membership_id = Column(
        Integer, ForeignKey("memberships.id", ondelete="RESTRICT"), nullable=True
    )
    reopening_requires_approval = Column(
        Boolean, nullable=False, default=False, server_default="false"
    )
    safeguarding_closed_by_membership_id = Column(
        Integer, ForeignKey("memberships.id", ondelete="RESTRICT"), nullable=True
    )

    __table_args__ = (
        CheckConstraint(
            "(kind = 'student_staff' AND student_id IS NOT NULL AND primary_staff_membership_id IS NOT NULL "
            "AND staff_membership_low_id IS NULL AND staff_membership_high_id IS NULL "
            "AND internal_guardian_user_id IS NULL AND external_guardian_participant_id IS NULL) OR "
            "(kind = 'staff_direct' AND student_id IS NULL AND primary_staff_membership_id IS NULL "
            "AND staff_membership_low_id IS NOT NULL AND staff_membership_high_id IS NOT NULL "
            "AND staff_membership_low_id < staff_membership_high_id "
            "AND internal_guardian_user_id IS NULL AND external_guardian_participant_id IS NULL) OR "
            "(kind = 'guardian_direct' AND primary_staff_membership_id IS NOT NULL "
            "AND staff_membership_low_id IS NULL AND staff_membership_high_id IS NULL "
            "AND ((internal_guardian_user_id IS NOT NULL AND external_guardian_participant_id IS NULL) "
            "OR (internal_guardian_user_id IS NULL AND external_guardian_participant_id IS NOT NULL)))",
            name="ck_conversations_kind_shape",
        ),
        CheckConstraint(
            "status IN ('active', 'closed_assignment_ended', 'closed_student_archived', "
            "'closed_restricted', 'archived')",
            name="ck_conversations_status",
        ),
        CheckConstraint(
            "restriction_type IS NULL OR restriction_type IN "
            "('family_replies', 'staff_replies', 'both_replies', 'read_only')",
            name="ck_conversations_restriction_type",
        ),
        CheckConstraint(
            "(restriction_type IS NULL AND restricted_at IS NULL "
            "AND restricted_by_membership_id IS NULL) OR "
            "(restriction_type IS NOT NULL AND restricted_at IS NOT NULL "
            "AND restricted_by_membership_id IS NOT NULL)",
            name="ck_conversations_restriction_shape",
        ),
        CheckConstraint("last_message_sequence >= 0", name="ck_conversations_last_sequence"),
        CheckConstraint(
            "(context_class_section_id IS NULL OR context_subject_group_id IS NULL)",
            name="ck_conversations_single_context",
        ),
        Index(
            "uq_conversations_active_student_staff",
            "school_id",
            "student_id",
            "primary_staff_membership_id",
            unique=True,
            postgresql_where=sql_text("kind = 'student_staff' AND status = 'active'"),
            sqlite_where=sql_text("kind = 'student_staff' AND status = 'active'"),
        ),
        Index(
            "uq_conversations_active_staff_direct",
            "school_id",
            "staff_membership_low_id",
            "staff_membership_high_id",
            unique=True,
            postgresql_where=sql_text("kind = 'staff_direct' AND status = 'active'"),
            sqlite_where=sql_text("kind = 'staff_direct' AND status = 'active'"),
        ),
        Index(
            "uq_conversations_active_guardian_direct_internal_student",
            "school_id",
            "primary_staff_membership_id",
            "internal_guardian_user_id",
            "student_id",
            unique=True,
            postgresql_where=sql_text(
                "kind = 'guardian_direct' AND status = 'active' "
                "AND internal_guardian_user_id IS NOT NULL AND student_id IS NOT NULL"
            ),
            sqlite_where=sql_text(
                "kind = 'guardian_direct' AND status = 'active' "
                "AND internal_guardian_user_id IS NOT NULL AND student_id IS NOT NULL"
            ),
        ),
        Index(
            "uq_conversations_active_guardian_direct_internal_general",
            "school_id",
            "primary_staff_membership_id",
            "internal_guardian_user_id",
            unique=True,
            postgresql_where=sql_text(
                "kind = 'guardian_direct' AND status = 'active' "
                "AND internal_guardian_user_id IS NOT NULL AND student_id IS NULL"
            ),
            sqlite_where=sql_text(
                "kind = 'guardian_direct' AND status = 'active' "
                "AND internal_guardian_user_id IS NOT NULL AND student_id IS NULL"
            ),
        ),
        Index(
            "uq_conversations_active_guardian_direct_external_student",
            "school_id",
            "primary_staff_membership_id",
            "external_guardian_participant_id",
            "student_id",
            unique=True,
            postgresql_where=sql_text(
                "kind = 'guardian_direct' AND status = 'active' "
                "AND external_guardian_participant_id IS NOT NULL AND student_id IS NOT NULL"
            ),
            sqlite_where=sql_text(
                "kind = 'guardian_direct' AND status = 'active' "
                "AND external_guardian_participant_id IS NOT NULL AND student_id IS NOT NULL"
            ),
        ),
        Index(
            "uq_conversations_active_guardian_direct_external_general",
            "school_id",
            "primary_staff_membership_id",
            "external_guardian_participant_id",
            unique=True,
            postgresql_where=sql_text(
                "kind = 'guardian_direct' AND status = 'active' "
                "AND external_guardian_participant_id IS NOT NULL AND student_id IS NULL"
            ),
            sqlite_where=sql_text(
                "kind = 'guardian_direct' AND status = 'active' "
                "AND external_guardian_participant_id IS NOT NULL AND student_id IS NULL"
            ),
        ),
        Index("ix_conversations_school_status_activity", "school_id", "status", "last_message_at", "id"),
        Index("ix_conversations_school_student_status", "school_id", "student_id", "status"),
        Index(
            "ix_conversations_school_primary_staff_activity",
            "school_id",
            "primary_staff_membership_id",
            "status",
            "last_message_at",
        ),
    )


class ConversationParticipant(Base):
    __tablename__ = "conversation_participants"

    id = Column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True)
    conversation_id = Column(
        BigInteger().with_variant(Integer, "sqlite"),
        ForeignKey("conversations.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    participant_kind = Column(String(24), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="RESTRICT"), nullable=True)
    membership_id = Column(Integer, ForeignKey("memberships.id", ondelete="RESTRICT"), nullable=True)
    external_participant_id = Column(
        Integer,
        ForeignKey("fhh_messaging_identities.id", ondelete="RESTRICT"),
        nullable=True,
    )
    side = Column(String(16), nullable=False)
    display_name_snapshot = Column(String(200), nullable=False)
    joined_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    left_at = Column(DateTime(timezone=True), nullable=True)
    last_delivered_sequence = Column(BigInteger, nullable=False, default=0, server_default="0")
    last_delivered_at = Column(DateTime(timezone=True), nullable=True)
    last_read_sequence = Column(BigInteger, nullable=False, default=0, server_default="0")
    last_read_at = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        CheckConstraint(
            "(participant_kind = 'staff' AND user_id IS NOT NULL AND membership_id IS NOT NULL "
            "AND external_participant_id IS NULL AND side = 'staff') OR "
            "(participant_kind = 'chh_guardian' AND user_id IS NOT NULL AND membership_id IS NULL "
            "AND external_participant_id IS NULL AND side = 'guardian') OR "
            "(participant_kind = 'fhh_parent' AND user_id IS NULL AND membership_id IS NULL "
            "AND external_participant_id IS NOT NULL AND side = 'guardian')",
            name="ck_conversation_participants_actor_shape",
        ),
        CheckConstraint("last_delivered_sequence >= 0", name="ck_conversation_participants_delivered"),
        CheckConstraint("last_read_sequence >= 0", name="ck_conversation_participants_read"),
        Index(
            "uq_conversation_participants_active_staff",
            "conversation_id",
            "membership_id",
            unique=True,
            postgresql_where=sql_text("participant_kind = 'staff' AND left_at IS NULL"),
            sqlite_where=sql_text("participant_kind = 'staff' AND left_at IS NULL"),
        ),
        Index(
            "uq_conversation_participants_active_chh_guardian",
            "conversation_id",
            "user_id",
            unique=True,
            postgresql_where=sql_text("participant_kind = 'chh_guardian' AND left_at IS NULL"),
            sqlite_where=sql_text("participant_kind = 'chh_guardian' AND left_at IS NULL"),
        ),
        Index(
            "uq_conversation_participants_active_fhh_parent",
            "conversation_id",
            "external_participant_id",
            unique=True,
            postgresql_where=sql_text("participant_kind = 'fhh_parent' AND left_at IS NULL"),
            sqlite_where=sql_text("participant_kind = 'fhh_parent' AND left_at IS NULL"),
        ),
        Index("ix_conversation_participants_conversation_side", "conversation_id", "side", "left_at"),
    )


class ConversationAccessGrant(Base):
    __tablename__ = "conversation_access_grants"

    id = Column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True)
    conversation_id = Column(
        BigInteger().with_variant(Integer, "sqlite"),
        ForeignKey("conversations.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    participant_id = Column(
        BigInteger().with_variant(Integer, "sqlite"),
        ForeignKey("conversation_participants.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )
    source_type = Column(String(32), nullable=False)
    staff_assignment_id = Column(Integer, ForeignKey("staff_assignments.id", ondelete="RESTRICT"), nullable=True)
    membership_id = Column(Integer, ForeignKey("memberships.id", ondelete="RESTRICT"), nullable=True)
    guardian_link_id = Column(Integer, ForeignKey("guardian_links.id", ondelete="RESTRICT"), nullable=True)
    fhh_link_id = Column(Integer, ForeignKey("fhh_links.id", ondelete="RESTRICT"), nullable=True)
    valid_from = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    valid_to = Column(DateTime(timezone=True), nullable=True)
    visible_from_sequence = Column(BigInteger, nullable=False, default=1, server_default="1")
    visible_through_sequence = Column(BigInteger, nullable=True)
    grant_reason = Column(String(64), nullable=False)
    granted_by_membership_id = Column(Integer, ForeignKey("memberships.id", ondelete="RESTRICT"), nullable=True)
    revoked_at = Column(DateTime(timezone=True), nullable=True)
    revoked_by_membership_id = Column(Integer, ForeignKey("memberships.id", ondelete="RESTRICT"), nullable=True)
    revoke_reason = Column(String(64), nullable=True)

    __table_args__ = (
        CheckConstraint(
            "(source_type = 'staff_assignment' AND staff_assignment_id IS NOT NULL "
            "AND membership_id IS NULL AND guardian_link_id IS NULL AND fhh_link_id IS NULL) OR "
            "(source_type = 'school_admin_membership' AND staff_assignment_id IS NULL "
            "AND membership_id IS NOT NULL AND guardian_link_id IS NULL AND fhh_link_id IS NULL) OR "
            "(source_type = 'guardian_link' AND staff_assignment_id IS NULL "
            "AND membership_id IS NULL AND guardian_link_id IS NOT NULL AND fhh_link_id IS NULL) OR "
            "(source_type = 'fhh_link' AND staff_assignment_id IS NULL "
            "AND membership_id IS NULL AND guardian_link_id IS NULL AND fhh_link_id IS NOT NULL) OR "
            "(source_type = 'manual_history_grant' AND staff_assignment_id IS NULL "
            "AND membership_id IS NULL AND guardian_link_id IS NULL AND fhh_link_id IS NULL "
            "AND granted_by_membership_id IS NOT NULL)",
            name="ck_conversation_access_grants_source_shape",
        ),
        CheckConstraint("visible_from_sequence >= 1", name="ck_conversation_access_grants_visible_from"),
        CheckConstraint(
            "visible_through_sequence IS NULL OR visible_through_sequence >= visible_from_sequence",
            name="ck_conversation_access_grants_visible_range",
        ),
        CheckConstraint("valid_to IS NULL OR valid_to >= valid_from", name="ck_conversation_access_grants_valid_range"),
        CheckConstraint(
            "(revoked_at IS NULL AND revoke_reason IS NULL AND revoked_by_membership_id IS NULL) OR "
            "(revoked_at IS NOT NULL AND revoke_reason IS NOT NULL)",
            name="ck_conversation_access_grants_revoke_shape",
        ),
        Index(
            "ix_conversation_access_grants_participant_validity",
            "conversation_id",
            "participant_id",
            "valid_from",
            "valid_to",
        ),
        Index("ix_conversation_access_grants_staff_assignment", "staff_assignment_id", "revoked_at"),
        Index("ix_conversation_access_grants_membership", "membership_id", "revoked_at"),
        Index("ix_conversation_access_grants_guardian_link", "guardian_link_id", "revoked_at"),
        Index("ix_conversation_access_grants_fhh_link", "fhh_link_id", "revoked_at"),
    )


class Message(Base):
    __tablename__ = "messages"

    id = Column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True)
    public_id = Column(Uuid(as_uuid=True), nullable=False, unique=True, default=uuid.uuid4)
    school_id = Column(Integer, ForeignKey("schools.id", ondelete="RESTRICT"), nullable=False, index=True)
    conversation_id = Column(
        BigInteger().with_variant(Integer, "sqlite"),
        ForeignKey("conversations.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    sequence = Column(BigInteger, nullable=False)
    sender_participant_id = Column(
        BigInteger().with_variant(Integer, "sqlite"),
        ForeignKey("conversation_participants.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    sender_display_name_snapshot = Column(String(200), nullable=False)
    client_message_id = Column(Uuid(as_uuid=True), nullable=False)
    message_type = Column(String(24), nullable=False, default="standard", server_default="standard")
    body = Column(Text, nullable=True)
    state = Column(String(16), nullable=False, default="active", server_default="active")
    urgent = Column(Boolean, nullable=False, default=False, server_default="false")
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    tombstoned_at = Column(DateTime(timezone=True), nullable=True)
    tombstoned_by_membership_id = Column(Integer, ForeignKey("memberships.id", ondelete="RESTRICT"), nullable=True)
    tombstone_reason = Column(String(160), nullable=True)
    retention_disposed_at = Column(DateTime(timezone=True), nullable=True)
    retention_policy_version = Column(Integer, nullable=True)
    retention_content_sha256 = Column(String(64), nullable=True)

    __table_args__ = (
        UniqueConstraint("conversation_id", "sequence", name="uq_messages_conversation_sequence"),
        UniqueConstraint(
            "conversation_id",
            "sender_participant_id",
            "client_message_id",
            name="uq_messages_sender_client_id",
        ),
        CheckConstraint("sequence >= 1", name="ck_messages_sequence"),
        CheckConstraint("message_type IN ('standard', 'voice_note')", name="ck_messages_type"),
        CheckConstraint(
            "body IS NULL OR (length(body) BETWEEN 1 AND 10000)",
            name="ck_messages_body_length",
        ),
        CheckConstraint("state IN ('active', 'tombstoned')", name="ck_messages_state"),
        CheckConstraint(
            "(state = 'active' AND tombstoned_at IS NULL AND tombstoned_by_membership_id IS NULL "
            "AND tombstone_reason IS NULL) OR "
            "(state = 'tombstoned' AND tombstoned_at IS NOT NULL AND tombstone_reason IS NOT NULL)",
            name="ck_messages_tombstone_shape",
        ),
        CheckConstraint(
            "(retention_disposed_at IS NULL AND retention_policy_version IS NULL "
            "AND retention_content_sha256 IS NULL) OR "
            "(retention_disposed_at IS NOT NULL AND retention_policy_version >= 1 "
            "AND length(retention_content_sha256) = 64 AND body IS NULL)",
            name="ck_messages_retention_disposition",
        ),
        Index("ix_messages_conversation_page", "conversation_id", "sequence"),
        Index("ix_messages_school_created", "school_id", "created_at", "id"),
    )


class MessageMedia(Base):
    __tablename__ = "message_media"

    id = Column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True)
    public_id = Column(Uuid(as_uuid=True), nullable=False, unique=True, default=uuid.uuid4)
    client_upload_id = Column(Uuid(as_uuid=True), nullable=False)
    school_id = Column(Integer, ForeignKey("schools.id", ondelete="RESTRICT"), nullable=False, index=True)
    conversation_id = Column(
        BigInteger().with_variant(Integer, "sqlite"),
        ForeignKey("conversations.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    message_id = Column(
        BigInteger().with_variant(Integer, "sqlite"),
        ForeignKey("messages.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )
    uploaded_by_participant_id = Column(
        BigInteger().with_variant(Integer, "sqlite"),
        ForeignKey("conversation_participants.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    sort_order = Column(Integer, nullable=False, default=0, server_default="0")
    state = Column(String(16), nullable=False, default="processing", server_default="processing")
    storage_backend = Column(String(16), nullable=False, default="local", server_default="local")
    full_storage_key = Column(String(500), nullable=True)
    thumbnail_storage_key = Column(String(500), nullable=True)
    content_type = Column(String(64), nullable=True)
    full_bytes = Column(Integer, nullable=True)
    thumbnail_bytes = Column(Integer, nullable=True)
    width = Column(Integer, nullable=True)
    height = Column(Integer, nullable=True)
    thumbnail_width = Column(Integer, nullable=True)
    thumbnail_height = Column(Integer, nullable=True)
    source_checksum_sha256 = Column(String(64), nullable=False)
    checksum_sha256 = Column(String(64), nullable=True)
    original_filename_safe = Column(String(160), nullable=True)
    metadata_stripped = Column(Boolean, nullable=False, default=False, server_default="false")
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    attached_at = Column(DateTime(timezone=True), nullable=True)
    expires_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc) + timedelta(hours=24),
    )
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    archive_full_storage_key = Column(String(500), nullable=True)
    archive_thumbnail_storage_key = Column(String(500), nullable=True)
    archive_full_sha256 = Column(String(64), nullable=True)
    archive_thumbnail_sha256 = Column(String(64), nullable=True)
    archived_at = Column(DateTime(timezone=True), nullable=True)
    archive_verified_at = Column(DateTime(timezone=True), nullable=True)
    hot_deleted_at = Column(DateTime(timezone=True), nullable=True)
    retention_deleted_at = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        UniqueConstraint(
            "conversation_id",
            "uploaded_by_participant_id",
            "client_upload_id",
            name="uq_message_media_participant_upload",
        ),
        UniqueConstraint("message_id", "sort_order", name="uq_message_media_message_order"),
        CheckConstraint("sort_order BETWEEN 0 AND 4", name="ck_message_media_sort_order"),
        CheckConstraint(
            "state IN ('processing', 'ready', 'attached', 'archived', 'retention_deleted', "
            "'failed', 'expired', 'deleted')",
            name="ck_message_media_state",
        ),
        CheckConstraint("storage_backend = 'local'", name="ck_message_media_storage_backend"),
        CheckConstraint(
            "(state IN ('ready', 'attached') AND full_storage_key IS NOT NULL "
            "AND thumbnail_storage_key IS NOT NULL AND content_type IS NOT NULL "
            "AND full_bytes > 0 AND thumbnail_bytes > 0 AND width > 0 AND height > 0 "
            "AND thumbnail_width > 0 AND thumbnail_height > 0 AND checksum_sha256 IS NOT NULL "
            "AND metadata_stripped = true) OR state NOT IN ('ready', 'attached')",
            name="ck_message_media_ready_shape",
        ),
        CheckConstraint(
            "(state IN ('attached', 'archived', 'retention_deleted') AND message_id IS NOT NULL "
            "AND attached_at IS NOT NULL) OR "
            "(state NOT IN ('attached', 'archived', 'retention_deleted') AND message_id IS NULL "
            "AND attached_at IS NULL)",
            name="ck_message_media_attachment_shape",
        ),
        CheckConstraint(
            "(state IN ('expired', 'deleted') AND deleted_at IS NOT NULL) "
            "OR (state NOT IN ('expired', 'deleted') AND deleted_at IS NULL)",
            name="ck_message_media_deleted_shape",
        ),
        CheckConstraint(
            "(state = 'archived' AND archive_full_storage_key IS NOT NULL "
            "AND archive_thumbnail_storage_key IS NOT NULL AND length(archive_full_sha256) = 64 "
            "AND length(archive_thumbnail_sha256) = 64 AND archived_at IS NOT NULL "
            "AND archive_verified_at IS NOT NULL) OR state <> 'archived'",
            name="ck_message_media_archive_shape",
        ),
        CheckConstraint(
            "(state = 'retention_deleted' AND retention_deleted_at IS NOT NULL "
            "AND full_storage_key IS NULL AND thumbnail_storage_key IS NULL "
            "AND archive_full_storage_key IS NULL AND archive_thumbnail_storage_key IS NULL) "
            "OR state <> 'retention_deleted'",
            name="ck_message_media_retention_deleted",
        ),
        Index("ix_message_media_conversation_message", "conversation_id", "message_id", "sort_order"),
        Index("ix_message_media_state_expiry", "state", "expires_at", "id"),
        Index("ix_message_media_archive_selection", "school_id", "state", "created_at", "id"),
    )


class MessageVoiceMedia(Base):
    __tablename__ = "message_voice_media"

    id = Column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True)
    public_id = Column(Uuid(as_uuid=True), nullable=False, unique=True, default=uuid.uuid4)
    client_upload_id = Column(Uuid(as_uuid=True), nullable=False)
    school_id = Column(Integer, ForeignKey("schools.id", ondelete="RESTRICT"), nullable=False, index=True)
    conversation_id = Column(
        BigInteger().with_variant(Integer, "sqlite"),
        ForeignKey("conversations.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    message_id = Column(
        BigInteger().with_variant(Integer, "sqlite"),
        ForeignKey("messages.id", ondelete="RESTRICT"),
        nullable=True,
        unique=True,
        index=True,
    )
    uploaded_by_participant_id = Column(
        BigInteger().with_variant(Integer, "sqlite"),
        ForeignKey("conversation_participants.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    state = Column(String(16), nullable=False, default="processing", server_default="processing")
    storage_backend = Column(String(16), nullable=False, default="local", server_default="local")
    storage_key = Column(String(500), nullable=True)
    content_type = Column(String(64), nullable=True)
    size_bytes = Column(Integer, nullable=True)
    duration_ms = Column(Integer, nullable=True)
    codec = Column(String(24), nullable=True)
    container = Column(String(24), nullable=True)
    source_checksum_sha256 = Column(String(64), nullable=False)
    checksum_sha256 = Column(String(64), nullable=True)
    metadata_stripped = Column(Boolean, nullable=False, default=False, server_default="false")
    transcription_state = Column(String(24), nullable=False, default="not_requested", server_default="not_requested")
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    attached_at = Column(DateTime(timezone=True), nullable=True)
    expires_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc) + timedelta(hours=24),
    )
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    archive_storage_key = Column(String(500), nullable=True)
    archive_sha256 = Column(String(64), nullable=True)
    archived_at = Column(DateTime(timezone=True), nullable=True)
    archive_verified_at = Column(DateTime(timezone=True), nullable=True)
    hot_deleted_at = Column(DateTime(timezone=True), nullable=True)
    retention_deleted_at = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        UniqueConstraint(
            "conversation_id",
            "uploaded_by_participant_id",
            "client_upload_id",
            name="uq_message_voice_media_participant_upload",
        ),
        CheckConstraint(
            "state IN ('processing', 'ready', 'attached', 'archived', 'retention_deleted', "
            "'failed', 'expired', 'deleted')",
            name="ck_message_voice_media_state",
        ),
        CheckConstraint("storage_backend = 'local'", name="ck_message_voice_media_storage_backend"),
        CheckConstraint(
            "(state IN ('ready', 'attached') AND storage_key IS NOT NULL "
            "AND content_type = 'audio/mp4' AND size_bytes > 0 "
            "AND duration_ms BETWEEN 600 AND 180000 AND codec = 'aac' "
            "AND container = 'mp4' AND checksum_sha256 IS NOT NULL "
            "AND metadata_stripped = true) OR state NOT IN ('ready', 'attached')",
            name="ck_message_voice_media_ready_shape",
        ),
        CheckConstraint(
            "(state IN ('attached', 'archived', 'retention_deleted') AND message_id IS NOT NULL "
            "AND attached_at IS NOT NULL) OR "
            "(state NOT IN ('attached', 'archived', 'retention_deleted') AND message_id IS NULL "
            "AND attached_at IS NULL)",
            name="ck_message_voice_media_attachment_shape",
        ),
        CheckConstraint(
            "(state IN ('expired', 'deleted') AND deleted_at IS NOT NULL) "
            "OR (state NOT IN ('expired', 'deleted') AND deleted_at IS NULL)",
            name="ck_message_voice_media_deleted_shape",
        ),
        CheckConstraint(
            "(state = 'archived' AND archive_storage_key IS NOT NULL "
            "AND length(archive_sha256) = 64 AND archived_at IS NOT NULL "
            "AND archive_verified_at IS NOT NULL) OR state <> 'archived'",
            name="ck_message_voice_media_archive_shape",
        ),
        CheckConstraint(
            "(state = 'retention_deleted' AND retention_deleted_at IS NOT NULL "
            "AND storage_key IS NULL AND archive_storage_key IS NULL) "
            "OR state <> 'retention_deleted'",
            name="ck_message_voice_media_retention_deleted",
        ),
        CheckConstraint(
            "transcription_state IN ('not_requested')",
            name="ck_message_voice_media_transcription_state",
        ),
        Index("ix_message_voice_media_conversation_message", "conversation_id", "message_id"),
        Index("ix_message_voice_media_state_expiry", "state", "expires_at", "id"),
        Index("ix_message_voice_media_archive_selection", "school_id", "state", "created_at", "id"),
    )


class MessageReceiptEvent(Base):
    __tablename__ = "message_receipt_events"

    id = Column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True)
    conversation_id = Column(
        BigInteger().with_variant(Integer, "sqlite"),
        ForeignKey("conversations.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    participant_id = Column(
        BigInteger().with_variant(Integer, "sqlite"),
        ForeignKey("conversation_participants.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    event_type = Column(String(16), nullable=False)
    through_sequence = Column(BigInteger, nullable=False)
    client_ack_id = Column(Uuid(as_uuid=True), nullable=False)
    device_session_ref = Column(String(96), nullable=True)
    occurred_at = Column(DateTime(timezone=True), nullable=False)
    recorded_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    __table_args__ = (
        UniqueConstraint(
            "participant_id",
            "event_type",
            "client_ack_id",
            name="uq_message_receipt_events_client_ack",
        ),
        CheckConstraint("event_type IN ('delivered', 'read')", name="ck_message_receipt_events_type"),
        CheckConstraint("through_sequence >= 0", name="ck_message_receipt_events_sequence"),
        Index("ix_message_receipt_events_conversation_recorded", "conversation_id", "recorded_at", "id"),
    )


class MessagingAuditEvent(Base):
    __tablename__ = "messaging_audit_events"

    id = Column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True)
    event_id = Column(Uuid(as_uuid=True), nullable=False, unique=True, default=uuid.uuid4)
    school_id = Column(Integer, ForeignKey("schools.id", ondelete="RESTRICT"), nullable=False, index=True)
    actor_kind = Column(String(24), nullable=False)
    actor_user_id = Column(Integer, ForeignKey("users.id", ondelete="RESTRICT"), nullable=True)
    actor_membership_id = Column(Integer, ForeignKey("memberships.id", ondelete="RESTRICT"), nullable=True)
    actor_external_participant_id = Column(
        Integer,
        ForeignKey("fhh_messaging_identities.id", ondelete="RESTRICT"),
        nullable=True,
    )
    event_type = Column(String(80), nullable=False)
    conversation_id = Column(
        BigInteger().with_variant(Integer, "sqlite"),
        ForeignKey("conversations.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    message_id = Column(
        BigInteger().with_variant(Integer, "sqlite"),
        ForeignKey("messages.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    participant_id = Column(
        BigInteger().with_variant(Integer, "sqlite"),
        ForeignKey("conversation_participants.id", ondelete="SET NULL"),
        nullable=True,
    )
    detail = Column(JSON, nullable=False, default=dict)
    request_correlation_id = Column(String(96), nullable=True)
    occurred_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    __table_args__ = (
        CheckConstraint(
            "(actor_kind = 'system' AND actor_user_id IS NULL AND actor_membership_id IS NULL "
            "AND actor_external_participant_id IS NULL) OR "
            "(actor_kind IN ('staff', 'safeguarding_admin') AND actor_user_id IS NOT NULL "
            "AND actor_membership_id IS NOT NULL AND actor_external_participant_id IS NULL) OR "
            "(actor_kind = 'chh_guardian' AND actor_user_id IS NOT NULL "
            "AND actor_membership_id IS NULL AND actor_external_participant_id IS NULL) OR "
            "(actor_kind = 'fhh_parent' AND actor_user_id IS NULL "
            "AND actor_membership_id IS NULL AND actor_external_participant_id IS NOT NULL)",
            name="ck_messaging_audit_events_actor_shape",
        ),
        Index("ix_messaging_audit_events_school_occurred", "school_id", "occurred_at", "id"),
        Index("ix_messaging_audit_events_type_occurred", "event_type", "occurred_at", "id"),
    )


class MessagingPermissionGrant(Base):
    __tablename__ = "messaging_permission_grants"

    id = Column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True)
    public_id = Column(Uuid(as_uuid=True), nullable=False, unique=True, default=uuid.uuid4)
    school_id = Column(Integer, ForeignKey("schools.id", ondelete="RESTRICT"), nullable=False, index=True)
    membership_id = Column(Integer, ForeignKey("memberships.id", ondelete="RESTRICT"), nullable=False, index=True)
    permission = Column(String(80), nullable=False)
    granted_by_membership_id = Column(Integer, ForeignKey("memberships.id", ondelete="RESTRICT"), nullable=False)
    grant_reason = Column(Text, nullable=False)
    granted_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    revoked_at = Column(DateTime(timezone=True), nullable=True)
    revoked_by_membership_id = Column(Integer, ForeignKey("memberships.id", ondelete="RESTRICT"), nullable=True)
    revoke_reason = Column(Text, nullable=True)

    __table_args__ = (
        CheckConstraint(
            "permission IN ('messaging.safeguarding_review', 'messaging.moderate', "
            "'messaging.export_evidence', 'messaging.export_internal_notes', "
            "'messaging.manage_safeguarding_permissions', 'messaging.manage_legal_holds')",
            name="ck_messaging_permission_grants_permission",
        ),
        CheckConstraint(
            "length(grant_reason) BETWEEN 3 AND 1000",
            name="ck_messaging_permission_grants_reason",
        ),
        CheckConstraint(
            "(revoked_at IS NULL AND revoked_by_membership_id IS NULL AND revoke_reason IS NULL) OR "
            "(revoked_at IS NOT NULL AND revoked_by_membership_id IS NOT NULL "
            "AND length(revoke_reason) BETWEEN 3 AND 1000)",
            name="ck_messaging_permission_grants_revoke_shape",
        ),
        Index(
            "uq_messaging_permission_grants_active",
            "school_id",
            "membership_id",
            "permission",
            unique=True,
            postgresql_where=sql_text("revoked_at IS NULL"),
            sqlite_where=sql_text("revoked_at IS NULL"),
        ),
        Index(
            "ix_messaging_permission_grants_school_permission",
            "school_id",
            "permission",
            "revoked_at",
        ),
    )


class MessagingRetentionPolicy(Base):
    """Append-only, effective-date-aware school retention policy version."""

    __tablename__ = "messaging_retention_policies"

    id = Column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True)
    public_id = Column(Uuid(as_uuid=True), nullable=False, unique=True, default=uuid.uuid4)
    school_id = Column(Integer, ForeignKey("schools.id", ondelete="RESTRICT"), nullable=False, index=True)
    policy_version = Column(Integer, nullable=False)
    effective_at = Column(DateTime(timezone=True), nullable=False)
    rules = Column(JSON().with_variant(JSONB, "postgresql"), nullable=False, default=dict)
    reason = Column(Text, nullable=False)
    acknowledged_school_policy = Column(Boolean, nullable=False, default=False, server_default="false")
    created_by_membership_id = Column(Integer, ForeignKey("memberships.id", ondelete="RESTRICT"), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    cancelled_at = Column(DateTime(timezone=True), nullable=True)
    cancelled_by_membership_id = Column(Integer, ForeignKey("memberships.id", ondelete="RESTRICT"), nullable=True)
    cancellation_reason = Column(Text, nullable=True)

    __table_args__ = (
        UniqueConstraint("school_id", "policy_version", name="uq_messaging_retention_policy_version"),
        CheckConstraint("policy_version >= 1", name="ck_messaging_retention_policy_version"),
        CheckConstraint("length(reason) BETWEEN 8 AND 2000", name="ck_messaging_retention_policy_reason"),
        CheckConstraint("acknowledged_school_policy = true", name="ck_messaging_retention_policy_acknowledged"),
        CheckConstraint(
            "(cancelled_at IS NULL AND cancelled_by_membership_id IS NULL AND cancellation_reason IS NULL) OR "
            "(cancelled_at IS NOT NULL AND cancelled_by_membership_id IS NOT NULL "
            "AND length(cancellation_reason) BETWEEN 8 AND 2000)",
            name="ck_messaging_retention_policy_cancellation",
        ),
        Index("ix_messaging_retention_policy_effective", "school_id", "effective_at", "policy_version"),
    )


class MessagingLegalHold(Base):
    """Confidential legal-hold state. Reasons never enter participant/FHH projections."""

    __tablename__ = "messaging_legal_holds"

    id = Column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True)
    public_id = Column(Uuid(as_uuid=True), nullable=False, unique=True, default=uuid.uuid4)
    school_id = Column(Integer, ForeignKey("schools.id", ondelete="RESTRICT"), nullable=False, index=True)
    scope_type = Column(String(24), nullable=False)
    conversation_id = Column(BigInteger().with_variant(Integer, "sqlite"), ForeignKey("conversations.id", ondelete="RESTRICT"), nullable=True, index=True)
    message_id = Column(BigInteger().with_variant(Integer, "sqlite"), ForeignKey("messages.id", ondelete="RESTRICT"), nullable=True, index=True)
    student_id = Column(Integer, ForeignKey("students.id", ondelete="RESTRICT"), nullable=True, index=True)
    reason = Column(Text, nullable=False)
    case_reference = Column(String(160), nullable=True)
    starts_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    review_at = Column(DateTime(timezone=True), nullable=True)
    created_by_membership_id = Column(Integer, ForeignKey("memberships.id", ondelete="RESTRICT"), nullable=False)
    released_at = Column(DateTime(timezone=True), nullable=True)
    released_by_membership_id = Column(Integer, ForeignKey("memberships.id", ondelete="RESTRICT"), nullable=True)
    release_reason = Column(Text, nullable=True)

    __table_args__ = (
        CheckConstraint("scope_type IN ('conversation', 'message', 'student')", name="ck_messaging_legal_holds_scope"),
        CheckConstraint(
            "(scope_type = 'conversation' AND conversation_id IS NOT NULL AND message_id IS NULL AND student_id IS NULL) OR "
            "(scope_type = 'message' AND conversation_id IS NULL AND message_id IS NOT NULL AND student_id IS NULL) OR "
            "(scope_type = 'student' AND conversation_id IS NULL AND message_id IS NULL AND student_id IS NOT NULL)",
            name="ck_messaging_legal_holds_target",
        ),
        CheckConstraint("length(reason) BETWEEN 8 AND 4000", name="ck_messaging_legal_holds_reason"),
        CheckConstraint("review_at IS NULL OR review_at > starts_at", name="ck_messaging_legal_holds_review"),
        CheckConstraint(
            "(released_at IS NULL AND released_by_membership_id IS NULL AND release_reason IS NULL) OR "
            "(released_at IS NOT NULL AND released_by_membership_id IS NOT NULL "
            "AND length(release_reason) BETWEEN 8 AND 4000)",
            name="ck_messaging_legal_holds_release",
        ),
        Index("ix_messaging_legal_holds_school_active", "school_id", "released_at", "scope_type", "id"),
    )


class MessagingLegalHoldEvent(Base):
    __tablename__ = "messaging_legal_hold_events"

    id = Column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True)
    event_id = Column(Uuid(as_uuid=True), nullable=False, unique=True, default=uuid.uuid4)
    hold_id = Column(BigInteger().with_variant(Integer, "sqlite"), ForeignKey("messaging_legal_holds.id", ondelete="RESTRICT"), nullable=False, index=True)
    school_id = Column(Integer, ForeignKey("schools.id", ondelete="RESTRICT"), nullable=False, index=True)
    action = Column(String(16), nullable=False)
    actor_membership_id = Column(Integer, ForeignKey("memberships.id", ondelete="RESTRICT"), nullable=False)
    reason = Column(Text, nullable=False)
    occurred_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    __table_args__ = (
        CheckConstraint("action IN ('placed', 'released')", name="ck_messaging_legal_hold_events_action"),
        CheckConstraint("length(reason) BETWEEN 8 AND 4000", name="ck_messaging_legal_hold_events_reason"),
        Index("ix_messaging_legal_hold_events_school_time", "school_id", "occurred_at", "id"),
    )


class MessagingOperationsJob(Base):
    """Durable, leased jobs for retention, archival, and evidence export custody."""

    __tablename__ = "messaging_operations_jobs"

    id = Column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True)
    public_id = Column(Uuid(as_uuid=True), nullable=False, unique=True, default=uuid.uuid4)
    school_id = Column(Integer, ForeignKey("schools.id", ondelete="RESTRICT"), nullable=False, index=True)
    job_type = Column(String(32), nullable=False)
    state = Column(String(24), nullable=False, default="pending", server_default="pending")
    dry_run = Column(Boolean, nullable=False, default=False, server_default="false")
    policy_id = Column(BigInteger().with_variant(Integer, "sqlite"), ForeignKey("messaging_retention_policies.id", ondelete="RESTRICT"), nullable=True)
    export_id = Column(BigInteger().with_variant(Integer, "sqlite"), ForeignKey("messaging_evidence_exports.id", ondelete="RESTRICT"), nullable=True)
    requested_by_membership_id = Column(Integer, ForeignKey("memberships.id", ondelete="RESTRICT"), nullable=False)
    operator_reason = Column(Text, nullable=False)
    payload = Column(JSON().with_variant(JSONB, "postgresql"), nullable=False, default=dict)
    progress = Column(JSON().with_variant(JSONB, "postgresql"), nullable=False, default=dict)
    last_cursor = Column(String(200), nullable=True)
    lease_owner = Column(String(96), nullable=True)
    lease_expires_at = Column(DateTime(timezone=True), nullable=True)
    attempt_count = Column(Integer, nullable=False, default=0, server_default="0")
    next_attempt_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    cancellation_requested_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    last_error_code = Column(String(80), nullable=True)
    last_error_detail = Column(String(500), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        CheckConstraint("job_type IN ('retention_preview', 'retention_execute', 'archive_media', 'evidence_export')", name="ck_messaging_operations_jobs_type"),
        CheckConstraint("state IN ('pending', 'leased', 'succeeded', 'failed', 'dead', 'cancelled')", name="ck_messaging_operations_jobs_state"),
        CheckConstraint("length(operator_reason) BETWEEN 8 AND 2000", name="ck_messaging_operations_jobs_reason"),
        CheckConstraint("attempt_count >= 0", name="ck_messaging_operations_jobs_attempts"),
        CheckConstraint(
            "(state = 'leased' AND lease_owner IS NOT NULL AND lease_expires_at IS NOT NULL) OR "
            "(state <> 'leased' AND lease_owner IS NULL AND lease_expires_at IS NULL)",
            name="ck_messaging_operations_jobs_lease",
        ),
        Index("ix_messaging_operations_jobs_claim", "state", "next_attempt_at", "lease_expires_at", "id"),
        Index("ix_messaging_operations_jobs_school_type", "school_id", "job_type", "created_at", "id"),
    )


class MessagingWorkerHeartbeat(Base):
    __tablename__ = "messaging_worker_heartbeats"

    worker_name = Column(String(48), primary_key=True)
    instance_id = Column(String(96), nullable=False)
    last_seen_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    last_success_at = Column(DateTime(timezone=True), nullable=True)
    last_error_code = Column(String(80), nullable=True)
    processed_total = Column(BigInteger, nullable=False, default=0, server_default="0")
    recovered_leases_total = Column(BigInteger, nullable=False, default=0, server_default="0")


class MessagingOperatorAction(Base):
    __tablename__ = "messaging_operator_actions"

    id = Column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True)
    event_id = Column(Uuid(as_uuid=True), nullable=False, unique=True, default=uuid.uuid4)
    school_id = Column(Integer, ForeignKey("schools.id", ondelete="RESTRICT"), nullable=False, index=True)
    actor_membership_id = Column(Integer, ForeignKey("memberships.id", ondelete="RESTRICT"), nullable=False)
    queue_kind = Column(String(32), nullable=False)
    action = Column(String(16), nullable=False)
    target_ref = Column(String(120), nullable=False)
    reason = Column(Text, nullable=False)
    occurred_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    __table_args__ = (
        CheckConstraint("queue_kind IN ('notification', 'retention', 'archive', 'export')", name="ck_messaging_operator_actions_queue"),
        CheckConstraint("action IN ('retry', 'cancel')", name="ck_messaging_operator_actions_action"),
        CheckConstraint("length(reason) BETWEEN 8 AND 2000", name="ck_messaging_operator_actions_reason"),
        Index("ix_messaging_operator_actions_school_time", "school_id", "occurred_at", "id"),
    )


class SafeguardingReviewSession(Base):
    __tablename__ = "safeguarding_review_sessions"

    id = Column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True)
    public_id = Column(Uuid(as_uuid=True), nullable=False, unique=True, default=uuid.uuid4)
    school_id = Column(Integer, ForeignKey("schools.id", ondelete="RESTRICT"), nullable=False, index=True)
    conversation_id = Column(BigInteger().with_variant(Integer, "sqlite"), ForeignKey("conversations.id", ondelete="RESTRICT"), nullable=False, index=True)
    reviewer_membership_id = Column(Integer, ForeignKey("memberships.id", ondelete="RESTRICT"), nullable=False, index=True)
    reason_category = Column(String(48), nullable=False)
    justification = Column(Text, nullable=False)
    acknowledgement = Column(Boolean, nullable=False)
    started_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    expires_at = Column(DateTime(timezone=True), nullable=False)
    ended_at = Column(DateTime(timezone=True), nullable=True)
    revoked_at = Column(DateTime(timezone=True), nullable=True)
    revoked_by_membership_id = Column(Integer, ForeignKey("memberships.id", ondelete="RESTRICT"), nullable=True)
    end_reason = Column(String(48), nullable=True)

    __table_args__ = (
        CheckConstraint(
            "reason_category IN ('reported_concern', 'safeguarding_investigation', "
            "'complaint', 'staff_conduct_review', 'parent_communication_review', "
            "'legal_regulatory_request', 'authorised_technical_support', 'other')",
            name="ck_safeguarding_review_sessions_reason",
        ),
        CheckConstraint(
            "length(justification) BETWEEN 8 AND 2000",
            name="ck_safeguarding_review_sessions_justification",
        ),
        CheckConstraint("acknowledgement = true", name="ck_safeguarding_review_sessions_acknowledged"),
        CheckConstraint("expires_at > started_at", name="ck_safeguarding_review_sessions_expiry"),
        CheckConstraint(
            "revoked_at IS NULL OR revoked_by_membership_id IS NOT NULL",
            name="ck_safeguarding_review_sessions_revoke_shape",
        ),
        Index(
            "ix_safeguarding_review_sessions_actor_expiry",
            "school_id",
            "reviewer_membership_id",
            "expires_at",
            "ended_at",
        ),
        Index(
            "ix_safeguarding_review_sessions_conversation",
            "school_id",
            "conversation_id",
            "started_at",
        ),
    )


class SafeguardingInternalNote(Base):
    __tablename__ = "safeguarding_internal_notes"

    id = Column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True)
    public_id = Column(Uuid(as_uuid=True), nullable=False, unique=True, default=uuid.uuid4)
    school_id = Column(Integer, ForeignKey("schools.id", ondelete="RESTRICT"), nullable=False, index=True)
    conversation_id = Column(BigInteger().with_variant(Integer, "sqlite"), ForeignKey("conversations.id", ondelete="RESTRICT"), nullable=False, index=True)
    review_session_id = Column(BigInteger().with_variant(Integer, "sqlite"), ForeignKey("safeguarding_review_sessions.id", ondelete="RESTRICT"), nullable=False)
    author_membership_id = Column(Integer, ForeignKey("memberships.id", ondelete="RESTRICT"), nullable=False)
    body = Column(Text, nullable=False)
    correction_of_note_id = Column(BigInteger().with_variant(Integer, "sqlite"), ForeignKey("safeguarding_internal_notes.id", ondelete="RESTRICT"), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    __table_args__ = (
        CheckConstraint("length(body) BETWEEN 3 AND 10000", name="ck_safeguarding_internal_notes_body"),
        Index("ix_safeguarding_internal_notes_conversation_created", "conversation_id", "created_at", "id"),
    )


class SafeguardingFlag(Base):
    __tablename__ = "safeguarding_flags"

    id = Column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True)
    public_id = Column(Uuid(as_uuid=True), nullable=False, unique=True, default=uuid.uuid4)
    school_id = Column(Integer, ForeignKey("schools.id", ondelete="RESTRICT"), nullable=False, index=True)
    conversation_id = Column(BigInteger().with_variant(Integer, "sqlite"), ForeignKey("conversations.id", ondelete="RESTRICT"), nullable=False, index=True)
    message_id = Column(BigInteger().with_variant(Integer, "sqlite"), ForeignKey("messages.id", ondelete="RESTRICT"), nullable=True, index=True)
    category = Column(String(48), nullable=False)
    severity = Column(String(16), nullable=False)
    status = Column(String(24), nullable=False, default="open", server_default="open")
    internal_note = Column(Text, nullable=True)
    assigned_membership_id = Column(Integer, ForeignKey("memberships.id", ondelete="RESTRICT"), nullable=True)
    created_by_membership_id = Column(Integer, ForeignKey("memberships.id", ondelete="RESTRICT"), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    resolved_by_membership_id = Column(Integer, ForeignKey("memberships.id", ondelete="RESTRICT"), nullable=True)
    resolution_note = Column(Text, nullable=True)

    __table_args__ = (
        CheckConstraint("severity IN ('low', 'medium', 'high', 'critical')", name="ck_safeguarding_flags_severity"),
        CheckConstraint("status IN ('open', 'follow_up', 'resolved')", name="ck_safeguarding_flags_status"),
        CheckConstraint(
            "(status <> 'resolved' AND resolved_at IS NULL AND resolved_by_membership_id IS NULL) OR "
            "(status = 'resolved' AND resolved_at IS NOT NULL AND resolved_by_membership_id IS NOT NULL)",
            name="ck_safeguarding_flags_resolution_shape",
        ),
        Index("ix_safeguarding_flags_school_status", "school_id", "status", "severity", "created_at"),
        Index("ix_safeguarding_flags_conversation_status", "conversation_id", "status", "created_at"),
    )


class MessagingModerationAction(Base):
    __tablename__ = "messaging_moderation_actions"

    id = Column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True)
    event_id = Column(Uuid(as_uuid=True), nullable=False, unique=True, default=uuid.uuid4)
    school_id = Column(Integer, ForeignKey("schools.id", ondelete="RESTRICT"), nullable=False, index=True)
    conversation_id = Column(BigInteger().with_variant(Integer, "sqlite"), ForeignKey("conversations.id", ondelete="RESTRICT"), nullable=False, index=True)
    message_id = Column(BigInteger().with_variant(Integer, "sqlite"), ForeignKey("messages.id", ondelete="RESTRICT"), nullable=True, index=True)
    review_session_id = Column(BigInteger().with_variant(Integer, "sqlite"), ForeignKey("safeguarding_review_sessions.id", ondelete="RESTRICT"), nullable=False)
    actor_membership_id = Column(Integer, ForeignKey("memberships.id", ondelete="RESTRICT"), nullable=False)
    action = Column(String(32), nullable=False)
    restriction_type = Column(String(32), nullable=True)
    reason_category = Column(String(48), nullable=False)
    confidential_reason = Column(Text, nullable=False)
    participant_safe_reason = Column(String(240), nullable=True)
    prior_state_hash = Column(String(64), nullable=False)
    new_state_hash = Column(String(64), nullable=False)
    occurred_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    __table_args__ = (
        CheckConstraint(
            "action IN ('restrict', 'remove_restriction', 'close', 'reopen', "
            "'tombstone', 'restore')",
            name="ck_messaging_moderation_actions_action",
        ),
        CheckConstraint(
            "restriction_type IS NULL OR restriction_type IN "
            "('family_replies', 'staff_replies', 'both_replies', 'read_only')",
            name="ck_messaging_moderation_actions_restriction_type",
        ),
        CheckConstraint("length(confidential_reason) BETWEEN 8 AND 4000", name="ck_messaging_moderation_actions_reason"),
        CheckConstraint("length(prior_state_hash) = 64 AND length(new_state_hash) = 64", name="ck_messaging_moderation_actions_hashes"),
        Index("ix_messaging_moderation_actions_conversation", "conversation_id", "occurred_at", "id"),
    )


class MessagingEvidenceExport(Base):
    __tablename__ = "messaging_evidence_exports"

    id = Column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True)
    public_id = Column(Uuid(as_uuid=True), nullable=False, unique=True, default=uuid.uuid4)
    school_id = Column(Integer, ForeignKey("schools.id", ondelete="RESTRICT"), nullable=False, index=True)
    conversation_id = Column(BigInteger().with_variant(Integer, "sqlite"), ForeignKey("conversations.id", ondelete="RESTRICT"), nullable=False, index=True)
    review_session_id = Column(BigInteger().with_variant(Integer, "sqlite"), ForeignKey("safeguarding_review_sessions.id", ondelete="RESTRICT"), nullable=False)
    created_by_membership_id = Column(Integer, ForeignKey("memberships.id", ondelete="RESTRICT"), nullable=False, index=True)
    export_mode = Column(String(24), nullable=False, default="internal", server_default="internal")
    reason_category = Column(String(48), nullable=False)
    justification = Column(Text, nullable=False)
    include_internal_notes = Column(Boolean, nullable=False, default=False, server_default="false")
    state = Column(String(24), nullable=False, default="requested", server_default="requested")
    artifact_storage_key = Column(String(200), nullable=True)
    artifact_sha256 = Column(String(64), nullable=True)
    manifest_sha256 = Column(String(64), nullable=True)
    size_bytes = Column(BigInteger, nullable=True)
    counts = Column(JSON().with_variant(JSONB, "postgresql"), nullable=False, default=dict)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    max_downloads = Column(Integer, nullable=False, default=3, server_default="3")
    download_count = Column(Integer, nullable=False, default=0, server_default="0")
    last_downloaded_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    generated_at = Column(DateTime(timezone=True), nullable=True)
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    failure_code = Column(String(80), nullable=True)
    verified_at = Column(DateTime(timezone=True), nullable=True)
    verification_state = Column(String(24), nullable=True)
    verification_detail = Column(JSON().with_variant(JSONB, "postgresql"), nullable=False, default=dict)
    custody_version = Column(Integer, nullable=False, default=1, server_default="1")

    __table_args__ = (
        CheckConstraint("export_mode IN ('internal', 'participant_safe')", name="ck_messaging_evidence_exports_mode"),
        CheckConstraint(
            "state IN ('requested', 'generating', 'ready', 'failed', 'expired', 'deleted', 'cancelled')",
            name="ck_messaging_evidence_exports_state",
        ),
        CheckConstraint("length(justification) BETWEEN 8 AND 2000", name="ck_messaging_evidence_exports_reason"),
        CheckConstraint("max_downloads BETWEEN 1 AND 10", name="ck_messaging_evidence_exports_max_downloads"),
        CheckConstraint("download_count >= 0 AND download_count <= max_downloads", name="ck_messaging_evidence_exports_download_count"),
        CheckConstraint(
            "(state = 'ready' AND artifact_storage_key IS NOT NULL AND artifact_sha256 IS NOT NULL "
            "AND manifest_sha256 IS NOT NULL AND size_bytes > 0 AND generated_at IS NOT NULL) OR "
            "state <> 'ready'",
            name="ck_messaging_evidence_exports_ready_shape",
        ),
        CheckConstraint(
            "verification_state IS NULL OR verification_state IN ('verified', 'mismatch', 'missing')",
            name="ck_messaging_evidence_exports_verification_state",
        ),
        CheckConstraint("custody_version >= 1", name="ck_messaging_evidence_exports_custody_version"),
        Index("ix_messaging_evidence_exports_expiry", "state", "expires_at", "id"),
        Index("ix_messaging_evidence_exports_school_created", "school_id", "created_at", "id"),
    )


class DevicePushRegistration(Base):
    __tablename__ = "device_push_registrations"

    id = Column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True)
    installation_id = Column(Uuid(as_uuid=True), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True)
    platform = Column(String(16), nullable=False, default="android", server_default="android")
    app_package = Column(String(100), nullable=False)
    locale = Column(String(8), nullable=False, default="en", server_default="en")
    fcm_token = Column(String(512), nullable=False, unique=True)
    state = Column(String(16), nullable=False, default="active", server_default="active")
    disabled_reason = Column(String(80), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
    last_seen_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    revoked_at = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        UniqueConstraint(
            "app_package",
            "installation_id",
            name="uq_device_push_registrations_package_installation",
        ),
        CheckConstraint("platform = 'android'", name="ck_device_push_registrations_platform"),
        CheckConstraint("locale IN ('en', 'ar')", name="ck_device_push_registrations_locale"),
        CheckConstraint(
            "state IN ('active', 'revoked', 'invalid')",
            name="ck_device_push_registrations_state",
        ),
        Index("ix_device_push_registrations_user_state", "user_id", "state", "id"),
    )


class NotificationOutbox(Base):
    __tablename__ = "notification_outbox"

    id = Column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True)
    event_id = Column(Uuid(as_uuid=True), nullable=False, unique=True, default=uuid.uuid4)
    school_id = Column(Integer, ForeignKey("schools.id", ondelete="RESTRICT"), nullable=False, index=True)
    message_id = Column(
        BigInteger().with_variant(Integer, "sqlite"),
        ForeignKey("messages.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )
    event_category = Column(String(24), nullable=False, default="chat", server_default="chat")
    source_type = Column(String(40), nullable=True)
    source_id = Column(Integer, nullable=True)
    source_action = Column(String(24), nullable=True)
    source_version = Column(Integer, nullable=False, default=1, server_default="1")
    route_type = Column(String(24), nullable=False, default="school_chat", server_default="school_chat")
    route_ref = Column(String(120), nullable=True)
    urgent = Column(Boolean, nullable=False, default=False, server_default="false")
    recipient_kind = Column(String(20), nullable=False)
    recipient_user_id = Column(Integer, ForeignKey("users.id", ondelete="RESTRICT"), nullable=True)
    recipient_fhh_link_id = Column(Integer, ForeignKey("fhh_links.id", ondelete="RESTRICT"), nullable=True)
    recipient_participant_id = Column(
        BigInteger().with_variant(Integer, "sqlite"),
        ForeignKey("conversation_participants.id", ondelete="RESTRICT"),
        nullable=True,
    )
    channel = Column(String(16), nullable=False, default="push", server_default="push")
    template_key = Column(String(96), nullable=False)
    template_args = Column(JSON().with_variant(JSONB, "postgresql"), nullable=False, default=dict)
    deep_link = Column(String(300), nullable=False)
    policy_version = Column(Integer, nullable=False)
    state = Column(String(24), nullable=False)
    eligible_at = Column(DateTime(timezone=True), nullable=False)
    scheduler_check_at = Column(DateTime(timezone=True), nullable=False)
    lease_owner = Column(String(96), nullable=True)
    lease_expires_at = Column(DateTime(timezone=True), nullable=True)
    attempt_count = Column(Integer, nullable=False, default=0, server_default="0")
    next_attempt_at = Column(DateTime(timezone=True), nullable=False)
    provider_message_ref = Column(String(200), nullable=True)
    last_error_code = Column(String(80), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    dispatched_at = Column(DateTime(timezone=True), nullable=True)
    provider_accepted_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    dedupe_key = Column(String(240), nullable=False, unique=True)

    __table_args__ = (
        CheckConstraint(
            "(recipient_kind = 'chh_user' AND recipient_user_id IS NOT NULL "
            "AND recipient_fhh_link_id IS NULL AND recipient_participant_id IS NOT NULL) OR "
            "(recipient_kind = 'fhh_link' AND recipient_user_id IS NULL "
            "AND recipient_fhh_link_id IS NOT NULL AND recipient_participant_id IS NULL)",
            name="ck_notification_outbox_recipient_shape",
        ),
        CheckConstraint("channel IN ('push', 'email', 'in_app_event')", name="ck_notification_outbox_channel"),
        CheckConstraint(
            "event_category IN ('chat', 'homework', 'notice', 'points', 'calendar', 'update')",
            name="ck_notification_outbox_category",
        ),
        CheckConstraint(
            "route_type IN ('school_chat', 'homework', 'notice', 'points', 'calendar', 'update')",
            name="ck_notification_outbox_route_type",
        ),
        CheckConstraint("source_version >= 1", name="ck_notification_outbox_source_version"),
        CheckConstraint(
            "(event_category = 'chat' AND message_id IS NOT NULL AND source_type IS NULL "
            "AND source_id IS NULL AND source_action IS NULL) OR "
            "(event_category <> 'chat' AND message_id IS NULL AND recipient_kind = 'fhh_link' "
            "AND source_type IS NOT NULL AND source_id IS NOT NULL AND source_action IS NOT NULL "
            "AND route_ref IS NOT NULL)",
            name="ck_notification_outbox_source_shape",
        ),
        CheckConstraint(
            "state IN ('held', 'pending', 'leased', 'dispatched', 'provider_accepted', "
            "'failed', 'dead', 'cancelled')",
            name="ck_notification_outbox_state",
        ),
        CheckConstraint("policy_version >= 1", name="ck_notification_outbox_policy_version"),
        CheckConstraint("attempt_count >= 0", name="ck_notification_outbox_attempt_count"),
        CheckConstraint(
            "(state = 'leased' AND lease_owner IS NOT NULL AND lease_expires_at IS NOT NULL) OR "
            "(state <> 'leased' AND lease_owner IS NULL AND lease_expires_at IS NULL)",
            name="ck_notification_outbox_lease_shape",
        ),
        Index(
            "ix_notification_outbox_scheduler",
            "state",
            "scheduler_check_at",
            "lease_expires_at",
            "id",
        ),
        Index(
            "ix_notification_outbox_dispatch",
            "state",
            "next_attempt_at",
            "eligible_at",
            "id",
        ),
        Index("ix_notification_outbox_school_state", "school_id", "state", "id"),
        Index("ix_notification_outbox_school_category_state", "school_id", "event_category", "state", "id"),
        Index("ix_notification_outbox_source", "school_id", "source_type", "source_id", "source_version"),
        Index("ix_notification_outbox_fhh_link_created", "recipient_fhh_link_id", "created_at"),
    )


class NotificationDelivery(Base):
    __tablename__ = "notification_deliveries"

    id = Column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True)
    outbox_id = Column(
        BigInteger().with_variant(Integer, "sqlite"),
        ForeignKey("notification_outbox.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    device_registration_id = Column(
        BigInteger().with_variant(Integer, "sqlite"),
        ForeignKey("device_push_registrations.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    state = Column(String(24), nullable=False, default="pending", server_default="pending")
    attempt_count = Column(Integer, nullable=False, default=0, server_default="0")
    next_attempt_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    lease_owner = Column(String(96), nullable=True)
    lease_expires_at = Column(DateTime(timezone=True), nullable=True)
    provider_message_ref = Column(String(200), nullable=True)
    last_error_code = Column(String(80), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    dispatched_at = Column(DateTime(timezone=True), nullable=True)
    provider_accepted_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        UniqueConstraint(
            "outbox_id",
            "device_registration_id",
            name="uq_notification_deliveries_outbox_device",
        ),
        CheckConstraint(
            "state IN ('pending', 'leased', 'provider_accepted', 'failed', 'dead', 'cancelled')",
            name="ck_notification_deliveries_state",
        ),
        CheckConstraint("attempt_count >= 0", name="ck_notification_deliveries_attempt_count"),
        CheckConstraint(
            "(state = 'leased' AND lease_owner IS NOT NULL AND lease_expires_at IS NOT NULL) OR "
            "(state <> 'leased' AND lease_owner IS NULL AND lease_expires_at IS NULL)",
            name="ck_notification_deliveries_lease_shape",
        ),
        Index(
            "ix_notification_deliveries_dispatch",
            "state",
            "next_attempt_at",
            "lease_expires_at",
            "id",
        ),
    )


@event.listens_for(Message, "before_update", propagate=True)
def _prevent_message_immutable_update(mapper, connection, target):
    state = sa_inspect(target)
    immutable_fields = (
        "public_id",
        "school_id",
        "conversation_id",
        "sequence",
        "sender_participant_id",
        "sender_display_name_snapshot",
        "client_message_id",
        "body",
        "urgent",
        "created_at",
    )
    changed = {field for field in immutable_fields if state.attrs[field].history.has_changes()}
    retention_disposal = bool(
        changed == {"body"}
        and target.body is None
        and target.retention_disposed_at is not None
        and target.retention_policy_version is not None
        and target.retention_content_sha256 is not None
    )
    if changed and not retention_disposal:
        raise ValueError("Message attribution and content are immutable")


@event.listens_for(MessageReceiptEvent, "before_update", propagate=True)
@event.listens_for(MessagingAuditEvent, "before_update", propagate=True)
@event.listens_for(SafeguardingInternalNote, "before_update", propagate=True)
@event.listens_for(MessagingModerationAction, "before_update", propagate=True)
@event.listens_for(SchoolSystemOwnerEvent, "before_update", propagate=True)
@event.listens_for(MessagingLegalHoldEvent, "before_update", propagate=True)
@event.listens_for(MessagingOperatorAction, "before_update", propagate=True)
def _prevent_messaging_append_only_update(mapper, connection, target):
    raise ValueError("Messaging evidence rows are append-only")


@event.listens_for(MessageReceiptEvent, "before_delete", propagate=True)
@event.listens_for(MessagingAuditEvent, "before_delete", propagate=True)
@event.listens_for(SafeguardingInternalNote, "before_delete", propagate=True)
@event.listens_for(MessagingModerationAction, "before_delete", propagate=True)
@event.listens_for(SchoolSystemOwnerEvent, "before_delete", propagate=True)
@event.listens_for(MessagingLegalHoldEvent, "before_delete", propagate=True)
@event.listens_for(MessagingOperatorAction, "before_delete", propagate=True)
@event.listens_for(Message, "before_delete", propagate=True)
def _prevent_messaging_append_only_delete(mapper, connection, target):
    raise ValueError("Messaging evidence rows are append-only")


class BehaviourCategory(Base):
    __tablename__ = "behaviour_categories"

    id = Column(Integer, primary_key=True, index=True)
    school_id = Column(Integer, ForeignKey("schools.id"), nullable=False, index=True)
    type = Column(String, nullable=False)
    label = Column(String, nullable=False)
    points_value = Column(Integer, nullable=False)
    sort_order = Column(Integer, nullable=False, default=0)
    active = Column(Boolean, nullable=False, default=True, server_default="true")
    is_quick_action = Column(Boolean, nullable=False, default=False, server_default="false")
    quick_action_order = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        CheckConstraint("type IN ('positive', 'needs_work')", name="ck_behaviour_categories_type"),
        CheckConstraint(
            "(type = 'positive' AND points_value > 0) OR (type = 'needs_work' AND points_value < 0)",
            name="ck_behaviour_categories_value_sign",
        ),
        CheckConstraint(
            "NOT is_quick_action OR quick_action_order IS NOT NULL",
            name="ck_behaviour_categories_quick_action_order",
        ),
        UniqueConstraint("school_id", "type", "label", name="uq_behaviour_categories_school_type_label"),
        Index("ix_behaviour_categories_school_active_sort", "school_id", "active", "type", "sort_order"),
        Index("ix_behaviour_categories_school_quick_actions", "school_id", "active", "is_quick_action", "type", "quick_action_order", "sort_order"),
    )


class BehaviourEvent(Base):
    __tablename__ = "behaviour_events"

    id = Column(Integer, primary_key=True, index=True)
    school_id = Column(Integer, ForeignKey("schools.id"), nullable=False, index=True)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False, index=True)
    category_id = Column(Integer, ForeignKey("behaviour_categories.id"), nullable=False, index=True)
    actor_user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    class_section_id = Column(Integer, ForeignKey("class_sections.id"), nullable=True, index=True)
    subject_group_id = Column(Integer, ForeignKey("subject_groups.id"), nullable=True, index=True)
    points_delta = Column(Integer, nullable=False)
    note = Column(Text, nullable=True)
    source = Column(String, nullable=False, default="teacher", server_default="teacher")
    context_type = Column(String, nullable=False, default="general", server_default="general")
    duty_context = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    reversed_at = Column(DateTime(timezone=True), nullable=True)
    reversed_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    reversal_reason = Column(String, nullable=True)

    __table_args__ = (
        CheckConstraint("source IN ('teacher', 'admin', 'correction')", name="ck_behaviour_events_source"),
        CheckConstraint("context_type IN ('class', 'subject', 'duty', 'general')", name="ck_behaviour_events_context_type"),
        CheckConstraint(
            "duty_context IS NULL OR duty_context IN ('break', 'lunch', 'playground', 'hallway', 'assembly', 'bus', 'general_duty')",
            name="ck_behaviour_events_duty_context",
        ),
        CheckConstraint(
            "(context_type = 'subject' AND subject_group_id IS NOT NULL AND class_section_id IS NULL AND duty_context IS NULL) OR "
            "(context_type = 'class' AND class_section_id IS NOT NULL AND subject_group_id IS NULL AND duty_context IS NULL) OR "
            "(context_type = 'duty' AND duty_context IS NOT NULL AND class_section_id IS NULL AND subject_group_id IS NULL) OR "
            "(context_type = 'general' AND class_section_id IS NULL AND subject_group_id IS NULL AND duty_context IS NULL)",
            name="ck_behaviour_events_context_combination",
        ),
        Index("ix_behaviour_events_school_student_created", "school_id", "student_id", "created_at"),
        Index("ix_behaviour_events_school_context_created", "school_id", "context_type", "duty_context", "created_at"),
        Index("ix_behaviour_events_school_created", "school_id", "created_at"),
        Index("ix_behaviour_events_school_class_created", "school_id", "class_section_id", "created_at"),
        Index("ix_behaviour_events_school_subject_group_created", "school_id", "subject_group_id", "created_at"),
        Index("ix_behaviour_events_school_actor_created", "school_id", "actor_user_id", "created_at"),
        Index("ix_behaviour_events_school_category_created", "school_id", "category_id", "created_at"),
    )


class Announcement(Base):
    __tablename__ = "announcements"

    id = Column(Integer, primary_key=True, index=True)
    school_id = Column(Integer, ForeignKey("schools.id"), nullable=False, index=True)
    author_user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    title = Column(String, nullable=False)
    body = Column(Text, nullable=False)
    audience_type = Column(String, nullable=False)
    class_section_id = Column(Integer, ForeignKey("class_sections.id"), nullable=True, index=True)
    subject_group_id = Column(Integer, ForeignKey("subject_groups.id"), nullable=True, index=True)
    status = Column(String, nullable=False, default="published", server_default="published")
    urgent = Column(Boolean, nullable=False, default=False, server_default="false")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        CheckConstraint("audience_type IN ('school', 'class_section', 'subject_group')", name="ck_announcements_audience_type"),
        CheckConstraint("status IN ('published', 'archived')", name="ck_announcements_status"),
        CheckConstraint(
            "(audience_type = 'school' AND class_section_id IS NULL AND subject_group_id IS NULL) OR "
            "(audience_type = 'class_section' AND class_section_id IS NOT NULL AND subject_group_id IS NULL) OR "
            "(audience_type = 'subject_group' AND class_section_id IS NULL AND subject_group_id IS NOT NULL)",
            name="ck_announcements_audience_target",
        ),
        Index("ix_announcements_school_status_created", "school_id", "status", "created_at"),
    )


class AnnouncementAttachment(Base):
    __tablename__ = "announcement_attachments"

    id = Column(Integer, primary_key=True, index=True)
    post_id = Column(Integer, ForeignKey("announcements.id"), nullable=False, index=True)
    school_id = Column(Integer, ForeignKey("schools.id"), nullable=False, index=True)
    uploaded_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    original_filename = Column(String, nullable=False)
    storage_key = Column(String, nullable=False, unique=True, index=True)
    content_type = Column(String, nullable=False)
    size_bytes = Column(Integer, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("ix_announcement_attachments_post_school", "post_id", "school_id"),
    )


class AnnouncementRead(Base):
    __tablename__ = "announcement_reads"

    id = Column(Integer, primary_key=True, index=True)
    announcement_id = Column(Integer, ForeignKey("announcements.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    school_id = Column(Integer, ForeignKey("schools.id"), nullable=False, index=True)
    read_at = Column(DateTime(timezone=True), server_default=func.now())
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        UniqueConstraint("announcement_id", "user_id", name="uq_announcement_reads_announcement_user"),
        Index("ix_announcement_reads_user_announcement", "user_id", "announcement_id"),
    )


class HomeworkItem(Base):
    __tablename__ = "homework_items"

    id = Column(Integer, primary_key=True, index=True)
    school_id = Column(Integer, ForeignKey("schools.id"), nullable=False, index=True)
    author_user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    item_type = Column(String, nullable=False)
    title = Column(String, nullable=False)
    body = Column(Text, nullable=False)
    audience_type = Column(String, nullable=False)
    class_section_id = Column(Integer, ForeignKey("class_sections.id"), nullable=True, index=True)
    subject_group_id = Column(Integer, ForeignKey("subject_groups.id"), nullable=True, index=True)
    due_at = Column(DateTime(timezone=True), nullable=True)
    status = Column(String, nullable=False, default="active", server_default="active")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    archived_at = Column(DateTime(timezone=True), nullable=True)
    resource_links = Column(JSON, nullable=False, default=list, server_default="[]")

    __table_args__ = (
        CheckConstraint("item_type IN ('homework', 'diary')", name="ck_homework_items_type"),
        CheckConstraint("status IN ('active', 'archived')", name="ck_homework_items_status"),
        CheckConstraint(
            "(audience_type = 'class_section' AND class_section_id IS NOT NULL AND subject_group_id IS NULL) OR "
            "(audience_type = 'subject_group' AND class_section_id IS NULL AND subject_group_id IS NOT NULL)",
            name="ck_homework_items_exactly_one_audience",
        ),
        Index("ix_homework_items_school_status_created", "school_id", "status", "created_at"),
    )


class HomeworkAttachment(Base):
    __tablename__ = "homework_attachments"

    id = Column(Integer, primary_key=True, index=True)
    homework_item_id = Column(Integer, ForeignKey("homework_items.id"), nullable=False, index=True)
    school_id = Column(Integer, ForeignKey("schools.id"), nullable=False, index=True)
    uploaded_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    original_filename = Column(String, nullable=False)
    storage_key = Column(String, nullable=False, unique=True, index=True)
    content_type = Column(String, nullable=False)
    size_bytes = Column(Integer, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (Index("ix_homework_attachments_item_school", "homework_item_id", "school_id"),)


class HomeworkItemCompletion(Base):
    __tablename__ = "homework_item_completions"

    id = Column(Integer, primary_key=True, index=True)
    homework_item_id = Column(Integer, ForeignKey("homework_items.id"), nullable=False, index=True)
    school_id = Column(Integer, ForeignKey("schools.id"), nullable=False, index=True)
    guardian_user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        UniqueConstraint("homework_item_id", "guardian_user_id", name="uq_homework_completion_item_guardian"),
        Index("ix_homework_completions_guardian_item", "guardian_user_id", "homework_item_id"),
    )


class CalendarEvent(Base):
    __tablename__ = "calendar_events"

    id = Column(Integer, primary_key=True, index=True)
    school_id = Column(Integer, ForeignKey("schools.id"), nullable=False, index=True)
    author_user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    title = Column(String, nullable=False)
    body = Column(Text, nullable=True)
    event_type = Column(String, nullable=False)
    audience_type = Column(String, nullable=False)
    class_section_id = Column(Integer, ForeignKey("class_sections.id"), nullable=True, index=True)
    subject_group_id = Column(Integer, ForeignKey("subject_groups.id"), nullable=True, index=True)
    starts_at = Column(DateTime(timezone=True), nullable=False)
    ends_at = Column(DateTime(timezone=True), nullable=True)
    all_day = Column(Boolean, nullable=False, default=False, server_default="false")
    status = Column(String, nullable=False, default="active", server_default="active")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    archived_at = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        CheckConstraint("event_type IN ('event', 'test', 'reminder', 'trip', 'civvies', 'charity')", name="ck_calendar_events_type"),
        CheckConstraint("status IN ('active', 'archived')", name="ck_calendar_events_status"),
        CheckConstraint(
            "(audience_type = 'school' AND class_section_id IS NULL AND subject_group_id IS NULL) OR "
            "(audience_type = 'class_section' AND class_section_id IS NOT NULL AND subject_group_id IS NULL) OR "
            "(audience_type = 'subject_group' AND class_section_id IS NULL AND subject_group_id IS NOT NULL)",
            name="ck_calendar_events_audience_target",
        ),
        Index("ix_calendar_events_school_status_starts", "school_id", "status", "starts_at"),
    )


class UpdatePost(Base):
    __tablename__ = "update_posts"

    id = Column(Integer, primary_key=True, index=True)
    school_id = Column(Integer, ForeignKey("schools.id"), nullable=False, index=True)
    author_user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    body = Column(Text, nullable=False)
    audience_type = Column(String, nullable=False)
    class_section_id = Column(Integer, ForeignKey("class_sections.id"), nullable=True, index=True)
    subject_group_id = Column(Integer, ForeignKey("subject_groups.id"), nullable=True, index=True)
    status = Column(String, nullable=False, default="active", server_default="active")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    archived_at = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        CheckConstraint("status IN ('active', 'archived')", name="ck_update_posts_status"),
        CheckConstraint(
            "(audience_type = 'class_section' AND class_section_id IS NOT NULL AND subject_group_id IS NULL) OR "
            "(audience_type = 'subject_group' AND class_section_id IS NULL AND subject_group_id IS NOT NULL)",
            name="ck_update_posts_exactly_one_audience",
        ),
        Index("ix_update_posts_school_status_created", "school_id", "status", "created_at"),
    )


class UpdatePhoto(Base):
    __tablename__ = "update_photos"

    id = Column(Integer, primary_key=True, index=True)
    post_id = Column(Integer, ForeignKey("update_posts.id"), nullable=False, index=True)
    school_id = Column(Integer, ForeignKey("schools.id"), nullable=False, index=True)
    uploaded_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    original_filename = Column(String, nullable=False)
    storage_key = Column(String, nullable=False, unique=True, index=True)
    content_type = Column(String, nullable=False)
    size_bytes = Column(Integer, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (Index("ix_update_photos_post_school", "post_id", "school_id"),)


def _default_magic_login_expires_at():
    return datetime.now(timezone.utc) + timedelta(minutes=15)


class MagicLoginToken(Base):
    __tablename__ = "magic_login_tokens"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, index=True, nullable=False)
    token_hash = Column(String, unique=True, index=True, nullable=False)
    return_to = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    expires_at = Column(DateTime(timezone=True), default=_default_magic_login_expires_at)
    used_at = Column(DateTime(timezone=True), nullable=True)
    requested_ip = Column(String, nullable=True)


class PlatformAdmin(Base):
    __tablename__ = "platform_admins"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True)
    granted_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    granted_at = Column(DateTime(timezone=True), server_default=func.now())
    revoked_at = Column(DateTime(timezone=True), nullable=True)


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    school_id = Column(Integer, ForeignKey("schools.id"), nullable=True)
    actor_user_id = Column(Integer, ForeignKey("users.id"))
    action = Column(String)
    entity_type = Column(String)
    entity_id = Column(Integer, nullable=True)
    detail = Column(JSON)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


@event.listens_for(AuditLog, "before_update", propagate=True)
def _prevent_audit_log_update(mapper, connection, target):
    raise ValueError("AuditLog rows are append-only")
