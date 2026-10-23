"""Scan the text of a PDF (a demo guide, a handout) for things no learner should see.

    uv run --with pypdf python tools/scan/scan_pdf.py GUIDE.pdf [--account PATTERN ...]

Checks every page's text for: key-like text, host paths (user home folders), account links
(UUID-like ids, and links matching `--account` regexes, such as a vendor's workspace URL), and
placeholders left in the text (TODO, TBD, FIXME, XXX, lorem ipsum, `<ANGLE PLACEHOLDERS>`).
Prints the page number and kind per hit, with keys masked; exit 1 on any hit.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

from scan_secrets import find_host_paths, find_keys

UUID = re.compile(r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b", re.I)
PLACEHOLDERS = re.compile(r"\b(?:TODO|TBD|FIXME|XXX)\b|lorem ipsum|<[A-Z][A-Z _-]{2,}>")


def page_texts(path: Path) -> list[str]:
    from pypdf import PdfReader

    return [page.extract_text() or "" for page in PdfReader(str(path)).pages]


def scan_text(text: str, accounts: tuple[str, ...] = ()) -> dict[str, list[str]]:
    account = [m.group(0)[:8] + "…" for m in UUID.finditer(text)]
    for pattern in accounts:
        account += [m.group(0) for m in re.finditer(pattern, text, re.I)]
    return {
        "keys": [f"{h.kind}: {h.masked}" for h in find_keys(text)],
        "host_paths": find_host_paths(text),
        "accounts": account,
        "placeholders": [m.group(0) for m in PLACEHOLDERS.finditer(text)],
    }


def scan_pdf(path: Path, accounts: tuple[str, ...] = ()) -> dict[str, list[str]]:
    """{kind: ["p<page>: <hit>", ...]} over every page."""
    out: dict[str, list[str]] = {"keys": [], "host_paths": [], "accounts": [], "placeholders": []}
    for n, text in enumerate(page_texts(path), start=1):
        for kind, hits in scan_text(text, accounts).items():
            out[kind] += [f"p{n}: {h}" for h in hits]
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("pdf", type=Path)
    ap.add_argument("--account", action="append", default=[], help="regex of an account link")
    a = ap.parse_args(argv)
    found = scan_pdf(a.pdf, tuple(a.account))
    for kind, hits in found.items():
        print(f"{kind}: {bool(hits)}")
        for h in hits[:20]:
            print(f"  {h}")
    return 1 if any(found.values()) else 0


if __name__ == "__main__":
    sys.exit(main())
