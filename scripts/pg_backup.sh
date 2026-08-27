#!/bin/bash
set -euo pipefail
BACKUP_DIR="/gfin/backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
DB_PASSWORD=$(cat /gfin/secrets/db_password.txt)
PGPASSWORD="$DB_PASSWORD" docker exec gfin_postgres_1 pg_dump -U gfin gfin > "$BACKUP_DIR/gfin_db_$TIMESTAMP.sql" 2>/dev/null
gzip "$BACKUP_DIR/gfin_db_$TIMESTAMP.sql"
# Keep only last 7 days
find "$BACKUP_DIR" -name "gfin_db_*.sql.gz" -mtime +7 -delete
echo "Backup created: gfin_db_$TIMESTAMP.sql.gz"
