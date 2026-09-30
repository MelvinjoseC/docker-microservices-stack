#!/bin/bash
# Database Restore Disaster Recovery Script
# Restores PostgreSQL and MongoDB from a backup archive tarball (.tar.gz)

set -e

BACKUP_TARBALL=$1

if [ -z "$BACKUP_TARBALL" ]; then
  echo "Usage: $0 <path-to-db_backup_TIMESTAMP.tar.gz>"
  echo "Available backups in ./backups:"
  ls -lh ./backups/*.tar.gz 2>/dev/null || echo "No backups found."
  exit 1
fi

if [ ! -f "$BACKUP_TARBALL" ]; then
  echo "Error: Backup file '$BACKUP_TARBALL' does not exist."
  exit 1
fi

TEMP_RESTORE_DIR=$(mktemp -d)
trap 'rm -rf "$TEMP_RESTORE_DIR"' EXIT

echo "=========================================================="
echo "Starting Database Restore Process..."
echo "Target Archive: $BACKUP_TARBALL"
echo "Extracting to temporary directory..."
tar -xzf "$BACKUP_TARBALL" -C "$TEMP_RESTORE_DIR"

PG_USER=${DB_USER:-"devuser"}
PG_DB=${DB_NAME:-"microservices_db"}
MONGO_USER=${MONGO_INITDB_ROOT_USERNAME:-"devuser"}
MONGO_PASS=${MONGO_INITDB_ROOT_PASSWORD:-"devpassword"}
MONGO_DB=${MONGO_INITDB_DATABASE:-"catalog_db"}

# 1. Restore PostgreSQL
PG_FILE=$(find "$TEMP_RESTORE_DIR" -name "postgres_*.sql" | head -n 1)
if [ -n "$PG_FILE" ]; then
  echo "Restoring PostgreSQL database: $PG_DB from $(basename "$PG_FILE")..."
  docker exec -i dev-postgres psql -U "$PG_USER" -d "$PG_DB" < "$PG_FILE"
  echo "✔ PostgreSQL restore complete."
else
  echo "⚠ No PostgreSQL dump found in archive, skipping."
fi

# 2. Restore MongoDB
MONGO_FILE=$(find "$TEMP_RESTORE_DIR" -name "mongodb_*.archive" | head -n 1)
if [ -n "$MONGO_FILE" ]; then
  echo "Restoring MongoDB database: $MONGO_DB from $(basename "$MONGO_FILE")..."
  docker exec -i dev-mongodb mongorestore --username "$MONGO_USER" --password "$MONGO_PASS" --authenticationDatabase admin --archive --drop < "$MONGO_FILE"
  echo "✔ MongoDB restore complete."
else
  echo "⚠ No MongoDB archive found in archive, skipping."
fi

echo "=========================================================="
echo "✔ Disaster recovery restore successfully completed!"
echo "=========================================================="
