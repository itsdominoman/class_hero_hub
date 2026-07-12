import os
os.environ["DATABASE_URL"] = "sqlite://"
os.environ["APP_ENV"] = "test"
os.environ["DEV_AUTH_ENABLED"] = "false"

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app import auth, database
from app.database import Base, get_db
from app.main import app
from app.models_school import (
    AcademicYear, BehaviourCategory, BehaviourEvent, BranchCampus, ClassSection,
    Enrolment, GradeLevel, GuardianLink, Membership, School, StaffAssignment,
    Student, Subject, SubjectGroup, User,
)

engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
Session = sessionmaker(bind=engine)
database.engine = engine; database.SessionLocal = Session

@pytest.fixture
def db():
    Base.metadata.create_all(engine); session = Session()
    yield session
    session.close(); Base.metadata.drop_all(engine)

@pytest.fixture
def client():
    def override():
        session = Session()
        try: yield session
        finally: session.close()
    app.dependency_overrides[get_db] = override
    yield TestClient(app)
    app.dependency_overrides.clear()

def headers(user, school=None):
    result = {"Authorization": f"Bearer {auth.create_access_token({'sub': user.email})}"}
    if school: result["X-School-Id"] = str(school.id)
    return result

@pytest.fixture
def world(db):
    a = School(name="Alpha", slug="alpha", status="active"); b = School(name="Beta", slug="beta", status="active")
    admin = User(email="admin@a.test", name="Admin"); teacher = User(email="teacher@a.test", name="Teacher"); guardian = User(email="guardian@test", name="Guardian"); outsider = User(email="other@test", name="Other")
    db.add_all([a,b,admin,teacher,guardian,outsider]); db.flush()
    db.add_all([Membership(school_id=a.id,user_id=admin.id,role="school_admin"), Membership(school_id=a.id,user_id=teacher.id,role="teacher")])
    s1=Student(school_id=a.id,first_name="A",last_name="One",status="active"); s2=Student(school_id=a.id,first_name="A",last_name="Two",status="active"); inactive=Student(school_id=a.id,first_name="Old",last_name="Student",status="inactive"); foreign=Student(school_id=b.id,first_name="B",last_name="One",status="active")
    db.add_all([s1,s2,inactive,foreign]); db.flush(); db.add(GuardianLink(school_id=a.id,student_id=s1.id,user_id=guardian.id,status="active")); db.commit()
    return locals()

def add_assignment_context(db, w):
    branch = BranchCampus(school_id=w["a"].id, code="MAIN", name="Main", status="active")
    year = AcademicYear(school_id=w["a"].id, code="2026", name="2026", status="active", is_current=True)
    level = GradeLevel(school_id=w["a"].id, code="G1", name="Grade 1", status="active")
    db.add_all([branch, year, level]); db.flush()
    section = ClassSection(school_id=w["a"].id, branch_campus_id=branch.id, academic_year_id=year.id, grade_level_id=level.id, code="A", name="Grade 1 A", status="active")
    subject = Subject(school_id=w["a"].id, code="ENG", name="English", status="active")
    db.add_all([section, subject]); db.flush()
    group = SubjectGroup(school_id=w["a"].id, academic_year_id=year.id, class_section_id=section.id, subject_id=subject.id, code="G1A-ENG", name="Grade 1 A English", status="active", enrolment_policy="default_for_section")
    db.add(group); db.flush()
    membership = db.query(Membership).filter_by(school_id=w["a"].id, user_id=w["teacher"].id).one()
    db.add_all([
        Enrolment(school_id=w["a"].id, student_id=w["s1"].id, class_section_id=section.id, kind="member"),
        StaffAssignment(school_id=w["a"].id, membership_id=membership.id, class_section_id=section.id, role="homeroom"),
        StaffAssignment(school_id=w["a"].id, membership_id=membership.id, subject_group_id=group.id, role="subject"),
    ]); db.commit()
    return section, subject, group

def test_defaults_admin_crud_and_teacher_active_visibility(db, client, world):
    w=world
    seeded=client.get("/api/school/behaviour/categories",headers=headers(w["admin"],w["a"])); assert seeded.status_code==200; assert len(seeded.json()["categories"])==31
    labels={row["label"] for row in seeded.json()["categories"]}; assert {"Good sportsmanship","Safe play","Helping at break","Out of bounds","Wandering halls","Running indoors","Leaving area without permission","Not following instructions"} <= labels
    created=client.post("/api/school/behaviour/categories",headers=headers(w["admin"],w["a"]),json={"type":"positive","label":"Curiosity","points_value":2,"sort_order":5,"active":True}); assert created.status_code==201
    category_id=created.json()["id"]
    assert client.patch(f"/api/school/behaviour/categories/{category_id}",headers=headers(w["admin"],w["a"]),json={"active":False}).status_code==200
    visible=client.get(f"/api/teach/behaviour/categories?school_id={w['a'].id}",headers=headers(w["teacher"])); assert visible.status_code==200; assert all(r["active"] for r in visible.json()["categories"]); assert category_id not in {r["id"] for r in visible.json()["categories"]}
    assert db.query(BehaviourCategory).filter_by(school_id=w["b"].id).count()==0

def test_teacher_same_school_events_are_auditable_and_cross_school_blocked(db, client, world):
    w=world; client.get("/api/school/behaviour/categories",headers=headers(w["admin"],w["a"])); category=db.query(BehaviourCategory).filter_by(school_id=w["a"].id,type="positive").first()
    result=client.post("/api/teach/behaviour/events",headers=headers(w["teacher"]),json={"school_id":w["a"].id,"student_ids":[w["s1"].id,w["s2"].id],"category_id":category.id,"note":"  Safe note  "}); assert result.status_code==201; assert result.json()["created"]==2
    events=db.query(BehaviourEvent).all(); assert {e.student_id for e in events}=={w["s1"].id,w["s2"].id}; assert all(e.actor_user_id==w["teacher"].id and e.points_delta==1 and e.category_id==category.id and e.note=="Safe note" and e.context_type=="general" for e in events)
    for student in (w["foreign"],w["inactive"]): assert client.post("/api/teach/behaviour/events",headers=headers(w["teacher"]),json={"school_id":w["a"].id,"student_ids":[student.id],"category_id":category.id}).status_code==400
    foreign_category=BehaviourCategory(school_id=w["b"].id,type="needs_work",label="Off task",points_value=-1,active=True); db.add(foreign_category); db.commit()
    assert client.post("/api/teach/behaviour/events",headers=headers(w["teacher"]),json={"school_id":w["a"].id,"student_ids":[w["s1"].id],"category_id":foreign_category.id}).status_code==400

def test_guardian_summary_is_link_scoped_and_revocation_removes_access(db, client, world):
    w=world; category=BehaviourCategory(school_id=w["a"].id,type="needs_work",label="Not listening",points_value=-2,active=True); db.add(category); db.flush(); db.add(BehaviourEvent(school_id=w["a"].id,student_id=w["s1"].id,category_id=category.id,actor_user_id=w["teacher"].id,points_delta=-2,note="Reminder",source="teacher")); db.commit()
    payload=client.get("/api/guardian/points",headers=headers(w["guardian"])).json(); assert payload["children"][0]["total"]==-2; assert payload["children"][0]["recent_events"][0]["category_id"]==category.id; assert "email" not in str(payload).lower() and "token" not in str(payload).lower()
    assert client.get("/api/guardian/points",headers=headers(w["outsider"])).json()=={"children":[]}
    link=db.query(GuardianLink).one(); link.status="revoked"; db.commit(); assert client.get("/api/guardian/points",headers=headers(w["guardian"])).json()=={"children":[]}

def test_teacher_student_search_is_auth_role_school_status_scoped_and_allow_listed(db, client, world):
    w=world; w["s1"].first_name="Alice"; w["s1"].preferred_name="Ali"; w["s1"].external_ref="SAFE-22"; w["s1"].avatar_id=31
    w["s2"].first_name="Alina"; w["inactive"].first_name="Alice"; w["foreign"].first_name="Alice"
    inactive_teacher=User(email="inactive-teacher@test",name="Inactive Teacher"); db.add(inactive_teacher); db.flush(); db.add(Membership(school_id=w["a"].id,user_id=inactive_teacher.id,role="teacher",status="inactive"))
    category=BehaviourCategory(school_id=w["a"].id,type="positive",label="Search total",points_value=2,active=True); db.add(category); db.flush(); db.add(BehaviourEvent(school_id=w["a"].id,student_id=w["s1"].id,category_id=category.id,actor_user_id=w["teacher"].id,points_delta=2,source="teacher")); db.commit()
    url=f"/api/teach/students/search?school_id={w['a'].id}&q=al"
    assert client.get(url).status_code==401
    assert client.get(url,headers=headers(w["outsider"])).status_code==403
    assert client.get(url,headers=headers(inactive_teacher)).status_code==403
    response=client.get(url,headers=headers(w["teacher"])); assert response.status_code==200
    rows=response.json()["students"]; assert {row["id"] for row in rows}=={w["s1"].id,w["s2"].id}
    alice=next(row for row in rows if row["id"]==w["s1"].id); assert alice["points_total"]==2 and alice["avatar_id"]==31 and alice["avatar_url_256"]
    assert set(alice)=={"id","display_name","first_name","last_name","preferred_name","name_ar","points_total","avatar_id","avatar_url_128","avatar_url_256","class_section","grade_level"}
    assert client.get(f"/api/teach/students/search?school_id={w['a'].id}&q=a",headers=headers(w["teacher"])).status_code==422
    assert client.get(f"/api/teach/students/search?school_id={w['b'].id}&q=al",headers=headers(w["teacher"])).status_code==403

def test_teacher_student_search_is_limited_and_searches_external_reference(db, client, world):
    w=world
    db.add_all([Student(school_id=w["a"].id,first_name=f"Limit{i:02d}",last_name="Student",external_ref=f"DUTY-{i:02d}",status="active") for i in range(35)]); db.commit()
    response=client.get(f"/api/teach/students/search?school_id={w['a'].id}&q=DUTY",headers=headers(w["teacher"])); assert response.status_code==200
    assert response.json()["limit"]==30 and len(response.json()["students"])==30
    names=[row["display_name"] for row in response.json()["students"]]; assert names==sorted(names, key=lambda value: value.lower())

def test_duty_award_outside_assignments_rejects_inactive_category_and_is_guardian_scoped(db, client, world):
    w=world
    active=BehaviourCategory(school_id=w["a"].id,type="positive",label="Safe play",points_value=1,active=True)
    inactive=BehaviourCategory(school_id=w["a"].id,type="needs_work",label="Old rule",points_value=-1,active=False); db.add_all([active,inactive]); db.commit()
    # This teacher has no staff assignment at all: active same-school membership is sufficient for duty awards.
    result=client.post("/api/teach/behaviour/events",headers=headers(w["teacher"]),json={"school_id":w["a"].id,"student_ids":[w["s1"].id],"category_id":active.id}); assert result.status_code==201
    assert client.post("/api/teach/behaviour/events",headers=headers(w["teacher"]),json={"school_id":w["a"].id,"student_ids":[w["s1"].id],"category_id":inactive.id}).status_code==400
    linked=client.get("/api/guardian/points",headers=headers(w["guardian"])).json(); assert linked["children"][0]["recent_events"][0]["category_label"]=="Safe play"
    assert client.get("/api/guardian/points",headers=headers(w["outsider"])).json()=={"children":[]}

def test_assignment_context_is_authorized_roster_scoped_and_applied_to_batch(db, client, world):
    w=world; section, subject, group=add_assignment_context(db,w)
    category=BehaviourCategory(school_id=w["a"].id,type="positive",label="Focused",points_value=1,active=True); db.add(category); db.commit()
    subject_award=client.post("/api/teach/behaviour/events",headers=headers(w["teacher"]),json={"school_id":w["a"].id,"student_ids":[w["s1"].id],"category_id":category.id,"context_type":"subject","subject_group_id":group.id})
    assert subject_award.status_code==201
    event=db.query(BehaviourEvent).order_by(BehaviourEvent.id.desc()).first(); assert event.context_type=="subject" and event.subject_group_id==group.id and event.class_section_id is None
    subject_payload=client.get("/api/guardian/points",headers=headers(w["guardian"])).json()["children"][0]["recent_events"][0]
    assert subject_payload["subject_name"]==subject.name and subject_payload["subject_code"]==subject.code and subject_payload["class_section_name"]==section.name
    class_award=client.post("/api/teach/behaviour/events",headers=headers(w["teacher"]),json={"school_id":w["a"].id,"student_ids":[w["s1"].id],"category_id":category.id,"context_type":"class","class_section_id":section.id})
    assert class_award.status_code==201
    event=db.query(BehaviourEvent).order_by(BehaviourEvent.id.desc()).first(); assert event.context_type=="class" and event.class_section_id==section.id and event.subject_group_id is None
    class_payload=client.get("/api/guardian/points",headers=headers(w["guardian"])).json()["children"][0]["recent_events"][0]
    assert class_payload["class_section_name"]==section.name and class_payload["subject_name"] is None and class_payload["subject_code"] is None
    for target in ({"context_type":"class","class_section_id":section.id},{"context_type":"subject","subject_group_id":group.id}):
        response=client.post("/api/teach/behaviour/events",headers=headers(w["teacher"]),json={"school_id":w["a"].id,"student_ids":[w["s1"].id,w["s2"].id],"category_id":category.id,**target})
        assert response.status_code==400
    db.add(Enrolment(school_id=w["a"].id, student_id=w["s2"].id, class_section_id=section.id, kind="member")); db.commit()
    batch=client.post("/api/teach/behaviour/events",headers=headers(w["teacher"]),json={"school_id":w["a"].id,"student_ids":[w["s1"].id,w["s2"].id],"category_id":category.id,"context_type":"subject","subject_group_id":group.id})
    assert batch.status_code==201 and batch.json()["created"]==2
    batch_ids={row["id"] for row in batch.json()["events"]}
    batch_events=db.query(BehaviourEvent).filter(BehaviourEvent.id.in_(batch_ids)).all()
    assert len(batch_events)==2 and all(row.context_type=="subject" and row.subject_group_id==group.id for row in batch_events)

def test_context_api_rejects_invalid_combinations_targets_and_duty_values(db, client, world):
    w=world; section, _, group=add_assignment_context(db,w)
    category=BehaviourCategory(school_id=w["a"].id,type="positive",label="Context",points_value=1,active=True); db.add(category); db.commit()
    unassigned=ClassSection(school_id=w["a"].id,branch_campus_id=section.branch_campus_id,academic_year_id=section.academic_year_id,grade_level_id=section.grade_level_id,code="B",name="Grade 1 B",status="active")
    foreign=ClassSection(school_id=w["b"].id,branch_campus_id=section.branch_campus_id,academic_year_id=section.academic_year_id,grade_level_id=section.grade_level_id,code="X",name="Foreign",status="active")
    db.add_all([unassigned,foreign]); db.commit()
    invalid=[
        {"context_type":"unknown"},
        {"context_type":"duty","duty_context":"cafeteria"},
        {"context_type":"duty","duty_context":"break","class_section_id":section.id},
        {"context_type":"subject","subject_group_id":group.id,"duty_context":"break"},
        {"context_type":"class"},
        {"context_type":"general","class_section_id":section.id},
    ]
    for context in invalid:
        response=client.post("/api/teach/behaviour/events",headers=headers(w["teacher"]),json={"school_id":w["a"].id,"student_ids":[w["s1"].id],"category_id":category.id,**context})
        assert response.status_code in {400,422}
    for target in (unassigned,foreign):
        response=client.post("/api/teach/behaviour/events",headers=headers(w["teacher"]),json={"school_id":w["a"].id,"student_ids":[w["s1"].id],"category_id":category.id,"context_type":"class","class_section_id":target.id})
        assert response.status_code in {400,403}

def test_duty_context_persists_and_guardian_payload_is_closed_world(db, client, world):
    w=world; category=BehaviourCategory(school_id=w["a"].id,type="needs_work",label="Wandering",points_value=-1,active=True); db.add(category); db.commit()
    response=client.post("/api/teach/behaviour/events",headers=headers(w["teacher"]),json={"school_id":w["a"].id,"student_ids":[w["s1"].id],"category_id":category.id,"context_type":"duty","duty_context":"hallway"})
    assert response.status_code==201
    event=db.query(BehaviourEvent).one(); assert event.context_type=="duty" and event.duty_context=="hallway"
    payload=client.get("/api/guardian/points",headers=headers(w["guardian"])).json()["children"][0]["recent_events"][0]
    assert payload["context_type"]=="duty" and payload["duty_context"]=="hallway"
    assert payload["subject_name"] is None and payload["subject_code"] is None and payload["class_section_name"] is None
    for forbidden in ("actor_user_id","staff_id","email","subject_group_id","subject_id","class_section_id","token","hash","storage_key","path"):
        assert forbidden not in payload

def test_database_rejects_invalid_context_combinations(db, world):
    w=world; category=BehaviourCategory(school_id=w["a"].id,type="positive",label="DB check",points_value=1,active=True); db.add(category); db.flush()
    db.add(BehaviourEvent(school_id=w["a"].id,student_id=w["s1"].id,category_id=category.id,actor_user_id=w["teacher"].id,points_delta=1,source="teacher",context_type="duty",duty_context="invalid"))
    with pytest.raises(IntegrityError): db.commit()
    db.rollback()
