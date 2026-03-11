#!/bin/sh
set -e

FILENAME="/backups/botox_$(date -u +%Y-%m-%d).sql.gz"

echo "[$(date -u)] Starting backup → $FILENAME"
pg_dump -h db -U "$POSTGRES_USER" "$POSTGRES_DB" | gzip > "$FILENAME"
echo "[$(date -u)] Backup done"

# Remove dumps older than 90 days (~13 weekly backups)
find /backups -name "botox_*.sql.gz" -mtime +90 -delete