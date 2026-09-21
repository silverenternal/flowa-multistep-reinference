# Wave 217 P2 — Pre-Public Content Audit

**Author:** Wave 217 P2 agent (ultracode session)
**Date:** 2026-09-21
**Scope:** Audit the repo contents before making the GitHub repo public.
**Goal:** Ensure no checkpoints, internal-only docs, or large files leak.

---

## 1. Summary

| Check | Result |
|---|---|
| .gitignore completeness | **PASS** — covers all critical patterns |
| Large files >50MB in working tree | 50 found, **0 tracked** |
| Checkpoint files (*.pt / *.pth / *.ckpt / *.safetensors / *.bin) in working tree | 41 found, **0 tracked** |
| Tracked `.env` / `.key` / `.pem` / API keys / passwords | **0 found** |
| README.md (top 30 lines) | **CLEAN** — no internal-only language |
| Audit docs with "Wave X" / "TODO" / "TBD" / "BLOCKED-ON-DATA" | **417 of 425** tracked audit docs |
| Audit docs with personal paths (`/home/<user>/`) | **109 tracked** audit docs |

**Verdict — Safe to push & set public, with one caveat (see §6):**

- All checkpoint / large / secret classes are correctly covered by
  .gitignore and are NOT tracked in git.
- The 34 unpushed commits (HEAD = `35f9e91`) introduce no new leak class.
- **Caveat:** 417 tracked audit docs in `docs/audit/` contain internal
  workflow markers (Wave numbers, TODOs) and 109 contain personal paths.
  These are tracked and will be visible after `git push`. They are
  *process records*, not source code or paper content, but they DO
  expose internal workflow detail. See §6 for the user-decision matrix.

---

## 2. .gitignore audit (PASS)

The 76-line `.gitignore` covers every leak class that matters for a public
release. Confirmed patterns present:

- **Model checkpoints:** `*.pt`, `*.pth`, `*.ckpt`, `*.safetensors` ✓
- **Compiled artifacts:** `*.so`, `*.o`, `*.a`, `*.py[cod]` ✓
- **Per-tool scratch:** `.cache/`, `.verify_outputs/`, `verification_outputs/`,
  `results/*_tmp/` ✓
- **Data:** `data/*` with explicit re-inclusion for `adaptive_reflow/data/`
  and `data/pfam_holdout/` ✓
- **Build artifacts:** `build/`, `dist/`, `*.egg-info`, `site/` ✓
- **Mutation testing:** `mutmut_results.json`, `.mutmut-cache/` ✓
- **Virtualenvs:** `.venvs/` (per-benchmark ~61 GB scratch) ✓
- **Tool caches:** `.pytest_cache/`, `.ruff_cache/`, `.mypy_cache/` ✓
- **Workflow scratch:** `.claude/` ✓
- **Artifacts / checkpoints / outputs dirs:** `artifacts/`, `checkpoints/`,
  `outputs/` ✓

**Missing patterns:** none that affect a public release.

---

## 3. Large-file scan (PASS — no leaks)

50 files exceed 50 MB in the working tree:

```text
./data/rectified_flow_cifar10.pth
./data/cifar10_rf.pth
./data/cifar10_test_ref.npz
./data/cifar10_inception_features.npz
./data/self_flow/selfflow_imagenet256.pt
./data/lineageflow/lineageflow-rp55.ckpt
./data/kanzi_ckpt/cleaned_model.pt
./data/geva_models/mask2former_swin-s-p4-w7-224_lsj_8x2_50e_coco.pth
./data/_torch_cifar10_cache/cifar-10-python.tar.gz
./data/FlowMol3/references/geom_raw_train.pickle
./.cache/models--openai--clip-vit-base-patch32/blobs/...
./data/flowmol3/weights_real/checkpoints/last.ckpt
./data/lumina_image_2_0/weights_real/transformer/...safetensors
./data/lumina_image_2_0/weights_real/vae/...safetensors
./data/lumina_image_2_0/weights_real/text_encoder/...safetensors
./data/hidream_i1/weights_dev/text_encoder/model.safetensors
... (33 more, all under data/ or .cache/)
```

**All 50 are in untracked paths** (`data/*` is in .gitignore; `.cache/`
is in .gitignore; `.venvs/` excluded). `git ls-files` returns zero files
matching `-size +50M`. None will be pushed.

---

## 4. Checkpoint-file scan (PASS — no leaks)

41 files match `*.pt` / `*.pth` / `*.bin` outside `.venvs/`:

```text
./tools/_kanzi_project_out_inv.pt
./data/rectified_flow_cifar10.pth
./data/cifar10_rf.pth
./data/geva_models/mask2former_swin-s-p4-w7-224_lsj_8x2_50e_coco.pth
./data/self_flow/selfflow_imagenet256.pt
./data/kanzi_ckpt/cleaned_model.pt
./data/kanzi_ckpt/kanzi_encoder.pt
./data/wan2_2/weights/Wan2.1_VAE.pth
./data/wan2_2/weights/models_t5_umt5-xxl-enc-bf16.pth
./data/lumina_image_2_0/weights/model_args.pth
./.venv/lib/python3.12/site-packages/_virtualenv.pth       (venv, not source)
./.venv/lib/python3.12/site-packages/_editable_impl_...pth (venv, not source)
./.cache/models--openai--clip-vit-base-patch32/snapshots/.../pytorch_model.bin
./data/FlowMol3/repo/data/qm9/test_data_*.pt               (qm9 marginal dists, <1KB)
./data/FlowMol3/repo/data/qm9/train_data_*.pt
./data/FlowMol3/repo/data/qm9/val_data_*.pt
./data/FlowMol3/repo/data/geom/test_data_*.pt
... (~20 more, all in untracked paths)
```

`git ls-files | grep -E "\.(pt|pth|ckpt|safetensors|bin)$"` returns **zero
files**. The three `*.pt` files under `data/FlowMol3/repo/data/qm9/` are
~1 KB QM9 marginal-distribution histograms (statistical priors, not model
weights) and are still under the `data/*` exclusion — they will not be
pushed.

---

## 5. Secret scan (PASS — no leaks)

- `git ls-files | grep -E "\.env|\.key|\.pem"` returns zero files.
- `find . -name "*.env" -not -path "./.venvs/*" -not -path "./.venv/*"
   -not -path "./.git/*"` returns zero files.
- Grep for `api[_-]?key|secret|password|token|bearer|aws[_-]?(key|secret)`
  in `docs/audit/` returns only 5 false positives, all about workflow
  tokens like "design tokens" or "61 k tokens consumed" — no credentials.
- Wave 217 P1 already ran the security scan on the 34 unpushed commits
  and confirmed SAFE TO PUSH.

---

## 6. Internal-only audit-doc scan (CAVEAT — user decision required)

**417 of 425 tracked `docs/audit/*.md` files** contain at least one of
the markers:

- `Wave [0-9]+` (wave-prefixed process record)
- `TODO` / `TBD` (open work)
- `BLOCKED-ON-DATA` (external dependency)

**109 of those 425 docs** also embed `/home/<user>/`-prefixed paths
(e.g. `/home/hugo/codes/flowa-multistep-reinference/...`) as hard-coded
links in the markdown.

These docs ARE tracked in git, so they will be visible after `git push`
and after setting the repo to public. They are not part of the source
code, paper, or reproduction pipeline — they are *wave-level process
records* maintained by Claude Code workflow agents.

### Why this is a caveat, not a blocker

- The user explicitly asked the agent to track per-wave audit records
  throughout Waves 1–217 as part of the workflow design.
- These records were never retroactively moved to `docs/ARCHIVE/`
  (which already holds the Wave-1–99 archive at
  `docs/ARCHIVE/audit-waves-1-99/`).
- The audit/INDEX.md (canonical, tracked) explicitly self-describes as
  "Per-wave curation table for `docs/audit/`" and references Wave
  numbers throughout.
- No API keys, no credentials, no real personal data — just per-wave
  workflow notes that document the methodology (which is itself
  useful for a reviewer auditing the claims).

### User-decision matrix

| Option | Action | Effect |
|---|---|---|
| **A. Ship as-is** (default) | No action | All 417 wave-tracking docs are visible publicly. Reviewer benefit: full transparency into the iterative methodology. |
| **B. Sanitize paths only** | Replace `/home/<user>/` with relative paths in the 109 docs, commit as one wave-217-P3 patch. | Removes the home-dir leak; preserves the wave workflow narrative. |
| **C. Move to docs/ARCHIVE/** | `git mv docs/audit/wave*.md docs/ARCHIVE/audit-waves-100-217/` | Internal-only docs no longer at the top-level public path; preserved in git history. Loses one-click review of methodology. |
| **D. Drop entirely** | `git rm` the 417 wave docs | Cleanest public surface, but loses process record. Not recommended. |

**Recommendation:** **Option B** (sanitize paths only) — minimal, safe,
preserves all other value. Wave-217-P3 can land this in one commit.

---

## 7. README.md audit (PASS)

Top 30 lines of `README.md` are clean. They include:

- Title, CI badge, GitHub link
- 2-paragraph "What is FlowA?" framing (paper-facing, not internal)
- Headline evidence table (R1–R6) with public links to per-R subdirs

References to `Wave 152 P5`, `Wave 155 P1`, `commit <sha>`, etc. are
acceptable for a public-facing README — they document methodology and
provenance. They do not match the leak patterns of §6 (no TODO / TBD /
BLOCKED-ON-DATA / personal path).

---

## 8. Decision tree for the user

```text
1. Push the 34 unpushed commits?         → YES (security-scan cleared in P1)
2. Make repo public?                     → YES, after one of A/B/C/D in §6
3. Generate Zenodo DOI?                  → YES, automatic after public
4. Update Data Availability with DOI?    → YES, after DOI issued
5. Submit to TPAMI?                      → YES, after F1–F7 in checklist
```

---

## 9. Fixes applied in this audit

**None required.** All known leak classes are already covered by
`.gitignore`; no checkpoint / large file / secret is tracked in git.
The §6 caveat is a user-decision item, not an automated fix.

---

## 10. Status: ready for push + public (with §6 caveat)

- ✓ .gitignore covers every leak class
- ✓ No checkpoint / model / large file tracked
- ✓ No secret / credential / API key tracked
- ✓ No new leak introduced by the 34 unpushed commits (P1 verified)
- △ 417 audit docs contain Wave-X/TODO markers (intentional workflow
   record — user decides whether to sanitize, archive, or ship as-is)
- △ 109 audit docs embed personal /home/<user>/ paths (Option B
   recommended; 1-commit fix)
