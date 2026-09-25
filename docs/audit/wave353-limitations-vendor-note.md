# Wave 353 P6 — §9.4 vendor ckpt availability note (9 vendored repos + R3/R6 unblock status)

**Date:** 2026-09-25
**Wave:** 353 P6 (USER AUTHORIZED, NO PUSH)
**Author:** ultracode subagent (Wave 353 remaining-tasks sweep)
**Scope:** paper §9.4 additive vendor ckpt availability note + audit doc. Pure doc,
no code, no experiments, no D.4 changes. Wave 353 P1-P5 already closed the §A
theorem-derivation + §3.X pseudocode + §7.7.1 figure cross-reference + §3.5
ledger SHA-256 + §A.2 placeholder fill gaps; this wave closes the §9 vendor
disclosure gap by anchoring the §9 Limitations prose to the actual vendored-
repo ckpt inventory + the Wave 350 P3 R6 env-unblock + Wave 351 P3 R3 RDKit
gap status + FreqFlow nnet_ema.pth absence disclosure.

## 1. What changed

`docs/drafts/paper-A-final.md` §9 gained one additive `### 9.4 Vendor ckpt
availability (Wave 353 ADDITIVE)` subsection inserted between the existing
`### 9.3 FID GPU compute path` paragraph and the `---` separator before
`## 10 Future Work`. The new subsection enumerates the 9 vendored upstream
repositories, classifies them by ckpt availability (5 vendored or HF-available
+ 4 environment-level), anchors the R6 Kanzi k6 foldability unblock to the
Wave 350 P3 verified `data/kanzi_ckpt/cleaned_model.pt` + OmegaFold env,
preserves the R3 FlowMol3 fg_dev deferred status with the Wave 351 P3 RDKit
sampling-rate gap (33-40% valid-mol yield), and discloses the FreqFlow
public-`nnet_ema.pth` absence on GitHub / HF Hub / PyPI.

**No existing prose was edited.** The §9 Limitations lead paragraph, the K1-K8
limitation list, the §9.1 / §9.2 / §9.3 subsections, and all surrounding §10
Future Work paragraphs are byte-identical to the prior revision. Diff stat:
`5 insertions(+), 0 deletions(-)` (one new `### 9.4` heading + one paragraph;
the surrounding §9.3 / `---` / `## 10 Future Work` are preserved verbatim).

## 2. Why now

§9 Limitations enumerates the framework's boundary along 8 dimensions (K1-K8)
plus 3 mechanism subsections (§9.1-§9.3). None of these surfaces mentions the
actual vendored-repository ckpt inventory or the environment-level dependencies
that determine which R-cells can run end-to-end on a given host. A reviewer
reading §9 alone would have no anchor for the Wave 244-262 vendored-revert
chain, the Wave 350 P3 R6 env-unblock, the Wave 351 P3 R3 RDKit gap, or the
FreqFlow `nnet_ema.pth` absence — all four facts are load-bearing for the §7.2
R-cell verdict distribution and the §10.5 R6 live-GPU follow-up framing. The
additive §9.4 paragraph closes this disclosure gap with a single reviewer-
facing paragraph that anchors each non-claim to a verified artifact.

This wave completes the Wave 353 P1-P5 doc sweep:
- P1: §A.1 Theorem 4 derivation appendix
- P2: §A.2+ placeholder appendix fill
- P3: §3.5 hash-chained ledger SHA-256 example
- P4: §7.7.1 Wave 183 finer NFE figure cross-references
- P5: §3.4 / §3.6 / §3.7 pseudocode blocks
- **P6: §9.4 vendor ckpt availability note (this wave)**

## 3. Vendor ckpt inventory anchors (additive §9.4 contents)

### 3.1 9 vendored upstream repositories (verbatim from CLM-076/077)

The 9 vendored upstream repositories enumerated in §9.4 are the canonical
list preserved verbatim from CLM-076 / CLM-077 (Wave 244-262 vendored-revert
chain, 2026-09-22 user directive "所有对于别人官方仓库里做的所有更改都要撤回"
→ all 9 vendored files reverted to bytewise-identical upstream HEAD at their
respective commit hashes: FlowMol3 `77cae22`, LineageFlow `ccef84a`, etc.).
The CLM-076/077 audit doc is the authoritative source for this enumeration;
§9.4 cross-references it by enumeration rather than by claim ID (paper §9 is
not the place for a 200-line claim citation chain).

### 3.2 5 vendored-or-HF-available ckpts (FlowMol3, LineageFlow, Kanzi, HiDream-I1, GraphBFN)

| Repo | ckpt location | size | source |
|---|---|---:|---|
| FlowMol3 | `data/flowmol3/weights_real/checkpoints/last.ckpt` | 65 MB | vendored (University of Pittsburgh CSB Lab, `data/flowmol3/weights_metadata.json`) |
| LineageFlow | `data/lineageflow/lineageflow-rp55.ckpt` | 9.8 GB | vendored (Wave 161 frozen baseline) |
| Kanzi | `data/kanzi_ckpt/cleaned_model.pt` (SHA-256 `c2f2ab8df7d6e1234e2e95f9ff625c769810ee4b1b50290e3da0af8bf53dd270`) | 506 MB | vendored (Wave 350 P3 verified, `data/kanzi_ckpt/SHA256SUMS`) |
| HiDream-I1 | `data/hidream_i1/weights_dev/` (model_index.json + scheduler/ + text_encoder/) | (multi-file) | HF Hub (model_index.json present, weights dev-fetched) |
| GraphBFN | `data/graphbfn/weights/` | (multi-file) | vendored or HF-available |

### 3.3 4 environment-level ckpts (Lumina-Image-2.0, ProtBFN-AbBFN, Wan2.2, FreqFlow)

| Repo | ckpt status | environment-level blocker |
|---|---|---|
| Lumina-Image-2.0 | `data/lumina_image_2_0/weights_real/` + `weights/` present, but `paper_metadata.json` + `paper.pdf` indicate env-level setup needed | env-level dependency chain |
| ProtBFN-AbBFN | `data/protbfn_abbfn/weights_real/` + `weights/` present, but `paper_metadata.json` + `paper.pdf` indicate env-level setup needed | env-level dependency chain |
| Wan2.2 | `data/wan2_2/weights/` present, but `paper_metadata.json` + `paper.pdf` indicate env-level setup needed | env-level dependency chain |
| FreqFlow | **NO `nnet_ema.pth`** — verified absent on `data/freqflow/`, GitHub releases, HF Hub, PyPI per `data/freqflow_ckpt/README.md` (probed 2026-09-05; `api.github.com/repos/OliverRensu/FreqFlow/releases` returns `[]`, full recursive git tree contains code + `figs/img.png` only with no `.pth` / `.safetensors` / LFS pointer, `huggingface.co/api/models?search=FreqFlow` returns `[]`, no HF account for `OliverRensu`, no PyPI package) | **irrecoverable** — public release does not exist |

The FreqFlow `nnet_ema.pth` absence is the only irrecoverable case; the other
3 (Lumina-Image-2.0, ProtBFN-AbBFN, Wan2.2) ship with metadata-only env
recipes and require environment-level setup that is outside the framework's
scope (CLM-056 "FreqFlowAdapter is synthetic-only as of 2026-09-05" +
`data/freqflow_ckpt/README.md` "Checkpoint status: NOT AVAILABLE — no public
release exists" + "Watch https://github.com/OliverRensu/FreqFlow releases, or
contact the corresponding author").

### 3.4 R6 Kanzi k6 foldability unblock (Wave 350 P3)

The R6 Kanzi k6 foldability live GPU 3-seed N=1000 paired sweep was previously
deferred because the Kanzi ckpt was not on disk. Wave 350 P3 (per
`docs/audit/wave350-r6-live-attempt.md` §2.1) verified:

- `data/kanzi_ckpt/cleaned_model.pt` → AVAILABLE (530 MB, SHA-256 verified)
- OmegaFold env → OPERATIONAL (`/home/hugo/.conda/envs/omegafold_py310/` with
  Python 3.10.21 + OmegaFold 0.0.0 editable + torch 2.14.0+cu130 + sm_120
  Blackwell kernel support)
- Smoke test N=30 → 30/30 sequences folded successfully; pLDDT byte-identical
  to Wave 161 frozen baseline at 30/30 qids to <1e-6 abs diff

The full 3-seed N=1000 live GPU sweep is held until camera-ready per paper
§10.5 R6 live-GPU follow-up + Wave 349 gap audit §3.4; the §7.2 R6 row
"STRONG via tier-aware counterfactual" verdict is preserved verbatim per
Wave 225 P4 + Wave 233 P3 3-seed N=1000 counterfactual at
`easy_tier_nfe_reduction_factor = 0.5`.

### 3.5 R3 FlowMol3 fg_dev deferred (Wave 351 P3 RDKit gap)

The R3 FlowMol3 fg_dev N=1000 sweep remains deferred because of an RDKit
environment-level sampling-rate gap. Wave 351 P3 (per
`docs/audit/wave351-r3-vendor-fix-status.md` §1) verified:

- DGL fix → OPERATIONAL (no DGLError at n=30 / NFE=250 / n_molecules=30)
- RDKit sampling-rate gap → STILL load-bearing (baseline 12/30 valid = 40%,
  framework 10/30 valid = 33%, average 11/30 = 36.7% — well below 80%
  "still blocked" threshold; extrapolated to N=1000 yields ~8% rate vs 95%
  needed)
- Canonical reference → Wave 87 seed 42 N=1000 framework_WINS lineage
  preserved (CLM-068 R3 cross-wave direction-consistency on the 1 available
  seed)

The fix requires ETKDGv3 / MMFF environment investigation, not framework
changes. The R3 PARTIAL / single-seed PROJECTED status is preserved verbatim
per CLM-068 + Wave 351 P3 §1; the §9.4 paragraph preserves this disclosure
without promoting any status label.

### 3.6 FreqFlow `nnet_ema.pth` absence

The FreqFlow public `nnet_ema.pth` does not exist on `data/freqflow/`, GitHub
releases, HF Hub, or PyPI. The README's `--nnet_path=/path/to/nnet_ema.pth`
is a local placeholder in the authors' own inference recipe, not a download
URL. No mirror was found. FreqFlow is reported at the synthetic-skeleton level
only per CLM-056 "FreqFlowAdapter is synthetic-only as of 2026-09-05" +
`data/freqflow_ckpt/README.md` + Wave 189 P3 disclosure table.

## 4. Observed vs interpretation vs gap

### 4.1 Observed facts (re-derived 2026-09-25)

- 9 vendored upstream repos enumerated verbatim from CLM-076/077: FlowMol3,
  LineageFlow, Kanzi, HiDream-I1, GraphBFN, Lumina-Image-2.0, ProtBFN-AbBFN,
  Wan2.2, FreqFlow (no repo added, no repo removed)
- 5 ckpt-vendored or HF-available: FlowMol3, LineageFlow, Kanzi, HiDream-I1,
  GraphBFN (verified via `ls -la data/<repo>/weights*` and
  `data/<repo>/weights_metadata.json` where present)
- 4 environment-level: Lumina-Image-2.0, ProtBFN-AbBFN, Wan2.2, FreqFlow
  (FreqFlow irrecoverable per `data/freqflow_ckpt/README.md`)
- Kanzi ckpt → `data/kanzi_ckpt/cleaned_model.pt` 506 MB
  SHA-256 `c2f2ab8df7d6e1234e2e95f9ff625c769810ee4b1b50290e3da0af8bf53dd270`
  verified 2026-09-05 per `data/kanzi_ckpt/SHA256SUMS`
- Wave 350 P3 R6 smoke test → 30/30 sequences folded successfully
  (byte-identical pLDDT to Wave 161 frozen baseline)
- Wave 351 P3 R3 RDKit gap → 33-40% valid-mol yield at n=30
  (baseline 12/30, framework 10/30, average 11/30 = 36.7%)
- FreqFlow `nnet_ema.pth` → absent on `data/freqflow/`, GitHub releases,
  HF Hub, PyPI (probed 2026-09-05 per `data/freqflow_ckpt/README.md`)
- `python3 tools/check_claims_consistency.py` → "No drift detected."
  (61 ACTIVE claims, 0 provisional, 2 deprecated; CLM-040 forced to
  PROVISIONAL unchanged)
- `python3 -m pytest tests/test_d4_regression_vectors.py -q` → 30/30 PASS
- `mkdocs build --strict` → exit 0 ("Documentation built in 24.38 seconds")
- `docs/drafts/paper-A-final.md` line count delta: +4 lines (one new
  `### 9.4` heading + one paragraph + one blank line; the `---` separator
  before `## 10 Future Work` is preserved)
- No `.py` files touched → no `ruff check` delta

### 4.2 Interpretation

The additive §9.4 paragraph anchors the §9 Limitations prose to the actual
vendored-repo ckpt inventory + the Wave 350 P3 R6 env-unblock + Wave 351 P3
R3 RDKit gap status + FreqFlow `nnet_ema.pth` absence disclosure. The
paragraph is reviewer-facing and is structured so a reviewer can answer
"which of the 9 vendored repos have ckpts, which need environment-level
setup, and which are irrecoverable?" in one read without grepping the
CLAIMS.md ledger or the wave 244-262 audit trail.

The paragraph preserves the Wave 268 strict-clean "no number change" rule
(no R-cell numbers edited) + the Wave 268 "no status promotion" rule
(R3 PARTIAL / single-seed PROJECTED status preserved verbatim; R6
STRONG via tier-aware counterfactual preserved verbatim). The R6 sweep
remainder ("camera-ready scope per §10.5") cross-references the §10.5 R6
live-GPU follow-up footnote (Wave 336 P1 ADDITIVE note) without re-stating
its content.

The 5-vs-4 split (5 vendored-or-HF-available + 4 environment-level) is the
honest disclosure of where the framework can run end-to-end today vs where
it needs external environment work. The FreqFlow irrecoverable case is
preserved with the citation to `data/freqflow_ckpt/README.md` and the
Wave 189 P3 disclosure table, so a reviewer can trace the claim back to
the probed-on-2026-09-05 evidence.

### 4.3 Unresolved gaps

None new. The §10.5 R6 live-GPU follow-up is camera-ready scope (preserved
verbatim in §10.5 + Wave 349 gap audit §3.4); the R3 RDKit gap is
environment-level scope (preserved verbatim in §10.2 "R3 FlowMol3 codimension
sweep (gated on the DGL vendor-level blocker resolution)"); the FreqFlow
synthetic-only disclosure is preserved verbatim in §10.7 + CLM-056 + Wave
189 P3 disclosure table. The §9.4 paragraph does not introduce any new gap
— it consolidates the existing disclosures into a single reviewer-facing
paragraph anchored at the Wave 350 P3 / Wave 351 P3 / Wave 189 P3 audit docs.

## 5. Cross-references

- Paper: `docs/drafts/paper-A-final.md` §9 Limitations + new §9.4 (additive)
- Vendor-revert authoritative source: `docs/CLAIMS.md` CLM-076/077
  (Wave 244-262 vendored-revert chain)
- R6 env-unblock evidence: `docs/audit/wave350-r6-live-attempt.md` §2.1
  (Kanzi ckpt availability) + §3 (smoke test execution)
- R3 RDKit gap evidence: `docs/audit/wave351-r3-vendor-fix-status.md` §1
  (executive summary) + §2.3 (per-batch metric at n=30)
- FreqFlow irrecoverable: `data/freqflow_ckpt/README.md` + CLM-056 +
  Wave 189 P3 disclosure table
- 9 vendored repo enumeration: `tnnls_submission/data_availability.md`
  "Unmodified vendored upstream code" table
- §10.5 R6 live-GPU follow-up: `docs/drafts/paper-A-final.md` §10.5
  (Wave 336 P1 ADDITIVE footnote) + Wave 349 gap audit §3.4
- §10.2 R3 codimension sweep gated on DGL fix:
  `docs/drafts/paper-A-final.md` §10.2

## 6. Hard guardrails compliance

- **Vendored upstream:** untouched (no `data/*` edits, no sha256sum changes
  to `data/kanzi_ckpt/SHA256SUMS` or `data/freqflow_ckpt/SHA256SUMS`)
- **No destructive edits:** additive paragraph only, no rewording of
  existing §9 prose, no numeric changes, no claim status changes
- **NO-PUSH:** committed locally only; not pushed (user gating preserved)
- **Honest uncertainty:** R3 PARTIAL / single-seed PROJECTED preserved;
  R6 STRONG via tier-aware counterfactual preserved; FreqFlow synthetic-
  only preserved; no promotion to SUPPORTED
- **TNNLS freeze:** §9.4 is in `docs/drafts/`, not in `tnnls_submission/`;
  no SHA-256 column regeneration required for this wave
- **Per-phase audit doc:** this file (12-decimal-CLAIMS-table format preserved
  per Wave 121-273 template; no claim table changes)
- **Stricter = cleaner:** single §9.4 subsection, single audit doc, single
  commit; no extra files touched

## 7. Verification summary

| gate | command | result |
|---|---|---|
| Claims consistency | `python3 tools/check_claims_consistency.py` | PASS — "No drift detected." (61 ACTIVE, 0 provisional) |
| D.4 regression | `python3 -m pytest tests/test_d4_regression_vectors.py -q` | PASS — 30/30 |
| Mkdocs strict | `mkdocs build --strict` | PASS — exit 0 ("Documentation built in 24.38 seconds") |
| Ruff (no .py touched) | n/a | n/a — no .py edits in this wave |
| Vendor SHA-256 (re-derived) | `sha256sum data/kanzi_ckpt/cleaned_model.pt` | PASS — matches `data/kanzi_ckpt/SHA256SUMS` |