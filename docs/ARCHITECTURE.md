# ARCHITECTURE.md — System shape, LLM boundary, jobs, failure modes

**Status:** Wave 0 baseline. First-class artifact.

---

## 1. Shape

```
                    astrolab.nikam.dev (Caddy, TLS)
                        │                    │
              /api/* ───┤                    ├─── everything else
                        ▼                    ▼
        astrolab-api (uvicorn :8015)   astrolab-web (SvelteKit SSR, node :8016)
                        │
                        ▼
                 PostgreSQL (db: astrolab, owner role: astrolab)
```

- **Backend** — Python 3.12, FastAPI, SQLAlchemy 2 (async, psycopg3), Alembic.
- **Frontend** — SvelteKit SSR (`adapter-node`) + Paraglide i18n. SSR is required
  for the SEO occupation catalog (Wave 2).
- **DB** — one Postgres database `astrolab`, owned by a dedicated role
  `astrolab` (NOT `postgres` — a hard lesson from Kvin's `installer_deals`
  permission failure). Nightly `pg_dump`.
- **Ports** — api `8015`, web `8016` (both free on nikam as of Wave 0). Both bind
  localhost; only Caddy is public.

## 2. LLM boundary (the important one)

The app depends **only** on the `LLMProvider` protocol and the
`LLMRequest`/`LLMResult` dataclasses (`app/llm/`). It never imports a concrete
backend and never shells out to a CLI directly.

```
feature code ─► get_provider() ─► GatedProvider (RateGate) ─► backend
                                                              ├─ max_cli  (Claude via CLI, $0, default)
                                                              └─ openrouter (paid fallback)
```

- **Backend selection is config** (`ASTROLAB_LLM_BACKEND`), so swapping
  max_cli → openrouter → a future gateway is an env change with zero code impact
  (a design decision, П1). No architectural lock-in to a CLI that has no SLA.
- **RateGate** bounds process-wide concurrency (`ASTROLAB_LLM_MAX_CONCURRENCY`)
  and per-minute rate (`ASTROLAB_LLM_RATE_LIMIT_PER_MIN`) so a burst of anonymous
  sessions can't stampede the backend or the subscription quota.
- **One degrade path:** every failure surfaces as `LLMUnavailable`. Callers
  (interview, re-rank) must fall back to the deterministic result — the LLM
  **never blocks a result** (DESIGN §4.4).
- **Determinism boundary:** the deterministic scorer owns `score`/`rank_det`
  (reproducible). The LLM writes only `rank_llm` + explanations; `rank_final` is
  computed on the backend (`rank_llm if ok else rank_det`). Every call is audited
  in `llm_calls`.
- **Wave 0 status:** interface, RateGate, both backends, and contract tests ship
  now; backends are dormant (no feature calls them, `healthy()` is False without
  credentials). Real generation wires in at Wave 3.

## 3. Data contracts

The full DESIGN §10.2 schema lands in the **first** Alembic migration
(`0001_initial`) — no "add the schema later" on tables that hold people's
results (a design decision, П7). Two DB-level guarantees:

- **`scoring_config` is immutable** — a trigger (`astrolab_block_mutation`)
  rejects UPDATE and DELETE. New weights = a new version row. A historical result
  can never be silently re-scored.
- **Token columns are hashes** with expiry; skills are a normalized M2M
  (`occupation_skills`), not a jsonb blob; provenance lives in `data_sources`.

The initial migration builds tables straight from ORM metadata, so model and
migration cannot drift at revision 1; later waves add incremental `op.*` steps.

## 4. Background jobs (nikam)

| Job | Trigger | What |
|---|---|---|
| retention purge | daily systemd timer | `scripts.retention_cleanup` — anon > 90d, expired tokens/reports |
| EGE refresh | yearly cron | refresh RU admission rules (Wave 4) |
| pg_dump | nightly | DB backup, 30-day rotation |

## 5. Deploy

`git push origin main` → GitHub webhook → `hub.nikam.dev/_astrolab_deploy` →
Caddy → webhook listener (:9099) → `astrolab-deploy.sh`:
fetch + `reset --hard origin/main` → backend `pip install` + `alembic upgrade
head` → frontend `npm ci` + `npm run build` → restart `astrolab-api` +
`astrolab-web`. Same pattern as hub-deploy / bridge-deploy. Secrets live in
`/etc/astrolab/env` (EnvironmentFile), never in git.

## 6. Failure modes

| Failure | Behaviour |
|---|---|
| LLM backend down / slow / bad output | `LLMUnavailable` → deterministic result stands; interview skipped |
| DB down | `/api/health` still 200 (liveness); `/api/health/ready` 500 (readiness) |
| Migration fails on deploy | deploy script aborts before restart (`set -e`); previous release keeps serving |
| Frontend build fails on deploy | deploy aborts before restart; old build keeps serving |
| Retention job error | idempotent; safe to re-run next day; no partial deletes (per-batch commit) |
| Backup disk full | pg_dump fails loudly in cron mail; app unaffected |

## 7. i18n

- UI strings: Paraglide (compile-time), URL strategy — `/ru`, `/en`, bare `/`
  → 307 `/ru`. Locale de-localized via SvelteKit `reroute` (`src/hooks.ts`);
  active locale set by `paraglideMiddleware` (`src/hooks.server.ts`).
- Content strings: `*_i18n` tables, fallback chain `locale → en → ru`.
- Rule: **no user-facing string in code** — only message keys. Enforced by a
  Cyrillic-in-`src` lint in CI.

## 8. Environments & config
- All config via `ASTROLAB_*` env (`app/config.py`), read from `/etc/astrolab/env`
  in prod, `.env` locally. `.env.example` documents every key. No secret is ever
  committed.
