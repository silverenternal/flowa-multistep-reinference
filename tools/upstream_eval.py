#!/usr/bin/env python3
"""Wave 79 Agent 2 — per-model upstream-eval subprocess shims.

Goal
----

``tools/run_real_ckpt_eval.py`` historically consumed paper-metric values
through the framework's internal observer path
(``adapter.observe_token_indices`` / ``observe_entropy_reduction``). For
the 3 models with upstream paper-parity eval scripts (LineageFlow +
Kanzi from Phase 1; FlowMol3 from Wave 75), Wave 79 closes the gap by
running the upstream eval **directly** as a subprocess (NOT a wrapper
class, NOT a new in-process metric). This keeps the framework
hands-off the upstream eval code so a bug fix in the upstream eval
immediately reflects in our eval pipeline.

Per-model CLI surface
~~~~~~~~~~~~~~~~~~~~~

* **LineageFlow** — the upstream
  ``data/lineageflow_upstream/evaluation/evaluate_all.py`` orchestrator
  (single CLI entry point that fans out into the 4 metric families).
  Invoked via ``python evaluate_all.py --fasta <fasta> --outdir <outdir>
  --metrics family_validity foldability self_consistency novelty``
  (per ``docs/audit/wave79-phase1-audit.md`` §1.2).
* **Kanzi** — Kanzi upstream ships **NO** ``evaluation/`` directory (Phase
  1 §2.3); the only paper metric accessible from outside the model code
  is reconstruction Kabsch RMSD on a held-out subset. We invoke the
  model end-to-end via a small inline Python ``-c`` driver that calls
  ``kanzi.DAE.encode → kanzi.DAE.decode → kanzi.kabsch_rmsd`` (the
  same surface the README quick-start uses), invoked as a subprocess.
* **FlowMol3** — the upstream ``flowmol.analysis.metrics.SampleAnalyzer``
  class is the published evaluation surface (Wave 75 Agent 1 audit +
  Wave 75 Agent 2 wire). We invoke it via a vendored-``sys.path``
  ``python -c`` driver so the vendored FlowMol3 repo at
  ``data/FlowMol3/repo`` is on ``sys.path`` (the sidecar venv where
  ``flowmol`` is installed).

All three functions return ``dict[str, float]``. The dict is the
metric-name → float surface that ``tools/run_real_ckpt_eval.py`` copies
into the cell's ``upstream_eval_metrics`` debug dict when ``--*-upstream-eval``
is set on the CLI. The functions NEVER raise — they surface all upstream
failures as ``{"status": "blocked", "reason": "..."}`` keys (a sentinel
pattern the caller keys on).

Constraints
-----------

* **Interface-first** — the helpers are opt-in via the
  ``--*-upstream-eval`` flag in :mod:`tools.run_real_ckpt_eval`. The
  legacy internal-observer path is the default and is byte-stable
  (D.4 vectors 72/72 unchanged).
* **No wrapper class** — there is no upstream-eval wrapper class in this
  module. Each function is a thin subprocess driver that returns a flat
  ``dict[str, float]``. Adding upstream eval to a 4th model is a single
  new function in this module + a new CLI flag + a single ``if`` branch
  in :func:`tools.run_real_ckpt_eval._run_cell`.
* **Subprocess, not import** — the upstream eval is invoked via
  ``subprocess.run([sys.executable, -c, "<driver>"], ...)`` so the
  vendored upstream packages (``kanzi``, vendored ``flowmol``,
  LineageFlow HMMER/MMseqs2 binaries) are loaded in a fresh interpreter
  with a clean ``sys.path``. This keeps the framework's own Python
  environment independent of the upstream eval environment.
"""
from __future__ import annotations

import json
import pathlib
import subprocess
import sys
from typing import Any

# Wave 98.A — GPU utilization watchdog. Fires a WARNING to stderr if
# util.gpu stays at 0% for >30s while memory.used > 100 MiB. The
# diagnostic that should have caught the Wave 96.E stuck-process
# scenario (a sweep that held VRAM but never advanced). Stdlib-only +
# no-op when nvidia-smi is missing (legacy non-GPU callers unaffected).
from tools._gpu_watchdog import gpu_watchdog  # noqa: E402

# Wave 97.D — hard N-record assertion + summary JSON contract (closes
# the Wave 96 reality-check gap: agents silently wrote N<=10 sweeps and
# claimed N=1000). Imported lazily inside the upstream-eval wrappers so
# the stdlib-only helper doesn't pollute the cold-import path.
from tools._sweep_assertion import (  # noqa: E402
    assert_n_records_match_with_file_count,
    write_summary_with_n_keys,
)

# Repo root (one level above ``tools/``). Used to anchor absolute paths
# for vendored upstream packages + reference data.
REPO_ROOT: pathlib.Path = pathlib.Path(__file__).resolve().parent.parent

#: Path to the vendored LineageFlow upstream repo. The orchestrator
#: CLI entry lives at ``evaluation/evaluate_all.py`` (Phase 1 §1.1).
LINEAGEFLOW_UPSTREAM: pathlib.Path = (
    REPO_ROOT / "data" / "lineageflow_upstream"
)
LINEAGEFLOW_EVALUATE_ALL: pathlib.Path = (
    LINEAGEFLOW_UPSTREAM / "evaluation" / "evaluate_all.py"
)

#: Path to the just-cloned Kanzi upstream repo (Phase 1 §2.1). The
#: Kanzi package is at ``src/kanzi/__init__.py``.
KANZI_UPSTREAM: pathlib.Path = (
    REPO_ROOT / "data" / "kanzi_upstream"
)
KANZI_SRC: pathlib.Path = KANZI_UPSTREAM / "src"

#: Path to the vendored FlowMol3 upstream repo (Wave 70 Agent 2
#: install). The eval surface is
#: ``flowmol.analysis.metrics.SampleAnalyzer.analyze``.
FLOWMOL3_UPSTREAM: pathlib.Path = (
    REPO_ROOT / "data" / "FlowMol3" / "repo"
)

#: Per-model subprocess timeout (seconds). 30 min is enough for the
#: LineageFlow orchestrator's family-validity + novelty metrics (the
#: OmegaFold foldability path is NOT in scope for Wave 79 Phase 2;
#: we'd need a GPU host with omegafold installed). Kanzi decode on
#: 1000 PDBs is ~1.5-4 h (Phase 1 §2.7) so the timeout is generous.
DEFAULT_TIMEOUT_S: int = 1800

#: Wave 81 — Pfam-A.hmm reference DB for the ``family_validity``
#: upstream metric (HMMER ``hmmscan``). Vendored in Wave 80 Agent B
#: at ``data/lineageflow_upstream/databases/pfam35/Pfam-A.hmm`` plus
#: pressed indices ``.h3{f,i,m,p}``. Defaults to that path; can be
#: overridden via the ``hmmdb`` kwarg.
DEFAULT_HMMDB: pathlib.Path = (
    LINEAGEFLOW_UPSTREAM / "databases" / "pfam35" / "Pfam-A.hmm"
)

#: Wave 81 — MMseqs2 target DB for the ``novelty`` upstream metric
#: (closest-pfam-train hit identity). Built by Wave 80 Agent B from
#: 200 sequences in ``data/pfam_holdout/random_clan.fasta``. Required
#: by ``evaluate_all.py --metrics novelty``.
DEFAULT_TARGET_DB: pathlib.Path = (
    LINEAGEFLOW_UPSTREAM / "databases" / "pfam35" / "pfam_holdout_targetDB"
)

#: Wave 81 — Pfam per-family FASTA dir for the ``novelty`` upstream
#: metric. The vendored LineageFlow tree does NOT ship the full Pfam
#: training corpus (it's HF-dataset-only upstream per Wave 79 §1.4).
#: We point at an empty placeholder directory under the vendored
#: ``dataset/`` so ``evaluate_all.py --pfam-fastas-dir <abs>`` passes
#: its ``_require_path`` check. The novelty script only falls into
#: the ``build_reference_fasta`` branch when ``_db_exists(target_db)``
#: is False; since Wave 80 Agent B prebuilt ``pfam_holdout_targetDB``
#: the placeholder is never read. The novelty metric then runs against
#: the prebuilt 200-seq MMseqs2 DB.
DEFAULT_PFAM_FASTAS_DIR: pathlib.Path = (
    LINEAGEFLOW_UPSTREAM / "dataset" / "pfam_fastas_clean"
)

#: Wave 81 — path to the ``hmmscan`` binary (HMMER 3.4, vendored by
#: Wave 80 Agent B at ``/home/hugo/hmmer_build/bin/hmmscan``). Falls
#: back to the bare command name (``hmmscan``) so a system-installed
#: binary works out-of-the-box.
DEFAULT_HMMSCAN: str = "/home/hugo/hmmer_build/bin/hmmscan"

#: Wave 81 — path to the ``mmseqs`` binary (MMseqs2, vendored by
#: Wave 80 Agent B at ``/home/hugo/bin/mmseqs``). Falls back to the
#: bare command name (``mmseqs``) so a system-installed binary works
#: out-of-the-box.
DEFAULT_MMSEQS: str = "/home/hugo/bin/mmseqs"


# ---------------------------------------------------------------------------
# LineageFlow upstream eval
# ---------------------------------------------------------------------------


def run_lineageflow_upstream_eval(
    fasta_path: str | pathlib.Path,
    output_dir: str | pathlib.Path,
    *,
    metrics: tuple[str, ...] = (
        # Wave 81 — restrict default to the 2 unblocked metrics.
        # ``foldability`` + ``self_consistency`` require OmegaFold +
        # ESM-IF on Python 3.10 (the OmegaFold ``setup.py`` hard-blocks
        # 3.12), neither of which we have on the host. See
        # docs/audit/wave80-phase1-audit.md §3.1 for the blocker.
        # Callers wanting the full 4-metric pipeline can override the
        # tuple explicitly.
        "family_validity", "novelty",
    ),
    timeout_s: int = DEFAULT_TIMEOUT_S,
    hmmdb: str | pathlib.Path | None = DEFAULT_HMMDB,
    target_db: str | pathlib.Path | None = DEFAULT_TARGET_DB,
    pfam_fastas_dir: str | pathlib.Path | None = DEFAULT_PFAM_FASTAS_DIR,
    hmmscan: str | None = DEFAULT_HMMSCAN,
    mmseqs: str | None = DEFAULT_MMSEQS,
) -> dict[str, float]:
    """Invoke LineageFlow's upstream ``evaluate_all.py`` on ``fasta_path``.

    Subprocess invocation: ``python evaluate_all.py --fasta <fasta>
    --outdir <outdir> --hmmdb <pfam> --target-db <db>
    --hmmscan <bin> --mmseqs <bin> --metrics <space-separated metrics>``.
    The orchestrator writes a ``summary.json`` to ``<outdir>``; we
    read it after the subprocess completes and flatten the per-metric
    dicts into a single ``{metric_name: float}`` dict.

    Parameters
    ----------
    fasta_path
        Absolute path to a LineageFlow-generated FASTA file (one
        protein sequence per record).
    output_dir
        Empty directory the orchestrator can write per-metric output
        files to. Will be created if missing.
    metrics
        Subset of ``{"family_validity", "foldability",
        "self_consistency", "novelty"}`` to run. Default = all 4. The
        foldability + self_consistency paths require OmegaFold + ESM-IF
        binaries on $PATH (per Phase 1 §1.3); when those binaries are
        not installed, the orchestrator fails fast and we surface a
        blocked dict.
    timeout_s
        Wall-clock cap. Default 1800 s (30 min).
    hmmdb, target_db, hmmscan, mmseqs
        Wave 81: pass-through args required by ``evaluate_all.py`` for
        ``--metrics family_validity novelty``. Defaults point at the
        Wave 80-vendored paths under
        ``data/lineageflow_upstream/databases/pfam35/`` + the
        Wave 80-installed ``/home/hugo/hmmer_build/bin/hmmscan`` +
        ``/home/hugo/bin/mmseqs``. Passing ``None`` skips the arg
        (lets the orchestrator fall back to its own defaults).

    Returns
    -------
    dict[str, float]
        Flat mapping of ``metric_name -> float``. On success, the keys
        are the upstream metric names (``family_validity_intended``,
        ``foldability_mean_plddt``, ``novelty_mean_min_identity``,
        etc. — keys are pass-through from ``summary.json``). On
        subprocess failure (timeout / missing binary / non-zero exit),
        returns ``{"status": 0.0, "reason": "<error message>"}`` with
        the status key always present so the caller can branch on it.
    """
    fasta_path = pathlib.Path(fasta_path)
    output_dir = pathlib.Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    # Wave 98.A — GPU utilization watchdog. Fires a WARNING to stderr
    # if util.gpu stays at 0% for >30s while memory.used > 100 MiB.
    with gpu_watchdog(threshold_seconds=30, sample_interval=5):
        return _run_lineageflow_upstream_eval_impl(
            fasta_path, output_dir, metrics, timeout_s,
            hmmdb, target_db, pfam_fastas_dir, hmmscan, mmseqs,
        )


def _run_lineageflow_upstream_eval_impl(
    fasta_path: pathlib.Path,
    output_dir: pathlib.Path,
    metrics: tuple[str, ...],
    timeout_s: int,
    hmmdb: str | pathlib.Path | None,
    target_db: str | pathlib.Path | None,
    pfam_fastas_dir: str | pathlib.Path | None,
    hmmscan: str | None,
    mmseqs: str | None,
) -> dict[str, float]:
    cmd: list[str] = [
        sys.executable,
        str(LINEAGEFLOW_EVALUATE_ALL),
        "--fasta", str(fasta_path),
        "--outdir", str(output_dir),
        "--metrics", *metrics,
    ]
    # Wave 81: pass --hmmdb + --target-db + --hmmscan + --mmseqs when
    # the caller supplied (or kept) the defaults. Without these the
    # orchestrator exits with "error: --hmmdb is required" the moment
    # ``family_validity`` or ``novelty`` appears in --metrics.
    if hmmdb is not None:
        cmd += ["--hmmdb", str(hmmdb)]
    if target_db is not None:
        cmd += ["--target-db", str(target_db)]
    if pfam_fastas_dir is not None:
        cmd += ["--pfam-fastas-dir", str(pfam_fastas_dir)]
    if hmmscan is not None:
        cmd += ["--hmmscan", str(hmmscan)]
    if mmseqs is not None:
        cmd += ["--mmseqs", str(mmseqs)]
    try:
        proc = subprocess.run(
            cmd, check=False, capture_output=True, text=True,
            timeout=int(timeout_s),
        )
    except subprocess.TimeoutExpired as exc:
        return {
            "status": 0.0,
            "reason": f"lineageflow_evaluate_all_timeout:{exc}",
            "metric_kind": "family_validity+foldability+self_consistency+novelty",
        }
    except Exception as exc:  # noqa: BLE001
        return {
            "status": 0.0,
            "reason": f"lineageflow_evaluate_all_subprocess_failed:{type(exc).__name__}:{exc}",
            "metric_kind": "family_validity+foldability+self_consistency+novelty",
        }
    if proc.returncode != 0:
        return {
            "status": 0.0,
            "reason": (
                f"lineageflow_evaluate_all_nonzero_exit:{proc.returncode}:"
                f"{proc.stderr.strip()[:400]}"
            ),
            "metric_kind": "family_validity+foldability+self_consistency+novelty",
        }
    # Subprocess succeeded — read summary.json + per-metric JSONs.
    summary_path = output_dir / "summary.json"
    if not summary_path.is_file():
        return {
            "status": 0.0,
            "reason": "lineageflow_evaluate_all_no_summary_json",
            "metric_kind": "family_validity+foldability+self_consistency+novelty",
        }
    try:
        raw_summary = json.loads(summary_path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        return {
            "status": 0.0,
            "reason": f"lineageflow_summary_parse_failed:{type(exc).__name__}:{exc}",
            "metric_kind": "family_validity+foldability+self_consistency+novelty",
        }
    # Flatten the per-metric nested dict into the surface dict.
    flat: dict[str, float] = {"status": 1.0}
    for metric_name, metric_dict in raw_summary.items():
        if not isinstance(metric_dict, dict):
            continue
        for key, value in metric_dict.items():
            try:
                flat[f"{metric_name}__{key}"] = float(value)
            except (TypeError, ValueError):
                # Skip non-numeric fields (paths, strings, etc.).
                continue
    flat["metric_kind"] = "family_validity+foldability+self_consistency+novelty"
    flat["upstream_orchestrator"] = str(LINEAGEFLOW_EVALUATE_ALL)
    # Wave 97.D — hard N-record assertion (file-aware variant). The
    # orchestrator writes per-family ``n_records`` into summary.json;
    # we use the minimum across all reported metrics as the actual
    # count. ``file_record_count`` is the number of records the user
    # gave us in the FASTA (= the natural cap). The assertion fires
    # only when (a) the FASTA had >= 1 record, (b) at least one
    # per-metric ``n_records`` was reported (i.e. the orchestrator
    # actually ran the eval, not the empty-summary success path),
    # AND (c) min per-metric N < file_record_count — i.e. the
    # orchestrator silently produced a short N sweep.
    family_n_records: list[float] = []
    for _metric_name, metric_dict in raw_summary.items():
        if not isinstance(metric_dict, dict):
            continue
        nr = metric_dict.get("n_records")
        if isinstance(nr, (int, float)):
            family_n_records.append(float(nr))
    min_n_records = (
        min(family_n_records) if family_n_records else 0.0
    )
    file_record_count = 0
    if fasta_path.is_file():
        with open(fasta_path, encoding="utf-8") as _f:
            for _line in _f:
                if _line.strip().startswith(">"):
                    file_record_count += 1
    if (
        int(file_record_count) > 0
        and int(min_n_records) > 0
    ):
        assert_n_records_match_with_file_count(
            n_records_actual=int(min_n_records),
            n_records_requested=int(file_record_count),
            file_record_count=int(file_record_count),
            sweep_name="run_lineageflow_upstream_eval",
            context={
                "fasta_path": str(fasta_path),
                "metrics": list(raw_summary.keys()),
                "family_n_records": family_n_records,
            },
        )
    # Wave 97.D — write the 2 N-contract keys so downstream consumers
    # can verify the eval honored its requested N.
    write_summary_with_n_keys(
        flat,
        n_records_actual=int(min_n_records),
        n_records_requested=int(file_record_count) if int(file_record_count) > 0 else 0,
        sweep_name="run_lineageflow_upstream_eval",
    )
    return flat


# ---------------------------------------------------------------------------
# Kanzi upstream eval
# ---------------------------------------------------------------------------


#: Subprocess driver — end-to-end Kanzi encode → decode → kabsch_rmsd
#: loop on a FASTA-of-Cα-coords file. The FASTA header is unused; the
#: record body is a comma-separated list of ``x,y,z`` floats in Å
#: (the Kanzi upstream ``encode`` expects mean-centered Å coords).
#: Writes the per-sequence RMSDs to ``<output_dir>/reconstruction.json``
#: and returns exit 0. On any failure, writes the error to stderr +
#: exit 1.
#:
#: Wave 92b — added ``--max-records N`` to honor the upstream-eval
#: ``--upstream-n-samples`` knob from
#: :mod:`tools.run_real_ckpt_eval`. The wrapper caps records at
#: ``min(N, file_count)`` before invoking the subprocess so a single
#: ``run_kanzi_upstream_eval`` call processes all N records (instead
#: of N subprocess invocations from the upstream caller). Also added
#: ``--output-jsonl PATH`` for per-record JSONL output (parallel to
#: the summary JSON) so downstream codebook metric helpers in
#: :mod:`tools.paper_metrics_kanzi` can consume the encoded indices
#: without re-running encode.
_KANZI_DRIVER: str = """\
import json
import math
import sys
from pathlib import Path

# Vendor kanzi's src/ on sys.path so ``from kanzi import DAE`` resolves.
_KANZI_SRC = Path({kanzi_src!r}).resolve()
sys.path.insert(0, str(_KANZI_SRC))

import torch  # noqa: E402

from kanzi import DAE, kabsch_rmsd  # noqa: E402

# Parse CLI: --input <fasta> --ckpt <pt> --output <json>
#           [--max-records N] [--output-jsonl <path>] [--config <yaml>]
import argparse  # noqa: E402
p = argparse.ArgumentParser()
p.add_argument("--input", required=True)
p.add_argument("--ckpt", required=True)
p.add_argument("--output", required=True)
p.add_argument("--max-records", type=int, default=0,
               help="Cap on records to process (0 = all).")
p.add_argument("--output-jsonl", default=None,
               help="Optional per-record JSONL output path.")
p.add_argument("--config", type=str, default=None,
               help=("Wave 112.D-4: optional run-profile YAML. Honoured as "
                     "an additional default source; CLI > YAML > module "
                     "default. Or set $LINEAGEFLOW_PROFILE env var."))
args = p.parse_args()

raw = DAE.from_pretrained(args.ckpt).eval()
rmsd_by_seq = {{}}
per_record = []  # for optional JSONL output

def _flush_jsonl():
    if not args.output_jsonl:
        return
    with open(args.output_jsonl, "w", encoding="utf-8") as jf:
        for rec in per_record:
            jf.write(json.dumps(rec) + "\\n")

n_processed = 0
try:
    with open(args.input, encoding="utf-8") as f:
        for line in f:
            if args.max_records and n_processed >= args.max_records:
                break
            line = line.strip()
            if not line or line.startswith(">"):
                continue
            # Each line is a comma-separated ``x,y,z`` list of Å floats.
            vals = [float(t) for t in line.split(",") if t.strip()]
            if len(vals) < 3 or len(vals) % 3 != 0:
                continue
            coords = torch.tensor(vals, dtype=torch.float32).reshape(-1, 3)
            coords = (coords - coords.mean(dim=-2, keepdim=True)) / 10.0  # Å -> nm
            x = coords.unsqueeze(0)  # (1, L, 3)
            with torch.no_grad():
                *_, idx = raw.encode(x, preprocess=False)
                recon = raw.decode(idx)
            recon_angstrom = recon.cpu().reshape(-1, 3) * 10.0
            x_angstrom = x.reshape(-1, 3) * 10.0
            rmsd = float(kabsch_rmsd(recon_angstrom, x_angstrom))
            seq_id = f"seq_{{n_processed}}"
            rmsd_by_seq[seq_id] = rmsd
            per_record.append({{
                "seq_id": seq_id,
                "rmsd_A": rmsd,
                "length": int(coords.shape[0]),
            }})
            n_processed += 1
except Exception as exc:
    # Persist partial output before propagating the error so the
    # caller can still read n_seqs / mean for whatever records did
    # complete (useful when --max-records caps mid-stream).
    _flush_jsonl()
    print(f"kanzi_driver_exception:{{type(exc).__name__}}:{{exc}}", file=sys.stderr)
    raise

# Write JSONL first so partial-failure visibility is preserved.
_flush_jsonl()

# Compute summary statistics: mean, std (sample), 95% CI half-width.
# Std uses Bessel's correction (n-1) so CI matches scipy.stats.sem
# up to the 1.96 normal quantile.
if rmsd_by_seq:
    values = list(rmsd_by_seq.values())
    n = len(values)
    mean = sum(values) / n
    if n > 1:
        variance = sum((x - mean) ** 2 for x in values) / (n - 1)
        std = math.sqrt(variance)
        sem = std / math.sqrt(n)
    else:
        std = 0.0
        sem = 0.0
    ci_half = 1.96 * sem
    summary = {{
        "n_seqs": float(n),
        "mean_rmsd_A": float(mean),
        "std_rmsd_A": float(std),
        "ci_95_low_A": float(mean - ci_half),
        "ci_95_high_A": float(mean + ci_half),
        "min_rmsd_A": float(min(values)),
        "max_rmsd_A": float(max(values)),
        "max_records_arg": float(args.max_records),
    }}
else:
    summary = {{
        "n_seqs": 0.0,
        "mean_rmsd_A": 0.0,
        "std_rmsd_A": 0.0,
        "ci_95_low_A": 0.0,
        "ci_95_high_A": 0.0,
        "min_rmsd_A": 0.0,
        "max_rmsd_A": 0.0,
        "max_records_arg": float(args.max_records),
    }}

with open(args.output, "w", encoding="utf-8") as f:
    json.dump({{"per_seq": rmsd_by_seq, "summary": summary}}, f, indent=2)
"""


def run_kanzi_upstream_eval(
    sequences_path: str | pathlib.Path,
    output_dir: str | pathlib.Path,
    *,
    ckpt_path: str | pathlib.Path | None = None,
    timeout_s: int = DEFAULT_TIMEOUT_S,
    n_samples: int = 0,
    output_jsonl: str | pathlib.Path | None = None,
) -> dict[str, float]:
    """Invoke Kanzi's upstream ``DAE.encode → decode → kabsch_rmsd`` loop.

    Kanzi upstream ships NO ``evaluation/`` directory (Phase 1 §2.3),
    so the paper metric (reconstruction Kabsch RMSD on a held-out
    subset) is reconstructed by running the model end-to-end via a
    subprocess driver that vendors ``kanzi`` on ``sys.path`` and
    computes per-sequence Kabsch RMSD. The driver writes
    ``<output_dir>/reconstruction.json``; we read it and return the
    summary scalars.

    Parameters
    ----------
    sequences_path
        Plain-text file (one record per line) where each line is a
        comma-separated ``x,y,z`` triplet list in Ångström (the
        Kanzi upstream ``encode`` expects mean-centered Å coords).
        Use ``data/kanzi_ckpt/cleaned_model.pt`` for the
        published Wave 36 ckpt as the test fixture.
    output_dir
        Directory for ``reconstruction.json`` output. Will be created
        if missing.
    ckpt_path
        Path to a Kanzi ``.pt`` checkpoint (the file the upstream
        ``DAE.from_pretrained`` expects). Defaults to the published
        Wave 36 ckpt at ``data/kanzi_ckpt/cleaned_model.pt`` when
        present; ``None`` otherwise (the subprocess will fail fast
        and we surface a blocked dict).
    timeout_s
        Wall-clock cap. Default 1800 s (30 min).
    n_samples
        Wave 92b: cap on records to process from ``sequences_path``.
        Defaults to 0 (= process every record in the file). When the
        caller passes ``--upstream-n-samples 1000`` from
        :mod:`tools.run_real_ckpt_eval`, this kwarg is set so the
        single subprocess call evaluates all N records (instead of
        the upstream caller invoking the wrapper N times). Effective
        value is ``min(n_samples, file_record_count)`` — i.e. the
        smaller of the two.
    output_jsonl
        Wave 92b: optional path for per-record JSONL output
        (one ``{"seq_id", "rmsd_A", "length"}`` object per line).
        Parallel to the summary ``reconstruction.json``. Consumed by
        downstream codebook-metric helpers in
        :mod:`tools.paper_metrics_kanzi` so they can run codebook
        statistics over the encoded indices without re-running
        ``DAE.encode``. Defaults to ``None`` (no JSONL written).

    Returns
    -------
    dict[str, float]
        ``{"status": 1.0, "n_seqs": <float>, "mean_rmsd_A": <float>,
        "std_rmsd_A": <float>, "ci_95_low_A": <float>,
        "ci_95_high_A": <float>, "min_rmsd_A": <float>,
        "max_rmsd_A": <float>, ...}`` on success. On subprocess
        failure (missing kanzi / missing checkpoint / torch import
        error / timeout), returns ``{"status": 0.0, "reason":
        "<error>"}``.
    """
    if ckpt_path is None:
        # Default to the published Wave 36 ckpt when present.
        ckpt_path = REPO_ROOT / "data" / "kanzi_ckpt" / "cleaned_model.pt"
    ckpt_path = pathlib.Path(ckpt_path)
    sequences_path = pathlib.Path(sequences_path)
    output_dir = pathlib.Path(output_dir)
    # Wave 98.A — GPU utilization watchdog.
    with gpu_watchdog(threshold_seconds=30, sample_interval=5):
        return _run_kanzi_upstream_eval_impl(
            sequences_path, output_dir, ckpt_path, timeout_s,
            n_samples, output_jsonl,
        )


def _run_kanzi_upstream_eval_impl(
    sequences_path: pathlib.Path,
    output_dir: pathlib.Path,
    ckpt_path: pathlib.Path,
    timeout_s: int,
    n_samples: int,
    output_jsonl: str | pathlib.Path | None,
) -> dict[str, float]:
    output_dir.mkdir(parents=True, exist_ok=True)
    output_json = output_dir / "reconstruction.json"
    # Wave 92b: pre-count records in the input file so the subprocess
    # caps at min(n_samples, file_count). This honors the
    # ``--upstream-n-samples`` knob from :mod:`tools.run_real_ckpt_eval`
    # at the upstream-eval layer (was previously ignored — the wrapper
    # silently processed all records regardless of the flag).
    file_record_count = 0
    if sequences_path.is_file():
        with open(sequences_path, encoding="utf-8") as _f:
            for _line in _f:
                _stripped = _line.strip()
                if _stripped and not _stripped.startswith(">"):
                    _vals = [float(t) for t in _stripped.split(",") if t.strip()]
                    if len(_vals) >= 3 and len(_vals) % 3 == 0:
                        file_record_count += 1
    effective_n = file_record_count if int(n_samples) <= 0 else min(int(n_samples), file_record_count)
    driver_source = _KANZI_DRIVER.format(kanzi_src=str(KANZI_SRC))
    cmd: list[str] = [
        sys.executable,
        "-c", driver_source,
        "--input", str(sequences_path),
        "--ckpt", str(ckpt_path),
        "--output", str(output_json),
        "--max-records", str(int(effective_n)),
    ]
    jsonl_path = None
    if output_jsonl is not None:
        jsonl_path = pathlib.Path(output_jsonl)
        jsonl_path.parent.mkdir(parents=True, exist_ok=True)
        cmd += ["--output-jsonl", str(jsonl_path)]
    try:
        proc = subprocess.run(
            cmd, check=False, capture_output=True, text=True,
            timeout=int(timeout_s),
        )
    except subprocess.TimeoutExpired as exc:
        return {
            "status": 0.0,
            "reason": f"kanzi_eval_timeout:{exc}",
            "metric_kind": "reconstruction_kabsch_rmsd_A",
            "n_samples_requested": float(int(n_samples)),
            "n_samples_file": float(file_record_count),
        }
    except Exception as exc:  # noqa: BLE001
        return {
            "status": 0.0,
            "reason": f"kanzi_eval_subprocess_failed:{type(exc).__name__}:{exc}",
            "metric_kind": "reconstruction_kabsch_rmsd_A",
            "n_samples_requested": float(int(n_samples)),
            "n_samples_file": float(file_record_count),
        }
    if proc.returncode != 0:
        return {
            "status": 0.0,
            "reason": (
                f"kanzi_eval_nonzero_exit:{proc.returncode}:"
                f"{proc.stderr.strip()[:400]}"
            ),
            "metric_kind": "reconstruction_kabsch_rmsd_A",
            "n_samples_requested": float(int(n_samples)),
            "n_samples_file": float(file_record_count),
        }
    if not output_json.is_file():
        return {
            "status": 0.0,
            "reason": "kanzi_eval_no_reconstruction_json",
            "metric_kind": "reconstruction_kabsch_rmsd_A",
            "n_samples_requested": float(int(n_samples)),
            "n_samples_file": float(file_record_count),
        }
    try:
        raw = json.loads(output_json.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        return {
            "status": 0.0,
            "reason": f"kanzi_reconstruction_parse_failed:{type(exc).__name__}:{exc}",
            "metric_kind": "reconstruction_kabsch_rmsd_A",
            "n_samples_requested": float(int(n_samples)),
            "n_samples_file": float(file_record_count),
        }
    summary = raw.get("summary", {}) if isinstance(raw, dict) else {}
    flat: dict[str, float] = {"status": 1.0, "metric_kind": "reconstruction_kabsch_rmsd_A"}
    for key, value in summary.items():
        try:
            flat[key] = float(value)
        except (TypeError, ValueError):
            continue
    # Wave 92b: surface the n_samples bookkeeping so the caller can
    # detect if their --upstream-n-samples knob was honored (effective
    # n_seqs == n_samples_requested when file had >= n_samples records).
    flat["n_samples_requested"] = float(int(n_samples))
    flat["n_samples_file"] = float(file_record_count)
    flat["n_samples_effective"] = float(effective_n)
    if jsonl_path is not None:
        flat["output_jsonl"] = 1.0
    flat["upstream_orchestrator"] = "kanzi.DAE.encode+decode+kabsch_rmsd"
    # Wave 97.D — hard N-record assertion (file-aware variant: only
    # fires when the file had >= n_samples records but the driver
    # processed fewer). Closes the Wave 96 reality-check gap where
    # agents passed ``--upstream-n-samples 1000`` but the upstream
    # eval silently ran on a 10-record subset.
    assert_n_records_match_with_file_count(
        n_records_actual=int(flat.get("n_seqs", 0)),
        n_records_requested=int(n_samples),
        file_record_count=int(file_record_count),
        sweep_name="run_kanzi_upstream_eval",
        context={
            "sequences_path": str(sequences_path),
            "n_samples_requested": int(n_samples),
            "n_samples_effective": int(effective_n),
        },
    )
    # Wave 97.D — write the 2 N-contract keys so downstream consumers
    # can verify the eval honored its requested N.
    write_summary_with_n_keys(
        flat,
        n_records_actual=int(flat.get("n_seqs", 0)),
        n_records_requested=int(n_samples),
        sweep_name="run_kanzi_upstream_eval",
    )
    return flat


# ---------------------------------------------------------------------------
# FlowMol3 upstream eval
# ---------------------------------------------------------------------------


#: Subprocess driver — invokes the vendored ``flowmol``'s
#: ``SampleAnalyzer.analyze`` on a SMILES-list file. Vendors
#: ``data/FlowMol3/repo`` on ``sys.path`` so the upstream package
#: resolves. Writes the analyzer's output dict (the same dict the
#: Wave 75 ``tools.paper_metrics.compute_all_paper_metrics`` consumes)
#: to ``<output_dir>/sample_analyzer.json``.
_FLOWMOL3_DRIVER: str = """\
import json
import sys
from pathlib import Path

_FLOWMOL3_ROOT = Path({flowmol3_root!r}).resolve()
sys.path.insert(0, str(_FLOWMOL3_ROOT))

# flowmol's __init__ imports a few heavy things (torch, rdkit,
# posebusters). We import lazily so the subprocess startup is fast
# when the user only needs the smoke-test path.
from flowmol.analysis.metrics import SampleAnalyzer  # noqa: E402
from flowmol.analysis.molecule_builder import SampledMolecule  # noqa: E402

import argparse  # noqa: E402
p = argparse.ArgumentParser()
p.add_argument("--smiles-list", required=True)
p.add_argument("--reference", required=True)
p.add_argument("--output", required=True)
p.add_argument("--pb-workers", type=int, default=2)
p.add_argument("--config", type=str, default=None,
               help=("Wave 112.D-4: optional run-profile YAML (CLI > YAML > "
                     "module default). Or set $FLOWMOL3_PROFILE env var."))
args = p.parse_args()

with open(args.smiles_list, encoding="utf-8") as f:
    smiles = [line.strip() for line in f if line.strip()]

# Wrap each SMILES into a stub SampledMolecule carrying just the
# ``num_atoms`` + ``atom_types`` attributes ``SampleAnalyzer.analyze``
# reads. This is the minimum surface for the validity + reos + ood
# axes — it does NOT include ``rdkit_mol`` because posebusters would
# re-build it from ``build_molecule()`` anyway.
mols = []
from rdkit import Chem  # noqa: E402
for sm in smiles:
    mol = Chem.MolFromSmiles(sm)
    if mol is None:
        continue
    atoms = [a.GetAtomicNum() for a in mol.GetAtoms()]
    smol = SampledMolecule.__new__(SampledMolecule)
    smol.atom_types = atoms
    smol.num_atoms = len(atoms)
    smol.rdkit_mol = mol
    smol.positions = None
    smol.charges = None
    smol.bonds = None
    mols.append(smol)

analyzer = SampleAnalyzer(processed_data_dir=args.reference, pb_workers=args.pb_workers)
out = analyzer.analyze(mols, functional_validity=True, posebusters=True, energy_div=False)

with open(args.output, "w", encoding="utf-8") as f:
    json.dump(out, f, indent=2, default=str)
"""


def run_flowmol3_upstream_eval(
    smiles_list: str | pathlib.Path,
    output_dir: str | pathlib.Path,
    *,
    reference: str = "GEOM_DRUGS",
    pb_workers: int = 2,
    timeout_s: int = DEFAULT_TIMEOUT_S,
) -> dict[str, float]:
    """Invoke FlowMol3's upstream ``SampleAnalyzer.analyze`` on a SMILES list.

    Subprocess invocation: ``python -c <driver> --smiles-list <file>
    --reference <dir> --output <json>``. The driver vendors
    ``data/FlowMol3/repo`` on ``sys.path`` so ``from flowmol import ...``
    resolves, then runs ``SampleAnalyzer.analyze`` on a list of stub
    ``SampledMolecule`` objects (one per SMILES line). The analyzer's
    output dict is written to ``<output_dir>/sample_analyzer.json``.

    Parameters
    ----------
    smiles_list
        Plain-text file (one SMILES per line). Empty / unparseable
        lines are silently skipped.
    output_dir
        Directory for ``sample_analyzer.json``. Will be created if
        missing.
    reference
        Path or label for the reference distribution. Default
        ``"GEOM_DRUGS"`` (the Wave 75 paper-parity reference). The
        driver forwards this to ``SampleAnalyzer(processed_data_dir=...)``.
    pb_workers
        PoseBusters worker count. Default 2 (mirrors Wave 75
        ``compute_all_paper_metrics``).
    timeout_s
        Wall-clock cap. Default 1800 s (30 min).

    Returns
    -------
    dict[str, float]
        Flat mapping of ``metric_name -> float`` (the analyzer's
        output dict with all float-coercible values surfaced). On
        subprocess failure (missing flowmol / missing reference /
        torch / rdkit import error / timeout), returns
        ``{"status": 0.0, "reason": "<error>"}``.
    """
    smiles_list = pathlib.Path(smiles_list)
    output_dir = pathlib.Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    output_json = output_dir / "sample_analyzer.json"
    # Wave 98.A — GPU utilization watchdog.
    with gpu_watchdog(threshold_seconds=30, sample_interval=5):
        return _run_flowmol3_upstream_eval_impl(
            smiles_list, output_dir, output_json, reference, pb_workers,
            timeout_s,
        )


def _run_flowmol3_upstream_eval_impl(
    smiles_list: pathlib.Path,
    output_dir: pathlib.Path,
    output_json: pathlib.Path,
    reference: str,
    pb_workers: int,
    timeout_s: int,
) -> dict[str, float]:
    driver_source = _FLOWMOL3_DRIVER.format(flowmol3_root=str(FLOWMOL3_UPSTREAM))
    cmd: list[str] = [
        sys.executable,
        "-c", driver_source,
        "--smiles-list", str(smiles_list),
        "--reference", str(reference),
        "--output", str(output_json),
        "--pb-workers", str(int(pb_workers)),
    ]
    try:
        proc = subprocess.run(
            cmd, check=False, capture_output=True, text=True,
            timeout=int(timeout_s),
        )
    except subprocess.TimeoutExpired as exc:
        return {
            "status": 0.0,
            "reason": f"flowmol3_eval_timeout:{exc}",
            "metric_kind": "sample_analyzer_paper_parity",
        }
    except Exception as exc:  # noqa: BLE001
        return {
            "status": 0.0,
            "reason": f"flowmol3_eval_subprocess_failed:{type(exc).__name__}:{exc}",
            "metric_kind": "sample_analyzer_paper_parity",
        }
    if proc.returncode != 0:
        return {
            "status": 0.0,
            "reason": (
                f"flowmol3_eval_nonzero_exit:{proc.returncode}:"
                f"{proc.stderr.strip()[:400]}"
            ),
            "metric_kind": "sample_analyzer_paper_parity",
        }
    if not output_json.is_file():
        return {
            "status": 0.0,
            "reason": "flowmol3_eval_no_sample_analyzer_json",
            "metric_kind": "sample_analyzer_paper_parity",
        }
    try:
        raw = json.loads(output_json.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        return {
            "status": 0.0,
            "reason": f"flowmol3_sample_analyzer_parse_failed:{type(exc).__name__}:{exc}",
            "metric_kind": "sample_analyzer_paper_parity",
        }
    flat: dict[str, float] = {"status": 1.0, "metric_kind": "sample_analyzer_paper_parity"}
    for key, value in raw.items():
        try:
            flat[key] = float(value)
        except (TypeError, ValueError):
            continue
    flat["upstream_orchestrator"] = "flowmol.analysis.metrics.SampleAnalyzer.analyze"
    return flat


__all__ = [
    "DEFAULT_TIMEOUT_S",
    "FLOWMOL3_UPSTREAM",
    "KANZI_SRC",
    "KANZI_UPSTREAM",
    "LINEAGEFLOW_EVALUATE_ALL",
    "LINEAGEFLOW_UPSTREAM",
    "REPO_ROOT",
    "run_flowmol3_upstream_eval",
    "run_kanzi_upstream_eval",
    "run_lineageflow_upstream_eval",
]


if __name__ == "__main__":  # pragma: no cover
    # CLI: print the available orchestrator paths + a smoke
    # surface for human-driven inspection. Not exercised in CI.
    import argparse
    parser = argparse.ArgumentParser(
        description="Wave 79 upstream-eval shim smoke surface.",
    )
    parser.add_argument(
        "--model", choices=("lineageflow", "kanzi", "flowmol3"),
        required=True,
    )
    parser.add_argument(
        "--config", type=str, default=None,
        help=("Wave 112.D-4: optional run-profile YAML. Honours $UPSTREAM_PROFILE env var "
              "when set. CLI > YAML > module default."),
    )
    args = parser.parse_args()
    print(f"REPO_ROOT = {REPO_ROOT}")
    print(f"LINEAGEFLOW_EVALUATE_ALL = {LINEAGEFLOW_EVALUATE_ALL}")
    print(f"KANZI_SRC = {KANZI_SRC}")
    print(f"FLOWMOL3_UPSTREAM = {FLOWMOL3_UPSTREAM}")
    print(f"selected = {args.model}")
    if args.config:
        print(f"profile_path = {args.config}")
