#!/bin/bash

# Config
DB_CONTAINER_NAME="odoo-db"   # Adjust to your container name
DB_NAME="odoo"
DB_USER="odoo"
BACKUP_DIR="$(dirname "$0")/db_backups"
DATE=$(date +%Y%m%d_%H%M%S)

# Ensure backup directory exists
mkdir -p "$BACKUP_DIR"

# Run pg_dump inside container
docker exec -t $DB_CONTAINER_NAME pg_dump -U $DB_USER $DB_NAME | gzip > "$BACKUP_DIR/odoo_db_$DATE.sql.gz"

# Optional: Remove backups older than 7 days
find "$BACKUP_DIR" -type f -mtime +7 -name "*.sql.gz" -exec rm {} \;

echo "Backup completed: $BACKUP_DIR/odoo_db_$DATE.sql.gz"