#!/usr/bin/env python3
"""Render the printable HTML booklet to PDF with WeasyPrint."""

from pathlib import Path

from weasyprint import HTML


ROOT = Path(__file__).resolve().parents[1]
source = ROOT / "docs" / "libretto.html"
target = ROOT / "docs" / "economia-leggere-e-capire.pdf"

if not source.is_file():
    raise SystemExit("Run scripts/build_site.py before building the PDF")

HTML(filename=source).write_pdf(target)
if target.stat().st_size < 10_000 or target.read_bytes()[:5] != b"%PDF-":
    raise RuntimeError("The generated PDF did not pass the basic integrity check")

print(f"Generated {target.name} ({target.stat().st_size // 1024} KiB).")
