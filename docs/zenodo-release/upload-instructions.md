# Zenodo Upload Instructions — FlowA v1.0 Camera-Ready

This document gives the exact, repeatable procedure for uploading the
FlowA v1.0 camera-ready release to Zenodo and capturing the DOI for
the paper.

## Prerequisites

- ORCID account (free; sign up at https://orcid.org/). The uploader
  MUST be a Zenodo-recognised author (any co-author works).
- Tarball: `/tmp/w165/zenodo_release/flowa-v1.0-camera-ready.tar.gz`
- SHA-256: `9699cd42161ae80b81fb385f0577ee4a61f94e04cea392d6d0281af061c430d7`
- Paper draft (`docs/paper-draft.md`) abstract + author list for the
  metadata fields.

## Step 1 — Sign in to Zenodo

1. Open https://zenodo.org/.
2. Click **Log in** → **Log in with ORCID**.
3. Authorise Zenodo to read your ORCID record (it does NOT modify it).

## Step 2 — Start a new upload

1. Click **+ New upload** in the top-right.
2. Choose **New record** (not a new version — this is the first release).
3. Resource type: **Software**.

## Step 3 — Fill in metadata

| Field | Value |
|---|---|
| Title | `FlowA v1.0: Inference-time paper-quantity-driven re-inference framework` |
| Authors | per `docs/paper-draft.md` §13 author block |
| Description | paper abstract (first paragraph of `docs/paper-draft.md` §1) |
| Keywords | `flow matching`, `re-inference`, `adaptive sampling`, `NFE budget`, `scientific reproducibility` |
| License | **MIT** (matches `LICENSE` file in the tarball) |
| Version | `v1.0` |
| Publication date | today (camera-ready submission date) |

## Step 4 — Upload the tarball

1. In the **Files** section, drag-and-drop (or click to browse)
   `flowa-v1.0-camera-ready.tar.gz`.
2. Zenodo will compute its own checksum. Verify it matches the
   SHA-256 recorded in `manifest.md` (paste into a hash checker
   such as `sha256sum` locally).
3. Click **Start upload** to begin transfer (≈3 GiB; allow 5–15 min
   on a typical connection).

## Step 5 — Link to GitHub (optional but recommended)

1. In the **Related identifiers** section, add:
   - Identifier type: `url`
   - Relation: `isSupplementTo`
   - Identifier: `https://github.com/<org>/flowa-multistep-reinference`
2. This makes Zenodo automatically create a per-release badge that
   reviewers can click to verify the source.

## Step 6 — Publish

1. Review every tab (Basic info, Authors, Description, Files, Funding,
   Related identifiers).
2. Tick **I agree to the Terms of Use**.
3. Click **Publish**.

## Step 7 — Capture the DOI

1. After publish, Zenodo will show a DOI badge like
   `10.5281/zenodo.XXXXXXX`.
2. **Copy the DOI immediately** — it is the only persistent handle
   you can cite.
3. Recommended citation format (BibTeX):

   ```bibtex
   @software{flowa_v1_zenodo,
     author       = {<authors per paper §13>},
     title        = {{FlowA v1.0: Inference-time paper-quantity-driven
                     re-inference framework}},
     month        = sep,
     year         = 2026,
     publisher    = {Zenodo},
     version      = {v1.0},
     doi          = {10.5281/zenodo.XXXXXXX},
     url          = {https://doi.org/10.5281/zenodo.XXXXXXX}
   }
   ```

4. Insert the DOI into the paper at the location added in
   Wave 165 P1 (§10.10 "Code & Data Availability"):
   - The DOI itself.
   - A short sentence: "Source code, test suite, and reproducibility
     scripts are archived at Zenodo (DOI: 10.5281/zenodo.XXXXXXX)."

## Step 8 — Verify the cite round-trip

1. After publishing, click the DOI on the Zenodo record page.
2. Confirm it resolves to the correct record.
3. Confirm the tarball on the Zenodo page is downloadable (it is the
   canonical immutable snapshot, even if the source GitHub repo later
   changes).

## Common pitfalls

- **Wrong resource type**: Zenodo distinguishes "Software", "Dataset",
  and "Publication". Use **Software** for code-only; **Dataset** if
  uploading the tarball under the assumption the data is the primary
  contribution (it isn't here).
- **Forgetting the license**: Zenodo requires an explicit licence
  field before publish. MIT matches the repo.
- **Version field empty**: Zenodo will still publish, but the DOI
  badge won't show a version. Always set `v1.0` for camera-ready.
- **DOI copy mistake**: DOI strings are case-sensitive. Use the
  copy button on the Zenodo page rather than retyping.

## Re-uploading a corrected version

If a critical bug is found after publish:

1. Go to the Zenodo record.
2. Click **New version** (top-right).
3. Re-upload the fixed tarball.
4. Zenodo will mint a NEW DOI for v1.0.1 (the old v1.0 DOI still
   resolves — it is immutable). Update the paper to cite the new
   version if the change affects the scientific content.

## Re-hosting large FASTA dependencies

`data/lineageflow_upstream/databases/pfam_canonical/Pfam-A.fasta*` is
excluded from the tarball because it is 6.27 GiB. To make the
release self-contained:

1. Upload the FASTA(s) as a **separate Dataset** record on Zenodo.
2. Cite that dataset from the FlowA v1.0 record via
   **Related identifiers → IsSupplementTo**.
3. In the paper §10.10, cite BOTH the FlowA software DOI and the
   dataset DOI.

## Provenance

- Procedure authored: Wave 165 P3 (2026-09-16).
- Tested against Zenodo web UI as of Wave 165 (2026-09).
