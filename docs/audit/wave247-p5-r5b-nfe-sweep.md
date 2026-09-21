# Wave 247 P5 — R5b CIFAR-10 RF NFE budget sweep (50/100/200) — PARTIAL

**Wave:** 247 P5  
**Date:** 2026-09-21  
**Status:** PARTIAL — NFE=50 + NFE=100 evaluated; NFE=200 NOT run  

## TL;DR

| NFE | Best scheduler | Best ΔFID% | Verdict |
|---:|---|---:|---|
| 50 | CodimensionSheetScheduler | -1.11% | framework_WINS |
| 100 | CodimensionSheetScheduler | -0.49% | framework_WINS |
| 200 | (not run) | — | — |

**WIN extends to higher NFE:** False  
**Best ΔFID% across completed cells:** -1.11%  

## 3-NFE × 4-scheduler table

| NFE | CosineAnneal | CodimensionSheet | EvidenceDriven | FreeTraj |
|---:|---:|---:|---:|---:|
| 50 | -0.17% (d_z=+4.659) | -1.11% (d_z=+4.425) | +1.34% (d_z=+4.812) | +0.78% (d_z=+4.399) |
| 100 | +0.44% (d_z=+4.710) | -0.49% (d_z=+4.597) | +0.52% (d_z=+4.665) | -0.07% (d_z=+4.529) |
| 200 | (not run) | (not run) | (not run) | (not run) |

## Best NFE per scheduler (most negative ΔFID%)

| Scheduler | Best NFE | ΔFID% at best NFE | d_z at best NFE |
|---|---:|---:|---:|
| CosineAnnealScheduler | 50 | -0.17% | +4.6592 |
| CodimensionSheetScheduler | 50 | -1.11% | +4.4254 |
| EvidenceDrivenScheduler | 100 | +0.52% | +4.6645 |
| FreeTrajScheduler | 100 | -0.07% | +4.5295 |

## Conclusion

**Based on completed NFEs, WIN does NOT uniformly extend.**
See the verdict_per_nfe_scheduler JSON field for the per-cell WIN map.


## Honest disclosure

* **NFE=200 NOT executed.** The P5 driver crashed on NFE=100 due to
  a 1800s subprocess timeout (P3 N=1000 sweep was using the same
  GPU 0 simultaneously, slowing down the N=200 NFE=100 runner beyond
  the 30-min per-NFE budget).
* **NFE=50 + NFE=100 evaluated from cached inception features.**
  NFE=50 features were cached by the P5 driver before the crash.
  NFE=100 features were computed on the fly from the .npz samples
  that the runner had written before the subprocess timeout hit.
* **D.4 byte-stable gate (30/30 PASS) is unaffected** — this evaluator
  does not modify framework source code.


## Files

* `scripts/wave247_p5_r5b_nfe_sweep.py` — main driver (crashed at NFE=100)
* `scripts/wave247_p5_p5_eval_partial.py` — partial post-crash evaluator
* `verification_outputs/wave247-p5-r5b-nfe{50,100}.csv` — per-NFE CSVs
* `verification_outputs/wave247-p5-r5b-nfe-sweep-aggregate.csv` — aggregate
* `verification_outputs/wave247-p5-r5b-nfe-sweep-summary.json` — summary

