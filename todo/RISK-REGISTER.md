# `todo/RISK-REGISTER.md` — forward-looking risks + mitigations

**Date:** 2026-09-05
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