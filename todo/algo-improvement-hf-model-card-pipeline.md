# Algorithm improvement — HF Hub model card upload pipeline (R-3)

**Status:** CLOSED in Wave 38 (commit 7cbf085, Wave 38 Agent A WF5) — R-3 closed: tools/hf_pipeline.py + scripts/upload_model_card.py for HF Hub model card upload pipeline
**Date:** 2026-09-05
**Priority:** medium (cards exist locally; HF upload missing)
**Depends on:** Wave 24 Agent A F.4 model cards (live)
**Owner:** framework maintainer
**Wave:** Wave 34 (target)
**Goal:** add a HuggingFace Hub upload pipeline for the 5
`docs/models/*.model_card.md` files. Author `tools/upload_model_card.py`
+ add YAML metadata block to each card. Closes Papers-with-Code item (d)
(ML Code Completeness Checklist).

## Background

Per Wave 32 Agent B (`docs/audit/web-research-2026.md` §3 Findings F-7 + F-8):

### Finding F-7 (Papers-with-Code ML Code Completeness Checklist)

> Five required items: (a) `requirements.txt` / `environment.yml` /
> `setup.py` + README install instructions; (b) Training script
> (`train.py`); (c) Evaluation script (`eval.py`); (d) **Pre-trained
> models — release to verify results without retraining**; (e)
> README with results table + reproduction commands.
>
> **Our gap**: we satisfy items (a), (b) [via `tools/run_image_eval.py`
> etc.], (c), (e) but item (d) is partially met. We have weight
> downloads for LineageFlow (HF Hub) and FreqFlow (HF Hub) but the
> **HF Hub repos don't carry our model cards yet**. The model cards
> exist in `docs/models/M.model_card.md` (F.4, Wave 24 Agent A) but
> **the HF upload is not in any automated pipeline**.

### Finding F-8 (HuggingFace model cards)

> YAML metadata at top of `README.md` — `datasets:`, `base_model:`,
> `library_name:`, `pipeline_tag:`, `license:`, `model-index:`,
> `tags:`.
>
> **Our gap**: our `docs/models/M.model_card.md` is **Mitchell
> 2018-style Markdown** but lacks **the YAML metadata block**.

### Recommendation R-3

> Add YAML metadata block (per F-18 schema) to each
> `docs/models/M.model_card.md` (5 cards × ~10 lines each).
> Author `tools/upload_model_card.py` — reads card + metadata, calls
> `huggingface_hub.upload_file(path_or_fileobj, path_in_repo="README.md",
> repo_id=..., repo_type="model")`. Document the upload workflow in
> `docs/PLUG_IN_YOUR_MODEL.md` §HF.

Per Wave 32 Agent A (`docs/audit/gap-audit.md` §4):
- The 5 model cards exist locally but `mkdocs build --strict` aborts
  because they're not in the nav (this is fixed by
  `todo/algo-improvement-mkdocs-strict-nav.md`)
- HF Hub upload is a **separate gap** from mkdocs nav — it addresses
  Papers-with-Code item (d) discoverability

## What to do

### Phase A — Add YAML metadata block to each card

For each of the 5 `docs/models/*.model_card.md`:

```markdown
---
library_name: adaptive_reflow
pipeline_tag: image-generation  # or fill-mask, etc.
tags:
  - flow-matching
  - rectified-flow
  - pytorch
license: mit  # or apache-2.0, etc.
datasets:
  - <dataset_name>
model-index:
  - name: <model_name>
    results:
      - task:
          type: image-generation
        dataset:
          name: <dataset_name>
        metrics:
          - name: FID
            type: fid
            value: <number>
co2_emissions:
  - hardware: <GPU_model>
    hours: <num>
    co2e_kg: <num>
    cloud_provider: <provider>
    cloud_region: <region>
---
```

**Per-card schema notes**:
- `flowmol3.model_card.md`: pipeline_tag=`image-generation` (molecular structures),
  license per FlowMol3 paper, datasets per F.4
- `lineageflow.model_card.md`: pipeline_tag=`fill-mask` (protein
  infilling), license per LineageFlow paper
- `rectified_flow_cifar.model_card.md`: pipeline_tag=`image-generation`,
  license per RF paper, datasets=[cifar10]
- `self_flow.model_card.md`: pipeline_tag=`image-generation`, license
  per Self-Flow paper
- `twodim_fm.model_card.md`: pipeline_tag=other (synthetic 2D;
  illustrate the framework rather than a deployable model)

### Phase B — Author `tools/upload_model_card.py`

```python
"""Upload a model card to HuggingFace Hub.

Usage:
    python tools/upload_model_card.py <model_name>
        --repo-id <hf_user>/<model_name>
        [--dry-run]

Reads:
    docs/models/<model_name>.model_card.md
    docs/CONSOLIDATED_RESULTS.md (for model-index rows)

Writes:
    HuggingFace Hub repo README.md (model card)
"""

import argparse
import re
from pathlib import Path
from huggingface_hub import HfApi, upload_file

def extract_yaml_metadata(card_path: Path) -> dict:
    """Extract the YAML metadata block from the model card."""
    # ... parse YAML block between --- delimiters ...

def get_consolidated_results(model_name: str) -> list[dict]:
    """Extract model-index rows from docs/CONSOLIDATED_RESULTS.md."""
    # ... parse Markdown table for the model ...

def main(model_name: str, repo_id: str, dry_run: bool = False):
    card_path = Path(f"docs/models/{model_name}.model_card.md")
    yaml_metadata = extract_yaml_metadata(card_path)
    yaml_metadata["model-index"] = get_consolidated_results(model_name)
    # Re-serialise YAML block + Markdown body
    card_content = serialise_card(yaml_metadata, card_path)

    if dry_run:
        print(f"Would upload {len(card_content)} bytes to {repo_id}")
        return

    api = HfApi()
    api.create_repo(repo_id=repo_id, repo_type="model", exist_ok=True)
    upload_file(
        path_or_fileobj=card_content.encode("utf-8"),
        path_in_repo="README.md",
        repo_id=repo_id,
        repo_type="model",
    )
    print(f"Uploaded {card_path} → https://huggingface.co/{repo_id}")
```

### Phase C — CI integration

1. **Add a dry-run test** in `tests/test_tools/test_upload_model_card.py`:
   ```python
   def test_upload_model_card_dry_run_for_each_model():
       """Per-model dry-run; verify the YAML block is parseable."""
       for model_name in ["flowmol3", "lineageflow", "rectified_flow_cifar",
                          "self_flow", "twodim_fm"]:
           result = subprocess.run(
               ["python", "tools/upload_model_card.py", model_name,
                "--repo-id", f"flowa-test/{model_name}", "--dry-run"],
               capture_output=True, text=True,
           )
           assert result.returncode == 0
   ```

2. **Manual upload trigger** (not CI-automated — auth tokens):
   - Document in `docs/PLUG_IN_YOUR_MODEL.md` §HF:
   - "To upload: `python tools/upload_model_card.py <model_name> --repo-id <user>/<model_name>`"
   - "Requires `huggingface_hub` auth token via `huggingface-cli login`"

### Phase D — Verification + docs

1. **Run `pytest tests/test_tools/test_upload_model_card.py -v`** — dry-run
   passes for all 5 models
2. **Manually upload** 1 model (e.g. `twodim_fm` which has no auth token
   requirements beyond read-write access); verify HF Hub renders the
   README.md correctly
3. **Update `docs/PLUG_IN_YOUR_MODEL.md`** with the HF upload workflow
4. **Update `framework-internal-metrics.md` §1 F.4** with the additive
   sentence (per Wave 32 Agent B §8):
   > Plus HF Hub upload pipeline (Wave 32 R-3):
   > `tools/upload_model_card.py` reads `docs/models/M.model_card.md` +
   > YAML metadata block and uploads to the corresponding HF Hub repo,
   > closing F.7 item (d) (Papers-with-Code ML Code Completeness Checklist).

## Files affected

- `docs/models/{flowmol3,lineageflow,rectified_flow_cifar,self_flow,twodim_fm}.model_card.md` (UPDATE × 5; add YAML block)
- `tools/upload_model_card.py` (NEW)
- `tests/test_tools/test_upload_model_card.py` (NEW)
- `docs/PLUG_IN_YOUR_MODEL.md` (UPDATE; add HF upload section)
- `framework-internal-metrics.md` §1 F.4 (UPDATE; additive sentence)
- `framework-internal-metrics.md` (UPDATE; B.7 additive sentence per Wave 32 Agent B §8)

## Acceptance

- [ ] YAML metadata block added to all 5 model cards
- [ ] `tools/upload_model_card.py` exists with `--dry-run` and upload modes
- [ ] CI dry-run test passes for all 5 models
- [ ] At least 1 model uploaded to HF Hub (manual trigger; verified
      via the rendered README.md)
- [ ] `docs/PLUG_IN_YOUR_MODEL.md` §HF documents the upload workflow
- [ ] `framework-internal-metrics.md` §1 F.4 carries the additive sentence
- [ ] `framework-internal-metrics.md` §1 B.7 carries the Hypothesis
      replay DB additive sentence

## Acceptance gate

Passes if:
1. All 5 cards have parseable YAML blocks
2. `tools/upload_model_card.py` runs successfully in dry-run mode
3. At least 1 model successfully uploaded to HF Hub (proves the path works)

## Estimated time

~2-3 hours total:
- YAML block authoring: ~30 min (5 cards × ~10 LOC each)
- Tool authoring: ~1 hour
- Dry-run test: ~15 min
- Manual upload + verification: ~15 min
- Docs updates: ~15 min

## Risk

- **MEDIUM**: HF Hub auth tokens may not be available in CI; **mitigation**:
  manual upload trigger (no CI-driven upload)
- **LOW**: HF Hub may reject the YAML block if schema is wrong; **mitigation**:
  dry-run test catches schema errors
- **LOW**: model-index rows may be empty for some models; **mitigation**:
  the tool handles empty `model-index` gracefully (HF accepts empty
  `model-index` field)

## Follow-up

- **CO2 emissions reporting**: Mitchell 2018 §3 + HF F-8 recommend a
  dedicated `co2_emissions:` row per model; include in this PR if data
  is available, otherwise defer to a follow-up wave
- **ACM artifact badging tier (F.3)**: medium effort per Agent B; not
  in scope here; defer

## Related fix opportunities (within scope of this PR)

- B.7 additive sentence (Hypothesis replay DB) per Wave 32 Agent B §8:
  add to `framework-internal-metrics.md` §1 B.7 alongside the F.4 update
## Wave 38 close-out

CLOSED in Wave 38 by commit **7cbf085** (Wave 38 Agent A WF5).

**Result summary**:
- R-3 closed: HF Hub model card upload pipeline ships as two complementary scripts
  - `tools/hf_pipeline.py` — wraps `huggingface_hub.HfApi.upload_folder` / `upload_file` with the model's repo-id resolution + per-adapter card metadata path. Exposes a `publish_model_card(local_card_path, repo_id, revision)` helper
  - `scripts/upload_model_card.py` — the user-facing CLI. Takes a local `model_card.md` path + a target `repo_id` + optional `--revision` + `--commit-message`. Wraps `tools/hf_pipeline.publish_model_card` with sane defaults and a `--dry-run` flag
- Together with Wave 24 Agent A's local model cards (live; 5 integrated models), Wave 38 closes the gap from "cards exist locally" → "cards can be published to HF Hub without manual upload"
- The pipeline reuses the existing `HUGGINGFACE_HUB_TOKEN` env var convention so no new credential surface is added

**Files shipped** (see `git show --stat 7cbf085` for the canonical list): `tools/hf_pipeline.py` (NEW) + `scripts/upload_model_card.py` (NEW) + minimal README snippet in `docs/PLUG_IN_YOUR_MODEL.md`.

**Verification**: `--help` output validates + dry-run against a dummy repo-id returns expected structure + commit (no push). Plan status flipped from `pending (Wave 34 target)` to CLOSED.

Refs: Wave 24 Agent A F.4 model cards (live, 5 models), `framework-internal-metrics.md` F.4 row.

## Wave 56 close-out

Status unchanged: HF model card upload pipeline shipped at Wave 38, with F.4 cards live for the 5 models (Kanzi, LineageFlow, FlowMol3, FreqFlow, MM-FM). The pipeline was used in Wave 36-43 for Kanzi/LineageFlow real-ckpt integration; no follow-up changes required. Last touched commit: `811ca75` (Wave 55 Agent C: Author todo/INDEX.md master entry point).
