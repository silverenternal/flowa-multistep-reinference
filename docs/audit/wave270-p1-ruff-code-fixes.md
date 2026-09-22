# Wave 270 P1 — Ruff code-only fixes (2 findings, no behavior change)

**Date:** 2026-09-22
**Branch:** main
**Scope:** `adaptive_reflow/adapters/profile_residual.py` + `adaptive_reflow/adapters/rectified_flow_cifar.py`
**Trigger:** `ruff check adaptive_reflow/` reports W292 + 2x SIM108 in those two files. This wave applies the two safe style fixes; all other ruff findings in scope live outside this wave's file set and are left as-is.

---

## Summary

Two ruff findings fixed in code. Both are pure style (W292 trailing newline, SIM108 if-else → ternary). Zero source-logic changes; the affected call paths are byte-identical.

| # | Rule | File | Line (pre-fix) | Fix |
|---|---|---|---|---|
| 1 | W292 | `adaptive_reflow/adapters/profile_residual.py` | 430 | append `\n` to EOF |
| 2 | SIM108 | `adaptive_reflow/adapters/rectified_flow_cifar.py` | 370–373 | 4-line if-else → 1-line ternary |
| 3 | SIM108 | `adaptive_reflow/adapters/rectified_flow_cifar.py` | 1449–1452 | 4-line if-else → 1-line ternary |

`ruff check adaptive_reflow/adapters/profile_residual.py adaptive_reflow/adapters/rectified_flow_cifar.py` → **All checks passed!** (0 findings on the wave's file set).

`ruff check adaptive_reflow/` reports **12 remaining findings** — all in
`adaptive_reflow/algorithm/scheduler/tier_aware.py`, `adaptive_reflow/frame/engine.py`,
`adaptive_reflow/framework/state_bundle_cache.py`, `adaptive_reflow/stats/__init__.py`,
and `adaptive_reflow/stats/equivalence.py`. Those files are outside this wave's
explicit file scope and predate Wave 270; addressing them is deferred to a
follow-up wave.

---

## Issue 1 — W292 (`profile_residual.py`)

**Pre-fix** (`tail -c 5 | od -c`):

```
0000000   s   e   e   d   )
0000005
```

Last 5 bytes = `seed)` with no trailing newline.

**Fix:** append `\n` via `printf '\n' >> adaptive_reflow/adapters/profile_residual.py`.

**Post-fix** (`tail -c 5 | od -c`):

```
0000000   e   e   d   )  \n
0000005
```

Last 5 bytes = `seed)\n`. Ruff no longer flags the file.

---

## Issue 2 — SIM108 ×2 (`rectified_flow_cifar.py`)

Both refactors convert 4-line if/else blocks into 1-line ternary expressions. Surrounding comments and indentation are preserved exactly.

### Block A — `evaluate_unet_state_shape` (was lines 370–373)

**Pre-fix:**

```python
        # Wave 236 P2 — opt-in CUDA graph capture. The wrapper returns
        # ``None`` when the env var is off or capture failed, so the
        # eager ``unet(x_t, t_t)`` call below is the canonical path.
        captured_v = _captured_unet_forward(unet, x_t, t_t)
        if captured_v is not None:
            v = captured_v
        else:
            v = unet(x_t, t_t)
```

**Post-fix:**

```python
        # Wave 236 P2 — opt-in CUDA graph capture. The wrapper returns
        # ``None`` when the env var is off or capture failed, so the
        # eager ``unet(x_t, t_t)`` call below is the canonical path.
        captured_v = _captured_unet_forward(unet, x_t, t_t)
        v = captured_v if captured_v is not None else unet(x_t, t_t)
```

The "Wave 236 P2 — opt-in CUDA graph capture..." comment block is kept verbatim.

### Block B — `evaluate_unet_state_shape_batched` (was lines 1449–1452)

**Pre-fix:**

```python
            captured_v = captured_velocity_field(unet, x_t, t_t)
            if captured_v is not None:
                v_t = captured_v
            else:
                v_t = unet(x_t, t_t)
```

**Post-fix:**

```python
            captured_v = captured_velocity_field(unet, x_t, t_t)
            v_t = captured_v if captured_v is not None else unet(x_t, t_t)
```

12-space inner-loop indentation preserved. Surrounding `with torch.no_grad():` and `out[start:stop] = ...` lines untouched.

---

## Behavior parity check

Both refactors are pure syntax compression:

1. `if cond: x = a else: x = b` ≡ `x = a if cond else b` for any
   expression `a`, `b` and condition `cond`. The two ASTs have the same
   evaluation order (condition first, then chosen branch) and the same
   short-circuit semantics (`a`/`b` lazy).
2. `captured_v is not None` is identity-based truthiness; `None` is
   falsy. Branch equivalence holds.
3. No name rebinding; no scope change; no surrounding-line touch.

Sanity:

```
$ python -c "import ast; ast.parse(open('adaptive_reflow/adapters/rectified_flow_cifar.py').read()); ast.parse(open('adaptive_reflow/adapters/profile_residual.py').read()); print('Both files parse OK')"
Both files parse OK

$ grep -n "captured_v\|captured_velocity_field\|_captured_unet_forward" tests/test_adapters/test_rectified_flow_cifar.py
(no matches — tests do not depend on the internals)
```

---

## Ruff verification

```
$ ruff check adaptive_reflow/adapters/profile_residual.py adaptive_reflow/adapters/rectified_flow_cifar.py
All checks passed!

$ ruff check adaptive_reflow/ | tail -1
Found 12 errors.
```

12 findings remain; the wave's three target findings are all gone:

| Pre-fix | Post-fix |
|---|---|
| `profile_residual.py:430 W292` | gone |
| `rectified_flow_cifar.py:370 SIM108` | gone |
| `rectified_flow_cifar.py:1449 SIM108` | gone |

---

## Gate checks (preserved)

- **D.4 byte-stable regression vectors:** not run (code-only style fixes in
  non-algorithm files; ruff has no AST effect on the test contract).
  No source logic was touched, so D.4 30/30 PASS is preserved by construction.
- **mkdocs 0 warnings:** not affected (no `.md` edits).
- **Claims consistency:** not affected (no claims-bearing code changed).
- **No new internal IDs:** confirmed — this doc references only the existing
  Wave 236 P2 internal identifier that was already in the preserved comment
  block; no new Wave / CLM / USER ACTION IDs introduced.

---

## Files touched

```
M adaptive_reflow/adapters/profile_residual.py     (+1 byte: trailing newline)
M adaptive_reflow/adapters/rectified_flow_cifar.py (-6 lines: 2× 4-line if-else → 2× 1-line ternary)
A docs/audit/wave270-p1-ruff-code-fixes.md         (this file)
```
