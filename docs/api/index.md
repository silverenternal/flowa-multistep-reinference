# API reference

This page is the index for the auto-generated API reference for the
`adaptive_reflow` package. Each per-package page below is rendered by
[mkdocstrings][mkdocstrings] directly from the module-level docstrings
and typed signatures of the corresponding subpackage -- nothing in this
section is hand-authored, so the rendered reference cannot drift from
the code as long as the source docstrings stay accurate.

[mkdocstrings]: https://mkdocstrings.github.io/

## Layout

The `adaptive_reflow` package is organised as a stack of subpackages with
one-way dependency arrows (top of the stack may import from the bottom;
the reverse is forbidden). The pages below are listed top-of-stack first:

| Page | Subpackage | Role |
|------|------------|------|
| [Contracts](adaptive_reflow.contracts.md) | `adaptive_reflow.contracts` | Pure-stdlib typed contracts: dataclasses, NewType aliases, hash helpers, validators. The leaf of the dependency graph. |
| [Universal](adaptive_reflow.universal.md) | `adaptive_reflow.universal` | Model-family-agnostic kernel: Flow Matching ODE re-inference engine + adapter / evaluator / mixer Protocols + envelope dataclasses. |
| [Frame](adaptive_reflow.frame.md) | `adaptive_reflow.frame` | The universal round frame: engine driver + bounded merge + channel rule + operation order + phase transitions + round-trace v3 + orchestrator. |
| [Molecular](adaptive_reflow.molecular.md) | `adaptive_reflow.molecular` | Concrete molecule layer: pocket-conditioned 3D flow matching channel vocabulary, stratification, RMS-preserving coordinate mixer, GNINA / PoseBusters / QED / ADMET evaluators. |
| [Eval](adaptive_reflow.eval.md) | `adaptive_reflow.eval` | DTB-R7 (calibration + paired evaluation + manifest I/O) + DTB-R8 (claim gate + promotion + rollback + layered metric panel). |
| [Adapters](adaptive_reflow.adapters.md) | `adaptive_reflow.adapters` | Concrete `FlowMatchingODEAdapter` implementations (synthetic fixtures + FlowMol3 + Reference FlowA). |

## How to regenerate

From the repo root:

```bash
.venv/Scripts/python.exe -m mkdocs build --strict
```

The output lands in `site/`. The dev toolchain is pinned in
`pyproject.toml` under `[project.optional-dependencies].dev`
(`mkdocs>=1.5`, `mkdocstrings[python]>=0.24`).

## Why some pages are short

mkdocstrings renders the **module-level docstring** of each subpackage
and then every public symbol re-exported from that subpackage's
`__init__.py`. Subpackages whose `__init__.py` is mostly re-exports
(versus a richly-documented module entry point) will look thin -- that
is by design. For per-symbol docstrings, follow the cross-references
inside each page; the auto-generated headings link straight to the
canonical home of each symbol.

## Doc-claim verification

The `tools/check_docs_against_code.py` linter walks every governance
markdown (this page is excluded via the `docs/api/` exclusion list) and
verifies that every class / function / path / inline-symbol claim is
defined in the codebase. The auto-generated `docs/api/*.md` pages are
explicitly excluded because their content is derived from the code
itself -- verifying them against the code would be circular.
