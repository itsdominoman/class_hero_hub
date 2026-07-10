from datetime import datetime, timedelta, timezone

from sqlalchemy import Boolean, CheckConstraint, Column, Date, DateTime, ForeignKey, Index, Integer, JSON, String, Text, UniqueConstraint, event
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
