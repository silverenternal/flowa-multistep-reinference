# Phase 4 — Model integration iteration (one model at a time, in Phase 3 order)

**Status:** pending
**Depends on:** Phase 3 complete (all ranked models have glue + adapters +
tests). The "if Phase 1-3 done well, Phase 4 is just glue" property means this
phase is the EMPIRICAL VALIDATION of the framework's headline claim.
**Owner:** framework maintainer
**Goal:** for each model in Phase 3 order, run a baseline-vs-framework
comparison. If the framework wins on every model, the headline claim "any FM
model, when integrated into our framework, improves" is **supported**. If any
model regresses, **honest report** + return to Phase 1-3 to fix root cause.

## Acceptance metric table (BEFORE running any integration)

Define explicitly what "framework improves" means per model. Wave 10 LineageFlow
proved that "metric = 1.0 vs 1.0 = tie" is uninformative when the metric
saturates. So:

| Model | Domain | Primary metric | Secondary metric | Improvement bar | Saturation check |
|---|---|---|---|---|---|
| LineageFlow | protein | family_validity (95.3% paper) | amino_acid_diversity, log_likelihood | ≥ +0.5pp OR ≥ +5% relative | if both arms saturate at ceiling, declare TIE (not supported) |
| FreqFlow | image | FID on ImageNet-256 (SOTA 1.38) | inception_score | ≥ +0.05 FID OR ≥ +5% relative | if FID < 2.0, declare TIE (already SOTA) |
| MM-FM | image | FID on ImageNet-256 (SOTA 2.74) | inception_score | ≥ +0.1 FID OR ≥ +5% relative | if FID < 3.0, declare TIE (already SOTA) |
| Kanzi | protein | designability (paper 0.617) | scRMSD (3.655 Å) | ≥ +0.01 designability OR ≤ -0.05 Å scRMSD | if both metrics at paper-parity, declare ALREADY-SOTA |
| Flowception | video | FVD on UCF-101 | video quality score | ≥ +0.5 FVD OR ≥ +3% relative | if FVD < 50, declare ALREADY-SOTA |
| Purrception | image (VQ) | FID on ImageNet-256 | reconstruction FID | ≥ +0.1 FID | n/a (no paper baseline) |
| AG-REPA | audio | FAD (speech) | FAD (audio) | ≥ -2% FAD | if FAD < 5.0, declare ALREADY-SOTA |

### Verdict rules (per model)

- **supported**: primary metric Δ ≥ improvement bar (positive direction) AND
  not at saturation
- **partially_supported**: primary metric Δ = 0% (TIE) OR at saturation
- **not_supported**: primary metric Δ < 0% (regression) AND ≥ -5% relative
- **blocked**: cannot run real forward pass (ckpt missing, upstream source
  missing, env missing) — separate from supported/not_supported

### Headline claim status (aggregate)

| Verdict count | Status |
|---|---|
| All models: supported | "any FM improves" claim FULLY supported |
| Majority: supported, some: partial | claim QUALIFIED — "framework improves most FM models" |
| Any: not_supported | claim INVALID — back to Phase 1-3 to fix root cause |
| Any: blocked | claim UNVERIFIED — those models excluded from claim validation |

## Sub-tasks (per model, in Phase 3 order)

For each model `M`:

1. **Re-read per-model analysis** (`todo/models/M.md`).
2. **Run baseline 1-pass** — single forward, N samples, seed 42, capture metric
   value.
3. **Run framework multi-round** — Phase 3's adapter + CosineAnnealScheduler
   (or model-appropriate scheduler per Phase 2 analysis), N samples, same
   seed, capture metric value.
4. **Compare** — `framework_improves_baseline=True/False`, `delta_pct`.
5. **If True** — append to `docs/CONSOLIDATED_RESULTS.md` §"Phase 4
   integration results"; add CLM to `docs/CLAIMS.md`.
6. **If False** — investigate per Phase 1+2+3 quality:
   - Is Phase 1 (theory lift) correctly applied?
   - Is Phase 2 (analysis) missing something about this model's complexity?
   - Is Phase 3 (glue) correct?
   - Fix root cause in Phase 1-3, then re-run.
7. **Honest report** either way — do NOT fabricate numbers.

## Specific models to integrate (per Phase 2/3 order)

Pull from `todo/models/RANKING.md` (Phase 2 output). The order will be
determined by Phase 2's ranking. Likely candidates (in approximate ranking
order, not final):

1. **LineageFlow** (ICML 2026, protein) — Wave 10 partially done
2. **FreqFlow** (CVPR 2026, image SiT-XL/2) — likely smallest
3. **MM-FM** (CVPR 2026, image DiT-XL/2) — 160 GB repo, complex
4. **Kanzi** (ICLR 2026, protein) — GitHub-only weights
5. **Flowception** (CVPR 2026, video) — no public pretrained ckpts (might be skipped)
6. **Purrception** (ICLR 2026, image 7B VQ) — likely too big
7. **AG-REPA** (ICML 2026, audio) — new axis

## Acceptance gate (BINDING — see `todo/GATES.md`)

**Gate name:** `G-MASTER-PHASE-4` (defined in `todo/GATES.md`)

**Pre-condition:** `G-MASTER-PHASE-3` passed for the model being tested
AND `G-FRAMEWORK-HEALTH` hard gates pass (per
`todo/framework-internal-metrics.md` §3 — Phase 3 → Phase 4 entry gate:
A.3 ≥ 2, B.1 ≥ 3264, B.2/B.3/B.4 pass, C.2 ≥ 18).

**Pass conditions per model `M` (ALL must hold):**
- [ ] PHASE-4 acceptance metric table (top of this file) populated for `M`
      (primary metric, secondary metric, improvement bar, saturation check)
- [ ] `todo/PHASE-4-results/M/comparison.md` exists with baseline-vs-framework
      numbers
- [ ] The verdict (supported / partially_supported / not_supported / blocked)
      is recorded in `todo/models/M.md` §F
- [ ] If verdict = supported: a row is added to `docs/CONSOLIDATED_RESULTS.md`
      §7+ for `M`
- [ ] If verdict = not_supported: **STOP and return to Phase 1-3 to fix root
      cause** (per user "如果...实现做错了" hypothesis). Append a new
      `lessons-learned.md` entry explaining the regression.

**Pass conditions (aggregate, after all models tested):**
- [ ] All models in RANKING.md have a verdict
- [ ] `docs/CONSOLIDATED_RESULTS.md` reflects all verdicts in a summary table
- [ ] Headline claim status (per top of this file) is recorded honestly
- [ ] `git status --short` returns empty
- [ ] `todo/STATUS.md` is up-to-date

**Verification commands:**
```bash
cd /home/hugo/codes/flowa-multistep-reinference
for M in $(awk -F'|' '/^\| .*\| /{print $2}' todo/models/RANKING.md); do
  test -f "todo/PHASE-4-results/${M}/comparison.md" && echo "✓ $M comparison"
  grep -q "${M}" "todo/models/${M}.md" && echo "✓ $M verdict"
done
.venvs/flowmol3_venv/bin/python -m pytest --collect-only -q 2>&1 | tail -3
.venvs/flowmol3_venv/bin/mkdocs build --strict 2>&1 | tail -3
```

**Block rule:** if a per-model verdict is `not_supported`, the **whole Phase 4
is blocked** until root cause is fixed. This is the strictest gate — the
user's "framework has theory, if integration doesn't improve, must be
implementation wrong" hypothesis means we do NOT proceed past regression.

## Acceptance (per-model)

- For each model: baseline-vs-framework comparison.md in `todo/PHASE-4-results/M/`.
- One row added to `docs/CONSOLIDATED_RESULTS.md` §"Phase 4 integration results"
  per model.
- Honest summary at the end: "framework improved X / Y models; Z models showed
  regression — see `todo/PHASE-4-results/M/` for details".

## Exit criteria (move to paper writeup or terminate)

`G-MASTER-PHASE-4` passed for all ranked models (all verdicts recorded).

## Out of scope

- Push (handled by `push-unpushed-commits.md`).
- Paper writeup (handled by `paper-writeup.md`).
- Adding new SOTA models not in Phase 2 ranking.

---

## Wave 33 Phase 3 Agent I — current-state snapshot (2026-09-05)

**Wave:** 33 Phase 3 Agent I (PHASE-4 model integration iteration kickoff)
**Last updated:** 2026-09-05
**Author:** Wave 33 Phase 3 Agent I

### Push state

- `git log origin/main..HEAD --oneline` returns **87 unpushed commits**
  (Wave 12 at `e0238ab` is the latest on `origin/main`; local HEAD is
  `c11fd33`).
- `push-unpushed-commits.md` self-describes as "done (Wave 12 commit
  `e0238ab` pushed 2026-09-05; origin/main matches local HEAD)" — this
  is **stale / incorrect**. The file's verbatim check
  "`git log origin/main..HEAD --oneline` returns empty" does NOT hold
  at the time of this update; the divergence is 87 commits, not 0.
- Root cause: throughout Wave 13-33, user directive has been
  "不要 push" (don't push); the local-only state is intentional, but the
  `push-unpushed-commits.md` file was never re-checked or corrected.
- Per the task directive "PHASE-4 should only START if push succeeded (or
  push was deferred but framework is frozen locally)", the framework is
  **frozen locally** (see freeze-checklist below) and push was
  **deferred** per user directive — so PHASE-4 work can begin.

### Framework-freeze-checklist status (per `todo/framework-freeze-checklist.md`)

| MUST | Status | One-line evidence |
|---|---|---|
| MUST-1 G-FRAMEWORK-HEALTH HARD gates | **PASS** | 28/28 internal HARD gates PASS (Wave 33 Phase 3 final verify, commit `c11fd33`) |
| MUST-2 G-MASTER-PHASE-3 (4 RANKING models) | **PASS** (via BLOCKED-with-fallback rule) | Kanzi + FreqFlow delivered (Wave 21); MM-FM + LineageFlow BLOCKED with documented fallbacks; net 6+ working models covers G.4 ≥3 families |
| MUST-3 Framework-core glue extracted | **PARTIAL** | `adaptive_reflow/core/{ckpt_loader,diffusers_wrapper,graph_wrapper,vae_decoder}.py` + 84 tests ship; per-adapter refactor deferred (gated on all 4 RANKING adapters existing) |
| MUST-4 G-MASTER-CAPABILITY | **PASS** | `tools/capability_audit.py --robust` reports all 5 G-HARD verdicts = PASS (G.1 0.0884, G.3 -0.0251, G.4 3, G.6 0.25, G.7 7/7) |
| MUST-5 Pushed to origin/main | **NOT DONE** | 87 unpushed commits (local-only per user "不要 push" directive) |

**Freeze verdict:** framework is **frozen locally** (MUST-1/2/4 PASS, MUST-3
PARTIAL with public surface shipped, MUST-5 deferred). PHASE-4 per-model
work can begin for any model whose PHASE-3 prerequisites have passed.

### Per-model PHASE-4 status (Wave 33 Phase 3 Agent I)

Per `todo/models/RANKING.md` (sorted by combined_score ascending) and
the per-model analysis files:

| Rank | Model | PHASE-3 (adapter + tests + glue) | PHASE-4 (baseline-vs-framework) | Per-model status | Why |
|---|---|---|---|---|---|
| 1 | **Kanzi** (ICLR 2026, protein) | **DONE** (Wave 21 K agent) — `adaptive_reflow/adapters/kanzi.py` (1567 lines), `tests/test_adapters/test_kanzi.py` (26 tests), D.4 regression vector `regression-vectors/kanzi.json` pinned | **NOT-STARTED** | **READY** | PHASE-3 acceptance met; PHASE-4 blocked only on push (no actual code-level blocker) |
| 2 | **FreqFlow** (CVPR 2026, image) | **DONE** (Wave 21 F agent) — `adaptive_reflow/adapters/freqflow.py` (1477 lines), `tests/test_adapters/test_freqflow.py` (30 tests), D.4 regression vector `regression-vectors/freqflow.json` pinned | **NOT-STARTED** | **READY** | PHASE-3 acceptance met; PHASE-4 blocked only on push |
| 3 | **MM-FM** (CVPR 2026, image) | **BLOCKED** (Wave 21 M agent + Wave 21.5 re-spawn both stalled on all 6 attempts; 605k tokens consumed, 43 tool uses, 0 files produced) | **CANNOT START** | **BLOCKED** | PHASE-3 deliverable not produced; documented BLOCKED-with-fallback per freeze-checklist MUST-2 |
| 4 | **LineageFlow** (ICML 2026, protein) | **PARTIALLY_INTEGRATED** (Wave 10) — adapter ships, 22 tests pass, D.4 regression vector `regression-vectors/lineageflow.json` pinned, but real forward pass BLOCKED on missing upstream `core.sampler` source | **CANNOT START** (real-ckpt verdict) | **BLOCKED** | Wave 10 baseline-vs-framework = TIE (synthetic shim family_validity 1.0 vs 1.0); verdict = `partially_supported` per `todo/models/lineageflow.md` §F. Real-ckpt verdict requires GitHub access to `core` source repo (sandbox network-blocked). |

### Per-model PHASE-4 next steps

For each model whose status is **READY**, the per-model PHASE-4 task per
the spec at top of this file is:
1. Re-read `todo/models/<model>.md` (per-model analysis).
2. Define the PHASE-4 acceptance metric table (primary metric, secondary
   metric, improvement bar, saturation check) — **already populated at
   top of this file** for Kanzi + FreqFlow.
3. Run baseline 1-pass vs framework multi-round (matched NFE, same
   seed 42).
4. Compare; record verdict in `todo/PHASE-4-results/<model>/comparison.md`.
5. Update `todo/models/<model>.md` §F with the verdict.
6. If verdict = supported: add a row to `docs/CONSOLIDATED_RESULTS.md` §7+.
7. If verdict = not_supported: STOP, return to Phase 1-3 to fix root cause
   per user "如果...实现做错了" hypothesis; append a `lessons-learned.md`
   entry.

#### Kanzi (READY)

- **PHASE-4 acceptance metric table** (per top of this file):
  - Primary metric: designability (paper 0.617)
  - Secondary metric: scRMSD (3.655 Å)
  - Improvement bar: ≥ +0.01 designability OR ≤ -0.05 Å scRMSD
  - Saturation check: if both metrics at paper-parity, declare
    ALREADY-SOTA
- **Prerequisites**: PHASE-3 PASS (Wave 21 K agent); regression vector
  pinned; framework frozen locally; capability gates PASS
- **Outstanding actions**:
  1. Run baseline 1-pass: Kanzi adapter in single-pass mode (no
     framework glue), seed 42, N samples, capture designability +
     scRMSD
  2. Run framework multi-round: Kanzi adapter with CosineAnnealScheduler
     (or model-appropriate scheduler per Phase 2 analysis), N samples,
     same seed, capture metrics
  3. Compare; record verdict in `todo/PHASE-4-results/kanzi/comparison.md`
  4. Update `todo/models/kanzi.md` §F with the verdict + add CLM entry
     if supported
  5. **BLOCKER**: requires GitHub access to download Kanzi ckpts (the
     `rdilip/kanzi` repo weights — currently sandbox network-blocked);
     if GitHub unreachable, document as PHASE-4 BLOCKED with same
     fallback pattern as LineageFlow

#### FreqFlow (READY)

- **PHASE-4 acceptance metric table** (per top of this file):
  - Primary metric: FID on ImageNet-256 (SOTA 1.38)
  - Secondary metric: inception_score
  - Improvement bar: ≥ +0.05 FID OR ≥ +5% relative
  - Saturation check: if FID < 2.0, declare TIE (already SOTA vs SiT
    baseline FID ~1.96, ΔFID 0.58; near-saturation risk per RANKING.md
    note 3)
- **Prerequisites**: PHASE-3 PASS (Wave 21 F agent); regression vector
  pinned; framework frozen locally; capability gates PASS
- **Outstanding actions**:
  1. Run baseline 1-pass: FreqFlow adapter in single-pass mode, seed
     42, N samples (≥5000 per RANKING.md saturation note), capture FID
  2. Run framework multi-round: FreqFlow with CosineAnnealScheduler, N
     samples (matched), capture FID
  3. **FID computation requires GPU** (Inception-v3 + standard
     reference batch); FLAG as GPU-required task
  4. **Saturation risk** (FID 1.38 vs SiT baseline ~1.96): verdict may
     be `partially_supported` (TIE at saturation) per verdict rules
  5. **BLOCKER**: requires HF Hub / GitHub access for FreqFlow
     `nnet_ema.pth` ckpt (currently sandbox network-blocked); if
     unreachable, document as PHASE-4 BLOCKED with fallback

#### MM-FM (BLOCKED)

- PHASE-3 deliverable (adapter + 22 tests + PLUG_IN_YOUR_MODEL entry)
  never produced; Wave 21 + Wave 21.5 both stalled.
- Documented BLOCKED-with-fallback per freeze-checklist MUST-2 (existing
  adapters cover ≥3 model families; G.4 ≥3 satisfied with margin).
- **No PHASE-4 work possible** until MM-FM PHASE-3 deliverable ships.
- Re-spawn would require a different agent shape than the prior 6
  attempts (the per-adapter re-spawn has consistent infra failure per
  freeze-checklist MUST-2 narrative).

#### LineageFlow (BLOCKED on real forward pass)

- Wave 10 partial integration: adapter ships + 22 tests pass + D.4
  regression vector pinned.
- Real forward pass BLOCKED on missing upstream `core.sampler` source
  (sandbox network-blocked GitHub; HF ckpt loads but pickle references
  unresolved classes).
- Wave 10 verdict: `partially_supported` (TIE at saturation; synthetic
  shim family_validity 1.0 vs 1.0).
- Per PHASE-4 verdict rules: if both arms saturate at ceiling, declare
  TIE (not supported) — Wave 10 already returned this verdict.
- **No further PHASE-4 work possible** without GitHub access to the
  upstream `core` source.

### Outstanding follow-ups

| Action | Owner | Status | Notes |
|---|---|---|---|
| **Push 87 unpushed commits to origin/main** | framework maintainer (user) | **PENDING USER GO-AHEAD** | `push-unpushed-commits.md` self-describes as "done" but is stale; user has consistently directed "不要 push" throughout Wave 13-33. Until push authorized, all Wave 13-33 work is local-only. |
| **Re-verify `tools/capability_audit.py --robust`** after push | next wave's verify agent | NOT STARTED | Push does not invalidate audit tool output; the audit should re-run post-push on the new origin/main HEAD to confirm cold-clone reproducibility on the integrated branch |
| **PHASE-4 Kanzi comparison.md** | next wave's PHASE-4 Kanzi agent | NOT STARTED | Requires GitHub access to download `rdilip/kanzi` ckpts |
| **PHASE-4 FreqFlow comparison.md** | next wave's PHASE-4 FreqFlow agent | NOT STARTED | Requires HF Hub / GitHub access; GPU required for FID |
| **MM-FM PHASE-3 re-spawn** (different agent shape) | framework maintainer | NOT STARTED | Wave 21 + Wave 21.5 both failed; new approach needed |
| **LineageFlow upstream `core` source** | framework maintainer | NOT STARTED | GitHub access required; document as design-only integration if unreachable |
| **`push-unpushed-commits.md` stale-state fix** | next wave's documentation agent | NOT STARTED | The file's verbatim check "`git log origin/main..HEAD --oneline` returns empty" does NOT hold; needs a clarifying "DEFERRED per user directive 2026-09-05" addendum |

### Exit criteria (move to paper writeup or terminate)

`G-MASTER-PHASE-4` passed for all ranked models (all verdicts recorded).

### Wave 33 Phase 3 Agent I sign-off

- [x] PHASE-4 todo file updated additively (this section)
- [x] Per-model PHASE-4 status documented (READY / BLOCKED / NOT-STARTED)
- [x] Push state documented (87 unpushed; framework frozen locally;
      push deferred per user directive)
- [x] Follow-up actions enumerated (push, MM-FM re-spawn, LineageFlow
      upstream, push-unpushed-commits.md stale fix)
- [x] Commit (no push) — see `commit_sha` in agent return JSON