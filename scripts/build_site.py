#!/usr/bin/env python3
"""Convert this booklet's LaTeX to a static site. Never modifies the source."""
import hashlib
import html
import json
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'docs'
SOURCE = ROOT / 'Economia_letture_progressive.tex'

def run(args, **kwargs):
    result = subprocess.run(args, text=True, capture_output=True, **kwargs)
    if result.returncode:
        raise RuntimeError(result.stderr + result.stdout[-4000:])
    return result.stdout

def group(text, start):
    while start < len(text) and text[start].isspace(): start += 1
    if text[start] != '{': raise ValueError(text[start:start+100])
    depth, i = 1, start + 1
    while depth:
        if text[i] == '\\': i += 2; continue
        if text[i] == '{': depth += 1
        if text[i] == '}': depth -= 1
        i += 1
    return text[start+1:i-1], i

def command(text, name, count, callback):
    pattern = re.compile(r'\\' + name + r'(?![A-Za-z])')
    while (match := pattern.search(text)):
        args, end = [], match.end()
        for _ in range(count):
            arg, end = group(text, end); args.append(arg)
        text = text[:match.start()] + callback(*args) + text[end:]
    return text

def graph(tex):
    digest = hashlib.sha256(tex.encode()).hexdigest()[:16]
    target = OUT / 'assets' / (digest + '.svg')
    if not target.exists():
        with tempfile.TemporaryDirectory() as temp:
            work = Path(temp)
            preamble = r'''\documentclass[border=5pt]{standalone}
\usepackage{fontspec,tikz,pgfplots}
\setmainfont{Latin Modern Roman}
\usetikzlibrary{arrows.meta,positioning}
\pgfplotsset{compat=1.18}
\definecolor{accent}{HTML}{25556B}
\begin{document}
'''
            # Match the original printed column width, independently of standalone.
            tex = tex.replace(r'\linewidth', '80mm')
            # Decimal multipliers need a TeX length, not concatenated units.
            tex = re.sub(r'([.]\d+)80mm', lambda m: str(float(m[1])*80)+'mm', tex)
            (work/'figure.tex').write_text(preamble+tex+r'\end{document}')
            run(['xelatex','-no-shell-escape','-interaction=nonstopmode','-halt-on-error','figure.tex'], cwd=work)
            run(['pdftocairo','-svg',str(work/'figure.pdf'),str(target)])
    return target.name

def convert(tex, references):
    fragments = {}
    def token(value):
        key = 'WEBPLACEHOLDER' + str(len(fragments)) + 'END'
        fragments[key] = value
        return key
    def simple(value):
        return run(['pandoc','-f','latex','-t','html5','--mathml'],input=value).strip().removeprefix('<p>').removesuffix('</p>')
    tex = re.sub(r'(?m)(?<!\\)%.*$', '', tex)
    tex = re.sub(r'\\begin\{tikzpicture\}[\s\S]*?\\end\{tikzpicture\}',
                 lambda m: token('<img class="diagram" alt="Diagramma della lettura" src="assets/'+graph(m[0])+'">'),tex)
    tex = command(tex,'voce',3,lambda a,b,c: token('<div class="vocab"><strong>'+simple(a)+'</strong><span lang="ar" dir="rtl">'+html.escape(c)+'</span><p>'+simple(b)+'.</p></div>'))
    tex = command(tex,'fonte',1,lambda key: token('<sup><a href="fonti.html#src-'+key+'" aria-label="Fonte '+str(references[key])+'">['+str(references[key])+']</a></sup>'))
    tex = command(tex,'ref',1,lambda key: str(references[key.removeprefix('src:')]))
    tex = command(tex,'captionof',2,lambda kind,caption: token('<p class="caption">'+simple(caption)+'</p>'))
    for key,title in [('attivita','Comprendere il testo'),('lessico','Parole da riutilizzare'),('lingua','Lavorare sulla lingua'),('scrittura','Rielaborare')]:
        tex = re.sub(r'\\'+key+r'(?![A-Za-z])',lambda m:r'\subsection*{'+title+'}',tex)
    tex = re.sub(r'\\begin\{minipage\}\{\\linewidth\}|\\end\{minipage\}', '',tex)
    tex = re.sub(r'\\(centering|small|noindent)(?![A-Za-z])','',tex)
    tex = tex.replace(r'\righe','')
    # Pandoc understands native tables, lists, formatting and formulas.
    ast = json.loads(run(['pandoc','-f','latex','-t','json'],input=tex))
    def check(node):
        if isinstance(node,dict):
            if node.get('t') in ('RawInline','RawBlock') and node['c'][0] == 'latex':
                raise ValueError('Unsupported LaTeX (conversion stopped): '+str(node['c']))
            for value in node.values(): check(value)
        elif isinstance(node,list):
            for value in node: check(value)
    check(ast)
    rendered = run(['pandoc','-f','json','-t','html5','--mathml'],input=json.dumps(ast))
    # Remove paragraph wrappers around isolated block placeholders before insertion.
    rendered = re.sub(r'<p>((?:WEBPLACEHOLDER\d+END\s*)+)</p>',r'\1',rendered)
    for key,value in fragments.items(): rendered = rendered.replace(key,value)
    return rendered

def main():
    OUT.mkdir(exist_ok=True); (OUT/'assets').mkdir(exist_ok=True)
    source = SOURCE.read_text()
    clean = re.sub(r'(?m)(?<!\\)%.*$', '',source)
    matches = re.findall(r'\\begin\{lettura\}\{([01])\}\{([^}]+)\}([\s\S]*?)\\end\{lettura\}', clean)
    chapters = [(title,body) for active,title,body in matches if active == '1']
    if not chapters: raise ValueError('No active chapters')
    entries = re.findall(r'\\item\\label\{src:([^}]+)\}([\s\S]*?)(?=\\item\\label|\\end\{enumerate\})', clean)
    refs = {key:i+1 for i,(key,_) in enumerate(entries)}
    nav = '<a href="index.html">Indice</a>' + ''.join(f'<a href="lettura-{i:02}.html"><span>{i:02}</span> {html.escape(title)}</a>' for i,(title,_) in enumerate(chapters,1)) + '<a href="fonti.html">Fonti e riferimenti</a>'
    def page(filename,title,body,number=None):
        pager = ''
        if number:
            pager = '<nav class="pager" aria-label="Letture adiacenti">'
            if number>1: pager += f'<a href="lettura-{number-1:02}.html">← Lettura precedente</a>'
            if number<len(chapters): pager += f'<a href="lettura-{number+1:02}.html">Lettura successiva →</a>'
            pager += '</nav>'
        output = f'''<!doctype html><html lang="it"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{html.escape(title)} · Economia</title><link rel="stylesheet" href="style.css"></head><body><a class="skip" href="#lettura">Vai al testo</a><aside><a class="brand" href="index.html">Economia:<br>leggere e capire</a><details open><summary>Le letture</summary><nav aria-label="Indice delle letture">{nav}</nav></details></aside><main id="lettura"><header><p class="eyebrow">{'LETTURA '+str(number).zfill(2) if number else 'DON BOSCO · MATERIALI DI ECONOMIA'}</p><h1>{html.escape(title)}</h1></header><article>{body}</article>{pager}<footer>Materiali di Marco Giovanni Ferrari · Versione di lavoro<br>Generato dal sorgente LaTeX. L'impaginazione web è distinta da quella per la stampa.</footer></main></body></html>'''
        (OUT/filename).write_text(output)
    for i,(title,body) in enumerate(chapters,1):
        page(f'lettura-{i:02}.html',title,convert(body,refs),i)
    intro = '<p>Un percorso di lettura, lessico economico e comprensione del testo.</p><ol class="contents">'+''.join(f'<li><a href="lettura-{i:02}.html">{html.escape(title)}</a></li>' for i,(title,_) in enumerate(chapters,1))+'</ol>'
    page('index.html','Letture di economia',intro)
    bibliography = '<ol>'+''.join('<li id="src-'+key+'">'+convert(body,refs)+'</li>' for key,body in entries)+'</ol>'
    page('fonti.html','Fonti e riferimenti',bibliography)
    shutil.copyfile(ROOT/'web/style.css',OUT/'style.css')
    (OUT/'.nojekyll').write_text('')
    # Audit every internal target and asset before publishing.
    from html.parser import HTMLParser
    class Links(HTMLParser):
        def handle_starttag(self,tag,attrs):
            for name,value in attrs:
                if name in ('href','src') and value and not value.startswith(('http:','https:','#')):
                    if not (OUT/value.split('#')[0]).is_file(): raise ValueError('Missing target: '+value)
    for path in OUT.glob('*.html'): Links().feed(path.read_text())
    print(f'Validated {len(chapters)} chapters, {len(entries)} sources, {len(list((OUT/"assets").glob("*.svg")))} diagrams.')

if __name__ == '__main__': main()
