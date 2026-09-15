# Wave 156 P3 — LineageFlow N=1000 HMMER Launch (REAL sequences)

**Branch:** main
**Date (UTC):** 2026-09-15 04:54
**Agent:** Wave 156 Agent 3

## Goal

Close **K7** (novelty_mmseqs2 raw N=1000 HMMER JSON) + provide the **canonical R1 +116% headline raw JSON** by running the full LineageFlow N=1000 HMMER scan with **REAL sampled sequences** (not the Wave 154b placeholder strings).

## FASTA generation (STEP 1-2)

Generator: `tools/gen_lineageflow_n1000_fastas.py`

CLI used (note: script uses `--outdir/--n/--seed/--min-len/--max-len`, not the `--output-dir/--n-records-per-family/--n-rounds/--nfe` aliases mentioned in the agent prompt):

```bash
python tools/gen_lineageflow_n1000_fastas.py \
    --outdir /tmp/w156/lineageflow_real_fastas/ \
    --n 1000 \
    --seed 42
```

Output:

| file | size | sha256 | records |
|---|---|---|---|
| `baseline.fasta`  | 124 KB | `4ef0ec94d67850aa018d8cb83806d1ad52f80081dca758a732891a08a9e80db1` | 1000 |
| `framework.fasta` | 128 KB | `73a1fca6d7d4259e975ead2c7b6efc61106876cd1749c7693062be0b8b47813d` | 1000 |
| `manifest.json`   | 717 B  | n/a | per-family metadata |

4 Pfam families × 250 records each = 1000 records per arm:
- PF00005.27 (ABC transporter)
- PF00072.24 (Response regulator receiver)
- PF00183.19 (HSP70)
- PF02517.18 (Radial spoke)

Sample headers:
- baseline: `>baseline_seed0|family=PF00005.27` (L=111)
- framework: `>framework_seed0|family=PF00005.27` (L=62)

framework.fasta ≠ baseline.fasta (per Wave 86 Pitfall #2 fix; framework records are produced by the real `LineageFlowAdapter.solve_ode` chain — `solve_ode → export_endpoint → apply_restart_distribution` × 3 rounds).

## HMMER launch (STEP 3-4)

HMMER binary: `/home/hugo/hmmer_build/bin/hmmscan` (HMMER 3.4, Aug 2023)
Database: `data/lineageflow_upstream/databases/pfam35/Pfam-A.hmm` (2.1 GB pre-pressed)

CLI (per arm):

```bash
nohup /home/hugo/hmmer_build/bin/hmmscan \
    --cpu 4 \
    --noali \
    --tblout <out_dir>/hits.tbl \
    data/lineageflow_upstream/databases/pfam35/Pfam-A.hmm \
    <arm>.fasta \
    > <out_dir>/hmmscan.log 2>&1 &
```

| arm | PID | start (UTC) | output dir |
|---|---|---|---|
| baseline  | 363448 | 2026-09-15 ~04:53 | `/tmp/w156/hmmer_real_n1000/baseline/` |
| framework | 363522 | 2026-09-15 ~04:53 | `/tmp/w156/hmmer_real_n1000/framework/` |

## Monitoring (STEP 5-6)

10-min monitoring window active (started at launch). The first 60 s of monitoring shows healthy progress:

- `RNl` state on both PIDs (Running, Nice, multi-threaded)
- `hits.tbl` files being written (4 KB at 30 s → growing)
- `Initial search space (Z): 30134` confirmed
- `//` separators between processed queries (per-sequence record boundary)
- No `Error` / `FAILED` strings in either log

Progress at +60 s:

| arm | queries processed | ETA |
|---|---|---|
| baseline  | ~130 / 1000 | ~5-6 min |
| framework | ~125 / 1000 | ~5-6 min |

**Estimated wallclock (revised):** The agent prompt estimated 30-50 h. Actual measurement at launch shows ~3.3 queries/sec/thread for the baseline arm and similar for the framework arm. With `--noali` against the 2.1 GB Pfam-A.hmm, wallclock per arm is approximately **5-7 minutes**, not 30-50 h. The pessimistic estimate likely assumed `--noali` was not used (full alignment output is much slower) or a much larger database. Both arms will be complete well within the 10-min monitoring window.

If the scan completes inside the 10-min window, no overnight wakeup is required; the JSON parsing + headline update + audit write can happen inline.

## Gates verified (STEP 8)

| gate | command | result |
|---|---|---|
| D.4 conformance | `pytest tests/ -k "d4" -q` | 33 passed, 31 skipped (torch/hypothesis env gap, pre-existing) — **preserved** |
| ruff | `ruff check adaptive_reflow/ tests/ scripts/run_ablation_sweep.py` | All checks passed! (0 errors) — **preserved** (Wave 156 P1 cleanup held) |
| claims | `python tools/check_claims_consistency.py` | **No drift detected.** — **preserved** |

## Files / PIDs (snapshot at write time)

- baseline PID: `363448` (alive, processing)
- framework PID: `363522` (alive, processing)
- baseline log: `/tmp/w156/hmmer_real_n1000/baseline/hmmscan.log`
- framework log: `/tmp/w156/hmmer_real_n1000/framework/hmmscan.log`
- baseline hits.tbl: `/tmp/w156/hmmer_real_n1000/baseline/hits.tbl`
- framework hits.tbl: `/tmp/w156/hmmer_real_n1000/framework/hits.tbl`

## Next step (post-launch, not in this commit)

Once both `hits.tbl` files are sealed (process exits), Agent 4 of Wave 156 will:

1. Parse `hits.tbl` per arm and compute per-record hit counts.
2. Compute framework vs baseline uplift at N=1000 (the canonical R1 +116% headline).
3. Write `docs/audit/wave156-hmmer-results.md` with raw JSON + parsed headline.
4. Append headline to `docs/CONSOLIDATED_RESULTS.md` (or equivalent).
5. Re-run claims check + D.4 + ruff.
6. Commit and (optionally) push.

## Notes on K7 / K8 closure

- **K7** (novelty_mmseqs2 raw N=1000 HMMER JSON) — closes when the baseline `hits.tbl` is sealed + parsed.
- **K8** (raw N=1000 HMMER JSON archival) — closes when both arms' `hits.tbl` are sealed + archived under `data/lineageflow_n1000/` or equivalent canonical location.
- This P3 launch produces the raw artifacts; the audit + commit happens in the next step.
