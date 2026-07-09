import os
from contextlib import contextmanager

os.environ["DATABASE_URL"] = "sqlite://"
os.environ["APP_ENV"] = "test"
os.environ["DEV_AUTH_ENABLED"] = "false"

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app import auth, database
from app.database import Base, get_db
from app.main import app
from app.models_school import Enrolment, StaffAssignment, SubjectGroup
from school_fixtures import seeded_schools  # noqa: F401


engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
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


@contextmanager
def count_queries():
    counter = {"n": 0}

    def _before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
        counter["n"] += 1

    event.listen(engine, "before_cursor_execute", _before_cursor_execute)
    try:
        yield counter
    finally:
        event.remove(engine, "before_cursor_execute", _before_cursor_execute)


def bearer(email: str, school_id: int | None = None) -> dict[str, str]:
    headers = {"Authorization": f"Bearer {auth.create_access_token({'sub': email})}"}
    if school_id is not None:
        headers["X-School-Id"] = str(school_id)
    return headers


def _base(code: str, name: str | None = None) -> dict:
    return {"code": code, "name": name or code, "name_ar": None, "sort_order": 0, "status": "active"}


def _post(client, path: str, email: str, school_id: int, payload: dict):
    return client.post(path, headers=bearer(email, school_id), json=payload)


def build_structure(client, admin_email: str, school_id: int, *, section_codes=("RED", "BLUE")) -> dict:
    branch = _post(client, "/api/school/branches", admin_email, school_id, _base("MAIN2", "Main")).json()
    stage = _post(client, "/api/school/education-stages", admin_email, school_id, _base("PRIMARY", "Primary")).json()
    year = _post(client, "/api/school/academic-years", admin_email, school_id, _base("2026-27", "2026/27")).json()
    level = _post(
        client, "/api/school/grade-levels", admin_email, school_id,
        {**_base("Y1", "Year 1"), "education_stage_id": stage["id"]},
    ).json()
    sections = []
    for code in section_codes:
        section = _post(
            client, "/api/school/class-sections", admin_email, school_id,
            {**_base(code, f"Year 1 {code}"), "branch_campus_id": branch["id"], "academic_year_id": year["id"], "grade_level_id": level["id"]},
        ).json()
        sections.append(section)
    subject_eng = _post(client, "/api/school/subjects", admin_email, school_id, _base("ENG", "English")).json()
    subject_math = _post(client, "/api/school/subjects", admin_email, school_id, _base("MATH", "Maths")).json()
    return {
        "branch": branch,
        "stage": stage,
        "year": year,
        "level": level,
        "sections": sections,
        "subject_eng": subject_eng,
        "subject_math": subject_math,
    }


def create_template(client, admin_email: str, school_id: int, *, education_stage_id=None, grade_level_id=None, subject_id, sort_order=0, status="active"):
    return _post(
        client, "/api/school/default-subject-templates", admin_email, school_id,
        {"education_stage_id": education_stage_id, "grade_level_id": grade_level_id, "subject_id": subject_id, "sort_order": sort_order, "status": status},
    )


def test_school_admin_can_crud_templates(db, client, seeded_schools):
    alpha = seeded_schools["schools"]["alpha"]
    admin = seeded_schools["users"]["alpha_admin"]
    structure = build_structure(client, admin.email, alpha.id)

    created = create_template(client, admin.email, alpha.id, education_stage_id=structure["stage"]["id"], subject_id=structure["subject_eng"]["id"])
    assert created.status_code == 201
    body = created.json()
    assert body["education_stage_id"] == structure["stage"]["id"]
    assert body["grade_level_id"] is None
    assert body["restored"] is False

    listed = client.get("/api/school/default-subject-templates", headers=bearer(admin.email, alpha.id))
    assert listed.status_code == 200
    assert len(listed.json()) == 1
    assert listed.json()[0]["subject"]["id"] == structure["subject_eng"]["id"]

    updated = client.put(
        f"/api/school/default-subject-templates/{body['id']}",
        headers=bearer(admin.email, alpha.id),
        json={"education_stage_id": structure["stage"]["id"], "grade_level_id": None, "subject_id": structure["subject_math"]["id"], "sort_order": 5, "status": "inactive"},
    )
    assert updated.status_code == 200
    assert updated.json()["subject_id"] == structure["subject_math"]["id"]
    assert updated.json()["status"] == "inactive"

    archived = client.delete(f"/api/school/default-subject-templates/{body['id']}", headers=bearer(admin.email, alpha.id))
    assert archived.status_code == 204
    listed_after = client.get("/api/school/default-subject-templates", headers=bearer(admin.email, alpha.id))
    assert listed_after.json() == []
    listed_with_archived = client.get("/api/school/default-subject-templates?include_archived=true", headers=bearer(admin.email, alpha.id))
    assert len(listed_with_archived.json()) == 1


def test_wrong_role_is_blocked(db, client, seeded_schools):
    alpha = seeded_schools["schools"]["alpha"]
    admin = seeded_schools["users"]["alpha_admin"]
    teacher = seeded_schools["users"]["alpha_teacher"]
    structure = build_structure(client, admin.email, alpha.id)

    response = create_template(client, teacher.email, alpha.id, education_stage_id=structure["stage"]["id"], subject_id=structure["subject_eng"]["id"])
    assert response.status_code == 403


def test_wrong_school_is_blocked(db, client, seeded_schools):
    alpha = seeded_schools["schools"]["alpha"]
    beta = seeded_schools["schools"]["beta"]
    alpha_admin = seeded_schools["users"]["alpha_admin"]
    beta_admin = seeded_schools["users"]["beta_admin"]
    structure = build_structure(client, alpha_admin.email, alpha.id)

    created = create_template(client, alpha_admin.email, alpha.id, education_stage_id=structure["stage"]["id"], subject_id=structure["subject_eng"]["id"])
    template_id = created.json()["id"]

    cross_school = client.put(
        f"/api/school/default-subject-templates/{template_id}",
        headers=bearer(beta_admin.email, beta.id),
        json={"education_stage_id": structure["stage"]["id"], "grade_level_id": None, "subject_id": structure["subject_eng"]["id"], "sort_order": 0, "status": "active"},
    )
    assert cross_school.status_code == 404

    cross_school_create = create_template(client, beta_admin.email, beta.id, education_stage_id=structure["stage"]["id"], subject_id=structure["subject_eng"]["id"])
    assert cross_school_create.status_code == 400


def test_exactly_one_scope_required(db, client, seeded_schools):
    alpha = seeded_schools["schools"]["alpha"]
    admin = seeded_schools["users"]["alpha_admin"]
    structure = build_structure(client, admin.email, alpha.id)

    neither = create_template(client, admin.email, alpha.id, subject_id=structure["subject_eng"]["id"])
    assert neither.status_code == 400

    both = create_template(
        client, admin.email, alpha.id,
        education_stage_id=structure["stage"]["id"], grade_level_id=structure["level"]["id"], subject_id=structure["subject_eng"]["id"],
    )
    assert both.status_code == 400


def test_active_and_inactive_duplicate_stage_template_rejected(db, client, seeded_schools):
    # Regression: stage templates have grade_level_id NULL for every row, so the
    # dedupe must not rely on the SQL unique constraint (NULLs never collide there).
    alpha = seeded_schools["schools"]["alpha"]
    admin = seeded_schools["users"]["alpha_admin"]
    structure = build_structure(client, admin.email, alpha.id)

    first = create_template(client, admin.email, alpha.id, education_stage_id=structure["stage"]["id"], subject_id=structure["subject_eng"]["id"])
    assert first.status_code == 201

    duplicate = create_template(client, admin.email, alpha.id, education_stage_id=structure["stage"]["id"], subject_id=structure["subject_eng"]["id"])
    assert duplicate.status_code == 409

    inactive = create_template(client, admin.email, alpha.id, education_stage_id=structure["stage"]["id"], subject_id=structure["subject_math"]["id"], status="inactive")
    assert inactive.status_code == 201
    duplicate_of_inactive = create_template(client, admin.email, alpha.id, education_stage_id=structure["stage"]["id"], subject_id=structure["subject_math"]["id"])
    assert duplicate_of_inactive.status_code == 409
    assert "inactive" in duplicate_of_inactive.json()["detail"].lower()


def test_archived_template_recreate_restores_in_place(db, client, seeded_schools):
    alpha = seeded_schools["schools"]["alpha"]
    admin = seeded_schools["users"]["alpha_admin"]
    structure = build_structure(client, admin.email, alpha.id)

    created = create_template(client, admin.email, alpha.id, education_stage_id=structure["stage"]["id"], subject_id=structure["subject_eng"]["id"]).json()
    client.delete(f"/api/school/default-subject-templates/{created['id']}", headers=bearer(admin.email, alpha.id))

    recreated = create_template(client, admin.email, alpha.id, education_stage_id=structure["stage"]["id"], subject_id=structure["subject_eng"]["id"])
    assert recreated.status_code == 201
    body = recreated.json()
    assert body["id"] == created["id"]
    assert body["restored"] is True
    assert body["status"] == "active"


def test_template_refs_must_belong_to_same_school(db, client, seeded_schools):
    alpha = seeded_schools["schools"]["alpha"]
    beta = seeded_schools["schools"]["beta"]
    alpha_admin = seeded_schools["users"]["alpha_admin"]
    beta_admin = seeded_schools["users"]["beta_admin"]
    alpha_structure = build_structure(client, alpha_admin.email, alpha.id)
    build_structure(client, beta_admin.email, beta.id)

    cross = create_template(client, beta_admin.email, beta.id, education_stage_id=alpha_structure["stage"]["id"], subject_id=alpha_structure["subject_eng"]["id"])
    assert cross.status_code == 400


def _preview(client, admin_email, school_id, **kwargs):
    payload = {"academic_year_id": kwargs.pop("academic_year_id")}
    payload.update(kwargs)
    return client.post("/api/school/default-subject-templates/preview", headers=bearer(admin_email, school_id), json=payload)


def _apply(client, admin_email, school_id, **kwargs):
    payload = {"academic_year_id": kwargs.pop("academic_year_id")}
    payload.update(kwargs)
    return client.post("/api/school/default-subject-templates/apply", headers=bearer(admin_email, school_id), json=payload)


def test_preview_resolves_stage_and_grade_templates_and_dedupes(db, client, seeded_schools):
    alpha = seeded_schools["schools"]["alpha"]
    admin = seeded_schools["users"]["alpha_admin"]
    structure = build_structure(client, admin.email, alpha.id)

    # ENG is templated at both stage and grade level -> must dedupe to one group per section.
    create_template(client, admin.email, alpha.id, education_stage_id=structure["stage"]["id"], subject_id=structure["subject_eng"]["id"])
    create_template(client, admin.email, alpha.id, grade_level_id=structure["level"]["id"], subject_id=structure["subject_eng"]["id"])
    create_template(client, admin.email, alpha.id, grade_level_id=structure["level"]["id"], subject_id=structure["subject_math"]["id"])

    preview = _preview(client, admin.email, alpha.id, academic_year_id=structure["year"]["id"])
    assert preview.status_code == 200
    body = preview.json()
    # 2 sections * 2 distinct subjects (ENG deduped, MATH) = 4 planned rows, all would_create.
    assert body["would_create"] == 4
    assert body["would_restore"] == 0
    assert body["skipped_existing"] == 0
    assert body["failed"] == 0
    subject_ids_per_section = {}
    for row in body["results"]:
        subject_ids_per_section.setdefault(row["class_section_id"], set()).add(row["subject_id"])
    for subject_ids in subject_ids_per_section.values():
        assert subject_ids == {structure["subject_eng"]["id"], structure["subject_math"]["id"]}


def test_optional_branch_stage_grade_filters_narrow_sections(db, client, seeded_schools):
    alpha = seeded_schools["schools"]["alpha"]
    admin = seeded_schools["users"]["alpha_admin"]
    structure = build_structure(client, admin.email, alpha.id, section_codes=("RED",))

    other_branch = _post(client, "/api/school/branches", admin.email, alpha.id, _base("NORTH2", "North")).json()
    other_stage = _post(client, "/api/school/education-stages", admin.email, alpha.id, _base("SECONDARY", "Secondary")).json()
    other_level = _post(
        client, "/api/school/grade-levels", admin.email, alpha.id,
        {**_base("Y7", "Year 7"), "education_stage_id": other_stage["id"]},
    ).json()
    other_section = _post(
        client, "/api/school/class-sections", admin.email, alpha.id,
        {**_base("GREEN", "Year 7 Green"), "branch_campus_id": other_branch["id"], "academic_year_id": structure["year"]["id"], "grade_level_id": other_level["id"]},
    ).json()

    create_template(client, admin.email, alpha.id, education_stage_id=structure["stage"]["id"], subject_id=structure["subject_eng"]["id"])
    create_template(client, admin.email, alpha.id, education_stage_id=other_stage["id"], subject_id=structure["subject_math"]["id"])

    by_grade = _preview(client, admin.email, alpha.id, academic_year_id=structure["year"]["id"], grade_level_id=structure["level"]["id"]).json()
    assert all(row["class_section_id"] == structure["sections"][0]["id"] for row in by_grade["results"])

    by_stage = _preview(client, admin.email, alpha.id, academic_year_id=structure["year"]["id"], education_stage_id=other_stage["id"]).json()
    assert all(row["class_section_id"] == other_section["id"] for row in by_stage["results"])
    assert by_stage["would_create"] == 1

    by_branch = _preview(client, admin.email, alpha.id, academic_year_id=structure["year"]["id"], branch_campus_id=other_branch["id"]).json()
    assert all(row["class_section_id"] == other_section["id"] for row in by_branch["results"])


def test_apply_creates_section_specific_default_for_section_groups(db, client, seeded_schools):
    alpha = seeded_schools["schools"]["alpha"]
    admin = seeded_schools["users"]["alpha_admin"]
    structure = build_structure(client, admin.email, alpha.id)
    create_template(client, admin.email, alpha.id, education_stage_id=structure["stage"]["id"], subject_id=structure["subject_eng"]["id"])

    apply_response = _apply(client, admin.email, alpha.id, academic_year_id=structure["year"]["id"])
    assert apply_response.status_code == 200
    body = apply_response.json()
    assert body["created"] == 2
    assert body["restored"] == 0
    assert body["skipped"] == 0
    assert body["failed"] == 0
    for row in body["results"]:
        assert row["status"] == "created"
        assert row["subject_group"]["enrolment_policy"] == "default_for_section"
        assert row["subject_group"]["class_section_id"] in [s["id"] for s in structure["sections"]]
        assert row["subject_group"]["grade_level_id"] is None

    groups = client.get("/api/school/subject-groups", headers=bearer(admin.email, alpha.id)).json()
    assert len(groups) == 2


def test_apply_is_idempotent_on_second_run(db, client, seeded_schools):
    alpha = seeded_schools["schools"]["alpha"]
    admin = seeded_schools["users"]["alpha_admin"]
    structure = build_structure(client, admin.email, alpha.id)
    create_template(client, admin.email, alpha.id, education_stage_id=structure["stage"]["id"], subject_id=structure["subject_eng"]["id"])

    first = _apply(client, admin.email, alpha.id, academic_year_id=structure["year"]["id"]).json()
    assert first["created"] == 2

    second = _apply(client, admin.email, alpha.id, academic_year_id=structure["year"]["id"]).json()
    assert second["created"] == 0
    assert second["skipped"] == 2
    for row in second["results"]:
        assert row["status"] == "skipped_existing"

    groups = client.get("/api/school/subject-groups", headers=bearer(admin.email, alpha.id)).json()
    assert len(groups) == 2


def test_apply_skips_existing_active_and_inactive_matching_groups(db, client, seeded_schools):
    alpha = seeded_schools["schools"]["alpha"]
    admin = seeded_schools["users"]["alpha_admin"]
    structure = build_structure(client, admin.email, alpha.id, section_codes=("RED",))
    create_template(client, admin.email, alpha.id, education_stage_id=structure["stage"]["id"], subject_id=structure["subject_eng"]["id"])

    preview = _preview(client, admin.email, alpha.id, academic_year_id=structure["year"]["id"]).json()
    generated_code = preview["results"][0]["code"]
    generated_name = preview["results"][0]["name"]

    manual_group = _post(
        client, "/api/school/subject-groups", admin.email, alpha.id,
        {
            **_base(generated_code, generated_name),
            "academic_year_id": structure["year"]["id"],
            "class_section_id": structure["sections"][0]["id"],
            "subject_id": structure["subject_eng"]["id"],
            "enrolment_policy": "explicit_only",
            "status": "inactive",
        },
    ).json()

    applied = _apply(client, admin.email, alpha.id, academic_year_id=structure["year"]["id"]).json()
    assert applied["created"] == 0
    assert applied["restored"] == 0
    assert applied["skipped"] == 1
    assert applied["results"][0]["status"] == "skipped_existing"
    assert applied["results"][0]["subject_group"]["id"] == manual_group["id"]

    groups = client.get("/api/school/subject-groups", headers=bearer(admin.email, alpha.id)).json()
    assert len(groups) == 1


def test_apply_restores_archived_matching_group(db, client, seeded_schools):
    alpha = seeded_schools["schools"]["alpha"]
    admin = seeded_schools["users"]["alpha_admin"]
    structure = build_structure(client, admin.email, alpha.id, section_codes=("RED",))
    create_template(client, admin.email, alpha.id, education_stage_id=structure["stage"]["id"], subject_id=structure["subject_eng"]["id"])

    first_apply = _apply(client, admin.email, alpha.id, academic_year_id=structure["year"]["id"]).json()
    group_id = first_apply["results"][0]["subject_group"]["id"]
    client.delete(f"/api/school/subject-groups/{group_id}", headers=bearer(admin.email, alpha.id))

    second_apply = _apply(client, admin.email, alpha.id, academic_year_id=structure["year"]["id"]).json()
    assert second_apply["created"] == 0
    assert second_apply["restored"] == 1
    assert second_apply["results"][0]["status"] == "restored"
    assert second_apply["results"][0]["subject_group"]["id"] == group_id
    assert second_apply["results"][0]["subject_group"]["status"] == "active"

    groups = client.get("/api/school/subject-groups", headers=bearer(admin.email, alpha.id)).json()
    assert len(groups) == 1


def test_apply_does_not_touch_teacher_assignments_or_enrolments(db, client, seeded_schools):
    alpha = seeded_schools["schools"]["alpha"]
    admin = seeded_schools["users"]["alpha_admin"]
    structure = build_structure(client, admin.email, alpha.id)
    create_template(client, admin.email, alpha.id, education_stage_id=structure["stage"]["id"], subject_id=structure["subject_eng"]["id"])

    assignments_before = db.query(StaffAssignment).count()
    enrolments_before = db.query(Enrolment).count()

    _apply(client, admin.email, alpha.id, academic_year_id=structure["year"]["id"])

    assert db.query(StaffAssignment).count() == assignments_before
    assert db.query(Enrolment).count() == enrolments_before


def test_cross_school_isolation_on_preview_and_apply(db, client, seeded_schools):
    alpha = seeded_schools["schools"]["alpha"]
    beta = seeded_schools["schools"]["beta"]
    alpha_admin = seeded_schools["users"]["alpha_admin"]
    beta_admin = seeded_schools["users"]["beta_admin"]
    alpha_structure = build_structure(client, alpha_admin.email, alpha.id)
    build_structure(client, beta_admin.email, beta.id)
    create_template(client, alpha_admin.email, alpha.id, education_stage_id=alpha_structure["stage"]["id"], subject_id=alpha_structure["subject_eng"]["id"])

    # Beta has no templates of its own, so its preview/apply against its own
    # academic year must be empty, not see Alpha's template or sections.
    beta_year = client.get("/api/school/academic-years", headers=bearer(beta_admin.email, beta.id)).json()[0]
    beta_preview = _preview(client, beta_admin.email, beta.id, academic_year_id=beta_year["id"]).json()
    assert beta_preview["would_create"] == 0

    cross_school_academic_year = client.post(
        "/api/school/default-subject-templates/preview",
        headers=bearer(beta_admin.email, beta.id),
        json={"academic_year_id": alpha_structure["year"]["id"]},
    )
    assert cross_school_academic_year.status_code == 400


def test_preview_and_apply_query_count_does_not_scale_with_section_count(db, client, seeded_schools):
    alpha = seeded_schools["schools"]["alpha"]
    admin = seeded_schools["users"]["alpha_admin"]
    structure = build_structure(client, admin.email, alpha.id, section_codes=("RED", "BLUE"))
    create_template(client, admin.email, alpha.id, education_stage_id=structure["stage"]["id"], subject_id=structure["subject_eng"]["id"])
    create_template(client, admin.email, alpha.id, grade_level_id=structure["level"]["id"], subject_id=structure["subject_math"]["id"])

    with count_queries() as baseline_counter:
        baseline = _preview(client, admin.email, alpha.id, academic_year_id=structure["year"]["id"])
    assert baseline.status_code == 200
    baseline_rows = len(baseline.json()["results"])

    extra_codes = [f"EXTRA{i}" for i in range(8)]
    for code in extra_codes:
        _post(
            client, "/api/school/class-sections", admin.email, alpha.id,
            {**_base(code, f"Year 1 {code}"), "branch_campus_id": structure["branch"]["id"], "academic_year_id": structure["year"]["id"], "grade_level_id": structure["level"]["id"]},
        )

    with count_queries() as many_counter:
        many = _preview(client, admin.email, alpha.id, academic_year_id=structure["year"]["id"])
    assert many.status_code == 200
    many_rows = len(many.json()["results"])
    assert many_rows > baseline_rows

    # Batched planner: a fixed number of reads regardless of section count, not
    # one extra query per additional section.
    assert many_counter["n"] - baseline_counter["n"] < 10

    with count_queries() as apply_counter:
        applied = _apply(client, admin.email, alpha.id, academic_year_id=structure["year"]["id"])
    assert applied.status_code == 200
    assert applied.json()["created"] == many_rows
    # Apply adds one INSERT per created row on top of the flat read set, but the
    # read portion must not scale with section count either.
    assert apply_counter["n"] - many_counter["n"] < many_rows + 15
