# Wave 43 — Concrete problems review (post Wave 41/42)

**Date:** 2026-09-05
**Status:** pending (specific problems identified; ultracode launch next)
**Source:** Wave 41 + Wave 42 + Wave 40 + Wave 39 results
**Owner:** framework maintainer

This is the **master review** of what's actually broken or incomplete as of 2026-09-05
end-of-Wave-42. Each problem has:
- Symptom (what user/agent sees)
- Root cause (the actual underlying issue)
- Scope (which files / which systems)
- Proposed fix (concrete steps)
- Acceptance gate (how we know it's fixed)
- Wave-43 owner (which workflow agent handles it)

---

## Problem 1 — `_compute_metric` always returns synthetic ceiling (TOP-MODEL CLAIM BLOCKER)

**Symptom**: After Wave 42 WF1 Agent A + Agent B ran `--force-mode real` on Kanzi + LineageFlow
in sidecar venvs, all 9 + 1 cells report `adapter_mode='torch'` (real-ckpt path confirmed).
BUT every cell's `status = TIE_AT_SATURATION` and `framework_wins = 0` because the per-cell
metric value is identical on baseline and framework (0.95 for Kanzi, 0.999 for LineageFlow).

**Root cause**: `tools/run_real_ckpt_eval.py:_compute_metric()` (lines 531-579 per Wave 36 Agent D
audit) is **hard-wired** to return `saturation_threshold` for both arms regardless of what the
real forward pass produces. The force_mode plumbing worked, but the metric layer is fake.

This is **the single blocker** for closing the "framework improves all flow matching models"
top-tier claim. Wave 36 Agent D designed this as the "trivial reading" synthetic fallback,
intended to be replaced with real metric computation when sidecar deps are ready. Wave 41 Agent B
flagged this as a deferred gate. **It needs fixing now.**

**Scope**:
- `tools/run_real_ckpt_eval.py` (only)
- Specifically `_compute_metric()` and the factory wiring for the per-model metric call
- The forward pass and force_mode plumbing are correct (no change needed there)

**Proposed fix**:
1. For Kanzi: compute real `protein_sequence_validity_rate` by decoding token indices via
   the Kanzi adapter's tokenizer, then checking via Bio.SeqIO that each sequence round-trips
   through the Pfam reference (needs Pfam subset, see Problem 2)
2. For LineageFlow: compute real `family_validity_rate` via the LineageFlow model's own
   Pfam-family classifier output (not via HMMER — that's a deferred alternative)
3. Wire to `_compute_metric(model_name, baseline_output, framework_output, paper_quantities)`
   with model-specific branches
4. Preserve the synthetic fallback as a `--metric-mode synthetic` flag for non-sidecar venvs
   (so CI keeps passing without ESM-2/Pfam)

**Acceptance gate**:
- 9 Kanzi cells run with `--force-mode real --metric-mode real` produce a non-zero
  per-cell `delta_pct` if framework is better than baseline
- 1+ LineageFlow cell same
- `framework_wins > 0` on real Kanzi AND/OR real LineageFlow
- Old synthetic path still works for CI

**Wave 43 owner**: WF1 Agent A (1 agent, ~30 min)

---

## Problem 2 — Sidecar deps for real downstream metrics

**Symptom**: Wave 41 Agent B + Wave 42 Agent A both reported that
`protein_sequence_validity_rate` (Kanzi) and `family_validity_rate` (LineageFlow) cannot be
computed because of missing sidecar deps.

**Reality check** (this scan):
- `esm` 2.0.0 IS installed in `.venvs/kanzi_venv/` ✅ (Agent B was wrong about this)
- `kanzi` 0.1.0 IS installed ✅
- `torch` 2.14.0+cu130 ✅
- `biopython` IS installed ✅ (via `from Bio import SeqIO`)
- `rdkit` NOT installed (probably not needed for Kanzi tokenizer)

**Missing for real Kanzi metric**:
- **Pfam held-out reference subset** — no `.fasta` file exists in `data/`. Found:
  `data/lineageflow_upstream/dataset/pfam_dataset.py` (Python source, not data) and
  `data/protbfn_abbfn/repo/example_inputs/sequences.fasta` (sample input, not held-out).

**Missing for real LineageFlow metric**:
- HMMER, OmegaFold, MMseqs2, ESM-IF — none of these installed anywhere in the project.
  However: the LineageFlow model's own Pfam-family classifier output should suffice as the
  primary signal (entropy=2.266/2.996 ceiling is already available via Wave 41 numerical
  forward); family_validity_rate is the secondary metric.

**Scope**:
- `.venvs/kanzi_venv/` (add Pfam reference subset)
- `data/kanzi/` (new directory for Pfam subset) or `data/protbfn_abbfn/repo/example_inputs/`
  (reuse existing fasta)
- `.venvs/lineageflow_venv/` (no new deps; use the model's own classifier)

**Proposed fix**:
1. Download a small Pfam held-out subset (e.g. 100-500 sequences from a single Pfam clan
   via https://ftp.ebi.ac.uk/pub/databases/Pfam/) into `data/pfam_holdout/random_clan.fasta`
   — light bandwidth (~1 MB), no big install
2. Wire `protein_sequence_validity_rate` to read `data/pfam_holdout/random_clan.fasta` and
   round-trip check via Bio.SeqIO
3. For LineageFlow: keep using the model's own classifier output (already works via
   `tools/run_lineageflow_real_ckpt.py`); no extra deps needed

**Acceptance gate**:
- `data/pfam_holdout/` contains ≥1 fasta with ≥100 sequences
- `protein_sequence_validity_rate` can be computed without ImportError
- Both sidecar venvs can compute their primary real metric

**Wave 43 owner**: WF1 Agent B (1 agent, ~20 min)

---

## Problem 3 — Pytest pollution from Wave 42 D.1 shrink + remaining per-adapter refactor

**Symptom**: Wave 40 Agent B (Phase 4 long-running) found 1 WAVE-42-INTRODUCED UNCOMMITTED failure
(`rectified_flow_cifar.py` lost `from collections import OrderedDict` during Wave 42 Agent C's
D.1 shrink work). Wave 41 Agent D confirmed 1 failure in test_adapters: `test_make_ref_prefixes_are_unchanged`
owned by Wave 42 Agent A.

**Root cause**: Parallel D.1 shrink agents modified files concurrently without adequate
pre-flight coordination; 1-2 imports got dropped.

**Also**: Wave 42 WF2 (must3-shrink) is in-flight shrinking 4 adapters (mnist_fm, twodim_fm,
rectified_flow_cifar, self_flow). Each shrink is supposed to remove inlined glue and depend on
`adaptive_reflow/core/` modules. We need to verify:
- All 4 commits landed without breaking pytest
- Per-adapter test count is preserved
- Per-adapter LOC went down

**Scope**:
- Wave 42 Agent C commit (rectified_flow_cifar OrderedDict loss)
- Wave 42 Agent A commit (test_make_ref shim loss in some test)
- Wave 42 WF2 background work (4 shrink commits)

**Proposed fix**:
1. Restore `from collections import OrderedDict` in `rectified_flow_cifar.py`
2. Restore the `_make_ref` shim (or update the test to not reference it)
3. Verify all Wave 42 D.1-shrink commits preserve pytest

**Acceptance gate**:
- Full pytest (`tests/`) passes 0 regressions vs Wave 38 baseline (1017 passed, 110 skipped)
- All 16 registered adapters pass `assert_adapter_compliance`
- per-adapter LOC reduction is preserved for the 4 shrunk adapters (mnist_fm, twodim_fm,
  rectified_flow_cifar, self_flow)

**Wave 43 owner**: WF2 Agent A (1 agent, ~20 min)

---

## Problem 4 — Paper writeup with Tier 3 (Kanzi + LineageFlow) results + figure

**Symptom**: docs/CONSOLIDATED_RESULTS.md §15.8 (Kanzi) + §15.9 (LineageFlow) have raw per-cell
tables but the **paper writeup** (docs/paper-draft.md or wherever) hasn't been updated with
Tier 3 results. Wave 42 WF3 paper-writeup agents should be doing this in-flight, but verify.

**Root cause**: Paper §4.x hasn't integrated the Tier 3 (real-ckpt on top-venue 2026) evidence.
Tier 1 (toy) and Tier 2 (CIFAR-10 RF NeurIPS Spotlight) are in the paper but Tier 3 is missing.

**Proposed fix**:
1. APPEND §Tier 3 to docs/paper-draft.md (or wherever the paper is) with:
   - One-sentence claim statement
   - Kanzi ICLR 2026: per-cell table + verdict (post metric-layer fix)
   - LineageFlow ICML 2026: per-cell table + verdict (post metric-layer fix)
   - Honest verdict block (what's closed vs what's still pending)
2. Generate `docs/figures/tier3_real_ckpt_signed_mean.png` (horizontal bar chart:
   families × signed_mean × tier-colored)
3. Cross-link from CONSOLIDATED_RESULTS §15 to the paper section

**Acceptance gate**:
- Paper has explicit Tier 3 section with Kanzi + LineageFlow per-cell tables
- `docs/figures/tier3_real_ckpt_signed_mean.png` exists
- Figure.md is referenced from the paper + CONSOLIDATED_RESULTS

**Wave 43 owner**: WF2 Agent B (1 agent, ~30 min)

---

## Problem 5 — Push 156 unpushed commits (user-gated)

**Symptom**: `git log origin/main..HEAD --oneline | wc -l = 156`. Per Wave 40 Agent A the count
was 129; Wave 41 + Wave 42 added ~27 more.

**Root cause**: User standing directive "do not push" from Wave 33 Agent H. User has not yet
given push authorization.

**Proposed fix**: User says "push" → I run `git push origin main` (~10s)

**Acceptance gate**: `git log origin/main..HEAD | wc -l = 0` after push.

**Wave 43 owner**: User (1 action, ~10s)

---

## Problem 6 — MUST-3 PARTIAL → PASS (per-adapter core adoption)

**Symptom**: framework-freeze-checklist.md shows MUST-3 = PARTIAL (4 core modules + 84 tests;
per-adapter adoption = 1 hit after Wave 41 Agent B shrunk flowmol3). Wave 42 WF2 background is
shrinking 4 more adapters (mnist_fm, twodim_fm, rectified_flow_cifar, self_flow).

**Root cause**: Pre-Wave-41, 0 adapters depended on `adaptive_reflow/core/`. Wave 41 Agent B added
flowmol3 as consumer 1. Wave 42 should add 4 more.

**Proposed fix** (mostly already in-flight):
1. Verify Wave 42 WF2 lands 4 more shrinks successfully
2. Per-adapter LOC reduction confirmed (Wave 41 Agent B: 276→264 = -12 lines for flowmol3;
   target ~50-200 lines saved for the 4 bigger adapters)
3. All 16 registered adapters still pass `assert_adapter_compliance`
4. Update framework-freeze-checklist.md MUST-3 to PASS once verified

**Acceptance gate**:
- ≥5 adapters import from `adaptive_reflow/core/` (1 from flowmol3 + 4 from Wave 42)
- Per-adapter LOC reduction across the 5 shrunk adapters
- 0 pytest regressions
- MUST-3 status = PASS in framework-freeze-checklist.md

**Wave 43 owner**: WF2 Agent A (combined with Problem 3) + Wave 42 WF2 verify

---

## Wave 43 ultracode plan

| WF | Agents | Problem | Key outputs |
|---|---|---|---|
| **WF1 metric-layer** | 2 (parallel) | P1 + P2 | `_compute_metric` real + Pfam subset + non-zero framework_wins |
| **WF2 cleanup-and-paper** | 2 (parallel) | P3 + P4 + P6 | pytest fix + paper §Tier 3 + figure + MUST-3 finalize |
| **WF3 push-prep** | 1 | P5 | final verify + push-ready summary (does NOT push — user-gated) |

Total: 5 agents across 3 workflows.

---

## Remaining NOT in this wave (longer-term follow-ups)

- **D.1 shrink 4 NEW big adapters**: flowmol3_v2 (3272 LOC), protbfn_abbfn (2168), hidream_i1 (1980),
  kanzi (1755). These are the real D.1 win. Future wave.
- **HF model card upload R-3 manual step**: deferred per Wave 38 Agent A note ("requires HF token").
  Future wave if user provides token.
- **CI on multiple GPU/CPU architectures**: deferred.
- **MMCY Tier 3 (HiDream, Lumina, Wan2.2, ProtBFN) real-ckpt framework-vs-baseline**: deferred —
  need real ckpts for each + GPU access. User currently has Wave 42 in-flight on Kanzi/LineageFlow
  which are the priority Tier 3 2026 venues.