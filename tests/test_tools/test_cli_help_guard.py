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

A driver that reads no arguments at all also cannot honour one, so the guard
is followed by a rejection: any argument other than ``-h``/``--help`` exits 2
with a message instead of running the default configuration.  Before that,
``--seed 7`` on such a driver ran the analysis and rewrote its evidence --
the same failure as ``--help``, one flag over.  Drivers that genuinely read
``sys.argv`` (``run_real_ckpt_eval``, the three that take a list of paths) are
not touched: they have their own argument handling, and rejecting their flags
would break them.

A second class surfaced on the same day: modules that do their work at
*module level*, with no ``__main__`` block at all.
``tools/build_verification_manifest.py --help`` regenerated the git-tracked
``verification_outputs/MANIFEST.md`` (115 lines changed) and then exited 1 on
its unclassified-file check.  Those modules carry the same guard at module
level, before their first effectful statement.  Underscore-prefixed modules
are internal libraries imported by other drivers (``_sota_common``,
``_figures_common``, ``_kanzi_sweep_runner``), so a guard there would fire on
the *importer's* argv and they are exempt.
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
SCRIPTS = REPO_ROOT / "scripts"

MAIN_TEST = "__name__ == '__main__'"


def _main_block(tree: ast.Module) -> ast.If | None:
    for node in tree.body:
        if isinstance(node, ast.If) and ast.unparse(node.test) == MAIN_TEST:
            return node
    return None


def _has_cli(source: str) -> bool:
    """True when the module parses its own arguments with argparse.

    The earlier version of this predicate accepted any use of ``sys.argv``,
    which exempted the four drivers that read ``sys.argv`` as a list of file
    paths -- ``r3_reaggregate_paired_ci.py`` treated ``--help`` as a filename
    and raised ``FileNotFoundError``.  Only argparse honours ``--help`` for
    free, so only argparse counts.
    """
    return "parse_args(" in source


#: Import-time configuration that is not a side effect worth guarding
#: against: ``matplotlib.use("Agg")`` and ``sys.path.insert(...)`` both have
#: to run before the figure code can even be imported.
_SAFE_CALLS = frozenset({"use", "insert"})


def _is_effectful(node: ast.stmt) -> bool:
    """True for a top-level statement that does work when the module loads."""
    if isinstance(node, ast.Expr):
        call = node.value
        if isinstance(call, ast.Constant):  # docstring
            return False
        if isinstance(call, ast.Call) and isinstance(call.func, ast.Attribute):
            return call.func.attr not in _SAFE_CALLS
        return True
    return isinstance(
        node,
        (ast.For, ast.AsyncFor, ast.While, ast.With, ast.AsyncWith, ast.Try,
         ast.Raise, ast.Assert, ast.Delete, ast.Return),
    )


def _module_guard_before_effects(tree: ast.Module) -> bool:
    """A guard at module level, placed before the first statement that acts.

    A module that never acts at import (a library such as ``_sota_common``)
    needs no guard: ``--help`` on it prints nothing and writes nothing.
    """
    for node in tree.body:
        if (
            isinstance(node, ast.If)
            and "--help" in ast.unparse(node.test)
            and "__doc__" in ast.unparse(node)
        ):
            return True
        if _is_effectful(node):
            return False
    return True


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
        if _has_cli(source):
            continue
        block = _main_block(tree)
        if block is not None:
            if not _has_help_guard(block):
                out.append(path.name)
        elif not path.name.startswith("_") and not _module_guard_before_effects(tree):
            # No ``__main__`` block: the body runs on import, so ``--help``
            # has to be honoured at module level.  ``build_verification_
            # manifest.py`` regenerated ``verification_outputs/MANIFEST.md``
            # this way on 2026-10-30.  Underscore-prefixed modules are
            # internal libraries (``_sota_common``, ``_figures_common``,
            # ``_kanzi_sweep_runner``) that other drivers import; a guard in
            # one of those would fire on the importer's argv.
            out.append(path.name)
    return out


def test_every_driver_honours_help() -> None:
    assert _violations(TOOLS) == []
    assert _violations(SCRIPTS) == []


def test_the_invariant_is_not_vacuous() -> None:
    """At least one driver relies on the guard rather than on argparse."""
    guarded = [
        path.name
        for root in (TOOLS, SCRIPTS)
        for path in sorted(root.glob("*.py"))
        if (block := _main_block(ast.parse(path.read_text(encoding="utf-8")))) is not None
        and _has_help_guard(block)
    ]
    assert len(guarded) >= 100


def test_a_driver_that_ignores_argv_is_reported(tmp_path) -> None:
    (tmp_path / "bad.py").write_text(
        '"""Doc."""\n\n\ndef main() -> None:\n    open("x", "w").write("y")\n\n\n'
        'if __name__ == "__main__":\n    main()\n',
        encoding="utf-8",
    )
    assert _violations(tmp_path) == ["bad.py"]


def test_a_script_with_no_main_block_is_reported(tmp_path) -> None:
    """The body runs on import, so the guard has to be at module level."""
    (tmp_path / "bare.py").write_text(
        '"""Doc."""\n\nimport os\n\nos.makedirs("out", exist_ok=True)\n',
        encoding="utf-8",
    )
    assert _violations(tmp_path) == ["bare.py"]


def test_a_module_level_guard_placed_before_the_work_is_accepted(tmp_path) -> None:
    (tmp_path / "ok.py").write_text(
        '"""Doc."""\n\nimport os\nimport sys\n\n'
        'if {"-h", "--help"} & set(sys.argv[1:]):\n'
        "    print(__doc__)\n    raise SystemExit(0)\n\n"
        'os.makedirs("out", exist_ok=True)\n',
        encoding="utf-8",
    )
    assert _violations(tmp_path) == []


def test_a_module_level_guard_placed_after_the_work_is_reported(tmp_path) -> None:
    (tmp_path / "late.py").write_text(
        '"""Doc."""\n\nimport os\nimport sys\n\n'
        'os.makedirs("out", exist_ok=True)\n\n'
        'if {"-h", "--help"} & set(sys.argv[1:]):\n'
        "    print(__doc__)\n    raise SystemExit(0)\n",
        encoding="utf-8",
    )
    assert _violations(tmp_path) == ["late.py"]


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


# ---------------------------------------------------------------------------
# Unknown flags on a driver that reads no arguments
# ---------------------------------------------------------------------------

_REJECTION_MARKER = "this driver takes no arguments"


def test_a_driver_that_ignores_argv_rejects_a_flag(tmp_path) -> None:
    """``--seed 7`` must exit 2 and write nothing, not run the default."""
    script = tmp_path / "fixed.py"
    script.write_text(
        '"""Doc."""\n\nimport sys\n\n\n'
        'def main() -> int:\n'
        '    open("ran.txt", "w").write("y")\n'
        "    return 0\n\n\n"
        'if __name__ == "__main__":\n'
        '    if {"-h", "--help"} & set(sys.argv[1:]):\n'
        "        print(__doc__)\n"
        "        raise SystemExit(0)\n"
        "    if len(sys.argv) > 1:\n"
        "        print("
        'f"{sys.argv[0]}: ' + _REJECTION_MARKER + '; "'
        'f"got {sys.argv[1:]}.", file=sys.stderr)\n'
        "        raise SystemExit(2)\n"
        "    raise SystemExit(main())\n",
        encoding="utf-8",
    )
    flag = subprocess.run(
        [sys.executable, str(script), "--seed", "7"],
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert flag.returncode == 2, flag.stdout + flag.stderr
    assert _REJECTION_MARKER in flag.stderr
    assert not (tmp_path / "ran.txt").exists()

    help_run = subprocess.run(
        [sys.executable, str(script), "--help"],
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert help_run.returncode == 0
    assert "Doc." in help_run.stdout
    assert not (tmp_path / "ran.txt").exists()


def test_the_rejection_covers_the_drivers_that_read_no_arguments() -> None:
    """The rejection is present where the guard is, and it is not vacuous."""
    guarded: list[str] = []
    rejecting: list[str] = []
    for root in (TOOLS, SCRIPTS):
        for path in sorted(root.glob("*.py")):
            src = path.read_text(encoding="utf-8")
            if '"--help"} & set(sys.argv[1:])' not in src:
                continue
            guarded.append(path.name)
            if _REJECTION_MARKER in src:
                rejecting.append(path.name)
    assert len(rejecting) >= 40
    # Every rejecting driver also honours --help; a rejection without the
    # guard would make `--help` exit 2.
    assert set(rejecting) <= set(guarded)
