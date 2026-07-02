# METHOD.md — Assessment methodology, scoring, and honesty

**Status:** Wave 0 baseline (pre-calibration). This document is a first-class
artifact: the assessment logic is versioned and reviewable like code.

> **Honesty rule (non-negotiable).** Astrolab's assessment is a *product
> adaptation of the RIASEC model*, **not a validated psychometric test**. The
> word "validated" (RU: «валидизировано») must not appear in UI copy, marketing,
> or reports until we have demonstrated it on our own data (see §6). Everywhere
> we say **"based on the RIASEC model"** and surface a confidence signal.

---

## 1. Instruments

| Block | Model it draws on | Measures | Format | Status |
|---|---|---|---|---|
| A. Interests | **RIASEC / Holland** (international standard; O*NET tags every occupation with it) | 6 axes: R, I, A, S, E, C | 48 swipe cards (8/axis), like / meh / no | adaptation |
| A′. Cross-frame | **Klimov ДДО** (man–man / tech / nature / sign / artistic) | 5 types, mapped from RIASEC | 10 of the A cards carry a Klimov tag; we show both frames | adaptation |
| B. Subjects | school-subject affinity | like × good-at, per subject | ~18-subject grid | product |
| C. Values | **work values** (O*NET WIP-inspired; Schein anchors for adults) | 6 axes: achievement, autonomy, recognition, relationships, stability, conditions | 20 forced-choice pairs | adaptation |
| D. Traits (optional) | **TIPI-10** (validated short Big Five) | OCEAN | 10 items, opt-in | validated source, short form |
| E. AI interview | adaptive dialogue (Sonnet) | contradictions, context, hidden interests | 6–10 questions | product; **degradable** |

The swipe/gamified adaptation is shorter and more engaging than the source
inventories — which is exactly why it is **not** the validated instrument and is
labelled as an adaptation.

## 2. Item provenance

- RIASEC item pool is authored to the six Holland activity domains; each item
  records which axis (and optional Klimov tag) it loads on.
- The bank is **versioned**: `question_bank.version`. A wording change is a new
  version row, never an in-place edit — so any historical result can be
  recomputed against the exact items it was taken with.
- Localised text lives in `question_i18n`; the item's psychometric identity
  (axis, weight) is language-independent.

## 3. Scoring

### 3.1 Trait vectors
Per session we compute, and store in `trait_scores` (one row per `kind`):
- `riasec` — 6 axis scores, min-max normalised to 0..1 across the axis's items.
- `klimov` — derived from RIASEC-tagged items.
- `values` — 6 axes from forced-choice wins, normalised 0..1.
- `subjects` — per subject, `affinity = like × good_at` (each 0..1).
- `tipi` — OCEAN, if the optional block was taken.

### 3.2 Occupation match (deterministic)
```
score = w_riasec · cos(riasec_user, riasec_occ)
      + w_subjects · subject_fit
      + w_values  · cos(values_user, values_occ)
      − soft_penalties
```
- `subject_fit` = mean user affinity over the occupation's key subjects.
- `soft_penalties` push down (never eliminate) options that violate a stated
  constraint — e.g. "not willing to study 6+ years" nudges medicine down.
- **Weights are a documented prior, not a validity claim.** Seeded in the
  immutable `scoring_config` (version 1), age-band-dependent:

| age_band | riasec | subjects | values |
|---|---|---|---|
| 14–16 | 0.45 | 0.35 | 0.20 |
| 17–19 | 0.50 | 0.25 | 0.25 |
| 20–23 | 0.50 | 0.20 | 0.30 |
| 24+   | 0.45 | 0.15 | 0.40 |
| default | 0.50 | 0.25 | 0.25 |

`core_tau = 0.55` is the threshold for the "Core" bucket.

### 3.3 The LLM never touches the number
The deterministic `score` and `rank_det` are pure and reproducible. The optional
LLM re-rank writes a **separate** `rank_llm` and a "why you" explanation; it may
only reorder the deterministic top-30 and may never introduce an occupation
outside it (anti-hallucination). Display order:
```
rank_final = rank_llm if llm_status == 'ok' else rank_det
```
computed on the backend so the UI never encodes the rule. Every LLM call is
audited in `llm_calls` (prompt_hash, model, config_version, output).

## 4. Buckets (anti-determinism)
- **Core** — top-5 with `score > core_tau`.
- **Near** — neighbours of the core in the ESCO skill graph that didn't make the
  top list (undervalued adjacents).
- **Dark horses** — 2–3 stretch options with a strong match on 1–2 axes from
  unusual fields, to widen horizons.

Results are always framed as "your profile is currently closest to…", never
"you are destined to be…". Retest every 6 months with a visible history.

## 5. Confidence signal
Every result carries a `methodology_stage` (`early` until calibration) and a
per-result confidence derived from completeness (how many blocks were answered)
and internal consistency. Surfaced in the UI as "early version of the
methodology" until §6 completes. The `/api/meta` endpoint exposes the active
`scoring_version` and stage.

## 6. Calibration plan
Once ~500 completed assessments exist:
1. **Reliability** — Cronbach's α per RIASEC axis; flag axes below ~0.7.
2. **Item quality** — item-total correlations; retire/rewrite weak items → a new
   `question_bank.version` (v2).
3. **Weight tuning** — revisit the §3.2 prior against outcome signals; a change
   is a new immutable `scoring_config` version.
4. Only after evidence do we relax the language in §0 — and even then, precisely
   (e.g. "internally consistent on our sample"), never a blanket "validated".

## 7. What is explicitly out of scope
No clinical, psychiatric, or diagnostic claims. The interview system prompt
forbids medical/mental-health advice and routes crisis topics to a soft exit
with a helpline. The assessment predicts *fit and direction*, not ability or worth.
