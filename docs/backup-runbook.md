# Backup & Restore Runbook (LOGOS)

## Overview

This runbook defines weekly backup and restore operations for LOGOS with three layers:

1. VPS local backup (`/root/backups/logos-backend`)
2. Offsite replication to Cloudflare R2 (`logos-backups`)
3. Weekly pull copy on macOS (`~/Backups/logos-backend`)

Schedule: **Sunday 02:30 (server time)**  
Retention: **12 backups (weeks)**.

## Required environment variables (VPS)

Add these variables in `/root/logos/.env`:

```bash
BACKUP_BASE_DIR=/root/backups/logos-backend
BACKUP_RETENTION_WEEKS=12
BACKUP_LOG_FILE=/var/log/logos-backup.log
BACKUP_LOCK_FILE=/var/lock/logos-backup.lock
R2_BUCKET_NAME=logos-backups
R2_ENDPOINT=https://<R2_ACCOUNT_ID>.r2.cloudflarestorage.com
R2_PREFIX=prod/weekly
R2_ACCESS_KEY_ID=<key_id>
R2_SECRET_ACCESS_KEY=<secret>
MEDIA_VOLUME_NAME=logos_media_volume
DB_CONTAINER_SERVICE=db
```

The scripts source `.env` automatically.

## Scripts

- `scripts/backup/backup_weekly.sh`
  - Creates DB dump (`db.sql.gz`)
  - Archives media volume (`media.tar.gz`)
  - Writes checksums and manifest
  - Uploads backup set to R2
  - Applies 12-week retention locally and on R2

- `scripts/backup/restore_test.sh [timestamp|latest]`
  - Verifies checksums
  - Restores DB to temporary DB (`logos_restore_test`)
  - Extracts media archive to temporary folder
  - Validates restored data and media presence
  - Cleans temporary resources

- `scripts/backup/sync_logos_backups.sh` (macOS)
  - Pulls weekly backups from R2 to `~/Backups/logos-backend`
  - Applies 12-week local retention on Mac

## Manual operations

From VPS:

```bash
cd /root/logos
bash scripts/backup/backup_weekly.sh
bash scripts/backup/restore_test.sh latest
```

From macOS (after configuring local env file):

```bash
bash /path/to/project/scripts/backup/sync_logos_backups.sh
```

## Cron setup (VPS)

Install weekly cron:

```cron
30 2 * * 0 cd /root/logos && /bin/bash /root/logos/scripts/backup/backup_weekly.sh
```

Logs:

- `/var/log/logos-backup.log`

## macOS weekly scheduling (launchd)

1. Copy `scripts/backup/com.logos.backup.sync.plist` to:
   - `~/Library/LaunchAgents/com.logos.backup.sync.plist`
2. Replace placeholder project path in `ProgramArguments`.
3. Load:

```bash
launchctl unload ~/Library/LaunchAgents/com.logos.backup.sync.plist 2>/dev/null || true
launchctl load ~/Library/LaunchAgents/com.logos.backup.sync.plist
launchctl start com.logos.backup.sync
```

## Full migration restore procedure (new VPS)

1. Deploy code and containers.
2. Download desired backup set (DB + media + checksum + manifest).
3. Restore DB:
   - `gunzip -c db.sql.gz | docker compose exec -T db psql -U <user> -d <db>`
4. Restore media:
   - `docker run --rm -v logos_media_volume:/data -v <backup_dir>:/backup alpine sh -c "tar -xzf /backup/media.tar.gz -C /data"`
5. Restart app:
   - `docker compose up -d`
6. Validate:
   - `/`
   - `/cms`
   - one article with cover image

## Post-restore validation checklist

- [ ] `docker compose ps` healthy for `db`, `web`, `nginx`
- [ ] `SELECT COUNT(*) FROM blog_article;` returns expected non-zero value
- [ ] Media files present in volume
- [ ] One article page loads with cover image
- [ ] CMS login works

## Key rotation guidance (R2)

When rotating `R2_ACCESS_KEY_ID` / `R2_SECRET_ACCESS_KEY`:

1. Create new key in Cloudflare R2 (same bucket scope).
2. Update `/root/logos/.env`.
3. Run manual backup test:
   - `bash scripts/backup/backup_weekly.sh`
4. Delete old key only after successful test.

## Failure handling

If backup fails:

1. Inspect `/var/log/logos-backup.log`.
2. Verify container and DB status:
   - `docker compose ps`
3. Verify R2 connectivity and credentials.
4. Re-run manually after fix:
   - `bash scripts/backup/backup_weekly.sh`
