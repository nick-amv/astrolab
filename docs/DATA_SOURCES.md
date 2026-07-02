# DATA_SOURCES.md — Provenance, licensing, and the review workflow

**Status:** Wave 0 baseline. First-class artifact: no occupation is published to
the public catalog / SEO, and no salary or demand figure is shown as fact,
without a recorded source and a human sign-off.

> **Provenance gate (Wave 2).** Every fact-bearing field
> (`occupation_country.salary_*`, `demand_note`, `edu_requirements.data`) must
> carry `source_id`, `confidence`, and `as_of_date`. LLM-derived values are
> visually marked in the UI as **estimates**, never as verified facts.

---

## 1. Source registry

Seeded into the `data_sources` table by the initial migration:

| name | What we use it for | License / terms | Freshness |
|---|---|---|---|
| **ESCO** (EU) | Catalog skeleton (~300 of 3000+ occupations), skill graph (for "near" occupations + adult skill-transfer), ready EN/DE/ES translations | Free reuse **with attribution** | Versioned releases; re-pull yearly |
| **O*NET** (US) | RIASEC profiles per occupation (Interest Profiler), work values, outlook | US public domain (attribution requested) | Annual DB releases |
| **RU-classifiers** | Fields of study (ОКСО), typical EGE subject combinations, admission deadlines | Official open data | Rules change yearly → refresh cron |
| **manual-seed** | Team-curated corrections, dark-horse picks, salary bands hand-entered | Internal | Stamped `as_of_date` |
| **llm-estimate** | Draft translations/enrichment; salary/demand *estimates* where no source exists | N/A — **estimate, not fact** | Regenerated on demand; always flagged |

Attribution strings for ESCO and O*NET are shown on occupation pages and in
`/about/methodology` (Wave 2).

## 2. Crosswalk

RIASEC profiles come from O*NET; the catalog skeleton comes from ESCO. We map
ESCO ↔ O*NET via the published crosswalk. Where an occupation has no O*NET
RIASEC vector, we may fill it with an LLM estimate — recorded as
`occupations.riasec_source = 'llm'` so it is never mistaken for O*NET data.
`riasec_source ∈ {onet, llm, curated}` is always set.

## 3. Content pipeline (Wave 2)

```
ESCO subset
  → ESCO↔O*NET crosswalk (RIASEC, values)
  → LLM translate to RU (haiku, batch)          [content_source='llm']
  → LLM enrich (day-in-life, who-fits)          [content_source='llm']
  → HUMAN REVIEW  ───────────────┐              [content_source='human', reviewed_at set]
  → publish (occupations.published = true)  ◄────┘  only reviewed rows
```

- MVP publishes **50 fully reviewed** occupations. The schema supports 300+; the
  remaining rows stay `published = false` and are drained through the same
  review workflow post-MVP.
- Hallucinated content about children's futures is the top reputational risk, so
  **human-in-the-loop is mandatory for everything published**, not just a sample.

## 4. Facts vs estimates in the UI

- A value with `confidence='high'` and a real `source_id` renders plainly.
- A value with `source_id → llm-estimate` (or `confidence='estimate'`) renders
  with an explicit "estimate" marker and its `as_of_date`.
- Salary/demand are **never** scraped in the MVP — manual seed + date stamp only.

## 5. Freshness & refresh

- `as_of_date` on every country-specific fact; stale data is visibly dated, not
  silently trusted.
- Annual cron on nikam refreshes RU admission rules (EGE combinations, deadlines)
  — these change yearly and drive real decisions.
- ESCO / O*NET re-pulled on their release cadence; a re-pull is a reviewed change,
  not an automatic overwrite of curated fields.

## 6. Reviewer workflow

- Reviewer sets `occupation_i18n.reviewed_at` + `content_source='human'` and, for
  facts, `occupation_country.reviewed_by/reviewed_at`.
- Only then may an admin flip `occupations.published = true`.
- Open question for Nikita (DESIGN §16.4): who reviews the 50 MVP occupations
  (and later the remaining 250+) — himself or an editor.
