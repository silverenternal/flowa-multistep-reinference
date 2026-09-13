# Wave 101 Layer-3 P2-A real-checkpoint eval audit

Date: 2026-09-13.

`tests/test_tools/test_run_real_ckpt_eval.py` is already a compatibility
shim from Wave 104. The former 2409-LOC module was split into six files under
`tests/test_tools/eval/`; the shim contains no test functions, preserving
pytest's single discovery location and all original names.

Baseline/verification:

```
pytest --collect-only -q tests/test_tools/eval  # 44 tests collected
pytest -q tests/test_tools/eval/test_cli.py     # 3 passed
```

No additional split is safe or necessary. Moving the existing shim or
sub-files would break documented backward paths without reducing test
coupling. Test counts, names, and D.4 assets remain unchanged.
