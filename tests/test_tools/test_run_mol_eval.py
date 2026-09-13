"""Tests for ``tools.run_mol_eval``.

The runner is the in-process arm of the molecular SOTA-comparison
harness (Phase A). It accepts a ``.npz`` of SMILES, a pickle of
RDKit molecules, or an ``.sdf`` and emits a single JSON with the
canonical five metrics: ``validity``, ``qed``, ``sa``, ``logp``,
``fcd``. Tests cover:

* the happy path (aspirin SMILES round-trips through every metric);
* graceful degradation on invalid SMILES;
* graceful degradation when the optional ``fcd`` library is absent;
* the JSON output schema is stable regardless of which dependencies
  resolved.

Stdlib + pytest + the existing ``[chemistry]`` extra. RDKit is
required for the happy path; ``fcd`` is intentionally probed but
tests skip cleanly when it is absent.

The test suite does NOT depend on the existence of any pre-generated
``.npz`` or ``.pkl`` file in the repo — each test builds its input
fixture from scratch with stdlib (a SMILES ``.npz``, an RDKit ``.pkl``,
or an ``.sdf`` via :class:`Chem.SDWriter`).
"""
from __future__ import annotations

import importlib.util
import json
import math
import pickle
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Any

import numpy as np
import pytest

if TYPE_CHECKING:
    pass

REPO_ROOT: Path = Path(__file__).resolve().parent.parent.parent
SCRIPT_PATH: Path = REPO_ROOT / "tools" / "run_mol_eval.py"


# ---------------------------------------------------------------------------
# Import helpers
# ---------------------------------------------------------------------------


def _load_module() -> Any:
    """Load the runner script as a module via spec_from_file_location.

    The runner is a top-level script under ``tools/`` that uses an
    inline ``sys.path`` injection rather than a package. Loading via
    :mod:`importlib` keeps the test hermetic and avoids the
    PYTHONPATH dance ``tools/run_sota_cifar_experiment`` uses.
    """
    spec = importlib.util.spec_from_file_location("run_mol_eval", str(SCRIPT_PATH))
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)  # type: ignore[union-attr]
    return module


def _rdkit_available() -> bool:
    try:
        import rdkit  # noqa: F401
    except ImportError:
        return False
    return True


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


#: Aspirin canonical SMILES. Used as the canonical "valid" molecule.
ASPIRIN_SMILES: str = "CC(=O)OC1=CC=CC=C1C(=O)O"

#: Canonical invalid SMILES. "C1CC" is a 3-membered ring opened with
#: ring-closure 1 that never closes — RDKit refuses to parse it.
INVALID_SMILES: str = "C1CC"


@pytest.fixture()
def aspirin_npz(tmp_path: Path) -> Path:
    """Write a single-aspirin ``.npz`` and return its path."""
    path = tmp_path / "aspirin.npz"
    np.savez(path, smiles=np.array([ASPIRIN_SMILES], dtype=object))
    return path


@pytest.fixture()
def invalid_npz(tmp_path: Path) -> Path:
    """Write a single-invalid-SMILES ``.npz`` and return its path."""
    path = tmp_path / "invalid.npz"
    np.savez(path, smiles=np.array([INVALID_SMILES], dtype=object))
    return path


@pytest.fixture()
def mixed_npz(tmp_path: Path) -> Path:
    """Write a 3-row ``.npz``: 1 valid SMILES + 2 invalid SMILES.

    Each entry must be a non-empty string; an empty SMILES string
    parses to a valid-but-empty RDKit mol which would skew the
    validity denominator, so we never feed one through.
    """
    path = tmp_path / "mixed.npz"
    np.savez(
        path,
        smiles=np.array(
            [ASPIRIN_SMILES, "not_a_smiles", INVALID_SMILES], dtype=object
        ),
    )
    return path


@pytest.fixture()
def aspirin_pkl(tmp_path: Path) -> Path:
    """Write an RDKit ``.pkl`` carrying one aspirin molecule."""
    if not _rdkit_available():
        pytest.skip("rdkit_unavailable")
    from rdkit import Chem

    path = tmp_path / "aspirin.pkl"
    mol = Chem.MolFromSmiles(ASPIRIN_SMILES)
    assert mol is not None
    with path.open("wb") as fh:
        pickle.dump([mol], fh)
    return path


@pytest.fixture()
def aspirin_sdf(tmp_path: Path) -> Path:
    """Write an RDKit ``.sdf`` carrying one aspirin molecule."""
    if not _rdkit_available():
        pytest.skip("rdkit_unavailable")
    from rdkit import Chem

    path = tmp_path / "aspirin.sdf"
    mol = Chem.MolFromSmiles(ASPIRIN_SMILES)
    assert mol is not None
    writer = Chem.SDWriter(str(path))
    try:
        writer.write(mol)
    finally:
        writer.close()
    return path


# ---------------------------------------------------------------------------
# Import + module-surface tests
# ---------------------------------------------------------------------------
# NOTE (Wave 62): ``test_module_imports`` was deleted. The ``module``
# fixture below (and every test in this file that uses it) already
# imports the script via ``_load_module()`` and exercises
# ``main`` / ``evaluate`` / ``OUTPUT_SCHEMA_VERSION`` directly;
# a separate smoke test asserting only ``hasattr(...)`` is duplicate.
# The schema-version contract is asserted via
# ``test_json_output_schema`` further below.
# ---------------------------------------------------------------------------
# Happy path: aspirin
# ---------------------------------------------------------------------------
# _load_module is module-scoped lazily so the missing-rdkit guard
# below can run BEFORE the rdkit import chain triggers a hard
# ModuleNotFoundError at script import time.


@pytest.fixture(scope="module")
def module() -> Any:
    """Lazily import the runner so the rdkit guard is observed."""
    return _load_module()


@pytest.mark.parametrize(
    ("fixture_name", "dataset", "expected_input_format"),
    [
        ("aspirin_npz", "qm9", "npz"),
        ("aspirin_pkl", "geom_drugs", "pkl"),
        ("aspirin_sdf", "geom_5_kekulized", "sdf"),
    ],
)
def test_metrics_on_input_formats(
    module: Any,
    fixture_name: str,
    dataset: str,
    expected_input_format: str,
    request: pytest.FixtureRequest,
) -> None:
    """A single-molecule input in any of the three supported formats
    (``npz`` / ``pkl`` / ``sdf``) round-trips through the metrics
    pipeline with ``validity=1.0`` and the canonical schema.

    The three formats used to live in three separate tests
    (``test_metrics_on_valid_molecule``, ``test_metrics_on_pickle_input``,
    ``test_metrics_on_sdf_input``); Wave 62 parametrizes on the
    fixture name so each format keeps its dedicated fixture but the
    three happy-path contracts share one body. ``request.getfixturevalue``
    resolves the per-param fixture name to its bound ``Path``.

    Only the ``npz`` form carries the full schema-stability assertions
    (every metric key present, QED in ``[0, 1]``, SA bounded to
    ``[1, 10]``); ``pkl`` / ``sdf`` assert the minimum (validity +
    counts + the right ``input_format``).
    """
    if not _rdkit_available():
        pytest.skip("rdkit_unavailable")
    input_path: Path = request.getfixturevalue(fixture_name)
    report = module.evaluate(
        input_path=input_path, reference_path=None, dataset=dataset
    )
    assert report["input_format"] == expected_input_format
    assert report["validity"] == pytest.approx(1.0, abs=1e-9)
    assert report["n_total"] == 1
    assert report["n_valid"] == 1
    if expected_input_format == "npz":
        # Schema stability: every metric key is present regardless of deps.
        for key in ("validity", "qed", "sa", "logp", "fcd"):
            assert key in report, key
        assert 0.0 <= report["qed"] <= 1.0
        # SA lives in [1, 10] for real molecules; allow the NaN fallback
        # only when the contrib is unimportable.
        if not math.isnan(report["sa"]):
            assert 1.0 <= report["sa"] <= 10.0
        # logP is unbounded; sanity-bound it to a wide drug-like range.
        if not math.isnan(report["logp"]):
            assert -10.0 <= report["logp"] <= 10.0


# NOTE (Wave 62): ``test_metrics_on_sdf_input`` was deleted. It is
# now the third parametrize-id of ``test_metrics_on_input_formats``
# (above), which asserts ``input_format == "sdf"`` + ``validity ==
# 1.0`` for the ``aspirin_sdf`` fixture. The split between the .npz /
# .pkl / .sdf tests had no per-format invariant worth its own function.


# ---------------------------------------------------------------------------
# Invalid molecule
# ---------------------------------------------------------------------------


def test_metrics_on_invalid_molecule(
    module: Any, invalid_npz: Path
) -> None:
    """Invalid SMILES must drop validity to 0; downstream metrics stay NaN."""
    if not _rdkit_available():
        pytest.skip("rdkit_unavailable")
    report = module.evaluate(
        input_path=invalid_npz, reference_path=None, dataset=None
    )
    assert report["n_total"] == 1
    assert report["n_valid"] == 0
    assert report["validity"] == pytest.approx(0.0, abs=1e-9)
    # No valid molecule -> every per-molecule metric is NaN, not 0.
    assert math.isnan(report["qed"])
    assert math.isnan(report["sa"])
    assert math.isnan(report["logp"])


def test_metrics_on_mixed_valid_invalid(
    module: Any, mixed_npz: Path
) -> None:
    """Mixed input: validity == n_valid / n_total; per-molecule metrics are over the valid set."""
    if not _rdkit_available():
        pytest.skip("rdkit_unavailable")
    report = module.evaluate(
        input_path=mixed_npz, reference_path=None, dataset=None
    )
    assert report["n_total"] == 3
    assert report["n_valid"] == 1
    assert report["validity"] == pytest.approx(1.0 / 3.0, abs=1e-9)


# ---------------------------------------------------------------------------
# Graceful fallback when fcd is unavailable
# ---------------------------------------------------------------------------


def test_graceful_fallback_when_fcd_unavailable(
    module: Any, aspirin_npz: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """FCD must be NaN with a stderr note when ``fcd`` is unimportable.

    We don't actually need rdkit for THIS test — the FCD branch
    fires BEFORE the rdkit probe in the evaluate pipeline when the
    reference is provided. But aspirin_npz already needs rdkit
    to materialise; we still skip when rdkit is missing.
    """
    if not _rdkit_available():
        pytest.skip("rdkit_unavailable")

    # Force the fcd probe to fail by hiding the module.
    monkeypatch.setitem(sys.modules, "fcd", None)

    # A real reference file is required by the missing-dep branch;
    # the fcd-not-found note should fire first.
    reference_path = tmp_path / "ref.txt"
    reference_path.write_text(ASPIRIN_SMILES + "\n", encoding="utf-8")
    report = module.evaluate(
        input_path=aspirin_npz,
        reference_path=reference_path,
        dataset="qm9",
    )
    assert any("fcd_unavailable" in n for n in report["stderr_notes"])
    assert "fcd" in report["missing_dependencies"]
    assert math.isnan(report["fcd"])
    # Other metrics still compute.
    assert report["validity"] == pytest.approx(1.0, abs=1e-9)


def test_fcd_na_when_reference_missing(
    module: Any, aspirin_npz: Path, tmp_path: Path
) -> None:
    """FCD must be NaN with a deterministic note when the reference path is missing.

    The exact note depends on whether ``fcd`` is installed: with
    ``fcd`` present, the note is ``fcd_reference_empty_or_missing``;
    without it, the note is ``fcd_unavailable``. Either is a valid
    "FCD was not computed" signal, and the metric must be NaN in
    both cases.
    """
    if not _rdkit_available():
        pytest.skip("rdkit_unavailable")
    reference_path = tmp_path / "missing_ref.txt"
    assert not reference_path.exists()
    report = module.evaluate(
        input_path=aspirin_npz,
        reference_path=reference_path,
        dataset="qm9",
    )
    assert math.isnan(report["fcd"])
    # At least one of the FCD-degradation notes must be present.
    notes_blob = " ".join(report["stderr_notes"])
    assert (
        "fcd_reference_empty_or_missing" in notes_blob
        or "fcd_unavailable" in notes_blob
    ), notes_blob


# ---------------------------------------------------------------------------
# JSON output schema
# ---------------------------------------------------------------------------


def test_json_output_schema(
    module: Any, aspirin_npz: Path, tmp_path: Path
) -> None:
    """The CLI must emit a JSON file containing every documented key."""
    if not _rdkit_available():
        pytest.skip("rdkit_unavailable")
    output_path = tmp_path / "metrics.json"
    rc = module.main(["--input", str(aspirin_npz), "--output", str(output_path)])
    assert rc == 0
    assert output_path.exists()
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    for key in (
        "schema_version",
        "input_path",
        "input_format",
        "dataset",
        "n_total",
        "n_valid",
        "validity",
        "qed",
        "sa",
        "logp",
        "fcd",
        "missing_dependencies",
        "stderr_notes",
    ):
        assert key in payload, key
    assert payload["schema_version"] == module.OUTPUT_SCHEMA_VERSION
    assert payload["input_format"] in {"npz", "pkl", "sdf"}


def test_main_returns_error_on_missing_input(
    module: Any, tmp_path: Path
) -> None:
    """A non-existent ``--input`` must surface exit code 1 (not crash)."""
    output_path = tmp_path / "metrics.json"
    rc = module.main(
        [
            "--input",
            str(tmp_path / "no_such_file.npz"),
            "--output",
            str(output_path),
        ]
    )
    assert rc == 1
    assert not output_path.exists()


# NOTE (Wave 62): ``test_help_flag_exits_cleanly`` was deleted.
# ``test_json_output_schema`` (above) drives ``main()`` with
# ``--input`` / ``--output`` / ``--dataset`` end-to-end, and
# ``test_main_returns_error_on_missing_input`` (above) drives
# ``main()`` with a missing input. Both exercises argparse. The
# standalone ``--help`` smoke that asserted rc==0 + flag-name
# substrings was duplicate coverage; a flag rename surfaces through
# the e2e suite (those tests would fail with a ``SystemExit`` on
# argparse parsing).


# ---------------------------------------------------------------------------
# Probe unit tests
# ---------------------------------------------------------------------------


_PROBE_NAMES: tuple[str, ...] = (
    "_probe_rdkit",
    "_probe_fcd",
    "_probe_posebusters",
)


def test_all_dependency_probes_return_bool(module: Any) -> None:
    """Every dependency probe must always return ``(bool, str | None)``.

    Aggregates the three single-probe contracts (``_probe_rdkit``,
    ``_probe_fcd``, ``_probe_posebusters``) into a single loop-based
    test because each probe has the identical shape contract; a
    regression in any probe surfaces with the offending name in the
    assertion message.
    """
    for name in _PROBE_NAMES:
        ok, err = getattr(module, name)()
        assert isinstance(ok, bool), f"{name}() must return bool"
        assert err is None or isinstance(err, str), (
            f"{name}() second return must be None or str"
        )


def test_compute_pb_validity_json_shape(module: Any) -> None:
    """``compute_pb_validity`` must always return the documented JSON shape.

    Tests the contract independent of whether PoseBusters is
    installed: every documented key is present in every return.
    The ``marker`` value is one of the four documented sentinels
    (``"not_installed"``, ``"stub_unavailable"``, ``"computed"``,
    ``"computed_etkdg_v3_only"``) and ``value`` is a float in
    ``[0, 1]`` or ``None`` or ``NaN``.
    """
    if not _rdkit_available():
        pytest.skip("rdkit_unavailable")
    from rdkit import Chem

    mol = Chem.MolFromSmiles(ASPIRIN_SMILES)
    assert mol is not None
    result = module.compute_pb_validity([mol])
    # Core keys always present.
    for key in (
        "value",
        "marker",
        "install_hint",
        "note",
        "conformer_protocol",
        "n_total",
        "n_pb_valid",
        "n_conformer_failures",
        "pass_per_check",
    ):
        assert key in result, key
    assert result["marker"] in {
        module.PB_VALIDITY_MARKER_NOT_INSTALLED,
        module.PB_VALIDITY_MARKER_STUB_UNAVAILABLE,
        module.PB_VALIDITY_MARKER_COMPUTED,
        module.PB_VALIDITY_MARKER_COMPUTED_ETKDG_V3_ONLY,
    }
    if result["marker"] == module.PB_VALIDITY_MARKER_NOT_INSTALLED:
        # Stable stub: value=None, install_hint non-null.
        assert result["value"] is None
        assert result["install_hint"] is not None
    else:
        # Real call path: value is a finite float in [0, 1].
        assert isinstance(result["value"], float)
        assert 0.0 <= result["value"] <= 1.0
        assert result["install_hint"] is None


def test_unsupported_extension_raises(module: Any, tmp_path: Path) -> None:
    """An unsupported ``--input`` extension must raise ``ValueError``."""
    bad = tmp_path / "foo.txt"
    bad.write_text("hello\n", encoding="utf-8")
    with pytest.raises(ValueError, match="unsupported_input_extension"):
        module.load_inputs(bad)


def test_npz_missing_smiles_key_raises(module: Any, tmp_path: Path) -> None:
    """An ``.npz`` without the ``smiles`` key must raise ``ValueError``."""
    path = tmp_path / "no_smiles.npz"
    np.savez(path, foo=np.array([1, 2, 3], dtype=np.int64))
    with pytest.raises(ValueError, match="npz_missing_key:smiles"):
        module.load_inputs(path)
