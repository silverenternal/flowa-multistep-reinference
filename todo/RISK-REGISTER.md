# `todo/RISK-REGISTER.md` — forward-looking risks + mitigations

> **HISTORICAL — not the primary management surface.** The live project state and
> history are in [`WAVES.md`](WAVES.md); this file is retained for provenance and
> its state pins (HEAD, gate counts) may predate the current HEAD.

**Date:** 2026-09-25 (last append: Wave 347 governance refresh — R-016..R-022 appended; original 2026-09-05 baseline preserved verbatim below)
**Purpose:** catalog risks that **could** happen (different from
`lessons-learned.md` which records risks that **did** happen). Each risk has
severity, trigger, mitigation. Append-only.

---

## R-001 — HuggingFace rate-limit or block during weight download

**Severity:** medium (frequent; 2-3 occurrences in Wave 6-10 history)
**Trigger:** `hf download` returns HTTP 429 (Too Many Requests) or 0 (blocked)
**Mitigation:**
1. Try `hf_hub_download` directly with explicit `token=None, headers={"User-Agent": "Mozilla/5.0"}`
2. Fall back to `git clone https://huggingface.co/<repo> data/<dir>` (LFS-aware)
3. If both fail: mark model as "design-only" and skip integration
**Owner:** Claude (per wave's setup agent)
**Recurrence:** 3+ times in this session (Wave 6 R6, Wave 10 setup, R5 control)

## R-002 — GitHub source repo not reachable from sandbox

**Severity:** high (the LineageFlow BLOCKED case)
**Trigger:** `git clone` to GitHub times out or returns network unreachable
**Mitigation:**
1. Try `WebFetch https://github.com/<owner>/<repo>` to read README + tree
2. Check arXiv abstract for code link (some papers post code on arXiv)
3. Search `https://paperswithcode.com/` for the paper
4. If all fail: declare model "design-only" + record reason in
   `todo/models/M.md` §F
**Owner:** Claude (per wave's setup agent)
**Recurrence:** Wave 10 LineageFlow (root cause of BLOCKED verdict)

## R-003 — Pretrained ckpt 10× larger than research estimate

**Severity:** medium (already happened: LineageFlow 9.788 GB vs "sub-GB" claim)
**Trigger:** actual downloaded ckpt size differs significantly from research
estimate
**Mitigation:**
1. **VERIFY file size on HF Hub before launching download** — use
   `huggingface_hub.HfApi().list_repo_files()` to enumerate files + sizes
2. Compare against GPU memory budget: `32 GB (5090)` or `98 GB (PRO 6000)`;
   reject any model with ckpt > 30 GB (5090) or > 80 GB (PRO 6000)
3. If ckpt too big: check for fp16/bf16 quantized versions; if none, skip
**Owner:** Claude (per wave's research + setup agents)
**Recurrence:** Wave 9 R3 + Wave 10 (both LineageFlow estimate errors)
**Linked LL:** LL-001 + LL-003

## R-004 — Upstream `core` source repo not published

**Severity:** critical (Wave 10 LineageFlow was BLOCKED for this reason)
**Trigger:** ckpt loads but `pickle.load` fails with `ModuleNotFoundError: No
module named 'core'`
**Mitigation:**
1. **Phase 2 (per-model analysis) must check upstream source availability
   BEFORE scheduling a wave** — see `todo/models/README.md` §C template
2. If upstream source is missing: declare model "design-only", skip the wave
3. If upstream source is on GitHub but not from a major org: check arXiv
   supplementary, project page, or author contact
**Owner:** Claude (Phase 2 analyst)
**Recurrence:** LineageFlow (Wave 10) — single occurrence but high impact
**Linked LL:** LL-001

## R-005 — metric_saturation invalidates comparison (TIE verdict)

**Severity:** medium (Wave 10 LineageFlow had this issue)
**Trigger:** both arms of baseline-vs-framework report the same metric value
(e.g., family_validity=1.0 vs 1.0)
**Mitigation:**
1. **Per-model acceptance metric table** (now in `PHASE-4-model-integration-iteration.md`)
   includes a "Saturation check" column
2. If primary metric saturates, use secondary metric (e.g., inception_score
   instead of FID when FID < 5.0)
3. If both metrics saturate: declare TIE = partially_supported, NOT supported
**Owner:** Claude (Phase 4 comparison agent)
**Recurrence:** Wave 10 LineageFlow
**Linked LL:** LL-002

## R-006 — dgl 2.1.0 unavailable on Python 3.12

**Severity:** high (FlowMol3 sidecar dependency; historical issue)
**Trigger:** `pip install dgl==2.1.0` fails with "no matching distribution"
**Mitigation:**
1. Check if dgl 2.4+ supports the model's required ops (most do)
2. If not: build Python 3.11 sidecar at `/home/hugo/.venv-flowmol311` via
   `uv venv --python 3.11`
3. Wire `tools/run_mol_eval_safe.py` to dispatch the sidecar subprocess
4. If sidecar build also fails: declare model "design-only"
**Owner:** Claude (per wave's setup agent)
**Recurrence:** Wave 8 I5 + Wave 10 setup

## R-007 — flash-attn needed but not installable

**Severity:** medium
**Trigger:** newer DiT-based models (Lumina, HiDream) need flash-attn; pip
install fails on the sandbox
**Mitigation:**
1. Use PyTorch's native `scaled_dot_product_attention` (works on most GPUs)
2. If model REQUIRES flash-attn: run on PRO 6000 (98GB) where flash-attn
   builds from source; skip 5090 path
3. Or use xformers as drop-in alternative
**Owner:** Claude (per wave's setup agent)
**Recurrence:** None observed in this session (yet)

## R-008 — Paper-axis gaps (vocab / metric / protocol mismatch)

**Severity:** high (FlowMol3 CTMC-vs-linear-interpolant gap is documented)
**Trigger:** framework's metric computation gives different numbers from paper's
**Mitigation:**
1. **Phase 2 per-model analysis** must check the paper's metric definition vs
   framework's metric (selection_ratio vs validity vs FID vs log-likelihood)
2. If gap exists: record in `todo/models/M.md` §C as "paper-axis gap" + how
   to handle
3. Honest reporting: don't claim "framework improves over paper baseline" if
   metric definitions differ
**Owner:** Claude (Phase 2 analyst + Phase 4 comparison agent)
**Recurrence:** FlowMol3 CTMC gap (Wave 6 R5); CIFAR-10 RF v4 (Wave 6)

## R-009 — dgl / torch geometric compatibility with torch upgrade

**Severity:** low
**Trigger:** upgrading torch breaks dgl or torch_scatter
**Mitigation:**
1. **DO NOT upgrade torch unless absolutely needed** — current venv is
   `torch 2.7.0+cu128 + dgl 2.4.0+cu124` (working)
2. If upgrade needed: do it in a separate venv + sidecar
**Owner:** Claude (per wave's setup agent)
**Recurrence:** None (yet)

## R-010 — Mkdocs --strict warnings on new doc edits

**Severity:** low (every doc edit must pass strict mode)
**Trigger:** adding new docs without updating mkdocs.yml nav
**Mitigation:**
1. Per the Wave 2 P2-11 pattern: add new doc to mkdocs.yml `not_in_nav` OR
   to the `nav:` block
2. Run `mkdocs build --strict` BEFORE commit
3. If a doc has orphans: append to not_in_nav (per existing pattern)
**Owner:** Claude (every wave's verify agent)
**Recurrence:** P2-11 (Wave 2); Wave 3 F-P0-2

## R-011 — Working tree dirty at end of wave (untracked files, bak files)

**Severity:** low
**Trigger:** agents create `todo.json.bak`, `docs/_benchmark_ablation.md`,
untracked PyCache directories
**Mitigation:**
1. Add `.gitignore` entries for `*.bak`, `docs/_*.md`, `__pycache__/`
2. Per-wave verify agent must `git status --short` and clean up
**Owner:** Claude (every wave's verify agent)
**Recurrence:** Wave 2, Wave 8, Wave 10

## R-012 — User-explicit direction changes scope

**Severity:** N/A (process risk, not technical)
**Trigger:** user changes the 4-phase plan, e.g., "skip Phase 2, do Phase 3 directly for LineageFlow"
**Mitigation:**
1. The LOOP.md / GATES.md / TIMELINE.md are **advisory**, not contract
2. When user redirects, update the relevant todo files to match
3. Don't restart waves that completed successfully just because the plan
   changed
**Owner:** Claude (or human) at every user turn

## R-013 — Workspace state diverges between sandbox and main branch

**Severity:** medium
**Trigger:** Wave runs in background and modifies `docs/ABLATION.md`,
`docs/benchmark-uplifts.md`, or other tracked files in-place (Wave 6 R1+R2
did this)
**Mitigation:**
1. After wave completes, `git status --short` to find unstaged tracked files
2. Decide: keep (commit) or revert (`git checkout -- <file>`)
3. Per user "什么都不动" directive: prefer REVERT for unintended changes
**Owner:** Claude (post-wave cleanup)
**Recurrence:** Wave 6 R1 + R2 overwrote docs/ABLATION.md + docs/benchmark-uplifts.md

## R-014 — Long-running wave hits OOM despite 28e3bf9 defenses

**Severity:** low (defenses in place + 80% abort threshold)
**Trigger:** subprocess exceeds RLIMIT_AS cap or GPU memory > 80%
**Mitigation:**
1. Per wave's setup agent: set `--cap-gb 24` (or 48 for big ckpt) on
   `tools/run_mol_eval_safe.py`
2. Monitor GPU memory with `nvidia-smi --query-gpu=memory.used -l 5` every 5s
3. If approaching limit, abort the subprocess
**Owner:** Claude (per wave's setup + run agents)
**Recurrence:** None (yet) thanks to defenses

## R-015 — Honest reporting suppressed by "make it work" pressure

**Severity:** low (process risk)
**Trigger:** when framework regresses, temptation is to hide or rationalize
the negative result
**Mitigation:**
1. **Per user directive**: "文档诚实记录" — always report negative results
2. Use "blocked" verdict for things that can't run; do NOT claim "supported"
3. Use "partially_supported" for ties at saturation; do NOT claim "supported"
4. Use "not_supported" for regressions; do NOT claim "supported"
5. When in doubt, log to `lessons-learned.md` with the actual numbers
**Owner:** Claude (every agent that produces a verdict)
**Recurrence:** N/A (preventive)

---

## R-016 — dgl 2.4.0 batched-path bug (Wave 187-216 multi-wave defect)

**Severity:** high (FlowMol3 + LineageFlow sweeps BLOCKED across 30 waves)
**Trigger:** dgl 2.4.0 batched-graph propagation introduced in Wave 187 to fix
B.1 (batched MPNN message-passing) — but the fix introduced a silent
per-channel mean-pool bug that only surfaces when batch size > 1 AND
`per_channel_jitter_std > 0`. The bug was masked by per-seed paired-t
testing at N=200 across single-seed sweeps; it surfaced only when Wave 216
P5 cross-seed N=1000 index-matched two-sample t tests reported systematic R2 (Kanzi) framework
REGRESSIONS on seeds 43/44. Per Wave 260 + Wave 262 defensive-patch revert,
the canonical mitigation is `python3 -c "import dgl; print(dgl.__version__)"
== 2.1.0` only for FlowMol3 sweeps (lineageflow_n1000 uses dgl 2.4.0 with
manual `_pool_per_channel` workaround).
**Mitigation:**
1. Per Wave 187 defect-postmortem (`docs/audit/flowmol3/wave208-p2-flowmol3-dgl-fix-or-sanity.md`):
   all FlowMol3 sweeps must use dgl 2.1.0 sidecar venv `flowmol3_venv`
2. LineageFlow N=1000 uses dgl 2.4.0 with explicit per-channel mean-pool
   workaround at `adaptive_reflow/adapters/lineageflow/_pool.py:74`
3. N=200 paired-t single-seed is INSUFFICIENT to catch this bug — always
   include 3-seed cross-seed N=1000 paired-t test on new framework paths
4. Per Wave 308 P1 lesson: framework-fallback contamination on seeds 43/44
   (silent path-fallback when per-seed FASTA generator missing) was
   MASKING the same multi-wave defect class — add explicit
   `seed_fallback_detected` column to all paired-t CSVs
**Owner:** Claude (every FlowMol3 + LineageFlow sweep setup agent)
**Recurrence:** Wave 187-216 (single occurrence, multi-wave duration;
30+ waves affected before root-cause isolated)
**Linked LL:** Wave 187 P1 + Wave 208 P2 + Wave 308 P1
**Linked audit:** `docs/audit/flowmol3/wave208-p2-flowmol3-dgl-fix-or-sanity.md`

## R-017 — Vendored upstream defensive-patch revert (Wave 244-262)

**Severity:** critical (user-authorized destructive edit; AGENTS.md §3 hard
guardrail #1 "vendored upstream is sacred" was reaffirmed in Wave 260)
**Trigger:** Wave 244 P1 manifest SHA-256 audit identified that 6 vendored
upstream files under `data/FlowMol3/`, `data/LineageFlow/`, `data/Kanzi/`
contained defensive-patch edits applied by the framework's adapter shim
during Wave 187-216 dgl 2.4.0 bug workaround; the edits were
DESTRUCTIVE modifications to others' original repos, in violation of the
Wave 260 user directive "all modifications to others' original repos
must be reverted."
**Mitigation:**
1. Per Wave 260 + Wave 262: revert all 6 vendored upstream files to
   upstream commit hashes (FlowMol3 `77cae22`, LineageFlow `ccef84a`,
   Kanzi `cfed9cf`)
2. Move the defensive-patch logic to the framework's adapter layer
   (`adaptive_reflow/adapters/<model>/_shim.py`) — the adapter is the
   framework's owned surface, the vendored repo is sacred
3. Add `tools/check_vendored_unchanged.sh` to CI as a pre-merge gate
   (per Wave 260 P1 + Wave 273 P3)
4. Per Wave 260 directive: vendored md5 must match upstream before
   commit; CI fails if drift detected
**Owner:** Claude (every wave that touches `data/<model>/`)
**Recurrence:** Wave 244 (single occurrence; 6 files affected; fully
reverted at Wave 262; CI gate added at Wave 273)
**Linked LL:** Wave 244 P1 + Wave 260 P1 + Wave 262 P1
**Linked audit:** `docs/audit/upstream-modifications.md` (23.5KB)

## R-018 — Cosine-vs-codim scheduler-attribution disclosure gap (Wave 341)

**Severity:** medium (paper-citation accuracy; resolved at Wave 342 + Wave 343
paper-evidence + Wave 347 governance refresh disclosure)
**Trigger:** Per Wave 341 deep-audit + Wave 292 pipeline-inventory audit,
the headline R-cells 12/13 use `CosineAnnealScheduler` (`adaptive_reflow/
algorithm/scheduler/cosine_anneal.py`), NOT `CodimensionSheetScheduler` —
the paper-quantity-driven scheduler cited as the framework's main
contribution is actually deployed on only 1/13 R-cells (R6's
`TierAwareCodimensionSheetScheduler` wrapper). The cosine-vs-codim gap
was a disclosure-of-attribution problem: paper §3.3 Table 3.2 cited the
scheduler family without specifying which controller was deployed on
which R-cell, leading readers to assume all 13 R-cells used the codim
controller when only 1 actually did.
**Mitigation:**
1. Per Wave 342 paper-evidence: README + README.zh.md + paper §3.3 Table
   3.2 + §7.1 Table 7.1 now carry an explicit Scheduler column
   (`CosineAnnealScheduler` / `TierAwareCodimensionSheetScheduler`)
2. Per Wave 347 governance refresh: this risk is now APPENDED to
   RISK-REGISTER.md as R-018 so future waves don't re-introduce the gap
3. Per user directive "还是先只用余弦退火作为调度器的写法" (Wave 292
   §1 addendum): the canonical default is cosine-only; codim is
   research-stage pending Wave 287 24-bug release engineering + Wave 291
   3-seed replication
4. Any future paper-evidence wave must cite the specific scheduler per
   R-cell, not the scheduler family
**Owner:** Claude (every paper-evidence wave that touches §3.3 / §7.1
tables)
**Recurrence:** Wave 341 + Wave 342 (resolved at Wave 342; documented at
Wave 347 to prevent re-introduction)
**Linked LL:** Wave 292 + Wave 341
**Linked audit:** `docs/audit/wave341-readme-cosine-vs-codim.md` (23.0KB)
+ `docs/audit/wave292-p1-pipeline-inventory.md`

## R-019 — TPAMI → TNNLS venue switch (Wave 238)

**Severity:** medium (process risk; 6-week prep plan was TPAMI-specific)
**Trigger:** Wave 238 P3 journal decision switched venue from TPAMI to
TNNLS based on (a) TPAMI 6-week prep plan deemed too aggressive given
Wave 203-205 stats-audit-fix scope, (b) TNNLS 14-page initial-submission
budget accommodates Wave 298 P1-P8 + Wave 311 Path A Lemma 1 + Wave 322
Path A Lemmas 2-3 framework-properties additions, (c) TNNLS accepts
multi-author honest-negative scope articulation per reviewer pool
post-2024.
**Mitigation:**
1. Per Wave 238 P3: `docs/audit/engineering/wave238-p3-journal-decision.md`
   documents the decision criteria + paper-format deltas (TPAMI
   single-column → TNNLS two-column IEEEtran-journal)
2. Wave 323 P3 typeset rebuild for TNNLS two-column: 14 pages verified
3. Wave 328 freeze manifest re-pointed at HEAD `60a3f75` for TNNLS
4. `tnnls_submission/` package now contains 8 files (MANIFEST + cover_letter
   + data_availability + figures + highlights + README + submission_checklist
   + tables) + supplementary_bundle/ + supplementary_bundle.zip
5. v3.0-tnnls-ready tag re-cut at Wave 328, 338, 343, 346
6. Per Wave 341 deep audit §7.3 (reviewer doc):
   `tnnls_submission/MANIFEST.md` references `paper-A-final.pdf` (not
   `paper-flat-ieeetran.pdf`) post-Wave 345 cross-doc fix
**Owner:** Claude (every paper-evidence wave that touches the submission
package)
**Recurrence:** Wave 238 P3 (single occurrence; full migration
completed at Wave 328; tag stable since Wave 346)
**Linked LL:** Wave 238 + Wave 323 + Wave 328
**Linked audit:** `docs/audit/engineering/wave238-p3-journal-decision.md`
(12.0KB) + `tnnls_submission/MANIFEST.md`

## R-020 — R5b REGRESSES → conditional-WIN reversal (Wave 235)

**Severity:** high (paper-citation accuracy; resolved at Wave 235 P1
+ Wave 342 README source-consistency fix + Wave 343 RMSPreserving
disposition + Wave 347 governance refresh disclosure)
**Trigger:** R5b (CIFAR-10 RF matched-NFE=50) flipped direction from
REGRESSES at all-n_rounds (Wave 195 P2 power-analysis) → conditional
WIN at `n_rounds=1` (`ΔFID` −1.60% to −2.53%) per Wave 235 P1; the
reversal was conditional on the number of restart-blend rounds, which
was not disclosed in the original Wave 195 P2 R-level inventory. The
paper §3.3 Table 3.2 + §7.1 Table 7.1 + §7 line 716 R5b bullet
originally cited "R5b REGRESSES" without disclosing the n_rounds
conditional, leading readers to assume the framework ALWAYS regresses
on R5b when in fact it wins at `n_rounds=1` (the deployment default).
**Mitigation:**
1. Per Wave 235 P1 + Wave 336 R5b mechanism audit: paper §7.1 Table 7.1
   R5b row + §7 line 716 R5b bullet + §3.3 Table 3.2 R5b row now
   disclose "R5b conditional WIN at n_rounds=1, REGRESSES at n_rounds≥2"
2. Per Wave 341 deep audit §3.5 + Wave 342 README source-consistency fix:
   the README N=200 headline "4/4 schedulers WIN" was inconsistent with
   the Wave 247 P3 N=1000 finding "2/4 schedulers WIN"; Wave 342 fixed
   the README to cite rounds1 actuals (the N=200 reading) not v2
   NFE-averaged (the N=1000 reading). The README fix is per Wave 268
   strict-clean rule (REPLACE not REVERT)
3. Per Wave 341 §3.5 verifier note: R5b is the cell with the LARGEST
   data-integrity surface — 4 verifications (rounds1 / rounds2 /
   rounds10 / v2-NFE-averaged) and only 2 are headline-visible
4. Future R5b citations must specify `n_rounds` value
**Owner:** Claude (every stats_method + paper_claims wave that cites R5b)
**Recurrence:** Wave 195 P2 → Wave 235 P1 (single reversal; resolved at
Wave 235 + Wave 342; documented at Wave 347 to prevent mis-citation)
**Linked LL:** Wave 195 P2 + Wave 235 P1 + Wave 247 P3 + Wave 336 + Wave 341
**Linked audit:** `docs/audit/stats_method/wave235-p1-r5b-fix.md` (11.5KB)
+ `docs/audit/wave341-deep-audit.md` §3.5

## R-021 — R5c smoke-ckpt → production-ckpt direction-flip (Wave 280)

**Severity:** high (paper-citation accuracy; resolved at Wave 280 P R5c
sweep + Wave 342 disclosure + Wave 347 governance refresh disclosure)
**Trigger:** R5c (MNIST FM matched-NFE=50) flipped direction between
two checkpoint sources: smoke ckpt (Wave 191 P3, epochs=1,
base_channels=8, max_train_images=6000, sha256 `ded1fa70c83b...`)
reported framework WINS −28.43% (Bonferroni p=3.95e-11, Cohen's
d_z=−13.18); production ckpt (Wave 280 P, materialized at
`data/mnist_fm/production.ckpt.npz`, 75 KB, 3 epochs,
base_channels=16, full 60K images, sha256 `27e2bb6c44758822749de...`)
reported baseline WINS +10.37% per seed d_z per seed [+1.55, +1.33,
+1.02] (Bonferroni p_bonf=0.0133). The two checkpoints differ in (a)
epochs (1 vs 3), (b) base_channels (8 vs 16), (c) training-data size
(6000 vs 60000), (d) ckpt size (22481 vs 75000 bytes). The original
paper §3.3 Table 3.2 R5c row cited "R5c framework WINS" without
disclosing the ckpt source, leading readers to assume the framework
WINS on the production ckpt when in fact it LOSES.
**Mitigation:**
1. Per Wave 280 P R5c sweep: paper §7.1 Table 7.1 R5c row + §3.3
   Table 3.2 R5c row + §7 line 716 R5c bullet now disclose BOTH
   ckpt sources explicitly: "smoke ckpt framework WINS −28.43%,
   production ckpt baseline WINS +10.37% per seed d_z [+1.55,
   +1.33, +1.02]"
2. Per Wave 341 deep audit §3.6 verifier note: "R5c is the
   most-disclosed cell — both smoke-ckpt and production-ckpt paths are
   documented in `aggregate.json` with explicit direction-flip; this is
   the project's most honest cell"
3. Per Wave 268 strict-clean rule + Wave 280 P directive: the smoke-ckpt
   reading is preserved as historical evidence (the Wave 191 ckpt is
   byte-stable); the production-ckpt reading is the load-bearing
   current evidence
4. Future R5c citations must specify `ckpt_source` value
**Owner:** Claude (every stats_method + paper_claims wave that cites R5c)
**Recurrence:** Wave 191 P3 → Wave 280 P (single direction-flip;
resolved at Wave 280; documented at Wave 347 to prevent mis-citation)
**Linked LL:** Wave 191 + Wave 250 + Wave 280
**Linked audit:** `docs/audit/wave280-p-r5c-sweep-result.md` + Wave 341
§3.6 + Wave 280 P K1 sweep-result

## R-022 — Wave 341 deep-audit finding cluster (R5a d_s + R5b source-mix
+ BGV12/Villani + RMSPreserving)

**Severity:** high (4 unresolved discrepancies at Wave 341 deep audit;
3 closed at Wave 342 + Wave 343, 1 partially closed with deferred
disposition)
**Trigger:** Wave 341 deep audit identified 4 paper ↔ project alignment
discrepancies + 1 CRITICAL citation error + 4 data holes + 3 governance
files stale by 137+ commits:
1. **CRITICAL — BGV12/Villani bibliography gap** (Wave 341 §6.1):
   `docs/drafts/paper-A-final.md` lines 306/312/433/866/1336+ cite
   "Bolley-Guilin-Villani (2012) concentration inequality (BGV12,
   Theorem 1.1)" but bibliography [10] was a totally different paper
   (Karl/Kemeter/Dax/Sierak. ICML 2024 / arXiv 2406.03980). Villani
   (2003) was also missing. **CLOSED at Wave 343** (BGV12 [N] + Villani
   2003 [M] bibliography entries added to `paper-A-final.tex` lines
   354-360, 588-590; inline [N]/[M] citation markers at the two §6.5
   reference sites + §6.6 cross-reference).
2. **HIGH — R5b README data-source inconsistency** (Wave 341 §6.2):
   README cited R5b v2 NFE-averaged (baseline=218.87 / framework=122.18)
   in the table header but R5b rounds1 actuals (baseline=454.39 /
   framework rounds1-conditional WIN) in the row. **CLOSED at Wave 342**
   (README source-consistent fix to rounds1 actuals).
3. **HIGH — R5b "3/4 schedulers" wording** (Wave 341 §6.3): README
   cited "3/4 schedulers WIN" but Wave 247 P3 found "2/4 schedulers WIN
   at N=1000". **CLOSED at Wave 342** (README fixed).
4. **MEDIUM — RMSPreservingCoordinateMixer referenced in paper but not
   in code** (Wave 341 §6.5): paper §6.2 Sub-claim 1.4 enumerated 4
   algorithm-layer blenders including `RMSPreservingCoordinateMixer`,
   but the class is a deprecated back-compat alias for
   `EqualRmsCoordinateMixer` (canonical name per ADR-0009). **PARTIALLY
   CLOSED at Wave 343** (removed from §6.2 Sub-claim 1.4 enumeration;
   3 algorithm-layer blenders only; additive disposition note added).
   The class itself is NOT reintroduced (it's a deprecated alias;
   per Wave 268 strict-clean rule, deprecation is preserved).
5. **HIGH — R5a d_s TIE_PERSISTS** (Wave 341 §3.4): 2D Two Moons paper
   R-level d_s=+0.460 at n=3 verified at Wave 209 P6 n=7 + Wave 216 P2
   n=10 but `|Δ|=0.00232` < `min_effect_size=0.01` floor → TIE
   persists. **NOT CLOSED** — deferred; n=30/n=100 confirmation not
   attempted; honest disclosure preserved.
**Mitigation:**
1. Wave 341 deep audit doc is the load-bearing audit trail for all 4
   discrepancies + 4 data holes + 3 stale governance files
2. Wave 343 closed BGV12/Villani + RMSPreserving; Wave 342 closed R5b
   README inconsistency + "3/4 schedulers" wording
3. R5a TIE_PERSISTS remains honestly disclosed in §10.6 R-level inventory
   per Wave 268 strict-clean rule (status history additive, no removal)
4. Wave 347 governance refresh closed the 3 stale governance files
   (STATUS.md + RISK-REGISTER.md + INDEX.md)
5. Any future paper-evidence wave must verify all citations resolve to
   real bibliography entries (not placeholder [10] entries)
**Owner:** Claude (every paper-evidence wave that touches paper §6 or
governance files)
**Recurrence:** Wave 341 deep audit (single finding cluster; 3 of 5
items closed at Wave 342 + Wave 343, 1 partially closed, 1 deferred
with honest disclosure; full resolution documented at Wave 347)
**Linked LL:** Wave 341 deep audit
**Linked audit:** `docs/audit/wave341-deep-audit.md` (52.5KB) +
`docs/audit/wave342-claims-fixes.md` + `docs/audit/wave342-readme-update.md`
+ `docs/audit/wave343-paper-fixes.md`