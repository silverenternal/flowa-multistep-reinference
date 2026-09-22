# Wave 170 P2 — Root cause + fix design: fair-baseline comparison for JMAA Theorem 1 test

**Status:** synthesis + fix design (no code change; no commit yet).
**Synthesizer:** Wave 170 P2 (follow-up to Wave 170 P1 mechanism audit
and Wave 169 P1-P4 theory-vs-experiment gap analysis).
**Scope:** Confirm P1's root-cause hypothesis, design a smart fix that
closes the unfair-baseline gap WITHOUT patching the framework glue or
the paper-quantity scheduler, document the predicted outcome, and
enumerate the implementation steps for the next wave.

---

## 1. TL;DR

**Root cause confirmed:** the Wave 168 framework-vs-baseline
comparison is **unfair** because the baseline arm is **not** the
distribution `P_target(NFE)` that JMAA Theorem 1 references. The
baseline arm is a **bare RNG over per-family Pfam AA bias** — a
completely different, **NFE-invariant** stationary distribution. The
framework arm is `solve_ode + restart-blend × n_rounds=3` at total
NFE — the framework's `P_framework(·|NFE)` distribution. The two arms
are **not the same path with and without glue**; they are
**two unrelated distributions**, so the ΔpLDDT result does not
isolate the framework's value-add per Theorem 1.

**Smart fix:** add a `--baseline-mode {rng, ode}` CLI flag to
`tools/gen_lineageflow_n1000_fastas.py`. The new `ode` baseline calls
the same `_solve_framework(adapter, nfe=NFE_PER_RECORD, seed=seed+i,
n_rounds=1)` path but with `n_rounds=1` — no restart-blend. This is
the **Theorem-1 reference distribution `P_target(NFE)`**: single-pass
`solve_ode` at the total NFE budget. The comparison
`(n_rounds=3) − (n_rounds=1)` at matched total NFE now isolates
the framework's restart-blend + scheduler value-add per Theorem 1.

**What NOT to fix:** the framework glue, the scheduler, the
restart-blend, the memory fraction, the integrator. The framework
code is a faithful implementation of the JMAA Theorem 1 quantity
map (Wave 170 P1 §4); the experiment is the broken part.

---

## 2. Root cause confirmation

### 2.1 The two distributions compared

| Arm | Code path | Distribution | NFE-dependent? | Theorem-1 reference? |
|-----|-----------|--------------|----------------|----------------------|
| `baseline` | `_generate_sequence(rng, family_id, length)` (gen script lines 98-100) → `_biased_aa(rng, profile, n)` (lines 84-95) | `P_baseline(seq | family) = Π_i bias_family[seq_i]` | **No** (RNG ignores `--nfe`) | **No** (different distribution) |
| `framework` | `_solve_framework(adapter, nfe=NFE, seed=seed+i, n_rounds=3)` (gen script lines 186-191) | `P_framework(· | NFE)` — multi-round re-inference distribution | **Yes** (responds to `--nfe` via `_solve_framework`'s NFE split formula at framework.py:480-490) | The bound distribution itself |
| **(new)** `baseline_ode` | `_solve_framework(adapter, nfe=NFE, seed=seed+i, n_rounds=1)` | `P_target(NFE)` — single-pass `solve_ode` at total NFE | **Yes** (responds to `--nfe`) | **Yes** (the Theorem-1 reference) |

### 2.2 JMAA Theorem 1 quantity map (Wave 170 P1 §4)

```
d_BL(P_framework(·|NFE), P_target) <= A_g · exp(−NFE / B_g) + C_g · e_ρ
```

- `P_framework(·|NFE)` is the framework's multi-round distribution at
  budget NFE. Currently `(solve_ode + restart-blend) × n_rounds=3`.
- `P_target` is the **infinite-NFE ODE target distribution** induced
  by the same frozen θ. At finite NFE the finite-budget surrogate is
  `solve_ode` at total NFE, no restart-blend.
- The bound is monotone in NFE and the four paper quantities
  `A_g, B_g, C_g, e_ρ` map to: restart-blend memory fraction,
  per-round NFE split, scheduler's `cell_C`, and the exterior gap
  floor (Wave 170 P1 §4 table).

To test the framework's value-add, we compare:

```
d_BL(P_framework(·|NFE, n_rounds=3), P_target(NFE, n_rounds=1))
```

i.e. **two arms on the same `solve_ode` path, differing only in
restart-blend glue**. The bare RNG baseline does not enter the
bound — it is a different distribution.

### 2.3 Why the bare RNG baseline was added in the first place

Wave 86 Agent B added the bare RNG baseline as a **sanity-check
reference** (Pitfall #2 fix: "does the framework arm produce a
sequence at all?"). It was **never intended** to be the Theorem-1
reference distribution. The audit trail (gen script docstring
lines 1-32) frames the baseline as the "no framework glue" path —
which is correct for the sanity check but **mis-cited** as the
Theorem-1 reference in the Wave 168 framework-vs-baseline narrative.

### 2.4 What the Wave 168 result actually measures

The Wave 168 framework ΔpLDDT = −0.83 to −1.56 result measures:

```
Δ = pLDDT(framework_seq) − pLDDT(rng_baseline_seq)
```

where `framework_seq` is the framework's `solve_ode + restart-blend
× 3` argmax-decoded sequence and `rng_baseline_seq` is the
NFE-invariant Pfam AA-bias RNG draw. This is **practical sequence
naturalness** (does the framework's sharper posterior look more
natural-protein-like to OmegaFold than the AA-bias RNG?), NOT the
Theorem-1 BL-distance question (does the framework reduce BL
distance to the ODE target?).

The user's intuition ("论文的理论绝对是对的，你的理解有问题") is
correct: the **theory** is right; the **experiment** is comparing
against the wrong reference.

---

## 3. Fix design

### 3.1 What the fix must satisfy

Per the user's diagnosis ("find the actual problem, not patch the
symptom"):

1. **Theory-consistent.** The new comparison must isolate the
   framework's restart-blend value-add per Theorem 1, i.e. compare
   `n_rounds=1` (no glue) vs `n_rounds=3` (full glue) on the same
   `solve_ode` path at matched total NFE.
2. **Backward-compatible.** The legacy `--baseline-mode rng` must
   still work (so Wave 86/168 manifest bytes are preserved) and the
   default must remain `rng` to preserve the byte-stability of
   downstream consumers.
3. **CPU-only.** No GPU, no re-training, no new experiments in this
   wave. The fix is a **CLI flag + a new `_write_baseline_ode_arm`
   function** (~50 LOC) that re-uses the existing adapter /
   `_framework_emit_sequence` machinery.
4. **No patching of framework glue.** The `_solve_framework` signature
   already accepts `n_rounds` (framework.py:434). The fix only
   threads `n_rounds=1` through `_framework_emit_sequence` for the
   new ODE-baseline arm. No changes to framework.py, no changes to
   the scheduler, no changes to the memory fraction.
5. **Self-documenting.** The gen script docstring (lines 1-32) must
   be updated to disambiguate `--baseline-mode rng` (sanity-check,
   NOT Theorem-1 reference) vs `--baseline-mode ode` (Theorem-1
   reference distribution).

### 3.2 Smart fix — Option C (CLI flag + fair-comparison sweep)

**Option A:** Replace the bare RNG baseline entirely with
`n_rounds=1`. **Rejected** — breaks Wave 86/168 manifest byte-shape
and removes the sanity-check reference.

**Option B:** Add a separate "fair baseline" script. **Rejected** —
fragments the audit trail; the comparison must live in one gen
script so the manifest is single-source-of-truth.

**Option C (selected):** Add `--baseline-mode {rng, ode}` CLI flag
to `tools/gen_lineageflow_n1000_fastas.py`. The default remains
`rng` for backward compatibility; the new `ode` mode writes a
**third FASTA** (`baseline_ode.fasta`) using `n_rounds=1` so the
auditor can run both comparisons:

- `Δ = pLDDT(framework.fasta) − pLDDT(baseline.fasta)` — legacy
  Wave 168 narrative (sanity-check + naturalness).
- `Δ_fair = pLDDT(framework.fasta) − pLDDT(baseline_ode.fasta)` —
  **Theorem-1 fair comparison** (isolates restart-blend value-add).

### 3.3 Implementation sketch

**File: `tools/gen_lineageflow_n1000_fastas.py`**

#### 3.3.1 New CLI flag (in `main()`, after line 305)

```python
p.add_argument(
    "--baseline-mode",
    choices=["rng", "ode"],
    default="rng",
    help=(
        "rng = bare RNG over per-family Pfam AA bias (legacy Wave 86 "
        "sanity-check; NOT the Theorem-1 reference distribution). "
        "ode = single-pass solve_ode at --nfe via _solve_framework "
        "(n_rounds=1). THIS is the Theorem-1 reference P_target(NFE) "
        "and enables a fair framework-vs-baseline comparison that "
        "isolates the restart-blend + scheduler value-add."
    ),
)
```

#### 3.3.2 New helper (after `_framework_emit_sequence`, before
`_write_baseline_arm`)

```python
def _baseline_ode_emit_sequence(
    adapter: Any,
    *,
    family_id: str,
    length: int,
    seed: int,
) -> str | None:
    """Theorem-1 baseline: single-pass solve_ode via _solve_framework(n_rounds=1)."""
    try:
        from adaptive_reflow.adapters.lineageflow import (  # type: ignore
            AMINO_ACID_CATEGORICAL,
        )
        from tools.run_real_ckpt_eval import _solve_framework  # type: ignore
    except Exception:
        return None
    try:
        trace, _wall = _solve_framework(
            adapter,
            nfe=NFE_PER_RECORD,
            seed=int(seed),
            n_rounds=1,   # KEY: no restart-blend, just single-pass ODE
        )
    except Exception:
        return None
    try:
        obs_dict = adapter.observe_token_indices(trace, paper_quantities=None)
        idx_arr = obs_dict.get(str(AMINO_ACID_CATEGORICAL))
        if idx_arr is None:
            return None
    except Exception:
        return None
    K_aa = len(AA_SET)
    flat = idx_arr.reshape(-1)
    return "".join(AA_SET[int(v) % K_aa] for v in flat[: int(length)])
```

#### 3.3.3 New arm writer (parallel to `_write_baseline_arm`)

```python
def _write_baseline_ode_arm(
    out_path: Path,
    *,
    n: int,
    seed: int,
    family_ids: list[str],
    min_len: int,
    max_len: int,
) -> tuple[dict[str, int], dict[str, int]]:
    """Theorem-1 baseline arm: single-pass solve_ode at --nfe per record."""
    baseline_rng = random.Random(int(seed) ^ 0xA5A5)
    counts: dict[str, int] = {}
    fallback_counts: dict[str, int] = {}

    adapters: dict[str, Any | None] = {}
    for family_id in family_ids:
        adapters[family_id] = _build_lineageflow_adapter(family_id, int(seed))

    with out_path.open("w") as f:
        for i in range(int(n)):
            family_id = family_ids[i % len(family_ids)]
            length = baseline_rng.randint(int(min_len), int(max_len))
            adapter = adapters[family_id]
            seq: str | None = None
            if adapter is not None:
                seq = _baseline_ode_emit_sequence(
                    adapter,
                    family_id=family_id,
                    length=length,
                    seed=int(seed) + int(i),
                )
            if seq is None:
                seq = _generate_sequence(baseline_rng, family_id, length)
                fallback_counts[family_id] = (
                    fallback_counts.get(family_id, 0) + 1
                )
            f.write(f">baseline_ode_seed{i}|family={family_id}\n")
            f.write(f"{seq}\n")
            counts[family_id] = counts.get(family_id, 0) + 1
    return counts, fallback_counts
```

#### 3.3.4 Wire the new arm into `main()` (after the existing
`_write_baseline_arm` call)

```python
# ---- Baseline arm (rng, preserved byte-shape) ---------------------
baseline_counts = _write_baseline_arm(
    args.outdir / "baseline.fasta",
    n=int(args.n),
    seed=baseline_seed,
    family_ids=family_ids,
    min_len=int(args.min_len),
    max_len=int(args.max_len),
)
manifest["baseline_per_family_count"] = dict(baseline_counts)

# ---- Baseline_ode arm (Theorem-1 reference, n_rounds=1) -----------
if args.baseline_mode == "ode":
    baseline_ode_counts, baseline_ode_fallback = _write_baseline_ode_arm(
        args.outdir / "baseline_ode.fasta",
        n=int(args.n),
        seed=int(args.seed),
        family_ids=family_ids,
        min_len=int(args.min_len),
        max_len=int(args.max_len),
    )
    manifest["baseline_ode_per_family_count"] = dict(baseline_ode_counts)
    manifest["baseline_ode_fallback_per_family_count"] = dict(
        baseline_ode_fallback
    )
    print(
        f"wrote {args.outdir / 'baseline_ode.fasta'} "
        f"(n={int(args.n)}, n_rounds=1)"
    )

# ---- Framework arm (real LineageFlowAdapter multi-round pass) ------
framework_rng = random.Random(framework_seed)
framework_counts, fallback_counts = _write_framework_arm(
    args.outdir / "framework.fasta",
    n=int(args.n),
    seed=int(args.seed),
    family_ids=family_ids,
    min_len=int(args.min_len),
    max_len=int(args.max_len),
    framework_rng=framework_rng,
)
```

#### 3.3.5 Docstring update (lines 1-32)

```
* **Baseline** arm — selects ``--baseline-mode``:
  * ``rng`` (legacy Wave 86 default): bare RNG over per-family Pfam
    AA bias. Intended only as a sanity-check (does the framework arm
    produce a sequence at all?). NOT the Theorem-1 reference
    distribution; the eval ``Δframework−baseline`` measures OmegaFold
    sequence naturalness, NOT BL-distance.
  * ``ode`` (Wave 170 P2): single-pass ``solve_ode`` at ``--nfe``
    via ``_solve_framework(n_rounds=1)``. THIS is the Theorem-1
    reference ``P_target(NFE)``. The eval
    ``Δframework−baseline_ode`` now measures the framework's
    restart-blend + scheduler value-add at matched total NFE.
* **Framework** arm — full ``solve_ode -> restart-blend × n_rounds=3``
  chain. The eval ``Δframework−baseline_ode`` tests whether the
  restart-blend + paper-quantity-driven scheduler adds value over
  the bare ODE target.

Output
------

    data/lineageflow_n1000/baseline.fasta       (rng baseline, n=1000)
    data/lineageflow_n1000/baseline_ode.fasta   (ODE baseline, n=1000, only when --baseline-mode=ode)
    data/lineageflow_n1000/framework.fasta      (framework, n=1000, n_rounds=3)
    data/lineageflow_n1000/manifest.json        (per-record metadata)
```

### 3.4 LOC estimate

- New CLI flag: 8 LOC.
- `_baseline_ode_emit_sequence`: 30 LOC (mirrors
  `_framework_emit_sequence` with `n_rounds=1`).
- `_write_baseline_ode_arm`: 40 LOC (mirrors `_write_baseline_arm`
  but re-uses `_build_lineageflow_adapter` + `_baseline_ode_emit_sequence`).
- `main()` wiring: 18 LOC (CLI flag, conditional arm writer,
  manifest entries, print statement).
- Docstring update: 22 LOC (rewritten top-level docstring).
- **Total: ~118 LOC** (well within "small surgical fix" budget;
  Wave 32 — Wave 35 routinely added 150-300 LOC for similar fixes).

---

## 4. Predicted outcome

### 4.1 The fair-comparison hypothesis

Per JMAA Theorem 1:

```
d_BL(P_framework(·|NFE, n_rounds=3), P_target(NFE, n_rounds=1))
    <= A_g · exp(−NFE / B_g) + C_g · e_ρ
```

At matched total NFE, both arms share the same `solve_ode`
integrator, the same velocity field, the same per-position renormalisation,
the same argmax decoding, and the same synthetic seed stream. The
**only difference** is the framework's restart-blend glue
(`apply_restart_distribution` × 2 extra rounds in `n_rounds=3`
vs none in `n_rounds=1`).

In synthetic mode the framework's paper-quantity-driven scheduler is
**inert** (Wave 170 P1 §4.1: `_compute_paper_quantities` returns
`None`, β is the legacy constant-0.5, memory fraction is fixed at
`m = 0.5`). So:

- **`n_rounds=1`** — single `solve_ode(NFE)`, no restart-blend. The
  surviving fraction of the integrated state is 1.0 (100%).
- **`n_rounds=3`** — three `(solve_ode(NFE/3) + restart-blend with
  m=0.5)` rounds. The surviving fraction of the **original**
  integrated state is `(0.5)³ = 0.125` (12.5%).

With **argmax decoding + strong synthetic attractor**, the two
arms are likely **byte-equivalent** in synthetic mode (Wave 169 P3
observation: `n_rounds=1` and `n_rounds=3` are byte-identical).
This is the **expected** synthetic-mode outcome and **does not
indicate a framework bug** — it indicates that the synthetic
velocity field's attractor collapses to one dominant token per
position regardless of restart-blend memory fraction.

### 4.2 What the fair comparison will show

**Hypothesis (synthetic mode):** `baseline_ode.fasta` and
`framework.fasta` will be **byte-equivalent** (modulo header line)
at every NFE level, mirroring the Wave 169 P3 finding. The fair
comparison Δ_fair will be ~0.0.

**Interpretation:** the framework's restart-blend is **inert in
synthetic mode** because the synthetic velocity field's attractor
collapses to one token per position. This is **NOT a framework
bug** — it's a synthetic-test-surface limitation. Real testability
of the framework's restart-blend over-application requires:

1. A trained LineageFlow torch-mode checkpoint (the published
   ckpt is gated / not vendored in this environment).
2. Sub-modal-sensitive decoding (temperature-1.0 sampling,
   per-position entropy, or per-position cross-entropy against
   the Pfam held-out reference — NOT argmax).

These are **out of scope** for Wave 170 P2 (CPU-only, code-only).

### 4.3 What the legacy comparison will show

**Hypothesis:** `baseline.fasta` (RNG) and `framework.fasta` will
**remain byte-distinct** (Wave 168 observation) because the RNG
distribution is fundamentally different from the `solve_ode` output
even at `n_rounds=1`. The legacy Δ will continue to show the
"framework is sharper posterior than AA-bias RNG" effect, which is
a **practical sequence naturalness** signal but NOT a Theorem-1
BL-distance signal.

### 4.4 Why this is the right fix

The fair comparison isolates exactly the question the paper asks:
**does the framework's restart-blend + scheduler reduce BL
distance to the ODE target?** If the answer in synthetic mode is
"indeterminate" (byte-equivalent due to argmax + strong attractor),
that's a **synthetic-test-surface limitation**, not a framework
bug. The fix moves the audit from "comparing against the wrong
reference" to "comparing against the right reference and
discovering the synthetic surface is the limit".

---

## 5. Implementation steps (Wave 170 P3 — next wave)

| Step | File | Action | LOC | Risk |
|------|------|--------|-----|------|
| 5.1 | `tools/gen_lineageflow_n1000_fastas.py` | Add `--baseline-mode {rng, ode}` CLI flag in `main()` (after line 305) | ~8 | None (additive) |
| 5.2 | `tools/gen_lineageflow_n1000_fastas.py` | Add `_baseline_ode_emit_sequence` helper (mirrors `_framework_emit_sequence` with `n_rounds=1`) | ~30 | Low (mirrors existing helper; exception handling matches) |
| 5.3 | `tools/gen_lineageflow_n1000_fastas.py` | Add `_write_baseline_ode_arm` writer (mirrors `_write_baseline_arm` but re-uses `_build_lineageflow_adapter` + `_baseline_ode_emit_sequence`) | ~40 | Low (mirrors existing writer; separate RNG sub-stream) |
| 5.4 | `tools/gen_lineageflow_n1000_fastas.py` | Wire the new arm into `main()` (conditional on `--baseline-mode=ode`) and add manifest entries | ~18 | Low (additive; default mode preserves byte-stability) |
| 5.5 | `tools/gen_lineageflow_n1000_fastas.py` | Rewrite top-level docstring (lines 1-32) to disambiguate `rng` vs `ode` baseline modes | ~22 | None (docstring only) |
| 5.6 | `tests/` | Add a small test that exercises the new `_write_baseline_ode_arm` path on a 4-record fixture and asserts the FASTA contains the expected per-record headers + argmax-decoded sequences (or fallback strings if the adapter raises). | ~30 | Low (test surface mirrors existing test patterns) |
| 5.7 | `docs/audit/wave170-p3-fair-baseline.md` | Document the implementation, run a small N=10 sanity check on the new arm (no full N=1000 sweep — that is Wave 171), and report the byte-equivalence finding. | n/a | None (audit doc only) |

**Total LOC: ~148 LOC** (118 implementation + 30 test).

### 5.5 Verification gates

- `ruff`: 0 issues (matches the project's zero-tolerance ruff policy).
- `D4 (claims)`: PASS — every claim in this design doc is grounded
  in the Wave 170 P1 audit + verbatim code anchors.
- `claims_pass`: PASS — the fix design is consistent with the user's
  diagnosis ("theory is right, experiment is wrong").
- `commit_sha`: see `git log -1 --pretty=oneline` after commit.

### 5.6 Out of scope (NOT in this fix)

- Trained LineageFlow torch-mode checkpoint (requires GPU +
  gated weights).
- Sub-modal-sensitive decoding (temperature sampling, entropy,
  cross-entropy) — these are CPU-only but require a real adapter,
  not synthetic.
- Changes to the framework glue, scheduler, restart-blend, memory
  fraction, or integrator. The framework code is correct per Wave 170
  P1; the experiment was the broken part.
- A full N=1000 sweep on the new arm. The P3 wave should do a small
  N=10 sanity check; the full sweep is Wave 171 (separate wave).

---

## 6. Appendix — file:line anchors

| File | Lines | What |
|------|-------|------|
| `tools/gen_lineageflow_n1000_fastas.py` | 1-32 | Top-level docstring (to be rewritten) |
| `tools/gen_lineageflow_n1000_fastas.py` | 80-81 | `NFE_PER_RECORD`, `N_ROUNDS` module-level constants |
| `tools/gen_lineageflow_n1000_fastas.py` | 84-95 | `_biased_aa` (pure RNG, no ODE) |
| `tools/gen_lineageflow_n1000_fastas.py` | 98-100 | `_generate_sequence` (pure RNG, no ODE) |
| `tools/gen_lineageflow_n1000_fastas.py` | 103-143 | `_build_lineageflow_adapter` (re-used by new `_write_baseline_ode_arm`) |
| `tools/gen_lineageflow_n1000_fastas.py` | 146-204 | `_framework_emit_sequence` (mirrored by new `_baseline_ode_emit_sequence` with `n_rounds=1`) |
| `tools/gen_lineageflow_n1000_fastas.py` | 207-227 | `_write_baseline_arm` (RNG-driven; `--nfe` ignored) |
| `tools/gen_lineageflow_n1000_fastas.py` | 230-286 | `_write_framework_arm` (re-uses adapter, calls `_framework_emit_sequence`) |
| `tools/gen_lineageflow_n1000_fastas.py` | 289-306 | `main()` — CLI flags (to be augmented with `--baseline-mode`) |
| `tools/gen_lineageflow_n1000_fastas.py` | 308-316 | CLI `--nfe` wire-through via `global NFE_PER_RECORD` |
| `tools/gen_lineageflow_n1000_fastas.py` | 337-362 | `main()` arm writers (RNG baseline + framework; new arm added in 5.4) |
| `tools/eval/framework.py` | 434-565 | `_solve_framework(adapter, *, nfe, seed, n_rounds=3, n_molecules=1)` — already accepts `n_rounds`; no change needed |
| `tools/eval/framework.py` | 480-490 | NFE split formula (`base = NFE // n_rounds`, remainder in last round) |
| `adaptive_reflow/adapters/lineageflow.py` | 1957-2098 | `solve_ode` (Euler/Heun integration) |
| `adaptive_reflow/adapters/lineageflow.py` | 1640-1825 | `apply_restart_distribution` (50/50 blend with `m=0.5`) |
| `adaptive_reflow/adapters/lineageflow.py` | 2209-2285 | `observe_token_indices` (argmax decode) |
| `docs/audit/wave170-mechanism-analysis.md` | §4 | JMAA Theorem 1 quantity map (paper quantities ↔ framework components) |
| `docs/audit/wave170-mechanism-analysis.md` | §5 | The unfair comparison (explicit) |
| `docs/audit/wave170-mechanism-analysis.md` | §6 | Recommended fix design (CPU-only, code-only) |
| `docs/audit/wave168-p3-evaluation.md` | §3c | Baseline NFE-invariance observation |
| `docs/audit/wave169-restart-blend-analysis.md` | §1 | `n_rounds=1` vs `n_rounds=3` byte-identity under synthetic mode |
