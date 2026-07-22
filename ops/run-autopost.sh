#!/usr/bin/env bash
# Astrolab Journal autopost — headless Claude on nikam. Fired by astrolab-autopost.timer.
# Works in a SEPARATE clone (/opt/astrolab-autopost) so it never fights the deploy
# webhook that resets /opt/astrolab. The agent generates 1 article in 5 langs,
# runs the deterministic post-passes (blog_chrome, blog_index — pure stdlib, no
# venv/node needed), validates, commits + pushes; the webhook then deploys.
set -uo pipefail
cd /opt/astrolab-autopost || exit 1
set -a; . /opt/hub/.env; set +a   # CLAUDE_CODE_OAUTH_TOKEN, GH_TOKEN, BOT_TOKEN, ADMIN_CHAT_ID
LOG=/var/log/astrolab-autopost.log
{
  echo "=== autopost start $(date -u) ==="
  git pull --ff-only || echo "git pull failed (continuing)"
  timeout 3600 claude -p "$(cat /opt/astrolab-autopost/docs/blog/AUTOPOST_PROMPT.md)" --output-format text
  echo "=== autopost end rc=$? $(date -u) ==="
} >> "$LOG" 2>&1
