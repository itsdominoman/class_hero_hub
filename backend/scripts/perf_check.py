"""Time the hot list/dashboard endpoints against whatever data is currently in the DB.

Usage (from repo root, against the running backend over the docker network):
  docker compose run --rm --no-deps -v $(pwd):/repo -w /repo backend python backend/scripts/perf_check.py

Override PERF_BASE_URL, PERF_ADMIN_EMAIL, PERF_TEACHER_EMAIL, PERF_SCHOOL_SLUG env vars
to point at a different school/backend. Read-only: only ever issues GET requests.
"""
from __future__ import annotations

import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

import httpx

from app import auth
from app.database import SessionLocal
from app.models_school import Membership, School, SubjectGroup, User

BASE_URL = os.environ.get("PERF_BASE_URL", "http://backend:8000")
ADMIN_EMAIL = os.environ.get("PERF_ADMIN_EMAIL", "dom@myeduzone.org")
TEACHER_EMAIL = os.environ.get("PERF_TEACHER_EMAIL", "domteacher@myeduzone.org")
SCHOOL_SLUG = os.environ.get("PERF_SCHOOL_SLUG", "united-international-school")

# Endpoints that scale with per-school data volume; flag anything over this.
SLOW_THRESHOLD_SECONDS = 1.0


def token_for(email: str) -> str:
    return auth.create_access_token({"sub": email})


def timed_get(client: httpx.Client, path: str, headers: dict[str, str]) -> tuple[int, float, int]:
    start = time.time()
    response = client.get(f"{BASE_URL}{path}", headers=headers, timeout=60)
    elapsed = time.time() - start
    count = len(response.json()) if response.status_code == 200 and isinstance(response.json(), list) else -1
    return response.status_code, elapsed, count


def main() -> None:
    db = SessionLocal()
    try:
        school = db.query(School).filter(School.slug == SCHOOL_SLUG).first()
        if school is None:
            print(f"No school with slug={SCHOOL_SLUG!r}; set PERF_SCHOOL_SLUG.")
            return
        admin_user = db.query(User).filter(User.email == ADMIN_EMAIL).first()
        teacher_user = db.query(User).filter(User.email == TEACHER_EMAIL).first()
        if admin_user is None:
            print(f"No user with email={ADMIN_EMAIL!r}; set PERF_ADMIN_EMAIL.")
            return
        subject_group_count = db.query(SubjectGroup).filter(SubjectGroup.school_id == school.id, SubjectGroup.status != "archived").count()
        teacher_membership = None
        if teacher_user is not None:
            teacher_membership = (
                db.query(Membership)
                .filter(Membership.school_id == school.id, Membership.user_id == teacher_user.id, Membership.role == "teacher")
                .first()
            )
    finally:
        db.close()

    admin_headers = {"Authorization": f"Bearer {token_for(ADMIN_EMAIL)}", "X-School-Id": str(school.id)}
    print(f"School: {school.name} (id={school.id}), {subject_group_count} active subject groups")
    print(f"Base URL: {BASE_URL}\n")

    admin_paths = [
        "/api/school/settings",
        "/api/school/setup-checklist",
        "/api/school/branches",
        "/api/school/education-stages",
        "/api/school/academic-years",
        "/api/school/grade-levels",
        "/api/school/class-sections",
        "/api/school/subjects",
        "/api/school/subject-groups",
        "/api/school/teachers",
        "/api/school/teachers/assignments",
        "/api/school/students",
    ]

    flagged = []
    with httpx.Client() as client:
        total = 0.0
        for path in admin_paths:
            status, elapsed, count = timed_get(client, path, admin_headers)
            total += elapsed
            marker = " <-- SLOW" if elapsed > SLOW_THRESHOLD_SECONDS else ""
            count_label = f", {count} rows" if count >= 0 else ""
            print(f"{status} {elapsed:6.3f}s  {path}{count_label}{marker}")
            if elapsed > SLOW_THRESHOLD_SECONDS:
                flagged.append((path, elapsed))
        print(f"\nAdmin /school page-load sequence total: {total:.3f}s")

        if teacher_membership is not None:
            teacher_headers = {"Authorization": f"Bearer {token_for(TEACHER_EMAIL)}"}
            status, elapsed, _ = timed_get(client, "/api/teach/dashboard", teacher_headers)
            print(f"\n{status} {elapsed:6.3f}s  /api/teach/dashboard")
            if elapsed > SLOW_THRESHOLD_SECONDS:
                flagged.append(("/api/teach/dashboard", elapsed))
        else:
            print(f"\nNo teacher membership for {TEACHER_EMAIL!r} at this school; skipping /api/teach/dashboard.")

    if flagged:
        print(f"\n{len(flagged)} endpoint(s) over the {SLOW_THRESHOLD_SECONDS}s guideline:")
        for path, elapsed in flagged:
            print(f"  {path}: {elapsed:.3f}s")
    else:
        print(f"\nAll endpoints under the {SLOW_THRESHOLD_SECONDS}s guideline.")


if __name__ == "__main__":
    main()
