#!/usr/bin/env bash
# OnFailure handler for astrolab-autopost.service — Telegram alert with the log tail.
set -a; . /opt/hub/.env; set +a
TAIL="$(tail -12 /var/log/astrolab-autopost.log 2>/dev/null | tr -d "\r")"
MSG="🔴 Astrolab АВТОПОСТИНГ УПАЛ ($(date -u +%F\ %T) UTC). astrolab-autopost.service завершился с ошибкой/таймаутом. Хвост лога:
${TAIL}

Поднять вручную: systemctl start astrolab-autopost.service"
curl -s -o /dev/null -X POST "https://api.telegram.org/bot${BOT_TOKEN}/sendMessage" \
  --data-urlencode "chat_id=${ADMIN_CHAT_ID}" \
  --data-urlencode "text=${MSG}" \
  --data-urlencode "disable_web_page_preview=true"
