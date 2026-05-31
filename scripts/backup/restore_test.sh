#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
ENV_FILE="${ENV_FILE:-${PROJECT_ROOT}/.env}"

if [[ -f "${ENV_FILE}" ]]; then
  set -a
  # shellcheck disable=SC1090
  source "${ENV_FILE}"
  set +a
fi

BACKUP_BASE_DIR="${BACKUP_BASE_DIR:-/root/backups/logos-backend}"
COMPOSE_DIR="${COMPOSE_DIR:-${PROJECT_ROOT}}"
DB_CONTAINER_SERVICE="${DB_CONTAINER_SERVICE:-db}"
MEDIA_VOLUME_NAME="${MEDIA_VOLUME_NAME:-logos_media_volume}"
RESTORE_TEST_DB_NAME="${RESTORE_TEST_DB_NAME:-logos_restore_test}"
RESTORE_TEST_DIR="${RESTORE_TEST_DIR:-/tmp/logos-restore-test}"

POSTGRES_DB="${POSTGRES_DB:-${DB_NAME:-}}"
POSTGRES_USER="${POSTGRES_USER:-${DB_USER:-}}"
POSTGRES_PASSWORD="${POSTGRES_PASSWORD:-${DB_PASSWORD:-}}"

required_vars=(
  "POSTGRES_DB"
  "POSTGRES_USER"
  "POSTGRES_PASSWORD"
)
for var_name in "${required_vars[@]}"; do
  if [[ -z "${!var_name:-}" ]]; then
    echo "Missing required variable: ${var_name}" >&2
    exit 1
  fi
done

backup_target="${1:-latest}"
if [[ "${backup_target}" == "latest" ]]; then
  latest_dir="$(find "${BACKUP_BASE_DIR}" -mindepth 1 -maxdepth 1 -type d | sort | tail -n1)"
  if [[ -z "${latest_dir}" ]]; then
    echo "No backup directory found in ${BACKUP_BASE_DIR}" >&2
    exit 1
  fi
  backup_dir="${latest_dir}"
else
  backup_dir="${BACKUP_BASE_DIR}/${backup_target}"
fi

if [[ ! -d "${backup_dir}" ]]; then
  echo "Backup directory not found: ${backup_dir}" >&2
  exit 1
fi

echo "$(date -Is) [INFO] Using backup set: ${backup_dir}"

db_dump_file="${backup_dir}/db.sql.gz"
media_archive_file="${backup_dir}/media.tar.gz"
checksums_file="${backup_dir}/checksums.sha256"

for f in "${db_dump_file}" "${media_archive_file}" "${checksums_file}"; do
  if [[ ! -f "${f}" ]]; then
    echo "Missing backup artifact: ${f}" >&2
    exit 1
  fi
done

echo "$(date -Is) [INFO] Verifying checksums..."
(cd "${backup_dir}" && sha256sum -c "$(basename "${checksums_file}")")

echo "$(date -Is) [INFO] Preparing restore test workspace..."
rm -rf "${RESTORE_TEST_DIR}"
mkdir -p "${RESTORE_TEST_DIR}/media"

echo "$(date -Is) [INFO] Recreating temporary database ${RESTORE_TEST_DB_NAME}..."
docker compose -f "${COMPOSE_DIR}/docker-compose.yml" exec -T \
  -e PGPASSWORD="${POSTGRES_PASSWORD}" \
  "${DB_CONTAINER_SERVICE}" \
  psql -U "${POSTGRES_USER}" -d postgres -v ON_ERROR_STOP=1 \
  -c "DROP DATABASE IF EXISTS ${RESTORE_TEST_DB_NAME};" \
  -c "CREATE DATABASE ${RESTORE_TEST_DB_NAME};"

echo "$(date -Is) [INFO] Restoring dump into ${RESTORE_TEST_DB_NAME}..."
gunzip -c "${db_dump_file}" | docker compose -f "${COMPOSE_DIR}/docker-compose.yml" exec -T \
  -e PGPASSWORD="${POSTGRES_PASSWORD}" \
  "${DB_CONTAINER_SERVICE}" \
  psql -U "${POSTGRES_USER}" -d "${RESTORE_TEST_DB_NAME}" -v ON_ERROR_STOP=1 >/dev/null

echo "$(date -Is) [INFO] Validating restored DB content..."
article_count="$(docker compose -f "${COMPOSE_DIR}/docker-compose.yml" exec -T \
  -e PGPASSWORD="${POSTGRES_PASSWORD}" \
  "${DB_CONTAINER_SERVICE}" \
  psql -U "${POSTGRES_USER}" -d "${RESTORE_TEST_DB_NAME}" -tAc "SELECT COUNT(*) FROM blog_article;")"

if [[ "${article_count}" -lt 1 ]]; then
  echo "Restore validation failed: no articles found in restored database." >&2
  exit 1
fi
echo "$(date -Is) [INFO] Restored article count: ${article_count}"

echo "$(date -Is) [INFO] Extracting media archive for validation..."
tar -xzf "${media_archive_file}" -C "${RESTORE_TEST_DIR}/media"
media_file_count="$(find "${RESTORE_TEST_DIR}/media" -type f | wc -l | tr -d ' ')"
echo "$(date -Is) [INFO] Restored media file count: ${media_file_count}"

if [[ "${media_file_count}" -lt 1 ]]; then
  echo "Restore validation failed: media archive contains no files." >&2
  exit 1
fi

echo "$(date -Is) [INFO] Cleanup test DB and temp files..."
docker compose -f "${COMPOSE_DIR}/docker-compose.yml" exec -T \
  -e PGPASSWORD="${POSTGRES_PASSWORD}" \
  "${DB_CONTAINER_SERVICE}" \
  psql -U "${POSTGRES_USER}" -d postgres -v ON_ERROR_STOP=1 \
  -c "DROP DATABASE IF EXISTS ${RESTORE_TEST_DB_NAME};" >/dev/null
rm -rf "${RESTORE_TEST_DIR}"

echo "$(date -Is) [INFO] Restore test completed successfully."
