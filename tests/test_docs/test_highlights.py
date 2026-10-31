"""The highlights file is the one package surface with a hard word limit.

TNNLS (like most IEEE journals) caps each highlight at 25 words. The file is
the only place the submission says something in its own words rather than
quoting a measured number, so it is also the only place where an edit can
break a submission requirement without breaking a number.

``tnnls_submission/README.md`` used to say to check this with

    awk '/^[0-9]\\./ {print NF-1, $0}' tnnls_submission/highlights.md

which counts the first *line* of each highlight. The highlights wrap, so that
command reported 13 / 13 / 9 / 11 / 10 for text that is really 18 / 23 / 18 /
21 / 15 -- an undercount of up to 40%, in the direction that lets an over-long
highlight through. The README now carries a command that counts the whole
paragraph; these tests hold the invariant itself.
"""
from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
HIGHLIGHTS = REPO_ROOT / "tnnls_submission" / "highlights.md"

LIMIT = 25

_ITEM_RE = re.compile(r"^(?P<num>\d+)\.\s+(?P<body>.*?)(?=^\d+\.\s|\Z)", re.M | re.S)


def _highlights(path: Path = HIGHLIGHTS) -> list[tuple[int, str]]:
    text = path.read_text(encoding="utf-8")
    out: list[tuple[int, str]] = []
    for m in _ITEM_RE.finditer(text):
        # A highlight ends at the first blank line; anything after it is
        # prose that belongs to the file, not to the numbered item.
        body = m.group("body").strip().split("\n\n")[0]
        out.append((int(m.group("num")), body))
    return out


def test_the_package_carries_five_highlights() -> None:
    items = _highlights()
    assert [n for n, _ in items] == [1, 2, 3, 4, 5], items


def test_no_highlight_exceeds_the_journal_limit() -> None:
    over = [(n, len(b.split()), b) for n, b in _highlights() if len(b.split()) > LIMIT]
    assert not over, "\n".join(f"highlight {n}: {w} words > {LIMIT}: {b[:80]}" for n, w, b in over)


def test_a_long_highlight_is_actually_caught(tmp_path) -> None:
    """Pin the failure mode: a 26-word highlight must not pass the limit test."""
    body = " ".join(["word"] * 26)
    fake = tmp_path / "highlights.md"
    fake.write_text(f"1. {body}\n2. short one\n", encoding="utf-8")

    items = _highlights(fake)
    assert len(items) == 2
    assert len(items[0][1].split()) == 26
    assert [n for n, b in items if len(b.split()) > LIMIT] == [1]
