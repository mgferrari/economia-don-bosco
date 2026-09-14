#!/usr/bin/env python3
"""Build the website and printable HTML from editable HTML fragments."""

import html
import json
import re
import shutil
from html.parser import HTMLParser
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CONTENT = ROOT / "content"
CHAPTERS = CONTENT / "chapters"
WEB = ROOT / "web"
OUT = ROOT / "docs"
PDF_NAME = "economia-leggere-e-capire.pdf"


def load_manifest():
    manifest = json.loads((CONTENT / "site.json").read_text())
    chapters = manifest["chapters"]
    numbers = [chapter["number"] for chapter in chapters]
    if numbers != list(range(1, len(chapters) + 1)):
        raise ValueError("Chapter numbers must be consecutive and start at 1")
    files = [chapter["file"] for chapter in chapters]
    if len(files) != len(set(files)):
        raise ValueError("Each chapter must use a different source file")
    return manifest, chapters


def source_numbers(sources):
    keys = re.findall(r'<li\s+id="src-([^"]+)"', sources)
    if not keys or len(keys) != len(set(keys)):
        raise ValueError("Source identifiers are missing or duplicated")
    return {key: number for number, key in enumerate(keys, 1)}


def citations(body, references, printable=False):
    used = []

    def replace(match):
        key = match.group(1)
        if key not in references:
            raise ValueError(f"Unknown source identifier: {key}")
        used.append(key)
        href = f"#src-{key}" if printable else f"fonti.html#src-{key}"
        number = references[key]
        return (
            f'<sup><a href="{href}" aria-label="Fonte {number}">'
            f'[{number}]</a></sup>'
        )

    rendered = re.sub(
        r'<sup><a\s+data-source="([^"]+)"\s*></a></sup>', replace, body
    )
    if "data-source=" in rendered:
        raise ValueError("Unsupported citation markup")
    return rendered, used


def navigation(chapters):
    links = ['<a href="index.html">Indice</a>']
    links.extend(
        f'<a href="lettura-{c["number"]:02}.html">'
        f'<span>{c["number"]:02}</span> {html.escape(c["title"])}</a>'
        for c in chapters
    )
    links.append('<a href="fonti.html">Fonti e riferimenti</a>')
    links.append(f'<a class="pdf-link" href="{PDF_NAME}">Scarica il PDF</a>')
    return "".join(links)


def page(title, body, nav, number=None, pager=""):
    eyebrow = (
        f"LETTURA {number:02}" if number else "DON BOSCO · MATERIALI DI ECONOMIA"
    )
    return f'''<!doctype html>
<html lang="it">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>{html.escape(title)} · Economia</title>
  <link rel="stylesheet" href="style.css">
</head>
<body>
  <a class="skip" href="#lettura">Vai al testo</a>
  <aside>
    <a class="brand" href="index.html">Economia:<br>leggere e capire</a>
    <details open><summary>Le letture</summary>
      <nav aria-label="Indice delle letture">{nav}</nav>
    </details>
  </aside>
  <main id="lettura">
    <header><p class="eyebrow">{eyebrow}</p><h1>{html.escape(title)}</h1></header>
    <article>{body}</article>
    {pager}
    <footer>Materiali di Marco Giovanni Ferrari · Versione di lavoro<br>
      Sito e PDF generati dagli stessi sorgenti HTML.</footer>
  </main>
</body>
</html>
'''


def pager(number, total):
    links = []
    if number > 1:
        links.append(
            f'<a href="lettura-{number-1:02}.html">← Lettura precedente</a>'
        )
    if number < total:
        links.append(
            f'<a href="lettura-{number+1:02}.html">Lettura successiva →</a>'
        )
    return (
        '<nav class="pager" aria-label="Letture adiacenti">'
        + "".join(links)
        + "</nav>"
    )


def printable_document(manifest, chapters, bodies, sources, references):
    toc = []
    sections = []
    for chapter, body in zip(chapters, bodies):
        if chapter.get("part"):
            toc.append(f'<li class="toc-part">{html.escape(chapter["part"])}</li>')
        number = chapter["number"]
        title = html.escape(chapter["title"])
        toc.append(
            f'<li><a href="#lettura-{number:02}"><span>{number:02}</span>{title}</a></li>'
        )
        rendered, _ = citations(body, references, printable=True)
        part = ""
        if chapter.get("part"):
            part = f'<p class="part-label">{html.escape(chapter["part"])}</p>'
        sections.append(
            f'<section class="print-chapter" id="lettura-{number:02}">{part}'
            f'<p class="chapter-number">LETTURA {number:02}</p>'
            f'<h1>{title}</h1><article>{rendered}</article></section>'
        )
    front = (CONTENT / "front-matter.html").read_text()
    return f'''<!doctype html>
<html lang="it">
<head>
  <meta charset="utf-8">
  <title>{html.escape(manifest["title"])}</title>
  <meta name="author" content="Marco Giovanni Ferrari">
  <link rel="stylesheet" href="print.css">
</head>
<body>
  <section class="title-page">
    <p>Materiali di economia</p>
    <h1>Economia:<br>leggere e capire</h1>
    <h2>Letture progressive per un anno scolastico</h2>
    <div class="title-rule"></div>
    <p>Scuola secondaria superiore<br>Italiano, lessico economico e comprensione del testo</p>
    <p class="author">Materiali di Marco Giovanni Ferrari<br>Versione di lavoro — settembre 2026</p>
  </section>
  {front}
  <nav class="print-toc"><h1>Indice</h1><ol>{''.join(toc)}</ol></nav>
  {''.join(sections)}
  <section class="print-sources" id="fonti"><h1>Fonti e riferimenti</h1>
    <p>I riferimenti sostengono definizioni, dati e passaggi storici specifici; esempi immaginari, esercizi e formulazioni didattiche sono originali.</p>
    {sources}
  </section>
</body>
</html>
'''


class LinkAudit(HTMLParser):
    def __init__(self, current):
        super().__init__()
        self.current = current

    def handle_starttag(self, tag, attrs):
        values = dict(attrs)
        if tag in {"script", "iframe", "object", "embed"}:
            raise ValueError(f"Unsupported <{tag}> in {self.current.name}")
        for name in ("href", "src"):
            value = values.get(name)
            if not value or value.startswith(("http:", "https:", "#", "mailto:")):
                continue
            if value == PDF_NAME:
                # The PDF is created immediately after this build step.
                continue
            target = OUT / value.split("#", 1)[0]
            if not target.is_file():
                raise ValueError(f"Missing target {value} in {self.current.name}")


def main():
    manifest, chapters = load_manifest()
    sources = (CONTENT / "sources.html").read_text()
    references = source_numbers(sources)
    bodies = [(CHAPTERS / chapter["file"]).read_text() for chapter in chapters]

    OUT.mkdir(exist_ok=True)
    nav = navigation(chapters)
    used_sources = set()
    for chapter, body in zip(chapters, bodies):
        number = chapter["number"]
        rendered, used = citations(body, references)
        used_sources.update(used)
        (OUT / f"lettura-{number:02}.html").write_text(
            page(
                chapter["title"], rendered, nav, number, pager(number, len(chapters))
            )
        )

    intro = (
        '<p>Un percorso di lettura, lessico economico e comprensione del testo.</p>'
        f'<p><a class="download" href="{PDF_NAME}">Scarica il libretto completo in PDF</a></p>'
        '<ol class="contents">'
        + "".join(
            f'<li><a href="lettura-{c["number"]:02}.html">'
            f'{html.escape(c["title"])}</a></li>'
            for c in chapters
        )
        + "</ol>"
    )
    (OUT / "index.html").write_text(page("Letture di economia", intro, nav))
    (OUT / "fonti.html").write_text(page("Fonti e riferimenti", sources, nav))
    (OUT / "libretto.html").write_text(
        printable_document(manifest, chapters, bodies, sources, references)
    )

    shutil.copyfile(WEB / "style.css", OUT / "style.css")
    shutil.copyfile(WEB / "print.css", OUT / "print.css")
    if (OUT / "assets").exists():
        shutil.rmtree(OUT / "assets")
    shutil.copytree(WEB / "assets", OUT / "assets")
    (OUT / ".nojekyll").write_text("")

    expected = {f"lettura-{i:02}.html" for i in range(1, len(chapters) + 1)}
    for old_page in OUT.glob("lettura-*.html"):
        if old_page.name not in expected:
            old_page.unlink()

    for path in OUT.glob("*.html"):
        LinkAudit(path).feed(path.read_text())

    unused = set(references) - used_sources
    if unused:
        raise ValueError(f"Sources not cited by any chapter: {sorted(unused)}")
    print(
        f"Validated {len(chapters)} HTML chapters, {len(references)} sources "
        f"and {len(list((OUT / 'assets').iterdir()))} assets."
    )


if __name__ == "__main__":
    main()
