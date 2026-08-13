#!/usr/bin/env bash
# Astrolab Journal autopost — headless Claude on nikam. Fired by astrolab-autopost.timer.
# Works in a SEPARATE clone (/opt/astrolab-autopost) so it never fights the deploy
# webhook that resets /opt/astrolab. The agent generates 1 article in 5 langs,
# runs the deterministic post-passes (blog_chrome, blog_index — pure stdlib, no
# venv/node needed), validates, commits + pushes; the webhook then deploys.
#
# git pull deliberately moved out to the unit's ExecStartPre: while it lived here,
# a fix to this file could only reach the server through a run this file had to
# survive. The school's autopost died in exactly that loop for three weeks.
set -uo pipefail
cd /opt/astrolab-autopost || exit 1
set -a; . /opt/hub/.env; set +a   # CLAUDE_CODE_OAUTH_TOKEN, GH_TOKEN, BOT_TOKEN, ADMIN_CHAT_ID
LOG=/var/log/astrolab-autopost.log
rc=0
{
  echo "=== autopost start $(date -u) ==="
  timeout 3600 claude -p "$(cat /opt/astrolab-autopost/docs/blog/AUTOPOST_PROMPT.md)" --output-format text
  rc=$?
  echo "=== autopost end rc=$rc $(date -u) ==="
} >> "$LOG" 2>&1

# Propagate the exit code. It used to be swallowed: the last command in the block
# was echo, so the service always succeeded and OnFailure could never fire — not
# even when Claude itself died. The watchdog would still catch it a day later,
# but an alert on the spot is cheaper than a day of quiet.
exit "$rc"
