#!/usr/bin/env python3
"""Build the static womenpedia.org site from the Wiki.js export into _site/.

Usage: python3 build.py   (then preview with: python3 -m http.server -d _site)
"""
import html
import re
import shutil
from pathlib import Path

SRC = Path(__file__).parent
OUT = SRC / "_site"
LANGS = {"en": "English", "es": "Español", "pt": "Português"}
NAV = ["women-artists", "women-in-stem", "women-activists", "women-in-business", "contact"]
SKIP = {".git", ".github", "_site", "build.py", "style.css", "README.md", "CNAME"}

TEMPLATE = """<!DOCTYPE html>
<html lang="{lang}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title} | Womenpedia</title>
<meta name="description" content="{description}">
<link rel="icon" href="/logo_circle.png">
<link rel="stylesheet" href="/style.css">
<script async src="https://www.googletagmanager.com/gtag/js?id=G-V8ZWTKLE0M"></script>
<script>window.dataLayer=window.dataLayer||[];function gtag(){{dataLayer.push(arguments)}}gtag('js',new Date());gtag('config','G-V8ZWTKLE0M');</script>
</head>
<body>
<header class="site-header">
  <a class="brand" href="{home}"><img src="/logo_circle.png" alt="">Womenpedia</a>
  <nav class="langs">{langs}</nav>
</header>
<nav class="site-nav">{nav}</nav>
<main>
{body}
</main>
<footer class="site-footer">Womenpedia Org · <a href="https://creativecommons.org/licenses/by-sa/4.0/">CC BY-SA 4.0</a></footer>
</body>
</html>
"""


def parse(path):
    """Split a Wiki.js export file into (front-matter dict, body html)."""
    text = path.read_text(encoding="utf-8")
    m = re.match(r"\s*<!--(.*?)-->", text, re.S)
    meta = dict(line.split(": ", 1) for line in m.group(1).strip().splitlines() if ": " in line)
    body = text[m.end():]
    # The "code" editor pages are full HTML documents; keep only what's inside <body>.
    b = re.search(r"<body[^>]*>(.*)</body>", body, re.S | re.I)
    body = b.group(1) if b else body
    # Wiki.js treated /en/... as the default locale, which is served at /.
    body = re.sub(r'href="/en/', 'href="/', body)
    return meta, body


def url(lang, path):
    prefix = "" if lang == "en" else f"/{lang}"
    return f"{prefix}/" if path == "home" else f"{prefix}/{path}"


def main():
    shutil.rmtree(OUT, ignore_errors=True)
    pages = {}  # (lang, path) -> (meta, body)
    for f in sorted(SRC.rglob("*")):
        rel = f.relative_to(SRC)
        if rel.parts[0] in SKIP or f.is_dir():
            continue
        if f.suffix == ".html":
            lang = rel.parts[0] if rel.parts[0] in LANGS and len(rel.parts) > 1 else "en"
            path = str(rel.with_suffix(""))[len(lang) + 1:] if lang != "en" else str(rel.with_suffix(""))
            meta, body = parse(f)
            if meta.get("published", "true") == "true":
                pages[(lang, path)] = (meta, body)
        else:
            (OUT / rel).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(f, OUT / rel)

    for (lang, path), (meta, body) in pages.items():
        langs = " ".join(
            f'<a href="{url(l, path)}"{" class=current" if l == lang else ""}>{name}</a>'
            for l, name in LANGS.items() if (l, path) in pages
        )
        nav = " ".join(
            f'<a href="{url(lang, p)}">{html.escape(pages[(lang, p)][0].get("title", p))}</a>'
            for p in NAV if (lang, p) in pages
        )
        page = TEMPLATE.format(
            lang=lang, title=html.escape(meta.get("title", path)),
            description=html.escape(meta.get("description", "")),
            home=url(lang, "home"), langs=langs, nav=nav, body=body,
        )
        dest = OUT / url(lang, path).strip("/") / "index.html"
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(page, encoding="utf-8")
        # Old Wiki.js URLs keep working: /en/..., and /home, /en/home, /es/home, /pt/home.
        old = [f"en/{path}"] if lang == "en" else []
        if path == "home":
            old += ["home", "en"] if lang == "en" else [f"{lang}/home"]
        for o in old:
            redirect = OUT / o / "index.html"
            redirect.parent.mkdir(parents=True, exist_ok=True)
            redirect.write_text(f'<!DOCTYPE html><meta http-equiv="refresh" content="0; url={url(lang, path)}">'
                                f'<link rel="canonical" href="{url(lang, path)}">', encoding="utf-8")

    shutil.copy2(SRC / "style.css", OUT / "style.css")
    (OUT / "CNAME").write_text("womenpedia.org\n")
    (OUT / "404.html").write_text(TEMPLATE.format(
        lang="en", title="Page not found", description="", home="/", langs="",
        nav="", body='<h1>Page not found</h1><p><a href="/">Back to Womenpedia</a></p>'), encoding="utf-8")

    # Self-check: every internal link and image must resolve to a built file.
    broken = set()
    for page in OUT.rglob("*.html"):
        for ref in re.findall(r'(?:href|src)="(/[^"#?]*)', page.read_text(encoding="utf-8")):
            target = OUT / ref.strip("/")
            if not (target.is_file() or (target / "index.html").is_file()):
                broken.add(f"{page.relative_to(OUT)} -> {ref}")
    print(f"Built {len(pages)} pages into {OUT}")
    if broken:
        print("Broken links:\n  " + "\n  ".join(sorted(broken)))
        raise SystemExit(1)


if __name__ == "__main__":
    main()
