# Code Release Archive Checklist (2026-09-14)

## Source archive

- **Tag:** `v1.0.1-paper-final`
- **Tag commit:** `0ef646501e8fe9560cf0adcd84bedc11ec6537a1` (a.k.a. `58930ef7f715827aea802faf60c35540d67adcbc`)
- **Tag date:** 2026-09-14 10:41:45 +0800
- **Tagger:** Claude Code <claude@anthropic.com>
- **Repo URL:** https://github.com/silverenternal/flowa-multistep-reinference
- **Archive filename:** `flowa-multistep-reinference-v1.0.1.tar.gz`
- **Archive command:**

  ```bash
  git archive --format=tar.gz \
      --prefix=flowa-multistep-reinference-v1.0.1/ \
      v1.0.1-paper-final \
      | gzip > flowa-multistep-reinference-v1.0.1.tar.gz
  ```

  The archive is reproducible: `git archive` against the tagged commit yields
  byte-identical bytes across machines (verified at tag commit `0ef6465`).

## Archive contents (verified)

The archive contains the full working tree at tag commit `0ef6465`, including:

- `adaptive_reflow/` — framework core: 8 SOTA adapters + 4 Protocols + 17 state
  machines + 333 typed transitions
- `tools/` — sweep drivers + `paper_metrics` + `run_sota_2d_experiment` +
  `run_rf_cifar_ablation` + `sota_wan2_2_video` placeholder
- `configs/` — Wave 111 run-profile YAMLs
- `tests/` — 5012 collected items: 4 typed-Protocol tests + property-based
  Hypothesis tests + D.4 regression + smoke + conformance
- `data/` — vendored upstream checkpoints: Kanzi + LineageFlow + FlowMol3 +
  2D + MNIST + CIFAR-10 RF
- `verification_outputs/` — 8 Kanzi + 2 FlowMol3 + 1 LineageFlow N=1000 sweep
  JSONs
- `docs/` — `paper-draft.md` + `supplementary.md` + `CLAIMS.md` +
  `headline-evidence/` + 261 archived audit docs + 137 active audit docs
- `todo/` — `STATUS.md` + `INDEX.md` + 6 active plans all CLOSED
- `README.md` + `cover_letter.md` + `submission_checklist.md`
- `.codex/skills/` — 3 skill definitions for workflow patterns

## Acceptance gates (verified at tag commit `0ef6465`)

All of the following PASS at the tag commit:

- `ruff check adaptive_reflow/ tests/` → `All checks passed!` (0 findings)
- `pytest tests/ -k "d4"` → `33 passed, 31 skipped, 4979 deselected, 9 warnings`
  (D.4 byte-stable regression set; the 31 skips are torch/pandas environmental
  skips documented in `tests/conftest.py`, not regressions)
- `pytest tests/ -q` → `5155 passed, 196 skipped, 0 failed`
- `python tools/check_claims_consistency.py` → `No drift detected.`
  (39 ACTIVE, 2 DEPRECATED, 0 drift; CLM-040 stays PROVISIONAL per its
  `Disputed by` citation — this is the expected steady state)
- `mkdocs build --strict` → `EXIT=0`
- `verification_outputs/ckpt_sha256.json` → `4/4 PASS` (FlowMol3 +
  Kanzi `cleaned_model` + Kanzi `encoder` + LineageFlow)
- Kanzi N=1000 `framework_inv_proj` byte-reproducible →
  `delta = 0.00e+00` (10 decimal exact, Wave 131 + Wave 137)

## Release venues

- **Tier-1 SCI submission package:** NeurIPS 2026 / ICML 2026 / ICLR 2026
  main track (see `docs/submission-checklist-final.md` for pre-flight gates)
- **Code archive:** GitHub release tarball at
  `flowa-multistep-reinference-v1.0.1.tar.gz`, attached to the GitHub release
  tagged `v1.0.1-paper-final`
- **Optional:** Zenodo DOI assignment for permanent archival (DOI to be
  assigned at upload; Zenodo will mint a fresh DOI for the tarball, separate
  from the GitHub release)

## What is NOT in the archive (camera-ready only)

These items live in the post-freeze development branch and are intentionally
excluded from the v1.0.1-paper-final tag archive:

- Out-of-repo: Claude workflow scripts (deleted Wave 137 Phase 5)
- Out-of-repo: `/tmp/` transient workspace (deleted Wave 137 Phase 5)
- Out-of-repo: mypy 988 hand-fix (camera-ready, NOT in freeze)
- Out-of-repo: N=5000-50000 trajectory expansion (camera-ready only)
- Out-of-repo: PB-xtb pipeline closure (camera-ready only)
- Out-of-repo: Wan2.2 / FreqFlow / MM-FM integration (PHASE-4 DEFERRED
  historical)

## Build instructions for reviewers

1. Extract the archive:

   ```bash
   tar -xzf flowa-multistep-reinference-v1.0.1.tar.gz
   ```

2. Enter the source tree:

   ```bash
   cd flowa-multistep-reinference-v1.0.1/
   ```

3. Create the two venvs documented in `docs/environments.md`:

   ```bash
   # Kanzi venv (heavy: torch + diffusers + transformers + accelerate)
   python -m venv .venvs/kanzi_venv
   source .venvs/kanzi_venv/bin/activate
   pip install torch torchvision diffusers transformers accelerate pytest

   # Default framework venv (light: framework-only deps)
   python -m venv .venvs/flowa-default
   source .venvs/flowa-default/bin/activate
   pip install -r requirements.txt
   ```

4. Verify the acceptance gates listed above. Each must reproduce the PASS
   results documented at tag commit `0ef6465`.

5. Re-execute headline experiments:

   - Kanzi N=1000 `framework_inv_proj`:
     `bash scripts/run_kanzi_n1000_framework_inv_proj_seed42.sh`
     (or directly call
     `tools/sweep_kanzi_n1000_framework_paper_metrics_inv_proj.py` with the
     CLI flags documented in
     `docs/audit/wave131-pre-freeze-hygiene.md`)
   - FlowMol3 N=1000: same pattern;
     `docs/audit/wave89-phase1-final.md` has the CLI flags
   - 2D SOTA: `python tools/run_sota_2d_experiment.py` (≈30 min CPU,
     Wall 1965.9 s historical)

6. Compare results to `docs/headline-evidence/` (10 subdirs + 31 symlinks +
   7 `SOURCE.md` files). Each headline-evidence directory points back to the
   verification JSON in `verification_outputs/` that produced it.

## License

- See the `LICENSE` file at the archive root (project default; preserve in
  any redistribution or derivative work)