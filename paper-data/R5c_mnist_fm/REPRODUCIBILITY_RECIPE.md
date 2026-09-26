# R5c MNIST FM FID — Reproducibility Recipe

**Cell:** R5c MNIST FM FID regime curve (smoke ckpt STRONG; production ckpt direction-FLIPS)
**Headline:** 3-point regime curve at matched NFE=50 — smoke ckpt d_z=-13.18 framework-WINS (-28.43% FID), intermediate +8.53% baseline-WINS, production 3-seed d_z=+1.30 baseline-WINS (+10.37% FID)
**Date:** 2026-09-27 (Wave 363 P1 — reproduction recipe authored)
**Verdict status:** **REGIME-DEPENDENT** (smoke ckpt STRONG; production ckpt honest-negative at matched NFE; framework value-add is cross-budget only per Wave 128 paradigm)

---

## (a) Headline Metric — 3-Point Regime Curve

The R5c cell is **regime-dependent**: the framework-vs-baseline direction
**flips** between under-trained and well-trained checkpoints. The
canonical evidence is a 3-point table mapping `epochs` × `base_channels`
× `max_train_images` → `delta_pct` (best-arm framework FID vs baseline
FID at matched NFE=50):

| ckpt | epochs | base_channels | max_train_imgs | n_records × n_seeds | baseline_fid | best_arm_fid | delta_pct | d_z | p_bonf | verdict |
|---|---|---|---|---|---|---|---|---|---|---|
| **smoke**       | 1 | 8  | 6 000  | 1000 × 1 (seed 42) | 29.4925 | 23.3879 | **-28.43%** | -13.18 | 3.95e-11 | **framework_wins** |
| **intermediate**| 2 | 16 | 60 000 | 200 × 1 (seed 42)  | 13.4498 | 15.4403 | **+8.53%**  | +1.16  | 1.58e-02 | **baseline_wins**  |
| **production**  | 3 | 16 | 60 000 | 200 × 3 (42/43/44) | 11.9896 | 13.6668 | **+10.37%** | +1.30  | 1.33e-02 | **baseline_wins**  |

The "best arm" is `EvidenceDrivenScheduler` on all 3 ckpts (per the
Wave 191 P3 / Wave 280 P / Wave 334 regime-curve sweeps).

**Honest framing:**
- The **epochs=1 → epochs=2** transition is **confounded** (smoke uses
  base_channels=8 + 6K imgs vs epochs=2-3 use base_channels=16 + 60K
  imgs).
- The **epochs=2 → epochs=3** transition is **clean** (matched
  architecture, matched dataset; only epochs varies). The framework's
  regression deepens from +8.53% (d_z = +1.16) to +10.37% (d_z = +1.30,
  3-seed mean). The verdict is `baseline_wins` at both epochs.

The framework value-add on MNIST FM at matched NFE=50 is therefore
**monotonically decreasing in ckpt quality**. The flip happens between
epochs=1 and epochs=2 (the under-trained → well-trained transition).

---

## (b) Evidence Chain + SHA-256 Anchors

The 3-point regime curve is anchored to 6 verification artefacts + 3
checkpoint artefacts. All hashes were verified at recipe authorship
(2026-09-27).

### Verification artefacts (smoke ckpt, Wave 191 P3, N=1000 × 1 seed)

| File | SHA-256 |
|---|---|
| `verification_outputs/wave191-p3-mnist-n1000.json` (headline) | `a5270a0aacc99551c3ed15304f00d68baa41ac3f6012e3ad26f2dbbe96dc5e06` |
| `verification_outputs/wave191-p3-mnist-n1000/baseline_samples.npz` | `f7eb8c3536426c70faae951803fd84814bdb3900aed5b7adfebd537e6c3fe290` |
| `verification_outputs/wave191-p3-mnist-n1000/cosine_samples.npz` | `6b44d91efb097d7456d39f7151c851a7d477ba16a53b0aef0e0333b1f90baa45` |
| `verification_outputs/wave191-p3-mnist-n1000/codimension_sheet_samples.npz` | `eb6cf305d88c536ba223844ccb08208ae3c797a972b93d6c6a12de77491aeeac` |
| `verification_outputs/wave191-p3-mnist-n1000/evidence_driven_samples.npz` | `be0d58de1e91d972fa03b01e0477bda5065534870cd09079f7c468b8bf698327` |

### Verification artefacts (production ckpt, Wave 280 P, 3-seed × N=200)

| File | SHA-256 |
|---|---|
| `verification_outputs/wave280-p-r5c/aggregate.json` | `806da3905748d51194713fd140c8a6258aaddb9dcdbbd65579fe6d4293947221` |

### Checkpoint artefacts (the 3 ckpts)

| Ckpt | Path | SHA-256 |
|---|---|---|
| smoke | `data/mnist_fm.npz` (22 481 B) | `ded1fa70c83b77f076351f5285571adefd05acb33ed65153db4b23a56f371634` |
| intermediate | `data/mnist_fm/epochs2.ckpt.npz` (75 438 B) | `ca3ae972b6580de8c9a957f01dee1df786539768a0064da57ffacd9cc80ae360` |
| production | `data/mnist_fm/production.ckpt.npz` (75 472 B) | `27e2bb6c44758822749de004595b9e0543cfc3caf1bfa47641bedcee34f220aa` |

### Regime-curve figure

| File | SHA-256 |
|---|---|
| `docs/figures/fig5_r5c_regime_curve.png` | `c3696fae872982ec77656cd69f26eea989a6cc926ec26af1ae82a5c8759154ae` |

### Bash verification (reviewer runs from `verification_outputs/`)

```bash
sha256sum -- verification_outputs/wave191-p3-mnist-n1000.json \
             verification_outputs/wave191-p3-mnist-n1000/{baseline,cosine,codimension_sheet,evidence_driven}_samples.npz \
             verification_outputs/wave280-p-r5c/aggregate.json \
             data/mnist_fm.npz \
             data/mnist_fm/epochs2.ckpt.npz \
             data/mnist_fm/production.ckpt.npz \
             docs/figures/fig5_r5c_regime_curve.png
# expected: a5270a0a / f7eb8c35 / 6b44d91e / eb6cf305d / be0d58de /
#           806da390 / ded1fa70 / ca3ae972 / 27e2bb6c / c3696fae
```

The `paper-data/R5c_mnist_fm/` directory mirrors 8 of these artefacts
via symlinks (per `paper-data/MANIFEST.md` §R5c); the SHA-256 chain is
preserved in `paper-data/SHA256SUMS`.

---

## (c) Reproducibility Path

**Environment:** `.venvs/flowmol3_venv` (per `docs/environments.md` —
2D FM / CIFAR / MNIST FM all use the `flowmol3_venv` per AGENTS.md §4.3
guardrail "**never mix model environments**"). CPU materialization is
in scope; sweep execution requires a single GPU (~10 min wall).

### Step 1 — Materialize the 3 ckpts (CPU-only)

```bash
source .venvs/flowmol3_venv/bin/activate
PYTHONPATH=. python3 tools/materialize_mnist_fm.py \
    --epochs 1 --base-channels 8  --max-train-images 6000  \
    --output data/mnist_fm.npz
PYTHONPATH=. python3 tools/materialize_mnist_fm.py \
    --epochs 2 --base-channels 16 --max-train-images 60000 \
    --output data/mnist_fm/epochs2.ckpt
PYTHONPATH=. python3 tools/materialize_mnist_fm.py \
    --epochs 3 --base-channels 16 --max-train-images 60000 \
    --output data/mnist_fm/production.ckpt
```

Wall-clock: smoke ckpt ~2 min, intermediate ckpt ~10 min, production
ckpt ~31 min (per Wave 280 P / Wave 334 wall-clock measurements; CPU
only, NumPy Adam trainer). The `materialize_mnist_fm.py:118-122`
post-save log line raises a benign `FileNotFoundError` against the
unsuffixed `--output` path AFTER `np.savez_compressed` has already
written the `.npz` file — the ckpt is fully materialized and SHA-256
verified despite the non-zero exit code (per Wave 280 P §5.3).

### Step 2 — Sweep (GPU; `flowmol3_venv`)

```bash
# Smoke ckpt: N=1000, seed=42
PYTHONPATH=. python3 scripts/wave191_p3_mnist_sweep.py \
    --n-samples 1000 --output-dir verification_outputs/wave191-p3-mnist-n1000 \
    --seed 42
# Intermediate ckpt: N=200, seed=42
PYTHONPATH=. python3 scripts/wave191_p3_mnist_sweep.py \
    --ckpt data/mnist_fm/epochs2.ckpt.npz --n-records 200 \
    --seed 42 --output-dir /tmp/wf334-r5c-sweep/seed42
# Production ckpt: N=200, seeds 42/43/44
for SEED in 42 43 44; do
  PYTHONPATH=. python3 scripts/wave191_p3_mnist_sweep.py \
    --ckpt data/mnist_fm/production.ckpt.npz --n-records 200 \
    --seed $SEED --output-dir /tmp/wf280-r5c/seed$SEED
done
```

Wall-clock: smoke ckpt sweep ~10.3 min (k=10 chunks × 4 arms × 50 NFE,
GPU); intermediate ckpt sweep ~3.6 min; production ckpt sweep ~6 min
per seed (×3 seeds = ~18 min total).

### Step 3 — Aggregate (CPU-only)

```bash
# Aggregate the production-ckpt 3-seed sweep into the canonical aggregate.json
PYTHONPATH=. python3 /tmp/wf280-r5c/aggregate.py \
    --input /tmp/wf280-r5c \
    --output verification_outputs/wave280-p-r5c/aggregate.json
```

The `aggregate.py` helper computes per-seed `d_z`, `delta_pct`, and
Bonferroni-corrected `p_bonf` (α=0.05/3=0.0167 across 3 arms), then
writes the canonical `wave280-p-r5c/aggregate.json` matching SHA-256
`806da390…3947221`.

### Step 4 — Reproduction invariants

The 3-point regime curve is reproduced when:
1. All 10 SHA-256 anchors above match (`verification_outputs/wave191-p3-mnist-n1000.{json,npz×4}` + `verification_outputs/wave280-p-r5c/aggregate.json` + 3 ckpts + the regime-curve figure).
2. The 3 chunk-FID delta_pct values reproduce: **-28.43%** (smoke), **+8.53%** (intermediate), **+10.37% ± 2.64%** (production, 3-seed mean).
3. The headline FIDs reproduce within FID-projection tolerance: smoke baseline 29.49 / framework 23.39; intermediate baseline 13.45 / framework 15.44; production baseline 11.99 / framework 13.67.

---

## (d) Disclosure (per Wave 268 Strict-Clean Rule)

**Status label: REGIME-DEPENDENT (smoke STRONG; production honest-negative).**

The R5c headline is **NOT** `SUPPORTED` (per the AGENTS.md hard
guardrail #4: never promote `UNDERPOWERED` / `DEFERRED` / `REGRESSES`
to `SUPPORTED` by wording alone). The verdict is **`REGIME-DEPENDENT`**:

- **Smoke ckpt** (epochs=1, base_channels=8, 6K imgs): **STRONG**
  framework_wins — d_z = -13.18, Bonferroni p = 3.95e-11 (smoke ckpt
  materialization is intentionally under-trained; absolute FID values
  are framework-internal projection-FID, not literature InceptionV3
  FID).
- **Intermediate ckpt** (epochs=2, base_channels=16, 60K imgs):
  **baseline_wins** at matched NFE=50 — d_z = +1.16, Bonferroni
  p = 0.0158 (single-seed sweep).
- **Production ckpt** (epochs=3, base_channels=16, 60K imgs):
  **baseline_wins** at matched NFE=50 — d_z = +1.30 mean (per-seed
  [+1.55, +1.33, +1.02], all > 0.8), Bonferroni p = 0.0133 mean
  (2 of 3 seeds < 0.0167 strict Bonferroni).

The framework's value-add on production-ckpt MNIST FM is the
**cross-budget** claim (Wave 128 paradigm): comparable quality at
fewer NFEs. At matched NFE=50, the framework's restart-blend glue has
no value-add and a small regression on production-quality ckpts.
This is consistent with the Wave 191 P2 CIFAR-10 RF
"baseline_wins at matched NFE" finding.

The CLM-059 status addendum (Wave 280 P) preserves the smoke-ckpt
`framework_wins -28.43%` reading verbatim and adds the
production-ckpt `baseline_wins +10.37%` reading as a new row —
**no R-level cell number is changed, no §10.6 R-level inventory is
modified** (per the Wave 268 strict-clean additive-status-history rule).

### Cross-references

- **Smoke-ckpt sweep:** `verification_outputs/wave191-p3-mnist-n1000.json`
  + `docs/CONSOLIDATED_RESULTS.md` §15.87 (Wave 191 P3 row).
- **Production-ckpt sweep:** `verification_outputs/wave280-p-r5c/aggregate.json`
  + `docs/audit/mnist/wave280-p-r5c-sweep-result.md` (Wave 280 P audit).
- **Regime curve:** `docs/audit/mnist/wf334-r5c-regime-curve.md` (Wave
  334 epoch=2 intermediate sweep) + `docs/figures/fig5_r5c_regime_curve.png`
  (Figure 5 regime curve rendering).
- **CLAIMS.md:** CLM-059 (smoke-ckpt `framework_wins` + production-ckpt
  `baseline_wins` addendum) + CLM-060 (Wave 195 P2 R-level power
  analysis) + CLM-060 Wave 280 P status addendum (3-seed evidence
  upgrades).
- **D.4 byte-stable regression gate:** `tests/test_d4_regression_vectors.py`
  must remain 30/30 PASS for the recipe to be in scope.

---

_Last updated: 2026-09-27 (Wave 363 P1 — R5c MNIST FM regime-curve
reproducibility recipe authored; SHA-256 chain verified at authorship;
D.4 30/30 PASS + claims consistency PASS + ruff 0 + mkdocs strict PASS)._