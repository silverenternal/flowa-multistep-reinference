# Wave 42 — MUST-3 adapter-shrink synthesis (Agent E final verify)

**Date:** 2026-09-05
**Agent:** Wave 42 Agent E (final verify + summary)
**Scope:** the four per-adapter D.1 shrinks landed in Wave 42
(`mnist_fm`, `rectified_flow_cifar`, `twodim_fm`, `self_flow`), and
whether they close the `MUST-3` PARTIAL in
`todo/framework-freeze-checklist.md`.

**Headline: MUST-3 stays PARTIAL. It is not PASS, and Wave 42 did not
move the sub-criterion that gates it.** The line-count work is real and
green, but it landed on the wrong four adapters to satisfy the contract
as written. Details in §3.

---

## 1. Verification commands (all re-run at HEAD by this agent)

| Command | Result |
|---|---|
| `pytest tests/test_adapters/ -q` | **977 passed, 77 skipped** in 464 s |
| `pytest tests/test_framework/test_assert_adapter_compliance.py -q` | **18 passed, 3 skipped** in 18 s |
| `pytest tests/test_core/ -q` | **83 passed, 1 skipped** in 6 s |
| `mkdocs build --strict` | **exit 0**, built in 9.57 s |

### 1.1 One regression found and fixed by this agent

The first `tests/test_adapters/` run came back **1 failed, 976 passed**:

```
FAILED tests/test_adapters/test_adapter_common.py::test_make_ref_prefixes_are_unchanged
ImportError: cannot import name '_make_ref' from
  'adaptive_reflow.adapters.rectified_flow_cifar'
```

This is a Wave 42 self-inflicted breakage, not a pre-existing one.
Agent C's `rectified_flow_cifar` shrink (`1d3cd2f`) deleted the private
`_make_ref` wrapper and inlined the shared helper at both call sites:

```python
ChannelName("image"): make_ref("rf_cifar:image", "initial", batch=..., sample=...)
```

That refactor is correct — the `rf_cifar:image` TensorRef namespace is
byte-identical either way, so `native_config_hash` and the ledger chain
are untouched — but `test_adapter_common.py` still imported the deleted
symbol. **The commit shipped with a red test that Agent C did not
re-run at repo scope** (the adapter's own `test_rectified_flow_cifar.py`
passes; only the cross-adapter namespace guard broke).

Fixed in the working tree by rewriting the rf arm of the guard to call
the shared helper with the same prefix, preserving the test's actual
intent (namespace stability, not wrapper existence):

```python
def rf_ref(label: str, **parts: object) -> object:
    return make_ref("rf_cifar:image", label, **parts)
```

Post-fix: `tests/test_adapters/` is **977 passed, 77 skipped**. The fix
is **uncommitted** — see §5.

---

## 2. Lines removed — reported straight

Per-adapter `git show --numstat` on the adapter file only (excluding the
audit docs each agent shipped alongside):

| Adapter | Commit | Added | Deleted | **Net** | LOC now |
|---|---|---:|---:|---:|---:|
| `mnist_fm.py` | `491eca3` | +18 | −51 | **−33** | 924 |
| `rectified_flow_cifar.py` | `1d3cd2f` | +37 | −76 | **−39** | 1317 |
| `twodim_fm.py` | `09c08c0` | +21 | −27 | **−6** | 1466 |
| `self_flow.py` | `16c8c3a` | +85 | −46 | **+39** | 1488 |
| **Total** | | **+161** | **−200** | **−39** | **5195** |

**Two numbers, and the honest one is the second:**

- **200 lines of inlined glue deleted** (gross deletions).
- **39 lines net removed** across the four files.

The gap is import blocks and delegation wrappers added back. `self_flow`
is the clearest case: it deleted 46 lines of hand-rolled path probing and
tensor conversion but added 85 lines of `adaptive_reflow.core` wiring, so
the file **grew by 39 lines**. Agent D reported this straight in
`docs/audit/wave42-self-flow-shrink.md` §5 ("the inlined glue did shrink,
but the file as a whole grew") and correctly noted the delta "does not
move D.1."

Quoting 200 as "lines removed" without the net figure would overstate the
result by ~5×. **Use −39.**

---

## 3. MUST-3 verdict: PARTIAL (unchanged)

`todo/framework-freeze-checklist.md` §MUST-3 requires four core modules
that each:

1. exist in `adaptive_reflow/core/`,
2. have ≥1 unit test in `tests/test_core/`,
3. **are imported by ≥2 of the new adapters (Kanzi / FreqFlow / MM-FM)**,
4. do not duplicate code already living in an adapter.

Measured at HEAD:

| Core module | LOC | Tests | Adapters importing it | Criterion 3 |
|---|---:|---|---|---|
| `ckpt_loader.py` | 574 | yes | `self_flow` (1) | **FAIL** |
| `diffusers_wrapper.py` | 613 | yes | `self_flow` (1) | **FAIL** |
| `graph_wrapper.py` | 714 | yes | `flowmol3` (1) | **FAIL** |
| `vae_decoder.py` | 715 | yes | *(none)* (0) | **FAIL** |

Only two adapters in the entire tree import `adaptive_reflow.core` at
all — `flowmol3.py` (4 references) and `self_flow.py` (6 references).

**The named adapters import zero core modules:**

- `adaptive_reflow/adapters/kanzi.py` — no `adaptive_reflow.core` import.
- `adaptive_reflow/adapters/freqflow.py` — no `adaptive_reflow.core` import.
- MM-FM — **no adapter file exists.** `ls adaptive_reflow/adapters/`
  shows `kanzi.py` and `freqflow.py` but no `mm_fm.py` / `mmfm.py`,
  despite task #492 ("Wave 21.5: Re-spawn MM-FM agent") being marked
  completed.

So criterion 3 is satisfied by **0 of 4** modules, and the gating
sentence in the checklist — "Per-adapter refactor: NOT STARTED … gated on
all 4 RANKING adapters existing" — is still literally true, because one
of the four RANKING adapters does not exist.

Wave 42 shrank `mnist_fm`, `twodim_fm`, `rectified_flow_cifar`, and
`self_flow`. Of these, only `self_flow` appears in the MUST-3 refactor
list (Kanzi / FreqFlow / MM-FM / Self-Flow / HiDream-I1 / Lumina). The
other three are legacy toy/CIFAR adapters that MUST-3 never named.

**Verdict: `MUST-3 = PARTIAL`.** The correct edit to the freeze
checklist is to record that 1 of 6 named adapters (Self-Flow) has been
refactored, not to flip the status.

### 3.1 What would actually close it

1. Wire `kanzi.py` and `freqflow.py` to `ckpt_loader` + `diffusers_wrapper`
   (both already load checkpoints and run diffusers-style forwards by
   hand). That alone takes criteria 3 from 0/4 to 2/4.
2. Ship the MM-FM adapter, or amend MUST-3 to drop MM-FM and re-baseline
   the "≥2 of the new adapters" quorum against the adapters that exist.
3. `vae_decoder.py` (715 LOC, 0 importers) is currently dead framework
   code. Either wire it to the latent-space adapters or mark it
   provisional — it should not count toward a PASS while unused.

---

## 4. Commit-message mislabel (flagged, not fixed)

Agent D's `self_flow` shrink was committed under
**`16c8c3a "docs(audit): Wave 40 Agent B — Phase 4 long-running
regression check"`**, whose diffstat is:

```
adaptive_reflow/adapters/self_flow.py     | 131 ++++++------
docs/audit/wave40-wave17-phase4-verify.md | 133 +++++++++++++
docs/audit/wave42-self-flow-shrink.md     | 260 +++++++++++++++++++++++
```

A Wave 42 adapter refactor is bundled into a commit labelled as a Wave 40
docs-audit. `git log --grep="Wave 42"` does not surface it, which is how
it nearly went uncounted in this synthesis. Left as-is (history is
already shared); noted so future audits searching by wave label know to
check `16c8c3a`.

---

## 5. Working-tree state

Modified and **uncommitted** at the time of writing:

- `tests/test_adapters/test_adapter_common.py` — the §1.1 regression fix.
  This should be committed before any push; without it `main` is red at
  `tests/test_adapters/`.

Also modified but outside this agent's scope (pre-existing, untouched
here): `adaptive_reflow/adapters/lineageflow.py`, `pyproject.toml`,
`requirements-lock.txt`, `tests/conftest.py`, several `docs/figures/*.png`
and `docs/r4-survey/exp3-results.json`.

---

## 6. Summary

- Test surface is **green**: 977 adapter tests, 18 compliance tests, 83
  core tests, `mkdocs --strict` exit 0.
- One Wave 42 regression found and fixed (stale `_make_ref` import).
- **−39 net lines** across four adapters (200 gross deletions, 161
  additions). `self_flow` grew.
- **MUST-3 remains PARTIAL.** All four core modules fail the "imported by
  ≥2 new adapters" criterion; Kanzi and FreqFlow import none, MM-FM does
  not exist, and `vae_decoder.py` has no importer at all.
- The shrink work is a genuine quality improvement to four adapters. It
  is not the work MUST-3 asks for.
