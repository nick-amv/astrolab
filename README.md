# Astrolab

Career-guidance platform — helps teenagers choose a profession and a path to
admission, and helps adults find or change their line of work. Russian-first,
built locale-agnostic. Live at **astrolab.nikam.dev**.

> Single source of truth for scope and decisions: **[DESIGN.md](DESIGN.md)** (v1.1,
> adversarially reviewed with Codex). Read it before contributing.

## Status

**Wave 0 — skeleton + first-class docs + deploy.** The vertical slices
(assessment → catalog → AI → RU admission) land in Waves 1–4. See DESIGN §13.

## Layout

```
backend/    FastAPI + SQLAlchemy 2 + Alembic (full §10.2 schema, migration 0001)
frontend/   SvelteKit SSR (adapter-node) + Paraglide i18n (/ru, /en)
docs/       METHOD.md · DATA_SOURCES.md · PRIVACY_MODEL.md · ARCHITECTURE.md
deploy/     systemd units, Caddy snippet, deploy webhook, provisioning
scripts/    check_cyrillic.py (CI guard: no hardcoded UI strings in source)
PRODUCT.md  design register for the impeccable design skill
```

## Local dev

**Backend** (needs a local Postgres, or point `ASTROLAB_DATABASE_URL` at one):
```bash
cd backend
python -m venv .venv && . .venv/Scripts/activate   # or bin/activate
pip install -e ".[dev]"
alembic upgrade head
uvicorn app.main:app --reload --port 8015
```

**Frontend**:
```bash
cd frontend
npm install
npm run dev          # or: npm run build && npm run preview
```

## Quality gates (CI)

- `scripts/check_cyrillic.py` — no hardcoded Cyrillic in source (keys only).
- Backend: ruff, mypy (non-blocking), `alembic upgrade head` from zero, pytest.
- Frontend: eslint, svelte-check, vitest, SSR build.

## Deploy

`git push origin main` → GitHub webhook → nikam pulls, migrates, rebuilds, and
restarts `astrolab-api` + `astrolab-web`. See `docs/ARCHITECTURE.md` §5 and
`deploy/`. Secrets live in `/etc/astrolab/env`, never in git.

## Principles worth not breaking

- The LLM never enters the deterministic score, and never blocks a result.
- `scoring_config` is immutable (DB trigger); results are reproducible.
- Anonymous-first; tokens hashed; deletion + retention from day one.
- Nothing is published to the catalog without human review.
- "Based on the RIASEC model" — never "validated" until calibrated (METHOD.md).
