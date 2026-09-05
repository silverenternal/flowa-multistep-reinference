# Algorithm improvement — D.4: pinned adapter regression vectors (first batch)

**Status:** CLOSED in Wave 38 (commit b88b32f, Wave 38 Agent A WF2) — D.4 first batch shipped: 5 pinned regression-vector adapters discovered in this run (vectors were already shipped; this batch makes them test-discoverable + gated)
**Date:** 2026-09-05
**Priority:** high (D.4 is a HARD gate per `framework-internal-metrics.md` §1 D.4)
**Depends on:** F.5 env_hash (live), F.6 mutation-audit harness pattern
**Owner:** framework maintainer
**Wave:** Wave 33 (target)
**Goal:** generate and commit a `(seed, input, NFE)` regression vector for
**5 adapters** as the first batch of D.4: `flowmol3_v2`, `twodim_fm`,
`lineageflow`, `kanzi`, `freqflow`. SHA-256 hash compared in CI to detect
silent byte-stability regressions under framework refactors.

## Background

Per `framework-internal-metrics.md` §1 D.4:
> Pinned adapter regression vectors: fixed (seed, input, NFE) tuple per
> adapter, hash compared in CI. Target: 18/18 by Wave 14.

Per Wave 32 Agent A (`docs/audit/gap-audit.md` §3):
- **D.4 NOT MET** — 0/18 adapters have a regression vector
- **No `regression-vectors/` directory exists** (verified 2026-09-05)
- **No `todo/` plan file exists** — this file closes that gap
- **Per-adapter discipline** requires the adapter author to commit a vector
  before PHASE-4 model integration testing (per Wave 19 P1A2 verdict)

Per `framework-freeze-checklist.md` MUST-1:
- D.4 is a HARD gate that blocks PHASE-4 entry

## Wave 32 scope (this plan)

This plan covers **first batch of 5 adapters only**:
1. `flowmol3_v2` (FlowMol3 v2; protein)
2. `twodim_fm` (synthetic 2D; CPU-only)
3. `lineageflow` (LineageFlow; protein, HF Hub)
4. `kanzi` (Kanzi; protein flow-AE, ICLR 2026)
5. `freqflow` (FreqFlow; image SiT-XL/2, CVPR 2026)

Rationale for these 5:
- `twodim_fm` is CPU-only and serves as the "fast feedback" adapter
- The other 4 are the active PHASE-2 / PHASE-3 model integration candidates
- Skipping the 5 PHASE-3-blocked (MM-FM, wan2_2_video, mnist_fm, rectified_flow_cifar, self_flow) avoids wasted vectors on adapters that aren't being integrated

Remaining 13 adapters to be planned in a follow-up wave after this batch
ships and the pattern stabilizes.

## What to do

### Phase A — Vector schema (author + ship)

1. **Author `adaptive_reflow/util/regression_vector.py`** (~50 LOC):
   ```python
   @dataclass(frozen=True)
   class RegressionVector:
       adapter_name: str
       adapter_version: str  # from adapter.VERSION or adapter.__version__
       seed: int
       input_id: str  # name of fixture used
       nfe: int
       host_fingerprint: dict[str, str]  # captured from env_hash.txt
       output_sha256: str  # SHA-256 of canonicalised output
       captured_at: str  # ISO 8601 timestamp
   ```

2. **Author `scripts/capture_regression_vector.py`** (~100 LOC):
   - Takes `--adapter <name>`, `--seed <int>`, `--input <fixture_path>`,
     `--nfe <int>` as args
   - Runs the adapter once (via `BatchedTrajectoryRunner` or directly)
   - Captures the byte-stable canonical output (deterministic subset
     of `trajectory[:1]` + `endpoint` + `metadata` as JSON)
   - SHA-256 hashes the canonicalised JSON
   - Writes `regression-vectors/<adapter>.json` with the `RegressionVector`
     schema populated

3. **Author `tests/test_adapters/test_regression_vectors.py`** (~80 LOC):
   - Parametrised over all 5 captured vectors
   - For each vector:
     - Re-run the adapter with the recorded `(seed, input, NFE)`
     - Re-compute the SHA-256 hash
     - Assert it matches the captured hash **on the same host**
   - **Skip with documented message** if the captured `host_fingerprint`
     does not match the current host (rationale: host shift may produce
     different RNG bytes — we record this rather than masking it)

### Phase B — Capture vectors (5 adapters)

For each of the 5 adapters:

1. **FlowMol3 v2**:
   - Seed: 42
   - Input: `tests/fixtures/flowmol3_v2/sample_input.pt` (or generate)
   - NFE: 10
   - Adapter: `flowmol3_v2_adapter`
   - Output: canonical trajectory + endpoint JSON

3. **twodim_fm**:
   - Seed: 42
   - Input: `tests/fixtures/twodim_fm/sample_input.npy` (or generate)
   - NFE: 100
   - Adapter: `twodim_fm`
   - Output: canonical endpoint (CPU-only; safe to capture without HF)

4. **lineageflow**:
   - Seed: 42
   - Input: `tests/fixtures/lineageflow/sample_input.pt` (or generate)
   - NFE: 10
   - Adapter: `lineageflow`
   - **GATED**: requires HF Hub weights download (Wave 10 ckpt)
   - **Skip if HF unavailable**; document in vector JSON

5. **kanzi**:
   - Seed: 42
   - Input: `tests/fixtures/kanzi/sample_input.pt` (or generate)
   - NFE: 10
   - Adapter: `kanzi`
   - **GATED**: requires ICLR 2026 ckpt (deferred; Wave 21 PHASE-3 work)
   - **Skip if ckpt unavailable**; document

6. **freqflow**:
   - Seed: 42
   - Input: `tests/fixtures/freqflow/sample_input.pt` (or generate)
   - NFE: 10
   - Adapter: `freqflow`
   - **GATED**: requires CVPR 2026 ckpt (deferred; Wave 21 PHASE-3 work)
   - **Skip if ckpt unavailable**; document

### Phase C — CI integration

1. **Update `.github/workflows/cpu-tests.yml`** to add a new job
   `regression-vectors` that:
   - Runs on every PR + push-to-main
   - Executes `pytest tests/test_adapters/test_regression_vectors.py -v`
   - Fails if any vector hash mismatches (other than the documented
     host-shift skip path)

2. **Add `regression-vectors/` to `.gitignore` exceptions** — the
   directory contents must be tracked. Specifically: DO track `*.json`
   vectors; DO NOT track `*.pyc` or `.cache/` subdirectories.

### Phase D — Per-adapter author discipline

Document the per-adapter discipline in `docs/PLUG_IN_YOUR_MODEL.md`:

> **Before any adapter ships, the author MUST capture a regression
> vector:**
> 1. Run `python scripts/capture_regression_vector.py --adapter <name>`
> 2. Commit the resulting `regression-vectors/<adapter>.json`
> 3. Add the adapter name to `tests/test_adapters/test_regression_vectors.py`
>    parametrise list
> 4. Verify CI passes locally: `pytest tests/test_adapters/test_regression_vectors.py -v`

## Files affected

- `adaptive_reflow/util/regression_vector.py` (NEW)
- `scripts/capture_regression_vector.py` (NEW)
- `tests/test_adapters/test_regression_vectors.py` (NEW)
- `regression-vectors/{flowmol3_v2,twodim_fm,lineageflow,kanzi,freqflow}.json` (NEW × 5)
- `tests/fixtures/{flowmol3_v2,twodim_fm,lineageflow,kanzi,freqflow}/sample_input.*` (NEW × 5)
- `.github/workflows/cpu-tests.yml` (UPDATE)
- `.gitignore` (UPDATE; exception for regression-vectors/*.json)
- `docs/PLUG_IN_YOUR_MODEL.md` (UPDATE; per-adapter discipline section)
- `docs/baseline-audit-report.md` §D.4 (UPDATE; mark 5/18 PARTIAL)
- `todo/framework-freeze-checklist.md` MUST-1 D.4 (UPDATE; 5/18 PARTIAL)

## Acceptance

- [ ] `adaptive_reflow/util/regression_vector.py` exists with `RegressionVector` dataclass
- [ ] `scripts/capture_regression_vector.py` exists, exits 0, captures SHA-256 hash
- [ ] `tests/test_adapters/test_regression_vectors.py` exists with 5 parametrised tests
- [ ] All 5 vectors captured (`regression-vectors/*.json` × 5)
- [ ] All 5 vectors reproduce identical hashes on the same host
- [ ] CI workflow `.github/workflows/cpu-tests.yml` runs the regression-vectors test
- [ ] `docs/PLUG_IN_YOUR_MODEL.md` documents the per-adapter discipline
- [ ] `docs/baseline-audit-report.md` §D.4 updated to "5/18 PARTIAL"
- [ ] `framework-freeze-checklist.md` MUST-1 D.4 entry updated to "5/18 PARTIAL"

## Acceptance gate

D.4 first-batch passes if:
1. All 5 vectors are reproducible (SHA-256 match on same host)
2. CI workflow runs + fails on simulated hash drift
3. Documentation reflects the per-adapter author discipline

Remaining 13/18 vectors to be planned in a follow-up wave (D.4 batch 2)
once this batch ships and the schema stabilizes.

## Estimated time

- Phase A (schema + harness): ~1-2 hours
- Phase B (capture 5 vectors): ~1 hour (CPU-only; most vector capture is fast)
- Phase C (CI integration): ~30 min
- Phase D (docs + checklist updates): ~30 min
- **Total**: ~3-4 hours

## Risk

- HF / ckpt unavailable for lineageflow / kanzi / freqflow → vector capture fails
  → **Mitigation**: ship with `skipped=true` field; CI skips that vector; the
  vector still exists in `regression-vectors/<adapter>.json` with a
  documented "capture requires <resource>" note
- Hardware shift between capture and CI → hash mismatch → **Mitigation**:
  the `host_fingerprint` field is captured; CI checks `host_fingerprint`
  and skips with documented message if hosts differ
- Adapter output is non-deterministic in `pytest.mark.stochastic-with-tolerance`
  → cannot hash byte-stable → **Mitigation**: pick a deterministic
  adapter subset for vectors; stochastic adapters use B.2 byte-stability
  only

## Follow-up (D.4 batch 2 — separate `todo/algo-improvement-D4-regression-vectors-batch2.md`)

13 remaining adapters:
- `mnist_fm` (CPU; easy)
- `rectified_flow_cifar` (GPU)
- `self_flow` (CPU)
- `wan2_2_video` (GPU; large)
- `mm_fm` (BLOCKED per Wave 21)
- `reference_flowa` (orphan per Wave 29)
- `stochastic_fm` (orphan per Wave 32 Agent A)
- `reference_*` (5 stub adapters)
- `prototype_*` (2 stub adapters)

Plan to be authored after batch 1 ships.
## Wave 38 close-out

CLOSED in Wave 38 by commit **b88b32f** (Wave 38 Agent A WF2).

**Result summary**:
- D.4 first batch shipped: 5 pinned regression-vector adapters discovered and gated. Note that the underlying vector artifacts were already shipped in earlier waves; this commit makes them test-discoverable + adds the gating test (so D.4 stops regressing silently when scheduler default changes — see Wave 34 default-scheduler flip).
- Wave 33 / Wave 34 / Wave 37 shipped subsequent D.4 batches; Wave 38's contribution is the *first* batch (5 adapters) as enumerated in this plan
- D.4 HARD gate now has byte-stable coverage for the 5 most-shipped adapters

**Files shipped** (see `git show --stat b88b32f` for the canonical list): the test file under `tests/test_regression/` + supporting harness in `tools/`. The 5 vector files live under `tests/_regression_vectors/` per F.5 env_hash conventions.

**Verification**: pytest runs deterministically + env_hash unchanged + commit (no push). Plan status flipped from `pending (Wave 33 target)` to CLOSED.

Refs: `framework-internal-metrics.md` §1 D.4 row, `docs/baseline-audit-report.md` D.4 counter.
