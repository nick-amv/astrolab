# Deploy — Astrolab on nikam

Host `nikam` (Hetzner). Repo checkout `/opt/astrolab` (owner: `astrolab`).
Postgres db `astrolab` owned by role `astrolab`. Public at `astrolab.nikam.dev`
via Caddy. Ports: api `8015`, web `8016` (localhost only).

## First-time provisioning

```bash
# on nikam, as root
export ASTROLAB_DB_PASSWORD='<random>'
export ASTROLAB_WEBHOOK_SECRET='<random hex>'
# clone somewhere or copy deploy/provision.sh, then:
bash provision.sh
```

`provision.sh` is idempotent. On first run it prints a deploy **public key** —
add it to `nick-amv/astrolab` as a read-only deploy key, then re-run to clone,
build, and start services. From a machine with `gh`:

```bash
gh repo deploy-key add key.pub -R nick-amv/astrolab -t nikam-astrolab   # read-only
```

## Manual glue (once)

1. **Webhook channel** — merge `deploy/webhook/hooks-astrolab.json` into
   `/etc/webhook/hooks.json` (a JSON array), replacing `__ASTROLAB_WEBHOOK_SECRET__`
   with the real secret. Then `systemctl restart hub-webhook`.
2. **Caddy** — append the `astrolab.nikam.dev { … }` block from
   `deploy/caddy/astrolab.Caddyfile`, and add the `_astrolab_deploy` route
   **inside** the existing `hub.nikam.dev { … }` block (commented at the bottom of
   that file). Then `caddy validate --config /etc/caddy/Caddyfile && systemctl reload caddy`.
3. **GitHub webhook** — repo → Settings → Webhooks → Add:
   - Payload URL: `https://hub.nikam.dev/_astrolab_deploy`
   - Content type: `application/json`
   - Secret: the `ASTROLAB_WEBHOOK_SECRET`
   - Events: just the push event.

## Steady state

`git push origin main` → GitHub → `hub.nikam.dev/_astrolab_deploy` → webhook
(:9099) → `/usr/local/bin/astrolab-deploy.sh`:
fetch + `reset --hard origin/main` → backend deps + `alembic upgrade head` →
frontend `npm ci` + build → `systemctl restart astrolab-api astrolab-web`.

Deploy script aborts (`set -e`) before restart if a migration or build fails, so
the previous release keeps serving.

## Services & timers

| Unit | Role |
|---|---|
| `astrolab-api.service` | FastAPI/uvicorn on :8015 |
| `astrolab-web.service` | SvelteKit SSR (node) on :8016 |
| `astrolab-retention.timer` | daily 03:30 — purge anon >90d + expired tokens/reports |
| `astrolab-backup.timer` | nightly 02:15 — pg_dump, 30-day rotation |

## Handy

```bash
systemctl status astrolab-api astrolab-web
journalctl -u astrolab-api -n 100 --no-pager
curl -s https://astrolab.nikam.dev/api/health
curl -s -o /dev/null -w '%{http_code}\n' https://astrolab.nikam.dev/en
```
