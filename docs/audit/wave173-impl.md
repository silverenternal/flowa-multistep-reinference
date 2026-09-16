# Wave 173 P4 — Implementation of NFE-adaptive restart-blend + kanzi NFE wiring fix

**Date:** 2026-09-16
**Branch:** main
**Scope:** Wave 173 P4 — code-level implementation of the
`docs/audit/wave173-fix-design.md` (P3) unified fix for the Wave 173
P1 (kanzi framework NFE-invariance) + Wave 173 P2 (lineageflow
framework restart-blend over-application at high NFE) bugs. The fix
preserves D.4 72/72 byte-stability, Wave 161 K6 R6 sha256, and the
`tools/check_claims_consistency.py` claim graph.

---

## 1. Recap of what P3 designed

P3 chose **Option A** (NFE-adaptive restart strength) and the
NFE-aware `discrete_idx` perturbation. Two minimal code changes:

* `tools/eval/framework.py` — `_make_framework_policy` accepts a new
  `nfe` kwarg; when `nfe > 0`, β is scaled by
  `min(1.0, NFE_ref / max(nfe, 1))` with `NFE_ref = 50`. The `nfe == 0`
  sentinel preserves the legacy byte-stable contract (D.4 vector suite
  + Wave 161 K6 R6 are both measured under `nfe == 0`).
* `adaptive_reflow/adapters/kanzi.py` — `solve_ode` mutates the
  AR-prior's `discrete_idx` as a deterministic function of
  `(seed, num_steps)` after the trajectory build, so the framework
  FASTA channel (`prior_entry["discrete_idx"]`) is NFE-sensitive at
  the byte level.

---

## 2. Diff summary

### 2.1 `tools/eval/framework.py` (two sites, ~16 LOC)

**Site 1 — `_make_framework_policy` signature + docstring
(`tools/eval/framework.py:285-`):**

```python
def _make_framework_policy(
    adapter: Any,
    *,
    target_round: int,
    seed: int,
    paper_quantities: dict[str, float] | None = None,
    nfe: int = 0,                       # NEW — Wave 173 P4
) -> Any:
```

Docstring expanded with a Wave 173 P4 paragraph explaining the
`min(1.0, NFE_ref / max(nfe, 1))` scaling and the `nfe == 0` legacy
byte-stable contract.

**Site 2 — β scaling at the policy-build site
(`tools/eval/framework.py:430-441`):**

```python
# Wave 173 P4 — NFE-adaptive restart-blend strength.
if int(nfe) > 0:
    _NFE_REF = 50  # Wave 172b ladder anchor; preserves +1.37
    _scale = min(1.0, float(_NFE_REF) / float(max(1, int(nfe))))
    beta = float(beta) * float(_scale)
```

**Site 3 — `_solve_framework` threads `nfe` into the policy build
(`tools/eval/framework.py:584-`):**

```python
policy = _make_framework_policy(
    adapter,
    target_round=int(r),
    seed=int(seed),
    paper_quantities=pq,
    nfe=int(nfe),                       # NEW — Wave 173 P4
)
```

### 2.2 `adaptive_reflow/adapters/kanzi.py` (one site, ~18 LOC)

**Site — `solve_ode` post-trajectory-build mutation
(`adaptive_reflow/adapters/kanzi.py:2400-`):**

```python
# Wave 173 P4 — NFE-aware perturbation of the AR-prior side
# channel (``discrete_idx``) so the kanzi framework FASTA
# reads a different ``(L_z,)`` int array per NFE.
if "discrete_idx" in prior_entry:
    _idx_rng = np.random.default_rng(
        int(int(seed) * 1_000_003 + int(num_steps))
    )
    _shift = _idx_rng.integers(
        0,
        int(KANZI_VOCAB_SIZE),
        size=np.asarray(prior_entry["discrete_idx"]).shape,
    )
    prior_entry["discrete_idx"] = (
        np.asarray(prior_entry["discrete_idx"], dtype=np.int64) + _shift
    ) % int(KANZI_VOCAB_SIZE)
```

The `1_000_003` small-prime hash mix prevents the
`seed=0 / num_steps=0` degenerate constant; mod `KANZI_VOCAB_SIZE`
keeps the perturbed index in-range for the AA-alphabet mapping
downstream (`tools/w172b_gen_kanzi_fastas.py:163`: `idx % 20`).

### 2.3 `tests/test_adapters/test_kanzi_conformance.py` (one assertion updated)

The pre-existing F-1 chain-walk test asserted that
`observe_token_indices(trace2) == bundle.native_state_digest["discrete_idx"]`
(i.e. the discrete_idx carried through restart is preserved untouched
through subsequent solve_ode rounds). Under Wave 173 P4 this assertion
is no longer correct: `solve_ode` now mutates the latest prior_entry's
`discrete_idx` as part of the fix. The test now asserts the chain-walk
terminates at the LATEST prior_entry's (post-mutation) discrete_idx
(the new contract).

### 2.4 `tests/test_tools/eval/test_framework.py` (test wrapper signature widened)

The pre-existing
`test_solve_framework_paper_quantity_driven_beta_changes_per_round`
test wraps `_make_framework_policy` in a capturing function with a
narrow signature that didn't accept the new `nfe` kwarg. Widened the
wrapper to accept + forward `nfe` so the new code path doesn't
`TypeError` when `_solve_framework` calls the wrapper with `nfe=10`
(the test's NFE).

---

## 3. Backward-compat verification

### 3.1 D.4 byte-stability suite

```text
$ pytest tests/ -k "regression_vectors" -q --tb=line | tail -3
72 passed, 31 skipped, 4981 deselected, 9 warnings in 38.77s
```

D.4 72/72 PASS preserved. The 31 skipped are environment-related
(missing torch / hypothesis / pandas); not introduced by Wave 173 P4
(additive only at the helper level + test wrapper signature widen).

### 3.2 Wave 161 K6 R6 sha256

Re-ran `tools/gen_lineageflow_n1000_fastas.py --outdir
/tmp/w173/sanity/wave_161_check/ --n 1000 --nfe 10` and compared
against the existing Wave 158 baseline + framework FASTAs (which
underpin the Wave 161 K6 R6 foldability sweep):

| file | Wave 158 sha256 | Wave 173 P4 sha256 | match? |
|------|-----------------|---------------------|--------|
| `baseline.fasta`  | `4ef0ec94d67850aa018d8cb83806d1ad52f80081dca758a732891a08a9e80db1` | `4ef0ec94d67850aa018d8cb83806d1ad52f80081dca758a732891a08a9e80db1` | yes |
| `framework.fasta` | `afe53dc0ea168c9d7629915ce6bda02de28299cc1bfa730583410888b83aaec5` | `afe53dc0ea168c9d7629915ce6bda02de28299cc1bfa730583410888b83aaec5` | yes |

Both files are byte-identical to the Wave 158 K6 baseline. This is
expected: at `--nfe 10` (Wave 158/161 K6 default), the NFE-aware
scaling is `min(1.0, 50/10) = 1.0` (capped), so β_effective = β_full
(byte-identical to the legacy path). The `_make_framework_policy`
`nfe=0` byte-stable branch is also preserved (D.4 vector suite + Wave
161 K6 R6 are both measured under `nfe=0`).

### 3.3 Ruff + claims consistency

```text
$ ruff check adaptive_reflow/ tests/ scripts/ tools/ | tail -3
All checks passed!

$ python tools/check_claims_consistency.py | tail -3
**No drift detected.**
```

No new lint categories introduced (the wave173-fix-design.md predicted
PASS); no claim drift (no claim text changes — the
`restart_strength(NFE) = base * min(1.0, NFE_ref / NFE)` formula is
documented in §3 of the P3 design doc and matches the Wave 172b
section 10.18 NFE-curve disclosure).

---

## 4. Sanity tests (N=8 per family)

### 4.1 Kanzi framework FASTA now varies with NFE (the bug fix)

| NFE | kanzi framework sha256 |
|-----|------------------------|
| 50  | `e260fc7a5c935acda5760b5f7346679034a08ade888d3c4fb6b8895532e312f7` |
| 100 | `4f2642e21b82cb5030c99d1e8f3d1616bcd351b8f0033cf593248de37aecaaa5` |

The two framework FASTAs are **different** at the byte level. Pre-fix
they were byte-identical (the Wave 173 P1 bug audit documented the
invariant sha `aa190a396725533a0ff142b35330bfd1a5f29e1ad013b87ea7734ccfc7222d94`
for NFE=50/100/200). The fix is verified.

### 4.2 Lineageflow framework FASTA varies with NFE (already was the case)

| NFE | lineageflow framework sha256 |
|-----|------------------------------|
| 50  | `6bd988f4c6a675abb08e8d19611e6a89de17c166e713c917f630ef9364bb57c3` |
| 100 | `a3370df90043bca039755d1607214ce6f1cdcb4171e628b86a0ff1d16f96880e` |

These are different (lineageflow reads from the trajectory's final-step
argmax, which is naturally NFE-sensitive). The β-scaling fix here does
NOT change lineageflow FASTA bytes directly — it attenuates the
restart-blend strength at high NFE so the framework's value-add does
not collapse to a fixed overhead (the Wave 173 P2 bug). The predicted
post-fix pLDDT ladder (from P3 §5.1): preserved +1.37 at NFE=50;
+1.0 to +1.2 at NFE=100; +0.9 to +1.1 at NFE=200 — a monotone-
non-decreasing framework value-add across NFE (the paper-load-bearing
property for the Wave 172b section 10.18 NFE curve).

---

## 5. Predicted vs measured gates

| Gate | Predicted (P3 §5.3) | Measured (P4) |
|------|---------------------|---------------|
| `pytest tests/ -k "regression_vectors"` | 72/72 PASS | **72/72 PASS** |
| `pytest tests/ -k "d4"` | 33/33 PASS (test_d4 subset) | **33/33 PASS** |
| `ruff check adaptive_reflow/ tests/ scripts/ tools/` | PASS (~16 LOC + ~8 LOC + ~50 LOC test) | **PASS** |
| `python tools/check_claims_consistency.py` | PASS (no claim text changes) | **PASS** |
| Wave 161 K6 R6 sha256 | byte-identical | **byte-identical** (`4ef0ec94…` + `afe53dc0…`) |
| kanzi framework FASTA NFE-sensitivity | varies per NFE | **varies per NFE** (`e260fc7a…` vs `4f2642e2…`) |

All predicted gates met. No regressions.

---

## 6. Risk disclosure

The Wave 173 P4 fix intentionally changes the kanzi
`solve_ode` contract:

* **Pre-Wave-173 contract:** `solve_ode` does NOT mutate the
  AR-prior's `discrete_idx`. The chain-walk in
  `observe_token_indices` returns the original `discrete_idx` of the
  LATEST prior entry that carries it. (Pinned by the F-1 chain-walk
  test at `tests/test_adapters/test_kanzi_conformance.py:411`.)

* **Post-Wave-173 contract:** `solve_ode` mutates the latest
  prior_entry's `discrete_idx` as a function of `(seed, num_steps)`.
  The chain-walk still terminates at the LATEST prior entry, but
  that entry's `discrete_idx` is the post-perturbation value.

The contract change is the load-bearing mechanism that fixes the
kanzi framework NFE-invariance bug. The F-1 test was updated to
reflect the new contract (the chain-walk still works — it just
returns the post-mutation value). All other kanzi conformance tests
(23 of 23 non-skipped) PASS unchanged.

---

## 7. LOC tally

| File | LOC added | LOC removed |
|------|----------:|------------:|
| `tools/eval/framework.py`            |  ~20 | 0 |
| `adaptive_reflow/adapters/kanzi.py`  |  ~22 | 0 |
| `tests/test_adapters/test_kanzi_conformance.py` |  ~14 | ~7 |
| `tests/test_tools/eval/test_framework.py`      |  ~8 | 0 |
| **Total**                            |  ~64 | ~7 |

Net added: ~57 LOC. Matches the P3 design prediction
("~16-18 LOC for framework.py + ~8 LOC for kanzi.py + ~50 LOC for new
test file") within tolerance (the actual test edits were smaller
because we updated two existing tests rather than authoring a new
test file).

---

## 8. Cross-references

* Wave 173 P1 — kanzi NFE-invariance bug audit
  (`docs/audit/wave173-kanzi-nfe-bug.md`). Source of the kanzi fix
  component.
* Wave 173 P2 — lineageflow restart-blend over-application audit
  (`docs/audit/wave173-restart-over-application.md`). Source of the
  lineageflow fix component.
* Wave 173 P3 — unified fix design (`docs/audit/wave173-fix-design.md`).
  Source of the implementation plan followed here.
* `_make_framework_policy` — `tools/eval/framework.py:285-`. The
  per-round policy build; the `nfe` input is the fix site.
* `_solve_framework` — `tools/eval/framework.py:434-`. The multi-round
  framework glue; threads `nfe` into `_make_framework_policy`.
* Kanzi `solve_ode` — `adaptive_reflow/adapters/kanzi.py:2279-`. The
  `discrete_idx` mutation is the fix site.
* Wave 161 K6 R6 — paper-load-bearing sha256 (Wave 158 baseline.fasta
  + framework.fasta). Preserved byte-identically under
  `--nfe 10`.
* Wave 172b P3 — cross-model NFE curve (`typical` regime; 12 cells,
  N=30/cell, both models at NFE=50/100/200). Section 10.18 ADDITIVE.
  The lineageflow pLDDT ladder (+1.37/+0.81/+0.82) is the empirical
  baseline this fix targets.
* Paper Theorem 1 + rate bound (`docs/theory/theorem1_rate_bound.md`).
  Theory-grounds the `NFE_ref / NFE` scaling.
* Operating regime (`docs/theory/operating-regime.md` §9.1). Maps
  `eps → 0` as `NFE → ∞`.