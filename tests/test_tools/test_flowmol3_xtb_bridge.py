"""Unit tests for ``tools.flowmol3_xtb_bridge``.

The bridge exposes three public functions — :func:`xtb_optimize_sdf`,
:func:`compute_med_rmsd`, :func:`xtb_energy_ratio` — that wrap the
upstream FlowMol3 geometry / chemistry helpers as subprocess calls.
This test file covers the five surface contracts enumerated in
Wave 88 Agent A / Wave 89 follow-up:

  (a) :func:`xtb_optimize_sdf` invokes ``subprocess.run`` with the
      correct argv (matches the upstream
      ``fm3_evals/geometry/xtb_optimization.py`` CLI verbatim), passes
      a populated env dict, and returns the ``_opt`` SDF path on
      success.
  (b) :func:`compute_med_rmsd` reads the dumped ``.pkl`` sidecar and
      surfaces its ``med_rmsd`` float verbatim (handles missing keys
      and malformed payloads gracefully).
  (c) :func:`xtb_energy_ratio` returns a non-negative ``float`` and
      parses the GFN2-xTB ``TOTAL ENERGY ... Eh`` line out of the
      captured subprocess output.
  (d) Missing xtb → ``XtbBridgeError`` carrying the install hint
      verbatim (no silent stub fallback).
  (e) Timeout → ``XtbBridgeError`` chained from
      :class:`subprocess.TimeoutExpired`.

All subprocess + filesystem + env resolution is mocked so the suite
runs in <1s without RDKit or xtb installed. The tests target the
*bridge contract*, not the upstream RDKit/xtb math — that coverage
lives upstream (Wave 82 audit).

Stdlib + ``unittest.mock`` + pytest only. The existing
``tests.conftest`` ``serial_tool`` fixture is NOT needed (no shared
filesystem lock; tmp_path is per-test).
"""
from __future__ import annotations

import os
import pickle  # nosec — only loads dicts we just wrote ourselves
import subprocess
import sys
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

# Make ``tools`` importable. The bridge lives at the repo root under
# ``tools/flowmol3_xtb_bridge.py`` and is import-only (no ``__main__``);
# loading it via importlib keeps the test hermetic and independent of
# any side effects from ``tools/__init__.py``.
REPO_ROOT: Path = Path(__file__).resolve().parent.parent.parent
BRIDGE_PATH: Path = REPO_ROOT / "tools" / "flowmol3_xtb_bridge.py"


def _load_bridge() -> Any:
    """Import the bridge module via spec_from_file_location.

    Mirrors the ``_load_module`` pattern in
    ``tests/test_tools/test_run_mol_eval.py`` so the test does NOT
    depend on a top-level ``tools`` package layout.
    """
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "flowmol3_xtb_bridge", str(BRIDGE_PATH)
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)  # type: ignore[union-attr]
    return module


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def bridge() -> Any:
    """Lazily import the bridge module once per test file."""
    return _load_bridge()


@pytest.fixture()
def fake_xtb(tmp_path: Path) -> Path:
    """Create a fake ``xtb`` binary on disk and return its path.

    The fake is an empty file marked executable; it never actually
    executes — the tests patch :func:`subprocess.run` to short-circuit
    it. The fixture exists only so the bridge's binary-resolution
    logic (``_resolve_xtb_binary``) accepts the path.
    """
    bin_path = tmp_path / "xtb"
    bin_path.write_text("#!/bin/sh\necho stub\n", encoding="utf-8")
    bin_path.chmod(0o755)
    return bin_path


@pytest.fixture()
def fake_xtb_optimization_script(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Create a stub ``xtb_optimization.py`` so the upstream-script
    existence check passes.

    The bridge only checks ``is_file()``; the body never executes
    because ``subprocess.run`` is patched.
    """
    script = tmp_path / "xtb_optimization.py"
    script.write_text("# stub\n", encoding="utf-8")
    monkeypatch.setattr(
        "tools.flowmol3_xtb_bridge.XTB_OPTIMIZATION_SCRIPT", script
    )
    return script


@pytest.fixture()
def fake_rmsd_energy_script(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Create a stub ``rmsd_energy.py`` for the same reason."""
    script = tmp_path / "rmsd_energy.py"
    script.write_text("# stub\n", encoding="utf-8")
    monkeypatch.setattr(
        "tools.flowmol3_xtb_bridge.RDKIT_RMSD_ENERGY_SCRIPT", script
    )
    return script


def _completed_proc(
    *,
    returncode: int = 0,
    stdout: str = "",
    stderr: str = "",
) -> MagicMock:
    """Build a fake :class:`subprocess.CompletedProcess` with the
    fields the bridge inspects."""
    proc = MagicMock(spec=subprocess.CompletedProcess)
    proc.returncode = returncode
    proc.stdout = stdout
    proc.stderr = stderr
    proc.args = []
    return proc


# ---------------------------------------------------------------------------
# (a) xtb_optimize_sdf calls subprocess correctly
# ---------------------------------------------------------------------------


def test_xtb_optimize_sdf_invokes_subprocess_with_correct_argv(
    bridge: Any,
    tmp_path: Path,
    fake_xtb: Path,
    fake_xtb_optimization_script: Path,
) -> None:
    """``xtb_optimize_sdf`` MUST shell out to the upstream script with
    the exact ``--input_sdf`` / ``--output_sdf`` / ``--init_sdf`` triple
    that ``data/FlowMol3/repo/fm3_evals/geometry/xtb_optimization.py``
    expects (lines 171-176). The opt-SDF output path follows the
    upstream convention ``<init_stem>_opt<init_suffix>``.
    """
    # Arrange: stub the upstream pipeline so the "opt" SDF exists.
    sdf_in = tmp_path / "in.sdf"
    sdf_in.write_text("in\n", encoding="utf-8")
    init_sdf = tmp_path / "init.sdf"
    init_sdf.write_text("init\n", encoding="utf-8")
    opt_sdf_expected = tmp_path / "init_opt.sdf"  # matches upstream convention

    def fake_run(cmd: list[str], **kwargs: Any) -> MagicMock:
        # Side effect: the upstream script would write the opt SDF here.
        opt_sdf_expected.write_text("opt\n", encoding="utf-8")
        return _completed_proc(returncode=0, stdout="", stderr="")

    with patch.object(bridge.subprocess, "run", side_effect=fake_run) as mock_run:
        # Act
        result = bridge.xtb_optimize_sdf(
            sdf_in,
            init_sdf,
            xtb_binary=str(fake_xtb),
        )

    # Assert: subprocess.run was called exactly once, with the expected argv.
    assert mock_run.call_count == 1
    call = mock_run.call_args
    cmd = call.args[0]
    assert cmd[0] == sys.executable, f"argv[0] must be sys.executable; got {cmd[0]!r}"
    assert cmd[1].endswith("xtb_optimization.py"), f"argv[1] must point at the upstream script; got {cmd[1]!r}"
    # The CLI triple is the upstream contract — see xtb_optimization.py:171-176.
    assert "--input_sdf" in cmd
    assert "--output_sdf" in cmd
    assert "--init_sdf" in cmd
    input_idx = cmd.index("--input_sdf")
    output_idx = cmd.index("--output_sdf")
    init_idx = cmd.index("--init_sdf")
    assert cmd[input_idx + 1] == str(sdf_in.resolve())
    assert cmd[output_idx + 1] == str(opt_sdf_expected.resolve())
    assert cmd[init_idx + 1] == str(init_sdf.resolve())
    # capture_output=True and text=True are the bridge's subprocess hygiene.
    assert call.kwargs.get("capture_output") is True
    assert call.kwargs.get("text") is True
    # Env must be passed and MUST carry PATH (xtb puts its prefix on PATH).
    env_passed = call.kwargs.get("env")
    assert isinstance(env_passed, dict)
    assert "PATH" in env_passed
    # Return value is the opt-SDF path (upstream convention).
    assert result == opt_sdf_expected
    assert result.is_file()


# ---------------------------------------------------------------------------
# (b) compute_med_rmsd parses output
# ---------------------------------------------------------------------------


def test_compute_med_rmsd_parses_dumped_pkl(
    bridge: Any,
    tmp_path: Path,
    fake_rmsd_energy_script: Path,
) -> None:
    """``compute_med_rmsd`` MUST read the ``rmsd_energy_results.pkl``
    sidecar written by the upstream script and return its ``med_rmsd``
    key as a ``float``."""
    init_sdf = tmp_path / "init.sdf"
    init_sdf.write_text("init\n", encoding="utf-8")
    opt_sdf = tmp_path / "opt.sdf"
    opt_sdf.write_text("opt\n", encoding="utf-8")

    # Match the upstream contract — rmsd_energy.py:62 writes med_rmsd
    # via np.median over per-pair RMSDs. We fabricate a plausible
    # payload so the bridge's parsing path is exercised.
    fake_payload = {
        "avg_rmsd": 0.42,
        "med_rmsd": 0.31,
        "avg_energy_gain": -0.05,
        "med_energy_gain": -0.04,
        "avg_mmff_drop": 1.2,
        "med_mmff_drop": 1.1,
    }

    def fake_run(cmd: list[str], **kwargs: Any) -> MagicMock:
        # The bridge derives the pkl path from --output_file stem.
        # The upstream rmsd_energy.py:126-134 writes to
        # ``Path(args.output_file).with_suffix('.pkl')`` OR
        # ``Path(args.init_sdf).parent / 'rmsd_energy_results.pkl'``
        # — the bridge checks BOTH candidates (see lines 477-485),
        # so writing to the init_sdf.parent location is enough.
        pkl_path = init_sdf.parent / "rmsd_energy_results.pkl"
        with pkl_path.open("wb") as fh:
            pickle.dump(fake_payload, fh)
        return _completed_proc(returncode=0, stdout="", stderr="")

    with patch.object(bridge.subprocess, "run", side_effect=fake_run):
        med = bridge.compute_med_rmsd(init_sdf, opt_sdf)

    # Assert: the float surfaces verbatim; nothing else leaks.
    assert isinstance(med, float)
    assert med == pytest.approx(0.31, rel=1e-9)


def test_compute_med_rmsd_rejects_non_dict_payload(
    bridge: Any,
    tmp_path: Path,
    fake_rmsd_energy_script: Path,
) -> None:
    """A malformed sidecar (e.g. ``list`` instead of ``dict``) MUST
    raise ``XtbBridgeError`` rather than crashing with ``TypeError``
    on ``results['med_rmsd']``. This guards downstream callers from
    silent partial failures if the upstream script changes shape."""
    init_sdf = tmp_path / "init.sdf"
    init_sdf.write_text("init\n", encoding="utf-8")
    opt_sdf = tmp_path / "opt.sdf"
    opt_sdf.write_text("opt\n", encoding="utf-8")

    def fake_run(cmd: list[str], **kwargs: Any) -> MagicMock:
        pkl_path = init_sdf.parent / "rmsd_energy_results.pkl"
        with pkl_path.open("wb") as fh:
            pickle.dump([1, 2, 3], fh)  # NOT a dict — must surface as XtbBridgeError
        return _completed_proc(returncode=0, stdout="", stderr="")

    with patch.object(bridge.subprocess, "run", side_effect=fake_run):
        with pytest.raises(bridge.XtbBridgeError) as excinfo:
            bridge.compute_med_rmsd(init_sdf, opt_sdf)
    # Error message must mention the malformed payload type.
    assert "non-dict" in str(excinfo.value).lower()


# ---------------------------------------------------------------------------
# (c) xtb_energy_ratio returns float
# ---------------------------------------------------------------------------


def test_xtb_energy_ratio_returns_finite_float(
    bridge: Any,
    tmp_path: Path,
    fake_xtb: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """``xtb_energy_ratio`` MUST return a finite non-negative ``float``
    parsed from the GFN2-xTB ``TOTAL ENERGY ... Eh`` stdout line.

    The test fakes the two single-point subprocess calls (init, opt)
    and verifies the ratio math: ``|E_init - E_opt| / min(|E_init|, |E_opt|)``.
    For ``E_init = -5.0`` and ``E_opt = -5.25``, the expected ratio is
    ``|0.25| / |-5.25| ≈ 0.04762``.

    Note: the bridge does ``from rdkit import Chem`` inline
    (``tools/flowmol3_xtb_bridge.py:610``) so the in-process ``Mol``
    copy + ``SDMolSupplier`` paths require rdkit. We inject a stub
    ``rdkit.Chem`` module into ``sys.modules`` so the test stays
    hermetic on hosts without rdkit installed (e.g. the framework's
    CPU-only CI rig).
    """
    # Stub rdkit.Chem — Mol(mol) returns a MagicMock and SDMolSupplier
    # yields an iterator that hands back our mocked mol.
    fake_chem = MagicMock()
    fake_chem.Mol.side_effect = lambda src: src  # Mol(mol) → identity
    fake_chem.SDMolSupplier.return_value = iter([MagicMock(name="opt_record")])
    fake_rdkit = MagicMock()
    fake_rdkit.Chem = fake_chem
    monkeypatch.setitem(sys.modules, "rdkit", fake_rdkit)
    monkeypatch.setitem(sys.modules, "rdkit.Chem", fake_chem)

    # Construct a minimal Mol-like object — the bridge only calls
    # ``mol.GetConformer`` / ``mol.GetNumAtoms`` / ``mol.GetAtoms`` /
    # ``mol.GetSymbol`` for XYZ writing. We mock those.
    mol = MagicMock()
    conf = MagicMock()
    # 2 atoms (e.g. H2) at synthetic positions; XYZ writer iterates
    # ``mol.GetAtoms()`` and looks up positions by index.
    atom_a = MagicMock()
    atom_a.GetIdx.return_value = 0
    atom_a.GetSymbol.return_value = "H"
    atom_b = MagicMock()
    atom_b.GetIdx.return_value = 1
    atom_b.GetSymbol.return_value = "H"
    mol.GetAtoms.return_value = [atom_a, atom_b]
    mol.GetNumAtoms.return_value = 2
    mol.GetConformer.return_value = conf
    pos_a = MagicMock()
    pos_a.x, pos_a.y, pos_a.z = 0.0, 0.0, 0.0
    pos_b = MagicMock()
    pos_b.x, pos_b.y, pos_b.z = 0.0, 0.0, 0.74
    conf.GetAtomPosition.side_effect = lambda i: pos_a if i == 0 else pos_b
    mol.HasProp.return_value = False  # no _Name → bridge picks first opt record
    # The init and opt SDFs must exist (the bridge validates both).
    init_sdf = tmp_path / "init.sdf"
    init_sdf.write_text("init\n", encoding="utf-8")
    opt_sdf = tmp_path / "opt.sdf"
    opt_sdf.write_text("opt\n", encoding="utf-8")

    # Two xtb calls: init -> -5.0 Eh, opt -> -5.25 Eh.
    # The bridge calls _single_point_energy twice (init_xyz, opt_xyz).
    call_count = {"n": 0}

    def fake_run(cmd: list[str], **kwargs: Any) -> MagicMock:
        call_count["n"] += 1
        if call_count["n"] == 1:
            return _completed_proc(
                returncode=0,
                stdout=":: total free energy    -5.00000 Eh   ::\n",
                stderr="",
            )
        return _completed_proc(
            returncode=0,
            stdout="TOTAL ENERGY              -5.25000 Eh\n",
            stderr="",
        )

    with patch.object(bridge.subprocess, "run", side_effect=fake_run):
        ratio = bridge.xtb_energy_ratio(
            mol,
            init_sdf,
            opt_sdf,
            xtb_binary=str(fake_xtb),
        )

    # Assert: float, non-negative, matches the closed-form ratio.
    assert isinstance(ratio, float)
    assert ratio >= 0.0
    expected = abs(-5.0 - (-5.25)) / min(abs(-5.0), abs(-5.25))
    assert ratio == pytest.approx(expected, rel=1e-6)
    # Both single-point calls must have happened.
    assert call_count["n"] == 2


# ---------------------------------------------------------------------------
# (d) Missing xtb → graceful error
# ---------------------------------------------------------------------------


def test_missing_xtb_returns_graceful_error(
    bridge: Any,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    fake_xtb_optimization_script: Path,
) -> None:
    """When NO xtb binary resolves (env var unset, default prefix
    missing, and ``$PATH`` empty), ``xtb_optimize_sdf`` MUST raise
    :class:`XtbBridgeError` carrying the install hint verbatim — no
    silent stub fallback.

    The bridge also MUST NOT call ``subprocess.run`` (a graceful
    failure must short-circuit before the subprocess).
    """
    # Force every resolution candidate to fail.
    monkeypatch.delenv("FLOWMOL3_XTB_BINARY", raising=False)
    monkeypatch.setattr(bridge, "DEFAULT_XTB_BINARY", "/nonexistent/xtb")
    monkeypatch.setattr(bridge.shutil, "which", lambda _: None)

    sdf_in = tmp_path / "in.sdf"
    sdf_in.write_text("in\n", encoding="utf-8")
    init_sdf = tmp_path / "init.sdf"
    init_sdf.write_text("init\n", encoding="utf-8")

    with patch.object(bridge.subprocess, "run") as mock_run:
        with pytest.raises(bridge.XtbBridgeError) as excinfo:
            bridge.xtb_optimize_sdf(
                sdf_in,
                init_sdf,
                # xtb_binary=None → defer to env/default/PATH resolution
            )

    # No subprocess attempted.
    mock_run.assert_not_called()
    # Error message carries the install hint verbatim (so callers can
    # surface it to operators without a string lookup).
    assert "install xtb" in str(excinfo.value).lower()
    assert bridge.XTB_INSTALL_HINT.split(" ")[0] in str(excinfo.value)


def test_missing_xtb_for_energy_ratio_raises(
    bridge: Any,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Same contract for ``xtb_energy_ratio``: missing xtb → loud
    ``XtbBridgeError``. Critical for the energy-axis fallback path
    used by ``tools/paper_metrics.py:_compute_pb_validity_pct``."""
    monkeypatch.delenv("FLOWMOL3_XTB_BINARY", raising=False)
    monkeypatch.setattr(bridge, "DEFAULT_XTB_BINARY", "/nonexistent/xtb")
    monkeypatch.setattr(bridge.shutil, "which", lambda _: None)

    mol = MagicMock()
    init_sdf = tmp_path / "init.sdf"
    init_sdf.write_text("init\n", encoding="utf-8")
    opt_sdf = tmp_path / "opt.sdf"
    opt_sdf.write_text("opt\n", encoding="utf-8")

    with pytest.raises(bridge.XtbBridgeError) as excinfo:
        bridge.xtb_energy_ratio(mol, init_sdf, opt_sdf)
    assert "install xtb" in str(excinfo.value).lower()


# ---------------------------------------------------------------------------
# (e) Timeout handling
# ---------------------------------------------------------------------------


def test_xtb_optimize_sdf_timeout_raises_xtb_bridge_error(
    bridge: Any,
    tmp_path: Path,
    fake_xtb: Path,
    fake_xtb_optimization_script: Path,
) -> None:
    """``subprocess.TimeoutExpired`` MUST be converted to
    :class:`XtbBridgeError` with a chained cause. The bridge MUST NOT
    propagate the raw ``TimeoutExpired`` (callers expect a uniform
    exception type and would otherwise need a second ``except``)."""
    sdf_in = tmp_path / "in.sdf"
    sdf_in.write_text("in\n", encoding="utf-8")
    init_sdf = tmp_path / "init.sdf"
    init_sdf.write_text("init\n", encoding="utf-8")

    def fake_run(cmd: list[str], **kwargs: Any) -> None:
        # Mirror the real subprocess.TimeoutExpired signature.
        raise subprocess.TimeoutExpired(cmd=cmd, timeout=kwargs.get("timeout"))

    with patch.object(bridge.subprocess, "run", side_effect=fake_run):
        with pytest.raises(bridge.XtbBridgeError) as excinfo:
            bridge.xtb_optimize_sdf(
                sdf_in,
                init_sdf,
                xtb_binary=str(fake_xtb),
                timeout_s=5,
            )

    # Chained cause preserved (callers can introspect if needed).
    assert isinstance(excinfo.value.__cause__, subprocess.TimeoutExpired)
    # Error message mentions the timeout.
    msg = str(excinfo.value).lower()
    assert "timed out" in msg or "timeout" in msg


def test_compute_med_rmsd_timeout_raises_xtb_bridge_error(
    bridge: Any,
    tmp_path: Path,
    fake_rmsd_energy_script: Path,
) -> None:
    """Same contract for ``compute_med_rmsd``."""
    init_sdf = tmp_path / "init.sdf"
    init_sdf.write_text("init\n", encoding="utf-8")
    opt_sdf = tmp_path / "opt.sdf"
    opt_sdf.write_text("opt\n", encoding="utf-8")

    def fake_run(cmd: list[str], **kwargs: Any) -> None:
        raise subprocess.TimeoutExpired(cmd=cmd, timeout=kwargs.get("timeout"))

    with patch.object(bridge.subprocess, "run", side_effect=fake_run):
        with pytest.raises(bridge.XtbBridgeError) as excinfo:
            bridge.compute_med_rmsd(init_sdf, opt_sdf, timeout_s=2)

    assert isinstance(excinfo.value.__cause__, subprocess.TimeoutExpired)


# ---------------------------------------------------------------------------
# Bonus: smoke test for the parser (verifies the regex matches real
# xtb output formats we have observed in Wave 82 / Wave 87 audits).
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("stdout_blob", "expected"),
    [
        ("TOTAL ENERGY              -5.234567 Eh\n", -5.234567),
        (":: total free energy    -5.25000 Eh   ::\n", -5.25),
        ("TOTAL SCF ENERGY            -1.5e+1 Eh\n", -15.0),
    ],
)
def test_parse_xtb_energy_handles_known_flavours(
    bridge: Any,
    stdout_blob: str,
    expected: float,
) -> None:
    """The private ``_parse_xtb_energy`` regex MUST match all three
    xtb total-energy flavours documented in the bridge module
    (GFN2-xTB / GFN1-xTB / GFN0-xtb)."""
    assert bridge._parse_xtb_energy(stdout_blob) == pytest.approx(expected, rel=1e-9)


def test_parse_xtb_energy_returns_none_on_garbage(bridge: Any) -> None:
    """A blob with no parseable energy line returns ``None`` — the
    caller (single-point energy helper) raises ``XtbBridgeError`` on
    a ``None`` return."""
    assert bridge._parse_xtb_energy("") is None
    assert bridge._parse_xtb_energy("no energy here\n") is None
    assert bridge._parse_xtb_energy("TOTAL ENERGY\n") is None  # no Eh suffix


__all__ = (
    "test_xtb_optimize_sdf_invokes_subprocess_with_correct_argv",
    "test_compute_med_rmsd_parses_dumped_pkl",
    "test_compute_med_rmsd_rejects_non_dict_payload",
    "test_xtb_energy_ratio_returns_finite_float",
    "test_missing_xtb_returns_graceful_error",
    "test_missing_xtb_for_energy_ratio_raises",
    "test_xtb_optimize_sdf_timeout_raises_xtb_bridge_error",
    "test_compute_med_rmsd_timeout_raises_xtb_bridge_error",
    "test_parse_xtb_energy_handles_known_flavours",
    "test_parse_xtb_energy_returns_none_on_garbage",
)
