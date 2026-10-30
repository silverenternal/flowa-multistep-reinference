"""The evidence tree must survive a clone.

`verification_outputs/` is gitignored (`.gitignore:64`) and force-added file by
file, with no written rule for which files get added. `paper-data/` and
`docs/headline-evidence/` are built out of symlinks into it. The combination
produced 29 links that resolved on the author's machine and dangled on every
clone — invisible to the rest of the gate chain, which only ever runs in the
working tree.

`tools/check_clone_integrity.py` walks `git ls-files --stage` for mode 120000
entries and resolves each one. These tests pin it.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
TOOL = REPO_ROOT / "tools" / "check_clone_integrity.py"


def _load() -> ModuleType:
    spec = importlib.util.spec_from_file_location("_clone_integrity", str(TOOL))
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["_clone_integrity"] = module
    spec.loader.exec_module(module)
    return module


def test_no_tracked_symlink_dangles() -> None:
    tool = _load()
    rows, counts = tool.check()
    broken = [r for r in rows if r["status"] == "broken"]
    assert not broken, (
        "tracked symlink(s) dangle on a clone; force-add the target "
        f"(git add -f <path>) or exempt with a reason: {broken[:5]}"
    )
    assert counts["broken"] == 0
    assert counts["ok"] + counts["build-output"] + counts["exempt"] > 100


def test_every_exemption_names_a_tracked_link() -> None:
    tool = _load()
    links = {link for link, _ in tool.tracked_symlinks()}
    for link, target in tool.KNOWN_DANGLING:
        assert link in links, f"exemption names a link that is not tracked: {link}"
        assert target, "exemption must record the resolved target"


def test_build_output_links_have_a_tracked_source() -> None:
    tool = _load()
    rows, _ = tool.check()
    for row in rows:
        if row["status"] == "build-output":
            assert tool._build_source(row["target"]) is not None, (
                f"{row['link']} points at a build output with no source file"
            )


def test_build_source_rejects_a_figure_that_does_not_exist() -> None:
    tool = _load()
    assert tool._build_source("site/figures/fig1_flowa_architecture.png") is not None
    assert tool._build_source("site/figures/figZZ_not_a_real_figure.png") is None


def test_paper_data_links_resolve() -> None:
    """`paper-data/` is the reviewer-facing data package; nothing there may dangle."""
    tool = _load()
    rows, _ = tool.check()
    bad = [r for r in rows
           if r["status"] != "ok" and r["link"].startswith("paper-data/")]
    assert not bad, f"paper-data link(s) do not resolve: {bad}"
