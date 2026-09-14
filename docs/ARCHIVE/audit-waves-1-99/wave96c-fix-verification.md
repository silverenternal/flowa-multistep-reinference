# Wave 96 Agent C — Kanzi framework endpoint diversity fix verification

**Date:** 2026-09-10
**Agent:** Wave 96 Agent C
**Branch:** main
**Fix under test:** commit `1f26bf6` — "Wave 96.B: fix Kanzi framework endpoint collapse root cause"
**Diagnosis under test:** `docs/audit/wave96a-collapse-diagnosis.md` (commit `a7b97d2`)
**Status:** FIX CONFIRMED on the diversity axis. One of three numeric targets missed — reported honestly in §5. **No source files modified.**

---

## 1. Mission

Wave 96.A diagnosed that the Wave 92c / Wave 95 P3.C Kanzi framework-arm
sweep collapsed every record to a single FSQ codebook index because the
sweep driver **synthesised** `x_final` as `N(0, σ=1e-3)` over `(64, 512)`
(L2 norm ≈ 0.18) instead of running the real framework pipeline.

Wave 96.B replaced `synthesize_x_final_512d(record_idx)` with
`real_framework_x_final_512d(adapter, record_idx, seed)`, which runs
`KanziAdapter.build_initial_state` + `KanziAdapter.solve_ode` (50-NFE
Euler) and returns `trajectory[-1]`.

Agent C's job: **verify the fix actually produced diverse endpoints** on
N=10 records, on the three metrics named in the brief.

---

## 2. Method

| Knob | Value |
|---|---|
| Interpreter | `.venvs/kanzi_venv/bin/python` |
| Step 2 | Re-ran `tools/_wave96a_diagnose_collapse.py` (unchanged) — reproduced the Wave 96.A baseline exactly |
| Step 3 | Ran a read-only A/B harness (`/tmp/wave96c_verify.py`, not committed) that imports **both** `synthesize_x_final_512d` (BEFORE, still present but deprecated) and `real_framework_x_final_512d` (AFTER) from the fixed sweep driver and pushes each through the *identical* per-record pipeline the driver uses |
| Records | 10 (matches the Wave 95 P3.C N=10 RETRY) |
| Seed | 42 |
| Ckpt | `data/kanzi_ckpt/cleaned_model.pt` |
| Adapter | `default_kanzi_adapter(weights_path=ckpt, force_mode="torch", num_steps=50, solver="euler")` — exactly the Wave 96.B construction |
| Pipeline per record | `x_final` → `kanzi_latent_to_coords` (bridge, `n_steps=20`) → `DAE.encode` → `idx_BL` → `DAE.decode` → Kabsch RMSD vs the bridge output |
| Raw output | `verification_outputs/wave96c_verify/wave96c_diversity.json` |

The BEFORE arm is not a re-quote of Wave 95 — it was re-executed here, and
it lands on **3.1783 ± 0.0000 Å**, byte-identical to the Wave 95 P3.C N=10
RETRY figure. That anchors the A/B: the only variable between arms is the
`x_final` generator.

### 2.1 Re-run of the Wave 96.A diagnostic (Step 2)

```
records processed:                  10
unique idx sequences (σ=1e-3):      1/10
identical-idx pair count:           45/45
x_final L2 norm range:              [0.1803, 0.1814]
pairwise x_final L2 (mean offdiag): 0.2557
min_dist to nearest codebook:       rec0 mean=0.043968
```

Identical to the Wave 96.A audit §3. The diagnosis reproduces.

---

## 3. Before / After

### 3.1 Endpoint geometry

| Metric | BEFORE (Wave 92c / 95 P3.C, σ=1e-3 synthetic) | AFTER (Wave 96.B, real `solve_ode`) | Ratio |
|---|---|---|---|
| `x_final` L2 norm (min) | 0.1803 | 180.39 | ×1001 |
| `x_final` L2 norm (max) | 0.1814 | 182.15 | ×1004 |
| **mean pairwise L2 `‖x_final[i] − x_final[j]‖`** | **0.2557** | **255.91** | **×1001** |
| pairwise L2 (min off-diag) | 0.2540 | 254.62 | ×1002 |
| pairwise L2 (max off-diag) | 0.2588 | 257.69 | ×996 |

Both arms have *non-zero* pairwise distance in 512-d — the BEFORE arm's
endpoints were never literally identical. The failure was that 0.2557 in
512-d projects to well inside a single FSQ cell (smallest half-width
0.143), so the diversity was destroyed at the snap step. AFTER, the
pairwise separation is three orders of magnitude larger and survives the
snap.

### 3.2 Codebook index diversity

| Metric | BEFORE | AFTER | Target |
|---|---|---|---|
| **unique `idx_BL` sequences across 10 records** | **1 / 10** | **10 / 10** | ≥ 5 distinct |
| identical idx-sequence pairs | 45 / 45 | **0 / 45** | 0 |
| distinct codebook indices used (pooled over 10×64 positions) | 54 | **391** | — |
| distinct indices *within* one record's 64 positions | 54 (identical set every record) | 57–62 (varies per record) | — |

> Note on the "54" in the BEFORE column: these are the indices recovered
> after `DAE.encode` of the *decoded* coordinates, not the bridge's own
> snap. The bridge itself snapped **every** position of **every** record
> to `idx=500` (Wave 96.A §3). The decoder's fixed output for that constant
> index sequence re-encodes to a fixed 54-index set — the same set for all
> 10 records, which is exactly why `n_unique_idx_sequences = 1`.

### 3.3 Reconstruction RMSD spread

| Metric | BEFORE | AFTER | Target |
|---|---|---|---|
| mean RMSD (Å) | 3.1783 | 1.7662 | — |
| min RMSD (Å) | 3.1783 | 1.4253 | — |
| max RMSD (Å) | 3.1783 | 2.1610 | — |
| **std RMSD (Å)** | **4.68e-16 (≡ 0)** | **0.2140** | > 0.5 |
| range (max − min, Å) | 0.0 | 0.7357 | — |

BEFORE, all ten per-record RMSDs are the *same float* to the last bit
(3.178325888309639) — the signature of a fully collapsed arm. AFTER, all
ten differ, spanning 1.43–2.16 Å.

---

## 4. Verdict

**The Wave 96.B fix worked.** The collapse is gone:

1. **Non-zero pairwise distance that survives the snap** — PASS. Mean
   pairwise L2 rose from 0.2557 to 255.91 (×1001), which is what carries
   the endpoints across FSQ cell boundaries.
2. **Multiple codebook indices spanned** — PASS, decisively. 10/10 unique
   `idx_BL` sequences against a target of ≥5, 0/45 identical pairs
   (was 45/45), 391 distinct pooled indices (was 54, all shared).
3. **Non-zero RMSD std** — PASS on the stated intent (*"NOT zero"*),
   **MISS on the stated threshold** (`> 0.5`). Measured 0.2140 Å. See §5.

The mechanism Wave 96.A predicted is confirmed end-to-end: real
`KanziAdapter.solve_ode` endpoints have L2 norm ~180, three orders of
magnitude above the σ=1e-3 synthetic ball, and that is precisely what
restores per-record codebook diversity.

---

## 5. Honest note on the RMSD-std target (0.214 vs > 0.5)

The `std > 0.5` target is **not met**, and it should not be quietly
rounded up to a pass.

The measured 0.2140 Å is a genuine, healthy spread — every record differs,
the range is 0.74 Å — but it is roughly half the requested threshold. Two
observations, offered without over-claiming:

* This RMSD is a **round-trip identity** measure
  (`bridge output → encode → decode → Kabsch vs bridge output`), i.e. it
  measures FSQ quantisation error, not endpoint diversity directly. Its
  spread is bounded by how much the decoder's reconstruction error varies
  across index sequences, which is a narrower quantity than the endpoint
  diversity itself. A 0.5 Å std on this particular metric was an
  optimistic target; the diversity signal it was standing in for is
  better read off §3.2, where the margin is unambiguous.
* At N=10 the std estimate is itself imprecise. This is a diversity smoke
  test, not a powered measurement, and the audit does not claim otherwise.

The correct reading: **criterion 3 passes on "non-zero", fails on "> 0.5",
and criteria 1 and 2 pass outright.** The collapse is fixed; the specific
0.5 Å number was the wrong yardstick for this metric.

---

## 6. What this does *not* establish

Scope discipline, since the surrounding waves care about the W2 verdict:

* This is **N=10**, a diversity check. It says nothing about whether the
  framework arm *beats* the baseline arm on any paper metric.
* The AFTER mean RMSD (1.77 Å) is lower than the BEFORE mean (3.18 Å), but
  these are not comparable quantities — BEFORE was measuring the decoder's
  fixed error at a single degenerate index, AFTER measures real
  quantisation error across real index sequences. **No improvement claim
  is made from that comparison.**
* The W2 closure criterion (`|Δ| < 0.5 Å`) requires a re-run of the full
  N=1000 sweep with the fixed driver plus a matched baseline arm. That is
  now *structurally measurable* (it was not before Wave 96.B) but it has
  not been measured here.

---

## 7. Files touched (Wave 96 Agent C)

| File | Change |
|---|---|
| `docs/audit/wave96c-fix-verification.md` | NEW — this audit doc |
| `verification_outputs/wave96c_verify/wave96c_diversity.json` | NEW — raw A/B metrics, 10 records × 2 arms |
| `verification_outputs/wave96a_diagnose/*.json` | REGENERATED by the Step-2 diagnostic re-run (byte-equivalent content) |

**No source files modified.** The verification harness was written to
`/tmp/wave96c_verify.py` and deliberately not added to the repo, since the
brief scoped Agent C to verification only.

---

## 8. TL;DR

| | idx diversity | mean pairwise L2 | RMSD std |
|---|---|---|---|
| **Before** (Wave 92c / 95 P3.C) | **1** unique sequence, 45/45 identical pairs | 0.2557 | **0.0** |
| **After** (Wave 96.B, `1f26bf6`) | **10** unique sequences, 0/45 identical pairs | **255.91** | **0.2140** |
| Target | ≥ 5 | non-zero | > 0.5 |
| Verdict | **PASS** | **PASS** | non-zero **PASS**, threshold **MISS** |

The Kanzi framework endpoint collapse is fixed. The sweep driver now
exercises the real framework pipeline, and the FSQ codebook is reachable.
Next step is a full N=1000 re-run with a matched baseline arm to settle W2.

Co-Authored-By: Claude Code <noreply@anthropic.com>
