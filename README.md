# Astrolab

**A free, privacy-first career-guidance platform for teenagers and adults.**
Live at **[astrolab.nikam.dev](https://astrolab.nikam.dev)** — no registration, no paywall, no course to buy.

Astrolab helps a person at a crossroads see a **map, not a verdict**. In about
12 minutes you take a short assessment based on the **RIASEC model (Holland
Codes)**, get a profile of your interests and work values, a fan of fitting
occupations with an honest "why this suits *you*", and — the part most tools skip
— the **concrete path to get there**: fields of study, the exact exams to take
(Russian ЕГЭ first), and application deadlines.

It was built for a real person (a nephew choosing where to apply after school)
and then opened to everyone, because the same problem hits hundreds of thousands
of families every year. It is a **social project**, not a business — monetization
is designed into the architecture but switched off.

---

## The problem it solves

Career guidance online is broken in a few places at once:

- **The test is bait.** Most "free" career tests are lead magnets for paid
  consultations and courses; the result is deliberately cut short so you reach a
  payment button.
- **Guessing instead of a method.** A lot of them are "which fruit are you"
  quizzes with no model behind them.
- **A test, but no path.** Even a decent test usually ends at a list of
  professions. A person needs the next link: which field to study, what to take,
  when to apply.
- **Adults barely exist.** Millions want to change careers at 30–45, but almost
  all content targets schoolchildren.

Astrolab closes exactly these gaps.

## How the assessment works

Not "one more quiz" — a chain from *"I don't know who I am"* to *"I know where to
apply."*

1. **Assessment (~12 min).** Short cards with no right answers, across a few blocks:

   | Block | Draws on | Format |
   |---|---|---|
   | Interests | **RIASEC / Holland** (international standard; O*NET tags every occupation with it) | swipe cards, like / meh / no |
   | Cross-frame | **Klimov ДДО** typology, mapped from RIASEC | second lens on the same answers |
   | School subjects | like × good-at per subject | affinity grid |
   | Work values | O*NET-inspired work values | **forced-choice pairs** — "which matters more, A or B", so real priorities surface instead of socially-desirable ones |
   | Traits (optional) | TIPI-10 short Big Five | opt-in |
   | AI interview (optional) | adaptive dialogue | surfaces contradictions and hidden interests; **fully degradable** |

2. **Profile.** Your interests across the six RIASEC types and what matters to you
   at work — shown visually, not as a dry list.

3. **Occupations, in three baskets.** *Core* (strong matches), *Nearby* (worth a
   look), and *Dark horses* (unexpected, to widen the field). Each occupation
   comes with a warm, honest explanation of why it fits you.

4. **How to get in.** Per occupation: fields of study (with specialty codes),
   typical exam combinations (ЕГЭ), a deadline calendar, and links to the
   universities and colleges that offer the field.

## Methodology & honesty

This is the part we refuse to fudge.

- **The match is a transparent formula, not a black-box model.** Occupation fit
  is a deterministic score (cosine similarity over RIASEC and values vectors +
  subject affinity − soft penalties). The **same answers always produce the same
  result**, and the ranking logic is explainable. Weights are a *documented
  prior*, not a validity claim, and the scoring config is immutable so any past
  result is reproducible.
- **AI is used in exactly one place.** It takes the *already-selected* occupations
  and reorders / explains them for a specific person. **The LLM never enters the
  score and never blocks a result.** It does not decide who you should be and does
  not invent occupations.
- **It's an assessment, not a diagnosis or a verdict.** Your profile changes with
  experience — retake it every six months. We say **"based on the RIASEC model"**
  and deliberately do **not** use the word "validated" until we can demonstrate it
  on our own data. When a choice affects years of someone's life, being honest
  about the limits of the method matters more than a confident promise.

## Privacy by design

Because many users are minors, privacy is in the foundation, not bolted on:

- **Anonymous by default** — the assessment runs with no registration.
- An account is only needed if *you* want to save a result and come back to it.
- Minimal data collection; tokens are hashed; deletion and retention are in from
  day one. We do not sell what we collect.

## For adults — a first-class case, not an afterthought

Changing careers is a huge, underserved segment. An adult takes the same
assessment, but instead of school subjects there's an **experience step** (paste a
résumé or describe your background). Recommendations are then framed as a
**transition, not a restart from zero** — the system points out what already
transfers. "Eight years in sales" isn't "start over"; it's a concrete set of
transferable skills that is worth a lot somewhere.

## Why it's free

It's a social project. There are no paid tiers, courses, or "expert consultation"
at the end. Charging a teenager to understand themselves feels wrong. Monetization
exists in the architecture for the future but is turned off — the service runs
free and without limits.

---

## Tech

- **Backend:** FastAPI · SQLAlchemy 2 · Alembic · PostgreSQL.
- **Frontend:** SvelteKit (SSR, adapter-node) · Paraglide i18n (Russian-first,
  locale-agnostic — every UI string is a translatable key).
- **AI:** an optional, degradable layer (reranking + explanations only).
- Russian-first product; built so other locales are drop-in.

### Repository layout

```
backend/    FastAPI + SQLAlchemy 2 + Alembic (schema + migrations)
frontend/   SvelteKit SSR + Paraglide i18n (/ru, /en)
docs/       METHOD.md · DATA_SOURCES.md · PRIVACY_MODEL.md · ARCHITECTURE.md
deploy/     systemd units, Caddy snippet, deploy webhook, provisioning
scripts/    check_cyrillic.py (CI guard: no hardcoded UI strings in source)
docs        internal design notes (kept private)
```

### Local development

**Backend** (needs a local Postgres, or point `ASTROLAB_DATABASE_URL` at one):

```bash
cd backend
python -m venv .venv && . .venv/Scripts/activate   # or bin/activate
pip install -e ".[dev]"
alembic upgrade head
uvicorn app.main:app --reload --port 8015
```

**Frontend:**

```bash
cd frontend
npm install
npm run dev          # or: npm run build && npm run preview
```

### Quality gates (CI)

- `scripts/check_cyrillic.py` — no hardcoded Cyrillic in source (keys only).
- Backend: ruff, mypy (non-blocking), `alembic upgrade head` from zero, pytest.
- Frontend: eslint, svelte-check, vitest, SSR build.

### Deploy

`git push origin main` → webhook → the server pulls, migrates, rebuilds, and
restarts `astrolab-api` + `astrolab-web`. Secrets live in `/etc/astrolab/env`,
never in git.

## Principles worth not breaking

- The LLM never enters the deterministic score, and never blocks a result.
- `scoring_config` is immutable (DB trigger); results are reproducible.
- Anonymous-first; tokens hashed; deletion + retention from day one.
- Nothing is published to the occupation catalog without human review.
- "Based on the RIASEC model" — never "validated" until calibrated (see
  [`docs/METHOD.md`](docs/METHOD.md)).

## Docs


- [`docs/METHOD.md`](docs/METHOD.md) — assessment methodology, scoring, honesty rule.
- [`docs/DATA_SOURCES.md`](docs/DATA_SOURCES.md) — occupation and admission data.
- [`docs/PRIVACY_MODEL.md`](docs/PRIVACY_MODEL.md) — data, retention, minors.
- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) — services, deploy, infra.

## Author

Built by **Nikita Amosov** — I make focused products that solve one real problem
end to end, not platforms-for-everything. More at **[nikam.dev](https://nikam.dev)**.

If Astrolab is useful, share it with someone who's deciding where to go next.
