# PRIVACY_MODEL.md — Data, retention, deletion, and minors

**Status:** Wave 0 baseline. First-class artifact. Astrolab serves minors, so
privacy is designed in, not bolted on.

> **Retention/deletion gate (Wave 0).** No teenager's session is stored without a
> working deletion path and an automatic retention purge. Both ship in Wave 0.

---

## 1. Principle: anonymous-first, minimal PII

- The whole assessment — test, profile, result, share link — works with **no
  account and no PII**. A `profiles` row is keyed by a random `anon_token`, not a
  person.
- Anonymous-first strongly reduces risk **but does not eliminate it**: answers +
  age_band + country + education_stage, if linked to a device or logs, can become
  personal or sensitive. Hence this document.
- When an account is created it holds **at most** an `email` OR a `tg_id` — never
  a name. (`users` table; both columns nullable.)

## 2. Tokens are never stored raw

- `auth_tokens.token_hash` and `reports.token_hash` store only the **SHA-256
  digest**. The raw token is shown to the user once and never persisted
  (`app/security/tokens.py`).
- Share links `/r/<token>`: hashed at rest, **expire after 180 days**
  (`reports.expires_at`, `ASTROLAB_REPORT_TTL_DAYS`).
- Auth tokens carry their own `expires_at`.

## 3. Retention

| Data | Retention | Mechanism |
|---|---|---|
| Anonymous profiles (no `user_id`) + all their sessions | **90 days** (`ASTROLAB_RETENTION_DAYS`) | daily systemd timer → `python -m scripts.retention_cleanup` → `purge_anonymous_sessions` |
| Expired auth tokens & share reports | at expiry | same job → `purge_expired_tokens` |
| AI interview transcripts | **lives and dies with its session** | `ai_interviews` FK `ondelete=CASCADE` on the session |
| Account-linked profiles | until the user deletes | user-initiated (see §4) |

Deletion cascades through FK `ondelete=CASCADE` from `profiles` / `users` down to
sessions, answers, trait_scores, matches, interviews, and reports.

## 4. Right to erasure

- Endpoint `POST /api/privacy/delete` accepts `{anon_token}` or `{user_id}`,
  removes the subject's data, and records the request in `deletion_log`
  (`requested_at`, `completed_at`).
- **Backups:** database backups are rotated on a 30-day cycle, so erased data
  disappears from backups within 30 days of deletion. This is documented to the
  user (Privacy page) rather than promising instant backup deletion.

## 5. Minors

- `<14`: soft prompt "ask a parent to take it with you" — informational, not a
  hard block.
- `<18` account creation requires a **parental-consent checkbox**, recorded in
  `consent_records` (kind = `parental`). 152-FZ / GDPR-aligned.
- A teenager's **raw answers are never shown to the parent** — the parent view
  (post-MVP) shows strengths and how-to-support only. Deliberate: the teen's
  privacy from the parent is a product decision.

## 6. Logging

- Analytics is privacy-first: **GoatCounter** (cookieless, no PII, no
  cross-site tracking, no ad pixels) for aggregate visit counts. No Google
  Analytics / ad pixels. In-app funnel events may also be first-party
  (`events` table).
- LLM call logs (`llm_calls`) store prompt **hashes**, model, and structured
  output — **not** raw free-text answers in shared/aggregate logs.
- Application logs must not contain raw tokens or raw answer text.

## 7. DPIA-lite checklist

- [x] Lawful basis: consent (accounts) / legitimate interest with minimisation
      (anonymous assessment).
- [x] Data minimisation: no name; email/tg optional; anonymous by default.
- [x] Purpose limitation: data used only for the assessment/result/report.
- [x] Storage limitation: 90-day anon retention; 180-day share links; 30-day
      backup rotation.
- [x] Security: hashed tokens, no raw tokens in logs, TLS at the edge (Caddy).
- [x] Data-subject rights: deletion endpoint + audit log from day one.
- [x] Minors: soft <14 gate, parental consent <18, teen-from-parent privacy.
- [ ] (pre-launch) Legal review of ToS/Privacy copy; appoint a contact for
      requests.

## 8. Not in Wave 0 (tracked)
- Auth wiring for the deletion endpoint (Wave 6) — currently exercised by tests
  and the admin path; a self-service authenticated flow lands with accounts.
- Export-my-data endpoint (nice-to-have, post-MVP).
