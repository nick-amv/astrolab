# DATA_SOURCES.md — Provenance, licensing, and the review workflow

**Status:** Wave 0 baseline. First-class artifact: no occupation is published to
the public catalog / SEO, and no salary or demand figure is shown as fact,
without a recorded source and a human sign-off.

> **Provenance gate (Wave 2).** Every fact-bearing field
> (`occupation_country.salary_*`, `demand_note`, `edu_requirements.data`) must
> carry `source_id`, `confidence`, and `as_of_date`. LLM-derived values are
> visually marked in the UI as **estimates**, never as verified facts.

> **Review gate (Wave 2, updated 2026-07-02).** Publication review is done by a
> **multi-model review panel** , not a
> single human. The council vets **descriptive** content (title, summary,
> day-in-life, who-fits, translation quality) for accuracy and hallucinations;
> its verdict + per-model rationale are recorded in `content_reviews`. Only
> content the council approves gets `published = true`.
> **Hard facts are exempt from council "approval as fact":** model consensus is
> not ground truth for RU salaries / EGE combinations / deadlines, so those
> stay `confidence = estimate` with provenance and a UI "estimate" marker —
> the council never launders a consensus number into a fact.

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
  → LLM translate to RU (batch)                 [content_source='llm']
  → LLM enrich (day-in-life, who-fits)          [content_source='llm']
  → MULTI-MODEL REVIEW ───────┐              [content_source='council', reviewed_at set]
  → publish (occupations.published = true)  ◄────┘  only council-approved rows
```

- MVP publishes **50 council-reviewed** occupations. The schema supports 300+;
  the remaining rows stay `published = false` and are drained through the same
  review workflow post-MVP.
- Hallucinated content about children's futures is the top reputational risk, so
  **council review is mandatory for everything published**, not just a sample.
  A council split (models disagree, or any flags a factual error) blocks publish.

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

## 6. Reviewer workflow (review panel)

- The ETL submits each occupation's descriptive content to a multi-model council
  (`app/etl/review.py` → `ReviewProvider`). Each model returns approve/reject +
  rationale + any factual flags.
- Verdicts are written to `content_reviews` (occupation, models, verdict,
  rationale, ts). Pass = all models approve and none raises a factual flag.
- On pass the pipeline sets `occupation_i18n.reviewed_at` + `content_source =
  'council'` and flips `occupations.published = true`. On a split it stays
  unpublished with the disagreement recorded for a follow-up pass.
- Facts (`occupation_country`, `edu_requirements`) are **not** "approved as fact"
  by the council — they keep `confidence='estimate'` + provenance until a real
  source backs them.
- Decided 2026-07-02 (Nikita): no human reviewer — the council is the reviewer.
