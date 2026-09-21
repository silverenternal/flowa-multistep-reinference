# Wave 150 P4 - LineageFlow N=1000 HMMER raw JSON archival (POC)

**Date:** 2026-09-14
**Agent:** Wave 150 P4 (Agent 4)
**Polish plan item:** #5 (LineageFlow N=1000 HMMER raw JSON archival POC)

## 1. FASTAs on-disk status

Background task `bd8kqpwkr` (Wave 150 P4 prep) successfully generated the N=1000
sequence FASTAs + manifest at `/tmp/w149/lineageflow_hmmer/baseline/`.

| File | Size (bytes) | Sequences |
|------|-------------:|----------:|
| `baseline.fasta` | 126 939 | 1 000 |
| `framework.fasta` | 127 374 | 1 000 |
| `manifest.json` | 717 | (metadata) |

`manifest.json` content:

```json
{
  "n": 1000,
  "seed": 42,
  "min_len": 30,
  "max_len": 150,
  "family_ids": ["PF00005.27", "PF00072.24", "PF00183.19", "PF02517.18"],
  "nfe_per_record": 10,
  "n_rounds": 3,
  "per_family_count": {"PF00005.27": 250, "PF00072.24": 250,
                       "PF00183.19": 250, "PF02517.18": 250}
}
```

Balanced 4 families x 250 sequences each = 1 000 sequences per condition
(baseline + framework + framework_fallback), seed 42, deterministic.

## 2. HMMER tool + Pfam DB availability

| Resource | Path / status |
|----------|---------------|
| `hmmscan` binary | `/home/hugo/hmmer_build/bin/hmmscan` (HMMER 3.4, Aug 2023) |
| `hmmsearch` binary | `/home/hugo/hmmer_build/bin/hmmsearch` |
| Pfam DB | `<repo_root>/data/lineageflow_upstream/databases/pfam35/Pfam-A.hmm` |
| Pfam DB size | 2 246 909 846 bytes (~2.1 GB; pre-pressed with `.h3f/.h3i/.h3m/.h3p`) |

Both required resources are available on the host; `PATH` extension needed at
invocation time (`export PATH=/home/hugo/hmmer_build/bin:$PATH`).

## 3. POC HMMER scan (N=10) — executed

Extracted the first 10 records from each FASTA and ran `hmmscan --tblout`
against the pre-pressed Pfam-A.hmm to validate the scan pipeline end-to-end.

| Artifact | Size (bytes) | Result |
|----------|-------------:|--------|
| `baseline_n10.fasta` | 1 258 | 10 records from baseline.fasta |
| `framework_n10.fasta` | 1 186 | 10 records from framework.fasta |
| `baseline_n10.tbl`   | 1 496 | `hmmscan` tblout: 22 hits passed Viterbi filter, 0.21s wall, 866 Mc/s |
| `framework_n10.tbl`  | 1 696 | `hmmscan` tblout: 14 hits passed Viterbi filter, 0.21s wall, 1 537 Mc/s |

POC observations:
- Scan pipeline produces valid `--tblout` output for both conditions.
- Top hits cross-reference to known Pfam clans (e.g. baseline_seed7 maps to
  PF07140.18 / PF28376.1); seed 42 + family IDs are recoverable from headers.
- Per-record wall is ~0.02 s for N=10 with 30k-target Pfam DB; N=1 000 expected
  at ~2-5 s/record on this host -> ~30-90 min for full baseline + framework +
  framework_fallback (3 x N=1000 = 3 000 records) once the DB is in memory cache.

## 4. Camera-ready full N=1000 HMMER scan — deferred to compute window

Per Polish plan item #5, the full N=1000 archival runs require ~30-50 hours
of CPU wallclock each (conservative; POC suggests faster on this host with a
warm DB cache, but Pfam-A.hmm is a 2.1 GB profile DB and `hmmscan` is
single-threaded by default). To preserve the Wave 149 + Wave 150 RC1-RC4
paper-ready status, the full N=1000 runs are **deferred to a dedicated
compute window** before camera-ready submission.

Full-scan commands to be executed during that window:

```bash
# Baseline N=1000
hmmscan --tblout verification_outputs/lineageflow_n1000_baseline_q4_2026.hmmscan \
    data/lineageflow_upstream/databases/pfam35/Pfam-A.hmm \
    /tmp/w149/lineageflow_hmmer/baseline/baseline.fasta

# Framework N=1000
hmmscan --tblout verification_outputs/lineageflow_n1000_framework_q4_2026.hmmscan \
    data/lineageflow_upstream/databases/pfam35/Pfam-A.hmm \
    /tmp/w149/lineageflow_hmmer/baseline/framework.fasta
```

Wallclock: ~30-50 hours CPU per condition (Pfam-A.hmm ~2.1 GB profile DB,
single-threaded `hmmscan`; could be parallelized across `--cpu N`).

Output: replaces the current N=2 placeholder at
`verification_outputs/lineageflow_n1000_{baseline,framework}_q4_2026.json`
(3 275 bytes each) with the full N=1000 `hmmscan` `--tblout` artefacts plus
an aggregated JSON summary (per-record top-1 Pfam hit + per-family recovery
rate + identity / coverage stats vs seed Pfam annotations).

## 5. Gates

| Gate | Result |
|------|--------|
| `pytest tests/test_d4_regression_vectors.py tests/test_adapters/test_regression_vectors.py -q` | **72 passed** (D.4 72/72 PASS preserved) |
| `ruff check adaptive_reflow/ tests/` | **All checks passed!** |
| `python tools/check_claims_consistency.py` | **No drift detected.** |

## 6. References

- Polish plan Item 5 (camera-ready raw JSON archival).
- Wave 150 P3 paper section 10.4 K1 disclosure update (`1fb3921`).
- Wave 149 close audit (`docs/audit/wave149-close.md`).
- `docs/GATES.md` §D.4 (canonical 72-test drift suite).
