# The mypy gate was skipped, not passing — and the skip covered 50 errors

**Date:** 2026-10-31
**Scope:** `adaptive_reflow/` type-check state, `tools/verify_submission_readiness.py`
gate 3 (`mypy_0`), and the two reviewer-facing rows that quote the result.
**Device:** CPU only. No GPU was used or needed.
**Environment:** `.venvs/flowmol3_venv/bin/python` (3.12, mypy 2.3.1),
cross-checked with a scratch `mypy 1.20.2` against the same interpreter.

---

## 1. Observed facts

1. `mypy` is **not** on `PATH` in this environment, and not installed for the
   system `python3`. It **is** installed in `.venvs/flowmol3_venv`:

   ```
   $ .venvs/flowmol3_venv/bin/python -m mypy --version
   mypy 2.3.1 (compiled: yes)
   ```

2. `tools/verify_submission_readiness.py:491` decided the gate with
   `shutil.which("mypy")` only, so the gate reported
   `SKIPPED` / `READY_WITH_SKIPS: mypy_0` — and its detail string said
   *"mypy not on PATH (sandbox without mypy); preserved from Wave 149 P5 audit"*.
   That sentence is false: mypy was in the tree the whole time.

3. Running the gate's own command in that venv, **before** any fix:

   ```
   $ .venvs/flowmol3_venv/bin/python -m mypy --strict adaptive_reflow/
   Found 50 errors in 16 files (checked 232 source files)
   ```

   A scratch `mypy 1.20.2` against the same interpreter gave **51** — the
   difference is one `import-untyped` for `yaml`, which mypy 2.x does not
   raise. So this is **not** a tool-version artifact: the tree was not
   `mypy --strict` clean under either 1.x or 2.x.

4. `pyproject.toml` already sets `strict = true` and
   `ignore_missing_imports = true`, so `mypy adaptive_reflow/` and
   `mypy --strict adaptive_reflow/` give the same result. The two
   reviewer-facing rows that quote the result are:

   | Surface | Text | Status at the time of this audit |
   |---|---|---|
   | `tnnls_submission/tables.md:89` | `Mypy type-check \| **0 errors** \| mypy adaptive_reflow/` | false (50) |
   | `tnnls_submission/MANIFEST.md:231` | `- **mypy type-check:** 0 errors.` | false (50) |
   | `tnnls_submission/SUBMISSION_READINESS.md:263` | `mypy --strict adaptive_reflow → 0 errors in 230 files` (2026-10-11) | true then; false by 2026-10-31 |

5. Error breakdown before the fix, by category:

   | Category | Count | Cause |
   |---|---|---|
   | `var-annotated` | 14 | numpy expression with an `Any` operand (`int(self._x.shape[1])`) collapses the overload |
   | `no-untyped-call` | 8 | `Bio.SeqIO.parse`, `torch.cuda.Stream`, `torch.cuda.CUDAGraph`, `diffusers.*.from_pretrained` |
   | `unused-ignore` | 7 | `# type: ignore[no-any-return]` left behind by earlier toolchains |
   | `no-any-return` | 6 | `nn.Module.__call__` is typed `Callable[..., Any]` in torch stubs |
   | `attr-defined` | 5 | `Bio.SeqIO.SeqRecord`, `diffusers.SiTTransformer2DModel`, implicit re-export of `MNIST_FLAT_DIM` |
   | `assignment` | 5 | `torch = None` / `SeqIO = None` optional-dependency fallbacks; `family: Tensor = None` |
   | `arg-type` | 3 | same optional-dependency narrowing, downstream |
   | `return-value` | 2 | `Module.__getattr__`'s `Tensor \| Module` union on a registered parameter |

   None of these is a runtime defect. Every one is a typing-boundary statement:
   either the annotation was missing, or a third-party stub is coarser than the
   runtime.

## 2. What changed

| File | Change | Why |
|---|---|---|
| `core/graph_wrapper.py` | `ei: NDArray[np.int64]` | ternary with an `Any` branch |
| `algorithm/perturbation/perturbation.py` | `logp/cons/theta/simplex: Any` | numpy ops on `Any` operands |
| `framework/cuda_graph_capture.py` | 2 × `# type: ignore[no-untyped-call]` | torch CUDA stubs |
| `legacy/control_policy.py` | `# type: ignore[assignment]` | optional-torch fallback |
| `eval/{freq_l1,amino_acid_recovery}.py` | `# type: ignore[no-untyped-call]` | `Bio.SeqIO.parse` is untyped |
| `adapters/protbfn_abbfn_model.py` | class-level `inv_freq: torch.Tensor`; 4 × `cast` | `Module.__getattr__` union + `nn.Module.__call__` returning `Any` |
| `adapters/protbfn_abbfn_adapter.py` | 2 × `# type: ignore[assignment]`, 2 × `# type: ignore[attr-defined]`, `net_full: Any`, 1 unused-ignore removed | optional-Bio fallback, `SeqIO.SeqRecord` re-export, numpy |
| `adapters/hidream_i1.py` | class-level `_dummy: torch.Tensor`; 3 × `# type: ignore[no-untyped-call]` | same two boundaries |
| `adapters/_hidream_i1_upstream_shim.py` | 1 × `# type: ignore[attr-defined]`, 4 unused-ignores removed | `diffusers.pipelines.hidream_image` re-export |
| `adapters/lineageflow.py` | 4 × `Any` annotations, 1 unused-ignore removed | numpy + a `__path__` assignment |
| `adapters/kanzi.py` | `family: torch.Tensor \| None`; 1 × `cast` | PEP 484 implicit-Optional default |
| `adapters/self_flow.py` | `# type: ignore[attr-defined]` | `diffusers.SiTTransformer2DModel` |
| `adapters/lumina_image_2_0.py` | `# type: ignore[no-untyped-call]` | `from_pretrained` |
| `adapters/flowmol3_v2_adapter.py` | 4 × `Any` annotations | numpy |
| `adapters/mnist_fm.py` | `"MNIST_FLAT_DIM"` added to `__all__` | explicit re-export (`no_implicit_reexport` under `--strict`) |

`mnist_fm.py` was the only file where the fix was a *contract* change rather
than an annotation: `MNIST_FLAT_DIM` is imported into `mnist_fm` from
`mnist_fm_train` and consumed by `mnist_fm_torch`, so the honest statement is
"this module re-exports it", which `__all__` says.

## 3. The gate fix

`tools/verify_submission_readiness.py` now resolves the executable in two
steps (`_resolve_mypy`): `PATH`, then `.venvs/*/bin/mypy`. The gate detail
string records which one it used. This matters beyond this file — a gate that
answers "SKIPPED" when the tool is present is indistinguishable from a gate
that passes, and it was covering 50 errors while the submission package
asserted zero.

## 4. Verification

| Gate | Result |
|---|---|
| `.venvs/flowmol3_venv/bin/python -m mypy --strict adaptive_reflow/` | `Success: no issues found in 232 source files` (was 50 errors / 16 files) |
| `ruff check adaptive_reflow/ tests/ scripts/ tools/` | All checks passed |
| `pytest tests/test_adapters/ -q` | 1213 passed, 72 skipped |
| `pytest tests/test_d4_regression_vectors.py -q` | 30 passed |
| `python3 tools/verify_submission_readiness.py` | `READY: all gates passed` (9/9, 0 skips; was `READY_WITH_SKIPS: mypy_0`) |

## 5. Gaps and caveats

- **The 0 is toolchain-scoped.** mypy 2.3.1 in `.venvs/flowmol3_venv` is the
  reading quoted in `tables.md`; a mypy 1.20.2 run against the same
  interpreter additionally wants `types-PyYAML` installed, because 1.x reports
  `import-untyped` for an installed-but-untyped package where 2.x does not.
  The code is clean under both; only the stub package differs.
- **`# type: ignore` is version-fragile.** `warn_unused_ignores = true` means
  a future stub improvement turns these ignores into errors. That is the
  intended behaviour — the ignore is a statement that a boundary is untyped
  *today*, and the gate should complain when that stops being true.
- **CLM-024 is untouched.** It records the historical Round-2 `33→0` over 118
  files plus an additive 2026-09-14 reframe quoting 988 errors. Neither
  number is rewritten here; the current reading is recorded in this note and
  in `AGENTS.md` §4.1's command list (which also now gives the working
  invocation, since `mypy` alone is not on `PATH`).
- **`docs/baseline-audit-report.md:1037`, `docs/models/*.model_card.md`** —
  the same pass replaced dead `docs/lessons-learned.md` / `todo/models/*.md`
  pointers on the reviewer-reachable model cards. Those files have not existed
  since 2026-10-13; the citations are now marked retired or reduced to the
  lesson label, with the lesson text kept inline.
