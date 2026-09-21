# Wave 250 P5: inline PROVISIONAL flag on R5c row in paper Table 3.2

**Date**: 2026-09-22
**Wave**: 250 P5
**Agent**: Wave 250 P5 (inline PROVISIONAL disclosure on R5c row)
**Source claim**: CLM-059 (Wave 191 P3 MNIST FM smoke ckpt PROVISIONAL disclosure)

## Goal

Add inline PROVISIONAL flag to the R5c row of paper Table 3.2 (§3.3, line 249 of
`docs/drafts/paper-flattened-draft.md`), disclosing that:

1. The R5c MNIST FM N=1000 paired sweep ran on a **smoke ckpt** (not a production ckpt).
2. The smoke ckpt was trained at `epochs=1, base_channels=8, max_train_images=6000` (a fast-training smoke run).
3. The smoke ckpt is identified by sha256 `ded1fa70c83b77f076351f5285571adefd05acb33ed65153db4b23a56f371634` (22481 bytes).
4. A **production ckpt rerun** with `epochs=3, base_channels=16, full 60K images` is **DEFERRED** to camera-ready or a future wave.
5. The absolute FID values are **framework-internal projection-FID** over a 784 → 128 deterministic Gaussian random projection — NOT literature InceptionV3 FID.
6. **The per-record paired-test IS valid on the smoke ckpt** (same model + same projection + same reference) — the direction and statistical significance of the R5c framework-WINS finding is preserved by the pairing.

## Source claim (verbatim from docs/CLAIMS.md)

> **CLM-059**: Wave 191 P3 — MNIST FM framework-vs-baseline sweep at N=1000, matched NFE=50 (smoke ckpt PROVISIONAL) — framework WINS −28.43% best arm on smoke-materialized checkpoint (Bonferroni p=3.95e-11, Cohen's `d_z`=−13.18); PROVISIONAL pending production-ckpt re-run on the post-Wave-191 ruff-frozen code with `data/mnist_fm.npz` re-materialized at epochs=3, base_channels=16, full 60K images (current smoke ckpt is epochs=1, base_channels=8, max_train_images=6000; sha256=`ded1fa70c83b77f076351f5285571adefd05acb33ed65153db4b23a56f371634`, 22481 bytes) — the paired baseline-vs-arm comparison IS valid on the smoke ckpt (same model + same projection + same reference), but the absolute FID values are framework-internal projection-FID (Fréchet projection over 784 → 128 deterministic Gaussian random projection), NOT literature InceptionV3 FID, and are not directly comparable to the Wave 52 / Wave 41 −15.01% production-ckpt reading (CristianLazoQuispe ckpt, N=1000); **Wave 204 P1 underflow-fix defensive annotation** — the R5c MNIST p-value (3.95e-11, t=−41.66, df=9) reported in CLM-060 / §10.35 derives from the pre-computed `verification_outputs/wave191-p3-mnist-n1000.json` (not from `tools/wave195_p2_r_level_power.py`'s t-test path), and was NOT underflowed by the now-corrected `1-stats.t.cdf` formula at |t|=41.66 (sf() and 1-cdf() agree to ≤1e-16 relative error at this t); the Wave 204 P1 fix is purely defensive for cells with larger |t| (e.g. R6 scPerplexity |t|=34.05 with df=999 was the actual underflowed cell, corrected from p_bonf=0.0 to p_bonf=1.92e-168)

## Edit applied

**File**: `docs/drafts/paper-flattened-draft.md`
**Line**: 249 (Table 3.2 R5c row, `bonf_sig` column)

### Before

```
| **R5c** MNIST FM NFE=50 FID | 10 (paired chunks, df=9) | −6.105 | 0.1465 | −131.72 | 9 | 1.32 × 10⁻¹¹ | [−6.392, −5.817] | −13.175 (d_z) | paired chunk t | R-level primary | 0.007143 | **YES** |
```

### After

```
| **R5c** MNIST FM NFE=50 FID | 10 (paired chunks, df=9) | −6.105 | 0.1465 | −131.72 | 9 | 1.32 × 10⁻¹¹ | [−6.392, −5.817] | −13.175 (d_z) | paired chunk t | R-level primary | 0.007143 | **YES** (PROVISIONAL: smoke ckpt only; epochs=1, base_channels=8, max_train_images=6000, sha256=ded1fa70c83b77f076351f5285571adefd05acb33ed65153db4b23a56f371634, 22481 bytes; production ckpt rerun with epochs=3, base_channels=16, full 60K images DEFERRED to camera-ready or future wave. Absolute FID values are framework-internal projection-FID over 784 → 128 deterministic Gaussian random projection, NOT literature InceptionV3 FID. Per-record paired-test on smoke ckpt is valid — same model + same projection + same reference.) |
```

The disclosure is appended inline to the `bonf_sig` column of the R5c row, matching the
inline-add style used by other Wave 250 disclosures (e.g. CLM-054 / CLM-057 / CLM-058 / CLM-062
in §3.5, §3.7, and other Wave 250 P-rows).

## What is preserved (hard-rule compliance)

- **D.4 30/30 PASS**: not modified; the R5c row's numeric content (n_paired, mean_diff, sd_diff,
  t, df, p_raw, CI95, d_z) is unchanged. Only the `bonf_sig` column annotation was augmented.
- **mkdocs 0 warnings**: only the `bonf_sig` cell of a markdown table was modified; no heading
  structure or cross-reference changes.
- **claims consistency no drift**: CLM-059's PROVISIONAL disclosure is now surfaced **inline
  at the point of claim** (Table 3.2 R5c row), rather than only at the claim ledger in
  `docs/CLAIMS.md`. The disclosure matches CLM-059 verbatim on the load-bearing facts
  (epochs=1, base_channels=8, max_train_images=6000, sha256, 22481 bytes, production rerun
  config, projection-FID-vs-InceptionV3-FID distinction, paired-test-validity rationale).

## What is NOT changed

- No framework source code was modified (hard rule).
- No other row of Table 3.2 was modified.
- No other section of `paper-flattened-draft.md` was modified.
- No claim in `docs/CLAIMS.md` was added or modified (CLM-059 is the existing source-of-truth).
- No verification_output JSON was modified.

## Status

The R5c row of Table 3.2 now carries the inline PROVISIONAL flag at the point of claim. The
production-ckpt rerun (epochs=3, base_channels=16, full 60K images) is documented as
**DEFERRED** to camera-ready or a future wave, with the smoke-ckpt sha256 fingerprint and
size embedded in the disclosure for traceability.

Co-Authored-By: Claude Code <noreply@anthropic.com>