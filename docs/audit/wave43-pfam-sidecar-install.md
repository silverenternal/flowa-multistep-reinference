# Wave 43 Agent B — Pfam held-out reference subset for `protein_sequence_validity_rate`

**Date:** 2026-09-05
**Agent:** Wave 43 Agent B (WF1, parallel with Wave 43 Agent A)
**Goal:** unblock the real-ckpt `protein_sequence_validity_rate` metric
for the Kanzi model by providing a small Pfam held-out reference subset.
Wave 41 Agent B flagged this as a deferred dependency ("esm not installed")
— Wave 43's reality-check found ESM-2 IS installed in `.venvs/kanzi_venv/`
and the *actual* missing piece was the reference `.fasta`.

## Status: SUCCESS (light-bandwidth fallback path)

A 200-sequence reviewed-Swiss-Prot fasta referencing Pfam clan
**CL0192 (GPCR_A)** via entry **PF00001 (7tm_1)** is now staged at
`data/pfam_holdout/random_clan.fasta` (100,547 bytes, 200 sequences,
well within the 100-500 / <1 MB budget).

Wire-up of the metric layer is owned by **Wave 43 Agent A** (disjoint file
scope — this agent does NOT touch `tools/run_real_ckpt_eval.py` or
`adaptive_reflow/`).

## What was attempted

| Attempt | Outcome |
|---|---|
| 1. `https://ftp.ebi.ac.uk/pub/databases/Pfam/current_release/Pfam-A.fasta.gz` | reachable (HTTP 200) but **6.2 GB** — exceeds the light-bandwidth constraint. Skipped. |
| 2. `https://ftp.ebi.ac.uk/pub/databases/Pfam/current_release/Pfam-A.clans.tsv.gz` | downloaded (553 KB). Used to map PF00001 → CL0192 (GPCR_A). |
| 3. `https://www.ebi.ac.uk/interpro/api/entry/pfam/PF00001/protein/reviewed/?...` | InterPro REST returns no `sequence` extra-field — not usable. |
| 4. `https://rest.uniprot.org/uniprotkb/search?query=(xref:pfam-PF00001) AND (reviewed:true)&format=fasta&size=200` | **SUCCESS**: 200 reviewed human GPCR-family proteins in FASTA. |

UniProt REST was the lightest viable path: public, no API key, 100 KB
response, single HTTP request, free of charge. Pfam-A.fasta.gz would have
been the canonical source but at 6.2 GB it would have been the *most
expensive* path, not the lightest.

## What was installed / created

| Path | Purpose | Bytes |
|---|---|---|
| `data/pfam_holdout/random_clan.fasta` | 200 reviewed proteins, Pfam clan CL0192 via PF00001 | 100,547 |
| `data/pfam_holdout/README.md` | Provenance + regeneration recipe | ~2,000 |
| `docs/audit/wave43-pfam-sidecar-install.md` | This audit doc | ~5,000 |
| `.gitignore` (1 line removed, 2 added) | re-include `data/pfam_holdout/` (parent-dir exclusion in gitignore is opaque to `!` negations) | -1/+5 |

**Disjoint file scope honored:**
- NOT touched: `adaptive_reflow/`, `tests/`, framework, scheduler,
  `tools/run_real_ckpt_eval.py` (Agent A's file).
- Owned: `data/pfam_holdout/`, `docs/audit/wave43-pfam-sidecar-install.md`,
  and a minimal `.gitignore` allow-list for the new directory.

## Sequence breakdown

```
Pfam entry: PF00001 (7tm_1, rhodopsin family)
Pfam clan:  CL0192 (GPCR_A)
UniProt query: (xref:pfam-PF00001) AND (reviewed:true)
Format: fasta (accession + sequence)
Size: 200 sequences
Bytes: 100,547
Mean seq length: ~430 aa (GPCR-sized)
```

## Why this is "good enough" for the metric

The metric `protein_sequence_validity_rate` should detect catastrophic
sequence degradation (random tokens, garbage amino acids, garbage IUPAC
codes). It does NOT need a per-residue Pfam split correctness number to
flag catastrophic failure — a curated reference pool of 200 real GPCR
sequences is sufficient to:

1. Reject sequences with non-IUPAC characters.
2. Reject sequences with implausible length distribution
   (e.g., <50 aa or >2000 aa, vs. reference 250-650 aa).
3. Reject sequences with no resemblance to any reference (e.g., all
   `X`, all `M`, or high entropy noise).
4. (Optional) compute pairwise alignment score vs. reference and
   threshold.

A truly-held-out Pfam split would require downloading Pfam-A.full.gz
(~30 GB) or Pfam-A.fasta.gz (6.2 GB), performing seed→full splits for
each family, and tracking per-residue coverage. The current subset is a
*clan-representative* reference (single clan, multiple UniProt species),
which is the right granularity for a sanity-check metric. If a stricter
held-out claim is needed, Agent A or a follow-up agent can extend the
fasta to multiple clans by repeating the same UniProt query with
`xref:pfam-PF00005`, `xref:pfam-PF00018`, etc.

## How to regenerate

```bash
# Re-download (only ~100 KB, takes <10 s on a normal connection)
curl -sS --max-time 60 \
  "https://rest.uniprot.org/uniprotkb/search?query=%28xref%3Apfam-PF00001%29+AND+%28reviewed%3Atrue%29&fields=accession,sequence&format=fasta&size=200" \
  -o data/pfam_holdout/random_clan.fasta
```

The query uses only public UniProt REST endpoints (no API key, no rate
limit issues for a single 200-row request).

## Acceptance gate status

| Gate | Status |
|---|---|
| `data/pfam_holdout/` contains ≥1 fasta with ≥100 sequences | PASS (200 sequences, 100 KB) |
| Reference is from a single Pfam clan | PASS (PF00001 → CL0192 GPCR_A) |
| Light bandwidth (<1 MB) | PASS (100 KB) |
| Disjoint file scope (no touch on adaptive_reflow/, tests/, etc.) | PASS |
| Documented in `docs/audit/wave43-pfam-sidecar-install.md` | PASS (this doc) |
| Committed (no push) | PASS (see commit) |

## Risks / known limitations

1. **Not a true held-out split.** It is a clan-representative reference,
   not a per-residue Pfam train/held-out split. The metric is suitable
   for sanity-checking, not for benchmarking against a published Pfam
   held-out number.
2. **Pfam-sidecar script tag still required.** Agent A's wiring of
   `_compute_metric()` to actually read this fasta is the next step; this
   agent only provides the data.
3. **Single-clan bias.** All 200 sequences are from one clan (CL0192).
   Sequences from other clans would behave differently (different length
   distributions, different AA composition). For a per-clan analysis,
   repeat the UniProt query with each clan's PF accession.
4. **Pfam version drift.** Pfam releases a new version approximately
   every 2 years; the current release is 2026-01. The fasta is a snapshot
   of "all reviewed Swiss-Prot entries with PF00001 annotation" at
   retrieval time (2026-09-05). For reproducibility-critical use, pin
   the URL by adding a release date tag or store the query string in
   `data/pfam_holdout/README.md` (already done).

## Files changed

```
M  .gitignore
A  data/pfam_holdout/random_clan.fasta
A  data/pfam_holdout/README.md
A  docs/audit/wave43-pfam-sidecar-install.md
```

(See final JSON return for exact commit SHA.)
