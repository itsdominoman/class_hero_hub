#!/usr/bin/env bash
set -Eeuo pipefail

readonly REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
readonly LIVE_CONTAINER="${POSTGRES_CONTAINER_NAME:-family-hero-hub-postgres}"
readonly STANZA="${PGBACKREST_STANZA:-fhh}"
readonly RESTORE_REPO="${RESTORE_REPOSITORY:-2}"
readonly APP_SLUG="class-hero-hub"
readonly SECRET_DIR="${BACKUP_SECRET_DIR:-/home/administrator/.config/${APP_SLUG}/backup-ssh}"
readonly STATUS_DIR="${BACKUP_STATUS_DIR:-${REPO_ROOT}/tmp/backup-status}"
readonly LOCK_FILE="${STATUS_DIR}/restore.lock"

restore_container=""
restore_volume=""
restore_network=""

cleanup() {
  local exit_code="$?"
  if [[ -n "$restore_container" ]]; then
    docker rm --force "$restore_container" >/dev/null 2>&1 || true
  fi
  if [[ -n "$restore_volume" ]]; then
    docker volume rm "$restore_volume" >/dev/null 2>&1 || true
  fi
  if [[ -n "$restore_network" ]]; then
    docker network rm "$restore_network" >/dev/null 2>&1 || true
  fi
  exit "$exit_code"
}
trap cleanup EXIT

main() {
  local suffix image backup_label db_name db_user deadline
  local revision public_tables total_rows nonempty_tables max_table_rows
  local system_identifier temp_file
  mkdir -p "$STATUS_DIR"
  exec 9>"$LOCK_FILE"
  flock -n 9 || { printf '%s\n' 'A restore rehearsal is already running.' >&2; return 75; }

  [[ "$RESTORE_REPO" == 1 || "$RESTORE_REPO" == 2 ]]
  [[ -r "${REPO_ROOT}/.env.backup" ]]
  [[ -d "$SECRET_DIR" ]]
  docker inspect "$LIVE_CONTAINER" >/dev/null
  image="$(docker inspect "$LIVE_CONTAINER" --format '{{.Image}}')"
  db_name="$(docker inspect "$LIVE_CONTAINER" --format '{{range .Config.Env}}{{println .}}{{end}}' | sed -n 's/^POSTGRES_DB=//p' | head -n 1)"
  db_user="$(docker inspect "$LIVE_CONTAINER" --format '{{range .Config.Env}}{{println .}}{{end}}' | sed -n 's/^POSTGRES_USER=//p' | head -n 1)"
  [[ -n "$image" && -n "$db_name" && -n "$db_user" ]]

  backup_label="$(docker exec --user postgres "$LIVE_CONTAINER" \
    pgbackrest --stanza="$STANZA" --repo="$RESTORE_REPO" info --output=json \
    | jq -r '.[0].backup[-1].label // empty')"
  [[ -n "$backup_label" ]]

  suffix="$(date +%s)-$$"
  restore_volume="${APP_SLUG}-restore-${suffix}"
  restore_container="${APP_SLUG}-restore-${suffix}"
  restore_network="${APP_SLUG}-restore-${suffix}"
  docker volume create "$restore_volume" >/dev/null
  docker network create "$restore_network" >/dev/null
  docker run --rm --entrypoint sh -v "${restore_volume}:/restore" "$image" \
    -c 'chown -R postgres:postgres /restore'

  docker run --rm --user postgres \
    --env-file "${REPO_ROOT}/.env.backup" \
    --entrypoint pgbackrest \
    -v "${restore_volume}:/var/lib/postgresql/data" \
    -v "${REPO_ROOT}/postgres/pgbackrest.conf:/etc/pgbackrest/pgbackrest.conf:ro" \
    -v "${SECRET_DIR}:/run/secrets/backup-ssh:ro" \
    "$image" --stanza="$STANZA" --repo="$RESTORE_REPO" --set="$backup_label" restore

  docker run --detach --name "$restore_container" --network "$restore_network" \
    --env-file "${REPO_ROOT}/.env" \
    --env-file "${REPO_ROOT}/.env.backup" \
    -v "${restore_volume}:/var/lib/postgresql/data" \
    -v "${REPO_ROOT}/postgres/pgbackrest.conf:/etc/pgbackrest/pgbackrest.conf:ro" \
    -v "${SECRET_DIR}:/run/secrets/backup-ssh:ro" \
    "$image" postgres -c archive_mode=off -c listen_addresses='' >/dev/null

  deadline=$((SECONDS + 60))
  until docker exec "$restore_container" pg_isready -U "$db_user" -d "$db_name" >/dev/null 2>&1; do
    (( SECONDS < deadline )) || { docker logs --tail 30 "$restore_container" >&2; return 1; }
    sleep 1
  done
  deadline=$((SECONDS + 120))
  until [[ "$(docker exec --user postgres "$restore_container" \
    psql -X -v ON_ERROR_STOP=1 -U "$db_user" -d "$db_name" -Atqc \
    "SELECT NOT pg_is_in_recovery() AND current_setting('transaction_read_only') = 'off'" \
    2>/dev/null || true)" == t ]]; do
    (( SECONDS < deadline )) || { docker logs --tail 30 "$restore_container" >&2; return 1; }
    sleep 1
  done

  revision="$(docker exec --user postgres "$restore_container" \
    psql -X -v ON_ERROR_STOP=1 -U "$db_user" -d "$db_name" -Atqc \
    'SELECT version_num FROM alembic_version')"
  read -r public_tables total_rows nonempty_tables max_table_rows < <(
    docker exec --interactive --user postgres "$restore_container" \
      psql -X -v ON_ERROR_STOP=1 -U "$db_user" -d "$db_name" -AtqF ' ' <<'SQL'
CREATE TEMP TABLE ops001_counts (row_count bigint NOT NULL);
DO $$
DECLARE table_ref record;
BEGIN
  FOR table_ref IN
    SELECT schemaname, tablename
    FROM pg_tables
    WHERE schemaname = 'public'
  LOOP
    EXECUTE format(
      'INSERT INTO ops001_counts SELECT count(*) FROM %I.%I',
      table_ref.schemaname,
      table_ref.tablename
    );
  END LOOP;
END
$$;
SELECT count(*), COALESCE(sum(row_count), 0),
       count(*) FILTER (WHERE row_count > 0), COALESCE(max(row_count), 0)
FROM ops001_counts;
SQL
  )
  system_identifier="$(docker exec --user postgres "$restore_container" \
    psql -X -v ON_ERROR_STOP=1 -U "$db_user" -d "$db_name" -Atqc \
    'SELECT system_identifier FROM pg_control_system()')"
  [[ -n "$revision" && "$public_tables" =~ ^[0-9]+$ && "$total_rows" =~ ^[0-9]+$ ]]

  temp_file="$(mktemp "${STATUS_DIR}/restore.json.XXXXXX")"
  jq -n \
    --arg timestamp "$(date --iso-8601=seconds)" \
    --argjson repository "$RESTORE_REPO" \
    --arg backup_label "$backup_label" \
    --arg alembic_revision "$revision" \
    --arg system_identifier "$system_identifier" \
    --argjson public_tables "$public_tables" \
    --argjson total_rows "$total_rows" \
    --argjson nonempty_tables "$nonempty_tables" \
    --argjson max_table_rows "$max_table_rows" \
    '{state:"ok", timestamp:$timestamp, source_repository:$repository,
      backup_label:$backup_label, database_opened:true,
      alembic_revision:$alembic_revision,
      metadata:{public_tables:$public_tables, aggregate_rows:$total_rows,
        nonempty_tables:$nonempty_tables, largest_table_rows:$max_table_rows},
      restored_system_identifier:$system_identifier,
      isolated:true, cleanup:"automatic"}' >"$temp_file"
  mv -f "$temp_file" "${STATUS_DIR}/restore.json"
  chmod 0644 "${STATUS_DIR}/restore.json"
  cat "${STATUS_DIR}/restore.json"
}

main "$@"
