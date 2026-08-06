"""Canonical school staff roles and the intentionally narrow scopes they imply."""

SCHOOL_ADMIN = "school_admin"
PRINCIPAL = "principal"
DEPUTY_PRINCIPAL = "deputy_principal"
HEAD_OF_DEPARTMENT = "head_of_department"
TEACHER = "teacher"
SUPPORT_STAFF = "support_staff"

STAFF_ROLES = (
    SCHOOL_ADMIN,
    PRINCIPAL,
    DEPUTY_PRINCIPAL,
    HEAD_OF_DEPARTMENT,
    TEACHER,
    SUPPORT_STAFF,
)

# These roles receive school-wide management visibility, but only on endpoints
# that explicitly opt in. They do not inherit school setup or platform access.
SCHOOL_WIDE_MANAGEMENT_ROLES = (SCHOOL_ADMIN, PRINCIPAL, DEPUTY_PRINCIPAL)
REPORTING_ROLES = (*SCHOOL_WIDE_MANAGEMENT_ROLES, HEAD_OF_DEPARTMENT)
COMMUNICATION_OVERSIGHT_ROLES = REPORTING_ROLES
# School administrators retain the existing explicit safeguarding permission
# grant workflow; principal/deputy authority is role-derived and school-wide.
ROLE_DERIVED_OVERSIGHT_ROLES = (PRINCIPAL, DEPUTY_PRINCIPAL)
