#!/bin/bash
# Database Backup Script for DevOps Microservices Stack
# This script executes backups of PostgreSQL and MongoDB databases,
# creates a compressed tarball, and implements a cleanup policy (retains last 7 days).

set -e

BACKUP_DIR="./backups"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
RETENTION_DAYS=7

# Credentials (default local fallback)
PG_USER=${DB_USER:-"devuser"}
PG_DB=${DB_NAME:-"microservices_db"}
MONGO_USER=${MONGO_INITDB_ROOT_USERNAME:-"devuser"}
MONGO_DB=${MONGO_INITDB_DATABASE:-"catalog_db"}

echo "=========================================================="
echo "Starting Database Backup Process..."
echo "Timestamp: $TIMESTAMP"
echo "=========================================================="

# Create backup directory
mkdir -p "$BACKUP_DIR"

# 1. PostgreSQL Backup
echo "Backing up PostgreSQL database: $PG_DB..."
docker exec dev-postgres pg_dump -U "$PG_USER" -d "$PG_DB" > "$BACKUP_DIR/postgres_$TIMESTAMP.sql"
echo "PostgreSQL backup completed successfully."

# 2. MongoDB Backup
echo "Backing up MongoDB database: $MONGO_DB..."
docker exec dev-mongodb mongodump --username "$MONGO_USER" --password "${MONGO_INITDB_ROOT_PASSWORD:-devpassword}" --authenticationDatabase admin --db "$MONGO_DB" --archive > "$BACKUP_DIR/mongodb_$TIMESTAMP.archive"
echo "MongoDB backup completed successfully."

# 3. Compress Backups
echo "Creating compressed tarball..."
tar -czf "$BACKUP_DIR/db_backup_$TIMESTAMP.tar.gz" -C "$BACKUP_DIR" "postgres_$TIMESTAMP.sql" "mongodb_$TIMESTAMP.archive"
rm "$BACKUP_DIR/postgres_$TIMESTAMP.sql" "$BACKUP_DIR/mongodb_$TIMESTAMP.archive"
echo "Backup compressed: $BACKUP_DIR/db_backup_$TIMESTAMP.tar.gz"

# 4. Retention Policy (Delete backups older than RETENTION_DAYS)
echo "Applying retention policy (deleting backups older than $RETENTION_DAYS days)..."
find "$BACKUP_DIR" -name "db_backup_*.tar.gz" -mtime +$RETENTION_DAYS -exec rm -f {} \;
echo "Retention policy applied."

echo "=========================================================="
echo "Database Backup completed successfully!"
echo "=========================================================="
