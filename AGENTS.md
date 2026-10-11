# AGENTS.md — Routing rules for any agent (Claude Code, Codex, ultracode sub-agents, future LLMs)

> **Read this first when entering this repo.** It routes every common
> task to the right project skill + the right commands so you do not
> reinvent them. Project skills are in `.codex/skills/` (Codex-format)
> AND mirrored below as portable checklists.
>
> **Management & map surfaces:** [`todo/WAVES.md`](todo/WAVES.md) is the
> consolidated project record (current state, phase history, evidence, gates,
> decisions, risks); [`docs/README.md`](docs/README.md) is the documentation
> map. Prefer these over per-increment records for management state.

---

## 1. Skill routing (the most important section)

Match the user's request to **one** of the three project skills. Do not
re-implement their checks — invoke the skill and follow it.

| Trigger phrases (user says any of these) | Project skill to invoke |
|---|---|
| "写论文", "改 paper", "改 abstract", "改 cover letter", "改 supplementary", "改 highlights", "改 data availability", "改 CLAIMS", "翻译 README", "中英 README", "doc updates", "paper polish", "narrative", "highlight result" | **`flowa-paper-evidence`** |
| "跑实验", "重跑 sweep", "reproduce R{1..6}", "sweep seed N", "control / framework / baseline 4-arm", "k6 foldability", "CIFAR FID re-run", "per-record csv", "statistical test (TOST/JT/BF01/meta/NI)" | **`flowa-experiment-sweep`** |
| "audit", "claim check", "drift", "regression", "gap investigation", "verification", "re-verify", "consistency check", "investigate", "为什么指标变了", "R-level 翻盘" | **`flowa-research-audit`** |

**Hybrid requests (most real asks):** when the user request touches multiple
> cells of the table, the agent must invoke **each skill in turn** and chain
> the audit-dossier to the next skill (do not parallelise — the evidence
> chain from `paper-evidence` is downstream of `experiment-sweep` and
> `research-audit`).

---

## 2. Project skills (portable mirror of `.codex/skills/`)

These are the three skills bundled with the project. Each one is a
short contract — read it once and obey it.

### 2.1 `flowa-paper-evidence` — write/update paper surfaces

Translate **verified** results into publication evidence.

- Read `docs/CLAIMS.md`, `docs/CONSOLIDATED_RESULTS.md`, `docs/INSIGHTS.md`,
  and the relevant `docs/audit/` records **before** editing prose.
- Every quantitative statement must point to a result artifact or audit
  with: model, metric, N, seed policy, environment (`.venvs/<model>_venv`),
  and comparison direction.
- Distinguish status labels — never promote provisional by wording:
  - `SUPPORTED`         — significant + powered
  - `NOT_SIGNIFICANT`   — non-sig but powered
  - `UNDERPOWERED`      — too few records to call
  - `REGRESSES`         — framework hurts the metric
  - `DEFERRED`          — env-blocked or compute-deferred
- When you change `tnnls_submission/*`, update the SHA-256 column in
  `tnnls_submission/MANIFEST.md` AND `tnnls_submission/cover_letter.md`
  (re-run `cd tnnls_submission && sha256sum -- *.md`).
- When you change `docs/CLAIMS.md`, run `python tools/check_claims_consistency.py`
  to verify no drift.
- Preserve caveats: metric-definition gaps, CPU/GPU differences, user-gated
  sweeps still pending.

**Owns (allowed to edit):**
- `docs/drafts/*.md` (paper draft)
- `docs/CLAIMS.md`
- `tnnls_submission/{MANIFEST,cover_letter,highlights,tables,figures,data_availability,submission_checklist}.md`
- `README.md`, `README.zh.md`, `cover-letter-tnnls.md`
- `docs/CONSOLIDATED_RESULTS.md`, `docs/INSIGHTS.md`
- `docs/audit/` records whose topic is paper

**Hard requirements before commit:**
- `python tools/check_claims_consistency.py` exits 0
- `mkdocs build --strict` exits 0 (if `mkdocs.yml` or `docs/` were touched)
- `ruff check` 0 findings in any *.py touched

### 2.2 `flowa-experiment-sweep` — bounded, restartable experiments

Run experiments as small, restartable, gate-checked increments.

- Read target config + adapter contract first; select the sidecar venv
  per `docs/environments.md` — **never mix model environments** (FlowMol3
  uses `flowmol3_venv`; LineageFlow uses `lineageflow_venv`; Kanzi uses
  `kanzi_venv`; 2D / CIFAR / MNIST FM all use `flowmol3_venv`).
- **Before** launching, capture and persist to `verification_outputs/<increment>/METADATA.json`:
  GPU ID + free memory, command line, config path, seed, sample count,
  output directory, max-records cap, wall-clock budget.
- Use bounded runs (`--max-records N` / `--num-records N`) and explicit
  `--seed`; never delete or overwrite a prior `verification_outputs/<old>/*`.
- Emit **two** outputs: (a) machine-readable JSON/CSV; (b) a short audit
  note `docs/audit/<increment>-<topic>.md` with device + skipped + stats
  caveats.
- After any code change: re-run focused `pytest tests/<relevant>.py` and
  applicable D.4 regression vectors.

**Owns:**
- `tools/sweep_*.py` (sweep drivers; may be added)
- `verification_outputs/<increment>/*` (new evidence)
- `docs/audit/<increment>-*.md` (audit note)
- `adaptive_reflow/adapters/<one>/` (only the one being tested)
- `reproduce/*.sh` (per-cell scripts)

**Hard requirements before commit:**
- `n_records_processed == planned` AND `n_records_skipped == 0`
- D.4 vectors `tests/test_d4_regression_vectors.py` still 30/30 PASS
  (or `--max-records` evidence is honored)
- Wall-clock and skipped-records are in the audit note

### 2.3 `flowa-research-audit` — reproducible evidence chain

Audit claims with a reproducible evidence chain.

- Start from the relevant claim, adapter, increment, or metric; inspect
  `docs/CLAIMS.md`, `todo/WAVES.md`, owning code/config **before**
  drawing conclusions.
- Record exact: file paths, commit, environment/venv, sample size,
  command used. Separate **observed facts** vs **interpretation** vs
  **unresolved gaps** in the audit note.
- **Prefer existing audit + verification tools**; do **not** re-run a
  long GPU sweep merely to restate a recorded result.
- After code changes: re-run D.4 vectors and the applicable capability
  gates. Preserve fail-closed behavior + user-gated push policy.
- Write findings to `docs/audit/<topic>.md` (or requested surface), then
  summarise impact + smallest next action.

**Owns:**
- `docs/audit/<topic>.md` (new audit)
- `todo/WAVES.md` (consolidated record), `todo/RISK-REGISTER.md`
  (state updates)
- May edit `docs/CLAIMS.md` only to flag (CLM-NNN status
  `SUPPORTED/UNDERPOWERED/REGRESSES/DEFERRED/NOT_SIGNIFICANT`) — never
  the wording, never the numbers.

**Hard requirements before commit:**
- `python tools/check_claims_consistency.py` exits 0 (only changes
  wording, never numbers)
- `pytest tests/test_d4_regression_vectors.py -q` 30/30 PASS

---

## 3. Hard guardrails (apply to ALL skills)

These come from real feedback in the conversation log. **Never violate.**

1. **Vendored upstream is sacred.** Files under `data/FlowMol3/`,
   `data/LineageFlow/`, `data/Kanzi/`, `data/HiDream-I1/`,
   `data/GraphBFN/`, `data/Lumina-Image-2.0/`, `data/ProtBFN-AbBFN/`,
   `data/Wan2.2/`, `data/FreqFlow/` (9 vendored repos) must stay
   byte-identical to upstream commit hashes (FlowMol3 `77cae22`,
   LineageFlow `ccef84a`, Kanzi `cfed9cf`, …). Per a standing user
   directive — *all modifications to others' original repos must be
   reverted.* Pinned commit list in
   `tnnls_submission/data_availability.md` "Unmodified vendored
   upstream code" table. Verify md5 matches upstream before commit.
2. **No destructive edits.** Additive is the rule. If a fix is
   destructive, do it as: (a) ADDITIVE paragraph first; (b) the
   destructive edit; (c) update the audit trail.
3. **NO-PUSH policy.** No `git push` without explicit user gating.
   Every agent commits; no agent pushes. Reaffirmed in `todo/PUSH-READY.md`.
4. **Honest uncertainty.** Never promote `UNDERPOWERED` / `DEFERRED` /
   `REGRESSES` / `NOT_SIGNIFICANT` to `SUPPORTED` by wording alone.
   Reframe wording, do not change numbers.
5. **TNNLS submission freeze is sacred.** Once `v3.0-tnnls-ready` tag
   is cut, only additive docs in `tnnls_submission/` are allowed.
   Numbers must not move; SHA-256s must be regenerated.
6. **Per-increment audit doc.** Every increment produces a `docs/audit/<increment>-*.md`
   note (existing records keep their historical names). Format mirrors the
   12-decimal-CLAIMS-table pattern.
7. **Stricter = cleaner.** Standing directive — "严格一点，按照最干净的方法来".
   When two valid options, pick the cleaner one (fewer files touched,
   fewer lines changed, more additive).

---

## 4. Standard command playbook (the fast path)

These are the canonical commands. Use them; do not improvise.

### 4.1 Pre-merge submission gates (CI mirror)

```bash
# D.4 byte-stable regression (must be 30/30 PASS)
python3 -m pytest tests/test_d4_regression_vectors.py -q

# ruff lint (must be 0 findings in scope dirs)
ruff check adaptive_reflow/ tests/ scripts/ tools/

# mkdocs build (must exit 0)
mkdocs build --strict

# claims consistency (must exit 0, no drift)
python3 tools/check_claims_consistency.py

# pytest full (subset green; full-suite is env/ordering-dependent)
python3 -m pytest tests/ -q

# mypy type-check (target: 0 errors; current state documented in CLM-024)
mypy adaptive_reflow/

# TNNLS submission package SHA-256 (must match MANIFEST)
cd tnnls_submission && sha256sum -- *.md
```

### 4.2 Paper-write workflow (template reference)

```bash
# 1. Look up the claim status
grep -nE "^### CLM-[0-9]+" docs/CLAIMS.md | head -50

# 2. Look up the headline evidence
ls verification_outputs/ | head -50

# 3. Look up the audit record for the change context
ls docs/audit/ | tail -20

# 4. After any docs edit, verify
python3 tools/check_claims_consistency.py
mkdocs build --strict
```

### 4.3 Experiment-sweep workflow (template reference)

```bash
# 1. Activate the right sidecar venv (NEVER MIX)
source .venvs/kanzi_venv/bin/activate      # for Kanzi
source .venvs/lineageflow_venv/bin/activate  # for LineageFlow
source .venvs/flowmol3_venv/bin/activate   # for FlowMol3 / 2D / CIFAR / MNIST FM

# 2. Capture pre-sweep METADATA
nvidia-smi > /tmp/sweep/METADATA.gpu
date -u +%FT%TZ > /tmp/sweep/METADATA.start

# 3. Run bounded sweep with explicit cap
python3 tools/sweep_*.py --max-records 1000 --seed 42 \
    --output-dir /tmp/sweep/seed42 2>&1 | tee /tmp/sweep/seed42.log

# 4. Move evidence into verification_outputs/
mkdir -p verification_outputs/<increment>-<topic>
mv /tmp/sweep/seed42/* verification_outputs/<increment>-<topic>/

# 5. Write audit note
$EDITOR docs/audit/<increment>-<topic>.md   # follow the audit-note format

# 6. Re-verify D.4 + relevant capability
python3 -m pytest tests/test_d4_regression_vectors.py -q
```

### 4.4 Research-audit workflow (template reference)

```bash
# 1. Find the claim / increment / topic under question
grep -RnE "CLM-[0-9]+|R[0-9]+" docs/CLAIMS.md docs/CONSOLIDATED_RESULTS.md | head -30

# 2. Re-read what was claimed (paper §X) vs what code does
$EDITOR docs/paper-draft.md       # the claim
grep -RnE "def .*?" adaptive_reflow/  # the code

# 3. Reproduce from existing artifact (NEVER re-run long sweep)
python3 -c "import json; print(json.load(open('verification_outputs/<increment>/result.json'))['headline'])"

# 4. Write audit note
$EDITOR docs/audit/<topic>.md   # follow the observed/interpretation/gap format
```

---

## 5. Top-level repo map (orientation)

```
AGENTS.md                         # ← THIS FILE (read first)
README.md / README.zh.md          # bilingual user-facing
CLAIMS.md                         # ACTIVE claim ledger (gate-mutation gate)
CHANGELOG.md                      # development history

adaptive_reflow/                  # core framework (do NOT casually edit)
├── universal/                     # model-agnostic kernel
├── algorithm/                    # 5-component scheduler
├── framework/                    # CUDA-graph capture
├── stats/                        # TOST / JT / BF01 / meta / NI
├── adapters/                     # 12 concrete FM adapters
└── contracts/                    # frozen typed dataclasses (paper quantities)

configs/                          # configuration presets
reproduce/                         # one-click per-cell scripts (R1..R6)
scripts/                          # experiment-driver + reproduction scripts
tests/                            # pytest suite + D.4 byte-stable regression
verification_outputs/                # byte-addressable headline evidence (gitignored)
tnnls_submission/                 # TNNLS submission package (7 files)
docs/                             # paper drafts + audit records
├── drafts/                        # paper source
├── audit/                         # audit trail (per-increment records)
├── api/                           # mkdocstrings auto-generated
└── ...
data/                             # 9 vendored upstream repos (DO NOT MODIFY)
eaai_submission/                  # historical EAAI submission (archive)
todo/                             # active root plans + governance
tools/                            # paper-metric + sweep scripts
.codex/skills/                    # Skill flowa-paper-evidence / experiment-sweep / research-audit
.claude/workflows/                # legacy experiment-driver JS workflows (do not delete)
.github/workflows/                # CI: ci.yml / cpu-tests / docs-deploy / docs-validate / ...
```

---

## 6. When you don't know what to do

If a request doesn't match any of the 3 project skills, **stop** and
ask the user. Do not invent a new workflow. The three skills cover all
historical work.

If a request seems destructive or controversial (e.g. touching vendored
code, pushing to remote, cutting a tag), **stop** and confirm with the
user. The hard guardrails in §3 cannot be overridden by an agent.

If you find yourself about to re-run a long GPU sweep just to restate
a recorded result, **stop** — read `verification_outputs/<existing>/`
first. Per `flowa-research-audit`: prefer existing tools.

---

_Last updated: 2026-10-11 (documentation-management consolidation — management surface `todo/WAVES.md`, map `docs/README.md`)._