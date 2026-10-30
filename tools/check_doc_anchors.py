#!/usr/bin/env python3
"""Verify that every ``page.md#anchor`` link points at a heading that exists.

``tools/check_doc_links.py`` resolves the *file* half of a relative link and
deliberately drops the fragment (``target.split("#")[0]``), so 101 fragment
links were never checked.  ``mkdocs build --strict`` does not check them
either: it validates that a target page exists, not that the fragment matches a
heading on it.

The anchors are not guessable.  The site renders with Python-Markdown's ``toc``
extension and no custom ``slugify``, which strips every non-ASCII character:
``## 1. 背景：paper 在解决什么问题`` becomes ``id="1-paper"``, and a heading that
is entirely Chinese becomes ``id="_1"``.  A link written as ``#背景`` therefore
resolves to nothing on the built page even though it looks right in the source.
That is why this tool renders each page with the same extension stack instead
of reimplementing the slug rule.

Requires the ``markdown`` package (a mkdocs dependency).  Without it the tool
prints ``SKIP`` and exits 0, so it is safe to call from a bare interpreter;
CI runs it in the job that installs the docs toolchain.

Usage::

    python3 tools/check_doc_anchors.py
"""

from __future__ import annotations

import pathlib
import re
import sys

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]

#: Same extension list as ``mkdocs.yml``.  ``toc`` is what assigns the ids.
EXTENSIONS = ["toc", "attr_list", "md_in_html", "pymdownx.superfences"]

_LINK = re.compile(r"\[[^\]]*\]\(([^)\s]+)\)")
_FENCE = re.compile(r"```.*?```", re.S)


def _sources() -> list[pathlib.Path]:
    """Every markdown file whose links a reader can click."""
    out: list[pathlib.Path] = []
    out += [p for p in (REPO_ROOT / "docs").rglob("*.md") if "ARCHIVE" not in p.parts]
    out += sorted(REPO_ROOT.glob("*.md"))
    out += sorted((REPO_ROOT / "tnnls_submission").rglob("*.md"))
    return out


def _anchors(path: pathlib.Path, markdown_module) -> set[str]:
    """Heading ids exactly as the site build assigns them."""
    md = markdown_module.Markdown(extensions=EXTENSIONS, output_format="html5")
    md.convert(path.read_text(encoding="utf-8", errors="ignore"))

    found: set[str] = set()

    def walk(tokens) -> None:
        for token in tokens:
            if token.get("id"):
                found.add(token["id"])
            walk(token.get("children", []))

    walk(md.toc_tokens)
    source = path.read_text(encoding="utf-8", errors="ignore")
    # attr_list anchors (``## Heading {#CLM-059}``) are emitted verbatim.
    found.update(re.findall(r"\{#([A-Za-z0-9_.:-]+)\}", source))
    # Raw HTML anchors (``<a id="背景"></a>``) survive ``md_in_html`` and are the
    # only way a Chinese heading can have a readable id -- ``toc``'s slugify
    # strips the characters that would have formed one.
    found.update(re.findall(r"<a\s+(?:id|name)=[\"']([^\"']+)[\"']", source))
    return found


def check() -> tuple[int, list[tuple[str, str, str]]]:
    """Return (links checked, [(source, link, reason)])."""
    try:
        import markdown  # noqa: PLC0415 -- optional dependency, probed at run time
    except ModuleNotFoundError:
        return 0, []

    cache: dict[pathlib.Path, set[str]] = {}
    problems: list[tuple[str, str, str]] = []
    checked = 0

    for source in _sources():
        text = _FENCE.sub("", source.read_text(encoding="utf-8", errors="ignore"))
        for match in _LINK.finditer(text):
            link = match.group(1)
            if "#" not in link or link.startswith(("http://", "https://", "mailto:")):
                continue
            page, fragment = link.split("#", 1)
            if not fragment:
                continue
            target = (source.parent / page).resolve() if page else source.resolve()
            if not target.is_file():
                continue  # the file half is check_doc_links' job
            checked += 1
            if target not in cache:
                cache[target] = _anchors(target, markdown)
            if fragment not in cache[target]:
                problems.append((source.relative_to(REPO_ROOT).as_posix(), link, str(target.relative_to(REPO_ROOT))))

    return checked, problems


def main() -> int:
    checked, problems = check()
    if checked == 0 and not problems:
        print("SKIP: the markdown package is not installed (it ships with mkdocs)")
        return 0
    for source, link, target in problems:
        print(f"BROKEN {source}: {link} -> no heading with that id in {target}")
    if problems:
        print(f"FAIL: {len(problems)} of {checked} fragment links resolve to no heading")
        return 1
    print(f"OK: {checked} fragment links resolve")
    return 0


if __name__ == "__main__":
    sys.exit(main())
