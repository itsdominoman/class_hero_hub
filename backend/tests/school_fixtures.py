import pytest

from app.models_school import Membership, PlatformAdmin, School, User


def _create_user(db, email: str, name: str) -> User:
    user = User(email=email, name=name, google_sub=f"sub-{email}")
    db.add(user)
    db.flush()
    return user


@pytest.fixture
def seeded_schools(db):
    platform_user = _create_user(db, "platform-admin@example.com", "Platform Admin")

    alpha = School(name="Alpha Academy", slug="alpha-academy")
    beta = School(name="Beta School", slug="beta-school")
    db.add_all([alpha, beta])
    db.flush()

    alpha_admin = _create_user(db, "alpha-admin@example.com", "Alpha Admin")
    alpha_teacher = _create_user(db, "alpha-teacher@example.com", "Alpha Teacher")
    beta_admin = _create_user(db, "beta-admin@example.com", "Beta Admin")
    beta_teacher = _create_user(db, "beta-teacher@example.com", "Beta Teacher")

    db.add_all(
        [
            Membership(
                school_id=alpha.id,
                user_id=alpha_admin.id,
                role="school_admin",
                created_by_user_id=platform_user.id,
            ),
            Membership(
                school_id=alpha.id,
                user_id=alpha_teacher.id,
                role="teacher",
                created_by_user_id=alpha_admin.id,
            ),
            Membership(
                school_id=beta.id,
                user_id=beta_admin.id,
                role="school_admin",
                created_by_user_id=platform_user.id,
            ),
            Membership(
                school_id=beta.id,
                user_id=beta_teacher.id,
                role="teacher",
                created_by_user_id=beta_admin.id,
            ),
            PlatformAdmin(user_id=platform_user.id, granted_by_user_id=None),
        ]
    )
    db.commit()

    return {
        "platform_user": platform_user,
        "schools": {"alpha": alpha, "beta": beta},
        "users": {
            "alpha_admin": alpha_admin,
            "alpha_teacher": alpha_teacher,
            "beta_admin": beta_admin,
            "beta_teacher": beta_teacher,
        },
    }
