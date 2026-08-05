#!/usr/bin/env bash
# Backs up japanese_bot.db to /root/backups, keeping the last 14 days.
#
# Uses sqlite3's .backup command rather than `cp`: .backup takes a proper
# read lock and produces a consistent snapshot even if the bot is mid-write.
# Copying the file directly can capture a torn database.
#
# Install on the VPS:
#   chmod +x backup_db.sh
#   ./backup_db.sh                 # run once now, verify it works
#   crontab -e                     # then add the line below
#
#   30 3 * * * /root/miniJapanesebot2db/backup_db.sh >> /root/backups/backup.log 2>&1
#
# That runs it nightly at 03:30. Check /root/backups/backup.log afterwards.
#
# IMPORTANT: these backups live on the SAME droplet. If the disk dies, they
# die with it. Either enable DigitalOcean Snapshots, or periodically pull a
# copy to your own machine:
#   scp root@<IP>:/root/backups/japanese_bot_*.db .

set -euo pipefail

APP_DIR="/root/miniJapanesebot2db"
DB_FILE="$APP_DIR/japanese_bot.db"
BACKUP_DIR="/root/backups"
KEEP_DAYS=14

mkdir -p "$BACKUP_DIR"

if [ ! -f "$DB_FILE" ]; then
  echo "$(date -Is) ERROR: $DB_FILE not found"
  exit 1
fi

DEST="$BACKUP_DIR/japanese_bot_$(date +%F).db"
sqlite3 "$DB_FILE" ".backup '$DEST'"

# Verify the snapshot is readable and non-empty before trusting it.
WORDS=$(sqlite3 "$DEST" "SELECT COUNT(*) FROM words;")
USERS=$(sqlite3 "$DEST" "SELECT COUNT(*) FROM users;")

if [ "$WORDS" -eq 0 ]; then
  echo "$(date -Is) ERROR: backup has 0 words — not trusting it, removing"
  rm -f "$DEST"
  exit 1
fi

echo "$(date -Is) OK: $DEST ($WORDS words, $USERS users)"

# Rotate: drop snapshots older than KEEP_DAYS.
find "$BACKUP_DIR" -name 'japanese_bot_*.db' -type f -mtime "+$KEEP_DAYS" -delete
