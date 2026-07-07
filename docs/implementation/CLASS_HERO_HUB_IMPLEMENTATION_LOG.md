# Class Hero Hub Implementation Log

## 2026-07-07

Branch: `main`

Commit at start of slice: `5c63ea4`

Task/prompt completed: Identity/tenancy foundation. The prompt was not explicitly numbered; logged as the first implementation slice for the Class Hero Hub identity foundation.

## Files Changed

- `backend/app/models_school/__init__.py`
- `backend/app/models_school/models.py`
- `backend/app/school_scope.py`
- `alembic/versions/c1a2b3d4e5f6_add_school_identity_tenancy.py`
- `backend/tests/conftest.py`
- `backend/tests/school_fixtures.py`
- `backend/tests/test_identity_models.py`
- `docs/implementation/CLASS_HERO_HUB_IMPLEMENTATION_LOG.md`

Existing files intentionally not modified:

- `backend/app/models.py`
- `backend/app/auth.py`
- `backend/app/main.py`
- Route files
- Frontend files
- Docker, Caddy, and environment files
- Product requirements docs

## Models, Tables, and Migrations Added

New model package:

- `backend/app/models_school/`

New SQLAlchemy models:

- `User`
- `School`
- `Membership`
- `PlatformAdmin`
- `AuditLog`

New Alembic revision:

- `c1a2b3d4e5f6_add_school_identity_tenancy.py`
- `down_revision = "7c2b9f1a0d4e"`

Tables created by the migration:

- `users`
- `schools`
- `memberships`
- `platform_admins`
- `audit_logs`

Constraints and indexes added:

- `users.email` unique indexed
- `users.google_sub` unique indexed and nullable
- `schools.slug` unique indexed
- `platform_admins.user_id` unique
- `memberships` unique constraint on `(school_id, user_id, role)` named `uq_memberships_school_user_role`
- Primary-key indexes following the existing model idiom where `id = Column(..., index=True)`
- Foreign keys among the new identity tables only

Audit behavior:

- `AuditLog` is append-only at ORM level via a SQLAlchemy `before_update` listener that raises `ValueError`.
- No database trigger was added.

## Tests Added or Changed

Added:

- `backend/tests/conftest.py`
- `backend/tests/school_fixtures.py`
- `backend/tests/test_identity_models.py`

Test coverage added:

- Unique user email constraint
- Unique `(school_id, user_id, role)` membership constraint
- `write_audit(...)` row creation
- Seed fixture integrity for two schools, school admins, teachers, memberships, and one platform admin

No existing tests were modified.

Follow-up fix after Docker test failure:

- Removed `backend/tests/conftest_school.py`.
- Added `backend/tests/school_fixtures.py` for school-only fixtures.
- Added `backend/tests/conftest.py` to force `DATABASE_URL=sqlite://`, `APP_ENV=test`, and `DEV_AUTH_ENABLED=false` before any test imports `app.database`.
- Updated `backend/tests/test_identity_models.py` to import `seeded_schools` from `school_fixtures`.

## Commands Run and Exact Results

Context-read commands:

```bash
sed -n '1,260p' backend/app/models.py
sed -n '1,220p' backend/app/database.py
find alembic/versions -maxdepth 1 -type f -name '*.py' | sort | tail -20 | xargs -r -n1 basename
sed -n '1,260p' backend/tests/test_parent_auth_session.py
sed -n '220,520p' backend/app/database.py
find backend/tests -maxdepth 1 -type f -name 'conftest*.py' -print -exec sed -n '1,240p' {} \;
sed -n '1,220p' alembic/env.py
for f in alembic/versions/*.py; do printf '%s\n' "$f"; sed -n '1,180p' "$f"; done
rg "Base.metadata.create_all|DATABASE_URL|APP_ENV|from app import|import app" backend/tests -n
rg "JSON|MutableDict|write_audit|IntegrityError" backend/app backend/tests -n
ls -la backend/app backend/tests alembic/versions
```

Result: completed successfully and confirmed the existing timestamp/status idioms, per-test SQLite setup pattern, Alembic head revision, and absence of a global `backend/tests/conftest.py`.

Git/context commands:

```bash
git branch --show-current
```

Exact output:

```text
main
```

```bash
git rev-parse --short HEAD
```

Exact output:

```text
5c63ea4
```

```bash
git status --short
```

Exact output before this log was added:

```text
?? alembic/versions/c1a2b3d4e5f6_add_school_identity_tenancy.py
?? backend/app/models_school/
?? backend/app/school_scope.py
?? backend/tests/conftest_school.py
?? backend/tests/test_identity_models.py
?? docs/CLASS_HERO_HUB_MASTER_BLUEPRINT.md
?? docs/audits/
```

Verification commands:

```bash
python -m pytest tests/test_identity_models.py -q
```

Exact output:

```text
/bin/bash: line 1: python: command not found
```

```bash
python3 -m pytest tests/test_identity_models.py -q
```

Exact output:

```text
/usr/bin/python3: No module named pytest
```

```bash
cd backend && python -m pytest tests -q
```

Exact output:

```text
/bin/bash: line 1: python: command not found
```

```bash
python3 -m py_compile backend/app/models_school/__init__.py backend/app/models_school/models.py backend/app/school_scope.py backend/tests/conftest_school.py backend/tests/test_identity_models.py alembic/versions/c1a2b3d4e5f6_add_school_identity_tenancy.py
```

Exact output:

```text
```

Result: exit code `0`.

Docker verification after rebuilding the backend image:

```bash
docker compose build backend
```

Result: exit code `0`; backend image rebuilt and copied the new source files.

```bash
docker compose up -d backend
```

Exact output:

```text
 Container family-hero-hub-backend  Recreate
 Container family-hero-hub-backend  Recreated
 Container family-hero-hub-backend  Starting
 Container family-hero-hub-backend  Started
```

```bash
docker compose exec backend python -m pytest --collect-only -q tests | tail -20
```

Relevant exact output:

```text
224 tests collected in 2.82s
```

```bash
docker compose exec backend python -m pytest tests -q
```

Exact result:

```text
224 passed, 204 warnings in 25.76s
```

Alembic checks:

```bash
docker compose exec backend alembic heads
```

Exact output:

```text
FAILED: No 'script_location' key found in configuration.
```

Reason: the running backend image workdir is `/app` and contains only the backend build context; repo-root `alembic.ini` is not present there.

```bash
docker compose run --rm -v /opt/apps/class_hero_hub:/workspace -w /workspace backend alembic heads
```

Exact output:

```text
c1a2b3d4e5f6 (head)
```

```bash
docker compose run --rm -v /opt/apps/class_hero_hub:/workspace -w /workspace backend alembic current
```

Exact output:

```text
INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
INFO  [alembic.runtime.migration] Will assume transactional DDL.
```

Observation: no current revision was printed for the configured live Postgres database.

```bash
docker compose run --rm -v /opt/apps/class_hero_hub:/workspace -w /workspace backend alembic upgrade head
```

Relevant exact failure:

```text
INFO  [alembic.runtime.migration] Running upgrade  -> 5fd2ed5269af, initial schema
psycopg.errors.DuplicateTable: relation "families" already exists
```

Reason: the configured live Postgres database has existing tables but no Alembic revision marker, so Alembic attempted to replay the initial schema.

Temporary Postgres migration validation:

```bash
tmpdb="class_hero_hub_migration_check_$(date +%s)"; echo "$tmpdb"; docker compose exec postgres createdb -U classhero "$tmpdb" && docker compose run --rm -e MIGRATION_DATABASE_URL="postgresql+psycopg://classhero:499337c5a3f9754b2eab74ab99c3a4bf93c6a6608c374c13380881a159fb30e8@postgres:5432/$tmpdb" -v /opt/apps/class_hero_hub:/workspace -w /workspace backend alembic upgrade head; status=$?; docker compose exec postgres dropdb -U classhero --if-exists "$tmpdb"; exit $status
```

Exact output:

```text
class_hero_hub_migration_check_1783403763
INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
INFO  [alembic.runtime.migration] Will assume transactional DDL.
INFO  [alembic.runtime.migration] Running upgrade  -> 5fd2ed5269af, initial schema
INFO  [alembic.runtime.migration] Running upgrade 5fd2ed5269af -> bf3d4a8c2e91, add child allowance settings
INFO  [alembic.runtime.migration] Running upgrade bf3d4a8c2e91 -> 9b0b6e5ad4d2, add allowance enabled at
INFO  [alembic.runtime.migration] Running upgrade 9b0b6e5ad4d2 -> 2f3c4d5e6a7b, add ledger source transaction
INFO  [alembic.runtime.migration] Running upgrade 2f3c4d5e6a7b -> 3a7e1c9d4b52, add school item checks (B2 pack-for-tomorrow checklist)
INFO  [alembic.runtime.migration] Running upgrade 3a7e1c9d4b52 -> 7c2b9f1a0d4e, add ledger idempotency constraints
INFO  [alembic.runtime.migration] Running upgrade 7c2b9f1a0d4e -> c1a2b3d4e5f6, add school identity tenancy
```

Result: exit code `0`; temporary database was dropped after the check.

Cleanup command:

```bash
find backend/app/models_school backend/tests alembic/versions -type d -name __pycache__ -prune -exec rm -rf {} +
```

Exact output:

```text
```

Result: removed only generated Python bytecode cache directories from the syntax compile check.

Dependency check command:

```bash
python3 - <<'PY'
try:
    import sqlalchemy
    print(f"sqlalchemy {sqlalchemy.__version__}")
except Exception as exc:
    print(f"sqlalchemy import failed: {exc}")
try:
    import pytest
    print(f"pytest {pytest.__version__}")
except Exception as exc:
    print(f"pytest import failed: {exc}")
PY
```

Exact output:

```text
sqlalchemy import failed: No module named 'sqlalchemy'
pytest import failed: No module named 'pytest'
```

Final status command:

```bash
git status --short
```

Exact output:

```text
?? alembic/versions/c1a2b3d4e5f6_add_school_identity_tenancy.py
?? backend/app/models_school/
?? backend/app/school_scope.py
?? backend/tests/conftest_school.py
?? backend/tests/test_identity_models.py
?? docs/CLASS_HERO_HUB_MASTER_BLUEPRINT.md
?? docs/audits/
?? docs/implementation/
```

## Assumptions Made

- The new school identity tables should coexist with the existing family/parent tables and should not alter any existing table.
- The new `User` table is intentionally separate from the existing `ParentUser` table.
- Existing SQLAlchemy idioms in this codebase allow nullable string/status/timestamp columns unless the existing pattern explicitly marks them non-null.
- `AuditLog` append-only enforcement is acceptable at the ORM layer for this foundation slice; database-level triggers can be added later if required.
- `write_audit(...)` should commit and refresh the row, matching the simple helper style implied by the task.
- The school fixture should not be named `conftest_school.py`; it is now `school_fixtures.py`.
- A minimal global `backend/tests/conftest.py` is appropriate because Docker Compose sets `DEV_AUTH_ENABLED=true`, and pytest imports app modules during collection. The test suite needs deterministic test environment values before any `app.database` import.
- The untracked files `docs/CLASS_HERO_HUB_MASTER_BLUEPRINT.md` and `docs/audits/` pre-existed this slice and were not modified.

## Risks and Follow-Up Items

- Host pytest verification could not be completed because `python` is missing and `python3` does not have `sqlalchemy` or `pytest` installed. Docker is the correct test environment.
- Initial Docker run before the fix produced `6 failed, 214 passed`. The failures were unauthenticated route tests returning `404` instead of `401`, plus one `sqlite3.OperationalError: no such table: parent_users`.
- Root cause: Docker Compose provides `DEV_AUTH_ENABLED=true`; if `app.database` is imported before per-module test environment overrides run, `settings.DEV_AUTH_ENABLED` stays true. Unauthenticated requests then enter dev-auth fallback and behave like an authenticated dev parent, causing 404s for inaccessible records and querying an uninitialized in-memory DB in one case.
- Fix: added root test `conftest.py` to force test environment before app imports, and moved school-only fixture code out of `conftest_school.py` to avoid ambiguity around pytest fixture/config discovery.
- Alembic `env.py` imports `app.models` but not `app.models_school`; the explicit migration is complete, but future autogenerate runs may need `models_school` imported into Alembic metadata loading.
- `AuditLog` append-only behavior is not enforced against raw SQL updates.
- S1b route/auth integration is now implemented; `require_platform_admin` and `require_school_role` are no longer stubs.
- No service-layer validation exists yet for role names, school status values, or user status values.
- The live configured Postgres database has existing tables but no Alembic revision marker; direct `alembic upgrade head` against it fails before reaching the new migration. The migration path itself passed on a temporary Postgres database.

## Reviewer Notes for Claude

- Check whether the table names `users`, `schools`, `memberships`, `platform_admins`, and `audit_logs` match the intended naming contract for all future school tenancy work.
- Review whether `write_audit(...)` should commit internally or only add/flush within an existing transaction. Current implementation commits for deterministic helper behavior in this foundation slice.
- Decide whether `AuditLog` needs database-trigger enforcement before production use.
- Confirm whether Alembic `env.py` should import `app.models_school` in a later slice for autogenerate visibility. This was not changed because the task explicitly constrained existing-file modifications and requested one explicit migration.
- Confirm whether nullable defaults in the migration should be tightened in a later hardening migration. Current choices follow the existing generated migration style.

## Next Recommended Implementation Slice

Original S1b recommendation, now completed:

- Implement `require_platform_admin`.
- Implement `require_school_role`.
- Add request/session resolution for the new `User` identity model.
- Add focused tests for platform admin access, school admin access, teacher membership checks, suspended/revoked membership denial, and cross-school isolation.
- Add audit writes around the first school-admin management actions once routes exist.

Next recommended slice after S1b:

- Add first school-admin management routes using `require_platform_admin` and `require_school_role`.
- Decide whether school identity should get response schemas before broad route work.
- Add database-level audit immutability if append-only enforcement must cover raw SQL.

## 2026-07-07 S1b Auth Wiring

Branch: `main`

Commit at start of slice: `5c63ea4`

Task/prompt completed: S1b, wire school identity tables into auth while preserving existing household/parent auth.

## S1b Files Changed

- `backend/app/auth.py`
- `backend/app/routes/authentication.py`
- `backend/app/main.py`
- `backend/app/school_scope.py`
- `backend/app/database.py`
- `.env.example`
- `backend/tests/test_user_auth.py`
- `docs/implementation/CLASS_HERO_HUB_IMPLEMENTATION_LOG.md`

Existing household behavior intentionally preserved:

- `get_current_parent` remains in place and still powers existing household routes.
- `/api/me` remains unchanged.
- CSRF/session middleware was not changed.
- No frontend, Docker, Caddy, or environment deployment files were changed.

## S1b Implementation Notes

- Google OAuth callback now upserts a school-identity `User` row using normalized email, Google subject, name, and `last_login_at`.
- Added `get_current_user` in `auth.py`, resolving `access_token` cookie and `Authorization: Bearer` token the same way as parent auth.
- Added `PLATFORM_ADMIN_EMAILS` setting with default empty string.
- Added `PLATFORM_ADMIN_EMAILS=` to `.env.example`.
- Bootstrap platform admin creation is idempotent for active rows and writes an audit log with detail `{"source": "bootstrap"}`.
- Implemented `require_platform_admin` as a FastAPI dependency.
- Implemented `require_school_role(*roles)` as a FastAPI dependency.
- School context resolves from path param `school_id` first, then `X-School-Id` header.
- Suspended schools return `403` with detail `This school account is currently suspended.`
- Added `GET /api/me/v2`, returning `user`, `is_platform_admin`, and active memberships.

## S1b Tests Added

Added `backend/tests/test_user_auth.py` covering:

- Google callback upserts `User` and preserves existing `ParentUser` callback flow.
- Cookie auth resolves `User` for `/api/me/v2`.
- Bootstrap platform admin is created once and is idempotent.
- `require_platform_admin` returns `403` for normal users.
- `require_school_role` allows matching active membership.
- `require_school_role` accepts `X-School-Id`.
- `require_school_role` rejects inactive membership.
- `require_school_role` rejects wrong-school access.
- `require_school_role` rejects suspended school.

## S1b Commands Run and Exact Results

Targeted mounted-source test:

```bash
docker compose run --rm -v /opt/apps/class_hero_hub/backend:/app -w /app backend python -m pytest tests/test_user_auth.py -q
```

Exact result:

```text
9 passed, 38 warnings in 3.09s
```

Full mounted-source suite:

```bash
docker compose run --rm -v /opt/apps/class_hero_hub/backend:/app -w /app backend python -m pytest tests -q
```

Exact result:

```text
233 passed, 213 warnings in 27.00s
```

Backend image rebuild:

```bash
docker compose build backend
```

Result: exit code `0`.

Recreate backend and run exact Docker test command:

```bash
docker compose up -d backend && docker compose exec backend python -m pytest tests -q
```

Exact result:

```text
233 passed, 213 warnings in 27.30s
```

## S1b Assumptions

- `User` and `ParentUser` remain separate identities for now, linked only by matching normalized email.
- Bootstrap platform admin audit uses the created `PlatformAdmin` row as the audited entity because there is no `source` column on `platform_admins`.
- A revoked existing `PlatformAdmin` row for a bootstrap email is reactivated rather than duplicated because `platform_admins.user_id` is unique.

## S1b Risks and Follow-Up Items

- `get_current_user` has no school-specific status policy beyond `User.status == active`; future slices should define user suspension/revocation semantics.
- `require_school_role` currently returns generic `School role required` for wrong role and wrong school to avoid leaking memberships.
- `/api/me/v2` returns plain dictionaries rather than Pydantic schemas; consider adding schemas before public API expansion.
- Audit immutability remains ORM-level only.

## S1b Reviewer Notes for Claude

- Review whether bootstrap-reactivating a revoked `PlatformAdmin` is desired or whether revoked rows should block bootstrap.
- Review whether `get_current_user` should auto-create a `User` in dev-auth mode; this mirrors the parent dev fallback but may not be wanted long term.
- Review whether `write_audit` should commit internally before auth flows rely on larger transactional units.

## 2026-07-07 Household Domain Removal

Branch: `main`

Commit at start of slice: `5c63ea4`

Task/prompt completed: remove Family Hero Hub household backend domain after identity v2.

## Household Removal Files Changed

- Replaced `backend/app/main.py` with an identity-only app surface.
- Replaced `backend/app/auth.py` with User-only JWT/cookie auth plus CSRF helpers.
- Replaced `backend/app/routes/authentication.py` with User-only Google OAuth, `/auth/me`, and logout.
- Replaced `backend/app/routes/dev.py` with QA login that seeds `User` plus `PlatformAdmin`.
- Replaced `backend/app/schemas.py` with identity-only schemas.
- Replaced `backend/app/models.py` with a legacy marker module; household ORM classes removed.
- Added `backend/app/invite_tokens.py` with generic token generation/hash/cookie/exchange helpers and `BoundedInMemoryRateLimiter`.
- Added `alembic/versions/d4e5f6a7b8c9_drop_household_domain.py`.
- Deleted household routes, household services, `child_auth.py`, `currencies.py`, and `mailer.py`.
- Deleted household test files.
- Kept/adapted identity, QA login, CSRF, and security tests.

## Household Tables Dropped by Migration

- `school_item_checks`
- `calendar_task_completions`
- `weekly_streaks`
- `child_allowance_settings`
- `child_device_sessions`
- `child_device_invites`
- `ledger_transactions`
- `redemption_requests`
- `pet_progress`
- `school_items`
- `calendar_entries`
- `preset_behaviours`
- `rewards`
- `family_invites`
- `registration_requests`
- `approved_parent_emails`
- `children`
- `parent_users`
- `families`

## Household Removal Tests

Kept/adapted:

- `backend/tests/test_identity_models.py`
- `backend/tests/test_user_auth.py`
- `backend/tests/test_dev_qa_login.py`
- `backend/tests/test_csrf_http.py`
- `backend/tests/test_security_hardening.py`

Added/updated coverage:

- `/api/me` serves identity v2 payload.
- `/api/me/v2` remains available.
- QA login creates/reuses a `User` and active `PlatformAdmin`.
- CSRF protection still blocks unsafe cookie-authenticated requests without matching token.
- Representative household routes return `404`.
- Security hardening tests still pass.

## Household Removal Commands and Results

Mounted-source suite:

```bash
docker compose run --rm -v /opt/apps/class_hero_hub/backend:/app -w /app backend python -m pytest tests -q
```

Exact result:

```text
47 passed, 5 warnings in 2.15s
```

Final rebuilt-container suite:

```bash
docker compose build backend && docker compose up -d backend && docker compose exec backend python -m pytest tests -q
```

Exact result:

```text
47 passed, 5 warnings in 2.00s
```

Alembic head:

```bash
docker compose run --rm -v /opt/apps/class_hero_hub:/workspace -w /workspace backend alembic heads
```

Exact output:

```text
d4e5f6a7b8c9 (head)
```

Temporary Postgres migration validation:

```bash
tmpdb="class_hero_hub_household_drop_check_$(date +%s)"; echo "$tmpdb"; docker compose exec postgres createdb -U classhero "$tmpdb" && docker compose run --rm -e MIGRATION_DATABASE_URL="postgresql+psycopg://classhero:499337c5a3f9754b2eab74ab99c3a4bf93c6a6608c374c13380881a159fb30e8@postgres:5432/$tmpdb" -v /opt/apps/class_hero_hub:/workspace -w /workspace backend alembic upgrade head; status=$?; docker compose exec postgres dropdb -U classhero --if-exists "$tmpdb"; exit $status
```

Relevant output:

```text
INFO  [alembic.runtime.migration] Running upgrade c1a2b3d4e5f6 -> d4e5f6a7b8c9, drop household domain
```

Result: exit code `0`.

Uvicorn boot smoke:

```text
INFO:     Started server process [88]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
```

Endpoint smoke through rebuilt container/TestClient:

```text
/api/health 200 {"status":"ok"}
/api/me 401 {"detail":"Not authenticated"}
/api/children 404 {"detail":"Not Found"}
/api/auth/google/login 302 https://accounts.google.com/o/oauth2/v2/auth...
```

## Household Removal Risks and Follow-Up Items

- The configured live Postgres service still has existing tables but no Alembic revision marker from earlier project state. Direct live QA login against that DB failed with `relation "users" does not exist`. The migration path itself passed on a temporary Postgres DB; the live DB needs a deliberate migration/stamp plan before runtime QA login can mutate it.
- `invite_tokens.py` is generic and currently not wired to a route after child/family deletion; it is preserved for future invite flows.
- `database.py` still has QA child settings validation compatibility even though QA child login was removed, to avoid broad validation-logic churn in this slice.

## Live Development Database Reset to Alembic Head - 2026-07-07

Scope: reset only the running Class Hero Hub development/proof-of-concept PostgreSQL schema for Docker Compose project `class_hero_hub`.

Safety verification commands:

```bash
pwd
git remote -v
git status --short --branch
git status --porcelain=v1
docker compose config --format json
docker compose exec -T postgres psql -U classhero -d class_hero_hub -c "select current_database(), current_user;"
```

Verified:

```text
pwd: /opt/apps/class_hero_hub
origin: git@github.com:itsdominoman/class_hero_hub.git
git status --short --branch: ## main...origin/main [ahead 1]
git status --porcelain=v1: no output
docker compose config name: class_hero_hub
postgres POSTGRES_DB: class_hero_hub
psql current_database/current_user: class_hero_hub / classhero
```

Disposable backup:

```bash
backup_path="/tmp/class_hero_hub_before_reset_20260707T063542Z.sql"
docker compose exec -T postgres pg_dump -U classhero -d class_hero_hub --clean --if-exists > "$backup_path"
ls -lh "$backup_path"
wc -l "$backup_path"
```

Result:

```text
/tmp/class_hero_hub_before_reset_20260707T063542Z.sql
-rw-rw-r-- 1 administrator administrator 72K Jul  7 08:35 /tmp/class_hero_hub_before_reset_20260707T063542Z.sql
2248 /tmp/class_hero_hub_before_reset_20260707T063542Z.sql
```

Reset method:

```bash
docker compose stop backend
docker compose exec -T postgres psql -U classhero -d class_hero_hub -v ON_ERROR_STOP=1 -c 'DROP SCHEMA public CASCADE; CREATE SCHEMA public AUTHORIZATION classhero; GRANT ALL ON SCHEMA public TO classhero; GRANT ALL ON SCHEMA public TO public;'
```

Result: `public` schema in database `class_hero_hub` was dropped and recreated. The old copied household tables were removed from this database only.

Alembic upgrade:

```bash
docker compose run --rm -v /opt/apps/class_hero_hub:/workspace -w /workspace backend alembic upgrade head
```

Relevant output:

```text
INFO  [alembic.runtime.migration] Running upgrade  -> 5fd2ed5269af, initial schema
INFO  [alembic.runtime.migration] Running upgrade 7c2b9f1a0d4e -> c1a2b3d4e5f6, add school identity tenancy
INFO  [alembic.runtime.migration] Running upgrade c1a2b3d4e5f6 -> d4e5f6a7b8c9, drop household domain
```

Alembic verification:

```bash
docker compose run --rm -v /opt/apps/class_hero_hub:/workspace -w /workspace backend alembic current
docker compose run --rm -v /opt/apps/class_hero_hub:/workspace -w /workspace backend alembic heads
docker compose exec -T postgres psql -U classhero -d class_hero_hub -c "select version_num from alembic_version;"
docker compose exec -T postgres psql -U classhero -d class_hero_hub -c "select tablename from pg_tables where schemaname = 'public' order by tablename;"
```

Results:

```text
alembic current: d4e5f6a7b8c9 (head)
alembic heads: d4e5f6a7b8c9 (head)
alembic_version.version_num: d4e5f6a7b8c9
public tables: alembic_version, audit_logs, memberships, platform_admins, schools, users
```

Backend boot and health check:

```bash
docker compose up -d backend
docker compose ps backend
docker compose logs --since=30s backend
curl -i -sS http://127.0.0.1:8000/api/health
```

Results:

```text
backend status: Up
backend logs: Application startup complete; Uvicorn running on http://0.0.0.0:8000
/api/health: HTTP/1.1 200 OK
/api/health body: {"status":"ok"}
```

Dev QA login verification against reset DB:

```bash
docker compose run --rm \
  -e QA_LOGIN_ENABLED=true \
  -e QA_LOGIN_TOKEN=qa-reset-login-token-20260707 \
  -v /opt/apps/class_hero_hub/backend:/app \
  -w /app \
  backend python - <<'PY'
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)
response = client.post(
    "/api/dev/qa-login",
    headers={"Host": "127.0.0.1:8000"},
    json={"token": "qa-reset-login-token-20260707"},
)
print("qa-login", response.status_code, response.json())
assert response.status_code == 200
me_response = client.get("/api/me")
print("me", me_response.status_code, me_response.json())
assert me_response.status_code == 200
assert me_response.json()["is_platform_admin"] is True
PY
```

Result:

```text
qa-login 200 {'status': 'ok', 'email': 'qa-parent@dev.familyherohub.com', 'user_id': 1, 'is_platform_admin': True, 'reused': False}
me 200 {'user': {'id': 1, 'email': 'qa-parent@dev.familyherohub.com', 'name': 'QA Parent', 'locale': 'en'}, 'is_platform_admin': True, 'memberships': []}
```

Backend tests:

```bash
docker compose exec backend python -m pytest tests -q
```

Result:

```text
47 passed, 5 warnings in 2.06s
```
