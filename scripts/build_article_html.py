"""Build a self-contained, copy-paste-friendly HTML preview from an article .md.

Mirrors the vc.ru standalone: clean 720px layout, screenshots inlined as base64
so the file renders anywhere. Custom tokens supported:
  [[SCREEN:file.png|caption]]  → <figure> with the image from article-screens/
Minimal markdown: # ## ### headings, **bold**, - lists, --- hr, [txt](url) links,
HTML comments stripped, blank-line-separated paragraphs.

Usage: python scripts/build_article_html.py article-pikabu.md [out.html]
"""
import base64
import mimetypes
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCREENS = ROOT / "article-screens"

STYLE = """
  body{max-width:720px;margin:0 auto;padding:32px 20px 80px;font:18px/1.6 -apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif;color:#1a1a1a;}
  h1{font-size:32px;line-height:1.2;letter-spacing:-.02em;margin:0 0 24px;}
  h2{font-size:25px;line-height:1.25;letter-spacing:-.01em;margin:44px 0 14px;}
  h3{font-size:19px;margin:26px 0 6px;}
  p{margin:0 0 18px;}
  ul{margin:0 0 18px;padding-left:24px;}
  li{margin:0 0 8px;}
  a{color:#0a58ff;text-decoration:underline;}
  strong{font-weight:700;}
  hr{border:0;border-top:1px solid #e5e5e5;margin:40px 0;}
  em{color:#555;}
  figure{margin:28px 0;}
  figure img{width:100%;height:auto;border:1px solid #eee;border-radius:12px;display:block;}
  figcaption{font-size:14px;color:#777;margin-top:8px;text-align:center;}
"""


def esc(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def inline(s: str) -> str:
    """Inline markdown: escape, then **bold** and [txt](url)."""
    s = esc(s)
    s = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", s)
    s = re.sub(r"\[([^\]]+)\]\((https?://[^)]+)\)",
               r'<a href="\2" target="_blank" rel="noopener">\1</a>', s)
    return s


def data_uri(fname: str) -> str | None:
    p = SCREENS / fname
    if not p.exists():
        return None
    mime = mimetypes.guess_type(p.name)[0] or "image/png"
    b64 = base64.b64encode(p.read_bytes()).decode()
    return f"data:{mime};base64,{b64}"


def figure(fname: str, caption: str) -> str:
    uri = data_uri(fname)
    cap = inline(caption)
    if uri is None:
        return (f'<figure><div style="border:2px dashed #ccc;border-radius:12px;'
                f'padding:40px;text-align:center;color:#999">СКРИН: {esc(fname)}</div>'
                f'<figcaption>{cap}</figcaption></figure>')
    return f'<figure><img src="{uri}" alt="{esc(caption)}"><figcaption>{cap}</figcaption></figure>'


def convert(md: str) -> str:
    md = re.sub(r"<!--.*?-->", "", md, flags=re.S)   # strip comments
    out: list[str] = []
    lines = md.split("\n")
    i = 0
    n = len(lines)
    while i < n:
        line = lines[i].rstrip()
        if not line.strip():
            i += 1
            continue
        m = re.match(r"\[\[SCREEN:([^|\]]+)\|([^\]]*)\]\]", line.strip())
        if m:
            out.append(figure(m.group(1).strip(), m.group(2).strip()))
            i += 1
            continue
        if line.strip() == "---":
            out.append("<hr>")
            i += 1
            continue
        h = re.match(r"(#{1,3})\s+(.*)", line)
        if h:
            lvl = len(h.group(1))
            out.append(f"<h{lvl}>{inline(h.group(2))}</h{lvl}>")
            i += 1
            continue
        if re.match(r"\s*[-*]\s+", line):
            items = []
            while i < n and re.match(r"\s*[-*]\s+", lines[i]):
                items.append(f"<li>{inline(re.sub(r'^\s*[-*]\s+', '', lines[i]).rstrip())}</li>")
                i += 1
            out.append("<ul>\n" + "\n".join(items) + "\n</ul>")
            continue
        # paragraph: gather until blank / block start
        para = [line]
        i += 1
        while i < n and lines[i].strip() and not re.match(
                r"(#{1,3}\s|\s*[-*]\s|\[\[SCREEN|---\s*$)", lines[i]):
            para.append(lines[i].rstrip())
            i += 1
        out.append(f"<p>{inline(' '.join(para))}</p>")
    return "\n".join(out)


def build(md_path: Path, out_path: Path) -> None:
    md = md_path.read_text(encoding="utf-8")
    title_m = re.search(r"^#\s+(.*)", re.sub(r"<!--.*?-->", "", md, flags=re.S), re.M)
    title = title_m.group(1).strip() if title_m else "Astrolab"
    desc = ("Astrolab — бесплатная платформа профориентации для подростков и взрослых: "
            "тест на модели RIASEC, подходящие профессии и путь поступления. Без регистрации.")
    body = convert(md)
    doc = (f'<!doctype html>\n<html lang="ru">\n<head>\n<meta charset="utf-8">\n'
           f'<meta name="viewport" content="width=device-width, initial-scale=1">\n'
           f'<title>{esc(title)}</title>\n<meta name="description" content="{esc(desc)}">\n'
           f'<style>{STYLE}</style>\n</head>\n<body>\n{body}\n</body>\n</html>\n')
    out_path.write_text(doc, encoding="utf-8")
    print(f"{md_path.name} -> {out_path.name}  ({len(doc)//1024} KB, title: {title[:60]})")


if __name__ == "__main__":
    src = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "article-pikabu.md"
    if not src.is_absolute():
        src = ROOT / src
    out = Path(sys.argv[2]) if len(sys.argv) > 2 else src.with_name(src.stem + "-standalone.html")
    if not out.is_absolute():
        out = ROOT / out
    build(src, out)
