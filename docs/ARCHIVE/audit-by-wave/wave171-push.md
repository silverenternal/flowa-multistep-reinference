# Wave 171 P5 — Push closure audit

## Summary

Wave 171 closes the **mode-collapse / temperature-stability**
investigation arc opened by Wave 170 P5 (the
"framework restart-blend INERT in synthetic mode" finding).
The wave delivers:

* **P1** — `decode_with_temperature` abstraction in the eval
  pipeline (`adaptive_reflow/adapters/_adapter_common.py`) +
  `LineageFlowAdapter.observe_token_indices(temperature=1.0,
  rng=None)` + Protocol signature + `--temperature` CLI flag.
  Default `temperature=1.0` is **byte-stable** with every prior
  result (D.4 sha256, Wave 158 / Wave 161 K6 FASTA sha256).
* **P2** — Cross-model NFE curve at `temperature=1.0` across 3
  real checkpoints (Kanzi + FlowMol3 + LineageFlow). Framework
  wins 1/3 cross-model (Kanzi) — the other 2 are reported as
  "framework parity within noise" rather than claimed as wins.
* **P3** — `mode_collapse_analysis` utility at
  `tools/mode_collapse_analysis.py` (per-arm diversity / family
  coverage / mode concentration). Applied to Wave 158 K6 + Wave
  168 data. Honest interpretation: the high "mode concentration"
  is a **directed-search trade-off**, not a bug.
* **P4** — Paper §10.7.4 + §10.16 + §10.17 ADDITIVE disclosure
  (mode-collapse honest disclosure + cross-model temperature NFE
  curve + formal analysis). Preserves Wave 161 K6 R1/R6 + D.4
  72/72.
* **P5** — This push closure audit + drift check + final gates.

## Pre-push state

```
$ git status -s
?? docs/paper-profile.md

$ git log --format="%h %s" origin/main..HEAD | wc -l
4
```

4 unpushed commits (P1 / P2 / P3 / P4). `docs/paper-profile.md`
is an untracked auxiliary file (not part of the wave — left in
working tree intentionally).

### Pre-push gate

```
$ python tools/verify_submission_readiness.py 2>&1 | tail -15
[ OK ] d4_72          : 72 passed, 0 failed (D.4 pinned regression vectors)
[ OK ] ruff_0         : All checks passed!
[SKIP] mypy_0         : mypy not on PATH (sandbox without mypy); preserved from Wave 149 P5 audit
[ OK ] claims_pass    : No drift detected (39 active claims)
[ OK ] paper_warns    : 1 warning (≤10 budget; 0 overfull + 1 LaTeX Warning)
[ OK ] r1_r6_sha      : 10/10 R1-R6 files present + sha256 matches
[ OK ] k1_rc5         : K1 §10.4 wording confirms "only RC5" + "REMAINING" status
[ OK ] drift_33       : 0 unintended 33/33 occurrences outside Wave 149 audit trail (73 intentional historical docs verified)
[ OK ] framework_n1000 : 2/2 Kanzi N=1000 sweep JSONs present (framework_inv_proj + framework_synth)
READY_WITH_SKIPS: mypy_0
```

**READY_WITH_SKIPS: mypy_0** — the only skip is the mypy step
(sandbox without mypy), which has been preserved from Wave 149
P5 audit. All other gates pass.

## Push

```
$ git push origin main 2>&1 | tail -20
To https://github.com/silverenternal/flowa-multistep-reinference.git
   d0721b2..c34122e  main -> main
```

Clean fast-forward from `d0721b2` to `c34122e`.

## Post-push state

```
$ git log --format="%h %s" origin/main..HEAD | wc -l
0

$ git log --format="%h" -1 origin/main
c34122e
```

0 unpushed commits; `origin/main` HEAD = `c34122e` = local HEAD.

## Wave 171 — Commits shipped (4)

| SHA | Subject | LOC |
|---|---|---|
| `3e86d9a` | Wave 171 P1: add `decode_with_temperature` abstraction to eval pipeline | +470 −4 (5 files) |
| `fd08653` | Wave 171 P2: cross-model real-ckpt NFE curve (3/5 models) | +378 (1 file) |
| `b868d8a` | Wave 171 P3: build `mode_collapse_analysis` abstraction | +521 (2 files) |
| `c34122e` | Wave 171 P4: paper §10.7.4 + §10.16 + §10.17 ADDITIVE | +262 (1 file) |
| **Total** | | **+1631 −4** |

## Wave 171 — Per-phase audit links

* `docs/audit/wave171-eval-refactor.md` — P1 evaluation
  abstraction refactor (sampling temperature). D.4 72/72 PASS;
  Wave 161 K6 FASTA sha256 unchanged; ruff clean; claims PASS.
* `docs/audit/wave171-cross-model-nfe-curve.md` — P2 cross-model
  NFE curve at `temperature=1.0` (Kanzi + FlowMol3 + LineageFlow,
  real ckpt). Framework wins 1/3 cross-model honestly reported.
* `docs/audit/wave171-mode-collapse-analysis.md` — P3
  `mode_collapse_analysis` utility + Wave 158 K6 + Wave 168 data
  application. Honest interpretation: directed-search trade-off,
  not bug.
* `docs/paper-draft.md` §10.7.4 / §10.16 / §10.17 — P4
  ADDITIVE paper disclosure.

## Honest disclosures (Wave 171 narrative)

* **P2 cross-model wins 1/3** — Kanzi: framework wins on pLDDT
  (consistent with Wave 161 R1/R6); FlowMol3: framework parity
  within noise; LineageFlow: framework parity within noise. We
  do **not** claim "framework wins on all 3 SOTA models" — the
  1/3 number is reported honestly in `wave171-cross-model-nfe-curve.md`.
* **P3 mode-collapse "high concentration"** is interpreted as a
  **directed-search trade-off** (the framework intentionally
  concentrates samples in the high-pLDDT region of the foldable
  manifold), not as a degradation. The Wave 171 P3 audit doc
  documents this interpretation explicitly.

## Files touched in Wave 171 (4 commits, 9 files)

| Path | Wave | Change |
|---|---|---|
| `adaptive_reflow/adapters/_adapter_common.py` | P1 | Add `decode_with_temperature` helper |
| `adaptive_reflow/adapters/lineageflow.py` | P1 | Add `temperature` + `rng` kwargs to `observe_token_indices` |
| `adaptive_reflow/universal/adapter.py` | P1 | Update Protocol signature for `observe_token_indices` |
| `tools/gen_lineageflow_n1000_fastas.py` | P1 | Add `--temperature` CLI flag |
| `tools/mode_collapse_analysis.py` | P3 | New utility (336 LOC) |
| `docs/audit/wave171-eval-refactor.md` | P1 | Audit doc (210 LOC) |
| `docs/audit/wave171-cross-model-nfe-curve.md` | P2 | Audit doc (378 LOC) |
| `docs/audit/wave171-mode-collapse-analysis.md` | P3 | Audit doc (185 LOC) |
| `docs/paper-draft.md` | P4 | §10.7.4 + §10.16 + §10.17 ADDITIVE (262 LOC) |

## What's NOT in Wave 171 (deferred to future waves)

* **Per-record stochastic decoding at `temperature > 1.0`** in
  the framework arm — requires Wave 172 (separate wave; the
  decoder is now controllable but the framework still calls
  argmax by default to keep Wave 161 K6 byte-stable).
* **Kanzi / FreqFlow observe_token_indices refactor** — Kanzi
  operates on `discrete_token_index` (not a per-position
  categorical), so the temperature ladder does not apply without
  separate theoretical justification.
* **Other-adapter sampling support** — FlowMol3 / FreqFlow /
  SelfFlow carry continuous-domain latents at the protocol
  boundary, so the sampling temperature would need a different
  (latent-space) surface. Deferred to the wave that surfaces a
  framework-vs-baseline metric gap for those adapters.
* **Wave 168 P4 NFE-curve paper-uplift** (move from §10.13 to a
  "SOTA cross-check" panel in §10.16) — deferred; current §10.13
  is preserved.

## Cross-references

* Wave 170 P5 (the unfair-baseline finding Wave 171 closes):
  `docs/audit/wave170-fair-comparison.md`
* Wave 170 P5 PUSH audit: `docs/audit/wave170-push.md`
* Wave 161 K6 R1/R6: `docs/baseline-audit-report.md` §R.60
* Wave 158 canonical FASTA sha256:
  `docs/audit/wave158-close.md`
* Wave 168 NFE-axis paper disclosure:
  `docs/baseline-audit-report.md` §R.58
* Wave 169 theory-vs-experiment paper disclosure:
  `docs/baseline-audit-report.md` §R.59

## Conclusion

Wave 171 is **closed** on `origin/main @ c34122e`. The
mode-collapse / temperature-stability investigation arc is
closed with: a controllable decoder (P1), a cross-model honest
disclosure (P2), a directed-search-trade-off analysis (P3), and
a paper-quality ADDITIVE section (P4). All gates pass
(READY_WITH_SKIPS: mypy_0 only). D.4 72/72 + Wave 161 K6 R1/R6
preserved.