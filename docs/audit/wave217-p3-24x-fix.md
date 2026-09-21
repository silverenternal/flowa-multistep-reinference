# Wave 217 P3 — E1: 24.6× overhead fix-or-document decision

**Captured**: 2026-09-21
**Author**: Wave 217 P3 (E1 decision agent)
**Inputs**:
- `docs/audit/wave212-p6-root-cause.md` (root-cause synthesis)
- `docs/drafts/paper-flattened-draft.md` §5.5 (current efficiency narrative)
- `docs/audit/wave211-p1-efficiency-narrative.md` (per-cell efficiency table source)
- TPAMI pre-submission self-checklist (user-supplied 2026-09-21)
**Decision target**: E1 of the user-supplied TPAMI pre-submission checklist
("24.6× overhead 是否已修？只诊断还是已优化？决定 §5.5 最终文本 — 最高 / M")

---

## 1. Decision (one paragraph)

**Option B: document as future work; no code change to `adaptive_reflow/`.**
The §5.5 narrative at `docs/drafts/paper-flattened-draft.md` lines 338–360
already contains the complete Wave 212 P6 root-cause attribution (70 % of
the 178 s gap is GPU-side activation retention across the framework's 4
separate `batched_inference` calls; ~12 % is state-bundle SHA-256 +
CUDA-launch overhead; ~17 % is `inject_forward_noise` + `observe_endpoint`
per-round I/O) and already states the recommended fix path as a
20-engineer-hour `_fused_batched_inference` change to
`RectifiedFlowCIFARAdapter` that is mathematically equivalent to the
current 4-call sequence (same Euler step, same noise schedule,
byte-identical outputs per paired seed). The fix is left as future
work; D.4 byte-stability guarantee is preserved at submission time.

## 2. Why Option A was rejected

The harness's Option A description names a narrower scope than the
Wave 212 P6 root-cause recommendation:

| Aspect | Harness's Option A | Wave 212 P6 Path D |
|---|---|---|
| Scope | "Cache state-bundle digest across rounds in `BatchedTrajectoryRunner`" | "Cache intermediate forward outputs across rounds in CIFAR adapter" |
| Where the change lives | `adaptive_reflow/algorithm/runner/batched_runner.py` | `adaptive_reflow/adapters/rectified_flow_cifar.py` |
| Effort estimate | ~8 h | ~20 h |
| Estimated gap closure | ~6.7 % (state-bundle SHA-256 bucket only) | ~70 % (memory_swap category) |
| Risk to head-finding `d_z` | LOW (claimed) | NONE (proven by mathematical equivalence in root-cause §4) |

Three reasons Option A is not pursued at submission time:

1. **The harness's Option A scope targets the wrong category.** The
   dominant driver of the 178 s gap is GPU-side activation retention
   (~70 %), not state-bundle SHA-256 (~6.7 % per Wave 212 P6 §2.2
   attribution table). Caching the state-bundle digest in
   `BatchedTrajectoryRunner` would close ~12 s of the 178 s gap (6.7 %
   × 178 s) — a 7 % improvement on R5b 24.6× that is dwarfed by the
   framework's headline ~10× NFE compression vs baseline NFE=500 and
   would not move the per-sample wall-clock from 930 ms meaningfully.

2. **The 20-hour Path D fix touches `RectifiedFlowCIFARAdapter`** (the
   adapter that anchors the Wave 191 P2 N=1000 anchor for the R5b
   cross-budget FID headline). Applying it now would (a) require a
   full N=1000 GPU sweep re-run on `cuda:1` (RTX 5090) to re-verify
   byte-stability of the d_z chain (Wave 191 P2 → Wave 207 P6 → Wave
   209 P4 → Wave 212 P6), (b) re-validate all R5b head-finding
   Bonferroni verdicts under the new call sequence, (c) re-run D.4
   byte-stable regression (33/33 PASS gate) under the fused call. None
   of these is achievable in the pre-submission window without
   threatening the byte-stability guarantee.

3. **§5.5 already documents the future-work intent transparently.** The
   paragraph at line 360 names the recommended fix path, the expected
   impact (~125 s of the 178 s gap closed; per-sample wall drops from
   930 ms toward 400–500 ms; cross-budget NFE compression vs baseline
   NFE=500 reaches ≈3× in wall-clock terms), and the effort estimate
   (~20 engineer-hours, scoped narrowly to `RectifiedFlowCIFARAdapter`).
   Reviewers reading the paper at submission time see the diagnosis,
   the recommended fix path, and the future-work commitment; they do
   not see a claim that the framework is faster than it is.

## 3. Verification that §5.5 already documents this correctly

`docs/drafts/paper-flattened-draft.md` lines 338–360 (current text):

> ### 5.5 Efficiency narrative: wall-clock, FLOPs, and matched-compute framing
>
> ...
>
> **Per-cell efficiency table** (line 346–354): R5b CIFAR-10 RF baseline
> 37.83 ms vs framework 930.52 ms = **24.60×** at matched NFE=50.
>
> **Reviewer question answered** (line 358): "the engineering roadmap
> is: (a) cache scheduler state across rounds (~50 ms -> ~5 ms per
> round, ~13% reduction); (b) parallelise paper-quantity computation
> onto a secondary CUDA stream (~3-4 ms per round, ~2% reduction); (c)
> `torch.compile` the `LinearBlender` and merge operator (~20 ms per
> round, ~9% reduction). Combined, R5b CIFAR framework per-sample wall
> drops from 930 ms to ~720 ms..."
>
> **Root-cause attribution for the 178 s framework overhead at the R5b
> N=1000 anchor** (line 360): "The diagnostic conclusion: the 178 s
> overhead is **not** dominated by the framework's per-component
> orchestration cost... The dominant driver — accounting for **~70 %
> of the 178 s gap** — is **GPU-side activation retention across the
> framework's 4 separate `batched_inference` calls**... The
> recommended fix path is to **cache intermediate forward outputs
> across rounds** by adding a fused `_fused_batched_inference(n=64,
> nfe_per_round=12, rounds=4)` method on the CIFAR adapter that runs
> all 4 rounds' NFE in a single shared CUDA kernel-launch context...
> Expected impact: ~125 s of the 178 s gap closed, R5b framework
> per-sample wall drops from 930 ms toward ~400–500 ms... Effort:
> ~20 engineer-hours, scoped narrowly to `RectifiedFlowCIFARAdapter`."

**Verified**: the §5.5 text is complete, technically correct, and
explicit about the future-work status of the fix. No §5.5 edits are
needed at submission time. The audit doc and commit for E1 therefore
mark the checklist item as **diagnose-only** with §5.5 finalised.

## 4. The harness's Option B paragraph vs the existing §5.5 paragraph

The harness's Option B suggested-paragraph states:

> "The wall-clock overhead of the framework is dominated by per-round
> CUDA kernel launch overhead and state-bundle SHA-256 hashing on the
> 3072-element image tensor × 4 rounds × 1000 records."

This **contradicts** the Wave 212 P6 root-cause analysis: state-bundle
SHA-256 is ~6.7 % of the 178 s gap, not the dominant driver. The §5.5
paragraph at line 360 correctly attributes the dominant driver to
**GPU-side activation retention across the 4 separate
`batched_inference` calls** (~70 % of the gap). Inserting the
harness's Option B paragraph would create an inconsistent attribution
between the root-cause paragraph and the Option B paragraph, weaken
the paper's honesty about where the overhead comes from, and expose
the paper to reviewer pushback ("you said the dominant driver is X
here and Y there — which is it?").

**Action taken**: the harness's Option B paragraph is **NOT** added to
§5.5. The existing §5.5 paragraph (line 360) is the authoritative
disclosure; it stays as-is.

## 5. E1 checklist status (the user-facing answer)

| Checklist item | Status at submission time |
|---|---|
| E1: 24.6× overhead 是否已修？ | **No — diagnosis only**. The 178 s overhead at R5b N=1000 is fully diagnosed (Wave 212 P6); the fix is left as documented future work (~20 engineer-hours, scoped narrowly to `RectifiedFlowCIFARAdapter`). |
| §5.5 最终文本 | **Finalised**. The root-cause attribution, the engineering roadmap, and the future-work fix path are all stated explicitly at lines 358 and 360 of `docs/drafts/paper-flattened-draft.md`. |
| D.4 byte-stable regression 33/33 PASS | **Preserved**. No change to `adaptive_reflow/`; the 33/33 PASS gate stays at submission time. |
| Risk to head-finding `d_z` (R5b cross-budget, R5b matched-NFE=50 boundary, etc.) | **None**. Path D (the only fix that would close a meaningful fraction of the gap) is not applied; existing d_z values from Wave 191 P2 / Wave 207 P6 / Wave 209 P4 / Wave 212 P6 are unchanged. |

## 6. Post-submission engineering roadmap (recorded for the record)

If the framework is revisited post-submission, the recommended fix
path is the Wave 212 P6 Path D — cache intermediate forward outputs
across rounds by adding `RectifiedFlowCIFARAdapter._fused_batched_inference(n=64,
nfe_per_round=12, rounds=4, seed_schedule=[0,1,2,3])` that runs all
4 rounds × 12 NFE in a single `solve_ode` call shape with shared
kernel-launch context. Acceptance gates:

1. CIFAR adapter `_fused_batched_inference` implementation is
   byte-identical to the 4-call sequence under paired seed (asserted
   by a new unit test `test_fused_batched_inference_byte_identical`).
2. Framework loop in `R5bCIFARRFDriver` calls the fused variant when
   round plan matches (4 × 12 NFE).
3. N=1000 sweep re-run on RTX 5090 (`cuda:1`); framework wall-clock
   drops from ~900 s toward ~500 s (≈55–60 % gap reduction).
4. Head-finding `d_z` byte-identical to Wave 191 P2 anchor (per-record
   paired difference check; must match anchor to all reported digits).
5. D.4 byte-stable regression suite re-run; 33/33 PASS gate retained.

Effort: ~20 engineer-hours. See `docs/audit/wave212-p6-root-cause.md`
§3.2 and §5 for the full breakdown.

## 7. Summary for the parent agent

| Question | Answer |
|---|---|
| Option chosen | **B (document as future work)** |
| Code change to `adaptive_reflow/` | **No** |
| §5.5 updated | **No** (existing §5.5 is already correct and complete; the harness's suggested Option B paragraph would contradict the root-cause attribution and is intentionally not added) |
| D.4 byte-stability 33/33 PASS preserved | **Yes** |
| Risk to head-finding `d_z` | **None** |
| E1 checklist item | **Marked as diagnose-only; §5.5 finalised** |

## 8. Outputs

* `docs/audit/wave217-p3-24x-fix.md` (this doc) — the decision record.
* No code change to `adaptive_reflow/`.
* No change to `docs/drafts/paper-flattened-draft.md` §5.5 (the
  existing text is already correct).
* No re-run of R5b N=1000 sweep (the byte-stability guarantee and
  the Wave 191 P2 d_z anchor are preserved as-is).

## 9. References

* `docs/audit/wave212-p6-root-cause.md` — root-cause synthesis (the
  diagnostic anchor for this decision).
* `docs/drafts/paper-flattened-draft.md` lines 338–360 — the §5.5
  final text (already documents root-cause + future-work fix path).
* `docs/audit/wave211-p1-efficiency-narrative.md` — per-cell
  efficiency table source (line 79 for the 24.6× figure).
* Wave 191 P2 anchor — R5b CIFAR-10 RF N=1000 sweep (the d_z chain
  preserved at submission time).
* Wave 217 P1 (`wave217-p1-security-scan.md`) — E4 unpushed-commits
  security scan PASS, completed prior to this decision.
* Wave 217 P2 (`wave217-p2-public-audit.md`) — pre-public content
  audit PASS, completed prior to this decision.