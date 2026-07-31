"""normalise guardian contacts for MIS Slice 2

Revision ID: c5d6e7f8a9b0
Revises: b4c5d6e7f8a9
Create Date: 2026-07-31
"""

from alembic import op
import sqlalchemy as sa


revision = "c5d6e7f8a9b0"
down_revision = "b4c5d6e7f8a9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("student_guardian_contacts", sa.Column("external_ref", sa.String(), nullable=True))
    op.add_column("student_guardian_contacts", sa.Column("phone", sa.String(), nullable=True))
    op.add_column("student_guardian_contacts", sa.Column("phone_normalized", sa.String(), nullable=True))
    op.add_column(
        "student_guardian_contacts",
        sa.Column("is_primary", sa.Boolean(), server_default=sa.text("false"), nullable=False),
    )
    op.add_column(
        "student_guardian_contacts",
        sa.Column("is_emergency", sa.Boolean(), server_default=sa.text("false"), nullable=False),
    )
    op.add_column(
        "student_guardian_contacts",
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
    )
    op.add_column(
        "student_guardian_contacts",
        sa.Column("source", sa.String(), server_default="manual", nullable=False),
    )
    op.add_column(
        "student_guardian_contacts",
        sa.Column("created_by_user_id", sa.Integer(), nullable=True),
    )
    op.create_foreign_key(
        "fk_student_guardian_contacts_created_by_user_id",
        "student_guardian_contacts",
        "users",
        ["created_by_user_id"],
        ["id"],
    )
    op.execute(
        "UPDATE student_guardian_contacts "
        "SET source = CASE WHEN source_import_id IS NULL THEN 'manual' ELSE 'import' END"
    )
    op.alter_column("student_guardian_contacts", "slot", existing_type=sa.Integer(), nullable=True)
    op.drop_constraint("ck_student_guardian_contacts_slot", "student_guardian_contacts", type_="check")
    op.create_check_constraint(
        "ck_student_guardian_contacts_slot",
        "student_guardian_contacts",
        "slot IS NULL OR slot IN (1, 2)",
    )
    op.create_check_constraint(
        "ck_student_guardian_contacts_source",
        "student_guardian_contacts",
        "source IN ('import', 'manual')",
    )
    op.create_index(
        "uq_guardian_contacts_student_external_ref_norm",
        "student_guardian_contacts",
        ["school_id", "student_id", sa.text("lower(btrim(external_ref))")],
        unique=True,
        postgresql_where=sa.text("external_ref IS NOT NULL AND length(btrim(external_ref)) > 0"),
    )


def downgrade() -> None:
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM student_guardian_contacts WHERE slot IS NULL) THEN
                RAISE EXCEPTION 'Cannot downgrade while non-slot guardian contacts exist';
            END IF;
        END
        $$;
        """
    )
    op.drop_index(
        "uq_guardian_contacts_student_external_ref_norm",
        table_name="student_guardian_contacts",
    )
    op.drop_constraint("ck_student_guardian_contacts_source", "student_guardian_contacts", type_="check")
    op.drop_constraint("ck_student_guardian_contacts_slot", "student_guardian_contacts", type_="check")
    op.create_check_constraint(
        "ck_student_guardian_contacts_slot",
        "student_guardian_contacts",
        "slot IN (1, 2)",
    )
    op.alter_column("student_guardian_contacts", "slot", existing_type=sa.Integer(), nullable=False)
    op.drop_constraint(
        "fk_student_guardian_contacts_created_by_user_id",
        "student_guardian_contacts",
        type_="foreignkey",
    )
    op.drop_column("student_guardian_contacts", "created_by_user_id")
    op.drop_column("student_guardian_contacts", "source")
    op.drop_column("student_guardian_contacts", "is_active")
    op.drop_column("student_guardian_contacts", "is_emergency")
    op.drop_column("student_guardian_contacts", "is_primary")
    op.drop_column("student_guardian_contacts", "phone_normalized")
    op.drop_column("student_guardian_contacts", "phone")
    op.drop_column("student_guardian_contacts", "external_ref")
