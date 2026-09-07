#!/bin/bash
BACKUP_DIR="$HOME/backups"
mkdir -p "$BACKUP_DIR"
DATE=$(date +%Y%m%d%H%M%S)

# Removed 'local' because these are not inside a function
folders=("Will-World")

for folder in "${folders[@]}"; do
  # Removed 'local' here as well
  SERVER_DIR="$HOME/$folder"
  
  # Use quotes around variables to handle paths with spaces correctly
  tar -czvf "$BACKUP_DIR/backup_$DATE.tar.gz" "$SERVER_DIR/world" "$SERVER_DIR/server.properties"
done

