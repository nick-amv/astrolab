#!/usr/bin/env bash
# Astrolab autopost watchdog — daily health check + self-heal + Telegram alert.
# Mirrors Anvil's. OnFailure only fires when the service crashes; this catches the
# quiet failures: a disabled timer, a cycle that silently produced nothing, or a
# published article that never made it into llms.txt (our AI-citation index).
set -a; . /opt/hub/.env; set +a
tg(){ curl -s -o /dev/null -X POST "https://api.telegram.org/bot${BOT_TOKEN}/sendMessage" --data-urlencode "chat_id=${ADMIN_CHAT_ID}" --data-urlencode "text=$1" --data-urlencode "disable_web_page_preview=true"; }
BUILD=/opt/astrolab/frontend/build/client
ISSUES=""; HEAL=""

systemctl is-enabled astrolab-autopost.timer >/dev/null 2>&1 || { ISSUES="${ISSUES}
- таймер был ВЫКЛЮЧЕН"; systemctl enable --now astrolab-autopost.timer >/dev/null 2>&1 && HEAL="${HEAL}
- таймер снова включён"; }
systemctl is-active astrolab-autopost.timer >/dev/null 2>&1 || ISSUES="${ISSUES}
- таймер не активен"

# freshness: newest article date vs now (2x/wk => never older than ~4 days)
STALE=$(python3 - <<PY 2>/dev/null
import json,datetime
try:
    d=json.load(open("${BUILD}/blog/index.json"))
    newest=max(a["date"] for a in d)
    age=(datetime.date.today()-datetime.date.fromisoformat(newest)).days
    print("STALE" if age>5 else "OK", newest, age, len(d))
except Exception as e:
    print("ERR", str(e)[:60])
PY
)
case "$STALE" in
  STALE*) ISSUES="${ISSUES}
- свежесть: ${STALE} (нет новых статей >5 дней)"
          # self-heal: trigger one re-run (guarded so we do it at most once/day)
          M="/tmp/astrolab-autopost-rerun-$(date +%F)"
          if [ ! -f "$M" ]; then touch "$M"; systemctl start --no-block astrolab-autopost.service && HEAL="${HEAL}
- запущен авто-перезапуск astrolab-autopost.service"; fi ;;
  ERR*) ISSUES="${ISSUES}
- не смог прочитать index.json: ${STALE}" ;;
esac

# AEO: every published article must be listed in llms.txt (blog_llms post-pass)
LLMS=$(python3 - <<PY 2>/dev/null
import json,re
try:
    arts=json.load(open("${BUILD}/blog/index.json"))
    txt=open("${BUILD}/llms.txt",encoding="utf-8").read()
    # Take the EN URL from the manifest rather than building it from the article
    # id: slugs are localized now, so /blog/en/<id>.html stopped being an address
    # (that assumption made this check cry wolf about all 10 articles at once).
    missing=[a["slug"] for a in arts if a.get("i18n",{}).get("en",{}).get("url","\\0") not in txt]
    print("MISSING "+",".join(missing) if missing else "OK", len(arts))
except Exception as e:
    print("ERR", str(e)[:60])
PY
)
case "$LLMS" in
  MISSING*) ISSUES="${ISSUES}
- llms.txt отстал от блога: ${LLMS} (запусти blog_llms и запушь)" ;;
  ERR*) ISSUES="${ISSUES}
- не смог сверить llms.txt: ${LLMS}" ;;
esac

if [ -n "$ISSUES" ]; then
  tg "🟠 Astrolab автопостинг — watchdog нашёл проблему:${ISSUES}${HEAL:+

Действия:${HEAL}}"
elif [ "$(date +%u)" = "7" ]; then
  tg "✅ Astrolab автопостинг здоров ($(echo "$STALE" | awk "{print \$4}") статей, новейшая $(echo "$STALE" | awk "{print \$2}"), llms.txt в синхроне). Watchdog на связи."
fi
