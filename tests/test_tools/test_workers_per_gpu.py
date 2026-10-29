"""Tests for the vendored LineageFlow foldability / self-consistency scripts.

**History.** Wave 201 P2 patched ``--workers-per-gpu`` into the two vendored
scripts and this file pinned that contract. The vendor tree was later restored
to byte-identical upstream (submission-checklist row 13), which removed the
flag, and the ten tests asserting it were xfailed — under a copy-pasted reason
that named an unrelated documentation gate. They were deleted on 2026-10-29;
the live per-GPU heuristic is pinned in ``test_gpu_workers_detect.py``, and the
triage is recorded in ``docs/audit/xfail-triage.md``.

What remains here are the three tests that never depended on the patch: the
vendored scripts' own default and their length-balanced sharding helpers.
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
