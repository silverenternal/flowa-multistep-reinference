# Pfam held-out reference subset

**Created:** 2026-09-05 (Wave 43 Agent B)
**Purpose:** provide a small, real-protein reference fasta for
`protein_sequence_validity_rate` (Kanzi real-ckpt metric). Wave 41 Agent B
flagged the missing reference as the reason the metric could not be computed
on real ckpts; this fasta unblocks it without requiring a multi-GB Pfam
download.

## File

- `random_clan.fasta` — 200 reviewed (Swiss-Prot) UniProt proteins carrying the
  Pfam `PF00001` (7tm_1, rhodopsin-like GPCR) domain annotation. PF00001 is
  the canonical entry point of clan **CL0192** (GPCR_A), so this is a
  single-clan held-out reference subset of 200 sequences (~100 KB, well below
  the 1 MB bandwidth budget).

## Download provenance

| | |
|---|---|
| Source | UniProt REST API `https://rest.uniprot.org/uniprotkb/search` |
| Query | `(xref:pfam-PF00001) AND (reviewed:true)` |
| Format | `fasta` with `fields=accession,sequence` |
| Size requested | 200 sequences |
| Size received | 200 sequences (100,547 bytes) |
| Retrieved | 2026-09-05 (Wave 43 Agent B) |

Pfam-A.clans.tsv.gz was downloaded separately (553 KB) and verified that
PF00001 → CL0192 (GPCR_A). Pfam-A.fasta.gz was *not* downloaded (6.2 GB;
exceeds the light-bandwidth constraint).

## How it is used

`tools/run_real_ckpt_eval.py` `_compute_metric()` for the Kanzi model
should read this fasta (e.g., via `Bio.SeqIO.parse`) and round-trip check
each generated token sequence against the reference set (e.g., per-residue
identity, sequence similarity, or membership test). Wire-up is owned by
**Wave 43 Agent A** (not in this agent's disjoint file scope).

## Why not a true held-out Pfam split?

A truly held-out split would require:
1. Downloading Pfam-A.full.gz (full alignment, ~30 GB) or Pfam-A.fasta.gz
   (sequences, 6.2 GB) — too bandwidth-heavy.
2. Splitting each family's seed alignment into train / held-out with the
   Pfam-recommended ratio.
3. Computing per-residue coverage of held-out positions for each generated
   sequence.

The current fasta is a *clan-representative* reference: it gives the metric
a real, well-curated protein pool to compare against (UniProt-reviewed
sequences) without claiming a per-residue Pfam-split correctness number. The
metric's purpose is to detect *catastrophic* sequence degradation (random
tokens, garbage amino acids), which this reference pool supports.

## Regeneration

If the file is lost or needs refresh:

```bash
curl -sS --max-time 60 \
  "https://rest.uniprot.org/uniprotkb/search?query=%28xref%3Apfam-PF00001%29+AND+%28reviewed%3Atrue%29&fields=accession,sequence&format=fasta&size=200" \
  -o data/pfam_holdout/random_clan.fasta
```

The query uses only public, free-of-charge UniProt REST endpoints (no API
key required).
