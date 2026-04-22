#!/bin/bash
# Sync images from Google Drive
# Requires: rclone configured with 'gdrive' remote
# Setup: rclone config (follow OAuth flow for Google Drive)

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
DATA_DIR="$PROJECT_ROOT/data"

echo "Syncing images from Google Drive..."
rclone sync Pathfinder:Pathfinder/images/ "$DATA_DIR/images/" --progress --transfers 8

echo "Syncing model weights from Google Drive..."
rclone sync Pathfinder:Pathfinder/models/ "$DATA_DIR/models/" --progress --transfers 4

echo "Done!"
