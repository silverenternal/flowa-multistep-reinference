"""The recipe-flag checker must catch a renamed flag and stay quiet otherwise.

Seven commands across ``reproduce/`` and ``scripts/`` named flags their driver
did not accept (``--n-seeds`` on the CIFAR driver, ``--output-dir`` on a
driver that spells it ``--outdir``, a nine-flag ``tools/run_real_ckpt_eval.py``
call against a six-flag CLI).  None of them ran, because the command blocks are
commented out until a reader uncomments them, so the drift was invisible.

These tests pin the checker's two failure modes and the two things it must not
confuse: a flag registered through ``tools._sota_common.add_sota_common_args``
is real even though the driver never calls ``add_argument("--output-dir")``,
and a commented-out recipe line is exactly the text that has to be checked.

The same defect recurred in prose on 2026-10-30, in the two experiment-setup
records that tell a reviewer which command re-runs which cell: five of their
six commands named a driver that has never existed or flags no driver accepts.
The checker reads those records too, and checks that a cited
``bash reproduce/x.sh`` is a real file.
"""

from __future__ import annotations

import pathlib
import subprocess
import sys

import pytest

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "tools"))

import check_recipe_flags  # noqa: E402

DRIVER = '''"""Doc."""
import argparse


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--outdir", required=True)
    parser.add_argument("--n", type=int, default=10)
    parser.parse_args()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
'''

SOTA_DRIVER = '''"""Doc."""
from tools._sota_common import add_sota_common_args
import argparse


def main() -> int:
    parser = argparse.ArgumentParser()
    add_sota_common_args(parser, include_seed=False)
    parser.parse_args()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
'''


def _tree(tmp_path: pathlib.Path, driver_body: str, recipe_body: str) -> pathlib.Path:
    (tmp_path / "reproduce").mkdir()
    (tmp_path / "scripts").mkdir()
    (tmp_path / "tools").mkdir()
    (tmp_path / "tools" / "drv.py").write_text(driver_body, encoding="utf-8")
    (tmp_path / "reproduce" / "cell.sh").write_text(recipe_body, encoding="utf-8")
    return tmp_path


def test_the_repository_is_clean() -> None:
    assert check_recipe_flags.check(REPO_ROOT) == []


def test_an_unknown_flag_is_reported(tmp_path) -> None:
    root = _tree(
        tmp_path,
        DRIVER,
        "#   python tools/drv.py \\\n#     --n 100 \\\n#     --output-dir /tmp/x\n",
    )
    problems = check_recipe_flags.check(root)
    assert len(problems) == 1
    assert "--output-dir" in problems[0]


def test_a_known_flag_in_a_commented_recipe_is_accepted(tmp_path) -> None:
    root = _tree(
        tmp_path,
        DRIVER,
        "#   python tools/drv.py \\\n#     --n 100 \\\n#     --outdir /tmp/x\n",
    )
    assert check_recipe_flags.check(root) == []


def test_a_missing_driver_is_reported(tmp_path) -> None:
    root = _tree(tmp_path, DRIVER, "python tools/absent.py --n 1\n")
    problems = check_recipe_flags.check(root)
    assert len(problems) == 1
    assert "no such driver" in problems[0]


def test_sota_common_flags_are_recognised(tmp_path) -> None:
    root = _tree(tmp_path, SOTA_DRIVER, "python tools/drv.py --output-dir /tmp/x\n")
    assert check_recipe_flags.check(root) == []


def test_the_continuation_line_is_part_of_the_same_command(tmp_path) -> None:
    root = _tree(
        tmp_path,
        DRIVER,
        "python tools/drv.py \\\n    --bogus 1\n",
    )
    problems = check_recipe_flags.check(root)
    assert len(problems) == 1
    assert "--bogus" in problems[0]


@pytest.mark.parametrize("flag", ["-h", "--help"])
def test_help_is_a_dry_run(flag) -> None:
    proc = subprocess.run(
        [sys.executable, str(REPO_ROOT / "tools" / "check_recipe_flags.py"), flag],
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert proc.returncode == 0, proc.stderr
    assert "shell recipe" in proc.stdout


# ---------------------------------------------------------------------------
# The reviewer-facing records under docs/audit/reproducibility/
# ---------------------------------------------------------------------------

RECORD = "docs/audit/reproducibility/p5-experiment-setup.md"


def _doc_tree(tmp_path: pathlib.Path, record_body: str) -> pathlib.Path:
    (tmp_path / "reproduce").mkdir()
    (tmp_path / "scripts").mkdir()
    (tmp_path / "tools").mkdir()
    (tmp_path / "tools" / "drv.py").write_text(DRIVER, encoding="utf-8")
    (tmp_path / "reproduce" / "01_cell.sh").write_text("#!/bin/bash\n", encoding="utf-8")
    record = tmp_path / RECORD
    record.parent.mkdir(parents=True)
    record.write_text(record_body, encoding="utf-8")
    return tmp_path


def test_a_record_naming_a_missing_driver_is_reported(tmp_path) -> None:
    root = _doc_tree(tmp_path, "```bash\npython tools/absent.py --n 1\n```\n")
    problems = check_recipe_flags.check(root)
    assert len(problems) == 1
    assert "no such driver" in problems[0]


def test_a_record_naming_a_flag_the_driver_lacks_is_reported(tmp_path) -> None:
    root = _doc_tree(tmp_path, "```bash\npython tools/drv.py --nfe 50\n```\n")
    problems = check_recipe_flags.check(root)
    assert len(problems) == 1
    assert "--nfe" in problems[0]


def test_a_record_naming_a_real_command_is_clean(tmp_path) -> None:
    root = _doc_tree(
        tmp_path,
        "```bash\nbash reproduce/01_cell.sh\npython tools/drv.py --n 1 --outdir /tmp/x\n```\n",
    )
    assert check_recipe_flags.check(root) == []


def test_a_record_naming_a_missing_recipe_is_reported(tmp_path) -> None:
    root = _doc_tree(tmp_path, "```bash\nbash reproduce/99_absent.sh\n```\n")
    problems = check_recipe_flags.check(root)
    assert len(problems) == 1
    assert "no such script" in problems[0]
