# Wave 83 Agent B — Kanzi codebook metrics wrapper implementation

**Date:** 2026-09-08
**Repo:** `/home/hugo/codes/flowa-multistep-reinference`
**Scope:** Implement `tools/paper_metrics_kanzi.py` — the Wave 83 Agent A
spec'd wrapper that surfaces the **5 missing Kanzi paper codebook
metrics** on top of the FSQ codebook output of the Kanzi upstream
``DAE.encode()``. Plus the 6th metric
(``reconstruction_kabsch_rmsd_A``) re-exported from the Wave 79
driver so the full 6-metric Kanzi paper suite is reachable through
one import.

**Status:** COMPLETE. All 11 new tests pass; D.4 byte-stable regression
33/33 PASS.

---

## 1. What was delivered

### 1.1 `tools/paper_metrics_kanzi.py` (~510 LOC, well above the 205-LOC
estimate because the module is **numpy-first + comprehensive
docstrings + Wave-79 driver delegation + smoke CLI** — the 205-LOC
figure was a "math + minimal scaffolding" estimate).

Public surface (mirrors the Wave 75 ``tools/paper_metrics.py`` FlowMol3
pattern):

* ``compute_codebook_entropy(idx_BL, vocab_size=4096)`` — Shannon
  entropy of the codebook usage histogram (base 2 bits). Matches
  upstream ``codebook_metrics`` at
  ``data/kanzi_upstream/src/kanzi/train_cb.py:113-117``.
* ``compute_codebook_perplexity(idx_BL, vocab_size=4096)`` —
  ``2 ** entropy`` (= effective vocab size). Matches upstream
  ``train_cb.py:117``.
* ``compute_codebook_js_distance(idx_BL, vocab_size=4096)`` —
  Jensen-Shannon distance for the deterministic ``(0, 1)`` batch
  pair. Returns ``sqrt(JS)`` in ``bits^0.5``. Matches upstream
  ``train_cb.py:102-110`` + ``119-127``. The ``(0, 1)`` pair fix is
  the byte-stable replacement for upstream's ``random.uniform``
  pair-pick.
* ``compute_codebook_utilization(idx_BL, vocab_size=4096)`` —
  fraction of codebook cells used. Matches upstream
  ``estimate_loss`` ``test/cb/utilization`` at
  ``train_cb.py:321``.
* ``compute_codebook_hamming_rotation_invariance(coords, encoder,
  n_rot=2, seed=0, vocab_size=4096)`` — per-position Hamming equality
  across ``n_rot / 2`` uniform-rotation pairs per backbone. Matches
  upstream ``estimate_loss`` ``test/cb/hamming`` at
  ``train_cb.py:309-322``. The seeded ``numpy.random.Generator`` is
  the byte-stable replacement for upstream's ``random.uniform``
  rotation sampler.
* ``compute_all_codebook_metrics(idx_BL, ...)`` — aggregator that
  returns a ``CodebookMetricsResult`` (frozen dataclass) with all 5
  fields.
* ``compute_reconstruction_kabsch_rmsd_A(...)`` — thin wrapper that
  delegates to ``tools.upstream_eval.run_kanzi_upstream_eval`` for
  the Wave 79 reconstruction-RMSD metric. This gives the full
  6-metric Kanzi paper suite reachable through one module.
* ``kanzi_available()`` — host check (mirrors
  ``flowmol3_metrics_upstream.is_upstream_available``).
* ``KANZI_DEFAULT_VOCAB_SIZE = 4096`` — default FSQ vocab size for the
  published Wave 36 Kanzi checkpoint (``levels = (8, 8, 8, 8)``).
* ``--smoke`` CLI surface for synthetic + optional-real-ckpt runs.

### 1.2 `tests/test_tools/test_paper_metrics_kanzi.py` (~430 LOC)

11 tests:

* 5 unit tests, one per metric (``test_entropy_uniform_distribution``,
  ``test_entropy_collapsed_distribution``,
  ``test_perplexity_uniform_and_collapsed``,
  ``test_js_distance_deterministic_pair_byte_stable``,
  ``test_utilization_full_and_partial``,
  ``test_hamming_rotation_invariance_identity_encoder``).
* 2 aggregator tests (``test_aggregator_returns_all_5_keys``,
  ``test_aggregator_byte_stable``).
* 1 availability test (``test_kanzi_available_returns_bool``).
* 1 reconstruction-wrapper test
  (``test_compute_reconstruction_kabsch_rmsd_A_handles_missing_kanzi``).
* 1 end-to-end integration test on the 4 demo PDBs
  (``test_paper_metrics_kanzi_end_to_end_on_4_demo_pdbs``).

All tests pass without the upstream Kanzi ckpt — the encoder for the
end-to-end smoke is a deterministic SHA-256-based hash stub.

---

## 2. Per-metric formula + paper alignment

### 2.1 ``codebook_entropy``

```
counts[i] = sum over (b, l) of 1{idx[b, l] == i}      for i in [0, V)
probs[i]  = counts[i] / sum(counts)
entropy   = -sum_i probs[i] * log2(probs[i])           (clamp_min(1e-12))
```

Range: ``[0, log2(V)]``. For ``V=4096`` (Wave 36 ckpt
``levels = (8, 8, 8, 8)``), upper bound = **12 bits**. Reference:
``data/kanzi_upstream/src/kanzi/train_cb.py:113-117``.

### 2.2 ``codebook_perplexity``

```
perplexity = 2 ** entropy
```

Range: ``[1.0, V]``. Reference: ``train_cb.py:117``.

### 2.3 ``codebook_js_distance``

```
counts_a = bincount(idx[0], minlength=V)
counts_b = bincount(idx[1], minlength=V)
pa = counts_a / counts_a.sum()
pb = counts_b / counts_b.sum()
m  = 0.5 * (pa + pb)
KL(p, q) = sum_i p[i] * log2(p[i] / q[i])          (clamp_min(1e-12))
JS(pa, pb) = 0.5 * KL(pa, m) + 0.5 * KL(pb, m)
js_distance = sqrt(JS(pa, pb))                      # in bits^0.5
```

Range: ``[0, 1]`` bits^0.5 (JS upper bound for two disjoint uniform
distributions over a shared alphabet). Reference:
``train_cb.py:102-110`` + ``119-127``.

**Determinism fix vs upstream:** upstream picks the (a, b) pair via
``random.uniform(0, 1) * B`` (``train_cb.py:121-122``). We fix the
pair to ``(0, 1)`` so the metric is byte-stable across re-runs. The
divergence from upstream is documented in the docstring (the upstream
"pick a random pair from batch" comment is descriptive, not
contractual).

### 2.4 ``codebook_utilization``

```
unique_codes = unique(idx.flatten())
utilization  = unique_codes.numel() / V
```

Range: ``[0, 1]``. A healthy FSQ-trained Kanzi model typically
achieves **0.3-0.7** for ``V=4096`` (FSQ paper §4.1, Mentzer et al.
2023, arXiv:2309.15505). Reference: ``train_cb.py:321``.

### 2.5 ``codebook_hamming_rotation_invariance``

```
for each backbone r in eval_split:
    idx_r0 = encode(rotate(x_r, R0))            # (L,) LongTensor
    idx_r1 = encode(rotate(x_r, R1))            # (L,) LongTensor
    hamming_r = (idx_r0 == idx_r1).float().mean()
hamming = mean over r of hamming_r
```

Range: ``[0, 1]``. A perfectly rotation-invariant encoder returns
``1.0``; a non-invariant one with random code matching returns
``~1/V`` (= 1/4096 for the Wave 36 ckpt). Reference:
``train_cb.py:309-322``.

**Determinism fix vs upstream:** upstream samples rotations via
``sample_uniform_rotation`` (``models.py:29-47``) which calls
``Rotation.random(...)`` with no seed control. We seed a
``numpy.random.Generator`` once at the top of the helper, then use it
to seed ``numpy.random.seed(...)`` before each ``Rotation.random``
call so scipy.spatial.transform picks a deterministic rotation matrix.

### 2.6 ``reconstruction_kabsch_rmsd_A`` (Wave 79 driver delegation)

The Wave 79 driver at ``tools/upstream_eval.py:run_kanzi_upstream_eval``
already produces ``<output_dir>/reconstruction.json`` with the
``mean_rmsd_A`` etc. summary. The wrapper just re-exports under the
paper-metric naming convention so callers can do
``from tools.paper_metrics_kanzi import compute_reconstruction_kabsch_rmsd_A``
for all 6 metrics.

---

## 3. Test coverage

### 3.1 Per-metric coverage

| Metric | Unit tests |
|--------|------------|
| entropy | uniform → log2(V); collapsed → 0.0 |
| perplexity | uniform → V; collapsed → 1.0; partial → in-between |
| js_distance | identical pair → 0.0; disjoint support → 1.0; single-row → 0.0; byte-stable (two calls = same output) |
| utilization | full → 1.0; partial (V/2 unique) → 0.5; empty → 0.0; OOR index → ValueError |
| hamming | identity encoder → 1.0; empty coords → 0.0; mismatched shape → ValueError; n_rot < 2 → ValueError |

### 3.2 Aggregator coverage

* All 5 keys present in the frozen dataclass.
* ``to_dict()`` JSON-serializable.
* Two calls with same input → byte-identical output dict (regression
  for the ``(0, 1)`` JS pair fix + seeded rotation sampler).

### 3.3 Reconstruction wrapper coverage

* Mocks ``tools.upstream_eval.run_kanzi_upstream_eval`` to return a
  canned sentinel dict; verifies the wrapper passes through
  unchanged. Proves the delegation contract without spawning a real
  subprocess (which would require the upstream ckpt).

### 3.4 End-to-end integration

``test_paper_metrics_kanzi_end_to_end_on_4_demo_pdbs``:

1. Reads the 4 demo PDBs from ``data/kanzi_upstream/pdbs/`` (1s7mB01,
   2hoxA01, 3bg1B01, 6nrzA01).
2. Truncates each to ``min(L_i) = 39`` residues (the shortest) so the
   ``(N, L, 3)`` stack has a uniform ``L``.
3. Encodes each via a SHA-256-based hash stub
   (deterministic + no upstream ckpt required).
4. Calls ``compute_all_codebook_metrics`` with the aggregated indices +
   the stacked coords + the hash encoder.
5. Asserts all 5 metrics are in their canonical ranges + utilization
   > 0 (non-degenerate).

Skips gracefully when the 4 demo PDBs are not vendored (e.g. on a
fresh clone).

---

## 4. D.4 byte-stable regression: 33/33 PASS

```
$ python3 -m pytest tests/ -k "d4" \
    --ignore=tests/test_property_based \
    --ignore=tests/test_expecttest_smoke.py \
    --ignore=tests/perf
...
33 passed, 6 skipped, 4798 deselected, 9 warnings in 2.44s
```

The 6 skipped tests are environment-skips (hypothesis / pytest-benchmark /
torch / rdkit not installed on this host); they are not new skips — they
are the same env-bound skips Wave 82 Agent A documented.

Without the ``--ignore`` flags, ``pytest -k "d4"`` collection trips over
the property-based tests (hypothesis not installed) — this is a
pre-existing pytest collection issue, not a regression caused by Wave 83.

---

## 5. Files delivered

| Path | LOC | Status |
|------|-----|--------|
| `tools/paper_metrics_kanzi.py` | ~510 | NEW |
| `tests/test_tools/test_paper_metrics_kanzi.py` | ~430 | NEW |
| `docs/audit/wave83-agent-b-codebook-metrics.md` | this file | NEW |

No modifications to existing files (the Wave 83 Agent B scope is
strictly additive).

---

## 6. Risk + mitigation

| Risk | Mitigation |
|------|------------|
| Wrapper confuses ``idx_BL`` (B, L) int32 with ``c_BLD`` (B, L, D) float | Coercion helper ``_coerce_idx`` raises ``TypeError`` on float dtype; docstring emphasizes the naming convention. |
| JS-distance byte-stability diverges from upstream | Fixed (0, 1) pair + log-guard; the divergence is documented in the docstring + the test explicitly asserts two-call byte-stability. |
| Hamming metric requires real ckpt + scipy | Test uses a SHA-256 hash stub for the encoder; real-ckpt path gated on ``kanzi_available()``. |
| Different PDB residue counts break ``np.stack`` | Integration test truncates all backbones to ``min(L_i)`` before stacking. |
| Real-ckpt smoke spawns a subprocess that may take hours | The smoke surface is opt-in (``--smoke`` CLI flag); default unit tests do not require a subprocess. |

---

## 7. JSON return

```json
{
  "wave": "Wave 83 Agent B",
  "scope": "tools/paper_metrics_kanzi.py implementation",
  "delivered": {
    "wrapper_module": "tools/paper_metrics_kanzi.py",
    "wrapper_loc": 510,
    "test_module": "tests/test_tools/test_paper_metrics_kanzi.py",
    "test_loc": 430,
    "test_count": 11,
    "metrics_implemented": [
      "codebook_entropy_bits",
      "codebook_perplexity",
      "codebook_js_distance",
      "codebook_utilization",
      "codebook_hamming_rotation_invariance"
    ],
    "metrics_re_exported": ["reconstruction_kabsch_rmsd_A"],
    "total_paper_metrics_exposed": 6
  },
  "test_results": {
    "paper_metrics_kanzi_tests": "11/11 PASS",
    "d4_byte_stable_regression": "33/33 PASS"
  },
  "determinism_fixes_vs_upstream": [
    "JS-distance: fixed (0, 1) batch pair (upstream: random.uniform)",
    "Hamming: seeded numpy.random.Generator (upstream: random.uniform)"
  ],
  "no_existing_files_modified": true,
  "blocking_dep_for_paper_claim": "AFDB-Foldseek held-out subset (Wave 83+ Agent C)",
  "blocking_dep_for_wrapper": "none"
}
```
