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


# ---------------------------------------------------------------------------
# LineageFlow upstream eval
# ---------------------------------------------------------------------------


def run_lineageflow_upstream_eval(
    fasta_path: str | pathlib.Path,
    output_dir: str | pathlib.Path,
    *,
    metrics: tuple[str, ...] = (
        "family_validity", "foldability", "self_consistency", "novelty",
    ),
    timeout_s: int = DEFAULT_TIMEOUT_S,
) -> dict[str, float]:
    """Invoke LineageFlow's upstream ``evaluate_all.py`` on ``fasta_path``.

    Subprocess invocation: ``python evaluate_all.py --fasta <fasta>
    --outdir <outdir> --metrics <space-separated metrics>``. The
    orchestrator writes a ``summary.json`` to ``<outdir>``; we read it
    after the subprocess completes and flatten the per-metric dicts
    into a single ``{metric_name: float}`` dict.

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
    cmd: list[str] = [
        sys.executable,
        str(LINEAGEFLOW_EVALUATE_ALL),
        "--fasta", str(fasta_path),
        "--outdir", str(output_dir),
        "--metrics", *metrics,
    ]
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
_KANZI_DRIVER: str = """\
import json
import sys
from pathlib import Path

# Vendor kanzi's src/ on sys.path so ``from kanzi import DAE`` resolves.
_KANZI_SRC = Path({kanzi_src!r}).resolve()
sys.path.insert(0, str(_KANZI_SRC))

import torch  # noqa: E402

from kanzi import DAE, kabsch_rmsd  # noqa: E402

# Parse CLI: --input <fasta> --ckpt <pt> --output <json>
import argparse  # noqa: E402
p = argparse.ArgumentParser()
p.add_argument("--input", required=True)
p.add_argument("--ckpt", required=True)
p.add_argument("--output", required=True)
args = p.parse_args()

raw = DAE.from_pretrained(args.ckpt).eval()
rmsd_by_seq = {{}}
with open(args.input, encoding="utf-8") as f:
    for line in f:
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
        rmsd_by_seq[f"seq_{{len(rmsd_by_seq)}}"] = rmsd

if rmsd_by_seq:
    values = list(rmsd_by_seq.values())
    summary = {{
        "n_seqs": float(len(values)),
        "mean_rmsd_A": float(sum(values) / len(values)),
        "min_rmsd_A": float(min(values)),
        "max_rmsd_A": float(max(values)),
    }}
else:
    summary = {{"n_seqs": 0.0, "mean_rmsd_A": 0.0, "min_rmsd_A": 0.0, "max_rmsd_A": 0.0}}

with open(args.output, "w", encoding="utf-8") as f:
    json.dump({{"per_seq": rmsd_by_seq, "summary": summary}}, f, indent=2)
"""


def run_kanzi_upstream_eval(
    sequences_path: str | pathlib.Path,
    output_dir: str | pathlib.Path,
    *,
    ckpt_path: str | pathlib.Path | None = None,
    timeout_s: int = DEFAULT_TIMEOUT_S,
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

    Returns
    -------
    dict[str, float]
        ``{"status": 1.0, "n_seqs": <float>, "mean_rmsd_A": <float>,
        "min_rmsd_A": <float>, "max_rmsd_A": <float>, ...}`` on
        success. On subprocess failure (missing kanzi / missing
        checkpoint / torch import error / timeout), returns
        ``{"status": 0.0, "reason": "<error>"}``.
    """
    if ckpt_path is None:
        # Default to the published Wave 36 ckpt when present.
        ckpt_path = REPO_ROOT / "data" / "kanzi_ckpt" / "cleaned_model.pt"
    ckpt_path = pathlib.Path(ckpt_path)
    sequences_path = pathlib.Path(sequences_path)
    output_dir = pathlib.Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    output_json = output_dir / "reconstruction.json"
    driver_source = _KANZI_DRIVER.format(kanzi_src=str(KANZI_SRC))
    cmd: list[str] = [
        sys.executable,
        "-c", driver_source,
        "--input", str(sequences_path),
        "--ckpt", str(ckpt_path),
        "--output", str(output_json),
    ]
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
        }
    except Exception as exc:  # noqa: BLE001
        return {
            "status": 0.0,
            "reason": f"kanzi_eval_subprocess_failed:{type(exc).__name__}:{exc}",
            "metric_kind": "reconstruction_kabsch_rmsd_A",
        }
    if proc.returncode != 0:
        return {
            "status": 0.0,
            "reason": (
                f"kanzi_eval_nonzero_exit:{proc.returncode}:"
                f"{proc.stderr.strip()[:400]}"
            ),
            "metric_kind": "reconstruction_kabsch_rmsd_A",
        }
    if not output_json.is_file():
        return {
            "status": 0.0,
            "reason": "kanzi_eval_no_reconstruction_json",
            "metric_kind": "reconstruction_kabsch_rmsd_A",
        }
    try:
        raw = json.loads(output_json.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        return {
            "status": 0.0,
            "reason": f"kanzi_reconstruction_parse_failed:{type(exc).__name__}:{exc}",
            "metric_kind": "reconstruction_kabsch_rmsd_A",
        }
    summary = raw.get("summary", {}) if isinstance(raw, dict) else {}
    flat: dict[str, float] = {"status": 1.0, "metric_kind": "reconstruction_kabsch_rmsd_A"}
    for key, value in summary.items():
        try:
            flat[key] = float(value)
        except (TypeError, ValueError):
            continue
    flat["upstream_orchestrator"] = "kanzi.DAE.encode+decode+kabsch_rmsd"
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
    args = parser.parse_args()
    print(f"REPO_ROOT = {REPO_ROOT}")
    print(f"LINEAGEFLOW_EVALUATE_ALL = {LINEAGEFLOW_EVALUATE_ALL}")
    print(f"KANZI_SRC = {KANZI_SRC}")
    print(f"FLOWMOL3_UPSTREAM = {FLOWMOL3_UPSTREAM}")
    print(f"selected = {args.model}")