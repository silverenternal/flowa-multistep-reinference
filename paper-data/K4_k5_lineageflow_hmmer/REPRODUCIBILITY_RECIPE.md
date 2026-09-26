# K4 LineageFlow HMMER length-bias_long — Reproducibility Recipe

**Cell:** K4 LineageFlow HMMER length-bias_long (200-300 AA POWERED metric-collection path; K5 framework-vs-baseline delta on the same metric is SUPPORTS-WITH-CAVEAT)
**Headline (K4):** `hmmscan_total_hits` POWERED at metric-collection level — 12-22 hits / 100 records non-zero across all 3 seeds (coverage 12-22% at 200-300 AA range); the metric is no longer at the floor that made the pre-Wave-280 K4 STATISTICAL-underpowered.
**Headline (K5 paired delta on K4 substrate):** mean Δ = +1.33 hits (+8.9% framework uplift), Cohen's d_z = +1.15, raw p_value = 0.184 (NOT-significant at α=0.05 due to d_f=2 with n=3 paired seeds), Bonferroni p_bonf = 0.734 (NOT-significant at α=0.0125 with m_tests=4 metrics). The framework-vs-baseline paired delta is visible in the expected direction but does not reach Bonferroni significance under the n=3 paired-seeds design.
**Date:** 2026-09-27 (Wave 363 P1 — reproduction recipe authored)
**Verdict status (Wave 268 strict-clean):** **K4 = POWERED** (metric-collection level) / **K5 paired delta = NOT_SIGNIFICANT** at strict Bonferroni α=0.0125 due to the n=3 paired-seeds design (d_f=2 is structurally underpowered for paired t-tests). Per `docs/CLAIMS.md` CLM-060 line 3031 (Wave 280 P addendum, preserved verbatim across Wave 306 demotion + Wave 326 cross-doc-snapshot).

---

## (a) Headline Metric — K4 POWERED + K5 Paired Delta SUPP-WITH-CAVEAT

The K4 cell is the LineageFlow HMMER length-bias_long path (`--upstream-eval-len-bias long` → 200-300 AA range). The metric is `hmmscan_total_hits` (total Pfam-A hits across the FASTA, counted from `hmmscan --tblout` per-query hit lines). The K5 cell on the same metric is the framework-vs-baseline paired delta (uniform-AA prior path, `--lineageflow-prior-mix 1.0`).

Per `docs/audit/wave280-p-k4k5-sweep-result.md` §3.2 + `verification_outputs/wave280-p-k4k5/summary_n100.json`, the canonical evidence is the 3-seed × N=100 paired sweep (`sweep_name="wf280_k4k5_3seed_n100"`, `seeds_run=3`, `n_records_per_seed=100`, `flags={"upstream_eval_len_bias": "long", "lineageflow_prior_mix": 1.0}`, `elapsed_total_s=124.01`).

### Per-seed scalars

| seed | n_records | baseline_hits | framework_hits | delta | coverage_any_hit |
|---:|---:|---:|---:|---:|---:|
| 42  | 100 | 20 | 22 | +2 | 0.22 |
| 43  | 100 | 12 | 14 | +2 | 0.14 |
| 44  | 100 | 13 | 13 |  0 | 0.13 |

All 3 seeds evaluated without error (`status=1.0` per JSON `per_seed[*].baseline.status` / `per_seed[*].framework.status`).

### Aggregate statistics (Wave 280 P §3.2 table)

| metric | mean | std_paired | t | d_f | p_value (raw) | d_z | p_bonf (m=4, α=0.05/4=0.0125) |
|---|---:|---:|---:|---:|---:|---:|---:|
| hmmscan_total_hits       | 16.33 / 15.00 = +1.33 | 1.15 | 2.0 | 2 | 0.184 | 1.15 | **0.734** |
| coverage_any_hit         | 0.163 / 0.150 = +0.013 | 0.012 | 2.0 | 2 | 0.184 | 1.15 | **0.734** |
| hmmscan_unique_queries   | (same as hits)        | 1.15 | 2.0 | 2 | 0.184 | 1.15 | **0.734** |
| intended_hit_rate_evalue | (same as coverage)    | 0.012 | 2.0 | 2 | 0.184 | 1.15 | **0.734** |

`k4k5_status: "PASS"` (from summary_n100.json line 141).

### Honest framing (Wave 268 strict-clean)

- **K4 (length-bias_long path): POWERED.** The hit-count metric is non-degenerate across all 3 seeds (12-22 hits per N=100 records = 12-22% coverage). The pre-Wave-280 K4 cell was STATISTICAL-underpowered (hit-counts at the floor); Wave 276 P K4 power-up (200-300 AA range → 2-3 Pfam domains per record) is confirmed end-to-end.
- **K5 (framework-vs-baseline delta on K4 substrate): NOT_SIGNIFICANT** at strict Bonferroni α=0.0125. The framework arm produces +1.33 more Pfam hits per N=100 (+8.9%) than the baseline arm, with Cohen's d_z = +1.15 (medium-to-large effect). Raw paired p_value = 0.184 (not significant at α=0.05 due to d_f=2 with n=3 paired seeds); Bonferroni p_bonf = 0.734 (not significant at α=0.0125). The direction is in the expected framework-wins direction but the 3-seed paired-seeds design lacks the statistical power to reach Bonferroni significance. The ties-at-zero HEADLINE outcome is broken — framework and baseline now produce distinguishable distributions — but the strict Bonferroni criterion is not met.
- **Status label (Wave 268 strict-clean):** K4 = POWERED (the metric is no longer at the floor); K5 paired delta = NOT_SIGNIFICANT at strict Bonferroni α=0.0125 (sample-size limitation honestly disclosed; promotion to STRONG/STRONG-with-caveat requires n≥7 paired seeds per Wave 280 P §8 option 1).

---

## (b) Evidence Chain + SHA-256 Anchors

The K4+K5 evidence chain lives entirely at `verification_outputs/wave280-p-k4k5/` (mirrored via symlinks at `paper-data/K4_k5_lineageflow_hmmer/`). The SHA-256 ledger at `verification_outputs/wave280-p-k4k5/SHA256SUMS` was verified at recipe authorship (2026-09-27). All 44 listed files pass `sha256sum --check`; the lone `SHA256SUMS: FAILED` line is the canonical self-referential hash (the file's own hash line does not match the file content when the line is included — this is expected behaviour, not a corruption).

### Canonical summary (Wave 280 P 3-seed × N=100 paired sweep)

| File | SHA-256 |
|---|---|
| `verification_outputs/wave280-p-k4k5/summary_n100.json` | `f382c79a209c29fe5115d83fc646d0321102a8f11176eb6aeac959410ddc71a3` |
| `verification_outputs/wave280-p-k4k5/SHA256SUMS` | `906420fb95c24cd316ba904102b2e21c69f82f6ab358d0be9ff009ca6a0c4f4a` |
| `verification_outputs/wave280-p-k4k5/seed42/fasta/manifest.json` | `12f5c662dd482fba8b6315f396db5c75e7c949e3f8ad4aa6c6ab67b535c31690` |
| `verification_outputs/wave280-p-k4k5/seed42/fasta/baseline_n100.fasta` | `dcac1e6894b0243c4394682f4dfca326f7b421508af1c4bf780209dbf45ca7ec` |
| `verification_outputs/wave280-p-k4k5/seed42/fasta/framework_n100.fasta` | `01c0fce0b48f158966474875951db3de5d422ad9b1872f9779d9a7d76ec751c5` |
| `verification_outputs/wave280-p-k4k5/seed42/hmmscan_n100/baseline/hmmscan.tbl` | `6b1260dffd3891f69f4de2c0cc579a96795aa0500115af3b01b605e377066ec7` |
| `verification_outputs/wave280-p-k4k5/seed42/hmmscan_n100/framework/hmmscan.tbl` | `82edb4d1f14dde8904b4cc697cdbdc4b2e399a9625597378cd27e11f74d9e90e` |
| `verification_outputs/wave280-p-k4k5/seed43/fasta/manifest.json` | `e105c7c2c241d2e1562339f88384cc332fe87d5ba38a0f8e9d4b2547d1793f5d` |
| `verification_outputs/wave280-p-k4k5/seed43/fasta/baseline_n100.fasta` | `6498cb3f918cd2340d3a237c275e6251e1c5af268d831c2fad8aa6c27934764b` |
| `verification_outputs/wave280-p-k4k5/seed43/fasta/framework_n100.fasta` | `b6a185a69e5ab6e82ba67fb979ab6fe738485274c0409f0d249598a5cd258ecd` |
| `verification_outputs/wave280-p-k4k5/seed43/hmmscan_n100/baseline/hmmscan.tbl` | `c16871fdf133614047947e577a717aeaa6f9570a016288895a1096722716ab9b` |
| `verification_outputs/wave280-p-k4k5/seed43/hmmscan_n100/framework/hmmscan.tbl` | `f8ac656ced178487ff0ca895727f3be32582810b1e0a3938e09abed649d0a995` |
| `verification_outputs/wave280-p-k4k5/seed44/fasta/manifest.json` | `e38ca35078eefc1dab1839dde5cb2b78483f5a523c993be68b7e6602b8476a3f` |
| `verification_outputs/wave280-p-k4k5/seed44/fasta/baseline_n100.fasta` | `0df8b4dbf4af058ea32eee9f5651073ab13a7959cf906620d6682dba7e4316fa` |
| `verification_outputs/wave280-p-k4k5/seed44/fasta/framework_n100.fasta` | `e9bd9f21b06a41e5d6eb3c867d78bb73452c68ef6bcf6ca77553de474bcb72b4` |
| `verification_outputs/wave280-p-k4k5/seed44/hmmscan_n100/baseline/hmmscan.tbl` | `0a507917209662e6747669fad4dd30921f717b9dde0a51345ac27dafd254cacd` |
| `verification_outputs/wave280-p-k4k5/seed44/hmmscan_n100/framework/hmmscan.tbl` | `136a30a0eb39247a8dbff502143f5c8882278241278e1a3db47f52a4f6183b8f` |

### Bash verification (reviewer runs from repo root)

```bash
# Full 44-file SHA-256 verification (canonical ledger)
cd verification_outputs/wave280-p-k4k5 && sha256sum --check SHA256SUMS
# expected: 43 OK (all listed files pass), 1 FAILED (SHA256SUMS self-line)

# Targeted summary verification
sha256sum -- verification_outputs/wave280-p-k4k5/summary_n100.json
# expected: f382c79a209c29fe5115d83fc646d0321102a8f11176eb6aeac959410ddc71a3  verification_outputs/wave280-p-k4k5/summary_n100.json
```

The 6 manifest.json + n100 FASTA + hmmscan.tbl files per seed (3 seeds × 6 = 18 files) carry the per-record pairings that the aggregate summary aggregates over. The full SHA-256 ledger at `verification_outputs/wave280-p-k4k5/SHA256SUMS` covers all FASTAs (N=500 canonical + N=100/N=50 subsamples), all `hmmscan.tbl` outputs (baseline + framework per seed), and the `manifest.json` capture of the sweep flags.

### Provenance audit doc

`docs/audit/wave280-p-k4k5-sweep-result.md` (the Wave 280 P per-sweep audit doc, 8 sections: goal + method + results + promotion to STRONG + invariants verified + edit discipline + artifacts + next step) is the canonical provenance record. The aggregate `docs/audit/wave280-final.md` (Wave 280 P final consolidation across 7 sweeps) carries the §0 TL;DR + §1 per-claim before/after status + §2 aggregate promotion count for the K4+K5 cell.

---

## (c) Reproducibility Path — CPU-only counterfactual from frozen N=100 evidence

The K4+K5 reproducibility path is **CPU-only** (no GPU required): the headline metric is computed from the existing `hmmscan --tblout` outputs at `verification_outputs/wave280-p-k4k5/seed{42,43,44}/hmmscan_n100/{baseline,framework}/hmmscan.tbl`. The Python snippet below reproduces all four aggregate statistics from the per-seed summary_n100.json.

### Reproducibility commands

```bash
# 1. Verify SHA-256 chain (canonical ledger)
cd verification_outputs/wave280-p-k4k5 && sha256sum --check SHA256SUMS
cd /home/hugo/codes/flowa-multistep-reinference

# 2. Re-derive aggregate statistics from summary_n100.json (CPU-only, <1 sec)
python3 -c "
import json, math
d = json.load(open('verification_outputs/wave280-p-k4k5/summary_n100.json'))
print('sweep_name:', d['sweep_name'])
print('seeds_run:', d['seeds_run'])
print('n_records_per_seed:', d['n_records_per_seed'])
print('flags:', d['flags'])
print('k4k5_status:', d['k4k5_status'])
print()
print('hit_count: baseline_mean =', d['hit_count']['baseline_mean'])
print('hit_count: framework_mean =', d['hit_count']['framework_mean'])
print()
s = d['stats']['hmmscan_total_hits']
print(f\"hmmscan_total_hits: mean_delta={s['mean_delta']:.4f}, std_paired={s['std_paired']:.4f}\")
print(f\"  t={s['t']:.4f}, d_f={s['d_f']}, raw p_value={s['p_value']:.6f}, d_z={s['d_z']:.4f}\")
print(f\"  Bonferroni p_bonf (m={d['m_tests']}, alpha=0.05/{d['m_tests']}=0.0125): {d['bonferroni_p_values'][0]:.6f}\")
"
# expected: mean_delta=1.3333, std_paired=1.1547, d_z=1.1547, p_value=0.1835, p_bonf=0.7340
```

### Optional CPU re-derivation from raw hmmscan.tbl files

For full reproducibility from raw artefacts (not just the aggregate summary), the per-seed `hmmscan.tbl` files can be re-scored with the canonical `family_validity_hmmer.py` scoring logic from `data/lineageflow_upstream/evaluation/family_validity_hmmer.py` (VENDORED — UNTOUCHED per "clone下来的原sota项目里的打分脚本依旧不能动，严格复用" directive, byte-stable since Wave 244-262 vendored file revert):

```bash
# Per-seed raw hmmscan.tbl count (per-query hit lines, excluding header/comment)
for seed in 42 43 44; do
  for arm in baseline framework; do
    tbl="verification_outputs/wave280-p-k4k5/seed${seed}/hmmscan_n100/${arm}/hmmscan.tbl"
    grep -c '^[^#]' "$tbl"  # counts data lines only (not header/comment lines)
  done
done
# expected: seed42 baseline=20, seed42 framework=22, seed43 baseline=12, seed43 framework=14, seed44 baseline=13, seed44 framework=13
```

### Wall-clock + environment

- **Wall-clock for the full 3-seed × N=100 sweep:** 124.01 seconds (canonical, from `summary_n100.json:elapsed_total_s`). Per-(seed, arm) `elapsed_s ≈ 20 sec` on an uncontended host (hmmscan `--cpu 4 --noali --tblout --acc` against `data/lineageflow_upstream/databases/pfam35/Pfam-A.hmm`).
- **Environment:** CPU-only — no GPU required. No specific Python venv is required for the verification snippets (the snippets only read JSON / count tblout lines). The original sweep driver (NOT committed, per "claude相关的确实不要commit" directive) lived in `/tmp/wf280_k4k5_n100_driver.py` and was invoked directly (no venv activation needed).
- **Pfam database:** `data/lineageflow_upstream/databases/pfam35/Pfam-A.hmm` (vendored, byte-stable). The `--noali` flag matches `family_validity_hmmer.py`'s wrapper invocation; the absence of `--E` matches `family_validity_hmmer.py` (which does NOT pass `-E` to hmmscan and instead post-filters hits internally by `--evalue`).

### Edit discipline preserved

Per `docs/audit/wave280-p-k4k5-sweep-result.md` §6: 0 vendored files touched (Pfam DB, `data/lineageflow_upstream/evaluation/*.py` unchanged); 0 project-owned files touched (`tools/gen_lineageflow_n1000_fastas.py` + `tools/upstream_eval.py` unchanged at the Wave 276 P state); sweep driver lived in `/tmp/` and was NOT committed per the user's "claude相关的确实不要commit" directive. The `vendoredTouched: false` invariant holds.

---

## (d) Disclosure — Honest Status Label per Wave 268 Strict-Clean

Per Wave 268 strict-clean rule + Wave 268 hard guardrail #4 ("Never promote UNDERPOWERED/DEFERRED/REGRESSES/NOT_SIGNIFICANT to SUPPORTED by wording alone") + the Wave 363 P1 "never fabricate numbers — only anchor to verified artifacts" directive:

### K4 cell (this recipe's headline)

- **Status label: POWERED** (metric-collection level).
- The K4 metric (`hmmscan_total_hits` at 200-300 AA range) is non-zero across all 3 seeds (range 12-22 hits per N=100 records = 12-22% coverage). The pre-Wave-280 K4 cell was STATISTICAL-underpowered (hit-counts at the floor); Wave 276 P K4 power-up is confirmed end-to-end. **No claim of framework-vs-baseline statistical significance is made for K4** (that is the K5 cell, addressed below).
- Verbatim from `docs/CLAIMS.md` CLM-060 line 3031 (Wave 280 P addendum, preserved across Wave 306 demotion + Wave 326 cross-doc-snapshot): "K4 POWERED (hit-counts 12-22/100 records non-zero across all 3 seeds)".

### K5 cell (paired delta on the K4 substrate — disclosed for completeness)

- **Status label: NOT_SIGNIFICANT** at strict Bonferroni α=0.0125 (m_tests=4).
- Raw paired p_value = 0.184 (NOT-significant at α=0.05 due to d_f=2 with n=3 paired seeds). Bonferroni p_bonf = 0.734 (NOT-significant at α=0.0125). The direction is in the expected framework-wins direction (mean Δ = +1.33 hits / +8.9%, Cohen's d_z = +1.15), but the 3-seed paired-seeds design lacks the statistical power to reach Bonferroni significance.
- Verbatim from `docs/CLAIMS.md` CLM-060 line 3031: "K5 SUPPORTS-WITH-CAVEAT (mean delta +1.33 hits / +8.9%, d_z=1.15, raw p=0.184 not significant at α=0.05 due to d_f=2; Bonferroni p=0.734 not significant at α=0.0125 due to n=3 paired-seeds design) ... K4 closes, K5 remains SUPPORTS-WITH-CAVEAT pending n=7 or larger seeds for Bonferroni".

### Honest uncertainty disclosure (preserved verbatim)

- The K5 paired delta is **SUPPORTS-WITH-CAVEAT, not SUPPORTED**. Per Wave 280 P §8 next-step analysis, the K5 cell requires one of: (1) increase seeds to n=7+ to push d_f above 5 (the cleanest option, matches user's "3seed就够了" for qualitative claim but n=7+ is required for Bonferroni); (2) adopt a per-record paired design (each seed contributes N paired observations, aggregate via mixed-effects) to lift effective d_f without more seeds; (3) drop the Bonferroni correction and use raw p<0.05 across 4 metrics (current raw p=0.184 still misses the raw threshold; requires Wave 22 rubric revision).
- The N=500 FASTA generation phase completed for all 3 seeds (canonical N=500 FASTAs at `/tmp/wf280-lineageflow/seed{42,43,44}/fasta/{baseline,framework}.fasta`) but the upstream-eval phase was downsampled to N=100 per seed due to CPU contention under system load average 89+ from concurrent sweeps. The K4+K5 implementation surface (the new `--upstream-eval-len-bias long` + `--lineageflow-prior-mix 1.0` flags on `tools/gen_lineageflow_n1000_fastas.py`) is byte-stable between N=500 and N=100 because it operates at the FASTA-generator level, not the per-record level.
- **Cross-cell distinction (preserved):** the Wave 280 P / Wave 326 K4 (LineageFlow HMMER 200-300 AA length-bias_long cell, currently POWERED per Wave 280 P §3.2) is a DIFFERENT cell from the camera-ready scope item #6 K4 (Kanzi decision-metric saturation cell, currently `UNDERPOWERED / TIES_AT_ZERO` per Wave 357 P4 camera-ready scope). This recipe addresses the LineageFlow HMMER K4 cell, NOT the Kanzi K4.

### Linked surfaces

- `verification_outputs/wave280-p-k4k5/summary_n100.json` — canonical aggregate JSON (SHA-256 verified above).
- `verification_outputs/wave280-p-k4k5/SHA256SUMS` — canonical 44-file ledger.
- `paper-data/K4_k5_lineageflow_hmmer/K4_k5_SOURCE.md` — provenance summary (mirrors this recipe's headline).
- `docs/audit/wave280-p-k4k5-sweep-result.md` — Wave 280 P per-sweep audit doc (provenance + per-seed scalars + aggregate stats + promotion to POWERED + invariants verified).
- `docs/audit/wave280-final.md` — Wave 280 P final consolidation (7-sweep TL;DR + per-claim before/after status).
- `docs/CLAIMS.md` CLM-060 line 3031 — Wave 280 P status addendum (K4 POWERED + K5 SUPP-WITH-CAVEAT, preserved verbatim across Wave 306 demotion + Wave 326 cross-doc-snapshot).
- `docs/CONSOLIDATED_RESULTS.md` §15.x (K4+K5 cross-doc-snapshot pointer, Wave 326 verbatim).

---

_Last updated: 2026-09-27 (Wave 363 P1 — K4 LineageFlow HMMER length-bias_long reproducibility recipe authored; SHA-256 chain + bash/Python recipes + honest disclosure for K4 POWERED + K5 NOT_SIGNIFICANT at strict Bonferroni)._
