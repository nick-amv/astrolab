# Language switcher (dropdown) + mobile topbar polish — design

**Date:** 2026-07-22 · **Status:** approved, implementing.

## Problem
5 locales (EN·ES·FR·RU·DE) rendered as flat chips clutter the topbar, especially on mobile. Move languages into a compact dropdown (app + blog), and do a light mobile polish. No hamburger / no full redesign (deliberately scoped).

## Decisions
- **Trigger:** pill `( ◉ EN ▾ )` — lucide **globe SVG** (not emoji, per the no-emoji-icons rule) + current locale code + chevron. Same visual language as the existing `.lang` chip.
- **Mechanism:** native `<details>/<summary>` — **no JS**. Critical because the blog is static HTML; details works identically in the SvelteKit app and the static blog with no duplicated logic.
- **Menu:** absolute popover under the trigger (`--surface`/`--line`/`--shadow`, radius `--r-sm`), 5 items with **native language names** (English · Español · Français · Русский · Deutsch), checkmark + bold on current. Order EN·ES·FR·RU·DE (RU between FR and DE).
- **Selecting a language** = a normal link (app: `localizeHref` same page; blog: `/blog/<slug>` or `/blog/<loc>/<slug>`). Instant switch, behavior unchanged.
- **Close:** on selection (navigation closes it) + a tiny inline "click outside → close".
- **Native names** are locale-independent → a plain constant map, identical in app + blog (not message keys).

## Mobile (≤620px, light polish)
- 5 chips → 1 dropdown pill frees the second row. Layout: brand on row 1; below, wrapping: `Method · Professions · Journal · Login · ( ◉ RU ▾ ) · ☾`.
- Menu items ≥44px tap targets; popover `right: 0` so it doesn't clip at the screen edge.
- Nothing collapses (no hamburger). Verify no horizontal overflow (old bug), tidy gaps/padding.

## Accessibility / theme
- `<summary>` is a native button (keyboard Enter/Space); `aria-label` "Language/Язык"; globe `aria-hidden`; `aria-current` on the active language. Popover uses theme tokens (dark-theme aware).

## Files
- App: `frontend/src/routes/+layout.svelte` (switcher), `frontend/src/routes/app.css` (`.lang-dd` styles + mobile media).
- Blog: `backend/scripts/blog_chrome.py` (`_lang_switcher()` → `<details>` + inject `.lang-dd` CSS), `frontend/static/blog/index.html`. Re-run `blog_chrome` → all articles updated.
- Verify: frontend build + prod Playwright mobile-topbar screenshot.
