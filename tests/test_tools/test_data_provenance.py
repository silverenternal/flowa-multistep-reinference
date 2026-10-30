"""The provenance checker must fail an unexplained stale hash and only that.

``tools/check_data_provenance.py`` walks ``docs/audit/wave*.md``, pairs each
cited sha256 with the ``verification_outputs/`` path beside it, and compares
the pair against the file on disk.  It was written in Wave 342 and never wired
into the gate chain, because three citations are stale *and* reconciled: the
document records the run-time hash, then the current one, then explains why the
bytes moved (``verification_outputs/`` is gitignored, so the original bytes
cannot be restored).  Failing on those three would mean a gate that can never
go green; passing them silently would mean a gate that cannot see a real stale
hash.  ``_reconciled_near`` is the line between the two, and these tests pin
both sides of it.
"""

from __future__ import annotations

import hashlib
import pathlib
import subprocess
import sys

import pytest

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "tools"))

import check_data_provenance as prov  # noqa: E402

ARTIFACT = "verification_outputs/demo/result.json"
CONTENT = b'{"value": 1}\n'
CURRENT = hashlib.sha256(CONTENT).hexdigest()
STALE = "0" * 64


@pytest.fixture()
def tree(tmp_path: pathlib.Path) -> pathlib.Path:
    audit = tmp_path / "docs" / "audit"
    audit.mkdir(parents=True)
    artifact = tmp_path / ARTIFACT
    artifact.parent.mkdir(parents=True)
    artifact.write_bytes(CONTENT)
    return tmp_path


def _write(tree: pathlib.Path, body: str) -> pathlib.Path:
    doc = tree / "docs" / "audit" / "wave999-demo.md"
    doc.write_text(body, encoding="utf-8")
    return doc


def _verify(tree: pathlib.Path) -> prov.ProvenanceResult:
    return prov.verify(audit_dir=tree / "docs" / "audit", repo_root=tree)


def test_the_repository_is_clean() -> None:
    assert prov.verify().drifts == ()


def test_a_matching_citation_is_accepted(tree) -> None:
    _write(tree, f"Cites `{ARTIFACT}` sha256 `{CURRENT}`.\n")
    result = _verify(tree)
    assert result.drifts == ()
    assert result.disclosed == ()
    assert len(result.citations) == 1


def test_a_stale_citation_without_a_note_is_a_drift(tree) -> None:
    _write(tree, f"Cites `{ARTIFACT}` sha256 `{STALE}`.\n")
    result = _verify(tree)
    assert len(result.drifts) == 1
    assert result.drifts[0].kind == "orphan_sha"
    assert result.disclosed == ()


def test_a_stale_citation_with_the_current_hash_beside_it_is_disclosed(tree) -> None:
    _write(
        tree,
        f"| `{ARTIFACT}` | sha256 `{STALE}` at run time |\n"
        "\n"
        f"**Hash note.** The file now hashes to `{CURRENT}`; the JSONL was\n"
        "rewritten during consolidation, which changes bytes without changing\n"
        "values.\n",
    )
    result = _verify(tree)
    assert result.drifts == ()
    assert len(result.disclosed) == 1


def test_the_reconciling_hash_must_be_near_the_citation(tree) -> None:
    filler = "\n" * (prov.RECONCILE_WINDOW + 10)
    _write(
        tree,
        f"Cites `{ARTIFACT}` sha256 `{STALE}`.\n"
        f"{filler}"
        f"Unrelated later note: `{CURRENT}`.\n",
    )
    result = _verify(tree)
    assert len(result.drifts) == 1
    assert result.disclosed == ()


def test_a_missing_file_is_a_drift(tree) -> None:
    _write(tree, "Cites `verification_outputs/demo/absent.json` sha256 `" + CURRENT + "`.\n")
    result = _verify(tree)
    assert len(result.drifts) == 1
    assert result.drifts[0].kind == "missing_file"


@pytest.mark.parametrize("flag", ["-h", "--help"])
def test_help_is_a_dry_run(flag) -> None:
    proc = subprocess.run(
        [sys.executable, str(REPO_ROOT / "tools" / "check_data_provenance.py"), flag],
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert proc.returncode == 0, proc.stderr
    assert "docs/audit/wave*.md" in proc.stdout
