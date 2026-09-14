# Wave 44 — D.1 Shrink Synthesis + Final Verify

**Agent:** Wave 44 Agent E (final verify + D.1 shrink synthesis)
**Date:** 2026-09-07
**Baseline commit:** `ecced10` (Wave 43 Agent C: final verify + cleanup/paper synthesis)
**HEAD at measurement:** `64a7b8d`

> **Measurement caveat.** Wave 45 agents were editing the working tree
> *while* this audit ran. `kanzi.py` changed from 1860 → 1875 → 1876
> lines between the first and last measurement, and HEAD advanced from
> `c61b767` to `64a7b8d`. All figures below are pinned to the commits
> and diffs named in each row. Re-run before quoting in the paper.

---

## 1. Verdict

| Check | Result |
|---|---|
| `pytest tests/test_adapters/` | **FAIL** — 1 failed, 976 passed, 77 skipped (373.51 s) |
| `mkdocs build --strict` | **PASS** — built in 9.88 s, exit 0 |
| D.1 adapter-LOC median | **UNCHANGED** — 1539.5 before, 1539.5 after |
| 4-adapter net LOC | **−72** (258 removed, 186 added) |

The wave is **not push-ready**: one adapter test fails (§4).

---

## 2. What "the 4 shrink adapters" are

Wave 44 touched seven adapters, but only four were scoped as D.1
*shrink* work — the four with a `docs/audit/wave44-*-shrink.md` doc.
The other three (`mnist_fm`, `rectified_flow_cifar`, `twodim_fm`) were
WF3 **core-adoption** work documented as `wave44-*-core.md`; they adopt
framework-core helpers but were not LOC-reduction tasks and all three
grew.

Commit subjects are unreliable here and should not be used to attribute
this work: `937fd14` is titled "hidream_i1 per-adapter shrink" but edits
`kanzi.py` and `lineageflow.py` only, and `3648fbe` is titled "mnist_fm
per-adapter framework-core adoption" but edits `flowmol3_v2_adapter.py`.
The rows below are attributed by **diff content**, not by subject line.

---

## 3. D.1 shrink result — the four adapters

| Adapter | Source of change | Added | Removed | **Net** |
|---|---|---:|---:|---:|
| `flowmol3_v2_adapter.py` | commit `3648fbe` | 39 | 54 | **−15** |
| `hidream_i1.py` | **uncommitted** working tree | 55 | 85 | **−30** |
| `kanzi.py` | commit `2afb199` (shrink only) | 48 | 49 | **−1** |
| `protbfn_abbfn_adapter.py` | commit `caec94b` | 44 | 70 | **−26** |
| **Total** | | **186** | **258** | **−72** |

- **`total_lines_removed` = 258** raw deletions; **net reduction = 72**.
  The net figure is the honest one to quote as "shrink".
- **`hidream_i1` is uncommitted.** Its −30 lines and its audit doc
  `docs/audit/wave44-hidream-i1-shrink.md` are both untracked. This
  result is lost if the tree is cleaned.
- **`kanzi` netted −1, not −103.** The shrink commit `2afb199` removed
  49 and added 48. Kanzi's whole-wave delta is **+118** (1758 → 1876)
  because WF2 `937fd14` added `observe_token_indices` (+130/−26) and
  Wave 45 added +16 more. Kanzi grew during Wave 44; it did not shrink.

Median LOC of these four adapters after the wave: **2046.0**
(1876, 1950, 2142, 3258).

---

## 4. Push blocker — Protocol / audit-table drift

`tests/test_adapters/test_protocol_deep_audit.py::test_j_audit_inventory_smoke`
fails:

```
AssertionError: audit covers Protocol methods {...9 methods...} but the
Protocol declares additional methods {'observe_token_indices'};
update PROTOCOL_METHOD_SHAPE
```

**Root cause.** Commit `937fd14` added `observe_token_indices` to the
`FlowMatchingODEAdapter` Protocol in `adaptive_reflow/universal/adapter.py:328`
but did not update the audit's `PROTOCOL_METHOD_SHAPE` table. The J.1
test exists precisely to fire closed on this, and it did. This is the
test working as designed, not a flaky failure.

**The fix is a design decision, not a typo.** `observe_token_indices` is
declared on the *required* Protocol surface but only 2 of 16 registered
adapters implement it (`kanzi`, `lineageflow`). Two options:

1. **Treat it as optional** (recommended). Move it into the existing
   `OPTIONAL_METHOD_SHAPE` table — the established precedent for
   `inject_forward_noise`, which is likewise detected via `hasattr` —
   and subtract `OPTIONAL_METHOD_SHAPE` keys from the required set in
   the J.1 inventory check. The Protocol docstring already reads as
   optional ("Adapters that implement this method are responsible
   for..."). Shape entry: `(("trace", "paper_quantities"), {})`.
2. **Treat it as required.** Then it must be implemented on all 16
   registered adapters, which is a much larger change.

**Not applied by this agent, deliberately.** Choosing between required
and optional Protocol surface belongs to the agent that introduced the
method, and three Wave 45 agents were mid-flight in exactly this
subsystem (`kanzi.observe_token_indices`, the eval-pipeline adapter
signatures) while this audit ran. Adding it to `PROTOCOL_METHOD_SHAPE`
naively would additionally parametrise tests A.1/A.2/H.1 across all
adapters and cascade new failures. `test_protocol_deep_audit.py` itself
is untouched by any in-flight agent, so the fix applies cleanly whenever
the required-vs-optional call is made.

---

## 5. D.1 metric — no movement

D.1 is defined in `todo/framework-internal-metrics.md` as "adapter line
count median", target ≤ 500.

| | Median |
|---|---:|
| Before (`ecced10`) | **1539.5** |
| After (`64a7b8d` + working tree) | **1539.5** |
| Target | ≤ 500 |

Measured over the 16 adapters in `ADAPTER_REGISTRY`, resolved to their
defining module via `inspect.getsourcefile`. (The metric's stated "18"
counts `synthetic_continuous` and `synthetic_mixed_channel`, which share
`synthetic.py`; 16 distinct registered entries exist today.)

**The median did not move.** It sits between `freqflow` (1537) and
`graphbfn` (1542) — neither of which Wave 44 touched. The four shrink
adapters are all far above the median (1876–3258), so removing 72 lines
from the top of the distribution cannot shift the midpoint. D.1 is
**still 3.1× its target** and Wave 44 made no measurable progress on it.

To move this metric, future waves must either shrink the adapters
sitting *at* the median (`freqflow`, `graphbfn`, `lineageflow`,
`wan2_2_video`, `self_flow`, `twodim_fm`) or cut the large adapters by
roughly an order of magnitude rather than by 1–2%.

Full distribution after Wave 44 (registry order by size):

| LOC | Adapter | | LOC | Adapter |
|---:|---|---|---:|---|
| 337 | `toy_linear` | | 1731 | `lineageflow` |
| 536 | `flowmol3` | | 1779 | `wan2_2_video` |
| 553 | `toy_gaussian` | | 1850 | `lumina_image_2_0` |
| 991 | `mnist_fm` | | 1876 | `kanzi` |
| 1363 | `rectified_flow_cifar` | | 1950 | `hidream_i1` |
| 1488 | `self_flow` | | 2142 | `protbfn_abbfn` |
| 1492 | `twodim_fm` | | 3258 | `flowmol3_v2` |
| 1537 | `freqflow` | | | |
| 1542 | `graphbfn` | | | |

---

## 6. Recommended next actions

1. **Resolve the Protocol drift** (§4) — blocks push.
2. **Commit or discard `hidream_i1.py`** — the only shrink of the four
   that is not yet in git, along with its audit doc.
3. **Correct the three mislabelled commit subjects** in any wave summary
   that cites them, or downstream attribution will be wrong.
4. **Re-scope D.1** — either target the median-adjacent adapters, or
   revise the ≤ 500 target, which four waves of shrink work have not
   moved.

---

## 7. Reproduction

```bash
.venvs/flowmol3_venv/bin/python -m pytest tests/test_adapters/ -q --tb=line
.venvs/flowmol3_venv/bin/mkdocs build --strict
git diff --numstat ecced10..HEAD -- adaptive_reflow/adapters/
```

Median, over the live registry:

```python
import inspect, pathlib, statistics
from adaptive_reflow.adapters import ADAPTER_REGISTRY
statistics.median(
    len(pathlib.Path(inspect.getsourcefile(c)).read_text().splitlines())
    for c in ADAPTER_REGISTRY.values()
)
```
