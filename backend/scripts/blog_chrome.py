"""Deterministic post-pass: rewrite the shared "chrome" (top nav + theme) of every
Journal article HTML so it matches the main Astrolab app.

Fixes two things and keeps them consistent across locales/articles:
  * full top nav (Method · Professions · Journal · Login + language switcher +
    theme toggle + Take-the-test CTA), localized, instead of the minimal bar;
  * theme: read the SAME localStorage key the app uses ("theme", values
    light/dark) in a before-paint <head> script (no flash), plus a working
    toggle button — the old bar used a different key so the Journal was always
    light.

Idempotent — safe to re-run after generating new articles. Operates on
frontend/static/blog/<slug>.html (ru) and blog/<locale>/<slug>.html.
Run:  python -m scripts.blog_chrome
"""

from __future__ import annotations

import re
from pathlib import Path

BLOG = Path(__file__).resolve().parents[2] / "frontend" / "static" / "blog"
# switcher display order: RU sits between FR and DE, not first (matches the app).
LOCS = ("en", "es", "fr", "ru", "de")

NAV = {
    "ru": {"method": "Методика", "prof": "Профессии", "journal": "Журнал", "login": "Войти",
           "theme": "Переключить тему", "test": "Пройти тест"},
    "en": {"method": "Method", "prof": "Professions", "journal": "Journal", "login": "Sign in",
           "theme": "Toggle theme", "test": "Take the test"},
    "es": {"method": "Método", "prof": "Profesiones", "journal": "Revista", "login": "Entrar",
           "theme": "Cambiar tema", "test": "Hacer el test"},
    "fr": {"method": "Méthode", "prof": "Métiers", "journal": "Journal", "login": "Se connecter",
           "theme": "Changer de thème", "test": "Faire le test"},
    "de": {"method": "Methode", "prof": "Berufe", "journal": "Journal", "login": "Anmelden",
           "theme": "Design wechseln", "test": "Test starten"},
}

_MOON = ('<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
         'stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'
         '<path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/></svg>')
_TOGGLE = ("(function(d){var n=d.dataset.theme===&quot;dark&quot;?&quot;light&quot;:&quot;dark&quot;;"
           "d.dataset.theme=n;try{localStorage.setItem(&quot;theme&quot;,n)}catch(e){}})"
           "(document.documentElement)")

# before-paint theme script — same key the app's app.html uses ("theme").
_HEAD_THEME = ('<script>try{var t=localStorage.getItem("theme");if(t!=="light"&&t!=="dark")'
               't=matchMedia("(prefers-color-scheme:dark)").matches?"dark":"light";'
               'document.documentElement.dataset.theme=t}catch(e){}</script>')

# toggle-button style appended into the article's <style> once.
_TT_CSS = (".nav-right .tt{background:none;border:0;cursor:pointer;color:var(--muted);"
           "padding:6px;border-radius:99px;display:inline-flex;line-height:0}"
           ".nav-right .tt:hover{color:var(--ink);background:var(--surface)}"
           ".nav-right a.active{color:var(--ink)}")

# native language names for the dropdown menu (locale-independent).
LANG_NAMES = {"en": "English", "es": "Español", "fr": "Français", "ru": "Русский", "de": "Deutsch"}
_GLOBE = ('<svg class="globe" width="15" height="15" viewBox="0 0 24 24" fill="none" '
          'stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" '
          'aria-hidden="true"><circle cx="12" cy="12" r="10"/><path d="M2 12h20"/>'
          '<path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 '
          '15.3 15.3 0 0 1 4-10z"/></svg>')
_CHEV = ('<svg class="chev" width="13" height="13" viewBox="0 0 24 24" fill="none" '
         'stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" '
         'aria-hidden="true"><path d="m6 9 6 6 6-6"/></svg>')
# language-dropdown style appended into the article's <style> once (mirrors the app).
_LANG_DD_CSS = (
    ".lang-dd{position:relative}"
    ".lang-dd summary{display:inline-flex;align-items:center;gap:5px;padding:6px 10px;"
    "font-size:.8rem;font-weight:700;color:var(--muted);border:1px solid var(--line-strong);"
    "border-radius:999px;cursor:pointer;list-style:none;user-select:none}"
    ".lang-dd summary::-webkit-details-marker{display:none}"
    ".lang-dd summary:hover{color:var(--ink);background:var(--surface)}"
    ".lang-dd[open] summary{color:var(--ink)}"
    ".lang-dd .chev{transition:transform .18s ease}"
    ".lang-dd[open] summary .chev{transform:rotate(180deg)}"
    ".lang-menu{position:absolute;right:0;top:calc(100% + 6px);z-index:20;min-width:148px;"
    "display:flex;flex-direction:column;padding:6px;background:var(--surface);"
    "border:1px solid var(--line);border-radius:var(--r-sm);box-shadow:var(--shadow,0 18px 44px rgba(90,70,160,.14))}"
    ".lang-menu a{padding:9px 12px;font-size:.85rem;font-weight:600;color:var(--muted);"
    "text-decoration:none;border-radius:10px}"
    ".lang-menu a:hover{color:var(--ink);background:color-mix(in oklab,var(--c3) 8%,var(--surface))}"
    ".lang-menu a.on{color:var(--ink);font-weight:800}"
    ".lang-menu a.on::before{content:\"\\2713 \";color:var(--chip-ink)}"
    "@media(max-width:620px){.lang-menu a{padding:11px 12px}}"
)
# close the open language dropdown on outside click (blog is static — tiny inline script).
_LANG_JS = ('<script>document.addEventListener("click",function(e){var d=document.querySelector'
            '(".lang-dd[open]");if(d&&!d.contains(e.target))d.open=false},true)</script>')

_HEADER_RE = re.compile(r'<header class="nav">.*?</header>', re.S)
_BOTTOM_THEME_RE = re.compile(r'<script>\s*try\{var t=localStorage\.getItem\("astrolab-theme"\).*?</script>', re.S)


def _lang_switcher(slug: str, loc: str) -> str:
    def url(l: str) -> str:
        return f"/blog/{slug}.html" if l == "ru" else f"/blog/{l}/{slug}.html"
    links = "".join(
        (f'<a class="on" href="{url(l)}" hreflang="{l}" aria-current="true">{LANG_NAMES[l]}</a>'
         if l == loc
         else f'<a href="{url(l)}" hreflang="{l}">{LANG_NAMES[l]}</a>')
        for l in LOCS
    )
    return (
        '<details class="lang-dd" translate="no">'
        f'<summary aria-label="Язык / Language">{_GLOBE}<span class="lc">{loc.upper()}</span>{_CHEV}</summary>'
        f'<div class="lang-menu">{links}</div>'
        '</details>'
    )


def _header(slug: str, loc: str) -> str:
    n = NAV[loc]
    return (
        '<header class="nav">\n'
        f'<a class="brand" href="/{loc}"><span class="mark"></span>Astrolab</a>\n'
        '<nav class="nav-right">\n'
        f'<a href="/{loc}/method">{n["method"]}</a>\n'
        f'<a href="/{loc}/professions">{n["prof"]}</a>\n'
        f'<a class="active" href="/blog/">{n["journal"]}</a>\n'
        f'<a href="/{loc}/login">{n["login"]}</a>\n'
        f'{_lang_switcher(slug, loc)}\n'
        f'<button class="tt" type="button" aria-label="{n["theme"]}" onclick="{_TOGGLE}">{_MOON}</button>\n'
        f'<a class="cta" href="/{loc}/test">{n["test"]}</a>\n'
        '</nav>\n'
        '</header>'
    )


def _process(p: Path) -> str:
    html = p.read_text("utf-8")
    m = re.search(r'<html lang="([a-z]{2})"', html)
    loc = m.group(1) if m and m.group(1) in NAV else "ru"
    slug = p.stem

    if not _HEADER_RE.search(html):
        return f"SKIP {p.name} (no <header class=nav>)"
    html = _HEADER_RE.sub(lambda _: _header(slug, loc), html, count=1)

    # before-paint theme script in <head> (after charset), once.
    if 'localStorage.getItem("theme")' not in html.split("</head>")[0]:
        html = html.replace('<meta charset="utf-8" />',
                             '<meta charset="utf-8" />\n' + _HEAD_THEME, 1)
    # toggle + language-dropdown CSS into the first <style>, once each.
    if ".nav-right .tt{" not in html:
        html = html.replace("</style>", _TT_CSS + "</style>", 1)
    if ".lang-dd{" not in html:
        html = html.replace("</style>", _LANG_DD_CSS + "</style>", 1)
    # close-on-outside-click for the dropdown, before </body>, once.
    if 'querySelector(".lang-dd[open]")' not in html:
        html = html.replace("</body>", _LANG_JS + "</body>", 1)
    # drop the old bottom theme script (wrong key).
    html = _BOTTOM_THEME_RE.sub("", html)

    p.write_text(html, encoding="utf-8")
    return f"OK   {loc}  {p.relative_to(BLOG)}"


def main() -> None:
    files = [f for f in BLOG.glob("*.html") if f.name != "index.html"]
    files += [f for l in LOCS for f in (BLOG / l).glob("*.html")]
    for p in sorted(files):
        print("[blog_chrome]", _process(p))


if __name__ == "__main__":
    main()
