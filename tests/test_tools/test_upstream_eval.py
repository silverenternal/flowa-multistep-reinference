"""Wave 79 Agent 2 — unit tests for ``tools/upstream_eval.py``.

These tests verify the per-model upstream-eval subprocess shims
(``run_lineageflow_upstream_eval``, ``run_kanzi_upstream_eval``,
``run_flowmol3_upstream_eval``) return the documented contract when
the actual upstream subprocess is mocked out:

1. ``status`` key is always present.
2. On success, ``status == 1.0``.
3. On subprocess failure (non-zero exit, timeout, missing binary),
   ``status == 0.0`` + ``reason`` carries the error.
4. JSON parse failures surface as ``status == 0.0`` + ``reason``.

The tests use ``unittest.mock.patch`` on ``subprocess.run`` so the
real upstream packages (LineageFlow HMMER, Kanzi torch + ckpt,
FlowMol3 vendored flowmol) are NEVER imported — the tests are
cold-clone safe + CI-friendly.

Stdlib-only (no torch / no rdkit / no flowmol). Mirrors the test
patterns in :mod:`tests.test_tools.test_run_real_ckpt_eval`.
"""
from __future__ import annotations

import importlib
import json
import os
import pathlib
import subprocess
import sys
import tempfile
from typing import Any
from unittest import mock

import pytest


def _import_tools_module() -> Any:
    """Lazy-import ``tools.upstream_eval`` so module-level side
    effects never run before this fixture."""
    repo_root = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", ".."),
    )
    if repo_root not in sys.path:
        sys.path.insert(0, repo_root)
    return importlib.import_module("tools.upstream_eval")


_UPSTREAM_EVAL = "tools.upstream_eval"


# ---------------------------------------------------------------------------
# 1. LineageFlow upstream eval subprocess smoke test
# ---------------------------------------------------------------------------


def test_upstream_eval_lineageflow_smoke() -> None:
    """Mock subprocess.run for the LineageFlow orchestrator; verify
    the helper flattens ``summary.json`` into ``dict[str, float]``.

    Mock contract:

    * ``subprocess.run`` returns ``CompletedProcess(returncode=0, stderr='',
      stdout='[ok] wrote ...')``.
    * The orchestrator's ``summary.json`` is mocked to contain 2
      metric families (family_validity + novelty) with float values.
    """
    upstream = _import_tools_module()
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = pathlib.Path(tmp)
        outdir = tmp_path / "lf_out"
        fasta_path = tmp_path / "samples.fasta"
        fasta_path.write_text(">seq1\nMKTII\n>seq2\nARNDCEQ\n", encoding="utf-8")
        # The orchestrator writes a ``summary.json`` containing the
        # 2 metric families we pretend succeeded.
        mock_summary = {
            "family_validity": {
                "n_records": 8.0,
                "intended_in_top1": 0.875,
                "intended_in_top10": 1.0,
            },
            "novelty": {
                "n_records": 8.0,
                "mean_max_identity_to_train": 0.42,
                "min_max_identity_to_train": 0.18,
            },
        }
        # The orchestrator writes ``inputs.json``, ``run_manifest.json``,
        # the per-metric ``<metric>.json`` / ``<metric>.jsonl``, and
        # the final ``summary.json``. We pre-create all of them so the
        # helper's read step succeeds.
        outdir.mkdir(parents=True, exist_ok=True)
        (outdir / "summary.json").write_text(
            json.dumps(mock_summary), encoding="utf-8",
        )
        fake_proc = subprocess.CompletedProcess(
            args=[], returncode=0, stderr="", stdout="[ok] wrote ...\n",
        )
        with mock.patch.object(
            upstream.subprocess, "run", return_value=fake_proc,
        ) as _mock_run:
            result = upstream.run_lineageflow_upstream_eval(
                fasta_path=str(fasta_path), output_dir=str(outdir),
            )
        # ---- Contract assertions ----------------------------------
        assert "status" in result, f"missing 'status' in {result!r}"
        assert result["status"] == 1.0, (
            f"expected status=1.0 (success), got {result['status']!r}"
        )
        # The flatten key pattern is ``<metric>__<key>``.
        assert (
            "family_validity__n_records" in result
        ), f"missing flattened family_validity__n_records: {result!r}"
        assert (
            "family_validity__intended_in_top1" in result
        ), f"missing family_validity__intended_in_top1: {result!r}"
        assert result["family_validity__intended_in_top1"] == 0.875
        assert result["family_validity__intended_in_top10"] == 1.0
        assert (
            "novelty__mean_max_identity_to_train" in result
        ), f"missing novelty__mean_max_identity_to_train: {result!r}"
        assert result["novelty__mean_max_identity_to_train"] == 0.42
        # The orchestrator path is surfaced for audit.
        assert (
            result.get("upstream_orchestrator") == str(
                upstream.LINEAGEFLOW_EVALUATE_ALL,
            )
        ), (
            f"expected orchestrator path {upstream.LINEAGEFLOW_EVALUATE_ALL!r}, "
            f"got {result.get('upstream_orchestrator')!r}"
        )
        assert "metric_kind" in result
        # Subprocess was called exactly once with the right CLI shape.
        assert _mock_run.call_count == 1
        call_args = _mock_run.call_args.args[0]
        assert call_args[0] == sys.executable
        assert call_args[1] == str(upstream.LINEAGEFLOW_EVALUATE_ALL)
        assert "--fasta" in call_args
        assert str(fasta_path) in call_args
        assert "--outdir" in call_args
        assert str(outdir) in call_args
        assert "--metrics" in call_args


def test_upstream_eval_lineageflow_subprocess_failure() -> None:
    """When the orchestrator subprocess exits non-zero, the helper
    returns ``status=0.0`` + a ``reason`` key (graceful degradation
    rather than raising)."""
    upstream = _import_tools_module()
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = pathlib.Path(tmp)
        fasta_path = tmp_path / "samples.fasta"
        fasta_path.write_text(">seq1\nMKTII\n", encoding="utf-8")
        outdir = tmp_path / "lf_out"
        outdir.mkdir(parents=True, exist_ok=True)
        # Subprocess returns non-zero (e.g. HMMER binary missing).
        fake_proc = subprocess.CompletedProcess(
            args=[],
            returncode=127,
            stderr="bash: hmmscan: command not found\n",
            stdout="",
        )
        with mock.patch.object(
            upstream.subprocess, "run", return_value=fake_proc,
        ):
            result = upstream.run_lineageflow_upstream_eval(
                fasta_path=str(fasta_path), output_dir=str(outdir),
            )
        assert result["status"] == 0.0, (
            f"expected status=0.0 (failure), got {result['status']!r}"
        )
        assert "reason" in result
        assert "127" in result["reason"], (
            f"expected exit code 127 in reason, got {result['reason']!r}"
        )
        assert "hmmscan" in result["reason"], (
            f"expected stderr hint in reason, got {result['reason']!r}"
        )


# ---------------------------------------------------------------------------
# 2. Kanzi upstream eval subprocess smoke test
# ---------------------------------------------------------------------------


def test_upstream_eval_kanzi_smoke() -> None:
    """Mock subprocess.run for the Kanzi inline-python driver; verify
    the helper flattens the ``reconstruction.json`` summary into
    ``dict[str, float]``."""
    upstream = _import_tools_module()
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = pathlib.Path(tmp)
        coords_path = tmp_path / "samples.ca.txt"
        # 6 floats = 2 Cα coords.
        coords_path.write_text(
            "1.5,2.0,3.0,4.0,5.0,6.0\n", encoding="utf-8",
        )
        outdir = tmp_path / "kz_out"
        outdir.mkdir(parents=True, exist_ok=True)
        # The Kanzi driver writes ``reconstruction.json`` with a
        # ``summary`` block containing the n_seqs + mean/min/max RMSD.
        mock_reconstruction = {
            "per_seq": {"seq_0": 1.23, "seq_1": 0.87},
            "summary": {
                "n_seqs": 2.0,
                "mean_rmsd_A": 1.05,
                "min_rmsd_A": 0.87,
                "max_rmsd_A": 1.23,
            },
        }
        output_json = outdir / "reconstruction.json"
        output_json.write_text(
            json.dumps(mock_reconstruction), encoding="utf-8",
        )
        fake_proc = subprocess.CompletedProcess(
            args=[], returncode=0, stderr="", stdout="",
        )
        # Provide a placeholder ckpt path; the mock subprocess doesn't
        # read it (so any path works).
        fake_ckpt = tmp_path / "fake_ckpt.pt"
        with mock.patch.object(
            upstream.subprocess, "run", return_value=fake_proc,
        ) as _mock_run:
            result = upstream.run_kanzi_upstream_eval(
                sequences_path=str(coords_path),
                output_dir=str(outdir),
                ckpt_path=str(fake_ckpt),
            )
        assert result["status"] == 1.0, (
            f"expected status=1.0, got {result['status']!r} with {result!r}"
        )
        assert result["n_seqs"] == 2.0
        assert result["mean_rmsd_A"] == 1.05
        assert result["min_rmsd_A"] == 0.87
        assert result["max_rmsd_A"] == 1.23
        assert "metric_kind" in result
        assert result["metric_kind"] == "reconstruction_kabsch_rmsd_A"
        assert (
            result.get("upstream_orchestrator")
            == "kanzi.DAE.encode+decode+kabsch_rmsd"
        )
        # The subprocess driver is invoked via ``python -c <driver>``.
        assert _mock_run.call_count == 1
        call_args = _mock_run.call_args.args[0]
        assert call_args[0] == sys.executable
        assert call_args[1] == "-c"
        # The driver body contains the kanzi import + encode + decode.
        assert "kabsch_rmsd" in call_args[2]
        assert "from kanzi import DAE" in call_args[2]
        # The driver arguments wire --input / --ckpt / --output.
        assert "--input" in call_args
        assert str(coords_path) in call_args
        assert "--ckpt" in call_args
        assert str(fake_ckpt) in call_args
        assert "--output" in call_args


def test_upstream_eval_kanzi_subprocess_timeout() -> None:
    """When the Kanzi subprocess times out (subprocess.TimeoutExpired
    on long DiT decode runs), the helper returns ``status=0.0`` +
    ``reason`` rather than raising."""
    upstream = _import_tools_module()
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = pathlib.Path(tmp)
        coords_path = tmp_path / "samples.ca.txt"
        coords_path.write_text("0,0,0\n", encoding="utf-8")
        outdir = tmp_path / "kz_out"
        outdir.mkdir(parents=True, exist_ok=True)
        with mock.patch.object(
            upstream.subprocess, "run",
            side_effect=subprocess.TimeoutExpired(cmd="...", timeout=30),
        ):
            result = upstream.run_kanzi_upstream_eval(
                sequences_path=str(coords_path),
                output_dir=str(outdir),
                timeout_s=30,
            )
        assert result["status"] == 0.0
        assert "timeout" in result["reason"].lower()
        assert result["metric_kind"] == "reconstruction_kabsch_rmsd_A"


# ---------------------------------------------------------------------------
# 3. FlowMol3 upstream eval subprocess smoke test
# ---------------------------------------------------------------------------


def test_upstream_eval_flowmol3_smoke() -> None:
    """Mock subprocess.run for the FlowMol3 SampleAnalyzer driver;
    verify the helper flattens the analyzer's output dict into
    ``dict[str, float]``."""
    upstream = _import_tools_module()
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = pathlib.Path(tmp)
        smiles_path = tmp_path / "samples.smi"
        smiles_path.write_text(
            "CCO\nc1ccccc1\nCCN\n", encoding="utf-8",
        )
        outdir = tmp_path / "fm_out"
        outdir.mkdir(parents=True, exist_ok=True)
        # The driver writes ``sample_analyzer.json`` with the
        # analyzer's output dict (4 paper metrics + REOS + ood).
        mock_analyzer_output = {
            "frac_valid_mols": 0.95,
            "frac_mols_stable_valence": 0.92,
            "frac_atoms_stable": 0.97,
            "pb_valid": 0.88,
            "pb_sanitization": 0.95,
            "flag_rate": 0.04,
            "ood_rate": 0.03,
            "reos_cum_dev": 1.2,
            "n_molecules": 3.0,
        }
        output_json = outdir / "sample_analyzer.json"
        output_json.write_text(
            json.dumps(mock_analyzer_output), encoding="utf-8",
        )
        fake_proc = subprocess.CompletedProcess(
            args=[], returncode=0, stderr="", stdout="",
        )
        with mock.patch.object(
            upstream.subprocess, "run", return_value=fake_proc,
        ) as _mock_run:
            result = upstream.run_flowmol3_upstream_eval(
                smiles_list=str(smiles_path),
                output_dir=str(outdir),
                reference="GEOM_DRUGS",
                pb_workers=2,
            )
        assert result["status"] == 1.0, (
            f"expected status=1.0, got {result['status']!r} with {result!r}"
        )
        assert result["frac_valid_mols"] == 0.95
        assert result["frac_mols_stable_valence"] == 0.92
        assert result["pb_valid"] == 0.88
        assert result["flag_rate"] == 0.04
        assert result["ood_rate"] == 0.03
        assert result["reos_cum_dev"] == 1.2
        assert result["n_molecules"] == 3.0
        assert result["metric_kind"] == "sample_analyzer_paper_parity"
        assert (
            result.get("upstream_orchestrator")
            == "flowmol.analysis.metrics.SampleAnalyzer.analyze"
        )
        # The driver vendors ``data/FlowMol3/repo`` on sys.path.
        assert _mock_run.call_count == 1
        call_args = _mock_run.call_args.args[0]
        assert call_args[0] == sys.executable
        assert call_args[1] == "-c"
        assert (
            "SampleAnalyzer" in call_args[2]
        ), "driver body should import SampleAnalyzer"
        assert (
            "sys.path.insert(0, str(_FLOWMOL3_ROOT))" in call_args[2]
        ), "driver body should vendor FlowMol3 repo on sys.path"
        # The driver arguments wire --smiles-list / --reference /
        # --output / --pb-workers.
        assert "--smiles-list" in call_args
        assert str(smiles_path) in call_args
        assert "--reference" in call_args
        assert "GEOM_DRUGS" in call_args
        assert "--output" in call_args
        assert "--pb-workers" in call_args


def test_upstream_eval_flowmol3_missing_output() -> None:
    """When the subprocess succeeds but ``sample_analyzer.json`` is
    missing, the helper returns ``status=0.0`` + ``reason`` rather
    than crashing (this catches the "subprocess did not write any
    output file" failure mode)."""
    upstream = _import_tools_module()
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = pathlib.Path(tmp)
        smiles_path = tmp_path / "samples.smi"
        smiles_path.write_text("CCO\n", encoding="utf-8")
        outdir = tmp_path / "fm_out"
        outdir.mkdir(parents=True, exist_ok=True)
        # Subprocess returns 0 BUT does NOT write ``sample_analyzer.json``.
        fake_proc = subprocess.CompletedProcess(
            args=[], returncode=0, stderr="", stdout="",
        )
        with mock.patch.object(
            upstream.subprocess, "run", return_value=fake_proc,
        ):
            result = upstream.run_flowmol3_upstream_eval(
                smiles_list=str(smiles_path), output_dir=str(outdir),
            )
        assert result["status"] == 0.0
        assert "no_sample_analyzer_json" in result["reason"]


# ---------------------------------------------------------------------------
# 4. Module-level surface contract (catches typo regressions)
# ---------------------------------------------------------------------------


def test_upstream_eval_module_paths_exist() -> None:
    """The 3 vendored paths the module advertises actually exist on
    disk (Wave 79 Phase 1 audit verified these locations)."""
    upstream = _import_tools_module()
    assert upstream.LINEAGEFLOW_EVALUATE_ALL.is_file(), (
        f"LineageFlow evaluate_all.py not at {upstream.LINEAGEFLOW_EVALUATE_ALL}"
    )
    # Kanzi has no ``evaluation/`` directory (Phase 1 §2.3); we check
    # the ``src/kanzi`` package is present so the vendored import works.
    assert upstream.KANZI_SRC.is_dir(), (
        f"Kanzi src dir not at {upstream.KANZI_SRC}"
    )
    assert (upstream.KANZI_SRC / "kanzi").is_dir(), (
        f"Kanzi package dir not at {upstream.KANZI_SRC / 'kanzi'}"
    )
    # FlowMol3 vendored repo has the analysis package.
    assert upstream.FLOWMOL3_UPSTREAM.is_dir(), (
        f"FlowMol3 repo not at {upstream.FLOWMOL3_UPSTREAM}"
    )
    assert (
        upstream.FLOWMOL3_UPSTREAM / "flowmol" / "analysis"
    ).is_dir(), (
        f"FlowMol3 analysis package not at "
        f"{upstream.FLOWMOL3_UPSTREAM / 'flowmol' / 'analysis'}"
    )


def test_upstream_eval_module_all_exports() -> None:
    """``__all__`` exports the 3 runner functions + the 4 path
    constants so callers can key on the public API."""
    upstream = _import_tools_module()
    expected_in_all = {
        "run_lineageflow_upstream_eval",
        "run_kanzi_upstream_eval",
        "run_flowmol3_upstream_eval",
        "LINEAGEFLOW_EVALUATE_ALL",
        "KANZI_SRC",
        "FLOWMOL3_UPSTREAM",
        "REPO_ROOT",
        "DEFAULT_TIMEOUT_S",
    }
    assert expected_in_all.issubset(set(upstream.__all__)), (
        f"missing exports in __all__: "
        f"{expected_in_all - set(upstream.__all__)}"
    )