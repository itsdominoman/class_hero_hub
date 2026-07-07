import os

os.environ["DATABASE_URL"] = "sqlite://"
os.environ["APP_ENV"] = "test"
os.environ["DEV_AUTH_ENABLED"] = "false"

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app import auth, database
from app.database import Base, get_db
from app.main import app
from app.models_school import BranchCampus, ClassSection, Membership, PlatformAdmin, School, Subject, User
from school_fixtures import seeded_schools  # noqa: F401


engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
database.engine = engine
database.SessionLocal = TestingSessionLocal


@pytest.fixture
def db():
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client():
    def override_get_db():
        session = TestingSessionLocal()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_get_db
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()


def bearer(email: str, school_id: int | None = None) -> dict[str, str]:
    headers = {"Authorization": f"Bearer {auth.create_access_token({'sub': email})}"}
    if school_id is not None:
        headers["X-School-Id"] = str(school_id)
    return headers


def _base(code: str, name: str | None = None) -> dict:
    return {
        "code": code,
        "name": name or code,
        "name_ar": None,
        "sort_order": 0,
        "status": "active",
    }


def _post(client, path: str, email: str, school_id: int, payload: dict):
    return client.post(path, headers=bearer(email, school_id), json=payload)


def create_structure(client, admin_email: str, school_id: int) -> dict:
    branch = _post(client, "/api/school/branches", admin_email, school_id, _base("NORTH", "North Campus")).json()
    stage = _post(client, "/api/school/education-stages", admin_email, school_id, _base("PRIMARY", "Primary")).json()
    year = _post(client, "/api/school/academic-years", admin_email, school_id, _base("2026-27", "2026/27")).json()
    level_payload = {**_base("Y1", "Year 1"), "education_stage_id": stage["id"]}
    level = _post(client, "/api/school/grade-levels", admin_email, school_id, level_payload).json()
    section_payload = {
        **_base("RED", "Year 1 Red"),
        "branch_campus_id": branch["id"],
        "academic_year_id": year["id"],
        "grade_level_id": level["id"],
    }
    section = _post(client, "/api/school/class-sections", admin_email, school_id, section_payload).json()
    subject = _post(client, "/api/school/subjects", admin_email, school_id, _base("ENG", "English")).json()
    group_payload = {
        **_base("Y1RED-ENG", "Year 1 Red English"),
        "academic_year_id": year["id"],
        "class_section_id": section["id"],
        "subject_id": subject["id"],
    }
    group = _post(client, "/api/school/subject-groups", admin_email, school_id, group_payload).json()
    return {
        "branch": branch,
        "stage": stage,
        "year": year,
        "level": level,
        "section": section,
        "subject": subject,
        "group": group,
    }


def test_school_settings_checklist_and_full_structure_crud(db, client, seeded_schools):
    alpha = seeded_schools["schools"]["alpha"]
    admin = seeded_schools["users"]["alpha_admin"]

    settings_response = client.put(
        "/api/school/settings",
        headers=bearer(admin.email, alpha.id),
        json={"grade_level_label": "Year"},
    )
    assert settings_response.status_code == 200
    assert settings_response.json()["grade_level_label"] == "Year"

    created = create_structure(client, admin.email, alpha.id)
    assert created["section"]["branch_campus_id"] == created["branch"]["id"]
    assert created["level"]["education_stage_id"] == created["stage"]["id"]
    assert created["group"]["subject_id"] == created["subject"]["id"]

    update_response = client.put(
        f"/api/school/branches/{created['branch']['id']}",
        headers=bearer(admin.email, alpha.id),
        json={**_base("NORTH", "North Campus Updated"), "name_ar": "فرع الشمال", "sort_order": 2},
    )
    assert update_response.status_code == 200
    assert update_response.json()["name"] == "North Campus Updated"
    assert update_response.json()["name_ar"] == "فرع الشمال"

    archive_response = client.delete(
        f"/api/school/branches/{created['branch']['id']}",
        headers=bearer(admin.email, alpha.id),
    )
    assert archive_response.status_code == 204
    assert db.query(BranchCampus).filter_by(id=created["branch"]["id"]).one().status == "archived"

    checklist_response = client.get("/api/school/setup-checklist", headers=bearer(admin.email, alpha.id))
    assert checklist_response.status_code == 200
    checklist = checklist_response.json()
    assert checklist["counts"]["class_sections"] == 1
    assert checklist["complete"] is True


def test_default_main_branch_and_one_branch_class_section_flow(db, client, seeded_schools):
    alpha = seeded_schools["schools"]["alpha"]
    admin = seeded_schools["users"]["alpha_admin"]

    branches_response = client.get("/api/school/branches", headers=bearer(admin.email, alpha.id))
    assert branches_response.status_code == 200
    assert branches_response.json()[0]["code"] == "MAIN"

    year = _post(client, "/api/school/academic-years", admin.email, alpha.id, _base("2026", "2026")).json()
    level = _post(client, "/api/school/grade-levels", admin.email, alpha.id, {**_base("FS1", "FS1"), "education_stage_id": None}).json()
    section_response = _post(
        client,
        "/api/school/class-sections",
        admin.email,
        alpha.id,
        {**_base("A", "FS1 A"), "academic_year_id": year["id"], "grade_level_id": level["id"]},
    )

    assert section_response.status_code == 201
    main_branch = db.query(BranchCampus).filter_by(school_id=alpha.id, code="MAIN").one()
    assert section_response.json()["branch_campus_id"] == main_branch.id


@pytest.mark.parametrize(
    ("path", "payload"),
    [
        ("/api/school/branches", _base("DUP", "Duplicate")),
        ("/api/school/education-stages", _base("DUP", "Duplicate")),
        ("/api/school/academic-years", _base("DUP", "Duplicate")),
        ("/api/school/grade-levels", {**_base("DUP", "Duplicate"), "education_stage_id": None}),
        ("/api/school/subjects", _base("DUP", "Duplicate")),
    ],
)
def test_duplicate_structure_records_return_conflict(db, client, seeded_schools, path, payload):
    alpha = seeded_schools["schools"]["alpha"]
    admin = seeded_schools["users"]["alpha_admin"]

    first = _post(client, path, admin.email, alpha.id, payload)
    second = _post(client, path, admin.email, alpha.id, payload)

    assert first.status_code == 201
    assert second.status_code == 409


def test_duplicate_sections_and_subject_groups_return_conflict(db, client, seeded_schools):
    alpha = seeded_schools["schools"]["alpha"]
    admin = seeded_schools["users"]["alpha_admin"]
    created = create_structure(client, admin.email, alpha.id)

    section_payload = {
        **_base("RED", "Year 1 Red Again"),
        "branch_campus_id": created["branch"]["id"],
        "academic_year_id": created["year"]["id"],
        "grade_level_id": created["level"]["id"],
    }
    group_payload = {
        **_base("Y1RED-ENG", "Duplicate Group"),
        "academic_year_id": created["year"]["id"],
        "class_section_id": created["section"]["id"],
        "subject_id": created["subject"]["id"],
    }

    assert _post(client, "/api/school/class-sections", admin.email, alpha.id, section_payload).status_code == 409
    assert _post(client, "/api/school/subject-groups", admin.email, alpha.id, group_payload).status_code == 409


@pytest.mark.parametrize(
    "method,path,payload",
    [
        ("get", "/api/school/settings", None),
        ("put", "/api/school/settings", {"grade_level_label": "Form"}),
        ("get", "/api/school/setup-checklist", None),
        ("get", "/api/school/branches", None),
        ("post", "/api/school/branches", _base("X")),
        ("get", "/api/school/education-stages", None),
        ("post", "/api/school/education-stages", _base("X")),
        ("get", "/api/school/academic-years", None),
        ("post", "/api/school/academic-years", _base("X")),
        ("get", "/api/school/grade-levels", None),
        ("post", "/api/school/grade-levels", {**_base("X"), "education_stage_id": None}),
        ("get", "/api/school/class-sections", None),
        ("get", "/api/school/subjects", None),
        ("post", "/api/school/subjects", _base("X")),
        ("get", "/api/school/subject-groups", None),
    ],
)
def test_school_setup_routes_reject_wrong_roles_and_platform_only_users(db, client, seeded_schools, method, path, payload):
    alpha = seeded_schools["schools"]["alpha"]
    teacher = seeded_schools["users"]["alpha_teacher"]
    platform_user = seeded_schools["platform_user"]

    kwargs = {"headers": bearer(teacher.email, alpha.id)}
    if payload is not None:
        kwargs["json"] = payload
    assert getattr(client, method)(path, **kwargs).status_code == 403

    kwargs = {"headers": bearer(platform_user.email, alpha.id)}
    if payload is not None:
        kwargs["json"] = payload
    assert getattr(client, method)(path, **kwargs).status_code == 403


def test_cross_school_structure_references_and_mutations_are_rejected(db, client, seeded_schools):
    alpha = seeded_schools["schools"]["alpha"]
    beta = seeded_schools["schools"]["beta"]
    alpha_admin = seeded_schools["users"]["alpha_admin"]
    beta_admin = seeded_schools["users"]["beta_admin"]
    created = create_structure(client, alpha_admin.email, alpha.id)

    beta_year = _post(client, "/api/school/academic-years", beta_admin.email, beta.id, _base("2026", "2026")).json()
    cross_section = _post(
        client,
        "/api/school/class-sections",
        beta_admin.email,
        beta.id,
        {
            **_base("A", "Cross School"),
            "branch_campus_id": created["branch"]["id"],
            "academic_year_id": beta_year["id"],
            "grade_level_id": created["level"]["id"],
        },
    )
    assert cross_section.status_code == 400

    update_alpha_from_beta = client.put(
        f"/api/school/branches/{created['branch']['id']}",
        headers=bearer(beta_admin.email, beta.id),
        json=_base("NORTH", "Wrong School"),
    )
    assert update_alpha_from_beta.status_code == 404

    alpha_section = db.query(ClassSection).filter_by(id=created["section"]["id"]).one()
    assert alpha_section.school_id == alpha.id


@pytest.mark.parametrize(
    "method,path,payload",
    [
        ("get", "/api/school/settings", None),
        ("put", "/api/school/settings", {"grade_level_label": "Year"}),
        ("get", "/api/school/setup-checklist", None),
        ("get", "/api/school/branches", None),
        ("post", "/api/school/branches", _base("X")),
        ("get", "/api/school/education-stages", None),
        ("post", "/api/school/education-stages", _base("X")),
        ("get", "/api/school/academic-years", None),
        ("post", "/api/school/academic-years", _base("X")),
        ("get", "/api/school/grade-levels", None),
        ("post", "/api/school/grade-levels", {**_base("X"), "education_stage_id": None}),
        ("get", "/api/school/class-sections", None),
        ("get", "/api/school/subjects", None),
        ("post", "/api/school/subjects", _base("X")),
        ("get", "/api/school/subject-groups", None),
    ],
)
def test_school_admin_cannot_use_another_school_context(db, client, seeded_schools, method, path, payload):
    beta = seeded_schools["schools"]["beta"]
    alpha_admin = seeded_schools["users"]["alpha_admin"]

    kwargs = {"headers": bearer(alpha_admin.email, beta.id)}
    if payload is not None:
        kwargs["json"] = payload

    assert getattr(client, method)(path, **kwargs).status_code == 403


def test_update_and_archive_endpoints_reject_wrong_roles_and_platform_only_users(db, client, seeded_schools):
    alpha = seeded_schools["schools"]["alpha"]
    admin = seeded_schools["users"]["alpha_admin"]
    teacher = seeded_schools["users"]["alpha_teacher"]
    platform_user = seeded_schools["platform_user"]
    created = create_structure(client, admin.email, alpha.id)
    update_cases = [
        (f"/api/school/branches/{created['branch']['id']}", _base("NORTH", "North Campus")),
        (f"/api/school/education-stages/{created['stage']['id']}", _base("PRIMARY", "Primary")),
        (f"/api/school/academic-years/{created['year']['id']}", _base("2026-27", "2026/27")),
        (f"/api/school/grade-levels/{created['level']['id']}", {**_base("Y1", "Year 1"), "education_stage_id": created["stage"]["id"]}),
        (
            f"/api/school/class-sections/{created['section']['id']}",
            {
                **_base("RED", "Year 1 Red"),
                "branch_campus_id": created["branch"]["id"],
                "academic_year_id": created["year"]["id"],
                "grade_level_id": created["level"]["id"],
            },
        ),
        (f"/api/school/subjects/{created['subject']['id']}", _base("ENG", "English")),
        (
            f"/api/school/subject-groups/{created['group']['id']}",
            {
                **_base("Y1RED-ENG", "Year 1 Red English"),
                "academic_year_id": created["year"]["id"],
                "class_section_id": created["section"]["id"],
                "subject_id": created["subject"]["id"],
            },
        ),
    ]

    for path, payload in update_cases:
        assert client.put(path, headers=bearer(teacher.email, alpha.id), json=payload).status_code == 403
        assert client.put(path, headers=bearer(platform_user.email, alpha.id), json=payload).status_code == 403
        assert client.delete(path, headers=bearer(teacher.email, alpha.id)).status_code == 403
        assert client.delete(path, headers=bearer(platform_user.email, alpha.id)).status_code == 403


def test_default_lists_exclude_archived_records_but_include_archived_returns_them(db, client, seeded_schools):
    alpha = seeded_schools["schools"]["alpha"]
    admin = seeded_schools["users"]["alpha_admin"]
    created = create_structure(client, admin.email, alpha.id)

    cases = {
        "branches": created["branch"],
        "education-stages": created["stage"],
        "academic-years": created["year"],
        "grade-levels": created["level"],
        "class-sections": created["section"],
        "subjects": created["subject"],
        "subject-groups": created["group"],
    }
    for path, row in cases.items():
        archive = client.delete(f"/api/school/{path}/{row['id']}", headers=bearer(admin.email, alpha.id))
        assert archive.status_code == 204

    for path, row in cases.items():
        default_ids = [r["id"] for r in client.get(f"/api/school/{path}", headers=bearer(admin.email, alpha.id)).json()]
        assert row["id"] not in default_ids, f"archived {path} leaked into default list"

        all_ids = [r["id"] for r in client.get(f"/api/school/{path}?include_archived=true", headers=bearer(admin.email, alpha.id)).json()]
        assert row["id"] in all_ids, f"include_archived did not return archived {path}"


def test_archived_parents_are_rejected_for_new_child_records(db, client, seeded_schools):
    alpha = seeded_schools["schools"]["alpha"]
    admin = seeded_schools["users"]["alpha_admin"]
    created = create_structure(client, admin.email, alpha.id)
    year, level, section, subject = created["year"], created["level"], created["section"], created["subject"]
    branch, stage = created["branch"], created["stage"]

    def archive(path: str, row_id: int) -> None:
        assert client.delete(f"/api/school/{path}/{row_id}", headers=bearer(admin.email, alpha.id)).status_code == 204

    # Archived education stage cannot be selected for a new grade level.
    archive("education-stages", stage["id"])
    assert _post(client, "/api/school/grade-levels", admin.email, alpha.id, {**_base("G9"), "education_stage_id": stage["id"]}).status_code == 400

    # Archived branch cannot be selected for a new class section (year + level still active).
    archive("branches", branch["id"])
    assert _post(client, "/api/school/class-sections", admin.email, alpha.id, {**_base("BLUE"), "branch_campus_id": branch["id"], "academic_year_id": year["id"], "grade_level_id": level["id"]}).status_code == 400

    # Archived subject cannot be selected for a new subject group (year + section still active).
    archive("subjects", subject["id"])
    assert _post(client, "/api/school/subject-groups", admin.email, alpha.id, {**_base("GRP-X"), "academic_year_id": year["id"], "class_section_id": section["id"], "subject_id": subject["id"]}).status_code == 400

    # Archived class section cannot be selected for a new subject group (fresh active subject + active year).
    subject2 = _post(client, "/api/school/subjects", admin.email, alpha.id, _base("MATH", "Maths")).json()
    archive("class-sections", section["id"])
    assert _post(client, "/api/school/subject-groups", admin.email, alpha.id, {**_base("GRP-Y"), "academic_year_id": year["id"], "class_section_id": section["id"], "subject_id": subject2["id"]}).status_code == 400

    # Archived academic year cannot be selected for a new class section (fresh active branch, level still active).
    branch2 = _post(client, "/api/school/branches", admin.email, alpha.id, _base("SOUTH", "South Campus")).json()
    archive("academic-years", year["id"])
    assert _post(client, "/api/school/class-sections", admin.email, alpha.id, {**_base("GREEN"), "branch_campus_id": branch2["id"], "academic_year_id": year["id"], "grade_level_id": level["id"]}).status_code == 400

    # Archived grade level cannot be selected for a new class section (fresh active branch + year).
    year2 = _post(client, "/api/school/academic-years", admin.email, alpha.id, _base("2027-28", "2027/28")).json()
    archive("grade-levels", level["id"])
    assert _post(client, "/api/school/class-sections", admin.email, alpha.id, {**_base("PURPLE"), "branch_campus_id": branch2["id"], "academic_year_id": year2["id"], "grade_level_id": level["id"]}).status_code == 400


def test_updates_may_keep_an_already_referenced_archived_parent(db, client, seeded_schools):
    alpha = seeded_schools["schools"]["alpha"]
    admin = seeded_schools["users"]["alpha_admin"]
    created = create_structure(client, admin.email, alpha.id)
    stage, level = created["stage"], created["level"]

    assert client.delete(f"/api/school/education-stages/{stage['id']}", headers=bearer(admin.email, alpha.id)).status_code == 204

    # Editing the grade level while keeping its existing (now archived) stage stays valid.
    keep = client.put(
        f"/api/school/grade-levels/{level['id']}",
        headers=bearer(admin.email, alpha.id),
        json={**_base("Y1", "Year 1 Renamed"), "education_stage_id": stage["id"]},
    )
    assert keep.status_code == 200
    assert keep.json()["name"] == "Year 1 Renamed"


def test_school_admin_can_update_each_structure_entity_in_place(db, client, seeded_schools):
    alpha = seeded_schools["schools"]["alpha"]
    admin = seeded_schools["users"]["alpha_admin"]
    created = create_structure(client, admin.email, alpha.id)

    def put(path: str, payload: dict):
        return client.put(f"/api/school/{path}", headers=bearer(admin.email, alpha.id), json=payload)

    branch = put(f"branches/{created['branch']['id']}", {**_base("NORTH", "North Renamed"), "name_ar": "الشمال", "sort_order": 3})
    assert branch.status_code == 200
    assert branch.json()["id"] == created["branch"]["id"]
    assert (branch.json()["name"], branch.json()["name_ar"], branch.json()["sort_order"]) == ("North Renamed", "الشمال", 3)

    stage = put(f"education-stages/{created['stage']['id']}", {**_base("PRIMARY", "Primary Renamed"), "status": "inactive"})
    assert stage.status_code == 200
    assert (stage.json()["name"], stage.json()["status"]) == ("Primary Renamed", "inactive")

    year = put(f"academic-years/{created['year']['id']}", _base("2026-27", "2026/2027 Renamed"))
    assert year.status_code == 200 and year.json()["name"] == "2026/2027 Renamed"

    # Changing a grade level's code must not break the class section that references it by id.
    level = put(f"grade-levels/{created['level']['id']}", {**_base("Y1X", "Year 1 Renamed"), "education_stage_id": created["stage"]["id"]})
    assert level.status_code == 200
    assert (level.json()["code"], level.json()["education_stage_id"]) == ("Y1X", created["stage"]["id"])

    section = put(
        f"class-sections/{created['section']['id']}",
        {
            **_base("RED", "Year 1 Red Renamed"),
            "branch_campus_id": created["branch"]["id"],
            "academic_year_id": created["year"]["id"],
            "grade_level_id": created["level"]["id"],
        },
    )
    assert section.status_code == 200 and section.json()["name"] == "Year 1 Red Renamed"

    subject = put(f"subjects/{created['subject']['id']}", _base("ENG", "English Renamed"))
    assert subject.status_code == 200 and subject.json()["name"] == "English Renamed"

    group = put(
        f"subject-groups/{created['group']['id']}",
        {
            **_base("Y1RED-ENG", "Year 1 Red English Renamed"),
            "academic_year_id": created["year"]["id"],
            "class_section_id": created["section"]["id"],
            "subject_id": created["subject"]["id"],
        },
    )
    assert group.status_code == 200 and group.json()["name"] == "Year 1 Red English Renamed"

    # Updated in place, not recreated: still exactly one class section, referencing the renamed level.
    section_row = db.query(ClassSection).filter_by(school_id=alpha.id).one()
    assert section_row.id == created["section"]["id"]
    assert section_row.grade_level_id == created["level"]["id"]


def test_updating_a_record_to_a_duplicate_code_is_rejected(db, client, seeded_schools):
    alpha = seeded_schools["schools"]["alpha"]
    admin = seeded_schools["users"]["alpha_admin"]
    first = _post(client, "/api/school/subjects", admin.email, alpha.id, _base("ENG", "English")).json()
    second = _post(client, "/api/school/subjects", admin.email, alpha.id, _base("MATH", "Maths")).json()

    conflict = client.put(
        f"/api/school/subjects/{second['id']}",
        headers=bearer(admin.email, alpha.id),
        json=_base("ENG", "Maths Duplicate"),
    )
    assert conflict.status_code == 409

    # Re-saving a record with its own unchanged code still succeeds.
    same_code = client.put(
        f"/api/school/subjects/{first['id']}",
        headers=bearer(admin.email, alpha.id),
        json=_base("ENG", "English Renamed"),
    )
    assert same_code.status_code == 200 and same_code.json()["name"] == "English Renamed"


def test_archived_records_restore_in_place_on_recreate(db, client, seeded_schools):
    alpha = seeded_schools["schools"]["alpha"]
    admin = seeded_schools["users"]["alpha_admin"]
    created = create_structure(client, admin.email, alpha.id)

    def archive(path: str, row_id: int) -> None:
        assert client.delete(f"/api/school/{path}/{row_id}", headers=bearer(admin.email, alpha.id)).status_code == 204

    def recreate(path: str, payload: dict):
        return _post(client, f"/api/school/{path}", admin.email, alpha.id, payload)

    def listed(path: str):
        return client.get(f"/api/school/{path}", headers=bearer(admin.email, alpha.id)).json()

    # Entities keyed on (school_id, code): archive then recreate with a changed name.
    simple = [
        ("branches", created["branch"], _base("NORTH", "North Restored")),
        ("education-stages", created["stage"], _base("PRIMARY", "Primary Restored")),
        ("academic-years", created["year"], _base("2026-27", "2026/27 Restored")),
        ("subjects", created["subject"], _base("ENG", "English Restored")),
    ]
    for path, original, payload in simple:
        archive(path, original["id"])
        assert original["id"] not in [r["id"] for r in listed(path)]  # hidden while archived
        resp = recreate(path, payload)
        assert resp.status_code == 201, (path, resp.json())
        body = resp.json()
        assert body["restored"] is True
        assert body["id"] == original["id"]  # same row, not a duplicate
        assert body["status"] == "active"
        assert body["name"] == payload["name"]  # editable field refreshed from the form
        # Visible again as active in the default (non-archived) list.
        assert any(r["id"] == original["id"] and r["status"] == "active" for r in listed(path))

    # Grade level (parent education stage still active).
    archive("grade-levels", created["level"]["id"])
    level = recreate("grade-levels", {**_base("Y1", "Year 1 Restored"), "education_stage_id": created["stage"]["id"]})
    assert level.status_code == 201
    assert (level.json()["restored"], level.json()["id"]) == (True, created["level"]["id"])
    assert level.json()["education_stage_id"] == created["stage"]["id"]

    # Class section (branch/year/level still active).
    archive("class-sections", created["section"]["id"])
    section = recreate(
        "class-sections",
        {
            **_base("RED", "Year 1 Red Restored"),
            "branch_campus_id": created["branch"]["id"],
            "academic_year_id": created["year"]["id"],
            "grade_level_id": created["level"]["id"],
        },
    )
    assert section.status_code == 201
    assert (section.json()["restored"], section.json()["id"]) == (True, created["section"]["id"])

    # Subject group (year/section/subject still active).
    archive("subject-groups", created["group"]["id"])
    group = recreate(
        "subject-groups",
        {
            **_base("Y1RED-ENG", "Year 1 Red English Restored"),
            "academic_year_id": created["year"]["id"],
            "class_section_id": created["section"]["id"],
            "subject_id": created["subject"]["id"],
        },
    )
    assert group.status_code == 201
    assert (group.json()["restored"], group.json()["id"]) == (True, created["group"]["id"])


def test_active_and_inactive_duplicates_are_rejected_with_clear_messages(db, client, seeded_schools):
    alpha = seeded_schools["schools"]["alpha"]
    admin = seeded_schools["users"]["alpha_admin"]
    first = _post(client, "/api/school/subjects", admin.email, alpha.id, _base("ENG", "English")).json()

    active_dup = _post(client, "/api/school/subjects", admin.email, alpha.id, _base("ENG", "English Again"))
    assert active_dup.status_code == 409
    assert "active" in active_dup.json()["detail"].lower()

    made_inactive = client.put(
        f"/api/school/subjects/{first['id']}",
        headers=bearer(admin.email, alpha.id),
        json={**_base("ENG", "English"), "status": "inactive"},
    )
    assert made_inactive.status_code == 200 and made_inactive.json()["status"] == "inactive"

    # Inactive is a visible managed record, not deleted: recreating its code is still rejected.
    inactive_dup = _post(client, "/api/school/subjects", admin.email, alpha.id, _base("ENG", "English Again"))
    assert inactive_dup.status_code == 409
    assert "inactive" in inactive_dup.json()["detail"].lower()
    assert db.query(Subject).filter_by(id=first["id"]).one().status == "inactive"


def test_restore_is_school_scoped_and_cross_school_isolated(db, client, seeded_schools):
    alpha = seeded_schools["schools"]["alpha"]
    beta = seeded_schools["schools"]["beta"]
    alpha_admin = seeded_schools["users"]["alpha_admin"]
    beta_admin = seeded_schools["users"]["beta_admin"]

    alpha_subject = _post(client, "/api/school/subjects", alpha_admin.email, alpha.id, _base("SHARED", "Alpha Shared")).json()
    assert client.delete(f"/api/school/subjects/{alpha_subject['id']}", headers=bearer(alpha_admin.email, alpha.id)).status_code == 204

    # Beta creating the same code makes a NEW beta row; it must not touch alpha's archived row.
    beta_subject = _post(client, "/api/school/subjects", beta_admin.email, beta.id, _base("SHARED", "Beta Shared"))
    assert beta_subject.status_code == 201
    assert beta_subject.json()["restored"] is False
    assert beta_subject.json()["id"] != alpha_subject["id"]
    assert db.query(Subject).filter_by(id=alpha_subject["id"]).one().status == "archived"

    # Beta admin cannot act inside alpha's context at all.
    cross = client.post("/api/school/subjects", headers=bearer(beta_admin.email, alpha.id), json=_base("SHARED", "X"))
    assert cross.status_code == 403


def test_wrong_role_user_cannot_restore_archived_record(db, client, seeded_schools):
    alpha = seeded_schools["schools"]["alpha"]
    admin = seeded_schools["users"]["alpha_admin"]
    teacher = seeded_schools["users"]["alpha_teacher"]

    subject = _post(client, "/api/school/subjects", admin.email, alpha.id, _base("ART", "Art")).json()
    assert client.delete(f"/api/school/subjects/{subject['id']}", headers=bearer(admin.email, alpha.id)).status_code == 204

    blocked = client.post("/api/school/subjects", headers=bearer(teacher.email, alpha.id), json=_base("ART", "Art"))
    assert blocked.status_code == 403
    assert db.query(Subject).filter_by(id=subject["id"]).one().status == "archived"
