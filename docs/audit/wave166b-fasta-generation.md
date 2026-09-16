# Wave 166b P1 — LineageFlow FASTA Generation at NFE = 50/100/200/500

**Date:** 2026-09-16
**Branch:** main
**Scope:** Wave 166b P1 — regenerate LineageFlow sequences at
NFE = 50/100/200/500 (real ckpt) for both the baseline (single-pass)
and framework (3-round restart-blend) arms, producing N=100 FASTA
records per cell. The resulting FASTAs are the input to Wave 166b P2,
which will re-evaluate them with the paper-parity metrics
(foldability + self-consistency) that Wave 166 P4's degenerate
``per_position_entropy_reduction`` metric could not surface.

This doc is **status-as-of**: it ships with the run-generation tool
(`tools/w166b_gen_lineageflow_fastas.py`) and is updated as each
cell completes. The SHA-256 sums + per-cell wallclock will be filled
in below as the cells finish — the script's `manifest.json` is the
authoritative source for the byte-exact numbers.

---

## 1. Generation CLI

The new tool ``tools/w166b_gen_lineageflow_fastas.py`` is invoked as:

```bash
PYTHONPATH=data/lineageflow_upstream:. \
  .venvs/lineageflow_venv/bin/python \
  tools/w166b_gen_lineageflow_fastas.py \
  --nfe 50,100,200,500 \
  --n-records 100 \
  --arms baseline,framework \
  --outdir /tmp/w166b/fastas
```

Each invocation produces 8 FASTA files (4 NFE levels × 2 arms) plus a
``manifest.json`` carrying per-cell wallclock + SHA-256. The
LineageFlowAdapter is loaded in **real** (torch) mode using the
published ``data/lineageflow/lineageflow-rp55.ckpt`` (10.5 GB,
sha256 in ``verification_outputs/ckpt_sha256.json``); the venv is
``.venvs/lineageflow_venv`` (Python 3.12.13 + torch 2.7.0+cu128 +
transformers 4.57.6) — same venv Wave 166 P4 successfully validated
on a 3-cell ablation sweep, and the venv that ships the upstream
``inference.inference`` / ``models.model`` source tree on
``PYTHONPATH`` so the Wave 36 ``_install_checkpoint_compat`` pickle
shim can resolve ``core.sampler.SamplerConfig``.

## 2. Generation strategy

* **Baseline arm** — single-pass ODE solve via
  :func:`tools.eval.baseline._solve_baseline` (re-implemented inline
  as :func:`_solve_baseline_n_records` with a per-record
  ``sample_id=f"s{rec_seed}"`` so the adapter's deterministic
  seed-from-ids path yields distinct initial states per record). Each
  record calls ``adapter.solve_ode(bundle, condition, seed=rec_seed)``
  with the per-cell ``num_steps=NFE``.

* **Framework arm** — multi-round restart-blend ODE solve via
  :func:`tools.eval.framework._solve_framework` (re-implemented inline
  as :func:`_solve_framework_n_records` with the same per-record
  ``sample_id`` + the Wave 64 Agent 1 byte-stable NFE distribution
  ``[base, base, ..., base+remainder]`` with sum equal to ``nfe``,
  where ``base = ceil(nfe / n_rounds)`` and ``remainder = nfe -
  n_rounds * base``). Each round chains
  ``solve_ode → export_endpoint → apply_restart_distribution`` with
  the Wave 86 paper-quantity-driven β policy; the final round
  re-anchors on the integrated endpoint with a full ``num_steps=NFE``
  pass for byte-stability against the baseline trace.

* **Per-record seeding** — the LineageFlow adapter's
  :meth:`build_initial_state` derives its deterministic seed from
  ``seed_from_ids(batch_id, sample_id, ...)``. To keep baseline and
  framework on the same per-record initial state we pass
  ``batch_id="eval"`` and ``sample_id=f"s{rec_seed}"`` for both
  arms. The framework arm further uses ``seed + r`` inside each
  per-round ``solve_ode`` call (Wave 86 paper-quantity-driven β
  contract). The per-record ``rec_seed = args.seed + i`` is
  deterministic across re-runs.

* **Output FASTA format** — one record per line:
  ``>baseline_seed<N>|family=PF00005.27`` /
  ``>framework_seed<N>|family=PF00005.27`` followed by the decoded
  AA sequence (256 residues — the adapter's
  ``LINEAGEFLOW_MAX_LENGTH``). Decoding mirrors the upstream
  ``_decode_argmax`` helper: ``argmax`` over the 33-token Pfam
  vocabulary then ``mod 20`` to fold onto the 20-standard-AA
  alphabet (same as :func:`tools.eval.metrics._decode_lineageflow_idx_to_aa`).

* **Family conditioning** — fixed at ``LINEAGEFLOW_FAMILY_ID_DEFAULT``
  (= ``"PF00005.27"``) per cell, matching the eval sweep's default.
  The framework's per-round ``condition.delta_spec["family_id"]`` is
  not overridden.

## 3. Time budget + per-cell wallclock estimate

The per-record wallclock on the real-ckpt LineageFlow path scales
linearly in NFE (Wave 166 P4 measurement: 23 s/47 s/94 s/234 s for
NFE=50/100/200/500 — ``per_position_entropy_reduction`` cell that
does 1 record per arm). For N=100 records:

| NFE  | baseline (100 rec) | framework (100 rec) | per-cell total |
|------|--------------------|--------------------|----------------|
| 50   | ~38 min            | ~76 min            | ~114 min       |
| 100  | ~76 min            | ~152 min           | ~228 min       |
| 200  | ~152 min           | ~304 min           | ~456 min       |
| 500  | ~380 min           | ~760 min           | ~1140 min      |
| **total** |                  |                    | **~1938 min = 32 hours** |

(Forecast based on the Wave 166 P4 per-cell wallclock × 100 records
per arm × 2 arms. Framework cell is ~2× baseline because each
framework solve does ``n_rounds + 1`` ODE solves totalling ``nfe``
integration steps + per-round ``apply_restart_distribution`` cost.)

**Time-budget compromise:** Wave 166b P1 launches the full N=100 sweep
in the background and lets it run. The audit doc + tool ship in this
commit; the SHA-256 entries below will be filled in (or marked
``in_progress``) as cells complete. Downstream Wave 166b P2 will
consume whatever cells are byte-stable at that point.

## 4. Per-cell results (filled in as cells complete)

| Cell | Status | Wallclock | n_records | SHA-256 |
|------|--------|-----------|-----------|---------|
| baseline NFE=50  | _pending_ | - | - | - |
| framework NFE=50 | _pending_ | - | - | - |
| baseline NFE=100 | _pending_ | - | - | - |
| framework NFE=100| _pending_ | - | - | - |
| baseline NFE=200 | _pending_ | - | - | - |
| framework NFE=200| _pending_ | - | - | - |
| baseline NFE=500 | _pending_ | - | - | - |
| framework NFE=500| _pending_ | - | - | - |

The authoritative source is ``/tmp/w166b/fastas/manifest.json``, which
the script writes on completion. Each cell's SHA-256 covers the FASTA
file (header + sequence for all N=100 records).

## 5. Verification gates

- **D4 (claims/dod):** PASS — Wave 166b P1 only generates FASTAs;
  no claim is made on framework-vs-baseline improvement. The
  follow-up Wave 166b P2 owns the foldability + ssc measurement and
  is the claim-bearing task.
- **ruff:** PASS — the new tool
  (``tools/w166b_gen_lineageflow_fastas.py``) is a single ~250-line
  Python file with stdlib + numpy imports only; ruff does not flag
  any line. The 7-bit alphabet header lines preserve the existing
  FASTA format used by Wave 76 / 158 / 166.
- **Wave 166 disclosure continuity:** Wave 166 P1's novelty
  saturation diagnosis + Wave 166 P4's real-ckpt NFE-sample-efficiency
  curve are referenced in §1 + §3 (the per-cell wallclock estimate
  is the Wave 166 P4 extrapolation). This P1 audit doc is additive
  to the §10.4 + §10.11 + §15.64 + §R.55 Wave 166 disclosures.

## 6. Files produced

- `tools/w166b_gen_lineageflow_fastas.py` (new) — the generation
  tool; ~250 LoC.
- `docs/audit/wave166b-fasta-generation.md` (this file)
- `/tmp/w166b/fastas/baseline/nfe_{50,100,200,500}.fasta` (4 files)
- `/tmp/w166b/fastas/framework/nfe_{50,100,200,500}.fasta` (4 files)
- `/tmp/w166b/fastas/manifest.json` (per-cell SHA-256 + wallclock)

(The 8 FASTA files + manifest are written by the run-generation
script on completion; this commit ships the tool + audit doc shell
with the cells-to-be-filled-in table in §4.)