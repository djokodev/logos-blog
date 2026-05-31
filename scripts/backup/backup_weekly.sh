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
BACKUP_RETENTION_WEEKS="${BACKUP_RETENTION_WEEKS:-12}"
BACKUP_LOG_FILE="${BACKUP_LOG_FILE:-/var/log/logos-backup.log}"
BACKUP_LOCK_FILE="${BACKUP_LOCK_FILE:-/var/lock/logos-backup.lock}"
R2_PREFIX="${R2_PREFIX:-prod/weekly}"
COMPOSE_DIR="${COMPOSE_DIR:-${PROJECT_ROOT}}"
DB_CONTAINER_SERVICE="${DB_CONTAINER_SERVICE:-db}"
MEDIA_VOLUME_NAME="${MEDIA_VOLUME_NAME:-logos_media_volume}"

POSTGRES_DB="${POSTGRES_DB:-${DB_NAME:-}}"
POSTGRES_USER="${POSTGRES_USER:-${DB_USER:-}}"
POSTGRES_PASSWORD="${POSTGRES_PASSWORD:-${DB_PASSWORD:-}}"

required_vars=(
  "POSTGRES_DB"
  "POSTGRES_USER"
  "POSTGRES_PASSWORD"
  "R2_BUCKET_NAME"
  "R2_ENDPOINT"
  "R2_ACCESS_KEY_ID"
  "R2_SECRET_ACCESS_KEY"
)
for var_name in "${required_vars[@]}"; do
  if [[ -z "${!var_name:-}" ]]; then
    echo "Missing required variable: ${var_name}" >&2
    exit 1
  fi
done

if ! command -v aws >/dev/null 2>&1; then
  echo "aws CLI is required on VPS (command not found)." >&2
  exit 1
fi

mkdir -p "$(dirname "${BACKUP_LOG_FILE}")"
touch "${BACKUP_LOG_FILE}"
exec > >(tee -a "${BACKUP_LOG_FILE}") 2>&1

if command -v flock >/dev/null 2>&1; then
  mkdir -p "$(dirname "${BACKUP_LOCK_FILE}")"
  exec 9>"${BACKUP_LOCK_FILE}"
  if ! flock -n 9; then
    echo "$(date -Is) [WARN] Backup already running, exiting."
    exit 1
  fi
fi

timestamp="$(date +%F_%H%M)"
backup_dir="${BACKUP_BASE_DIR}/${timestamp}"
mkdir -p "${backup_dir}"

echo "$(date -Is) [INFO] Starting weekly backup in ${backup_dir}"

db_dump_file="${backup_dir}/db.sql.gz"
media_archive_file="${backup_dir}/media.tar.gz"
manifest_file="${backup_dir}/manifest.json"
checksums_file="${backup_dir}/checksums.sha256"

echo "$(date -Is) [INFO] Dumping PostgreSQL database..."
docker compose -f "${COMPOSE_DIR}/docker-compose.yml" exec -T \
  -e PGPASSWORD="${POSTGRES_PASSWORD}" \
  "${DB_CONTAINER_SERVICE}" \
  pg_dump -U "${POSTGRES_USER}" -d "${POSTGRES_DB}" --no-owner --no-privileges \
  | gzip -9 > "${db_dump_file}"

echo "$(date -Is) [INFO] Archiving media volume ${MEDIA_VOLUME_NAME}..."
docker run --rm \
  -v "${MEDIA_VOLUME_NAME}:/data:ro" \
  -v "${backup_dir}:/backup" \
  alpine:3.20 \
  sh -c 'tar -czf /backup/media.tar.gz -C /data .'

echo "$(date -Is) [INFO] Generating checksums and manifest..."
(
  cd "${backup_dir}"
  sha256sum db.sql.gz media.tar.gz > "${checksums_file##*/}"
)

cat > "${manifest_file}" <<EOF
{
  "created_at": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "timestamp": "${timestamp}",
  "project": "logos-backend",
  "database": "${POSTGRES_DB}",
  "db_dump_file": "$(basename "${db_dump_file}")",
  "media_archive_file": "$(basename "${media_archive_file}")",
  "checksums_file": "$(basename "${checksums_file}")"
}
EOF

echo "$(date -Is) [INFO] Uploading backup set to R2 bucket ${R2_BUCKET_NAME}..."
AWS_ACCESS_KEY_ID="${R2_ACCESS_KEY_ID}" \
AWS_SECRET_ACCESS_KEY="${R2_SECRET_ACCESS_KEY}" \
AWS_DEFAULT_REGION="auto" \
aws s3 cp "${backup_dir}/" "s3://${R2_BUCKET_NAME}/${R2_PREFIX}/${timestamp}/" \
  --recursive \
  --endpoint-url "${R2_ENDPOINT}" \
  --only-show-errors

echo "$(date -Is) [INFO] Applying local retention (keep ${BACKUP_RETENTION_WEEKS} backups)..."
if [[ -d "${BACKUP_BASE_DIR}" ]]; then
  mapfile -t local_dirs < <(find "${BACKUP_BASE_DIR}" -mindepth 1 -maxdepth 1 -type d -printf "%f\n" | sort)
  if (( ${#local_dirs[@]} > BACKUP_RETENTION_WEEKS )); then
    delete_count=$(( ${#local_dirs[@]} - BACKUP_RETENTION_WEEKS ))
    for old_dir in "${local_dirs[@]:0:delete_count}"; do
      rm -rf "${BACKUP_BASE_DIR:?}/${old_dir}"
      echo "$(date -Is) [INFO] Deleted local backup ${old_dir}"
    done
  fi
fi

echo "$(date -Is) [INFO] Applying R2 retention (keep ${BACKUP_RETENTION_WEEKS} backups)..."
prefixes_raw="$(
  AWS_ACCESS_KEY_ID="${R2_ACCESS_KEY_ID}" \
  AWS_SECRET_ACCESS_KEY="${R2_SECRET_ACCESS_KEY}" \
  AWS_DEFAULT_REGION="auto" \
  aws s3api list-objects-v2 \
    --bucket "${R2_BUCKET_NAME}" \
    --prefix "${R2_PREFIX}/" \
    --delimiter "/" \
    --query 'CommonPrefixes[].Prefix' \
    --output text \
    --endpoint-url "${R2_ENDPOINT}" 2>/dev/null || true
)"

if [[ -n "${prefixes_raw}" ]]; then
  mapfile -t r2_prefixes < <(tr '\t' '\n' <<< "${prefixes_raw}" | sed '/^\s*$/d' | sort)
  if (( ${#r2_prefixes[@]} > BACKUP_RETENTION_WEEKS )); then
    delete_count=$(( ${#r2_prefixes[@]} - BACKUP_RETENTION_WEEKS ))
    for old_prefix in "${r2_prefixes[@]:0:delete_count}"; do
      AWS_ACCESS_KEY_ID="${R2_ACCESS_KEY_ID}" \
      AWS_SECRET_ACCESS_KEY="${R2_SECRET_ACCESS_KEY}" \
      AWS_DEFAULT_REGION="auto" \
      aws s3 rm "s3://${R2_BUCKET_NAME}/${old_prefix}" \
        --recursive \
        --endpoint-url "${R2_ENDPOINT}" \
        --only-show-errors
      echo "$(date -Is) [INFO] Deleted R2 backup ${old_prefix}"
    done
  fi
fi

echo "$(date -Is) [INFO] Weekly backup completed successfully."
