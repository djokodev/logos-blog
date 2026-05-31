#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
iso_now() { date +"%Y-%m-%dT%H:%M:%S%z"; }

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

AWS_BIN="${AWS_BIN:-$(command -v aws || true)}"
if [[ -z "${AWS_BIN}" && -x "/opt/homebrew/bin/aws" ]]; then
  AWS_BIN="/opt/homebrew/bin/aws"
fi
if [[ -z "${AWS_BIN}" && -x "/usr/local/bin/aws" ]]; then
  AWS_BIN="/usr/local/bin/aws"
fi

if [[ -z "${AWS_BIN}" ]]; then
  echo "aws CLI is required on macOS for sync (command not found)." >&2
  exit 1
fi

mkdir -p "${LOCAL_BACKUP_DIR}"

echo "$(iso_now) [INFO] Syncing backups from R2 -> ${LOCAL_BACKUP_DIR}"
AWS_ACCESS_KEY_ID="${R2_ACCESS_KEY_ID}" \
AWS_SECRET_ACCESS_KEY="${R2_SECRET_ACCESS_KEY}" \
AWS_DEFAULT_REGION="auto" \
"${AWS_BIN}" s3 sync "s3://${R2_BUCKET_NAME}/${R2_PREFIX}/" "${LOCAL_BACKUP_DIR}/" \
  --endpoint-url "${R2_ENDPOINT}" \
  --only-show-errors

echo "$(iso_now) [INFO] Applying local retention (keep ${LOCAL_RETENTION_WEEKS} backups)..."
local_dirs="$(
  find "${LOCAL_BACKUP_DIR}" -mindepth 1 -maxdepth 1 -type d -exec basename {} \; | sort
)"
local_count="$(printf '%s\n' "${local_dirs}" | sed '/^\s*$/d' | wc -l | tr -d ' ')"
if [[ -z "${local_count}" ]]; then
  local_count=0
fi
if (( local_count > LOCAL_RETENTION_WEEKS )); then
  delete_count=$(( local_count - LOCAL_RETENTION_WEEKS ))
  while IFS= read -r old_dir; do
    [[ -z "${old_dir}" ]] && continue
    rm -rf "${LOCAL_BACKUP_DIR:?}/${old_dir}"
    echo "$(iso_now) [INFO] Deleted local Mac backup ${old_dir}"
  done < <(printf '%s\n' "${local_dirs}" | sed '/^\s*$/d' | head -n "${delete_count}")
fi

echo "$(iso_now) [INFO] Mac sync completed."
