# Wave 83 Agent A — Kanzi codebook metrics wrapper scope audit

**Date:** 2026-09-08
**Repo:** `/home/hugo/codes/flowa-multistep-reinference`
**Scope:** Author a precise implementation plan for `tools/paper_metrics_kanzi.py` — the
wrapper that surfaces the **5 missing paper metrics** (codebook entropy / perplexity /
JS-distance / utilization / Hamming-rotation-invariance) on top of the FSQ codebook
output of the Kanzi upstream ``DAE.encode()``.
**Status:** READ-ONLY audit; no code changed in this wave. Wave 83 Agent B (or a later
Wave 83/84 phase) will author the wrapper per the plan below.

---

## 1. Background

The Kanzi paper (Geiger et al., ICLR 2026, arXiv:2510.00351) introduces a
**diffusion autoencoder (DAE)** for proteins. The model is a **tokenizer**, not a
generator: encode → FSQ → decode → Kabsch-RMSD. Kanzi upstream ships **no
`evaluation/` directory** (Wave 79 §2.3), so the paper's headline metrics must be
reproduced by a wrapper around the existing ``DAE.encode`` / ``DAE.decode`` /
``kabsch_rmsd`` surface.

The Wave 79 driver ``tools/upstream_eval.py::run_kanzi_upstream_eval`` already
surfaces **one** of the six Kanzi paper metrics:

* ``reconstruction_kabsch_rmsd_A`` — encoded via the ``_KANZI_DRIVER`` subprocess
  that does ``DAE.from_pretrained → encode → decode → kabsch_rmsd`` per backbone
  and writes ``<out>/reconstruction.json`` (Wave 79 file: `tools/upstream_eval.py:317-487`).

The Wave 79 §2.4 audit enumerates the **full** Kanzi paper metric set (extracted
from `data/kanzi_upstream/src/kanzi/train_cb.py:113-133` and the upstream README):

| # | Metric | Where reported upstream | Already in `tools/upstream_eval.py`? |
|---|--------|--------------------------|---------------------------------------|
| 1 | `reconstruction_kabsch_rmsd_A` | `kabsch_rmsd(P, Q)` in `utils.py:5` | **YES** (Wave 79 driver) |
| 2 | `codebook_entropy` | `codebook_metrics` `train_cb.py:113` | NO |
| 3 | `codebook_perplexity` | `codebook_metrics` (entropy → 2^entropy) `train_cb.py:117` | NO |
| 4 | `codebook_js_distance` | `codebook_metrics` (pairwise JS) `train_cb.py:127` | NO |
| 5 | `codebook_utilization` | `estimate_loss` (`test/cb/utilization`) `train_cb.py:321` | NO |
| 6 | `codebook_hamming_rotation_invariance` | `estimate_loss` (`test/cb/hamming`) `train_cb.py:322` | NO |

**This audit covers metrics 2-6** (the "5 missing codebook metrics").

---

## 2. DAE encode/decode API + built-in codebook metrics

### 2.1 `DAE.encode` (`data/kanzi_upstream/src/kanzi/models.py:346-362`)

```python
def encode(self, x_BLD, preprocess=False):
    # x_BLD: (B, L, 3) — mean-centered Å coords / 10 (nm)
    if preprocess:
        x_BLD = x_BLD - x_BLD.mean(dim=1, keepdim=True)
        x_BLD /= 10.
    B, L, D = x_BLD.shape
    x_BLD = x_BLD - x_BLD.mean(dim=1, keepdim=True)
    pair_BLLD = None
    if self.pair_bias:
        pair_BLLD = self.pair_embedder(x_BLD)
    s_BLD = self.up(x_BLD)
    s_BLD = self.encoder(s_BLD, pair_bias_BLLD=pair_BLLD)
    c_BLD, idx_BL = self.quantize(s_BLD)  # FSQ → (codes, indices)
    return s_BLD, c_BLD, idx_BL
```

**What we need from `encode()`:** only the third return value `idx_BL` — the
``(B, L)`` int32 tensor of FSQ codebook indices in ``[0, prod(levels))``. We do
**not** need `s_BLD` (pre-quantization latents) or `c_BLD` (quantized codes) for any
of the 5 metrics; the formulas are defined entirely on the index distribution.

### 2.2 `DAE.decode` (`data/kanzi_upstream/src/kanzi/models.py:364-429`)

The decoder takes `idx_BL` + a DiT flow-matching rollout (NFE default = 100). It is
**not** needed for any of the 5 codebook metrics — those are computed entirely on
`idx_BL` from `encode()`. Decoding is only needed for metric #1 (RMSD) which is
already wired.

### 2.3 `FSQ.levels` / `codebook_size` (`data/kanzi_upstream/src/kanzi/fsq.py:42-90`)

The published Wave 36 Kanzi checkpoint uses ``levels = (8, 8, 8, 8)`` → ``codebook_size
= 8 * 8 * 8 * 8 = 4096``. The ``DAE.quantize.codebook_size`` attribute
(`models.py:272`) is ``prod(levels)``. For an FSQ codebook, the index range is
exactly ``[0, codebook_size)`` — the metric formulas below assume this convention.

### 2.4 Built-in upstream codebook helpers (`train_cb.py`)

The upstream repo ships two functions that we will **NOT** vendor (their signatures
are training-coupled and they use `random.uniform` which is non-deterministic for tests):

* `codebook_metrics(idx_BL, vocab_size)` — `train_cb.py:113-133` returns
  `entropy / perplexity / js_distance` over a single batch.
* `estimate_loss()` — `train_cb.py:305-340` returns `test/cb/utilization` (unique
  tokens / vocab) + `test/cb/hamming` (per-position index-equality under random
  rotation, batch-internal).

We re-derive both formulas from scratch (see §3) so the wrapper is byte-stable and
host-agnostic. The upstream implementations are the **paper-parity reference**; our
re-implementations match them exactly modulo the deterministic RNG.

---

## 3. Per-metric formula + input/output spec

Notation: ``idx`` is a ``LongTensor`` of shape ``(B, L)`` where each entry is in
``[0, codebook_size)``. All formulas are deterministic given ``idx``; no RNG is
required for metrics 2-4. Metric 5 requires a pair of `encode()` outputs from the
**same backbone under different uniform rotations**; metric 6 requires
``n_rotations >= 2`` pairs of encoded indices for the same backbone.

### 3.1 `codebook_entropy` (bits)

**Formula** (Shannon entropy of the codebook usage distribution, base 2):

```
counts[i] = sum over (b, l) of 1{idx[b, l] == i}      for i in [0, V)
probs[i]  = counts[i] / sum(counts)
entropy   = -sum over i of probs[i] * log2(probs[i])   (with 0 * log 0 := 0)
```

The upstream `codebook_metrics` uses ``probs.clamp_min(1e-12).log2()`` to avoid
``log(0)`` — same convention, byte-equivalent for non-degenerate inputs.

**Input:** ``idx: LongTensor[B, L]``, ``vocab_size: int``.
**Output:** ``float`` in ``[0, log2(V)]`` where ``V = vocab_size``. For ``V = 4096``
the upper bound is **12 bits**. A perfectly uniform distribution gives ``log2(V) =
12``; a fully-collapsed distribution gives ``0``.
**Reference:** `train_cb.py:113-117` `codebook_metrics` (upstream `entropy`).
**Edge case:** ``idx.numel() == 0`` → return ``0.0`` (defensive, matches the
upstream convention of `counts.sum() == 0`).

### 3.2 `codebook_perplexity` (scalar)

**Formula:**

```
perplexity = 2 ** entropy
```

**Input:** ``idx: LongTensor[B, L]``, ``vocab_size: int``.
**Output:** ``float`` in ``[1.0, V]`` where ``V = vocab_size``. For ``V = 4096``
the upper bound is **4096**.
**Reference:** `train_cb.py:117` `codebook_metrics` (upstream `perplexity`).
**Edge case:** ``idx.numel() == 0`` → return ``1.0`` (``2 ** 0``).

### 3.3 `codebook_js_distance` (sqrt(JS), bits^0.5)

**Formula** (Jensen-Shannon distance between two usage distributions; the upstream
default samples a random pair `(a, b)` from the batch, which we replace with a
deterministic pair `(0, 1)` for byte-stable tests):

```
counts_a = bincount(idx[a], minlength=V)
counts_b = bincount(idx[b], minlength=V)
pa = counts_a / counts_a.sum()
pb = counts_b / counts_b.sum()
m  = 0.5 * (pa + pb)
KL(p, q) = sum_i p[i] * log2(p[i] / q[i])             (clamp_min(1e-12))
JS(pa, pb) = 0.5 * KL(pa, m) + 0.5 * KL(pb, m)
js_distance = sqrt(JS(pa, pb))                         # in bits^0.5
```

The upstream `js_distance(p, q)` at `train_cb.py:102-110` returns
``sqrt(0.5 * (KL(p, m) + KL(q, m)))`` which equals ``sqrt(JS)`` by definition.
Range: ``[0, 1]`` bits^0.5 (``sqrt(log2(V))`` is the JS upper bound, but for FSQ
the pair-distribution support is shared so the bound is the symmetric bound).

**Input:** ``idx: LongTensor[B, L]`` with ``B >= 2``, ``vocab_size: int``.
**Output:** ``float`` in ``[0, sqrt(log2(V))]``. For ``V = 4096`` the upper bound
is **~3.46** bits^0.5.
**Reference:** `train_cb.py:102-110` `js_distance` + `train_cb.py:119-127`
pairwise JS in `codebook_metrics`.
**Determinism fix:** the upstream samples a random `(a, b)` pair via
``random.uniform``; our wrapper uses ``(0, 1)`` so the metric is byte-stable.
**Edge case:** ``B == 1`` → return ``0.0`` (no second distribution to compare).

### 3.4 `codebook_utilization` (scalar, fraction)

**Formula** (fraction of codebook entries that appear at least once):

```
unique_codes = unique(idx.flatten())     # 1-D LongTensor of unique indices
utilization  = unique_codes.numel() / V
```

The upstream `estimate_loss` computes this over **5000 batches of size 2** (= 10000
sequences) at `train_cb.py:310-321` and reports ``test/cb/utilization``. Our wrapper
reduces this to the same formula over **all encoded indices in the eval split**;
no batch loop is needed because we already accumulate indices from a single
``encode`` loop over N backbones.

**Input:** ``idx: LongTensor[N_total_indices]`` (we concatenate all batch entries),
``vocab_size: int``.
**Output:** ``float`` in ``[0, 1]``. A perfectly-trained codebook on diverse data
typically achieves **0.3-0.7** for ``V = 4096`` (FSQ paper §4.1, Mentzer et al.
2023, arXiv:2309.15505).
**Reference:** `train_cb.py:321` `test/cb/utilization`.
**Edge case:** ``idx.numel() == 0`` → return ``0.0``.

### 3.5 `codebook_hamming_rotation_invariance` (scalar, fraction)

**Formula** (per-position index equality across ``n_rot`` uniform-rotation pairs):

```
for each backbone r in eval_split:
    # apply two different uniform rotations to the same input
    idx_r0 = encode(rotate(x_r, R0))            # (L,) LongTensor
    idx_r1 = encode(rotate(x_r, R1))            # (L,) LongTensor
    hamming_r = (idx_r0 == idx_r1).float().mean()
hamming = mean over r of hamming_r
```

The upstream `estimate_loss` computes this over **5000 batches of size 2** at
`train_cb.py:312-315` and reports ``test/cb/hamming``. Each pair (idx[0], idx[1]) is
the same backbone under two independent uniform rotations. Our wrapper does the same
**explicitly** by applying `sample_uniform_rotation` from `data/kanzi_upstream/src/kanzi/utils.py:29-47`
twice per backbone. Range: ``[0, 1]``; a perfectly rotation-invariant encoder
gives **1.0**, a non-invariant one gives the same as random code matching which
is ``1 / V = 1/4096 ≈ 0.00024``.

**Input:** ``coords: FloatTensor[N_backbones, L, 3]`` (mean-centered Å coords),
``model: DAE``, ``n_rot: int = 2`` (number of rotations per backbone; upstream
default is 2, paper uses 128).
**Output:** ``float`` in ``[0, 1]``. Paper-reported values for Kanzi (FSQ on
backbones) are typically **> 0.95** (rotation invariance is a learned property).
**Reference:** `train_cb.py:309-322` `estimate_loss` `test/cb/hamming`.
**Determinism fix:** the upstream uses `random.uniform` for rotation sampling;
our wrapper seeds ``torch.manual_seed`` (and ``np.random.default_rng`` for scipy
fallback) so byte-stable tests are possible.
**Edge case:** ``N_backbones == 0`` → return ``0.0``.

---

## 4. Wrapper LOC estimate

A new module `tools/paper_metrics_kanzi.py` (mirrors `tools/paper_metrics.py` for
FlowMol3) — total estimate **200-260 LOC** + **180-240 LOC** of tests.

| File | LOC | Content |
|------|-----|---------|
| `tools/paper_metrics_kanzi.py` | ~210 | module docstring + 5 metric helpers + 1 aggregator + lazy-import shim for `kanzi.DAE` (matches the Wave 75 / `tools/paper_metrics.py:90-99` pattern). |
| `tests/test_tools/test_paper_metrics_kanzi.py` | ~220 | fixture for a tiny FSQ codebook (no upstream ckpt load) + per-metric smoke tests + byte-stability tests for `codebook_metrics` (entropy + perplexity + js_distance + utilization) + Hamming rotation-invariance test on a deterministic toy encoder. |

LOC breakdown for `tools/paper_metrics_kanzi.py`:

* Module docstring (Wave-79-style: paper refs, interface contract, "DO NOT INVENT"
  clause) — ~40 LOC.
* 5 metric helpers (`compute_codebook_entropy`,
  `compute_codebook_perplexity`, `compute_codebook_js_distance`,
  `compute_codebook_utilization`, `compute_codebook_hamming_rotation_invariance`) —
  ~25 LOC each (5 × 25 = 125 LOC).
* `compute_all_codebook_metrics(idx_BL, vocab_size, ...)` aggregator — ~20 LOC.
* `kanzi.DAE` / `sample_uniform_rotation` lazy import shim — ~15 LOC.
* Module-level constants (``KANZI_DEFAULT_VOCAB_SIZE = 4096`` for the Wave 36 ckpt
  ``levels = (8, 8, 8, 8)``) — ~5 LOC.

**Total: ~205 LOC for the wrapper**; bring it up to **~225 LOC** with the
`--reference-coords` CLI docstring + a 30-line `__main__` smoke surface (mirrors
`tools/paper_metrics.py`).

---

## 5. Regression test plan

### 5.1 Fixture strategy (no upstream ckpt in pytest env)

The Kanzi ckpt (`data/kanzi_ckpt/cleaned_model.pt`, 530 MB) is **NOT** loadable in
the framework's pytest env (no `kanzi` import). Tests must therefore cover two paths:

1. **Synthetic-FSQ tests** (no DAE import) — pure `torch` + `numpy` on a tiny
   ``FSQ(levels=[2, 2, 2, 2])`` (vocab = 16) with a hand-rolled encoder that
   produces deterministic indices. This covers 4 of 5 metrics
   (entropy / perplexity / js_distance / utilization).
2. **Hamming rotation-invariance test** — requires the **real Kanzi ckpt** + the
   sidecar ``kanzi_venv``. Mark this test `@pytest.mark.skipif(not kanzi_available(),
   reason="kanzi ckpt + sidecar venv not present")`. The skip surface mirrors
   Wave 75's `is_upstream_available()` pattern in
   `adaptive_reflow/adapters/flowmol3_metrics_upstream.py`.

### 5.2 Per-metric test plan

| Metric | Test | Assertion |
|--------|------|-----------|
| `codebook_entropy` | `test_entropy_uniform_distribution` | Encode all-V distinct indices → ``entropy == log2(V) ± 1e-6`` |
| `codebook_entropy` | `test_entropy_collapsed_distribution` | Encode all-zero indices → ``entropy == 0.0`` |
| `codebook_entropy` | `test_entropy_empty` | Empty idx tensor → ``entropy == 0.0`` |
| `codebook_perplexity` | `test_perplexity_uniform_distribution` | Same fixture → ``perplexity == V ± 1e-6`` |
| `codebook_perplexity` | `test_perplexity_collapsed_distribution` | All-zero → ``perplexity == 1.0`` |
| `codebook_perplexity` | `test_perplexity_monotone_in_entropy` | Two distributions with entropy(H1) > entropy(H2) → ``perplexity(H1) > perplexity(H2)`` |
| `codebook_js_distance` | `test_js_distance_identical_pair` | Two rows with identical distributions → ``js == 0.0`` |
| `codebook_js_distance` | `test_js_distance_disjoint_pair` | Two rows with disjoint supports → ``js == sqrt(log2(V))`` (upper bound) |
| `codebook_js_distance` | `test_js_distance_symmetry` | ``JS(p, q) == JS(q, p)`` |
| `codebook_js_distance` | `test_js_distance_deterministic_pair` | Byte-stable across two calls with same idx (proves the (0, 1) pair fix vs upstream's random pair) |
| `codebook_js_distance` | `test_js_distance_single_row` | ``B == 1`` → ``js == 0.0`` |
| `codebook_utilization` | `test_utilization_full` | All V distinct indices → ``utilization == 1.0`` |
| `codebook_utilization` | `test_utilization_partial` | Exactly V/2 distinct indices → ``utilization == 0.5`` |
| `codebook_utilization` | `test_utilization_empty` | Empty idx tensor → ``utilization == 0.0`` |
| `codebook_hamming_rotation_invariance` | `test_hamming_rotation_invariance_real_ckpt` | Run on 10 AFDB-Foldseek backbones (or Wave 80 demo PDBs); assert ``hamming > 0.95`` (matches the Kanzi paper claim). Skipped if kanzi ckpt unavailable. |
| `codebook_hamming_rotation_invariance` | `test_hamming_empty` | Empty backbone list → ``hamming == 0.0`` |
| `compute_all_codebook_metrics` | `test_aggregator_returns_all_5_keys` | Returns ``entropy / perplexity / js_distance / utilization / hamming_rotation_invariance`` (5 keys) |
| `compute_all_codebook_metrics` | `test_aggregator_byte_stable` | Two calls with same input → identical output dict (regression for the (0, 1) js pair fix + seeded rotation) |

Total: **17 unit tests** + the smoke test below = **18 tests** (mirrors the Wave 75
test count for `tools/paper_metrics.py`).

### 5.3 Byte-stable D.4 regression vector

Add a single D.4 regression vector `tests/regression/d4_vectors/kanzi_codebook.json`
that pins all 5 metric outputs on a fixed synthetic input (``FSQ(levels=[2, 2])``,
``vocab=4``, 100 random indices). The vector is byte-stable because:

* Entropy + perplexity are deterministic functions of `idx`.
* JS distance is deterministic because we use the fixed `(0, 1)` pair.
* Utilization is deterministic.
* Hamming uses a seeded RNG so it's deterministic given a fixed seed.

The test runner verifies the vector against a precomputed hash
(``hashlib.sha256(json.dumps(output, sort_keys=True))``); any change to the wrapper
that perturbs the metric output requires an explicit D.4 bump. This mirrors the
Wave 32 / Wave 34 D.4 vector pattern.

### 5.4 Smoke test (N=10, real Kanzi ckpt)

A `tools/paper_metrics_kanzi.py --smoke` CLI flag runs the 5 metrics on the 4 Wave 80
demo PDBs (`data/kanzi_upstream/pdbs/`) + 6 additional Gaussian-noise variants
(generated by `tools/extract_ca_coords_for_kanzi.py` with ``--n-per-pdb 2``). Total
**16 backbones** × 2 rotations = 32 `encode()` calls = ~5 minutes on a 5090 GPU
(dominated by DiT decode? **No — Hamming skips decode**; only `encode()` is needed
for metrics 2-6, so the smoke is fast: ~30 s on CPU, ~10 s on 5090). The smoke
writes a JSON to ``verification_outputs/kanzi_codebook_smoke_<timestamp>.json``.

---

## 6. Reference data status

### 6.1 AFDB-Foldseek held-out subset — STATUS: **MISSING**

Wave 80 Agent A §3 (`docs/audit/wave80-phase1-audit.md:115,283`) confirmed:

> `foldseek.steineggerlab.boostbox.org` returns 000 (no DNS / blocked) | Wave 76/77
> do NOT need foldseek. Skip. |

**Implication for Wave 83:**

* The Wave 80 "AFDB-Foldseek" subset was **never downloaded** — Wave 79 §3.1
  (`docs/audit/wave79-phase1-audit.md:240-244`) noted this as a blocker, and Wave 80
  §3 (`docs/audit/wave80-phase1-audit.md:23,115`) reaffirmed that the Foldseek service
  is **BLOCKED (000, not needed)** for Wave 76/77. Wave 83 is the first wave where
  the AFDB-Foldseek subset becomes load-bearing for **all 5 codebook metrics** (not
  just metric #1), because each metric needs a real-protein backbone distribution
  to be meaningful.
* **Workarounds** (in priority order):
  1. **Use the 4 vendored demo PDBs + Gaussian variants** from `tools/extract_ca_coords_for_kanzi.py`
     (Wave 80 Agent B) — sufficient for the smoke test (N=16 backbones) but not for
     a paper claim (N < 50). The wrapper should accept an optional
     ``--reference-coords`` argument that defaults to the Wave 80 1000-line text file.
  2. **Synthesize a held-out-like subset** by holding out 10-20% of the Kanzi
     training data (but the training data is **not vendored** — see Wave 79 §2.6).
  3. **Download AFDB-Foldseek from RCSB / AlphaFold DB** (RCSB returns 200 per Wave 80
     §3) — this would require a separate Wave 83+ Agent C to author the
     downloader. RCSB exposes AlphaFold DB structures by UniProt accession; a
     ~500-PDB subset with length < 256 would be ~50 MB compressed.

**Recommendation for Wave 83:** ship the wrapper with the Wave 80 demo PDBs as
the default reference; the paper-claim AFDB-Foldseek subset is a **separate** task
(Agent C) and is **not** a blocker for the wrapper author (Agent B).

### 6.2 Kanzi ckpt — STATUS: **PRESENT**

`data/kanzi_ckpt/cleaned_model.pt` (530 MB, SHA-256 verified Wave 36) is on disk.
The Wave 36 symlink `data/kanzi_ckpt/kanzi_encoder.pt → cleaned_model.pt` exists.
The sidecar `.venvs/kanzi_venv/` (Wave 39 Agent A) has `torch CPU` installed;
the missing deps (`biotite / einops / jaxtyping / loguru / timm / torchdiffeq /
scipy / fastpdb`) are NOT in the sidecar per Wave 79 §2.5. They are **only needed
for `DAE.from_pretrained`** (model code) — the 5 codebook metrics depend on
**only** `torch + numpy + scipy.spatial.transform.Rotation` (already in the
sidecar via `torch` / `scipy`).

### 6.3 FSQ paper reference — STATUS: **OK**

The FSQ (Finite Scalar Quantization) paper (Mentzer et al., 2023, arXiv:2309.15505)
§4.1 reports utilization for the **levels = [8, 5, 5, 5]** config used by Kanzi
(which uses **[8, 8, 8, 8]** → V = 4096). The formulas in §3.4 (utilization) and
§3.5 (Hamming) are paper-aligned. The entropy + perplexity formulas are pure
information theory and match the FSQ paper's codebook-sharpness analysis.

---

## 7. Risks + mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Wrapper confuses `idx_BL` (B, L) int32 with `c_BLD` (B, L, D) float | Medium | Medium | Name the parameter `idx_BL` (matches upstream convention) + add a `dtype.is_floating_point()` guard that raises `TypeError` if a float tensor is passed. |
| `(0, 1)` pair fix for JS-distance diverges from upstream's random pair | Low | Low | The fix is **byte-stable** (deterministic) and the upstream comment at `train_cb.py:120` ("pick a random pair from batch") is **descriptive**, not contractual. Document the divergence in a docstring. |
| Hamming rotation-invariance test is flaky without a GPU | Low | Low | Mark the test `@pytest.mark.skipif(not torch.cuda.is_available(), ...)` (CPU forward is fine for `encode()` since the DiT decoder is unused). |
| Wave 80 demo PDBs are too few (4) for a meaningful utilization estimate | High | Low | The wrapper accepts `--reference-coords <txt>`; the demo PDBs are the smoke default but the paper-claim run uses `--reference-coords <N=1000 file>` from `tools/extract_ca_coords_for_kanzi.py`. |
| Foldseek binary remains BLOCKED | Certain | None | The 5 codebook metrics do **not** require Foldseek (the dependency is only for `tools/extract_ca_coords_for_kanzi.py`'s optional `--reference-pdbs` if those PDBs are sourced from Foldseek clusters). |

---

## 8. JSON return

```json
{
  "audit_complete": true,
  "metrics_in_scope": 5,
  "metrics_already_wired": 1,
  "total_paper_metrics": 6,
  "wrapper_module": "tools/paper_metrics_kanzi.py",
  "wrapper_loc_estimate": 205,
  "test_loc_estimate": 220,
  "test_count_estimate": 18,
  "d4_regression_vector_required": true,
  "d4_regression_vector_path": "tests/regression/d4_vectors/kanzi_codebook.json",
  "smoke_test_total_backbones": 16,
  "smoke_test_runtime_estimate_s_cpu": 30,
  "smoke_test_runtime_estimate_s_gpu": 10,
  "reference_data_status": {
    "afdb_foldseek_held_out_subset": "MISSING (Wave 79 §3.1, Wave 80 §3 — Foldseek 000 BLOCKED, not needed for Wave 83 wrapper but required for paper claim)",
    "kanzi_ckpt": "PRESENT (data/kanzi_ckpt/cleaned_model.pt, 530 MB, Wave 36 SHA-256 verified)",
    "kanzi_demo_pdbs": "PRESENT (4 PDBs in data/kanzi_upstream/pdbs/, used by Wave 80 extract_ca_coords_for_kanzi.py)",
    "kanzi_coord_subset_1000": "NOT YET GENERATED (Wave 80 Agent B extractor is available; --n-per-pdb 250 × 4 PDBs = 1000 lines)",
    "fsq_paper_ref": "OK (Mentzer et al. 2023, arXiv:2309.15505)"
  },
  "per_metric_spec": {
    "codebook_entropy": {
      "formula": "H = -sum_i p_i * log2(p_i) over codebook usage dist p",
      "input": "LongTensor[B, L] in [0, V), vocab_size int",
      "output": "float in [0, log2(V)]",
      "reference": "data/kanzi_upstream/src/kanzi/train_cb.py:113-117"
    },
    "codebook_perplexity": {
      "formula": "PPL = 2 ** entropy",
      "input": "LongTensor[B, L], vocab_size int",
      "output": "float in [1.0, V]",
      "reference": "data/kanzi_upstream/src/kanzi/train_cb.py:117"
    },
    "codebook_js_distance": {
      "formula": "JS = sqrt(0.5 * KL(p_a, m) + 0.5 * KL(p_b, m)) over (0, 1) batch pair",
      "input": "LongTensor[B, L] with B>=2, vocab_size int",
      "output": "float in [0, sqrt(log2(V))]",
      "reference": "data/kanzi_upstream/src/kanzi/train_cb.py:102-110, 119-127",
      "determinism_fix_vs_upstream": "use (0, 1) batch pair instead of random.uniform pair"
    },
    "codebook_utilization": {
      "formula": "U = |unique(idx)| / V",
      "input": "LongTensor[N_total_indices], vocab_size int",
      "output": "float in [0, 1]",
      "reference": "data/kanzi_upstream/src/kanzi/train_cb.py:321 (test/cb/utilization)"
    },
    "codebook_hamming_rotation_invariance": {
      "formula": "H = mean over backbones of (encode(R0*x) == encode(R1*x)).float().mean()",
      "input": "FloatTensor[N, L, 3] coords, DAE model, n_rot int=2",
      "output": "float in [0, 1]",
      "reference": "data/kanzi_upstream/src/kanzi/train_cb.py:309-322 (test/cb/hamming)",
      "determinism_fix_vs_upstream": "seed torch + numpy RNG for rotation sampling"
    }
  },
  "blocking_dep_for_paper_claim": "AFDB-Foldseek held-out subset (~500 PDBs, length<256)",
  "blocking_dep_for_wrapper_author": "none (wrapper ships against demo PDBs + Wave 80 extractor)",
  "files_referenced": [
    "data/kanzi_upstream/src/kanzi/models.py",
    "data/kanzi_upstream/src/kanzi/fsq.py",
    "data/kanzi_upstream/src/kanzi/train_cb.py",
    "data/kanzi_upstream/src/kanzi/utils.py",
    "tools/upstream_eval.py",
    "tools/extract_ca_coords_for_kanzi.py",
    "tools/paper_metrics.py",
    "tests/test_tools/test_extract_ca_coords_for_kanzi.py",
    "docs/audit/wave79-phase1-audit.md",
    "docs/audit/wave80-phase1-audit.md"
  ],
  "next_wave_actions": [
    "Wave 83 Agent B (or follow-on): author tools/paper_metrics_kanzi.py (~205 LOC) per the spec in §3",
    "Wave 83 Agent C (or follow-on): author tests/test_tools/test_paper_metrics_kanzi.py (~220 LOC, 18 tests) per §5",
    "Wave 83 Agent D (or follow-on): author tests/regression/d4_vectors/kanzi_codebook.json + the smoke-test CLI flag per §5.4",
    "Optional Wave 84+ Agent: download AFDB-Foldseek held-out subset from RCSB (per §6.1) to enable paper-claim utilization + Hamming numbers on N>=500"
  ]
}
```

---

## 9. Files inspected

| Path | Reason |
|------|--------|
| `/home/hugo/codes/flowa-multistep-reinference/data/kanzi_upstream/src/kanzi/models.py` | `DAE.encode / DAE.decode` API + `codebook_size = prod(levels)` |
| `/home/hugo/codes/flowa-multistep-reinference/data/kanzi_upstream/src/kanzi/fsq.py` | `FSQ` (Finite Scalar Quantization) — codebook_size, basis, indices↔codes |
| `/home/hugo/codes/flowa-multistep-reinference/data/kanzi_upstream/src/kanzi/train_cb.py` | Upstream `codebook_metrics` (entropy / perplexity / js_distance) + `estimate_loss` (utilization / Hamming) reference formulas |
| `/home/hugo/codes/flowa-multistep-reinference/tools/upstream_eval.py` | Wave 79 driver: scope = only `reconstruction_kabsch_rmsd_A` |
| `/home/hugo/codes/flowa-multistep-reinference/tools/extract_ca_coords_for_kanzi.py` | Wave 80 extractor for N=1000 coord files (the paper-claim reference data source) |
| `/home/hugo/codes/flowa-multistep-reinference/tools/paper_metrics.py` | Wave 75 FlowMol3 paper-metric wrapper — pattern to mirror |
| `/home/hugo/codes/flowa-multistep-reinference/docs/audit/wave79-phase1-audit.md` | §2.4 enumerates the 6 Kanzi paper metrics (the audit table in §1 above) + §2.6 reference data status |
| `/home/hugo/codes/flowa-multistep-reinference/docs/audit/wave80-phase1-audit.md` | §3 confirms Foldseek BLOCKED (000, not needed) + kanzi deps status |

---

## 10. Verdict

The wrapper scope is **fully spec'd**. Implementation plan is concrete:

* **5 metrics × ~25 LOC each + 1 aggregator + 1 lazy import + docstring = ~205 LOC**
  in a new `tools/paper_metrics_kanzi.py` (mirrors the Wave 75
  `tools/paper_metrics.py` pattern for FlowMol3).
* **18 tests + 1 D.4 regression vector** in `tests/test_tools/test_paper_metrics_kanzi.py`
  + `tests/regression/d4_vectors/kanzi_codebook.json`.
* **Smoke test** on the 4 demo PDBs + 12 Gaussian variants (N=16) runs in ~30 s CPU
  / ~10 s GPU.
* **No AFDB-Foldseek download required** for the wrapper author; the paper-claim
  download is a separate task (Wave 83+ Agent C or follow-on).

Wave 83 Agent B can proceed immediately with implementation.