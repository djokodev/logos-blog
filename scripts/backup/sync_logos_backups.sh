#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

# Optional local env file for macOS sync runtime.
LOCAL_BACKUP_ENV_FILE="${LOCAL_BACKUP_ENV_FILE:-${HOME}/.config/logos-backup/env}"
if [[ -f "${LOCAL_BACKUP_ENV_FILE}" ]]; then
  set -a
  # shellcheck disable=SC1090
  source "${LOCAL_BACKUP_ENV_FILE}"
  set +a
fi

LOCAL_BACKUP_DIR="${LOCAL_BACKUP_DIR:-${HOME}/Backups/logos-backend}"
LOCAL_RETENTION_WEEKS="${LOCAL_RETENTION_WEEKS:-12}"
R2_PREFIX="${R2_PREFIX:-prod/weekly}"

required_vars=(
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

mkdir -p "${LOCAL_BACKUP_DIR}"

echo "$(date -Is) [INFO] Syncing backups from R2 -> ${LOCAL_BACKUP_DIR}"
AWS_ACCESS_KEY_ID="${R2_ACCESS_KEY_ID}" \
AWS_SECRET_ACCESS_KEY="${R2_SECRET_ACCESS_KEY}" \
AWS_DEFAULT_REGION="auto" \
aws s3 sync "s3://${R2_BUCKET_NAME}/${R2_PREFIX}/" "${LOCAL_BACKUP_DIR}/" \
  --endpoint-url "${R2_ENDPOINT}" \
  --only-show-errors

echo "$(date -Is) [INFO] Applying local retention (keep ${LOCAL_RETENTION_WEEKS} backups)..."
mapfile -t local_dirs < <(find "${LOCAL_BACKUP_DIR}" -mindepth 1 -maxdepth 1 -type d -printf "%f\n" | sort)
if (( ${#local_dirs[@]} > LOCAL_RETENTION_WEEKS )); then
  delete_count=$(( ${#local_dirs[@]} - LOCAL_RETENTION_WEEKS ))
  for old_dir in "${local_dirs[@]:0:delete_count}"; do
    rm -rf "${LOCAL_BACKUP_DIR:?}/${old_dir}"
    echo "$(date -Is) [INFO] Deleted local Mac backup ${old_dir}"
  done
fi

echo "$(date -Is) [INFO] Mac sync completed."
