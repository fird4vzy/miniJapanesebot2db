#!/usr/bin/env bash
# Run this from inside your local clone of miniJapanesebot2db, on the
# machine where you have push access (not necessarily the VPS).
#
# It:
#  1. Stops tracking files that should never be in git (real user data,
#     logs, backups) — they stay on disk, just untracked from now on.
#  2. Deletes junk files that shouldn't exist at all.
#  3. Commits the result.
#
# NOTE: this only removes the files from the CURRENT commit. The old
# versions (with real user IDs) still exist in git history. If this repo
# is public, treat those old commits as already leaked — full history
# rewrite (git-filter-repo) is a separate, more careful step; ask before
# running it since it force-rewrites history for everyone with a clone.

set -euo pipefail

echo "Untracking runtime data (kept on disk, just no longer in git)..."
git rm --cached --ignore-unmatch \
  japanese_bot.db \
  subscribers.json \
  settings.json \
  scores.json \
  bot.log

echo "Deleting junk files entirely..."
git rm --ignore-unmatch \
  "aux | grep bot.py" \
  bot.py.save

echo "Staging updated .gitignore, deploy.yml, bot.py, and migration script..."
git add .gitignore .github/workflows/deploy.yml bot.py migrate_level_to_db.py .env.example

git commit -m "Fix deploy service name, move level pref into DB, stop tracking user data/junk files"

echo
echo "Done locally. Review with 'git show --stat HEAD', then:"
echo "  git push origin main"
