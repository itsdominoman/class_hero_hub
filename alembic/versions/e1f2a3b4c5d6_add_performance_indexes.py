"""Add composite indexes for hot list/roster query patterns

Revision ID: e1f2a3b4c5d6
Revises: d0e1f2a3b4c5
Create Date: 2026-07-09 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op


revision: str = "e1f2a3b4c5d6"
down_revision: Union[str, Sequence[str], None] = "d0e1f2a3b4c5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index("ix_memberships_school_role_status", "memberships", ["school_id", "role", "status"])
    op.create_index("ix_subject_groups_school_status", "subject_groups", ["school_id", "status"])
    op.create_index("ix_staff_assignments_school_membership", "staff_assignments", ["school_id", "membership_id"])
    op.create_index("ix_students_school_status", "students", ["school_id", "status"])
    op.create_index("ix_enrolments_school_section_kind", "enrolments", ["school_id", "class_section_id", "kind"])
    op.create_index("ix_enrolments_school_group_kind", "enrolments", ["school_id", "subject_group_id", "kind"])


def downgrade() -> None:
    op.drop_index("ix_enrolments_school_group_kind", table_name="enrolments")
    op.drop_index("ix_enrolments_school_section_kind", table_name="enrolments")
    op.drop_index("ix_students_school_status", table_name="students")
    op.drop_index("ix_staff_assignments_school_membership", table_name="staff_assignments")
    op.drop_index("ix_subject_groups_school_status", table_name="subject_groups")
    op.drop_index("ix_memberships_school_role_status", table_name="memberships")
