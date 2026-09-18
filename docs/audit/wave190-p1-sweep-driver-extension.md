# Wave 190 P1 — sweep-driver extension (n=30 paired sweep on kanzi + lineageflow)

**Date:** 2026-09-18
**Branch:** main
**Commit:** (this commit)
**Scope:** Extend the Wave 189 P4 ablation driver
(``scripts/wave189_p4_theorem_load_bearing_kanzi.py``) so the
Theorem 1 load-bearing ablation can run as a **paired n=30 sweep**
on **both** the kanzi adapter (Wave 36 protein axis, synthetic mode,
``state_shape=(64, 64)``) and the LineageFlow adapter (Wave 10 protein
axis, synthetic mode, ``state_shape=(256, 33)`` per the Wave 188 P1
ground truth). The n=3 cells from Wave 189 P4 (seeds ``{0, 1, 2}``)
are preserved as a "n=3 sub-experiment" inside the new n=30 JSON so
the paper can diff cell-by-cell and verify byte-stability with the
baseline.

---

## 1. What was extended

A new script,
``scripts/wave190_p1_theorem_load_bearing_extended.py``, supersedes
the kanzi-only path with:

| CLI flag | Default | Purpose |
|---|---|---|
| ``--n-seeds`` | ``30`` | Number of paired seeds (range ``[0, n_seeds)``). |
| ``--seeds`` | (unset) | Optional comma-separated seed list (overrides ``--n-seeds``). |
| ``--adapter`` | ``kanzi`` | ``kanzi``, ``lineageflow``, or ``both``. |
| ``--n-rounds`` | ``5`` | Framework rounds per cell. |
| ``--nfe`` | ``1000`` (kanzi) / ``100`` (lineageflow) | Per-pass NFE budget. Per-adapter defaults match the adapter's canonical state-size scaling (kanzi is 8x smaller on the latent, lineageflow's ``state_shape=(256, 33)`` matches the published Pfam-RP55 NFE ladder). |

The new script **imports** the Wave 189 P4 solver helpers
(``_solve_baseline``, ``_solve_framework``,
``_extract_endpoint_latent``, ``_per_position_entropy_reduction``,
``_aggregate``, ``_implication``) via
``importlib.util.spec_from_file_location`` so the n=3 continuity
cells are byte-identical to the baseline. No factory was duplicated.

Per-adapter adapters:

* **kanzi** — ``adaptive_reflow.adapters.kanzi.default_kanzi_adapter(force_mode="synthetic")``
  (state_shape ``(64, 64)``, ``LINEAGEFLOW_NUM_STEPS_DEFAULT=1000`` for
  the synthetic field's NFE ladder).
* **lineageflow** — ``adaptive_reflow.adapters.lineageflow.default_lineageflow_adapter(force_mode="synthetic")``
  (state_shape ``(256, 33)`` per Wave 188 P1 ground truth; canonical
  ``LINEAGEFLOW_NUM_STEPS_DEFAULT=100``).

The lineageflow path is the **first n=3 sub-experiment on the
LineageFlow adapter** for the Theorem 1 load-bearing ablation — the
Wave 189 P4 baseline has no lineageflow row, so the
``continuity_check`` reports
``"no Wave 189 P4 baseline exists for adapter_kind='lineageflow'"``
on lineageflow and that is the **correct** behaviour (the n=3
sub-experiment IS the first n=3 baseline on that adapter).

---

## 2. Smoke test results (kanzi, n=6)

The smoke-test invocation is:

```bash
python scripts/wave190_p1_theorem_load_bearing_extended.py \
    --adapter kanzi --n-seeds 6
```

This writes ``verification_outputs/wave190-p2-kanzi-n6-smoke.json``.

| Metric | Value |
|---|---|
| ``n_records`` | 6 |
| ``seeds`` | ``[0, 1, 2, 3, 4, 5]`` |
| ``adapter_kind`` | ``kanzi`` |
| ``nfe`` | 1000 |
| ``n_rounds_framework`` | 5 |
| ``verdict`` | ``load_bearing`` (at n=6 the 29-paper-quantity L2 axis signal crosses the 0.05 p-value threshold that the n=3 baseline could not) |
| ``p_value_with_vs_without_quantities`` | 0.0028 |
| ``p_value_l2_axis`` | 0.0023 |
| ``effect_size.entropy_axis`` | -12.20 |
| ``effect_size.l2_axis`` | 45.08 |
| ``framework_no_paper_quantities.mean_endpoint_l2_vs_baseline.mean`` | 97.51 (cosine baseline perturbs the latent ~97 backbone-coord units in Euclidean space) |
| ``framework_with_paper_quantities.mean_endpoint_l2_vs_baseline.mean`` | 0.46 (paper-quantity scheduler barely moves it) |
| Wallclock | ~3 s for all 6 cells |

The n=3 continuity check (seeds ``{0, 1, 2}``) correctly flags
``all_match_within_tolerance=False`` because the smoke test ran with
``n_rounds=5`` (the Wave 190 P1 default) while the Wave 189 P4 baseline
ran with ``n_rounds=3``. This is **expected behaviour, not a bug** —
the continuity check is meant to surface byte-stability regressions
when the **same args** are used; an args-difference check would be
tautological. To verify byte-identity:

```bash
python scripts/wave190_p1_theorem_load_bearing_extended.py \
    --adapter kanzi --seeds "0,1,2" --n-rounds 3 --nfe 1000 \
    --output /tmp/wave190_continuity_test.json
```

This returns ``n_match=3 / n_total_compared=3`` with ``rel_diff=0.00e+00``
on every key — i.e. the solver is byte-identical when args match the
Wave 189 P4 baseline.

---

## 3. Per-adapter output paths

For the production n=30 sweep:

```bash
python scripts/wave190_p1_theorem_load_bearing_extended.py \
    --adapter both --n-seeds 30
```

writes:

* ``verification_outputs/wave190-p2-kanzi-n30.json`` (Wave 190 P2 — kanzi n=30 paired sweep, with the n=3 sub-experiment cells sliced from seeds ``{0, 1, 2}`` and a ``continuity_check`` against ``wave189-p4-theorem-load-bearing-kanzi.json``).
* ``verification_outputs/wave190-p3-lineageflow-n30.json`` (Wave 190 P3 — lineageflow n=30 paired sweep, the first n=3 sub-experiment on this adapter).

Both JSONs follow the Wave 189 P4 schema (``configurations``,
``effect_size``, ``p_value_*``, ``verdict``, ``cells``, etc.) so they
are diffable cell-by-cell with the original baseline.

---

## 4. Verdict schema unification

The Wave 189 P4 verdict carve-out for the n=3 case
(``load_bearing_only_on_axis_endpoint_l2_marginal_n3``) is renamed to
``load_bearing_only_on_axis_endpoint_l2_marginal`` when ``n_records>=10``
so the schema is uniform across n. The verbatim
``_marginal_n3`` label is preserved on the n=3 sub-experiment's
``continuity_check.baseline_summary.verdict`` field for byte-stable
diff with the Wave 189 P4 baseline.

---

## 5. Honesty disclosure

Same constraint as Wave 188 P3 / Wave 189 P4:

* kanzi has **no public torch ckpt** in this environment (probed
  upstream: HF empty, GitHub releases empty, recursive tree code-only
  — see ``data/kanzi_ckpt/README.md``).
* lineageflow has **no public torch ckpt** reachable in this
  environment (the ``lineageflow-rp55.ckpt`` is a 9.788 GB
  PyTorch-Lightning zip archive gated on a CUDA host with ``torch>=2.1``
  + the upstream ``core`` source repo, both of which are missing per
  Wave 10 / Wave 39 / Wave 45). The lineageflow synthetic mode is
  the canonical ``synthetic`` shim.

Both adapters therefore run in ``force_mode="synthetic"``. The
paper-metric axis (``reconstruction_kabsch_rmsd_A``) is
``BLOCKED_no_torch`` on both. The entropy axis is reported instead.

---

## 6. Files added / changed

| Path | Change |
|---|---|
| ``scripts/wave190_p1_theorem_load_bearing_extended.py`` | new — multi-adapter paired sweep driver |
| ``verification_outputs/wave190-p2-kanzi-n6-smoke.json`` | new — smoke-test JSON (kanzi n=6, ~3 s wall) |
| ``docs/audit/wave190-p1-sweep-driver-extension.md`` | new — this audit doc |

The original ``scripts/wave189_p4_theorem_load_bearing_kanzi.py`` is
untouched; the new script imports its helpers via
``importlib.util``.