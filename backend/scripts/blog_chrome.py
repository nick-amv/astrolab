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

_HEADER_RE = re.compile(r'<header class="nav">.*?</header>', re.S)
_BOTTOM_THEME_RE = re.compile(r'<script>\s*try\{var t=localStorage\.getItem\("astrolab-theme"\).*?</script>', re.S)


def _lang_switcher(slug: str, loc: str) -> str:
    def url(l: str) -> str:
        return f"/blog/{slug}.html" if l == "ru" else f"/blog/{l}/{slug}.html"
    links = "".join(
        f'<a class="on" href="{url(l)}" hreflang="{l}">{l.upper()}</a>' if l == loc
        else f'<a href="{url(l)}" hreflang="{l}">{l.upper()}</a>'
        for l in LOCS
    )
    return f'<span class="lang" translate="no">{links}</span>'


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
    # toggle CSS into the first <style>, once.
    if ".nav-right .tt{" not in html:
        html = html.replace("</style>", _TT_CSS + "</style>", 1)
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
