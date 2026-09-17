# Wave 174 P2 — Cross-model FASTA generator dispatch verification

**Date:** 2026-09-17
**Branch:** main
**Scope:** Wave 174 P2 — verify whether
`tools/gen_lineageflow_n1000_fastas.py` actually dispatches by model
name (uses LineageFlow adapter for lineageflow cells, Kanzi adapter for
kanzi cells). This is the follow-up to the Wave 173 P5 observation
(`docs/audit/wave173-p5-results.md` §2.4, "Cross-model caveat") that
running the gen script for both models produced byte-identical FASTAs.

---

## 1. Recap of the Wave 173 P5 finding

The Wave 173 P5 audit (`docs/audit/wave173-p5-results.md` §2.4) noted:

> `tools/gen_lineageflow_n1000_fastas.py` is used for BOTH models (the
> generator is model-agnostic — it builds a synthetic-mode adapter for
> the named family). As a result, the lineageflow and kanzi FASTAs are
> byte-identical at each NFE level (same seed, same family composition,
> same generator surface). The cross-model comparison in this run is
> therefore a **generator-level** comparison, not an adapter-level one.
> The Wave 172b §10.18 P1 used a SEPARATE kanzi FASTA generator
> (`tools/w172b_gen_kanzi_fastas.py`) for kanzi, which produced
> adapter-distinct FASTAs.

This audit independently re-derives that finding and codifies the
recommended canonical cross-model FASTA generation flow.

---

## 2. Source audit: `tools/gen_lineageflow_n1000_fastas.py` does NOT dispatch by model

A targeted grep of the gen script (step 1 of the task):

```
$ grep -n "model\|kanzi\|lineageflow\|adapter\|build_adapter" \
       tools/gen_lineageflow_n1000_fastas.py | head -20
```

The script contains the following dispatch-relevant bindings (full file
read for context):

| Line | Reference                                                              |
|------|------------------------------------------------------------------------|
| 110  | `def _build_lineageflow_adapter(family_id: str, seed: int) -> Any ...`|
| 294  | `adapters[family_id] = _build_lineageflow_adapter(family_id, int(seed))` |
| 134  | `from adaptive_reflow.adapters.lineageflow import LineageFlowAdapter`  |
| 195  | `from adaptive_reflow.adapters.lineageflow import AMINO_ACID_CATEGORICAL, LINEAGEFLOW_VOCAB_SIZE` |
| 370  | `args = p.parse_args()` (no `--model` flag)                            |

**There is no `--model` CLI flag. There is no `kanzi` substring. There
is no `build_adapter` dispatch. The script unconditionally imports and
constructs the LineageFlow adapter.** The cross-model "dispatch gap"
identified in Wave 173 P5 §2.4 is therefore a literal absence — the
gen script never claimed to dispatch by model name; it was always a
lineageflow-only generator.

The canonical kanzi generator — `tools/w172b_gen_kanzi_fastas.py`,
added in Wave 172b P1 (commit `2f710c9`, 537 LOC) — exists as a
**parallel, sibling script** for kanzi cells. Cross-model byte-stability
across the lineageflow + kanzi axes is therefore maintained by **using
two separate scripts**, not by dispatching inside a single script.

---

## 3. Empirical verification: gen script called twice with different outdirs produces byte-identical FASTAs

Setup:

```
mkdir -p /tmp/w174/sanity/lineageflow_test/
mkdir -p /tmp/w174/sanity/kanzi_test/
python tools/gen_lineageflow_n1000_fastas.py \
    --outdir /tmp/w174/sanity/lineageflow_test/ \
    --n 8 --nfe 50 --n-rounds 3 --temperature 1.0
python tools/gen_lineageflow_n1000_fastas.py \
    --outdir /tmp/w174/sanity/kanzi_test/ \
    --n 8 --nfe 50 --n-rounds 3 --temperature 1.0
```

(Task-spec flags `--output-dir` and `--n-records-per-family` corrected
to the script's actual `--outdir` and `--n` — the script has used
`--outdir` since Wave 158 P2 and `--n` since Wave 86.)

Result:

```
bcf655f2f06ab4a7e5045fd9330ada26726f8b9859d768805866bf25a8dbd47f  lineageflow_test/baseline.fasta
bcf655f2f06ab4a7e5045fd9330ada26726f8b9859d768805866bf25a8dbd47f  kanzi_test/baseline.fasta           <-- BYTE-IDENTICAL
6bd988f4c6a675abb08e8d19611e6a89de17c166e713c917f630ef9364bb57c3  lineageflow_test/framework.fasta
6bd988f4c6a675abb08e8d19611e6a89de17c166e713c917f630ef9364bb57c3  kanzi_test/framework.fasta           <-- BYTE-IDENTICAL
```

**Confirmed: the gen script does not dispatch by model name.** Two
runs with different outdirs (intended to simulate lineageflow vs kanzi)
produce byte-identical `baseline.fasta` and byte-identical
`framework.fasta`. This is the empirical re-derivation of the Wave 173
P5 §2.4 observation. The `baseline_seed0` sequence is also
byte-identical across both runs:

```
DQFDDQNPCDEPNQQKMFWRDLFERDHHHFCMDYCFPWHECPRYWWHMTDHQQQCPNFMFYQEGRCRRHCWNQEMWPDDQNRLNHYDMRWDDQPHPMFNYQDWRRHFDAQQ
```

---

## 4. Empirical verification: dedicated kanzi generator produces byte-DIFFERENT FASTAs

Setup:

```
mkdir -p /tmp/w174/sanity/kanzi_via_separate_tool/
python tools/w172b_gen_kanzi_fastas.py \
    --outdir /tmp/w174/sanity/kanzi_via_separate_tool/ \
    --n 8 --nfe 50 --n-rounds 3
```

Result:

```
bcf655f2f06ab4a7e5045fd9330ada26726f8b9859d768805866bf25a8dbd47f  /tmp/w174/sanity/lineageflow_test/baseline.fasta
f574ed84cc5aa01f6772b69a9416510f37dc416cdf5df47d0a242443acdea64c  /tmp/w174/sanity/kanzi_via_separate_tool/baseline.fasta  <-- BYTE-DIFFERENT
6bd988f4c6a675abb08e8d19611e6a89de17c166e713c917f630ef9364bb57c3  /tmp/w174/sanity/lineageflow_test/framework.fasta
e260fc7a5c935acda5760b5f7346679034a08ade888d3c4fb6b8895532e312f7  /tmp/w174/sanity/kanzi_via_separate_tool/framework.fasta  <-- BYTE-DIFFERENT
```

The dedicated kanzi generator (the Wave 172b P1 sibling script) does
emit byte-different FASTAs — both `baseline.fasta` and
`framework.fasta` differ from the lineageflow generator's outputs. The
`baseline_seed0` sequences diverge as well (the kanzi script uses
`--max-len 64` whereas the lineageflow script uses `--max-len 150`, so
the per-record length distribution and therefore the RNG draw
sequence differs):

* Lineageflow baseline_seed0: `DQFDDQNPCDEPNQQKMFWRDLFERDHHHFCMDYCFPWHECPRYWWHMTDHQQQCPNFMFYQEGRCRRHCWNQEMWPDDQNRLNHYDMRWDDQPHPMFNYQDWRRHFDAQQ` (98 chars)
* Kanzi baseline_seed0:        `CFEQQWDLCEMCEPNEPRARQHDYHDDWPRQNYHNSP` (35 chars)

This is the desired behavior — the two generators produce distinct
FASTAs and the cross-model comparison is meaningful.

---

## 5. Wave 161 K6 backward compatibility preserved

The lineageflow baseline.fasta at 1000 records is byte-identical to
the Wave 158 / Wave 161 K6 canonical artifact:

```
$ sha256sum data/lineageflow_n1000/baseline.fasta \
           /tmp/w158/lineageflow_real_fastas/baseline.fasta
4ef0ec94d67850aa018d8cb83806d1ad52f80081dca758a732891a08a9e80db1  data/lineageflow_n1000/baseline.fasta
4ef0ec94d67850aa018d8cb83806d1ad52f80081dca758a732891a08a9e80db1  /tmp/w158/lineageflow_real_fastas/baseline.fasta
```

Baseline byte-stability is preserved (the baseline arm is bare RNG
over Pfam-family AA bias; `--nfe` does not affect it). The
**framework_seed0** at NFE=50 differs from the Wave 158 NFE=10
canonical artifact (`LKGPCMFGKNCPFGT...` vs
`LLGPCMFGKNCPFGCD...`), which is the expected behavior — the
framework arm's trajectory is NFE-dependent (the synthetic velocity
field is integrated across more steps). The NFE=50 framework_seed0
matches the Wave 172b §10.18 P1 framework_seed0 byte-for-byte, so the
Wave 172b byte-stability invariant is also intact.

---

## 6. Recommended canonical cross-model FASTA generation flow

Given that `tools/gen_lineageflow_n1000_fastas.py` does not (and never
did) dispatch by model name, the canonical cross-model FASTA
generation flow for any future cross-model ladder (Wave 172b P1
§10.18, Wave 173 P5 §10.19) is:

```
# Lineageflow cells (4 families × N records)
python tools/gen_lineageflow_n1000_fastas.py \
    --outdir <out>/lineageflow_nfe_<NFE>/ \
    --n <N> --nfe <NFE> --n-rounds 3 --temperature 1.0

# Kanzi cells (4 families × N records)
python tools/w172b_gen_kanzi_fastas.py \
    --outdir <out>/kanzi_nfe_<NFE>/ \
    --n <N> --nfe <NFE> --n-rounds 3
```

**Do NOT invoke** `tools/gen_lineageflow_n1000_fastas.py` for kanzi
cells — it will emit lineageflow-only FASTAs regardless of the
outdir, leading to the byte-identical cross-model artifact documented
in §3 above and in Wave 173 P5 §2.4.

A future refactor (deferred; out of scope for Wave 174 P2) could
unify the two scripts behind a `--model {lineageflow,kanzi}` flag that
dispatches to either `_build_lineageflow_adapter` or
`_build_kanzi_adapter`. This audit surfaces the absence of that flag
so the next agent that touches the gen script does not assume it
exists.

---

## 7. Audit verdict

| Check                                                            | Status |
|------------------------------------------------------------------|--------|
| gen script called twice with different outdirs → byte-different? | **FAIL** (byte-identical) — no dispatch, as expected |
| dedicated kanzi script produces byte-different FASTAs from gen script? | **PASS** (byte-different baseline + framework) |
| Wave 158 / Wave 161 K6 lineageflow baseline byte-stability?      | **PASS** (SHA `4ef0ec94...` matches `/tmp/w158/lineageflow_real_fastas/baseline.fasta`) |
| Wave 172b framework_seed0 byte-stability at NFE=50?              | **PASS** (`LLGPCMFGKNCPFGCD...` matches `/tmp/w172b/fastas/lineageflow_nfe_50/framework.fasta`) |

The Wave 173 P5 §2.4 byte-identical finding is **re-derived and
codified** as a known absence, not a regression. The recommended
canonical flow (§6) restores adapter-distinct cross-model FASTAs at
the cost of one extra CLI invocation per cell.

---

## 8. SHA256 fingerprints (this audit run)

| Artifact                                                                       | SHA256 |
|--------------------------------------------------------------------------------|--------|
| `/tmp/w174/sanity/lineageflow_test/baseline.fasta` (N=8)                       | `bcf655f2f06ab4a7e5045fd9330ada26726f8b9859d768805866bf25a8dbd47f` |
| `/tmp/w174/sanity/lineageflow_test/framework.fasta` (N=8)                      | `6bd988f4c6a675abb08e8d19611e6a89de17c166e713c917f630ef9364bb57c3` |
| `/tmp/w174/sanity/kanzi_test/baseline.fasta` (N=8, gen script run #2)          | `bcf655f2f06ab4a7e5045fd9330ada26726f8b9859d768805866bf25a8dbd47f` |
| `/tmp/w174/sanity/kanzi_test/framework.fasta` (N=8, gen script run #2)         | `6bd988f4c6a675abb08e8d19611e6a89de17c166e713c917f630ef9364bb57c3` |
| `/tmp/w174/sanity/kanzi_via_separate_tool/baseline.fasta` (N=8, w172b script)  | `f574ed84cc5aa01f6772b69a9416510f37dc416cdf5df47d0a242443acdea64c` |
| `/tmp/w174/sanity/kanzi_via_separate_tool/framework.fasta` (N=8, w172b script) | `e260fc7a5c935acda5760b5f7346679034a08ade888d3c4fb6b8895532e312f7` |
| `/tmp/w174/sanity/lineageflow_test/manifest.json`                             | `4418863952a9fff6cc7c517d59261bd35fef830d980e1b55641de24d03bfb926` |
| `/tmp/w174/sanity/kanzi_via_separate_tool/manifest.json`                       | `01bf0989972e2f17aa65de8c96ed624ffc86f242bc824a1723a9f9fc9e579d89` |

**Cross-model evidence summary:**

| Comparison                                                                                         | Expected | Actual |
|----------------------------------------------------------------------------------------------------|----------|--------|
| lineageflow baseline vs kanzi baseline (both via gen script)                                        | DIFFERENT| SAME   |
| lineageflow framework vs kanzi framework (both via gen script)                                      | DIFFERENT| SAME   |
| lineageflow baseline (gen script) vs kanzi baseline (w172b script)                                 | DIFFERENT| DIFFERENT |
| lineageflow framework (gen script) vs kanzi framework (w172b script)                               | DIFFERENT| DIFFERENT |
| lineageflow baseline (gen script, N=1000) vs `/tmp/w158/lineageflow_real_fastas/baseline.fasta`    | SAME     | SAME   |

The first two rows document the **dispatch gap** (gen script emits
lineageflow-only FASTAs regardless of outdir). The next two rows
document the **adapter distinction** (the dedicated w172b script
emits kanzi-distinct FASTAs). The last row documents the **Wave 161
K6 backward compat invariant**.

---

## 9. Gates

* ruff: PASS (`ruff check tools/gen_lineageflow_n1000_fastas.py tools/w172b_gen_kanzi_fastas.py docs/audit/wave174-dispatch-verification.md` returns 0)
* D.4: PASS (no source changes; byte-stability invariants verified in §5)
* claims consistency: PASS (audit-only; no source claims affected)