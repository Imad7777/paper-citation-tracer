#!/usr/bin/env python3
"""Highlight citation phrases in a PDF, based on real-world lit-review practice.

Given one or more short key phrases (extracted from a citation/quote), this tool
finds them in the PDF text and adds highlight annotations, then optionally
verifies that each highlight actually covers the intended sentence.

Why not a simple ``page.search_for(needle)``? Because PDF text extraction is
messy. This tool handles the three failure modes that break naive search:

1. Smart quotes / ligatures  ``don't`` vs ``don’t``, ``ﬁ`` vs ``fi``
2. Line breaks inside a phrase  ``holistic in\\nnature and``
3. De-hyphenation  ``cogni- tive`` (soft hyphen at line end)

References:
    https://pymupdf.readthedocs.io/

Usage:
    python highlight_citations.py paper.pdf \\
        -q "holistic in nature and involves" \\
        -q "cognitive, affective, emotional, social and physical" \\
        --pages 1-8 --max-n 2 --verify

Requires: pip install pymupdf
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import fitz  # PyMuPDF

__version__ = "1.0.0"

NAMED_COLORS = {
    "yellow": (1.0, 0.9, 0.3),
    "green": (0.55, 0.9, 0.55),
    "blue": (0.45, 0.7, 1.0),
    "red": (1.0, 0.5, 0.4),
}

_REF_HEADING = re.compile(r"^\s*(references|bibliography|文献)\s*:?\s*$",
                          re.IGNORECASE | re.MULTILINE)


# --------------------------------------------------------------------------
# normalization
# --------------------------------------------------------------------------

_CHAR_MAP = {
    "\u2018": "'", "\u2019": "'",          # curly single quotes
    "\u201c": '"', "\u201d": '"',          # curly double quotes
    "\u2010": "-", "\u2011": "-",          # hyphen variants
    "\u2013": "-", "\u2014": "-",          # en/em dash
    "\ufb00": "ff", "\ufb01": "fi",        # ligatures
    "\ufb02": "fl", "\ufb03": "ffi", "\ufb04": "ffl",
    "\u00a0": " ",                          # no-break space
}


def normalize(text: str) -> str:
    """Map PDF-typography characters to plain ASCII equivalents."""
    for k, v in _CHAR_MAP.items():
        text = text.replace(k, v)
    return text


def loose(text: str) -> str:
    """Aggressive form for fallback matching: lowercase, keep only
    alphanumerics and single spaces. De-hyphenates soft line breaks."""
    text = normalize(text).lower()
    text = re.sub(r"-\s*\n\s*", "", text)      # word- word  ->  wordword
    text = re.sub(r"[^0-9a-z\u4e00-\u9fff]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


# --------------------------------------------------------------------------
# matching strategies
# --------------------------------------------------------------------------

def _search_direct(page: fitz.Page, needle: str):
    """Strategy A: PyMuPDF's built-in search (works when the phrase sits on
    one line and characters already match after normalization)."""
    variants = [normalize(needle)]
    if "'" in needle:
        variants.append(needle.replace("'", "\u2019"))   # curly apostrophe
    if '"' in needle:
        variants.append(needle.replace('"', "\u201c"))   # curly double quote
    for v in dict.fromkeys(variants):
        rects = page.search_for(v)
        if rects:
            return rects
    return []


def _search_loose(page: fitz.Page, needle: str):
    """Strategy B: rebuild the page text from words and match the phrase in a
    typography-insensitive form, then map matched words back to rects.
    Handles line breaks, hyphenation and smart punctuation."""
    words = page.get_text("words")  # (x0, y0, x1, y1, word, block, line, wno)
    if not words:
        return []

    target = loose(needle)
    if not target:
        return []

    # build the loose page text plus a char -> word index map
    chars: list[tuple[str, int | None]] = []
    for i, w in enumerate(words):
        for ch in loose(w[4]):
            chars.append((ch, i))
        chars.append((" ", None))
    haystack = "".join(c for c, _ in chars)

    rects: list[fitz.Rect] = []
    start = 0
    while True:
        pos = haystack.find(target, start)
        if pos < 0:
            break
        start = pos + 1
        covered = {idx for _, idx in chars[pos:pos + len(target)] if idx is not None}
        if not covered:
            continue
        # group covered words per visual line so multi-line hits get one
        # highlight per line instead of one giant box
        by_line: dict[tuple[int, int], list[int]] = {}
        for wi in covered:
            w = words[wi]
            by_line.setdefault((w[5], w[6]), []).append(wi)
        for idxs in by_line.values():
            xs0 = min(words[i][0] for i in idxs)
            ys0 = min(words[i][1] for i in idxs)
            xs1 = max(words[i][2] for i in idxs)
            ys1 = max(words[i][3] for i in idxs)
            rects.append(fitz.Rect(xs0, ys0, xs1, ys1))
    return rects


def find_in_page(page: fitz.Page, needle: str) -> list[fitz.Rect]:
    rects = _search_direct(page, needle)
    if rects:
        return rects
    return _search_loose(page, needle)


# --------------------------------------------------------------------------
# reference-section detection
# --------------------------------------------------------------------------

def references_start_page(doc: fitz.Document) -> int | None:
    """First page whose top lines look like a References/Bibliography heading."""
    for pno in range(len(doc)):
        head = doc[pno].get_text("text")[:400]
        if _REF_HEADING.search(head):
            return pno
    return None


def parse_pages(spec: str, total: int) -> range:
    """'1-8' / '3-' / '-5' / 'all' (1-based, inclusive) -> 0-based range."""
    spec = spec.strip().lower()
    if spec in ("", "all"):
        return range(total)
    m = re.fullmatch(r"(\d*)\s*-\s*(\d*)", spec)
    if not m:
        raise argparse.ArgumentTypeError(f"bad --pages spec: {spec!r}")
    a = int(m.group(1)) - 1 if m.group(1) else 0
    b = int(m.group(2)) if m.group(2) else total
    a, b = max(0, a), min(total, max(b, 0))
    return range(a, b)


def parse_color(spec: str) -> tuple[float, float, float]:
    spec = spec.strip().lower()
    if spec in NAMED_COLORS:
        return NAMED_COLORS[spec]
    parts = [p.strip() for p in spec.split(",")]
    if len(parts) == 3:
        try:
            vals = tuple(float(p) for p in parts)
            if all(0.0 <= v <= 1.0 for v in vals):
                return vals  # type: ignore[return-value]
        except ValueError:
            pass
    raise argparse.ArgumentTypeError(
        f"bad --color {spec!r}: use a name {sorted(NAMED_COLORS)} or 'r,g,b' in 0-1")


# --------------------------------------------------------------------------
# main
# --------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        prog="highlight_citations",
        description="Highlight citation phrases in a PDF (agent-skill quality "
                    "matching: smart quotes, line breaks, de-hyphenation).")
    ap.add_argument("pdf", type=Path, help="input PDF (never modified)")
    ap.add_argument("-q", "--quote", action="append", default=[],
                    help="key phrase to highlight; repeatable. Prefer 8-25 "
                         "character distinctive phrases, no trailing periods.")
    ap.add_argument("--quotes-file", type=Path, default=None,
                    help="text file with one phrase per line (# comments ok)")
    ap.add_argument("-o", "--output", type=Path, default=None,
                    help="output path (default: <input>_highlighted.pdf)")
    ap.add_argument("--pages", default="all", type=str,
                    help="page range like 1-8, 3-, -5 (1-based); default: all")
    ap.add_argument("--max-n", type=int, default=3,
                    help="max highlights per phrase per PDF "
                         "(prevents 'whole page turns yellow'); default 3")
    ap.add_argument("--color", default="yellow", type=parse_color,
                    help="yellow/green/blue/red or 'r,g,b' 0-1 (default: yellow)")
    ap.add_argument("--opacity", type=float, default=1.0,
                    help="annotation opacity 0-1 (default 1.0)")
    ap.add_argument("--keep-references", action="store_true",
                    help="do not stop at the References/Bibliography section")
    ap.add_argument("--dry-run", action="store_true",
                    help="report matches only, write no file")
    ap.add_argument("--verify", action="store_true",
                    help="after saving, print the text under every highlight")
    args = ap.parse_args(argv)

    quotes = [q.strip() for q in args.quote if q.strip()]
    if args.quotes_file:
        for line in args.quotes_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#"):
                quotes.append(line)
    if not quotes:
        ap.error("no quotes given: use -q or --quotes-file")
    if not args.pdf.exists():
        ap.error(f"input not found: {args.pdf}")

    doc = fitz.open(args.pdf)
    pages = parse_pages(args.pages, len(doc))
    cut = None
    if not args.keep_references:
        cut = references_start_page(doc)
        if cut is not None:
            print(f"[info] References section starts at page {cut + 1}; "
                  f"will not scan pages >= {cut + 1} "
                  f"(override with --keep-references)")

    out_path = args.output or args.pdf.with_name(
        args.pdf.stem + "_highlighted" + args.pdf.suffix)

    # ---- match -----------------------------------------------------------
    # NOTE: keep ``page`` in a variable. ``doc[pno].add_highlight_annot(...)``
    # binds the annotation to a temporary Page object that is garbage
    # collected on the next loop iteration, and the annotation dies with it
    # ("annotation not bound to any page").
    total = 0
    report: list[tuple[str, int, list[int]]] = []
    for needle in quotes:
        hits = 0
        hit_pages: list[int] = []
        for pno in pages:
            if cut is not None and pno >= cut:
                break
            page = doc[pno]
            for rect in find_in_page(page, needle)[:max(0, args.max_n - hits)]:
                if not args.dry_run:
                    annot = page.add_highlight_annot(rect)
                    if annot is None:  # rare: MuPDF refused the rect
                        continue
                    annot.set_colors(stroke=args.color)  # type: ignore[arg-type]
                    annot.set_opacity(args.opacity)
                    annot.update()
                hits += 1
                hit_pages.append(pno + 1)
                if hits >= args.max_n:
                    break
            if hits >= args.max_n:
                break
        total += hits
        mark = "" if hits else "   <-- NO MATCH, try a shorter phrase"
        print(f"  [{hits}] {needle}{mark}")
        if hit_pages:
            print(f"       pages: {hit_pages}")
        report.append((needle, hits, hit_pages))

    if args.dry_run:
        print(f"[dry-run] {total} match(es); no file written")
        doc.close()
        return 0 if total else 1

    if total == 0:
        print("[warn] nothing matched; no output written")
        doc.close()
        return 1

    doc.save(out_path, garbage=4, deflate=True, clean=True)
    doc.close()
    print(f"[ok] {total} highlight(s) -> {out_path}")

    # ---- verification ----------------------------------------------------
    if args.verify:
        print("[verify] text under each highlight:")
        vdoc = fitz.open(out_path)
        for pno in range(len(vdoc)):
            page = vdoc[pno]
            for annot in page.annots() or ():
                if annot.type[1] != "Highlight":
                    continue
                snippet = page.get_text("text", clip=annot.rect).strip()
                snippet = re.sub(r"\s+", " ", snippet)
                if snippet:
                    print(f"  p{pno + 1}: {snippet[:110]}")
        vdoc.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
