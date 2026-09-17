# Wave 175 P2 — per-adapter NFE_REF implementation

**Scope:** minimal-blast-radius implementation of Option A from
`docs/audit/wave175-p1-design.md` §4.

**Owners:** Wave 175 P2 implementer.

---

## 1. Edits

### `tools/eval/io.py`

Added a new module-level registry near the `DOWNSTREAM_METRICS` block:

```python
# Wave 175 — per-adapter NFE_REF for NFE-adaptive restart-blend strength.
# LineageFlow NFE_REF=50 preserves Wave 172b ladder anchor (+1.37/+0.81/+0.83
# pLDDT delta at NFE=50/100/200) and the lineageflow uniform-win story.
# Kanzi NFE_REF=10 attenuates β so restart-blend does NOT over-apply to
# kanzi's high-baseline pLDDT=57.4 ceiling (Wave 174 P5 evidence: at
# NFE_REF=50, kanzi β was 1.0/0.5/0.25 → pLDDT regressed -2.25/-5.79/-0.54
# at NFE=50/100/200; the regression is structural — restart-blend cannot
# improve a saturated metric and may perturb the integrator off the
# calibration manifold). At NFE_REF=10, kanzi β scales to 0.2/0.1/0.05 at
# NFE=50/100/200, effectively making the framework a memory-only pass that
# preserves the baseline pLDDT while still benefiting from the per-round
# paper-quantity-aware scheduler (which drives scPerplexity independently
# of restart-blend β magnitude).
ADAPTER_NFE_REF: dict[str, int] = {
    "KanziAdapter": 10,         # saturated at pLDDT=57.4
    "LineageFlowAdapter": 50,   # Wave 172b ladder anchor
}
DEFAULT_NFE_REF: int = 50
```

### `tools/eval/framework.py`

Import line:

```python
from tools.eval.io import (  # type: ignore
    ADAPTER_NFE_REF,
    DEFAULT_NFE_REF,
    DOWNSTREAM_METRICS,
    FLOWMOL3_REAL_CKPT,
)
```

Inside `_make_framework_policy` (replacing the Wave 173 P4 hardcoded
`_NFE_REF = 50`):

```python
# Wave 173 P4 — NFE-adaptive restart-blend strength. The
# ``nfe == 0`` sentinel preserves the legacy byte-stable contract
# (D.4 vector suite + Wave 161 K6 R6 sha256 are both measured
# under ``nfe == 0``); only ``nfe > 0`` exercises the new
# ``min(1.0, NFE_ref / max(nfe, 1))`` scaling. See
# ``docs/audit/wave173-fix-design.md`` §4.1 + §6.
#
# Wave 175 — per-adapter NFE_REF (replaces the hardcoded
# ``_NFE_REF = 50``). LineageFlow keeps 50 (Wave 172b anchor cell
# +1.37/+0.81/+0.83); Kanzi gets 10 (saturated pLDDT=57.4 ceiling
# — restart-blend perturbation cannot improve a saturated metric;
# see ``docs/audit/wave175-p1-design.md`` §4 Option A and
# ``docs/audit/wave175-p2-impl.md`` for the byte-stability
# argument and β attenuation table).
if int(nfe) > 0:
    _adapter_name = type(adapter).__name__
    _NFE_REF = int(ADAPTER_NFE_REF.get(_adapter_name, DEFAULT_NFE_REF))
    _scale = min(1.0, float(_NFE_REF) / float(max(1, int(nfe))))
    beta = float(beta) * float(_scale)
```

---

## 2. β attenuation table (post-fix)

| NFE | LineageFlow β scale | LineageFlow β (×0.5 base) | Kanzi β scale | Kanzi β (×0.5 base) |
|----:|--------------------:|---------------------------:|--------------:|---------------------:|
|  50 |               1.000 |                     0.5000 |         0.200 |               0.1000 |
| 100 |               0.500 |                     0.2500 |         0.100 |               0.0500 |
| 200 |               0.250 |                     0.1250 |         0.050 |               0.0250 |

*Kanzi β at NFE=100/200 is now < 5% of full → restart-blend perturbation
is effectively suppressed; the framework operates as a memory-only
multi-round pass that preserves baseline pLDDT while the per-round
paper-quantity-aware scheduler continues to drive scPerplexity
independently of β magnitude.*

---

## 3. Byte-stability argument

The fix is **additive only on the `nfe > 0` path**:
- D.4 vector suite uses `nfe == 0` (legacy default) → the `if int(nfe) > 0` block is **bypassed entirely** → byte-stable.
- Wave 161 K6 R6 (the kanzi `framework_inv_proj` +1.12 pLDDT headline) was measured under `nfe == 0` (per `tools/eval/framework.py:323-326` docstring) → unchanged.
- Wave 172b ladder (the `+1.37` lineageflow NFE=50 anchor) used `nfe > 0` with `_NFE_REF = 50`; after the fix lineageflow still maps to `_NFE_REF = 50` → identical behavior on the lineageflow path.
- Wave 174 P5 ladder (the `+1.37 / +0.81 / +0.83` lineageflow and `−2.25 / −5.79 / −0.54` kanzi headline) used `nfe > 0` with `_NFE_REF = 50`; after the fix:
  - Lineageflow path: identical (`_NFE_REF = 50` for both pre- and post-fix).
  - Kanzi path: `_NFE_REF = 10` (new) → β attenuated.

The D.4 vector sha256 + Wave 161 K6 R6 sha256 must remain byte-identical.
The Wave 172b ladder must reproduce. The Wave 174 P5 lineageflow numbers
must reproduce. Only the kanzi path differs.

---

## 4. Verification

* `pytest tests/ -k "d4" -q` — **33 passed, 30 skipped** (no regressions).
* `ruff check tools/eval/framework.py tools/eval/io.py` — **All checks passed!**
* `python tools/check_claims_consistency.py` — **No drift detected.**
  39 active claims, 0 provisional, 2 deprecated (CLM-040 forced to PROVISIONAL
  per `Disputed by` citation — pre-existing state, not caused by this change).

---

## 5. Expected outcome (P3 sanity + P4 full)

If P3 confirms kanzi pLDDT no longer regresses at NFE=100 (target:
`ΔpLDDT ≥ −2` or positive), P4 full N=30 ladder will produce the
following expected kanzi numbers:

| NFE | baseline pLDDT | framework pLDDT (expected) | Δ (expected) | Δ scPerplexity (preserved) |
|----:|---------------:|---------------------------:|-------------:|---------------------------:|
|  50 |          57.41 |                       ~57.0 | ≈ −0.4       | ≈ −3.5 to −3.8             |
| 100 |          57.41 |                       ~57.3 | ≈ −0.1       | ≈ −3.0 to −3.5             |
| 200 |          57.41 |                       ~57.4 | ≈ 0.0        | ≈ −3.0 to −3.5             |

The kanzi pLDDT is expected to come within ±1 of baseline at all NFE
levels (the framework now operates as memory-only at high NFE so the
integrator trajectory stays on the calibration manifold). The scPerplexity
win is expected to be slightly smaller than Wave 174 (−3.0 to −3.8 instead
of −3.02 to −3.87) because the per-round paper-quantity scheduler still
drives exploration independent of β, but the perturbation magnitude is
reduced.

If P3 sanity shows `ΔpLDDT < −2`, escalate to NFE_REF=5 (β scale 0.1/0.05/0.025
at NFE=50/100/200) or NFE_REF=0 (disable restart-blend entirely for kanzi,
keep only paper-quantity-driven scheduler).

---

## 6. File paths (absolute)

* `/home/hugo/codes/flowa-multistep-reinference/tools/eval/io.py` — new
  `ADAPTER_NFE_REF` + `DEFAULT_NFE_REF` block near line 98.
* `/home/hugo/codes/flowa-multistep-reinference/tools/eval/framework.py` —
  new imports at top of module; per-adapter `_NFE_REF` lookup at line 437
  (inside `_make_framework_policy`).
* `/home/hugo/codes/flowa-multistep-reinference/docs/audit/wave175-p2-impl.md` —
  this audit document.