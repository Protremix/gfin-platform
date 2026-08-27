#!/bin/bash
# GFIN Daily Database Backup
BACKUP_DIR=/gfin/backups
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE=$BACKUP_DIR/gfin_db_$DATE.sql.gz

mkdir -p $BACKUP_DIR

# Dump and compress
docker exec gfin_postgres_1 pg_dump -U gfin gfin | gzip > $BACKUP_FILE

# Keep only last 30 days
find $BACKUP_DIR -name 'gfin_db_*.sql.gz' -mtime +30 -delete

# Log
echo "$(date) - Backup created: $BACKUP_FILE ($(du -h $BACKUP_FILE | cut -f1))" >> /gfin/backups/backup.log
