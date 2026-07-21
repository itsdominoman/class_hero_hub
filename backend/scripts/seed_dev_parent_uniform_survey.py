"""Create the small UIS development survey used for pre-pilot verification.

Dry-run by default. The survey is always a draft, so this script never sends
notifications or accepts responses. It is idempotent by school and title.
"""
from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.database import SessionLocal
from app.models_school import (
    FhhLink,
    School,
    SchoolSystemOwner,
    Student,
    Survey,
    SurveyOption,
    SurveyQuestion,
    SurveyTarget,
)


TITLE = "Parent feedback on school uniforms"
SCHOOL_SLUG = "united-international-school"
UTC = timezone.utc


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true", help="commit the development-only draft")
    args = parser.parse_args()
    environment = (os.getenv("APP_ENV") or os.getenv("ENVIRONMENT") or "").lower()
    if environment in {"production", "prod"}:
        raise SystemExit("Refusing to seed a development survey in production")

    db = SessionLocal()
    try:
        school = db.query(School).filter(School.slug == SCHOOL_SLUG).one()
        existing = db.query(Survey).filter(Survey.school_id == school.id, Survey.title == TITLE).first()
        if existing is not None:
            print(f"existing draft: {existing.public_id}")
            return 0
        owner = db.query(SchoolSystemOwner).filter(SchoolSystemOwner.school_id == school.id).one()
        students = (
            db.query(Student)
            .join(FhhLink, FhhLink.student_id == Student.id)
            .filter(
                Student.school_id == school.id,
                Student.status == "active",
                FhhLink.status == "active",
                FhhLink.revoked_at.is_(None),
            )
            .distinct()
            .order_by(Student.id)
            .limit(3)
            .all()
        )
        if not students:
            raise SystemExit("UIS has no active FHH-linked test families")

        now = datetime.now(UTC)
        survey = Survey(
            school_id=school.id,
            title=TITLE,
            introduction="A clearly marked development survey for testing the pre-pilot parent feedback workflow.",
            instructions="Development test only. Please use sample answers and avoid personal information.",
            audience_type="selected_families",
            anonymous=True,
            response_mode="household",
            opens_at=now + timedelta(days=1),
            closes_at=now + timedelta(days=8),
            parent_results_visible=True,
            push_enabled=True,
            dashboard_card_enabled=True,
            notices_feed_enabled=True,
            status="draft",
            created_by_membership_id=owner.membership_id,
        )
        db.add(survey)
        db.flush()
        for student in students:
            db.add(SurveyTarget(survey_id=survey.id, target_type="student", target_id=student.id))

        questions = [
            SurveyQuestion(survey_id=survey.id, question_type="single_choice", prompt="Which uniform item should be reviewed first?", required=True, sort_order=0),
            SurveyQuestion(survey_id=survey.id, question_type="rating", prompt="How satisfied are you with the current uniform?", required=True, sort_order=1, scale_min=1, scale_max=5),
            SurveyQuestion(survey_id=survey.id, question_type="long_text", prompt="What one practical improvement would you suggest?", required=False, sort_order=2),
        ]
        db.add_all(questions)
        db.flush()
        for order, label in enumerate(("Shirt / blouse", "Trousers / skirt", "PE kit", "Outerwear")):
            db.add(SurveyOption(question_id=questions[0].id, label=label, sort_order=order))

        if args.apply:
            db.commit()
            db.refresh(survey)
            print(f"created draft: {survey.public_id}; selected families: {len(students)}")
        else:
            db.rollback()
            print(f"dry run: would create UIS draft for {len(students)} selected linked families")
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
