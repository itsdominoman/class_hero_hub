#!/bin/bash

# Configuration
DB_PATH="/opt/apps/family-hero-hub/data/family_hero_hub.sqlite"
BACKUP_DIR="/opt/backups/family-hero-hub"
TIMESTAMP=$(date +"%Y%m%d-%H%M%S")
BACKUP_PATH="${BACKUP_DIR}/family_hero_hub-${TIMESTAMP}.sqlite"

# Create backup directory if it doesn't exist
mkdir -p "${BACKUP_DIR}"

# Check if database exists
if [ -f "${DB_PATH}" ]; then
    echo "Backing up database to ${BACKUP_PATH}..."
    cp "${DB_PATH}" "${BACKUP_PATH}"
    echo "Backup complete."
else
    echo "Database file not found at ${DB_PATH}. Skipping backup."
fi
