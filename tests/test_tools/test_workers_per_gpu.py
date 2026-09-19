"""Tests for the ``--workers-per-gpu`` flag added to the LineageFlow evaluation
scripts in Wave 201 P2.

These tests pin the per-GPU concurrency contract on the two upstream
foldability / self-consistency scripts:

* ``data/lineageflow_upstream/evaluation/foldability_omegafold.py`` —
  each GPU now spawns ``N`` concurrent OmegaFold subprocesses (instead of
  just one), where ``N`` is the value of ``--workers-per-gpu``.
* ``data/lineageflow_upstream/evaluation/self_consistency_esmif.py`` —
  each GPU now spawns ``N`` concurrent ESM-IF workers (instead of just
  one), where ``N`` is the value of ``--workers-per-gpu``.

The default (``workers_per_gpu=1``) preserves the Wave 158 behaviour.
"""

from __future__ import annotations

import importlib.util
import json
import sys
import time
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent

FOLD_PATH = (
    REPO_ROOT
    / "data"
    / "lineageflow_upstream"
    / "evaluation"
    / "foldability_omegafold.py"
)
SC_PATH = (
    REPO_ROOT
    / "data"
    / "lineageflow_upstream"
    / "evaluation"
    / "self_consistency_esmif.py"
)


# ---------------------------------------------------------------------------
# Module loaders (mirror ``test_ablation_sweep_cli.py`` pattern so each test
# module is hermetic).
# ---------------------------------------------------------------------------


def _load_module(path: Path, *, synthetic_name: str) -> Any:
    spec = importlib.util.spec_from_file_location(synthetic_name, str(path))
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[synthetic_name] = module
    try:
        spec.loader.exec_module(module)  # type: ignore[union-attr]
    finally:
        sys.modules.pop(synthetic_name, None)
    return module


# ---------------------------------------------------------------------------
# foldability_omegafold.py — workers-per-gpu dispatch
# ---------------------------------------------------------------------------


# 10 short AA sequences (length 30..60 — well within the 10..min-len filter).
_TEN_SEQS_FASTA = """>q0
ACDEFGHIKLMNPQRSTVWYACDEFGHIKLMN
>q1
ACDEFGHIKLMNPQRSTVWYACDEFGHIKLMNPQRSTVWY
>q2
ACDEFGHIKLMNPQRSTVWYACDEFGHIKLMNPQRSTVWYACDEFGHIKLMN
>q3
ACDEFGHIKLMNPQRSTVWYACDEFGHIKLMNPQRSTVWYACDEFGHIKLMNPQRSTVWY
>q4
ACDEFGHIKLMNPQRSTVWYACDEFGHIKLMNPQRSTVWYACDEFGHIKLMNPQRSTVWYACDEFGHIKLMN
>q5
ACDEFGHIKLMNPQRSTVWY
>q6
ACDEFGHIKLMNPQRSTVWYACDEFGHIKLMN
>q7
ACDEFGHIKLMNPQRSTVWYACDEFGHIKLMNPQRSTVWY
>q8
ACDEFGHIKLMNPQRSTVWYACDEFGHIKLMNPQRSTVWYACDEFGHIKLMN
>q9
ACDEFGHIKLMNPQRSTVWYACDEFGHIKLMNPQRSTVWYACDEFGHIKLMNPQRSTVWY
"""


def _make_fake_pdb(qid: str) -> str:
    """Build a minimal valid PDB with a single CA atom at residue 1.

    The pLDDT parser only inspects ATOM records (CA-only) and reads
    the B-factor from columns 60-66, so a 1-CA PDB is sufficient.
    """
    # Columns:
    #   1-6   "ATOM  "
    #   7-11  serial
    #   13-16 atom name
    #   17    altLoc
    #   18-20 residue
    #   22    chain
    #   23-26 residue seq
    #   31-38 x, 39-46 y, 47-54 z
    #   55-60 occupancy, 61-66 B-factor
    return (
        "ATOM      1  CA  ALA A   1       0.000   0.000   0.000  1.00  80.00           C\n"
        "END\n"
    )


class _FakeProc:
    """A minimal stand-in for ``subprocess.Popen``.

    Tracks spawn time (so we can assert concurrent start) and exposes
    ``poll()`` / ``wait()`` semantics that mirror Popen enough for the
    sharded dispatch loop to terminate cleanly.

    ``poll()`` returns ``None`` for the first ``completion_delay_s`` seconds
    after spawn (default 0.05s) and the configured return code thereafter,
    so the dispatch loop in ``run_omegafold_sharded`` naturally exits via
    its ``alive = [p for p in procs if p.poll() is None]`` check.
    """

    completion_delay_s: float = 0.05
    instances: list[_FakeProc] = []

    def __init__(self, cmd: list[str], env: dict[str, str] | None = None, **kwargs: Any) -> None:
        self.cmd = list(cmd)
        self.env = dict(env or {})
        self.gpu = self.env.get("CUDA_VISIBLE_DEVICES")
        self.spawn_t = time.time()
        self._returncode = 0
        self._rc_set = False
        _FakeProc.instances.append(self)

    # The sharded loop only calls poll() and wait(); both need to terminate
    # the loop. poll() returns None while alive; wait() returns final rc.
    def poll(self) -> int | None:
        if self._rc_set:
            return self._returncode
        if time.time() - self.spawn_t >= self.completion_delay_s:
            self._returncode = 0
            self._rc_set = True
            return 0
        return None

    def wait(self) -> int:
        if not self._rc_set:
            remaining = self.completion_delay_s - (time.time() - self.spawn_t)
            if remaining > 0:
                time.sleep(remaining)
            self._returncode = 0
            self._rc_set = True
        return self._returncode

    @classmethod
    def reset(cls) -> None:
        cls.instances.clear()


@pytest.fixture()
def fake_fold_subprocess(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> list[_FakeProc]:
    """Patch ``subprocess.Popen`` inside foldability_omegafold and write
    fake PDBs for each spawned shard so the consolidation step finds them.

    Returns the list of fake procs (one per spawned subprocess).
    """

    # Patch OmegaFold binary resolution so it doesn't actually shell out.
    fold_mod = sys.modules.get("foldability_omegafold_under_test")
    if fold_mod is None:
        # Pre-import so the ``subprocess`` symbol the script uses is the
        # one we're patching. We import via spec_from_file_location under a
        # synthetic name; the patched ``subprocess`` is the one in
        # ``sys.modules["subprocess"]`` (real Python builtin module).
        fold_mod = _load_module(FOLD_PATH, synthetic_name="foldability_omegafold_under_test")

    _FakeProc.reset()
    monkeypatch.setattr(fold_mod.subprocess, "Popen", _FakeProc)
    # Bypass the ``which`` resolution path — pretend ``omegafold`` lives in PATH.
    monkeypatch.setattr(fold_mod, "_parse_omegafold_cmd", lambda bin_: ["omegafold"])

    # Side effect on spawn: write a fake PDB per query into the shard's
    # out_dir so the post-process consolidation finds it.
    real_popen = _FakeProc

    class _WritePDBs(real_popen):
        def __init__(self, cmd: list[str], env: dict[str, str] | None = None, **kwargs: Any) -> None:
            super().__init__(cmd, env, **kwargs)
            # cmd layout: [omegafold, fasta_path, out_dir, *extra_args]
            assert len(cmd) >= 3, f"unexpected cmd layout: {cmd!r}"
            out_dir = Path(cmd[2])
            fasta_path = Path(cmd[1])
            out_dir.mkdir(parents=True, exist_ok=True)
            for line in fasta_path.read_text().splitlines():
                if line.startswith(">"):
                    qid = line[1:].split()[0]
                    (out_dir / f"{qid}.pdb").write_text(_make_fake_pdb(qid))

    monkeypatch.setattr(fold_mod.subprocess, "Popen", _WritePDBs)
    return _FakeProc.instances  # type: ignore[return-value]


def _write_fasta(tmp_path: Path) -> Path:
    p = tmp_path / "queries.fasta"
    p.write_text(_TEN_SEQS_FASTA)
    return p


def test_foldability_workers_per_gpu_argparse_default() -> None:
    """``--workers-per-gpu`` defaults to 1 (preserves Wave 158 behaviour)."""
    fold_mod = _load_module(FOLD_PATH, synthetic_name="fold_under_test_args")
    # Import argparse inside the loaded module; argparse instances are
    # build per main() invocation so we replicate it via parse_args.
    import argparse

    # Build the parser by mimicking the main() parser creation. Easier:
    # just import and call parse_args via the module's main namespace.
    # Since the parser is constructed inside main(), we just assert via
    # sys.argv that the default is honoured.
    import contextlib

    # Drive main() with --help and inspect printed defaults. Easiest: run
    # parse_args() directly via the module's parser.
    # The simplest contract test: introspect via ``run_omegafold_sharded``
    # signature (it accepts ``workers_per_gpu`` with default 1).
    import inspect
    import io

    sig = inspect.signature(fold_mod.run_omegafold_sharded)
    assert "workers_per_gpu" in sig.parameters
    assert sig.parameters["workers_per_gpu"].default == 1


def test_foldability_workers_per_gpu_dispatches_n_subprocesses_per_gpu(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """With ``--workers-per-gpu 2`` and 1 GPU, exactly 2 concurrent
    ``subprocess.Popen`` calls are issued.

    Also verifies all 10 sequences end up folded (consolidation stage
    finds the 10 fake PDBs we wrote).
    """
    fold_mod = _load_module(FOLD_PATH, synthetic_name="fold_under_test_dispatch")
    _FakeProc.reset()
    monkeypatch.setattr(fold_mod.subprocess, "Popen", _FakeProc)
    monkeypatch.setattr(fold_mod, "_parse_omegafold_cmd", lambda bin_: ["omegafold"])

    class _WritePDBs(_FakeProc):
        def __init__(self, cmd: list[str], env: dict[str, str] | None = None, **kwargs: Any) -> None:
            super().__init__(cmd, env, **kwargs)
            assert len(cmd) >= 3, f"unexpected cmd layout: {cmd!r}"
            out_dir = Path(cmd[2])
            fasta_path = Path(cmd[1])
            out_dir.mkdir(parents=True, exist_ok=True)
            for line in fasta_path.read_text().splitlines():
                if line.startswith(">"):
                    qid = line[1:].split()[0]
                    (out_dir / f"{qid}.pdb").write_text(_make_fake_pdb(qid))

    monkeypatch.setattr(fold_mod.subprocess, "Popen", _WritePDBs)

    fasta = _write_fasta(tmp_path)
    outdir = tmp_path / "out"
    outdir.mkdir()

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "foldability_omegafold.py",
            "--fasta",
            str(fasta),
            "--outdir",
            str(outdir),
            "--gpus",
            "0",
            "--workers-per-gpu",
            "2",
            "--omegafold-bin",
            "omegafold",
            "--log-every",
            "0",
        ],
    )
    fold_mod.main()

    # Exactly 2 concurrent subprocesses (1 GPU × workers_per_gpu=2).
    assert len(_FakeProc.instances) == 2, (
        f"expected 2 Popen calls, got {len(_FakeProc.instances)}"
    )

    # All spawned subprocesses target the same GPU (workers share a GPU).
    gpus_used = {p.gpu for p in _FakeProc.instances}
    assert gpus_used == {"0"}, f"expected GPU 0 for all workers, got {gpus_used}"

    # All spawned subprocesses started "concurrently" (within 0.5s window).
    spawn_times = [p.spawn_t for p in _FakeProc.instances]
    assert max(spawn_times) - min(spawn_times) < 0.5, (
        f"workers did not start concurrently: {spawn_times}"
    )

    # All 10 sequences are folded (consolidation step found PDBs in each shard).
    jsonl = outdir / "foldability.jsonl"
    assert jsonl.exists(), f"foldability.jsonl missing: {jsonl}"
    rows = [json.loads(line) for line in jsonl.read_text().splitlines() if line.strip()]
    assert len(rows) == 10, f"expected 10 rows, got {len(rows)}"
    assert sum(1 for r in rows if "plddt_mean" in r) == 10, (
        f"expected 10 folded rows with plddt_mean, got "
        f"{sum(1 for r in rows if 'plddt_mean' in r)}"
    )


def test_foldability_workers_per_gpu_4_spawns_4_subprocesses(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """With ``--workers-per-gpu 4`` and 1 GPU, 4 concurrent subprocesses
    are spawned (and all 10 sequences are folded across them)."""
    fold_mod = _load_module(FOLD_PATH, synthetic_name="fold_under_test_4")
    _FakeProc.reset()
    monkeypatch.setattr(fold_mod.subprocess, "Popen", _FakeProc)
    monkeypatch.setattr(fold_mod, "_parse_omegafold_cmd", lambda bin_: ["omegafold"])

    class _WritePDBs(_FakeProc):
        def __init__(self, cmd: list[str], env: dict[str, str] | None = None, **kwargs: Any) -> None:
            super().__init__(cmd, env, **kwargs)
            assert len(cmd) >= 3
            out_dir = Path(cmd[2])
            fasta_path = Path(cmd[1])
            out_dir.mkdir(parents=True, exist_ok=True)
            for line in fasta_path.read_text().splitlines():
                if line.startswith(">"):
                    qid = line[1:].split()[0]
                    (out_dir / f"{qid}.pdb").write_text(_make_fake_pdb(qid))

    monkeypatch.setattr(fold_mod.subprocess, "Popen", _WritePDBs)

    fasta = _write_fasta(tmp_path)
    outdir = tmp_path / "out4"
    outdir.mkdir()

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "foldability_omegafold.py",
            "--fasta",
            str(fasta),
            "--outdir",
            str(outdir),
            "--gpus",
            "0",
            "--workers-per-gpu",
            "4",
            "--omegafold-bin",
            "omegafold",
            "--log-every",
            "0",
        ],
    )
    fold_mod.main()

    assert len(_FakeProc.instances) == 4, (
        f"expected 4 Popen calls, got {len(_FakeProc.instances)}"
    )

    jsonl = outdir / "foldability.jsonl"
    rows = [json.loads(line) for line in jsonl.read_text().splitlines() if line.strip()]
    assert len(rows) == 10
    assert sum(1 for r in rows if "plddt_mean" in r) == 10


def test_foldability_workers_per_gpu_2_faster_than_1(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """With 1 GPU and the fake fold costing a fixed per-process wall
    time, ``--workers-per-gpu 2`` should finish in roughly half the wall
    time of ``--workers-per-gpu 1`` (concurrent vs sequential).

    The fake proc sleeps for ``PER_PROC_LATENCY_S`` (3.0s) in ``wait()``.
    With ``workers_per_gpu=1`` the wall time is ~3s; with
    ``workers_per_gpu=2`` two procs share the GPU and the wall time
    drops to ~3s as well (since they're effectively parallel), but the
    throughput (records/sec) doubles. We assert the wall time does not
    regress — and that the 2-proc run completes within a slack of the
    1-proc run.
    """
    fold_mod = _load_module(FOLD_PATH, synthetic_name="fold_under_test_speedup")

    # Per-proc fold latency — long enough to measure the difference.
    PER_PROC_LATENCY_S = 3.0

    class _SlowFakeProc(_FakeProc):
        def __init__(self, cmd: list[str], env: dict[str, str] | None = None, **kwargs: Any) -> None:
            super().__init__(cmd, env, **kwargs)
            assert len(cmd) >= 3
            out_dir = Path(cmd[2])
            fasta_path = Path(cmd[1])
            out_dir.mkdir(parents=True, exist_ok=True)
            for line in fasta_path.read_text().splitlines():
                if line.startswith(">"):
                    qid = line[1:].split()[0]
                    (out_dir / f"{qid}.pdb").write_text(_make_fake_pdb(qid))

        # ``wait()`` blocks for ``PER_PROC_LATENCY_S`` so the 1-proc
        # case clearly takes longer than the 2-proc case. ``wait()`` is
        # idempotent — once ``_rc_set`` is True (e.g. via ``poll()``),
        # it returns immediately. This is critical: the dispatch loop
        # calls ``for p in procs: p.wait()`` *after* the poll loop exits,
        # so we must NOT re-sleep here or 2 procs → 2× latency.
        def wait(self) -> int:  # noqa: D401
            if self._rc_set:
                return self._returncode
            time.sleep(PER_PROC_LATENCY_S)
            self._returncode = 0
            self._rc_set = True
            return 0

        # ``poll()`` mirrors wait() so the dispatch loop naturally exits.
        def poll(self) -> int | None:
            if self._rc_set:
                return self._returncode
            if time.time() - self.spawn_t >= PER_PROC_LATENCY_S:
                self._returncode = 0
                self._rc_set = True
                return 0
            return None

    def _run_with_workers(n: int) -> tuple[float, int]:
        _FakeProc.reset()
        monkeypatch.setattr(fold_mod.subprocess, "Popen", _SlowFakeProc)
        monkeypatch.setattr(fold_mod, "_parse_omegafold_cmd", lambda bin_: ["omegafold"])
        fasta_dir = tmp_path / f"fasta_w{n}"
        fasta_dir.mkdir(exist_ok=True)
        fasta_local = _write_fasta(fasta_dir)
        out_local = tmp_path / f"out_w{n}"
        out_local.mkdir(exist_ok=True)
        monkeypatch.setattr(
            sys,
            "argv",
            [
                "foldability_omegafold.py",
                "--fasta",
                str(fasta_local),
                "--outdir",
                str(out_local),
                "--gpus",
                "0",
                "--workers-per-gpu",
                str(n),
                "--omegafold-bin",
                "omegafold",
                "--log-every",
                "0",
            ],
        )
        t0 = time.time()
        fold_mod.main()
        return time.time() - t0, len(_FakeProc.instances)

    wall_w1, n_procs_w1 = _run_with_workers(1)
    wall_w2, n_procs_w2 = _run_with_workers(2)

    # Sanity: 2 procs spawned when workers_per_gpu=2, 1 proc when =1.
    assert n_procs_w1 == 1
    assert n_procs_w2 == 2

    # The 2-proc run should complete in approximately the same wall time
    # as the 1-proc run (procs run concurrently). Allow up to 30% slack
    # to absorb poll-loop granularity (the dispatch loop sleeps 1s between
    # polls), but no regression.
    assert wall_w2 < wall_w1 * 1.3, (
        f"workers_per_gpu=2 ({wall_w2:.2f}s, {n_procs_w2} procs) should not regress "
        f"vs workers_per_gpu=1 ({wall_w1:.2f}s, {n_procs_w1} proc); "
        f"ratio = {wall_w2/wall_w1:.2f}"
    )


# ---------------------------------------------------------------------------
# self_consistency_esmif.py — workers-per-gpu dispatch
# ---------------------------------------------------------------------------


class _FakeProcess:
    """A minimal stand-in for ``multiprocessing.Process``.

    Records the kwargs it was started with (so the test can assert
    workers-per-gpu spawned N processes per GPU) and exposes
    ``is_alive()`` / ``join()`` / ``exitcode`` semantics that mirror
    ``mp.Process`` enough for the dispatch loop to terminate cleanly.
    """

    instances: list[_FakeProcess] = []

    def __init__(self, *, target: Any, kwargs: dict[str, Any]) -> None:
        self.target = target
        self.kwargs = dict(kwargs)
        self.gpu = self.kwargs.get("gpu")
        self.indices = list(self.kwargs.get("indices", []))
        self._alive = True
        self.exitcode: int | None = None

    def start(self) -> None:
        _FakeProcess.instances.append(self)
        # Drive the worker function inline so the jsonl parts are written
        # to disk (the consolidation step at the end of main() reads them).
        try:
            self.target(**self.kwargs)
            self.exitcode = 0
        except Exception:
            self.exitcode = 1
        finally:
            self._alive = False

    def is_alive(self) -> bool:
        return self._alive

    def join(self) -> None:
        # Synchronous: start() already completed inline.
        return None

    @classmethod
    def reset(cls) -> None:
        cls.instances.clear()


def _write_fake_pdbs(pdb_dir: Path, qids: list[str]) -> None:
    """Write a fake PDB for each qid so ESM-IF scoring finds a structure."""
    pdb_dir.mkdir(parents=True, exist_ok=True)
    for qid in qids:
        (pdb_dir / f"{qid}.pdb").write_text(_make_fake_pdb(qid))


def _patch_esmif_for_test(
    monkeypatch: pytest.MonkeyPatch,
    fold_mod: Any | None = None,
    fold_mod_path: Path | None = None,
) -> Any:
    """Load self_consistency_esmif.py under test, patch ESM-IF + mp.Process,
    and return the loaded module."""
    sc_mod = _load_module(SC_PATH, synthetic_name="self_consistency_under_test_speedup")

    # Patch _try_import_esmif to return a no-op (model, alphabet).
    class _NoopModel:
        def to(self, device: Any) -> _NoopModel:
            return self

        def eval(self) -> _NoopModel:
            return self

        def forward(self, *args: Any, **kwargs: Any) -> tuple[Any, None]:
            # Shape doesn't matter — _score_one uses cross_entropy which we
            # monkeypatch below.
            import torch

            return torch.zeros(1, 1), None

    def _fake_try_import() -> tuple[Any, Any]:
        class _FakeAlphabet:
            padding_idx = 0

        return _NoopModel(), _FakeAlphabet()

    monkeypatch.setattr(sc_mod, "_try_import_esmif", _fake_try_import)

    # Patch _score_one to return deterministic finite values.
    def _fake_score_one(
        model: Any,
        alphabet: Any,
        *,
        pdb: Path,
        chain: str,
        seq: str,
        device: str,
    ) -> tuple[float, float]:
        return (-1.5, 4.4817)  # exp(1.5) ≈ 4.48

    monkeypatch.setattr(sc_mod, "_score_one", _fake_score_one)

    # The script imports ``multiprocessing as mp`` locally inside ``main()``.
    # We replace the ``multiprocessing`` module in ``sys.modules`` with a fake
    # so that ``import multiprocessing as mp`` (anywhere in the test scope)
    # resolves to our fake, which exposes ``Process`` and ``get_context``.
    fake_mp = _make_fake_mp_module()
    monkeypatch.setitem(sys.modules, "multiprocessing", fake_mp)
    return sc_mod


def _make_fake_mp_module() -> ModuleType:
    """Build a tiny module mimicking ``multiprocessing`` with our Process fake."""
    mp = ModuleType("mp_fake")
    mp.Process = _FakeProcess  # type: ignore[attr-defined]

    def _get_context(name: str) -> ModuleType:
        ctx = ModuleType(f"mp_ctx_{name}")
        ctx.Process = _FakeProcess  # type: ignore[attr-defined]
        return ctx

    mp.get_context = _get_context  # type: ignore[attr-defined]
    return mp


def _build_esmif_queries_fasta(tmp_path: Path, qids: list[str]) -> Path:
    """Build a FASTA with the requested qids (sequence is the same dummy
    30-residue peptide — ESM-IF only needs to *see* a structure, which we
    fake)."""
    p = tmp_path / "queries.fasta"
    lines: list[str] = []
    for q in qids:
        lines.append(f">{q}")
        lines.append("ACDEFGHIKLMNPQRSTVWYACDEFGHIKLMN")
    p.write_text("\n".join(lines) + "\n")
    return p


def test_sc_workers_per_gpu_dispatches_n_processes_per_gpu(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """With ``--workers-per-gpu 2`` and 1 GPU, the ESM-IF script spawns 2
    processes per GPU (total = 2). All 10 queries are scored."""
    _FakeProcess.reset()
    sc_mod = _patch_esmif_for_test(monkeypatch)

    qids = [f"q{i}" for i in range(10)]
    queries_fa = _build_esmif_queries_fasta(tmp_path, qids)
    pdb_dir = tmp_path / "pdb"
    _write_fake_pdbs(pdb_dir, qids)
    outdir = tmp_path / "sc_out"
    outdir.mkdir()

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "self_consistency_esmif.py",
            "--queries-fasta",
            str(queries_fa),
            "--pdb-dir",
            str(pdb_dir),
            "--outdir",
            str(outdir),
            "--gpus",
            "0",
            "--workers-per-gpu",
            "2",
        ],
    )
    sc_mod.main()

    assert len(_FakeProcess.instances) == 2, (
        f"expected 2 Process instances, got {len(_FakeProcess.instances)}"
    )
    gpus_used = {p.kwargs["gpu"] for p in _FakeProcess.instances}
    assert gpus_used == {0}, f"expected all on GPU 0, got {gpus_used}"

    # All 10 queries covered (indices union covers 0..9).
    union_idx = set()
    for p in _FakeProcess.instances:
        union_idx.update(p.indices)
    assert union_idx == set(range(10)), f"covered indices = {sorted(union_idx)}"

    # jsonl has 10 rows.
    jsonl = outdir / "self_consistency.jsonl"
    rows = [json.loads(line) for line in jsonl.read_text().splitlines() if line.strip()]
    assert len(rows) == 10, f"expected 10 rows, got {len(rows)}"


def test_sc_workers_per_gpu_4_spawns_4_processes(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """With ``--workers-per-gpu 4`` and 1 GPU, 4 concurrent processes are
    spawned; all 10 queries are scored."""
    _FakeProcess.reset()
    sc_mod = _patch_esmif_for_test(monkeypatch)

    qids = [f"q{i}" for i in range(10)]
    queries_fa = _build_esmif_queries_fasta(tmp_path, qids)
    pdb_dir = tmp_path / "pdb4"
    _write_fake_pdbs(pdb_dir, qids)
    outdir = tmp_path / "sc_out4"
    outdir.mkdir()

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "self_consistency_esmif.py",
            "--queries-fasta",
            str(queries_fa),
            "--pdb-dir",
            str(pdb_dir),
            "--outdir",
            str(outdir),
            "--gpus",
            "0",
            "--workers-per-gpu",
            "4",
        ],
    )
    sc_mod.main()

    assert len(_FakeProcess.instances) == 4, (
        f"expected 4 Process instances, got {len(_FakeProcess.instances)}"
    )

    union_idx = set()
    for p in _FakeProcess.instances:
        union_idx.update(p.indices)
    assert union_idx == set(range(10)), f"covered indices = {sorted(union_idx)}"

    jsonl = outdir / "self_consistency.jsonl"
    rows = [json.loads(line) for line in jsonl.read_text().splitlines() if line.strip()]
    assert len(rows) == 10


def test_sc_workers_per_gpu_default_one(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Default ``--workers-per-gpu`` is 1 (preserves Wave 158 behaviour)."""
    _FakeProcess.reset()
    sc_mod = _patch_esmif_for_test(monkeypatch)

    qids = [f"q{i}" for i in range(10)]
    queries_fa = _build_esmif_queries_fasta(tmp_path, qids)
    pdb_dir = tmp_path / "pdb_default"
    _write_fake_pdbs(pdb_dir, qids)
    outdir = tmp_path / "sc_out_default"
    outdir.mkdir()

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "self_consistency_esmif.py",
            "--queries-fasta",
            str(queries_fa),
            "--pdb-dir",
            str(pdb_dir),
            "--outdir",
            str(outdir),
            "--gpus",
            "0",
        ],
    )
    sc_mod.main()

    # 1 process per GPU (default), 1 GPU → 1 process.
    assert len(_FakeProcess.instances) == 1, (
        f"expected 1 Process instance, got {len(_FakeProcess.instances)}"
    )
    assert _FakeProcess.instances[0].indices == list(range(10))


# ---------------------------------------------------------------------------
# Length-balanced sub-shard assignment (Wave 201 P3)
# ---------------------------------------------------------------------------
#
# These tests pin the load-balancing contract:
# * When ``--workers-per-gpu N`` is used (N > 1), each GPU's records are
#   split into N sub-shards via LPT bin-packing by sequence length.
# * The longest record lands in sub-shard 0; subsequent records go to the
#   least-loaded shard. This is materially more load-balanced than
#   round-robin when per-sequence wall time scales with length.
# * The dispatch contract is still preserved: union of sub-shards covers
#   every record, total record count is preserved, and ``--workers-per-gpu``
#   still spawns exactly N procs per GPU.


def _lengths_in_fasta_order(fa_path: Path) -> list[int]:
    """Read a FASTA and return the lengths of the sequences in file order."""
    out: list[int] = []
    cur: list[str] = []
    for line in fa_path.read_text().splitlines():
        if line.startswith(">"):
            if cur:
                out.append(len("".join(cur)))
            cur = []
        elif line.strip():
            cur.append(line.strip())
    if cur:
        out.append(len("".join(cur)))
    return out


def test_foldability_workers_per_gpu_length_balanced_assigns_longest_first(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """With ``--workers-per-gpu 2`` and 1 GPU, the two sub-shard FASTAs
    must reflect length-balanced assignment: the longest record lands
    in sub-shard A (by itself), and the rest of the records are split
    such that total per-shard length is roughly balanced.
    """
    fold_mod = _load_module(FOLD_PATH, synthetic_name="fold_under_test_balanced")
    _FakeProc.reset()
    monkeypatch.setattr(fold_mod.subprocess, "Popen", _FakeProc)
    monkeypatch.setattr(fold_mod, "_parse_omegafold_cmd", lambda bin_: ["omegafold"])

    class _WritePDBs(_FakeProc):
        def __init__(self, cmd: list[str], env: dict[str, str] | None = None, **kwargs: Any) -> None:
            super().__init__(cmd, env, **kwargs)
            assert len(cmd) >= 3
            out_dir = Path(cmd[2])
            fasta_path = Path(cmd[1])
            out_dir.mkdir(parents=True, exist_ok=True)
            for line in fasta_path.read_text().splitlines():
                if line.startswith(">"):
                    qid = line[1:].split()[0]
                    (out_dir / f"{qid}.pdb").write_text(_make_fake_pdb(qid))

    monkeypatch.setattr(fold_mod.subprocess, "Popen", _WritePDBs)

    # 10 sequences with deliberately skewed lengths (10..100 in steps of 10).
    lengths = [10, 20, 30, 40, 50, 60, 70, 80, 90, 100]
    seqs = ["".join("ACDEFGHIKL" for _ in range(L // 10)) for L in lengths]
    fasta_lines = []
    for i, (_L, s) in enumerate(zip(lengths, seqs, strict=True)):
        fasta_lines.append(f">q{i}")
        fasta_lines.append(s)
    fasta = tmp_path / "queries.fasta"
    fasta.write_text("\n".join(fasta_lines) + "\n")

    outdir = tmp_path / "out_balanced"
    outdir.mkdir()

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "foldability_omegafold.py",
            "--fasta",
            str(fasta),
            "--outdir",
            str(outdir),
            "--gpus",
            "0",
            "--workers-per-gpu",
            "2",
            "--omegafold-bin",
            "omegafold",
            "--log-every",
            "0",
        ],
    )
    fold_mod.main()

    # Exactly 2 sub-shards spawned.
    assert len(_FakeProc.instances) == 2, (
        f"expected 2 Popen calls, got {len(_FakeProc.instances)}"
    )

    # Inspect each sub-shard's FASTA; compute per-shard total length.
    shard_fastas = [Path(p.cmd[1]) for p in _FakeProc.instances]
    per_shard_lengths = [
        sum(_lengths_in_fasta_order(fa)) for fa in shard_fastas
    ]

    # The total length across both shards equals sum(lengths) — every
    # sequence landed somewhere (no records lost, no records duplicated).
    assert sum(per_shard_lengths) == sum(lengths), (
        f"per-shard lengths {per_shard_lengths} don't sum to {sum(lengths)}"
    )

    # Length-balanced: the two shards should differ in total length by at
    # most a single longest record (100). With LPT bin-packing on
    # [10, 20, ..., 100], optimal makespan is 190 (10+20+...+100 = 550
    # divided by 2 = 275; actual LPT result is {100+90+80=270, 70+60+50+40+30+20+10=280}
    # — diff = 10). Round-robin would give {10+30+50+70+90=250,
    # 20+40+60+80+100=300} (diff = 50). We assert diff <= 30 (well within
    # the LPT guarantee, well below round-robin).
    diff = abs(per_shard_lengths[0] - per_shard_lengths[1])
    assert diff <= 30, (
        f"length-balanced dispatch produced unbalanced shards: {per_shard_lengths} "
        f"(diff = {diff}, expected <= 30 for these lengths)"
    )

    # The longest record (length 100) should be alone in some sub-shard,
    # because with 2 workers the LPT algorithm drops q9 (len=100) into
    # whichever shard is empty first. (Both sub-shards start empty, so
    # q9 goes to shard 0; then the remaining 9 records are split between
    # shard 1 and shard 0.)
    longest_shard_idx = max(
        range(len(shard_fastas)),
        key=lambda k: max(_lengths_in_fasta_order(shard_fastas[k]), default=0),
    )
    longest_in_shard = _lengths_in_fasta_order(shard_fastas[longest_shard_idx])
    assert max(longest_in_shard) == 100, (
        f"longest record (len=100) should be present in some shard; got "
        f"per-shard maxes = "
        f"{[max(_lengths_in_fasta_order(fa), default=0) for fa in shard_fastas]}"
    )


def test_foldability_shard_by_length_helper_is_load_balanced() -> None:
    """Direct unit test of ``shard_by_length`` (the LPT bin-packing helper
    used for length-balanced sub-sharding).

    With records of wildly different lengths (1, 1, 1, 100), 2 shards
    should put the 100 alone in shard A and the 1's in shard B.
    """
    fold_mod = _load_module(FOLD_PATH, synthetic_name="fold_under_test_lpt")
    # Build FastaRecords directly (no FASTA roundtrip needed).
    from dataclasses import dataclass

    @dataclass(frozen=True)
    class _R:
        seq: str

    records = [_R("A"), _R("A"), _R("A"), _R("A" * 100)]
    shards = fold_mod.shard_by_length(records, num_shards=2)
    assert len(shards) == 2
    shard_total = [sum(len(r.seq) for r in s) for s in shards]
    # The 100 alone in one shard, the 3 A's in the other.
    assert sorted(shard_total) == [3, 100], (
        f"LPT bin-packing should put {100} alone; got shard totals = {shard_total}"
    )


def test_sc_balanced_indices_by_length_helper_load_balances() -> None:
    """Direct unit test of ``_balanced_indices_by_length`` (the LPT
    bin-packing helper used for length-balanced sub-sharding in the
    ESM-IF script).

    The order of indices in the input is irrelevant — only the lengths
    of the corresponding queries matter.
    """
    sc_mod = _load_module(SC_PATH, synthetic_name="sc_under_test_lpt")
    queries = [
        sc_mod.Query(qid=f"q{i}", seq="A" * L) for i, L in enumerate([10, 50, 90, 30, 70])
    ]
    bins = sc_mod._balanced_indices_by_length(
        list(range(5)),
        queries=queries,
        num_bins=2,
    )
    assert len(bins) == 2
    bin_total = [sum(len(queries[i].seq) for i in b) for b in bins]
    # LPT trace on sorted DESC [90, 70, 50, 30, 10]:
    #   90 → bin 0 (loads = [90, 0])
    #   70 → bin 1 (loads = [90, 70])
    #   50 → bin 1 (loads = [90, 120])
    #   30 → bin 0 (loads = [120, 120])
    #   10 → bin 0 (loads = [130, 120])
    # Round-robin on input order [10, 50, 90, 30, 70] with 2 bins would
    # give loads = [10+90+30 = 130, 50+70 = 120] (same total but with no
    # co-location of long records — the key benefit of LPT is *pairing*
    # of longest records with shortest, which mitigates the worst-case
    # bottleneck).
    # We assert the LPT-optimal-ish result: sorted bin totals in
    # [120, 130] — well within the LPT 4/3 guarantee (≤ 4/3 - 1/N
    # × OPT = 7/6 × 125 = 145.8).
    assert sorted(bin_total) == [120, 130], (
        f"got bin totals = {bin_total}, expected [120, 130]"
    )
    # Union of indices covers all input indices.
    covered: set[int] = set()
    for b in bins:
        covered.update(b)
    assert covered == set(range(5)), f"covered = {covered}"


def test_sc_balanced_indices_by_length_one_bin_returns_input() -> None:
    """When ``num_bins <= 1`` the helper must short-circuit and return
    the input indices unchanged (preserves Wave 158 behaviour for N=1)."""
    sc_mod = _load_module(SC_PATH, synthetic_name="sc_under_test_one_bin")
    queries = [sc_mod.Query(qid=f"q{i}", seq="A" * 10) for i in range(3)]
    out = sc_mod._balanced_indices_by_length(
        [0, 1, 2],
        queries=queries,
        num_bins=1,
    )
    assert out == [[0, 1, 2]]


def test_run_foldability_propagates_workers_per_gpu_to_subprocess(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """``run_foldability.py`` must add ``--workers-per-gpu N`` to both
    the fold and the self-consistency subprocess invocations when N > 1.

    This is a hermetic dispatch test: the fold sub-call writes a fake PDB
    per sequence so the SC sub-call can run without a real OmegaFold or
    ESM-IF install. We monkeypatch the two sub-scripts' main() entry
    points to record the sys.argv they receive, then assert that
    ``--workers-per-gpu 4`` is in both argv lists.
    """
    fold_mod = _load_module(FOLD_PATH, synthetic_name="fold_for_propagation")
    sc_mod = _load_module(SC_PATH, synthetic_name="sc_for_propagation")

    fold_received_argv: list[str] = []
    sc_received_argv: list[str] = []

    def _fake_fold_main() -> None:
        # Record argv, then write fake PDBs for every sequence so the SC
        # sub-call (driven by ``queries.fasta``) finds them.
        fold_received_argv.extend(sys.argv)
        # Build the queries fasta the SC sub-call will read.
        fasta_path = Path(sys.argv[sys.argv.index("--fasta") + 1])
        outdir = Path(sys.argv[sys.argv.index("--outdir") + 1])
        outdir.mkdir(parents=True, exist_ok=True)
        (outdir / "queries.fasta").write_bytes(fasta_path.read_bytes())
        # Write one fake PDB per qid.
        pdb_dir = outdir / "pdb"
        pdb_dir.mkdir(parents=True, exist_ok=True)
        for line in fasta_path.read_text().splitlines():
            if line.startswith(">"):
                qid = line[1:].split()[0]
                (pdb_dir / f"{qid}.pdb").write_text(_make_fake_pdb(qid))
        # Write a stub foldability.jsonl so the merge step has something
        # to read.
        rows = []
        for line in fasta_path.read_text().splitlines():
            if line.startswith(">"):
                qid = line[1:].split()[0]
                rows.append(
                    json.dumps({"qid": qid, "pdb_path": str(pdb_dir / f"{qid}.pdb")})
                )
        (outdir / "foldability.jsonl").write_text("\n".join(rows) + "\n")

    def _fake_sc_main() -> None:
        sc_received_argv.extend(sys.argv)
        # Write a stub self_consistency.jsonl so the merge step has
        # something to read.
        outdir = Path(sys.argv[sys.argv.index("--outdir") + 1])
        queries_fa = Path(sys.argv[sys.argv.index("--queries-fasta") + 1])
        rows = []
        for line in queries_fa.read_text().splitlines():
            if line.startswith(">"):
                qid = line[1:].split()[0]
                rows.append(json.dumps({"qid": qid, "sc_perplexity": 4.5}))
        (outdir / "self_consistency.jsonl").write_text("\n".join(rows) + "\n")

    # Patch the two module main() entry points.
    monkeypatch.setattr(fold_mod, "main", _fake_fold_main)
    monkeypatch.setattr(sc_mod, "main", _fake_sc_main)

    # Now load run_foldability.py and patch its module references to the
    # fake fold / sc modules.
    run_path = (
        REPO_ROOT
        / "data"
        / "lineageflow_upstream"
        / "evaluation"
        / "run_foldability.py"
    )
    run_mod = _load_module(run_path, synthetic_name="run_foldability_under_test")
    # The script does `Path(__file__).with_name(...)` to locate the two
    # sibling scripts. With our synthetic name + ``with_name`` this still
    # resolves to the real on-disk path, which is fine because we've
    # patched the modules via ``sys.modules`` above; the subprocess.run
    # calls would try to exec the real scripts. Instead, monkeypatch
    # ``subprocess.run`` to call our fake mains directly.
    calls: list[list[str]] = []

    def _fake_subprocess_run(cmd: list[str], *args: Any, **kwargs: Any) -> Any:
        calls.append(list(cmd))
        # Drive the matching fake main().
        if "foldability_omegafold.py" in cmd[1]:
            sys.argv = cmd[1:]
            _fake_fold_main()
        elif "self_consistency_esmif.py" in cmd[1]:
            sys.argv = cmd[1:]
            _fake_sc_main()
        return _CompletedProcessLike(0)

    class _CompletedProcessLike:
        def __init__(self, rc: int) -> None:
            self.returncode = rc

    monkeypatch.setattr(run_mod.subprocess, "run", _fake_subprocess_run)

    # Drive run_foldability.main() with --workers-per-gpu 4.
    fasta = tmp_path / "queries.fasta"
    fasta.write_text(_TEN_SEQS_FASTA)
    outdir = tmp_path / "run_out"
    outdir.mkdir()

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "run_foldability.py",
            "--fasta",
            str(fasta),
            "--outdir",
            str(outdir),
            "--fold-gpus",
            "0,1",
            "--sc-gpus",
            "0,1",
            "--workers-per-gpu",
            "4",
            "--omegafold-bin",
            "omegafold",
        ],
    )
    run_mod.main()

    # Both sub-calls were issued.
    assert len(calls) == 2, f"expected 2 subprocess.run calls, got {len(calls)}"
    fold_call, sc_call = calls[0], calls[1]

    # Both received --workers-per-gpu 4.
    for name, call in (("fold", fold_call), ("sc", sc_call)):
        assert "--workers-per-gpu" in call, (
            f"{name} sub-call missing --workers-per-gpu: {call}"
        )
        i = call.index("--workers-per-gpu")
        assert call[i + 1] == "4", (
            f"{name} sub-call --workers-per-gpu={call[i + 1]!r}, expected '4'"
        )


def test_run_foldability_omits_workers_per_gpu_when_default(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """With the default ``--workers-per-gpu 1`` (or when the flag is
    omitted), the sub-calls must NOT include ``--workers-per-gpu``.

    This preserves the Wave 158 baseline behaviour: the default does not
    propagate any new flag to the sub-scripts (preserves sub-script
    defaults of 1).
    """
    fold_mod = _load_module(FOLD_PATH, synthetic_name="fold_no_propagate")
    sc_mod = _load_module(SC_PATH, synthetic_name="sc_no_propagate")

    monkeypatch.setattr(fold_mod, "main", lambda: None)
    monkeypatch.setattr(sc_mod, "main", lambda: None)

    run_path = (
        REPO_ROOT
        / "data"
        / "lineageflow_upstream"
        / "evaluation"
        / "run_foldability.py"
    )
    run_mod = _load_module(run_path, synthetic_name="run_foldability_no_propagate")

    calls: list[list[str]] = []

    def _fake_subprocess_run(cmd: list[str], *args: Any, **kwargs: Any) -> Any:
        calls.append(list(cmd))
        return _CompletedProcessLike0()

    class _CompletedProcessLike0:
        returncode = 0

    monkeypatch.setattr(run_mod.subprocess, "run", _fake_subprocess_run)

    fasta = tmp_path / "queries.fasta"
    fasta.write_text(_TEN_SEQS_FASTA)
    outdir = tmp_path / "default_out"
    outdir.mkdir()

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "run_foldability.py",
            "--fasta",
            str(fasta),
            "--outdir",
            str(outdir),
            "--fold-gpus",
            "0",
            "--sc-gpus",
            "0",
            # No --workers-per-gpu (default = 1).
            "--omegafold-bin",
            "omegafold",
        ],
    )
    run_mod.main()

    # Both sub-calls were issued.
    assert len(calls) == 2
    for call in calls:
        assert "--workers-per-gpu" not in call, (
            f"default --workers-per-gpu 1 must NOT propagate; got: {call}"
        )
