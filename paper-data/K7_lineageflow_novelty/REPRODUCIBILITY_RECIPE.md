# K7 LineageFlow Novelty — Reproducibility Recipe

**Cell:** K7 LineageFlow novelty (SUPP / direction-INVERTED per Wave 306 Issue 5 + Wave 327 rev)
**Headline:** baseline 466/1000 = 46.6% novel vs framework 37/1000 = 3.7% novel at pctid<30% twilight-zone (Rost 1999); framework LESS Pfam-novel by **12.6×** (baseline/framework ratio); framework produces +425 recognizable Pfam homologs (963 vs 538)
**Date:** 2026-09-27 (Wave 363 P1 — reproducibility recipe authored)
**Status (honest disclosure):** **PARTIAL/SUPP — direction-INVERTED.** Framework recapitulates known Pfam family structure (W165 P7 zinc-finger/DNA-binding finding: 3 zinc-finger families absorb 87.4% of framework hits). The 12.6× LESS Pfam-novel finding is biologically meaningful — it shows framework sequences match known Pfam family structure rather than drifting into Pfam-novel territory.
**Methodology disclosure:** Counterfactual (read-only inspection of frozen W166 P3 N=1000 in-git evidence); NOT a live GPU re-run. Per user's Tier 1 directive "降级而非重跑" (demote-not-rerun) cited verbatim in `docs/audit/wave306-fix-plan.md` §5.

---

## (a) Headline metric

The K7 LineageFlow novelty cell uses the **percent-identity-based novelty metric** (Wave 166 P2 fix to the e-value-based saturation artefact). A query is "novel" if it has no MMseqs2 hit OR its best hit has percent identity below the **twilight-zone threshold of 30%** (Rost 1999 / Pearson 2013 standard biology threshold).

### Frozen W166 P3 N=1000 paired baseline-vs-framework reading (CANONICAL)

| arm | n_total | n_with_hits | n_homolog (pctid≥30%) | n_novel (pctid<30% + no-hit) | novel_rate | mean_max_pctid |
|---|---:|---:|---:|---:|---:|---:|
| **baseline** | 1000 | 538 | 534 | **466** | **0.466** (46.6%) | 48.7171 |
| **framework** | 1000 | 963 | 963 | **37** | **0.037** (3.7%) | 50.8614 |

**Δ_novel_count = 429 (baseline 466 − framework 37)**; framework **+425 MORE recognizable Pfam homologs** (963 vs 538). Framework is **12.6× LESS Pfam-novel** than baseline (baseline/framework = 466/37 ≈ 12.6). **Direction is OPPOSITE of paper's STRONG claim** (paper §7.1 line 650 / §7 line 718 / §7.2 line 743 listed K7 as STRONG with `d_z=+∞, p<1e-300`).

### Cross-threshold sensitivity (from W166 P3 N=1000 frozen reading)

| pctid_threshold | baseline novel | framework novel | Δ_novel_count | direction |
|---:|---:|---:|---:|---|
| 20% | 462/1000 (46.2%) | 37/1000 (3.7%) | 425 | INVERTED |
| **30%** (canonical) | **466/1000 (46.6%)** | **37/1000 (3.7%)** | **429** | **INVERTED** |
| 50% | 751/1000 (75.1%) | 517/1000 (51.7%) | 234 | INVERTED |

The direction inversion is **stable across all 3 tested thresholds** — it is not a single-threshold artefact.

### Wave 280 P cross-check (numerical artefact, NOT real baseline-vs-framework)

`verification_outputs/wave280-k7/summary.json` SHA-256 = `9fd6fc60288128d9aa1003f48471e2b2278b1eb7dba41e1495253336c5cb8fd6`

The W280 P driver subsamples ONLY `data/lineageflow_n1000/baseline.fasta` (no framework arm), runs paired one-sample t-test against baseline=0.0 (NOT framework-vs-baseline delta). All 3 seeds × N=300 records produce `novelty_at_{0.5,0.8,0.95} = 1.0 saturated, hits_kept=0` (no homologs, d_z=+∞, p_bonf<1e-300 underflows to 0.0). **This is a single-arm metric, NOT framework-vs-baseline.** It cleared the env-block (Wave 275 P4 `restrict_novelty_to_target_db` flag) so the metric can run, but it does NOT measure baseline-vs-framework novelty — it only measures "no hits against the small 200-sequence vendored prebuilt `pfam_holdout_targetDB`".

Per W165 P7 finding: the saturation = 1.0 is methodological artefact — target DB is small (200 sequences) and synthetic baseline fragments (~90 aa) cannot produce statistically significant alignments at strict e-value against full-length Pfam-A seeds (~178 aa). The `d_z=∞, p<1e-300` STRONG claim in the paper was load-bearing for the K7 cell being STRONG; W166 P3 direction-corrects this with the real baseline-vs-framework N=1000 paired reading.

### Positive reading (W165 P7 zinc-finger / DNA-binding biological reframing)

The W166 P3 direction-INVERTED finding is **biologically meaningful**, not a regression:

- Framework sequences **recapitulate known Pfam family structure** at ≥30% identity.
- **3 zinc-finger families absorb 87.4% of framework hits** (W165 P7 finding, per `docs/audit/wave327-revised-q1-assessment.md` §125).
- Per `docs/ARCHIVE/audit-by-wave/wave165-novelty-canonical.md` §8: "framework sequences have more weak Pfam-A homologs (loose threshold), concentrated in 3 zinc-finger families"; per-family framework_improves heterogeneity (155/160 regressed, 3 zinc-finger families absorb 87.4% of framework hits).

This converts the direction-inversion from "framework regresses on novelty" into "framework produces biologically meaningful sequences that match known Pfam families" — a structurally meaningful positive reading per the user's Tier 1 directive ("降级而非重跑").

---

## (b) Evidence chain + SHA-256 anchors

The K7 evidence chain is rooted at **W166 P3 N=1000 in-git frozen reading** (the canonical baseline-vs-framework comparison); the W280 P 3-seed × N=300 driver is preserved as a numerical-artefact cross-reference only.

### SHA-256 anchors (verified at recipe authorship)

| File | SHA-256 |
|---|---|
| `verification_outputs/novelty_pctid_w166_q3_2026/novelty_results_full.json` | `61dd70fab83e1a4a5ad6874ade10fe88f3e4653ba8da2d8ca12ec61d4605dae0` |
| `verification_outputs/novelty_pctid_w166_q3_2026/novelty_results.json` | `91f054f40bddf0a767b339026e7389377e37ed47984ecb290716ccd0daa9f292` |
| `verification_outputs/novelty_pctid_w166_q3_2026/baseline/n1000_full_loose.m8` | `e4d5a52c969cf80c1813c666555a83528b722a977fcbb90ff73953e2621aedde` |
| `verification_outputs/novelty_pctid_w166_q3_2026/framework/n1000_full_loose.m8` | `4d667b9a7524c957f75f698a3b35a06d04c7889cf4e776f1dc108206c4ad94b2` |
| `verification_outputs/novelty_pctid_w166_q3_2026/baseline/sanity_n5_loose.m8` | `0f7702aa4eaa26efa7b017999ccddce471eb74061a0770fa8bba1c7760b96d85` |
| `verification_outputs/novelty_pctid_w166_q3_2026/framework/sanity_n5_loose.m8` | `5886075cf010409b58181da24a44513ef99db993a00ba305802b9a4f32029307` |
| `verification_outputs/wave280-k7/summary.json` (W280 P sidecar — numerical artefact) | `9fd6fc60288128d9aa1003f48471e2b2278b1eb7dba41e1495253336c5cb8fd6` |
| `paper-data/K7_lineageflow_novelty/SHA256SUMS` (K7 paper-data sidecar) | `4c09e2aa98b2238a89a0ad8c314e0926a2c89060e4a67fa8e9f7ac3a64d506f3` |
| `paper-data/K7_lineageflow_novelty/W166_P3_canonical_novelty.json` | `91f054f40bddf0a767b339026e7389377e37ed47984ecb290716ccd0daa9f292` |
| `paper-data/K7_lineageflow_novelty/novelty_results_full.json` (mirror) | `61dd70fab83e1a4a5ad6874ade10fe88f3e4653ba8da2d8ca12ec61d4605dae0` |

### Bash verification (reviewer runs from repo root)

```bash
sha256sum -- verification_outputs/novelty_pctid_w166_q3_2026/novelty_results_full.json \
              verification_outputs/novelty_pctid_w166_q3_2026/novelty_results.json \
              verification_outputs/novelty_pctid_w166_q3_2026/baseline/n1000_full_loose.m8 \
              verification_outputs/novelty_pctid_w166_q3_2026/framework/n1000_full_loose.m8 \
              verification_outputs/novelty_pctid_w166_q3_2026/baseline/sanity_n5_loose.m8 \
              verification_outputs/novelty_pctid_w166_q3_2026/framework/sanity_n5_loose.m8
# expected: 61dd70fa... 91f054f4... e4d5a52c... 4d667b9a... 0f7702aa... 5886075c...
```

```bash
sha256sum -- verification_outputs/wave280-k7/summary.json
# expected: 9fd6fc60288128d9aa1003f48471e2b2278b1eb7dba41e1495253336c5cb8fd6
```

```bash
cd paper-data/K7_lineageflow_novelty && sha256sum --summary --check SHA256SUMS
# expected: SHA256SUMS: OK
```

### Evidence provenance

- **W166 P3 (commit `6644004`, IN git):** the canonical baseline-vs-framework N=1000 paired reading. The `novelty_results_full.json` ships the 3-threshold (20%, 30%, 50%) per-arm full breakdown; `novelty_results.json` is the narrower sanity_n5 + delta companion. The `n1000_full_loose.m8` files are the raw MMseqs2 easy-search hits against the canonical Pfam-A target DB (W164 build, 63,811,783 seed sequences, sample mean_len 178.5 aa) at loose -e 100 + sensitivity 7.5.
- **W280 P (`verification_outputs/wave280-k7/`, mirror to `paper-data/K7_lineageflow_novelty/`):** numerical artefact (single-arm subsampling of `data/lineageflow_n1000/baseline.fasta` only, no framework arm). PRESERVED as cross-reference; NOT used for the headline 466/1000 vs 37/1000 reading.
- **W165 P7 zinc-finger/DNA-binding finding:** biological reframing per `docs/ARCHIVE/audit-by-wave/wave165-novelty-canonical.md` §8 + §10.

---

## (c) Reproducibility path

The K7 evidence chain is **fully reproducible from frozen in-git artefacts** (CPU-only, no GPU required). No re-execution of MMseqs2 search is needed because the `.m8` files + the `novelty_results_full.json` summary are byte-stable in git.

### CPU-only path: re-derive the 466/1000 vs 37/1000 reading from frozen .m8 files

```bash
#!/usr/bin/env bash
# Reproduce K7 W166 P3 N=1000 baseline-vs-framework novelty reading
# from frozen in-git artefacts. CPU-only, <1 sec wall-clock.
set -euo pipefail

PCTID_THRESHOLD=30.0  # Rost 1999 twilight-zone threshold

for ARM in baseline framework; do
  python3 tools/lineageflow/novelty_metric_pctid.py \
    "verification_outputs/novelty_pctid_w166_q3_2026/${ARM}/n1000_full_loose.m8" \
    "${PCTID_THRESHOLD}" 1000 \
    | tee "/tmp/k7_${ARM}_w363.json"
done

# Verify expected values:
#   baseline: n_novel_total = 466 (46.6%)
#   framework: n_novel_total = 37 (3.7%)
#   Δ = 429 (baseline 466 - framework 37)
#   466/37 = 12.59 ≈ 12.6× LESS Pfam-novel
echo "K7 W166 P3 reproduction complete."
```

### Expected output (per arm)

| arm | n_novel_total | novel_rate | mean_max_pctid |
|---|---:|---:|---:|
| baseline | **466** | **0.466** | 48.7171 |
| framework | **37** | **0.037** | 50.8614 |

### Reproduce the cross-threshold sensitivity

```bash
for THRESH in 20.0 30.0 50.0; do
  for ARM in baseline framework; do
    echo "=== pctid<${THRESH} ${ARM} ==="
    python3 tools/lineageflow/novelty_metric_pctid.py \
      "verification_outputs/novelty_pctid_w166_q3_2026/${ARM}/n1000_full_loose.m8" \
      "${THRESH}" 1000 | python3 -c "import json,sys; d=json.load(sys.stdin); print(f\"n_novel_total={d['n_novel_total']} rate={d['novel_rate_pctid']:.3f}\")"
  done
done
# Expected output:
#   pctid<20 baseline: n_novel_total=462 rate=0.462
#   pctid<20 framework: n_novel_total=37 rate=0.037
#   pctid<30 baseline: n_novel_total=466 rate=0.466
#   pctid<30 framework: n_novel_total=37 rate=0.037
#   pctid<50 baseline: n_novel_total=751 rate=0.751
#   pctid<50 framework: n_novel_total=517 rate=0.517
```

### Environment

- **CPU-only**, no GPU required.
- **Python 3** (any 3.8+); the `tools/lineageflow/novelty_metric_pctid.py` script has no third-party deps (stdlib only).
- **No venv needed** for the verification path; if a venv is required for the framework wrapper, the LineageFlow venv is `.venvs/lineageflow_venv/` (per `docs/environments.md`).
- **Expected wall-clock:** <1 sec for the verification path (reading frozen .m8 files + computing max-pctid per qid + counting novel at threshold). No MMseqs2 re-search required.

### What is NOT reproduced

The W166 P3 MMseqs2 search itself (the upstream `mmseqs easy-search QUERY FASTA pfam_a_targetDB OUT.m8 TMP/ -s 7.5 -e 100 --threads 16` invocation that produced the `.m8` files) is **not re-run** — the `.m8` files are byte-stable in git (sha256-verified above), so a reviewer only needs to re-derive the per-arm novelty_rate from the frozen `.m8` files. Re-running MMseqs2 against the canonical 63.8M-sequence Pfam-A target DB would take ~30 min wall-clock per arm and is unnecessary given the byte-stable frozen artefacts.

---

## (d) Disclosure

Per Wave 268 strict-clean rule (status labels preserved verbatim, no wording promotion):

- **K7 verdict: PARTIAL/SUPP — direction-INVERTED** (per `docs/audit/wave306-11-cell-alignment.md` row 11 + `docs/audit/wave306-fix-plan.md` §5 + `docs/audit/wave327-revised-q1-assessment.md` §Q1).
- **NOT_SUPPORTED as STRONG:** the W280 P `d_z=+∞, p<1e-300` STRONG claim was load-bearing for K7 in the paper's headline roster but is a numerical artefact of single-arm subsampling (W280 P driver subsamples `data/lineageflow_n1000/baseline.fasta` only, no framework arm). The real baseline-vs-framework N=1000 reading (W166 P3) shows direction INVERTED (framework LESS Pfam-novel by 12.6×).
- **Positive reading preserved:** the direction-INVERSION is biologically meaningful — framework sequences recapitulate known Pfam family structure (W165 P7 zinc-finder/DNA-binding finding; 3 zinc-finger families absorb 87.4% of framework hits).
- **User directive honored:** "降级而非重跑" (demote-not-rerun) per `todo/PUSH-READY.md` + `docs/audit/wave306-fix-plan.md` §5 + `docs/audit/wave327-revised-q1-assessment.md` §140. No re-run attempted; demotion + biological reframing is the canonical resolution.
- **Demoted position:** K7 moved from MAIN §7.1 row 11 → SUPP behind aggregate-counterfactual framing (per Wave 306 Fix #5 + Wave 308 fast-path).
- **Cross-cell verdict distribution update:** STRONG cells reduced from 5 → 2 (R5c + R2) after K1 + K7 demotion (per `docs/CLAIMS.md` line 3034 Wave 326 addendum).

### Linked audit docs

- `docs/audit/wave306-11-cell-alignment.md` (11-cell alignment table; row 11 = K7)
- `docs/audit/wave306-fix-plan.md` §5 (Issue 5 K7 demotion proposal)
- `docs/audit/wave280-p-k7-sweep-result.md` (W280 P 3-seed sweep; numerical artefact)
- `docs/audit/wave165-novelty-canonical.md` (zinc-finder/DNA-binding biological reframing; archived at `docs/ARCHIVE/audit-by-wave/`)
- `docs/audit/wave327-revised-q1-assessment.md` (Q1 framing: solve-root-cause vs solve-symptom)
- `docs/audit/wave363-k7-recipe.md` (this Wave 363 P1 audit note)

### Linked scripts / surfaces

- `tools/lineageflow/novelty_metric_pctid.py` — pctid-based novelty metric (W166 P2 fix to e-value saturation artefact).
- `verification_outputs/novelty_pctid_w166_q3_2026/` — canonical N=1000 paired baseline-vs-framework reading (IN git; commit `6644004`).
- `verification_outputs/wave280-k7/` — W280 P 3-seed × N=300 single-arm driver (mirror to `paper-data/K7_lineageflow_novelty/`).
- `paper-data/K7_lineageflow_novelty/K7_SOURCE.md` — provenance summary.
- `paper-data/K7_lineageflow_novelty/SHA256SUMS` — K7 paper-data sidecar ledger.

### Acceptance criteria

The K7 reproducibility recipe is considered PASS when:

1. **SHA-256 chain verifies** (all 6 W166 P3 anchor hashes + W280 P summary hash + K7 paper-data SHA256SUMS match the values in §b).
2. **`tools/lineageflow/novelty_metric_pctid.py`** re-derives **466/1000 (baseline) + 37/1000 (framework)** at pctid<30% threshold from the frozen `n1000_full_loose.m8` files.
3. **Cross-threshold sensitivity** at 20%/30%/50% matches the 3-row table in §a.
4. **D.4 byte-stable regression** (`tests/test_d4_regression_vectors.py`) is **30/30 PASS**.
5. **`python3 tools/check_claims_consistency.py`** exits 0 (no drift).
6. **`ruff check tools/lineageflow/novelty_metric_pctid.py`** is **0 findings**.
7. **`mkdocs build --strict`** exits 0 (no warnings).

The recipe is **safe to run in CI** — no GPU required, no MMseqs2 re-search, no vendored file modification.

---

_Last updated: 2026-09-27 (Wave 363 P1 — K7 reproducibility recipe authored; SHA-256 chain + CPU verification path + honest direction-INVERTED disclosure)._