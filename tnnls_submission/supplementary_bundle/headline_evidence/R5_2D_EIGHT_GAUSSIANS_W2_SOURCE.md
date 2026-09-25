# R5: 2D Eight Gaussians W2 -10.40% (matched NFE 500)

**Headline:** baseline W2 = 0.5579, framework W2 = 0.4999, delta = -10.40%
**N:** 1000 per arm (Wave 16 SOTA 2D RF experiment, commit 4a482ff)
**Source-of-truth:** docs/r4-survey/10-sota-2d-experiment-results.md (the per-target table)

**Per-scheduler detail:**
- CosineAnnealScheduler / CodimensionSheetScheduler / FreeTrajScheduler: W2 = 0.4999 (byte-identical)
- EvidenceDrivenScheduler: W2 = 0.5512 (PID-driven deviation)

**Reproducibility:** Re-run `python tools/run_sota_2d_experiment.py` with default 5 seeds,
20 rounds, 1000 samples/round. Wall-clock historical: 1965.9s.

---

## Post-Wave-151 P5 audit reconciliation note (2026-09-14)

**STALE absolute numbers in this SOURCE.md headline (line 3).** The R5
SOURCE.md headline says "baseline W2 = 0.5579, framework W2 = 0.4999"
but the canonical numbers per the source-of-truth (this directory's
`source_audit.md` symlink → `docs/r4-survey/10-sota-2d-experiment-results.md`
line 32 + line 55), per `docs/headline-evidence/README.md` line 21, and
per `verification_outputs/g1_deep_dive_q3_2026.json` lines 60-61 are:

- baseline W2 = **0.6606**
- framework W2 = **0.5919**
- delta = -0.0687 = **-10.40%**

Both the stale (0.5579/0.4999) and the canonical (0.6606/0.5919) values
compute to -10.40%, so the percentage headline is correct either way. The
stale absolute values 0.5579/0.4999 appear ONLY in this SOURCE.md (verified
via `grep -rn '0.5579\|0.4999'` across `docs/` and `verification_outputs/`);
no other doc carries these stale values, so there is no downstream
propagation risk.

Note: the per-scheduler detail in this SOURCE.md line 8-9 also cites
W2 = 0.4999 (stale) vs source_audit.md line 33-36 W2 = 0.5919
(canonical). The per-scheduler relative ranking (CosineAnnealScheduler
/ CodimensionSheetScheduler / FreeTrajScheduler byte-identical,
EvidenceDrivenScheduler deviating) is correct in both versions.

This note is **ADDITIVE only** — the existing prose headline numbers
above are preserved verbatim (no destructive edits to historical
SOURCE.md text). The headline percentage (-10.40%) is byte-stable across
Waves 135-151.

See `docs/audit/wave151-headline-evidence-audit.md` for the per-R
audit ledger and fix inventory.