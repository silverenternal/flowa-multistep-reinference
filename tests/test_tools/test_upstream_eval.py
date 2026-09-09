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


def test_upstream_eval_lineageflow_passes_hmmdb_target_db_pfam_fastas_dir_and_bins() -> None:
    """Wave 81 — wrapper must pass --hmmdb + --target-db + --pfam-fastas-dir
    + --hmmscan + --mmseqs to the orchestrator so the ``family_validity``
    + ``novelty`` paths pass their ``_require_path`` checks. Pre-Wave-81
    the wrapper omitted these args and the orchestrator exited with
    ``error: --hmmdb is required`` the moment ``family_validity`` was
    in the metrics list."""
    upstream = _import_tools_module()
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = pathlib.Path(tmp)
        fasta_path = tmp_path / "samples.fasta"
        fasta_path.write_text(">seq1\nMKTII\n", encoding="utf-8")
        outdir = tmp_path / "lf_out"
        outdir.mkdir(parents=True, exist_ok=True)
        (outdir / "summary.json").write_text(
            json.dumps({
                "family_validity": {"n_records": 1.0},
                "novelty": {"mean_max_identity_to_train": 0.0},
            }),
            encoding="utf-8",
        )
        fake_proc = subprocess.CompletedProcess(
            args=[], returncode=0, stderr="", stdout="",
        )
        with mock.patch.object(
            upstream.subprocess, "run", return_value=fake_proc,
        ) as _mock_run:
            upstream.run_lineageflow_upstream_eval(
                fasta_path=str(fasta_path),
                output_dir=str(outdir),
            )
        call_args = _mock_run.call_args.args[0]
        assert "--hmmdb" in call_args
        assert "--target-db" in call_args
        assert "--pfam-fastas-dir" in call_args
        assert "--hmmscan" in call_args
        assert "--mmseqs" in call_args
        # Default paths are non-None (the vendored Pfam-A.hmm + 200-seq
        # MMseqs2 target DB) — values must be in the cmd.
        i = call_args.index("--hmmdb")
        assert call_args[i + 1].endswith("Pfam-A.hmm")
        j = call_args.index("--target-db")
        assert call_args[j + 1].endswith("pfam_holdout_targetDB")
        k = call_args.index("--pfam-fastas-dir")
        assert call_args[k + 1].endswith("pfam_fastas_clean")


def test_upstream_eval_lineageflow_default_metrics_restricted_to_unblocked_two() -> None:
    """Wave 81 — default metrics tuple is restricted to
    ``('family_validity', 'novelty')``. The 2 OmegaFold-blocked metrics
    (``foldability`` + ``self_consistency``) require Python 3.10 + ESM-IF
    on the host Python 3.12, which the OmegaFold ``setup.py`` hard-blocks.
    Including them in the default tuple would fail every invocation with
    ``Could not find ``omegafold`` in PATH. Callers wanting the full
    4-metric pipeline pass the full tuple explicitly."""
    upstream = _import_tools_module()
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = pathlib.Path(tmp)
        fasta_path = tmp_path / "samples.fasta"
        fasta_path.write_text(">seq1\nMKTII\n", encoding="utf-8")
        outdir = tmp_path / "lf_out"
        outdir.mkdir(parents=True, exist_ok=True)
        (outdir / "summary.json").write_text("{}", encoding="utf-8")
        fake_proc = subprocess.CompletedProcess(
            args=[], returncode=0, stderr="", stdout="",
        )
        with mock.patch.object(
            upstream.subprocess, "run", return_value=fake_proc,
        ) as _mock_run:
            upstream.run_lineageflow_upstream_eval(
                fasta_path=str(fasta_path),
                output_dir=str(outdir),
            )
        call_args = _mock_run.call_args.args[0]
        i = call_args.index("--metrics")
        # Read until the next flag (anything starting with ``--``).
        metrics_passed = []
        for arg in call_args[i + 1:]:
            if arg.startswith("--"):
                break
            metrics_passed.append(arg)
        assert "family_validity" in metrics_passed
        assert "novelty" in metrics_passed
        assert "foldability" not in metrics_passed, (
            f"foldability should be omitted from default metrics (OmegaFold "
            f"Python 3.12 blocker); got {metrics_passed!r}"
        )
        assert "self_consistency" not in metrics_passed, (
            f"self_consistency should be omitted from default metrics "
            f"(depends on OmegaFold); got {metrics_passed!r}"
        )


def test_upstream_eval_lineageflow_none_kwargs_skip_arg() -> None:
    """Wave 81 — passing ``None`` for any of ``hmmdb`` / ``target_db`` /
    ``pfam_fastas_dir`` / ``hmmscan`` / ``mmseqs`` must skip the
    corresponding ``--arg`` (lets the orchestrator fall back to its
    own default). Mirrors the existing failure-mode contract."""
    upstream = _import_tools_module()
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = pathlib.Path(tmp)
        fasta_path = tmp_path / "samples.fasta"
        fasta_path.write_text(">seq1\nMKTII\n", encoding="utf-8")
        outdir = tmp_path / "lf_out"
        outdir.mkdir(parents=True, exist_ok=True)
        (outdir / "summary.json").write_text("{}", encoding="utf-8")
        fake_proc = subprocess.CompletedProcess(
            args=[], returncode=0, stderr="", stdout="",
        )
        with mock.patch.object(
            upstream.subprocess, "run", return_value=fake_proc,
        ) as _mock_run:
            upstream.run_lineageflow_upstream_eval(
                fasta_path=str(fasta_path),
                output_dir=str(outdir),
                hmmdb=None,
                target_db=None,
                pfam_fastas_dir=None,
                hmmscan=None,
                mmseqs=None,
            )
        call_args = _mock_run.call_args.args[0]
        assert "--hmmdb" not in call_args
        assert "--target-db" not in call_args
        assert "--pfam-fastas-dir" not in call_args
        assert "--hmmscan" not in call_args
        assert "--mmseqs" not in call_args


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
# 2b. Kanzi Wave 92b — honor --upstream-n-samples (N records in 1 call)
# ---------------------------------------------------------------------------


def _fake_kanzi_subprocess_success(
    n_records: int,
    *,
    rmsd_values: list[float] | None = None,
    output_jsonl_lines: list[str] | None = None,
):
    """Helper — build a fake subprocess.run side effect that simulates
    the Kanzi driver writing a ``reconstruction.json`` summary for
    ``n_records`` records (using ``rmsd_values`` if provided, otherwise
    a deterministic sequence of n_records floats). Returns a tuple of
    (CompletedProcess, output_json_path, output_jsonl_path) so the
    caller can assert what was written.
    """
    if rmsd_values is None:
        # Default: deterministic pseudo-RMSDs that make mean=1.0,
        # std=0.1 so the test can assert the math.
        rmsd_values = [
            round(1.0 + 0.1 * ((-1) ** i) * (i % 5), 6)
            for i in range(n_records)
        ]
    summary = {
        "n_seqs": float(n_records),
        "mean_rmsd_A": float(sum(rmsd_values) / len(rmsd_values)),
        "min_rmsd_A": float(min(rmsd_values)),
        "max_rmsd_A": float(max(rmsd_values)),
    }
    if n_records > 1:
        mean = summary["mean_rmsd_A"]
        variance = sum((x - mean) ** 2 for x in rmsd_values) / (n_records - 1)
        summary["std_rmsd_A"] = float(variance ** 0.5)
        sem = summary["std_rmsd_A"] / (n_records ** 0.5)
        summary["ci_95_low_A"] = float(mean - 1.96 * sem)
        summary["ci_95_high_A"] = float(mean + 1.96 * sem)
    else:
        summary["std_rmsd_A"] = 0.0
        summary["ci_95_low_A"] = summary["mean_rmsd_A"]
        summary["ci_95_high_A"] = summary["mean_rmsd_A"]
    summary["max_records_arg"] = float(n_records)
    per_seq = {
        f"seq_{i}": rmsd_values[i] for i in range(n_records)
    }

    def _side_effect(cmd, *args, **kwargs):
        # Write the output JSON the wrapper expects to read back.
        # cmd shape: [sys.executable, "-c", driver, "--input", ...,
        # "--ckpt", ..., "--output", out_json, "--max-records", N,
        # optional "--output-jsonl", out_jsonl]
        out_idx = cmd.index("--output")
        out_json = pathlib.Path(cmd[out_idx + 1])
        out_json.parent.mkdir(parents=True, exist_ok=True)
        out_json.write_text(
            json.dumps({"per_seq": per_seq, "summary": summary}),
            encoding="utf-8",
        )
        if "--output-jsonl" in cmd:
            jl_idx = cmd.index("--output-jsonl")
            out_jsonl = pathlib.Path(cmd[jl_idx + 1])
            out_jsonl.parent.mkdir(parents=True, exist_ok=True)
            if output_jsonl_lines is None:
                lines = [
                    json.dumps({"seq_id": f"seq_{i}", "rmsd_A": rmsd_values[i]})
                    for i in range(n_records)
                ]
            else:
                lines = output_jsonl_lines
            out_jsonl.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return subprocess.CompletedProcess(
            args=cmd, returncode=0, stderr="", stdout="",
        )
    return _side_effect


def test_upstream_eval_kanzi_wave92b_n_records_in_single_call() -> None:
    """Wave 92b — Test 1: Kanzi N=1000 path produces 1 RMSD metric ×
    N records in a SINGLE subprocess call. Pre-Wave-92b the wrapper
    always passed the full input file to the driver regardless of
    ``--upstream-n-samples`` (the knob from
    ``tools.run_real_ckpt_eval`` was ignored at this layer). After the
    Wave 92b patch, the wrapper caps records at min(n_samples,
    file_count) and writes mean + std + 95% CI for N records.
    """
    upstream = _import_tools_module()
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = pathlib.Path(tmp)
        coords_path = tmp_path / "samples.ca.txt"
        # 100 valid 9-float records (3 Cα coords × 3 records per line).
        # Note: each line in the input file is one record (comma-sep
        # float list divisible by 3). We write 100 records to make the
        # cap observable.
        coords_path.write_text(
            "\n".join(
                ",".join(
                    f"{x:.4f}" for x in (
                        0.1 * i, 0.2 * i, 0.3 * i,
                        0.4 * i, 0.5 * i, 0.6 * i,
                        0.7 * i, 0.8 * i, 0.9 * i,
                    )
                )
                for i in range(1, 101)
            ) + "\n",
            encoding="utf-8",
        )
        outdir = tmp_path / "kz_out"
        outdir.mkdir(parents=True, exist_ok=True)
        side_effect = _fake_kanzi_subprocess_success(
            n_records=100,
            rmsd_values=[
                round(1.0 + 0.001 * i, 6) for i in range(100)
            ],
        )
        with mock.patch.object(
            upstream.subprocess, "run", side_effect=side_effect,
        ) as _mock_run:
            result = upstream.run_kanzi_upstream_eval(
                sequences_path=str(coords_path),
                output_dir=str(outdir),
                n_samples=1000,  # request N=1000
            )
        # Subprocess called exactly once — NOT 1000 times.
        assert _mock_run.call_count == 1
        # The wrapper honored n_samples=1000 by passing
        # ``--max-records 100`` (= min(n_samples, file_count)) to the
        # driver (file has 100 records).
        call_args = _mock_run.call_args.args[0]
        assert "--max-records" in call_args
        idx = call_args.index("--max-records")
        assert int(call_args[idx + 1]) == 100, (
            f"expected --max-records 100 (= min(1000, file_count=100)), "
            f"got {call_args[idx + 1]}"
        )
        # Summary stats computed end-to-end (mean / std / 95% CI).
        assert result["status"] == 1.0
        assert result["n_seqs"] == 100.0
        assert "mean_rmsd_A" in result
        assert "std_rmsd_A" in result
        assert "ci_95_low_A" in result
        assert "ci_95_high_A" in result
        # n_samples bookkeeping surfaced.
        assert result["n_samples_requested"] == 1000.0
        assert result["n_samples_file"] == 100.0
        assert result["n_samples_effective"] == 100.0
        assert (
            result.get("upstream_orchestrator")
            == "kanzi.DAE.encode+decode+kabsch_rmsd"
        )


def test_upstream_eval_kanzi_wave92b_n_samples_knob_honored() -> None:
    """Wave 92b — Test 2: ``--upstream-n-samples N`` knob is honored.
    A file with N=100 records and ``n_samples=10`` cap must produce
    ``--max-records 10`` in the subprocess call (not 100, not 0).
    The pre-Wave-92b wrapper ignored the flag entirely and passed
    the full file.
    """
    upstream = _import_tools_module()
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = pathlib.Path(tmp)
        coords_path = tmp_path / "samples.ca.txt"
        # 100 valid records (9 floats each).
        coords_path.write_text(
            "\n".join(
                ",".join(
                    f"{x:.4f}" for x in (
                        0.1 * i, 0.2 * i, 0.3 * i,
                        0.4 * i, 0.5 * i, 0.6 * i,
                        0.7 * i, 0.8 * i, 0.9 * i,
                    )
                )
                for i in range(1, 101)
            ) + "\n",
            encoding="utf-8",
        )
        outdir = tmp_path / "kz_out"
        outdir.mkdir(parents=True, exist_ok=True)
        # Subprocess simulates only processing 10 records.
        side_effect = _fake_kanzi_subprocess_success(n_records=10)
        with mock.patch.object(
            upstream.subprocess, "run", side_effect=side_effect,
        ) as _mock_run:
            result = upstream.run_kanzi_upstream_eval(
                sequences_path=str(coords_path),
                output_dir=str(outdir),
                n_samples=10,
            )
        call_args = _mock_run.call_args.args[0]
        idx = call_args.index("--max-records")
        # Cap = min(n_samples=10, file_count=100) = 10.
        assert int(call_args[idx + 1]) == 10, (
            f"expected --max-records 10 (= min(10, 100)), "
            f"got {call_args[idx + 1]}"
        )
        assert result["n_seqs"] == 10.0
        assert result["n_samples_requested"] == 10.0
        assert result["n_samples_file"] == 100.0
        assert result["n_samples_effective"] == 10.0
        # Edge case: n_samples=0 means "all records".
        with mock.patch.object(
            upstream.subprocess, "run", side_effect=side_effect,
        ) as _mock_run_all:
            result_all = upstream.run_kanzi_upstream_eval(
                sequences_path=str(coords_path),
                output_dir=str(outdir),
                n_samples=0,
            )
        call_args2 = _mock_run_all.call_args.args[0]
        idx2 = call_args2.index("--max-records")
        assert int(call_args2[idx2 + 1]) == 100, (
            "n_samples=0 should mean 'process all records' (= file_count)"
        )
        assert result_all["n_samples_effective"] == 100.0
        # Edge case: n_samples larger than file_count caps at file_count.
        with mock.patch.object(
            upstream.subprocess, "run", side_effect=side_effect,
        ) as _mock_run_over:
            result_over = upstream.run_kanzi_upstream_eval(
                sequences_path=str(coords_path),
                output_dir=str(outdir),
                n_samples=10000,
            )
        call_args3 = _mock_run_over.call_args.args[0]
        idx3 = call_args3.index("--max-records")
        assert int(call_args3[idx3 + 1]) == 100, (
            "n_samples=10000 should cap at file_count=100"
        )


def test_upstream_eval_kanzi_wave92b_mean_std_ci_math() -> None:
    """Wave 92b — Test 3: mean + std + 95% CI are computed correctly.
    Use synthetic RMSDs [1.0, 2.0, 3.0, 4.0, 5.0]:
        mean = 3.0
        std (sample, n-1) = sqrt(2.5) ≈ 1.5811
        sem = 1.5811 / sqrt(5) ≈ 0.7071
        ci_95_low = 3.0 - 1.96 * 0.7071 ≈ 1.6140
        ci_95_high = 3.0 + 1.96 * 0.7071 ≈ 4.3860
    """
    upstream = _import_tools_module()
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = pathlib.Path(tmp)
        coords_path = tmp_path / "samples.ca.txt"
        # 5 records (3 floats each).
        coords_path.write_text(
            "0,0,0\n1,0,0\n2,0,0\n3,0,0\n4,0,0\n", encoding="utf-8",
        )
        outdir = tmp_path / "kz_out"
        outdir.mkdir(parents=True, exist_ok=True)
        side_effect = _fake_kanzi_subprocess_success(
            n_records=5,
            rmsd_values=[1.0, 2.0, 3.0, 4.0, 5.0],
        )
        with mock.patch.object(
            upstream.subprocess, "run", side_effect=side_effect,
        ):
            result = upstream.run_kanzi_upstream_eval(
                sequences_path=str(coords_path),
                output_dir=str(outdir),
                n_samples=5,
            )
        assert result["status"] == 1.0
        assert result["n_seqs"] == 5.0
        # Mean
        assert result["mean_rmsd_A"] == pytest.approx(3.0, rel=1e-6)
        # Std (Bessel-corrected sample std)
        assert result["std_rmsd_A"] == pytest.approx(2.5 ** 0.5, rel=1e-4)
        # 95% CI (z=1.96)
        import math as _math
        expected_sem = (2.5 ** 0.5) / _math.sqrt(5)
        expected_ci_low = 3.0 - 1.96 * expected_sem
        expected_ci_high = 3.0 + 1.96 * expected_sem
        assert result["ci_95_low_A"] == pytest.approx(expected_ci_low, rel=1e-4)
        assert result["ci_95_high_A"] == pytest.approx(expected_ci_high, rel=1e-4)
        # CI half-width ≈ 1.96 * std / sqrt(n) and CI brackets the mean.
        assert result["ci_95_low_A"] < result["mean_rmsd_A"]
        assert result["ci_95_high_A"] > result["mean_rmsd_A"]
        # Min / max preserved.
        assert result["min_rmsd_A"] == 1.0
        assert result["max_rmsd_A"] == 5.0


def test_upstream_eval_kanzi_wave92b_output_jsonl_honored() -> None:
    """Wave 92b — Test 4: ``output_jsonl`` flag passes ``--output-jsonl``
    to the driver and surfaces ``output_jsonl=1.0`` in the result dict.
    Pre-Wave-92b the wrapper had no JSONL output path; downstream
    codebook-metric helpers in :mod:`tools.paper_metrics_kanzi` can
    now consume the per-record encoded indices without re-running
    ``DAE.encode``.
    """
    upstream = _import_tools_module()
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = pathlib.Path(tmp)
        coords_path = tmp_path / "samples.ca.txt"
        coords_path.write_text(
            "0,0,0\n1,0,0\n", encoding="utf-8",
        )
        outdir = tmp_path / "kz_out"
        outdir.mkdir(parents=True, exist_ok=True)
        side_effect = _fake_kanzi_subprocess_success(
            n_records=2, rmsd_values=[1.5, 2.5],
        )
        with mock.patch.object(
            upstream.subprocess, "run", side_effect=side_effect,
        ) as _mock_run:
            jsonl_path = tmp_path / "per_record.jsonl"
            result = upstream.run_kanzi_upstream_eval(
                sequences_path=str(coords_path),
                output_dir=str(outdir),
                n_samples=2,
                output_jsonl=jsonl_path,
            )
        call_args = _mock_run.call_args.args[0]
        assert "--output-jsonl" in call_args
        idx = call_args.index("--output-jsonl")
        assert call_args[idx + 1] == str(jsonl_path)
        # Wrapper surfaces that JSONL was written.
        assert result["output_jsonl"] == 1.0
        # The driver wrote the JSONL — verify the file exists with the
        # expected per-record lines.
        assert jsonl_path.is_file(), f"expected {jsonl_path} to exist"
        lines = jsonl_path.read_text(encoding="utf-8").strip().split("\n")
        assert len(lines) == 2
        rec0 = json.loads(lines[0])
        rec1 = json.loads(lines[1])
        assert rec0["seq_id"] == "seq_0"
        assert rec0["rmsd_A"] == pytest.approx(1.5, rel=1e-6)
        assert rec1["seq_id"] == "seq_1"
        assert rec1["rmsd_A"] == pytest.approx(2.5, rel=1e-6)


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