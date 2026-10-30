"""Every ``tools/*.py`` entry point must treat ``--help`` as a dry run.

Thirty drivers in ``tools/`` execute their analysis from the ``__main__`` block
and read no arguments at all.  ``python3 tools/wave195_p2_r_level_power.py
--help`` therefore ran the power analysis and rewrote its evidence, which is
how sixteen files under ``verification_outputs/`` were overwritten during a
smoke test on 2026-10-30 (restored from git; see
``docs/audit/doc-anchor-audit.md`` section 6).

Each of those drivers now opens its ``__main__`` block with

    if {"-h", "--help"} & set(sys.argv[1:]):
        print(__doc__)
        raise SystemExit(0)

This test pins the invariant statically -- the guard must be the *first*
statement of the block -- and once dynamically, on a copy of a driver run
inside ``tmp_path`` so a regression fails the test instead of rewriting a
figure in the repository.
"""

from __future__ import annotations

import ast
import pathlib
import shutil
import subprocess
import sys

import pytest

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
TOOLS = REPO_ROOT / "tools"

MAIN_TEST = "__name__ == '__main__'"


def _main_block(tree: ast.Module) -> ast.If | None:
    for node in tree.body:
        if isinstance(node, ast.If) and ast.unparse(node.test) == MAIN_TEST:
            return node
    return None


def _has_cli(tree: ast.Module, source: str) -> bool:
    """True when the module parses its own arguments."""
    return "sys.argv" in source or "parse_args" in source


def _has_help_guard(block: ast.If) -> bool:
    if not block.body:
        return False
    first = block.body[0]
    return (
        isinstance(first, ast.If)
        and "--help" in ast.unparse(first.test)
        and "__doc__" in ast.unparse(first)
    )


def _violations(root: pathlib.Path) -> list[str]:
    out: list[str] = []
    for path in sorted(root.glob("*.py")):
        source = path.read_text(encoding="utf-8")
        try:
            tree = ast.parse(source)
        except SyntaxError:
            continue
        block = _main_block(tree)
        if block is None:
            continue
        if _has_cli(tree, source):
            continue
        if not _has_help_guard(block):
            out.append(path.name)
    return out


def test_every_driver_honours_help() -> None:
    assert _violations(TOOLS) == []


def test_the_invariant_is_not_vacuous() -> None:
    """At least one driver relies on the guard rather than on argparse."""
    guarded = [
        path.name
        for path in sorted(TOOLS.glob("*.py"))
        if (block := _main_block(ast.parse(path.read_text(encoding="utf-8")))) is not None
        and _has_help_guard(block)
    ]
    assert len(guarded) >= 30


def test_a_driver_that_ignores_argv_is_reported(tmp_path) -> None:
    (tmp_path / "bad.py").write_text(
        '"""Doc."""\n\n\ndef main() -> None:\n    open("x", "w").write("y")\n\n\n'
        'if __name__ == "__main__":\n    main()\n',
        encoding="utf-8",
    )
    assert _violations(tmp_path) == ["bad.py"]


def test_help_exits_before_work(tmp_path) -> None:
    """A copy of a real driver prints its docstring and writes nothing."""
    driver = TOOLS / "render_r5c_regime_curve.py"
    target = tmp_path / "tools" / driver.name
    target.parent.mkdir()
    shutil.copy2(driver, target)

    proc = subprocess.run(
        [sys.executable, str(target), "--help"],
        capture_output=True,
        text=True,
        timeout=60,
    )

    assert proc.returncode == 0, proc.stderr
    assert "R5c regime-dependent curve" in proc.stdout
    assert not (tmp_path / "docs").exists()


@pytest.mark.parametrize("flag", ["-h", "--help"])
def test_both_help_spellings_are_honoured(tmp_path, flag) -> None:
    driver = TOOLS / "render_r5c_regime_curve.py"
    target = tmp_path / "tools" / driver.name
    target.parent.mkdir()
    shutil.copy2(driver, target)

    proc = subprocess.run(
        [sys.executable, str(target), flag],
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert proc.returncode == 0
    assert "Render the R5c" in proc.stdout
